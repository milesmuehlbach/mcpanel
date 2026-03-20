import hashlib
import pathlib
import re
import requests

class ServerDownloader:
    @staticmethod
    def get_available_versions() -> list[dict]:
        return []

    @staticmethod
    def download_version(uid: str, hash: str | None, base_path: pathlib.Path) -> None:
        raise ValueError(f"unknown unspecified server version uid: {uid}")

class MojangDownloader(ServerDownloader):
    MOJANG_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"

    @staticmethod
    def get_available_versions() -> list[dict]:
        s = requests.Session()
        r = s.get(MojangDownloader.MOJANG_MANIFEST_URL)
        r.raise_for_status()
        
        try:
            json = r.json()
        except:
            raise ValueError("upstream error in mojang metadata: invalid json")
        
        entries = []
        for version in json.get("versions", []):
            display_type = "Server"
            display_component = "Mojang"
            display_version = f"{
                "Snapshot " if version.get("type") == "snapshot" else ""
            }{
                version.get("id")
            }"
            
            entries.append(
                {
                    "uid": f"server:mojang:{version.get('type')}-{version.get('id')}",
                    "type": "server",
                    "component": "mojang",
                    "version": f"{version.get('type')}-{version.get('id')}",
                    "display_type": display_type,
                    "display_component": display_component,
                    "display_version": display_version,
                    "display_name": f"{display_component} {display_type} {display_version}",
                    "hashes": {
                        "md5": version.get("md5"),
                        "sha1": version.get("sha1"), # only sha1 should be present in mojang manifest
                        "sha256": version.get("sha256")
                    },
                    "released_at": version.get("releaseTime"),
                }
            )
        
        return entries
    
    @staticmethod
    def download_version(uid: str, hash: str | None, base_path: pathlib.Path) -> None:
        s = requests.Session()
        r = s.get(MojangDownloader.MOJANG_MANIFEST_URL)
        r.raise_for_status()
        
        try:
            json = r.json()
        except:
            raise ValueError("upstream error in mojang metadata: invalid json")
        
        for version in json.get("versions", []):
            if f"server:mojang:{version.get('type')}-{version.get('id')}" != uid: continue

            r = s.get(version.get("url"))
            r.raise_for_status()

            if hashlib.sha1(r.content).hexdigest() != hash:
                raise ValueError("upstream error in mojang metadata: hash mismatch in version metadata")
            
            try:
                json = r.json()
            except:
                raise ValueError("upstream error in mojang metadata: invalid json")

            server = json.get("downloads", {}).get("server", {})
            url = server.get("url")
            sha1 = server.get("sha1")
            size_bytes = server.get("size")

            if not isinstance(url, str) or not url:
                raise ValueError("upstream error in mojang metadata: missing server url")

            if not isinstance(sha1, str) or not sha1:
                raise ValueError("upstream error in mojang metadata: missing server sha1")

            if not isinstance(size_bytes, int) or size_bytes < 0:
                raise ValueError("upstream error in mojang metadata: missing server size")

            server_response = s.get(url)
            server_response.raise_for_status()

            server_bytes = server_response.content
            if len(server_bytes) != size_bytes:
                raise ValueError("downloaded server size mismatch")

            if hashlib.sha1(server_bytes).hexdigest() != sha1:
                raise ValueError("downloaded server sha1 mismatch")

            jar_path = base_path / "jar" / f"{uid.replace(':', '_')}.jar"
            jar_path.parent.mkdir(parents=True, exist_ok=True)
            jar_path.write_bytes(server_bytes)

            return

        raise ValueError(f"unknown mojang server version uid: {uid}")

