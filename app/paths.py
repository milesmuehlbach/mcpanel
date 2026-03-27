import os
from pathlib import Path

WORKING_PATH_ENV = "MCPANEL_PATH"

def get_workdir() -> Path:
    return Path(os.environ.get(WORKING_PATH_ENV, "./minecraft")).resolve()