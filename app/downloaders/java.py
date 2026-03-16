import requests
import hashlib

PRISM_META_URL = "https://meta.prismlauncher.org/v1/"
SUPPORTED_RUNTIMES = ["net.minecraft.java", "com.azul.java", "net.adoptium.java"]

def get_available_runtimes():
    s = requests.Session()

    r = s.get(PRISM_META_URL + "index.json")
    r.raise_for_status()

    try:
        json = r.json()
    except:
        raise ValueError(f"upstream error in prism metadata: invalid json")

    if json.get("formatVersion") != 1:
        raise ValueError(f"upstream error in prism metadata: unsupported format version")

    valid_uids = {}
    for package in json.get("packages", []):
        if package.get("uid") in SUPPORTED_RUNTIMES:
            valid_uids[package.get("uid")] = package.get("sha256")
    
    for uid, sha256 in valid_uids.items():
        r = s.get(PRISM_META_URL + uid + "/index.json")

        if hashlib.sha256(r.content).hexdigest() != sha256:
            raise ValueError(f"upstream error in prism metadata: sha256 mismatch for {uid}")        
        
        try:
            json = r.json()
        except:
            raise ValueError(f"upstream error in prism metadata: invalid json")
        
        if json.get("formatVersion") != 1:
            raise ValueError(f"upstream error in prism metadata: unsupported format version")
        
        if json.get("uid") != uid:
            raise ValueError(f"upstream error in prism metadata: uid mismatch for {uid}")
        
        for version in json.get("versions", []):
            yield {
                "uid": f"jre:{uid}:{version.get('version')}",
                "type": "jre",
                "component": uid,
                "version": version.get("version"),
                "display_type": "Runtime",
                "display_component": {"net.minecraft.java": "OpenJDK", "com.azul.java": "Azul", "net.adoptium.java": "Adoptium"}.get(uid, uid),
                "display_version": version.get("version"),
                "sha256": version.get("sha256"),
                "releaseTime": version.get("releaseTime"),
            }