class PaperDownloader(ServerDownloader):
    PAPER_MANIFEST_URL = "https://fill.papermc.io/v3/projects/paper/versions"

    @staticmethod
    def get_available_versions() -> list[dict]:
        s = requests.Session()
        r = s.get(PaperDownloader.PAPER_MANIFEST_URL)
        r.raise_for_status()
        
        try:
            json = r.json()
        except:
            raise ValueError("upstream error in paper metadata: invalid json")
        
        entries = []
        for version in json.get("versions", []):
            id = version.get("version", {}).get("id")
            build = max(version.get("builds", []), default=0)
            status = "release" if re.fullmatch(r'^\d+\.\d+(\.\d+)?$', id) else "snapshot"
            
            display_type = "Server"
            display_component = "Paper"
            display_version = f"{
                "Snapshot " if status == "snapshot" else ""
            }{id} (build {build})"

            entries.append(
                {
                    "uid": f"server:paper:{status}-{id}-{build}",
                    "type": "server",
                    "component": "paper",
                    "version": f"{status}-{id}-{build}",
                    "display_type": display_type,
                    "display_component": display_component,
                    "display_version": display_version,
                    "display_name": f"{display_component} {display_type} {display_version}",
                    "hashes": {
                        "md5": None,
                        "sha1": None,
                        "sha256": None,
                    },
                    "released_at": None
                }
            )

        return entries
    
    @staticmethod
    def download_version(uid: str, hash: None, base_path: pathlib.Path) -> None:
        # expect hash to be None and ignore it bc paper metadata doesn't include it

        s = requests.Session()

        uid_version = uid.removeprefix("server:paper:")
        version_parts = uid_version.split("-")
        if len(version_parts) < 3:
            raise ValueError(f"invalid paper server version uid: {uid}")
        
        version_type = version_parts[0]
        version_id = version_parts[1]
        version_build = version_parts[2]

        r = s.get(f"{PaperDownloader.PAPER_MANIFEST_URL}/{version_id}/builds/{version_build}")
        try:
            r.raise_for_status()
        except:
            raise ValueError(f"unknown paper server version uid: {uid}")

        try:
            json = r.json()
        except:
            raise ValueError("upstream error in paper metadata: invalid json")
        
        build = json.get("id")
        downloads = json.get("downloads", {}).get("server:default", {}) # if "server:default" changes, i'm sliming ts out
        paper_name = downloads.get("name") # this is PAPER's name for the server jar, not OURS!!!
        sha256 = downloads.get("checksums", {}).get("sha256")
        size = downloads.get("size")
        url = downloads.get("url")

        if not isinstance(build, int) or build < 0:
            raise ValueError("upstream error in paper metadata: missing build number")
        
        if not isinstance(paper_name, str) or not paper_name:
            raise ValueError("upstream error in paper metadata: missing version name")

        if not isinstance(url, str) or not url:
            raise ValueError("upstream error in paper metadata: missing server url")

        if not isinstance(sha256, str) or not sha256:
            raise ValueError("upstream error in paper metadata: missing server sha256")

        if not isinstance(size, int) or size < 0:
            raise ValueError("upstream error in paper metadata: missing server size")
        
        if version_build != str(build):
            raise ValueError(f"upstream error in paper metadata: build number mismatch for uid {uid}")
        
        if version_id not in paper_name:
            raise ValueError(f"upstream error in paper metadata: version id mismatch for uid {uid}")

        server_response = s.get(url)
        server_response.raise_for_status()

        server_bytes = server_response.content
        if len(server_bytes) != size:
            raise ValueError("downloaded server size mismatch")

        if hashlib.sha256(server_bytes).hexdigest() != sha256:
            raise ValueError("downloaded server sha256 mismatch")

        jar_path = base_path / "jar" / f"{uid.replace(':', '_')}.jar"
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        jar_path.write_bytes(server_bytes)

DOWNLOADERS = {
    "mojang": MojangDownloader,
    "paper": PaperDownloader
}

def get_available_versions() -> list[dict]:
    entries = []
    for downloader_cls in DOWNLOADERS.values():
        entries.extend(downloader_cls.get_available_versions())
    return entries

def download_version(uid: str, hash: str | None, base_path: pathlib.Path) -> None:
    for server_type, downloader_cls in DOWNLOADERS.items():
        if uid.startswith(f"server:{server_type}:"):
            return downloader_cls.download_version(uid, hash, base_path)
    
    raise ValueError(f"unknown server version uid: {uid}")
