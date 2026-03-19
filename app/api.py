from argon2 import PasswordHasher
from dataclasses import asdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import json
import jwt
import os
from pathlib import Path
from pydantic import BaseModel
import secrets
import sqlite3

from app.downloaders import java
from app.tasks import TaskManager

WORKING_PATH_ENV = "MCPANEL_PATH"

def get_workdir() -> Path:
    return Path(os.environ.get(WORKING_PATH_ENV, "./minecraft")).resolve()

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
task_manager = TaskManager()

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

##################
# AUTH ENDPOINTS #
##################

class AuthCredentialsInterface(BaseModel):
    username: str
    password: str

class AuthPermissionsInterface(BaseModel):
    user_id: int | None = None
    permissions: dict[str, bool]

@V1.post("/auth/login")
async def _v1_auth_login(
    body: AuthCredentialsInterface
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
    body: AuthCredentialsInterface
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
    body: AuthCredentialsInterface
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
async def _v1_auth_permissions_get(
    uid: int = Depends(get_user_id),
    user_id: int | None = None
):
    target_uid = uid
    if user_id is not None and user_id != uid:
        if not has_permissions(uid, "permissions.view_permissions"):
            raise HTTPException(403, "insufficient permissions")
        target_uid = user_id

    permissions = get_user_permissions(target_uid)

    return {"message": "success", "permissions": permissions}

@V1.post(
    "/auth/permissions",
    dependencies=[Depends(require_permission("permissions.set_permissions"))],
)
async def _v1_auth_permissions_post(
    body: AuthPermissionsInterface,
    uid: int = Depends(get_user_id)
):
    target_uid = uid if body.user_id is None else body.user_id
    target_permissions = set(get_user_permissions(target_uid))
    updated_permissions = set(target_permissions)
    is_other_user = target_uid != uid

    for permission, enabled in body.permissions.items():
        permission = permission.strip()
        if not permission:
            raise HTTPException(400, "invalid permission")

        if is_other_user and not has_permissions(uid, permission):
            raise HTTPException(403, "insufficient permissions")

        if not enabled:
            if is_other_user and not has_permissions(uid, "permissions.view_permissions"):
                raise HTTPException(403, "insufficient permissions")

            if not is_other_user and permission == "admin" and "admin" in target_permissions:
                continue

            updated_permissions.discard(permission)
            continue

        updated_permissions.add(permission)

    normalized_permissions = sorted(updated_permissions)

    with get_db() as db:
        db.execute(
            "UPDATE users SET permissions = ? WHERE id = ?",
            (json.dumps(normalized_permissions), target_uid),
        )

    return {"message": "success", "permissions": normalized_permissions}

#######################
# COMPONENT ENDPOINTS #
#######################

class ComponentInstallInterface(BaseModel):
    uid: str
    sha256: str

@V1.get(
    "/components/list",
    dependencies=[Depends(require_permission("components.list_components"))]
)
async def _v1_components_list(
    type: str,
):
    match type:
        case "jre":
            return {"message": "success", "components": java.get_available_runtimes()}
        case _:
            raise HTTPException(400, "invalid component type")

@V1.post(
    "/components/install",
    dependencies=[Depends(require_permission("components.install_component"))],
)
async def _v1_components_install(
    body: ComponentInstallInterface
):
    match body.uid.strip().split(":", 1)[0]:
        case "jre":
            task_id = task_manager.enqueue(
                java.download_runtime,
                body.uid,
                body.sha256,
                get_workdir(),
                name=f"Install JRE ({body.uid})",
            )
            return {"message": "success", "task_id": task_id}
        case _:
            raise HTTPException(400, "invalid component type")

##################
# TASK ENDPOINTS #
##################

@V1.get(
    "/tasks/list",
    dependencies=[Depends(require_permission("tasks.list_tasks"))]
)
async def _v1_tasks_list():
    return {
        "message": "success",
        "tasks": [asdict(task) for task in task_manager.list_tasks()],
    }

@V1.get(
    "/tasks/status",
    dependencies=[Depends(require_permission("tasks.get_status"))]
)
async def _v1_tasks_status(
    task_id: str
):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return {"message": "success", "task": asdict(task)}


api.include_router(V1)
