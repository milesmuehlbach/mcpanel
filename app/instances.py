import datetime
import json
import pathlib
import platform
import psutil
import re
import shutil
import subprocess
import threading
import uuid

from app.database import get_installed_components

MEM_DATA = psutil.virtual_memory()
DEFAULT_MB = max(1024, min(8192, int(MEM_DATA.total / 1024 / 1024 / (4 if platform.system() == "Windows" else 2))))
DEFAULT_ARGUMENTS = [
    "-XX:+AlwaysPreTouch",
    "-XX:+DisableExplicitGC",
    "-XX:+ParallelRefProcEnabled",
    "-XX:+PerfDisableSharedMem",
    "-XX:+UnlockExperimentalVMOptions",
    "-XX:+UseG1GC",
    "-XX:G1HeapRegionSize=8M",
    "-XX:G1HeapWastePercent=5",
    "-XX:G1MaxNewSizePercent=40",
    "-XX:G1MixedGCCountTarget=4",
    "-XX:G1MixedGCLiveThresholdPercent=90",
    "-XX:G1NewSizePercent=30",
    "-XX:G1RSetUpdatingPauseTimePercent=5",
    "-XX:G1ReservePercent=20",
    "-XX:InitiatingHeapOccupancyPercent=15",
    "-XX:MaxGCPauseMillis=200",
    "-XX:MaxTenuringThreshold=1",
    "-XX:SurvivorRatio=32",
    "-DIReallyKnowWhatIAmDoingISwear"
]

DEFAULT_PARAMTERS = [
    "nogui"
]

JAVA_COMPONENT_UID_PATTERN = re.compile(r"^jre:(?!.*\.{2})[a-z.]+:[a-z0-9]+$")
SERVER_COMPONENT_UID_PATTERN = re.compile(r"^server:[a-z]+:(?!.*\.{2})[a-z0-9.-]+$")

def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def _to_datetime(timestamp: int | float) -> datetime.datetime:
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    return datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

