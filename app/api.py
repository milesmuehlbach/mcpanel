from argon2 import PasswordHasher
from dataclasses import asdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel, StringConstraints
import secrets
import sqlite3
from typing import Annotated
from uuid import UUID

from app.database import (
    create_user,
    get_setting,
    get_user_count,
    get_user_login_record,
    get_user_permissions as load_user_permissions,
    get_username,
    init_db,
    get_installed_components,
    install_jre_component,
    install_server_component,
    set_user_permissions,
)
from app.downloaders import java, server
from app.instances import InstanceManager
from app.paths import WORKING_PATH_ENV, get_workdir
from app.tasks import TaskManager

def get_user_permissions(uid: int) -> list[str]:
    permissions = load_user_permissions(uid)
    if permissions is None:
        raise HTTPException(404, "user not found")
    return permissions

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
get_workdir().mkdir(parents=True, exist_ok=True)

init_db()
JWT_SECRET = get_setting("jwt_secret", secrets.token_urlsafe(32))
# TODO: ts InstanceManager and TaskManager only work bc we're currently running only ONE FastAPI worker process! scaling to multiple workers fails, ts may need to be db-based in ts (near? far? who tf knows) future
instance_manager = InstanceManager(get_workdir())
task_manager = TaskManager()

def get_auth_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, object]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "missing or invalid authorization")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "invalid or expired token")

    uid = payload.get("id")
    if not isinstance(uid, int):
        raise HTTPException(401, "invalid token payload")

    return payload

def get_user_id(
    payload: dict[str, object] = Depends(get_auth_payload),
) -> int:
    uid = payload.get("id")
    if isinstance(uid, bool) or not isinstance(uid, int):
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
    username = body.username.lower()
    password = body.password

    result = get_user_login_record(username)

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
    username = body.username.lower()
    password = body.password

    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "username must be 1-32 characters")

    if len(password) < 12:
        raise HTTPException(400, "password must be at least 12 characters")

    password_hash = ph.hash(password)

    try:
        create_user(username, password_hash, [])
    except sqlite3.IntegrityError:
        raise HTTPException(409, "username already exists")

    return {"message": "registration successful"}

@V1.get("/auth/me")
async def _v1_auth_me(
    payload: dict[str, object] = Depends(get_auth_payload),
):
    uid = payload.get("id")
    exp = payload.get("exp")

    if isinstance(uid, bool) or not isinstance(uid, int):
        raise HTTPException(401, "invalid token payload")

    username = get_username(uid)
    if username is None:
        raise HTTPException(401, "invalid token payload")

    expires_at = exp if isinstance(exp, int) else None

    return {
        "message": "token is valid",
        "status": True,
        "user": {
            "id": uid,
            "username": username,
        },
        "expires_at": expires_at,
    }

@V1.get("/auth/onboarding")
async def _v1_auth_onboarding_get():
    user_count = get_user_count()
    if user_count > 0:
        return {"message": "onboarding not allowed", "status": False}
    
    return {"message": "onboarding allowed", "status": True}

@V1.post("/auth/onboarding")
async def _v1_auth_onboarding_post(
    body: AuthCredentialsInterface
):
    username = body.username
    password = body.password

    user_count = get_user_count()
    if user_count > 0:
        raise HTTPException(403, "onboarding not allowed")

    username = username.strip()
    if not username or len(username) > 32:
        raise HTTPException(400, "username must be 1-32 characters")

    if len(password) < 8:
        raise HTTPException(400, "password must be at least 8 characters")

    password_hash = ph.hash(password)

    create_user(username, password_hash, ["admin"])

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

    set_user_permissions(target_uid, normalized_permissions)

    return {"message": "success", "permissions": normalized_permissions}

#######################
# COMPONENT ENDPOINTS #
#######################

MD5Hash = Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{32}$")]
SHA1Hash = Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{40}$")]
SHA256Hash = Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{64}$")]

class ComponentInstallInterface(BaseModel):
    uid: str
    md5: MD5Hash | None = None
    sha1: SHA1Hash | None = None
    sha256: SHA256Hash | None = None

@V1.get(
    "/components/list",
    dependencies=[Depends(require_permission("components.list_components"))]
)
async def _v1_components_list(
    type: str,
):
    # TODO: query and cache available components on init
    
    match type:
        case "jre":
            return {"message": "success", "components": java.get_available_runtimes()}
        case "server":
            return {"message": "success", "components": server.get_available_versions()}
        case _:
            raise HTTPException(400, "invalid component type")

