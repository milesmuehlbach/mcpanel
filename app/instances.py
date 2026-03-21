import datetime
import json
import pathlib
import platform
import psutil
import shutil
import subprocess
import threading
import uuid

from app.api import get_installed_components

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
        self.base_path = base_path
        self.path = base_path / "instances" / str(uuid)
        self.json = self.path / "instance.json"

        self.set_defaults()
        self.load_instance_config()

        self.process = None
        self.running = False
        self.bridge_thread = None

    def set_defaults(self):
        now = _utcnow()

        self.name = f"My Instance {self.uuid.hex[:8]}"
        self.jar = None
        self.java = None
        self.memory = DEFAULT_MB
        self.arguments = list(DEFAULT_ARGUMENTS)

        self.created_at = now
        self.updated_at = now

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
                        self.name = name

                    jar = config.get("jar")
                    if jar is None or isinstance(jar, str):
                        self.jar = jar

                    java = config.get("java")
                    if java is None or isinstance(java, str):
                        self.java = java

                    memory = config.get("memory")
                    if isinstance(memory, int) and not isinstance(memory, bool) and memory > 0:
                        self.memory = memory

                    arguments = config.get("arguments")
                    if isinstance(arguments, list) and all(isinstance(argument, str) for argument in arguments):
                        self.arguments = list(arguments)

                    created_at = config.get("created_at")
                    if _is_valid_timestamp(created_at):
                        self.created_at = _to_datetime(created_at)

                    updated_at = config.get("updated_at")
                    if _is_valid_timestamp(updated_at):
                        self.updated_at = _to_datetime(updated_at)
                case _:
                    return

    def save_instance_config(self):
        self.updated_at = _utcnow()

        config = {
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

        self.path.mkdir(parents=True, exist_ok=True)
        self.json.write_text(json.dumps(config, indent=4), encoding="utf-8")
    
    @staticmethod
    def create_instance(base_path: pathlib.Path, server_uid: str, java_uid: str, name: str | None = None, memory: int | None = None, arguments: list[str] | None = None) -> Instance:
        installed_components = get_installed_components()
        if server_uid not in installed_components.keys():
            raise ValueError(f"specified server component with uid '{server_uid}' is not installed")
        if java_uid not in installed_components.keys():
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
        pass # TODO: flippin nuke the instance folder

    def start(self):
        if self.running:
            raise RuntimeError(f"instance {self.uuid} is already running")

        java_executable = self._get_java_executable()

        command = [
            str(java_executable),
            f"-Xmx{self.memory}M",
            f"-Xms{self.memory}M",
            *self.arguments,
            "-jar",
            str(self.jar),
            *DEFAULT_PARAMTERS
        ]

        # TODO: automatically restart server on crash? make it a user option?
        self.process = subprocess.Popen(
            command,
            cwd=self.path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.running = True

        self.bridge_thread = threading.Thread(target=self._bridge_runner, daemon=True)
        self.bridge_thread.start()

    def stop(self):
        if self.process and self.running:
            self.sendline("stop")
            self.process.wait()
            self.running = False
        
    def sendline(self, cmd):
        if self.process and self.running:
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush() 
        else:
            raise RuntimeError(f"instance {self.uuid} is not running")
    
    def _bridge_runner(self):
        while self.running and self.process:
            lineout = self.process.stdout.readline()
            if not lineout:
                break
            
            print(f"[SERVER] [STDOUT] {lineout.strip()}")
            
        self.running = False

    def _get_java_executable(self) -> pathlib.Path:
        java_executable = pathlib.Path(self.base_path, *self.java.split(":"), "bin", "javaw.exe" if platform.system() == "Windows" else "java") # TODO: super vunerable! validate java uid, either here or higher up the chain
        if not java_executable.is_file():
            raise FileNotFoundError(f"java executable not found at expected path: {java_executable}")
        return java_executable
    
    def _get_server_jar(self) -> pathlib.Path:
        server_jar = self.base_path / "jar" / self.jar # TODO: vunerable, validate jar name and path
        if not server_jar.is_file():
            raise FileNotFoundError(f"server jar not found at expected path: {server_jar}")
        return server_jar

class InstanceManager:
    def __init__(self, base_path: pathlib.Path):
        self.base_path = base_path
        self.instances: list[Instance] = []
