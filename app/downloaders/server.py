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

            # uid format:
            # server:mojang:release-1.21.11

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
        pass

DOWNLOADERS = {
    "mojang": MojangDownloader
}

def get_available_versions() -> list[dict]:
    entries = []
    for downloader_cls in DOWNLOADERS.values():
        entries.extend(downloader_cls.get_available_versions())
    return entries

def download_version(uid: str, hash: str | None, base_path: pathlib.Path) -> None:
    for downloader_cls in DOWNLOADERS.values():
        if uid.startswith(f"server:{downloader_cls.__name__.lower()}:"):
            return downloader_cls.download_version(uid, hash, base_path)
    
    raise ValueError(f"unknown server version uid: {uid}")