def _is_valid_timestamp(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0

def _to_epoch_seconds(value: datetime.datetime) -> int:
    return int(value.timestamp())

class Instance:
    def __init__(self, uuid: uuid.UUID, base_path: pathlib.Path):
        self.uuid = uuid
        self.base_path = base_path.resolve()
        self.path = self.base_path / "instances" / str(uuid)
        self.json = self.path / "instance.json"

        now = _utcnow()
        self.created_at = now
        self.updated_at = now

        self._name = ""
        self._jar = None
        self._java = None
        self._memory = DEFAULT_MB
        self._arguments = list(DEFAULT_ARGUMENTS)
        self._persistence = False

        self.set_defaults()
        self.load_instance_config()
        self._persistence = True

        self.process = None
        self.running = False
        self.bridge_thread = None

    def set_defaults(self):
        now = _utcnow()

        self._name = f"My Instance {self.uuid.hex[:8]}"
        self._jar = None
        self._java = None
        self._memory = DEFAULT_MB
        self._arguments = list(DEFAULT_ARGUMENTS)

        self.created_at = now
        self.updated_at = now
    
    def build_info(self) -> dict:
        return {
            "version": 1,
            "uuid": str(self.uuid),
            "name": self.name,
            "jar": self.jar,
            "java": self.java,
            "memory": self.memory,
            "arguments": list(self.arguments),
            "created_at": _to_epoch_seconds(self.created_at),
            "updated_at": _to_epoch_seconds(self.updated_at)
        }

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("name must be a non-empty string")
        self._name = value
        self.updated_at = _utcnow()
        if self._persistence:
            self.save_instance_config()

    @property
    def jar(self) -> str | None:
        return self._jar

    @jar.setter
    def jar(self, value: str | None):
        if value is not None and not isinstance(value, str):
            raise ValueError("jar must be a string or None")
        self._jar = value
        self.updated_at = _utcnow()
        if self._persistence:
            self.save_instance_config()

    @property
    def java(self) -> str | None:
        return self._java

    @java.setter
    def java(self, value: str | None):
        if value is not None and not isinstance(value, str):
            raise ValueError("java must be a string or None")
        self._java = value
        self.updated_at = _utcnow()
        if self._persistence:
            self.save_instance_config()

    @property
    def memory(self) -> int:
        return self._memory

    @memory.setter
    def memory(self, value: int):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError("memory must be a positive integer")
        self._memory = value
        self.updated_at = _utcnow()
        if self._persistence:
            self.save_instance_config()

    @property
    def arguments(self) -> list[str]:
        return list(self._arguments)

    @arguments.setter
    def arguments(self, value: list[str]):
        if not isinstance(value, list) or not all(isinstance(argument, str) for argument in value):
            raise ValueError("arguments must be a list of strings")
        self._arguments = list(value)
        self.updated_at = _utcnow()
        if self._persistence:
            self.save_instance_config()

    def load_instance_config(self):
        try:
            config = json.loads(self.json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.save_instance_config() # save ts defaults
            return

        if not isinstance(config, dict):
            self.save_instance_config()
            return
        
        version = config.get("version")
        if isinstance(version, int) and version > 0:
            match version:
                case 1:
                    name = config.get("name")
                    if isinstance(name, str) and name.strip():
                        self._name = name

                    jar = config.get("jar")
                    if jar is None or isinstance(jar, str):
                        self._jar = jar

                    java = config.get("java")
                    if java is None or isinstance(java, str):
                        self._java = java

                    memory = config.get("memory")
                    if isinstance(memory, int) and not isinstance(memory, bool) and memory > 0:
                        self._memory = memory

                    arguments = config.get("arguments")
                    if isinstance(arguments, list) and all(isinstance(argument, str) for argument in arguments):
                        self._arguments = list(arguments)

                    created_at = config.get("created_at")
                    if _is_valid_timestamp(created_at):
                        self.created_at = _to_datetime(created_at)

                    updated_at = config.get("updated_at")
                    if _is_valid_timestamp(updated_at):
                        self.updated_at = _to_datetime(updated_at)
                case _:
                    return

    def save_instance_config(self):
        self.path.mkdir(parents=True, exist_ok=True)
        self.json.write_text(json.dumps(self.build_info(), indent=4), encoding="utf-8")
    
    @staticmethod
    def create_instance(base_path: pathlib.Path, server_uid: str, java_uid: str, name: str | None = None, memory: int | None = None, arguments: list[str] | None = None) -> Instance:
        base_path = base_path.resolve()
        installed_components = get_installed_components()
        if server_uid not in installed_components:
            raise ValueError(f"specified server component with uid '{server_uid}' is not installed")
        if java_uid not in installed_components:
            raise ValueError(f"specified java component with uid '{java_uid}' is not installed")
        
        instance = Instance(uuid.uuid4(), base_path)
        # vulnerable, validate!!!
        if name is not None:
            instance.name = name
        if memory is not None:
            instance.memory = memory
        if arguments is not None:
            instance.arguments = arguments
        instance.jar = f"{server_uid.replace(':', '_')}.jar"
        instance.java = java_uid

        instance.save_instance_config()

        source_server_jar = instance._get_server_jar()
        destination_server_jar = instance.path / source_server_jar.name
        shutil.copy2(source_server_jar, destination_server_jar)

        eula_path = instance.path / "eula.txt"
        eula_path.write_text(f"# This file was generated by MCPanel at {instance.updated_at}, with the acknowledgement of the user.\n# By using MCPanel, you agree to the Minecraft EULA at https://www.minecraft.net/eula\n\neula=true\n", encoding="utf-8")

        return instance
    
    @staticmethod
    def delete_instance(base_path: pathlib.Path, uuid: uuid.UUID):
        instance_root = (base_path / "instances").resolve()
        instance_path = (instance_root / str(uuid)).resolve()

        if instance_path.parent != instance_root:
            raise ValueError(f"refusing to delete unexpected path: {instance_path}")
        if not instance_path.exists():
            raise FileNotFoundError(f"instance path does not exist: {instance_path}")
        if not instance_path.is_dir() or instance_path.is_symlink():
            raise ValueError(f"refusing to delete non-directory or symlink path: {instance_path}")

        pending_delete_path = instance_root / f".deleting-{uuid}-{_to_epoch_seconds(_utcnow())}"
        if pending_delete_path.exists():
            raise FileExistsError(f"temporary deletion path already exists: {pending_delete_path}")

        instance_path.rename(pending_delete_path)
        try:
            shutil.rmtree(pending_delete_path)
        except Exception:
            pending_delete_path.rename(instance_path)
            raise

    def start(self):
        if self.running:
            raise RuntimeError(f"instance {self.uuid} is already running")

        java_executable = self._get_java_executable()
        source_server_jar = self._get_server_jar()
        instance_server_jar = (self.path / source_server_jar.name).resolve()
        if not instance_server_jar.is_file():
            raise FileNotFoundError(f"instance server jar not found at expected path: {instance_server_jar}")

        command = [
            str(java_executable),
            f"-Xmx{self.memory}M",
            f"-Xms{self.memory}M",
            *self.arguments,
            "-jar",
            str(instance_server_jar.name),
            *DEFAULT_PARAMTERS
        ]

        # TODO: automatically restart server on crash? make it a user option?
        self.process = subprocess.Popen(
            command,
            cwd=self.path.resolve(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self.running = True

        self.bridge_thread = threading.Thread(target=self._bridge_runner, daemon=True)
        self.bridge_thread.start()

    def stop(self):
        # TODO: maybe move waiting logic to bridge thread?
        # ideally the exposed API should be non-blocking
        if self.process and self.running:
            self.sendline("stop")
            self.process.wait()
            self.running = False
        
    def sendline(self, cmd):
        if self.process and self.running and self.process.stdin:
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush() 
        else:
            raise RuntimeError(f"instance {self.uuid} is not running")
    
    def _bridge_runner(self):
        while self.running and self.process and self.process.stdout:
            lineout = self.process.stdout.readline()
            if not lineout:
                break
            
            print(f"[SERVER] {lineout.strip()}")
            
        self.running = False

    def _get_java_executable(self) -> pathlib.Path:
        if not isinstance(self.java, str) or not JAVA_COMPONENT_UID_PATTERN.fullmatch(self.java):
            raise ValueError(f"invalid java uid format: {self.java}")

        java_parts = self.java.split(":")

        java_executable = (self.base_path / pathlib.Path(*java_parts) / "bin" / ("java.exe" if platform.system() == "Windows" else "java")).resolve()
        if self.base_path not in java_executable.parents:
            raise ValueError(f"resolved java executable escaped base path: {java_executable}")
        if not java_executable.is_file():
            raise FileNotFoundError(f"java executable not found at expected path: {java_executable}")
        return java_executable
    
    def _get_server_jar(self) -> pathlib.Path:
        if not isinstance(self.jar, str) or not self.jar.endswith(".jar"):
            raise ValueError("server jar is not set")

        server_uid = self.jar[:-4].replace("_", ":")
        if not SERVER_COMPONENT_UID_PATTERN.fullmatch(server_uid):
            raise ValueError(f"invalid server uid format: {server_uid}")

        jar_name = f"{server_uid.replace(':', '_')}.jar"
        if self.jar != jar_name:
            raise ValueError(f"invalid server jar filename: {self.jar}")

        jar_root = (self.base_path / "jar").resolve()
        server_jar = (jar_root / jar_name).resolve()
        if server_jar.parent != jar_root:
            raise ValueError(f"resolved server jar escaped jar root: {server_jar}")
        if not server_jar.is_file():
            raise FileNotFoundError(f"server jar not found at expected path: {server_jar}")
        return server_jar

class InstanceManager:
    def __init__(self, base_path: pathlib.Path):
        self.base_path = base_path.resolve()
        self.instances: list[Instance] = []
        self._instances_by_uuid: dict[uuid.UUID, Instance] = {}

        self.scan_instances(replace=True)

    @staticmethod
    def _normalize_uuid(value: uuid.UUID | str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            return uuid.UUID(value)
        raise TypeError("instance uuid must be a uuid.UUID or string")

    @property
    def instance_root(self) -> pathlib.Path:
        return (self.base_path / "instances").resolve()

    def get_instances(self) -> list[Instance]:
        return list(self.instances)
    
    def get_instance_overviews(self) -> list[dict]:
        return [instance.build_info() for instance in self.instances]

    def has_instance(self, instance_uuid: uuid.UUID | str) -> bool:
        normalized_uuid = self._normalize_uuid(instance_uuid)
        return normalized_uuid in self._instances_by_uuid

    def get_instance(self, instance_uuid: uuid.UUID | str) -> Instance:
        normalized_uuid = self._normalize_uuid(instance_uuid)
        instance = self._instances_by_uuid.get(normalized_uuid)
        if instance is None:
            raise KeyError(f"instance '{normalized_uuid}' is not loaded")
        return instance

    def reload_instance(self, instance_uuid: uuid.UUID | str) -> Instance:
        normalized_uuid = self._normalize_uuid(instance_uuid)
        instance = Instance(normalized_uuid, self.base_path)
        instance.save_instance_config() # ensure config is saved with any legacy conversions, if necessary
        self._instances_by_uuid[normalized_uuid] = instance
        self.instances = list(self._instances_by_uuid.values())
        return instance

    def scan_instances(self, replace: bool = True) -> list[Instance]:
        instance_root = self.instance_root
        if not instance_root.exists():
            if replace:
                self.instances = []
                self._instances_by_uuid = {}
            return self.get_instances()
        if not instance_root.is_dir() or instance_root.is_symlink():
            raise ValueError(f"unexpected instances path: {instance_root}")

        scanned_instances: dict[uuid.UUID, Instance] = {}
        for entry in instance_root.iterdir():
            if not entry.is_dir() or entry.is_symlink():
                continue

            try:
                instance_uuid = uuid.UUID(entry.name)
                instance = Instance(instance_uuid, self.base_path)
                instance.save_instance_config() # ensure config is saved with any legacy conversions, if necessary
                scanned_instances[instance_uuid] = instance
            except Exception as e:
                print(f"skipping invalid instance directory '{entry}': {e}")

        if replace:
            self._instances_by_uuid = scanned_instances
        else:
            self._instances_by_uuid.update(scanned_instances)

        self.instances = list(self._instances_by_uuid.values())
        return self.get_instances()

    def create_instance(self, server_uid: str, java_uid: str, name: str | None = None, memory: int | None = None, arguments: list[str] | None = None) -> Instance:
        instance = Instance.create_instance(
            self.base_path,
            server_uid,
            java_uid,
            name=name,
            memory=memory,
            arguments=arguments,
        )
        self._instances_by_uuid[instance.uuid] = instance
        self.instances = list(self._instances_by_uuid.values())
        return instance

    def delete_instance(self, instance_uuid: uuid.UUID | str) -> None:
        normalized_uuid = self._normalize_uuid(instance_uuid)
        existing = self._instances_by_uuid.get(normalized_uuid)
        if existing is not None and existing.running:
            raise RuntimeError(f"instance '{normalized_uuid}' is running; stop it before deletion")

        Instance.delete_instance(self.base_path, normalized_uuid)

        self._instances_by_uuid.pop(normalized_uuid, None)
        self.instances = list(self._instances_by_uuid.values())

    def start_instance(self, instance_uuid: uuid.UUID | str) -> Instance:
        instance = self.get_instance(instance_uuid)
        instance.start()
        return instance

    def stop_instance(self, instance_uuid: uuid.UUID | str) -> Instance:
        instance = self.get_instance(instance_uuid)
        instance.stop() # see earlier notes about non-blocking instance stopping
        return instance

    def restart_instance(self, instance_uuid: uuid.UUID | str) -> Instance:
        instance = self.get_instance(instance_uuid)
        if instance.running:
            instance.stop() # see earlier notes about non-blocking instance stopping
        instance.start()
        return instance

    def stop_all(self) -> list[tuple[uuid.UUID, Exception]]:
        errors: list[tuple[uuid.UUID, Exception]] = []
        for instance in list(self.instances):
            if not instance.running:
                continue

            try:
                instance.stop()
            except Exception as e:
                errors.append((instance.uuid, e))

        return errors
