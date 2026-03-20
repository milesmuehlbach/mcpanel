import hashlib
import pathlib
import requests

class ServerDownloader:

    @staticmethod
    def get_available_versions() -> list[dict]:
        return []

    @staticmethod
    def download_version(uid: str, hash: str | None, base_path: pathlib.Path) -> None:
        pass

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

DOWNLOADERS = {
    "mojang": MojangDownloader
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