@V1.post(
    "/components/install",
    dependencies=[Depends(require_permission("components.install_component"))],
)
async def _v1_components_install(
    body: ComponentInstallInterface
):
    ##############################################################################################
    # future TODO: 1. save size and hash data of installed components in db                      #
    #              2. verify integrity of installed components on launch                         #
    #              3. uninstall components?/repair them? (idk) if integrity check fails          #
    # probably around the time we implement component database, management, uninstallation, etc. #
    ##############################################################################################

    match body.uid.strip().split(":", 1)[0]:
        case "jre":
            sha256 = body.sha256.strip() if body.sha256 is not None else ""
            if not sha256:
                raise HTTPException(400, "sha256 is required for jre installation")

            task_id = task_manager.enqueue(
                install_jre_component,
                body.uid,
                sha256,
                get_workdir(),
                name=f"Install JRE ({body.uid})",
            )
            return {"message": "success", "task_id": task_id}
        case "server":
            server_type = body.uid.strip().split(":")[1]
            hash = None

            match server_type:
                case "mojang":
                    hash = body.sha1.strip() if body.sha1 is not None else ""
                    if not hash:
                        raise HTTPException(400, "sha1 is required for mojang server installation")
                case "paper":
                    hash = None # setting it again here for clarity

            task_id = task_manager.enqueue(
                install_server_component,
                body.uid,
                hash,
                get_workdir(),
                name=f"Install Server ({body.uid})",
            )
            return {"message": "success", "task_id": task_id}
        case _:
            raise HTTPException(400, "invalid component type")

@V1.get("/components/installed")
def _v1_components_installed():
    components = get_installed_components()
    return {"message": "success", "components": components}

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

######################
# INSTANCE ENDPOINTS #
######################

class InstanceInterface(BaseModel):
    uuid: str

class OptionalInstanceInterface(InstanceInterface):
    uuid: str | None = None

class InstanceParameterInterface(BaseModel):
    server_uid: str
    java_uid: str
    name: str | None = None
    memory: int | None = None
    arguments: list[str] | None = None

@V1.get(
    "/instances/list",
    dependencies=[Depends(require_permission("instances.list_instances"))]
)
async def _v1_instances_list():
    return {"message": "success", "instances": [instance.build_info() for instance in instance_manager.get_instances()]}

@V1.post(
    "/instances/check",
    dependencies=[Depends(require_permission("instances.list_instances"))]
)
async def _v1_instances_check(
    body: InstanceInterface
):
    if instance_manager.has_instance(body.uuid):
        return {"message": "success", "status": True}
    return {"message": "success", "status": False}

@V1.post(
    "/instances/reload",
    dependencies=[Depends(require_permission("instances.create_instance"))] # TODO: maybe a seperate instances.manage_instances permission is more ideal? figure ts out ltr
)
async def _v1_instances_reload(
    body: OptionalInstanceInterface
):
    if body.uuid is None:
        instance_manager.scan_instances()
        return {"message": "success"}
    else:
        instance_manager.reload_instance(body.uuid)
        return {"message": "success"}

@V1.post(
    "/instances/create",
    dependencies=[Depends(require_permission("instances.create_instance"))]
)
async def _v1_instances_create(
    body: InstanceParameterInterface
):
    instance = instance_manager.create_instance(
        server_uid=body.server_uid,
        java_uid=body.java_uid,
        name=body.name,
        memory=body.memory,
        arguments=body.arguments,
    )
    return {"message": "success", "uuid": instance.uuid, "instance": instance.build_info()}

@V1.post(
    "/instances/{instance_uuid:uuid}/start",
    dependencies=[Depends(require_permission("instances.start_instance"))]
)
async def _v1_instances_start(
    instance_uuid: UUID,
):
    if not instance_manager.has_instance(instance_uuid):
        raise HTTPException(404, "instance not found")

    def start_task() -> dict[str, object]:
        instance = instance_manager.start_instance(instance_uuid)
        return {
            "action": "start",
            "uuid": str(instance.uuid),
            "running": instance.running,
            "instance": instance.build_info(),
        }

    task_id = task_manager.enqueue(
        start_task,
        name=f"Start Instance ({instance_uuid})",
    )
    return {"message": "success", "task_id": task_id}


@V1.post(
    "/instances/{instance_uuid:uuid}/stop",
    dependencies=[Depends(require_permission("instances.stop_instance"))]
)
async def _v1_instances_stop(
    instance_uuid: UUID,
):
    if not instance_manager.has_instance(instance_uuid):
        raise HTTPException(404, "instance not found")

    def stop_task() -> dict[str, object]:
        instance = instance_manager.stop_instance(instance_uuid)
        return {
            "action": "stop",
            "uuid": str(instance.uuid),
            "running": instance.running,
            "instance": instance.build_info(),
        }

    task_id = task_manager.enqueue(
        stop_task,
        name=f"Stop Instance ({instance_uuid})",
    )
    return {"message": "success", "task_id": task_id}


@V1.post(
    "/instances/{instance_uuid:uuid}/restart",
    dependencies=[Depends(require_permission("instances.stop_instance"))] # TODO: again, maybe seperate instances.restart_instance or a general instance.manage_instance permission? debate for later
)
async def _v1_instances_restart(
    instance_uuid: UUID,
):
    if not instance_manager.has_instance(instance_uuid):
        raise HTTPException(404, "instance not found")

    def restart_task() -> dict[str, object]:
        instance = instance_manager.restart_instance(instance_uuid)
        return {
            "action": "restart",
            "uuid": str(instance.uuid),
            "running": instance.running,
            "instance": instance.build_info(),
        }

    task_id = task_manager.enqueue(
        restart_task,
        name=f"Restart Instance ({instance_uuid})",
    )
    return {"message": "success", "task_id": task_id}

api.include_router(V1)
