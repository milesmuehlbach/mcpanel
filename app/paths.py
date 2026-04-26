import os
from pathlib import Path

WORKING_PATH_ENV = "MCPANEL_PATH"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_BUILD_DIR = PROJECT_ROOT / "build"
FRONTEND_APP_DIR = FRONTEND_BUILD_DIR / "_app"
FRONTEND_ASSETS_DIR = FRONTEND_BUILD_DIR / "assets"
FRONTEND_INDEX_FILE = FRONTEND_BUILD_DIR / "index.html"
FRONTEND_FAVICON_FILE = FRONTEND_ASSETS_DIR / "favicon.ico"


def get_workdir() -> Path:
    return Path(os.environ.get(WORKING_PATH_ENV, "./minecraft")).resolve()
