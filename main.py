import argparse
import os
import pathlib
import uvicorn

from app.api import WORKING_PATH_ENV as APP_PATH_ENV

def app_factory():
    from app.server import app
    return app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comprehensive Minecraft server management panel")
    parser.add_argument(
        "--path",
        "-p",
        type=pathlib.Path,
        default=pathlib.Path("./minecraft"),
        help="path to the working directory (default: ./minecraft)",
    )
    parser.add_argument(
        "--dev",
        type=bool,
        default=False,
        help="run in development mode with hot reloading (default: False)",
    )
    args = parser.parse_args()

    os.environ[APP_PATH_ENV] = str(args.path.resolve())

    uvicorn.run("main:app_factory", host="0.0.0.0", port=8080, workers=1, reload=args.dev, factory=True) # WORKERS HAS TO BE 1 BC I'M A FUCKING DUMBASS
