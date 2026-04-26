import concurrent.futures
import hashlib
import io
import json
import os
import pathlib
import platform
import requests
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
from typing import Any
import zipfile

try:
    import lzma
except ImportError:
    lzma = None

PRISM_META_URL = "https://meta.prismlauncher.org/v1/"
SUPPORTED_RUNTIMES = ["net.minecraft.java", "com.azul.java", "net.adoptium.java"]

MAX_DOWNLOAD_WORKERS = 8
JAVA_EXECUTABLE_NAMES = {"java", "java.exe"}

_THREAD_LOCAL = threading.local()


def _get_platform_string() -> str:
    system = platform.system()
    architecture = platform.machine()

    runtime_system = {
        "Windows": "windows",
        "Darwin": "mac-os",
        "Linux": "linux",
    }.get(system, system)
    runtime_architecture = {
        "x86_64": "x64",
        "AMD64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(architecture, architecture)

    return f"{runtime_system}-{runtime_architecture}"


def _get_download_session() -> requests.Session:
    session = getattr(_THREAD_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        _THREAD_LOCAL.session = session

    return session


def _validate_download_payload(data: bytes, download: dict[str, Any], context: str):
    size = download.get("size")
    if size is not None and len(data) != size:
        raise ValueError(f"{context} size mismatch")

    sha256 = download.get("sha256")
    if sha256 is not None and hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError(f"{context} sha256 mismatch")

    sha1 = download.get("sha1")
    if sha1 is not None and hashlib.sha1(data).hexdigest() != sha1:
        raise ValueError(f"{context} sha1 mismatch")


def _resolve_runtime_path(base_path: pathlib.Path, relative_path: str) -> pathlib.Path:
    resolved_base_path = base_path.resolve()
    resolved_target_path = (base_path / relative_path).resolve()

    try:
        resolved_target_path.relative_to(resolved_base_path)
    except ValueError:
        raise ValueError(
            f"upstream error in runtime manifest: invalid path {relative_path}"
        )

    return resolved_target_path


def _select_runtime_download(
    entry: dict[str, Any], relative_path: str
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    downloads = entry.get("downloads")
    if not isinstance(downloads, dict):
        raise ValueError(
            f"upstream error in runtime manifest: missing downloads for {relative_path}"
        )

    raw_download = downloads.get("raw")
    if raw_download is not None and not isinstance(raw_download, dict):
        raise ValueError(
            f"upstream error in runtime manifest: invalid raw download for {relative_path}"
        )

    lzma_download = downloads.get("lzma")
    if lzma_download is not None and not isinstance(lzma_download, dict):
        raise ValueError(
            f"upstream error in runtime manifest: invalid lzma download for {relative_path}"
        )

    if lzma_download is not None and lzma is not None:
        return "lzma", lzma_download, raw_download

    if raw_download is not None:
        return "raw", raw_download, raw_download

    if lzma_download is not None:
        raise ValueError(f"python lzma support is required to install {relative_path}")

    raise ValueError(
        f"upstream error in runtime manifest: missing downloads for {relative_path}"
    )


def _write_runtime_file(
    target_path: pathlib.Path,
    data: bytes,
    executable: bool | None = None,
    mode: int | None = None,
):
    target_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb",
            delete=False,
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_file.write(data)
            temp_path = pathlib.Path(temp_file.name)

        temp_path.replace(target_path)

        if platform.system() != "Windows":
            if mode is not None:
                target_path.chmod(mode)
            elif executable is not None:
                target_path.chmod(0o755 if executable else 0o644)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def _get_archive_member_path(member_name: str) -> pathlib.PurePosixPath:
    member_path = pathlib.PurePosixPath(member_name.replace("\\", "/"))
    if member_path.is_absolute() or ".." in member_path.parts:
        raise ValueError(
            f"upstream error in runtime archive: invalid path {member_name}"
        )

    return member_path


def _get_java_prefix(
    member_paths: list[pathlib.PurePosixPath],
) -> pathlib.PurePosixPath:
    candidates = set()
    for member_path in member_paths:
        if len(member_path.parts) < 2:
            continue

        if (
            member_path.parts[-2] != "bin"
            or member_path.name not in JAVA_EXECUTABLE_NAMES
        ):
            continue

        candidates.add(member_path.parent.parent)

    if not candidates:
        raise ValueError("upstream error in runtime archive: missing JAVA_HOME")

    ordered_candidates = sorted(
        candidates, key=lambda candidate: (len(candidate.parts), str(candidate))
    )
    if len(ordered_candidates) > 1 and len(ordered_candidates[0].parts) == len(
        ordered_candidates[1].parts
    ):
        raise ValueError("upstream error in runtime archive: ambiguous JAVA_HOME")

    return ordered_candidates[0]


def _resolve_archive_symlink_target(
    staged_runtime_path: pathlib.Path,
    link_path: pathlib.Path,
    link_target: str,
    context: str,
) -> pathlib.Path:
    if not isinstance(link_target, str) or not link_target:
        raise ValueError(
            f"upstream error in runtime archive: invalid symlink target ({context})"
        )

    normalized_target = link_target.replace("\\", "/")
    if pathlib.PurePosixPath(normalized_target).is_absolute():
        raise ValueError(
            f"upstream error in runtime archive: invalid symlink target ({context})"
        )

    resolved_staged_runtime_path = staged_runtime_path.resolve()
    resolved_target_path = (link_path.parent / normalized_target).resolve()

    try:
        resolved_target_path.relative_to(resolved_staged_runtime_path)
    except ValueError:
        raise ValueError(
            f"upstream error in runtime archive: invalid symlink target ({context})"
        )

    return resolved_target_path


def _materialize_archive_symlink(
    link_path: pathlib.Path,
    link_target: str,
    resolved_target_path: pathlib.Path,
    context: str,
):
    if link_path.is_symlink() or link_path.exists():
        if link_path.is_dir() and not link_path.is_symlink():
            shutil.rmtree(link_path)
        else:
            link_path.unlink()

    link_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        os.symlink(
            link_target, link_path, target_is_directory=resolved_target_path.is_dir()
        )
        return
    except AttributeError, NotImplementedError, OSError:
        pass

    if resolved_target_path.is_file():
        shutil.copy2(resolved_target_path, link_path)
        return

    if resolved_target_path.is_dir():
        shutil.copytree(resolved_target_path, link_path)
        return

    raise ValueError(
        f"upstream error in runtime archive: unsupported symlink target ({context})"
    )


def _finalize_archive_symlinks(
    staged_runtime_path: pathlib.Path,
    symlink_entries: list[tuple[pathlib.Path, str, str]],
):
    pending_entries = symlink_entries[:]
    while pending_entries:
        next_pending_entries: list[tuple[pathlib.Path, str, str]] = []
        progress_made = False

        for link_path, link_target, context in pending_entries:
            resolved_target_path = _resolve_archive_symlink_target(
                staged_runtime_path,
                link_path,
                link_target,
                context,
            )

            if not (resolved_target_path.exists() or resolved_target_path.is_symlink()):
                next_pending_entries.append((link_path, link_target, context))
                continue

            _materialize_archive_symlink(
                link_path, link_target, resolved_target_path, context
            )
            progress_made = True

        if not progress_made:
            unresolved_context = ", ".join(
                context for _, _, context in next_pending_entries[:3]
            )
            raise ValueError(
                f"upstream error in runtime archive: unresolved symlink target ({unresolved_context})"
            )

        pending_entries = next_pending_entries


def _extract_zip_runtime(zip_content: bytes, runtime_path: pathlib.Path):
    runtime_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        archive = zipfile.ZipFile(io.BytesIO(zip_content))
    except zipfile.BadZipFile:
        raise ValueError("upstream error in runtime archive: invalid zip")

    with archive:
        java_home_prefix = _get_java_prefix(
            [
                _get_archive_member_path(info.filename)
                for info in archive.infolist()
                if not info.is_dir()
            ]
        )

        with tempfile.TemporaryDirectory(dir=runtime_path.parent) as temp_dir:
            staged_runtime_path = pathlib.Path(temp_dir) / "runtime"
            staged_runtime_path.mkdir(parents=True, exist_ok=True)

            extracted_files = 0
            symlink_entries: list[tuple[pathlib.Path, str, str]] = []
            for info in archive.infolist():
                member_path = _get_archive_member_path(info.filename)
                if java_home_prefix != pathlib.PurePosixPath("."):
                    try:
                        relative_member_path = member_path.relative_to(java_home_prefix)
                    except ValueError:
                        continue
                else:
                    relative_member_path = member_path

                if str(relative_member_path) == ".":
                    continue

                target_path = _resolve_runtime_path(
                    staged_runtime_path, str(relative_member_path)
                )

                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                mode = info.external_attr >> 16
                if mode and stat.S_ISLNK(mode):
                    with archive.open(info, "r") as member_file:
                        symlink_target_data = member_file.read()

                    try:
                        symlink_target = symlink_target_data.decode("utf-8")
                    except UnicodeDecodeError:
                        raise ValueError(
                            f"upstream error in runtime archive: invalid symlink target ({info.filename})"
                        )

                    if "\x00" in symlink_target:
                        raise ValueError(
                            f"upstream error in runtime archive: invalid symlink target ({info.filename})"
                        )

                    symlink_entries.append((target_path, symlink_target, info.filename))
                    continue

                with archive.open(info, "r") as member_file:
                    data = member_file.read()

                if not mode:
                    mode = (
                        0o755
                        if relative_member_path.name in JAVA_EXECUTABLE_NAMES
                        else 0o644
                    )

                _write_runtime_file(target_path, data, mode=mode)
                extracted_files += 1

            _finalize_archive_symlinks(staged_runtime_path, symlink_entries)

            if extracted_files == 0:
                raise ValueError("upstream error in runtime archive: empty JAVA_HOME")

            if not any(
                (staged_runtime_path / "bin" / name).is_file()
                for name in JAVA_EXECUTABLE_NAMES
            ):
                raise ValueError(
                    "upstream error in runtime archive: missing java executable"
                )

            if runtime_path.exists():
                if runtime_path.is_dir():
                    shutil.rmtree(runtime_path)
                else:
                    runtime_path.unlink()

            shutil.move(str(staged_runtime_path), str(runtime_path))


def _extract_tar_gz_runtime(tar_gz_content: bytes, runtime_path: pathlib.Path):
    runtime_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        archive = tarfile.open(fileobj=io.BytesIO(tar_gz_content), mode="r:gz")
    except tarfile.TarError:
        raise ValueError("upstream error in runtime archive: invalid tar.gz")

    with archive:
        java_home_prefix = _get_java_prefix(
            [
                _get_archive_member_path(member.name)
                for member in archive.getmembers()
                if member.isfile() or member.issym() or member.islnk()
            ]
        )

        with tempfile.TemporaryDirectory(dir=runtime_path.parent) as temp_dir:
            staged_runtime_path = pathlib.Path(temp_dir) / "runtime"
            staged_runtime_path.mkdir(parents=True, exist_ok=True)

            extracted_files = 0
            symlink_entries: list[tuple[pathlib.Path, str, str]] = []
            for member in archive.getmembers():
                member_path = _get_archive_member_path(member.name)
                if java_home_prefix != pathlib.PurePosixPath("."):
                    try:
                        relative_member_path = member_path.relative_to(java_home_prefix)
                    except ValueError:
                        continue
                else:
                    relative_member_path = member_path

                if str(relative_member_path) == ".":
                    continue

                target_path = _resolve_runtime_path(
                    staged_runtime_path, str(relative_member_path)
                )

                if member.isdir():
                    target_path.mkdir(parents=True, exist_ok=True)
                    continue

                if member.issym():
                    if "\x00" in member.linkname:
                        raise ValueError(
                            f"upstream error in runtime archive: invalid symlink target ({member.name})"
                        )

                    symlink_entries.append((target_path, member.linkname, member.name))
                    continue

                if not (member.isfile() or member.islnk()):
                    raise ValueError(
                        f"upstream error in runtime archive: unsupported entry type ({member.name})"
                    )

                extracted_member = archive.extractfile(member)
                if extracted_member is None:
                    raise ValueError(
                        f"upstream error in runtime archive: failed to extract {member.name}"
                    )

                with extracted_member:
                    data = extracted_member.read()

                mode = member.mode or (
                    0o755
                    if relative_member_path.name in JAVA_EXECUTABLE_NAMES
                    else 0o644
                )
                _write_runtime_file(target_path, data, mode=mode)
                extracted_files += 1

            _finalize_archive_symlinks(staged_runtime_path, symlink_entries)

            if extracted_files == 0:
                raise ValueError("upstream error in runtime archive: empty JAVA_HOME")

            if not any(
                (staged_runtime_path / "bin" / name).is_file()
                for name in JAVA_EXECUTABLE_NAMES
            ):
                raise ValueError(
                    "upstream error in runtime archive: missing java executable"
                )

            if runtime_path.exists():
                if runtime_path.is_dir():
                    shutil.rmtree(runtime_path)
                else:
                    runtime_path.unlink()

            shutil.move(str(staged_runtime_path), str(runtime_path))


def _remove_macos_quarantine(runtime_path: pathlib.Path):
    if platform.system() != "Darwin":
        return

    try:
        subprocess.run(
            ["xattr", "-dr", "com.apple.quarantine", str(runtime_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        pass


def _download_json_runtime_file(
    base_path: pathlib.Path, relative_path: str, entry: dict[str, Any]
):
    variant, download, final_download = _select_runtime_download(entry, relative_path)

    url = download.get("url")
    if not isinstance(url, str) or not url:
        raise ValueError(
            f"upstream error in runtime manifest: missing url for {relative_path}"
        )

    session = _get_download_session()
    response = session.get(url)
    response.raise_for_status()

    payload = response.content
    _validate_download_payload(
        payload, download, f"downloaded runtime file {variant}: {relative_path}"
    )

    file_data = payload
    if variant == "lzma":
        try:
            file_data = lzma.decompress(payload)
        except Exception:
            raise ValueError(
                f"downloaded runtime file lzma decode failed: {relative_path}"
            )

    if final_download is not None:
        _validate_download_payload(
            file_data, final_download, f"downloaded runtime file raw: {relative_path}"
        )

    target_path = _resolve_runtime_path(base_path, relative_path)
    _write_runtime_file(
        target_path, file_data, executable=bool(entry.get("executable"))
    )


def _download_json_runtime(manifest_content: bytes, base_path: pathlib.Path):
    try:
        manifest = json.loads(manifest_content)
    except Exception:
        raise ValueError("upstream error in runtime manifest: invalid json")

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("upstream error in runtime manifest: missing files")

    base_path.mkdir(parents=True, exist_ok=True)

    file_entries: list[tuple[str, dict[str, Any]]] = []
    for relative_path, entry in files.items():
        if not isinstance(relative_path, str):
            raise ValueError("upstream error in runtime manifest: invalid path")

        if not isinstance(entry, dict):
            raise ValueError(
                f"upstream error in runtime manifest: invalid entry for {relative_path}"
            )

        entry_type = entry.get("type")
        if entry_type == "directory":
            _resolve_runtime_path(base_path, relative_path).mkdir(
                parents=True, exist_ok=True
            )
            continue

        if entry_type != "file":
            raise ValueError(
                f"upstream error in runtime manifest: unsupported entry type for {relative_path}"
            )

        file_entries.append((relative_path, entry))

    if not file_entries:
        return

    worker_count = min(MAX_DOWNLOAD_WORKERS, len(file_entries))
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _download_json_runtime_file, base_path, relative_path, entry
            )
            for relative_path, entry in file_entries
        ]

        for future in concurrent.futures.as_completed(futures):
            future.result()


def get_available_runtimes():
    s = requests.Session()

    r = s.get(PRISM_META_URL + "index.json")
    r.raise_for_status()

    try:
        json = r.json()
    except:
        raise ValueError("upstream error in prism metadata: invalid json")

    if json.get("formatVersion") != 1:
        raise ValueError("upstream error in prism metadata: unsupported format version")

    valid_uids = {}
    for package in json.get("packages", []):
        if package.get("uid") in SUPPORTED_RUNTIMES:
            valid_uids[package.get("uid")] = package.get("sha256")

    entries = []
    for id, sha256 in valid_uids.items():
        r = s.get(PRISM_META_URL + id + "/index.json")

        if hashlib.sha256(r.content).hexdigest() != sha256:
            raise ValueError(
                f"upstream error in prism metadata: sha256 mismatch for {id}"
            )

        try:
            json = r.json()
        except:
            raise ValueError(f"upstream error in prism metadata: invalid json")

        if json.get("formatVersion") != 1:
            raise ValueError(
                f"upstream error in prism metadata: unsupported format version"
            )

        if json.get("uid") != id:
            raise ValueError(f"upstream error in prism metadata: uid mismatch for {id}")

        for version in json.get("versions", []):
            display_type = "Java"
            display_component = {
                "net.minecraft.java": "OpenJDK",
                "com.azul.java": "Azul",
                "net.adoptium.java": "Adoptium",
            }.get(id, id)
            display_version = version.get("version").replace("java", "")

            entries.append(
                {
                    "uid": f"jre:{id}:{version.get('version')}",
                    "type": "jre",
                    "component": id,
                    "version": version.get("version"),
                    "display_type": display_type,
                    "display_component": display_component,
                    "display_version": display_version,
                    "display_name": f"{display_component} {display_type} {display_version}",
                    "hashes": {
                        "md5": version.get("md5"),
                        "sha1": version.get("sha1"),
                        "sha256": version.get(
                            "sha256"
                        ),  # only sha256 should be present in prism metadata
                    },
                    "released_at": version.get("releaseTime"),
                }
            )

    return entries


def download_runtime(uid: str, sha256: str | None, base_path: pathlib.Path):
    s = requests.Session()

    parts = uid.split(":")
    if len(parts) != 3 or parts[0] != "jre":
        raise ValueError(f"invalid runtime uid: {uid}")

    component = parts[1]
    version = parts[2]

    if component not in SUPPORTED_RUNTIMES:
        raise ValueError(f"unsupported runtime component: {component}")

    metadata_response = s.get(PRISM_META_URL + component + "/" + version + ".json")
    metadata_response.raise_for_status()

    if (
        sha256 is not None
        and hashlib.sha256(metadata_response.content).hexdigest() != sha256
    ):
        raise ValueError(f"downloaded runtime sha256 mismatch")

    try:
        metadata = metadata_response.json()
    except:
        raise ValueError(f"upstream error in prism metadata: invalid json")

    if metadata.get("formatVersion") != 1:
        raise ValueError(
            f"upstream error in prism metadata: unsupported format version"
        )

    platform_string = _get_platform_string()

    runtimes = sorted(
        metadata.get("runtimes", []),
        key=lambda runtime: (
            runtime.get("version", {}).get("major", 0),
            runtime.get("version", {}).get("minor", 0),
            runtime.get("version", {}).get("security", 0),
        ),
        reverse=True,
    )

    url = None
    runtime_sha256 = None
    for runtime in runtimes:
        if runtime.get("runtimeOS") != platform_string:
            continue

        runtime_url = runtime.get("url")
        if not isinstance(runtime_url, str) or not runtime_url:
            raise ValueError("upstream error in prism metadata: missing runtime url")

        checksum = runtime.get("checksum")
        if isinstance(checksum, dict) and checksum.get("type") == "sha256":
            checksum_hash = checksum.get("hash")
            if isinstance(checksum_hash, str) and checksum_hash:
                runtime_sha256 = checksum_hash

        url = runtime_url
        break

    if url is None:
        raise ValueError(f"no runtime found for platform: {platform_string}")

    r = s.get(url)
    r.raise_for_status()

    if (
        runtime_sha256 is not None
        and hashlib.sha256(r.content).hexdigest() != runtime_sha256
    ):
        raise ValueError(f"downloaded runtime sha256 mismatch")

    runtime_path = base_path / "jre" / component / version

    if url.endswith(".json"):
        _download_json_runtime(r.content, runtime_path)
    elif url.endswith(".zip"):
        _extract_zip_runtime(r.content, runtime_path)
    elif url.endswith(".tar.gz"):
        _extract_tar_gz_runtime(r.content, runtime_path)
    else:
        pass

    _remove_macos_quarantine(runtime_path)
