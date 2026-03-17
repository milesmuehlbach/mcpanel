from argon2 import PasswordHasher
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import json
import jwt
from pydantic import BaseModel
import secrets
import sqlite3

from app.downloaders import java

def _normalize_permissions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for item in value:
        if not isinstance(item, str):
            continue

        permission = item.strip()
        if not permission or permission in seen:
            continue

        seen.add(permission)
        normalized.append(permission)

    return normalized

def get_db() -> sqlite3.Connection:
    return sqlite3.connect("minecraft/default.db")

def init_db() -> None:
    with get_db() as db:
        db.execute("PRAGMA journal_mode=WAL;")
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_argon2 TEXT NOT NULL,
                permissions TEXT NOT NULL
            );
            """
        )

def get_setting(key: str, value: str) -> str:
    with get_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is not None:
            return row[0]

        db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise RuntimeError(f"failed to init setting: {key}")

        return row[0]

def get_user_permissions(uid: int):
    with get_db() as db:
        row = db.execute(
            "SELECT permissions FROM users WHERE id = ?",
            (uid,),
        ).fetchone()

    if row is None:
        raise HTTPException(404, "user not found")

    permissions = row[0]

    try:
        parsed = json.loads(permissions)
        normalized = _normalize_permissions(parsed)
    except json.JSONDecodeError:
        normalized = []

    if permissions != json.dumps(normalized):
        with get_db() as db:
            db.execute(
                "UPDATE users SET permissions = ? WHERE id = ?",
                (json.dumps(normalized), uid),
            )

    return normalized

def has_permissions(uid: int, required_permission: str) -> bool:
    permissions = get_user_permissions(uid)
    if "admin" in permissions:
        return True

    required_permission = required_permission.strip()
    if not required_permission:
        return False

    accepted_permissions = {required_permission}
    parts = required_permission.split(".")
    for index in range(1, len(parts)):
        accepted_permissions.add(".".join(parts[:index]))

    return any(permission in accepted_permissions for permission in permissions)

########
# INIT #
########

ph = PasswordHasher()
api = APIRouter()
V1 = APIRouter(prefix="/v1")
bearer = HTTPBearer(auto_error=False)

init_db()
JWT_SECRET = get_setting("jwt_secret", secrets.token_urlsafe(32))

##################
# AUTH ENDPOINTS #
##################

def get_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "missing or invalid authorization")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid or expired token")

    uid = payload.get("id")
    if not isinstance(uid, int):
        raise HTTPException(401, "invalid token payload")

    return uid

def require_permission(required_permission: str):
    def dependency(
        uid: int = Depends(get_user_id),
    ) -> None:
        # implicitly requires formal auth
        if not has_permissions(uid, required_permission):
            raise HTTPException(403, "insufficient permissions")

    return dependency

class AuthCredentialsInterface(BaseModel):
    username: str
    password: str

@V1.post("/auth/login")
async def _v1_auth_login(
    body: AuthCredentialsInterface,
):
    username = body.username
    password = body.password

    with get_db() as db:
        result = db.execute(
            "SELECT id, password_argon2 FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if result is None:
        raise HTTPException(401, "invalid username or password")
    
    try:
        uid = result[0]
        hash = result[1]
        ph.verify(hash, password)
    except Exception:
        raise HTTPException(401, "invalid username or password")
    
    token = jwt.encode(
        {
            "id": uid,
            "exp": int((datetime.now() + timedelta(hours=24)).timestamp())
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return {"message": "login successful", "token": token}

@V1.post(
    "/auth/register",
    dependencies=[Depends(require_permission("users.register_user"))],
)
async def _v1_auth_register(
    body: AuthCredentialsInterface,
):
    username = body.username
    password = body.password

    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "username must be 1-32 characters")

    if len(password) < 12:
        raise HTTPException(400, "password must be at least 12 characters")

    password_hash = ph.hash(password)

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO users (username, password_argon2, permissions) VALUES (?, ?, ?)",
                (
                    username,
                    password_hash,
                    json.dumps([])
                ),
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "username already exists")

    return {"message": "registration successful"}

@V1.get("/auth/onboarding")
async def _v1_auth_onboarding_get():
    with get_db() as db:
        user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    if user_count > 0:
        return {"message": "onboarding not allowed", "status": False}
    
    return {"message": "onboarding allowed", "status": True}

@V1.post("/auth/onboarding")
async def _v1_auth_onboarding_post(
    body: AuthCredentialsInterface,
):
    username = body.username
    password = body.password

    with get_db() as db:
        user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    if user_count > 0:
        raise HTTPException(403, "onboarding not allowed")

    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "username must be 1-32 characters")

    if len(password) < 12:
        raise HTTPException(400, "password must be at least 12 characters")

    password_hash = ph.hash(password)

    with get_db() as db:
        db.execute(
            "INSERT INTO users (username, password_argon2, permissions) VALUES (?, ?, ?)",
            (
                username,
                password_hash,
                json.dumps(["admin"])
            ),
        )

    return {"message": "onboarding successful"}

@V1.get("/auth/permissions")
async def _v1_auth_permissions(
    uid: int = Depends(get_user_id),
):
    with get_db() as db:
        result = db.execute(
            "SELECT permissions FROM users WHERE id = ?",
            (uid,),
        ).fetchone()

    if result is None:
        raise HTTPException(404, "user not found")

    return {"message": "success", "permissions": json.loads(result[0])}

#######################
# COMPONENT ENDPOINTS #
#######################

@V1.get(
    "/components/list",
    dependencies=[Depends(require_permission("components.list_components"))],
)
async def _v1_components_list(
    type: str,
):
    match type:
        case "jre":
            return {"message": "success", "components": java.get_available_runtimes()}
        case _:
            raise HTTPException(400, "invalid component type")

api.include_router(V1)
