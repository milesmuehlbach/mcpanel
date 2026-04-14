from pathlib import Path

from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api

app = FastAPI(title="mcpanel")

BUILD_DIR = Path("build")
INDEX_FILE = BUILD_DIR / "index.html"
FAVICON_FILE = BUILD_DIR / "assets" / "favicon.ico"


@app.exception_handler(Exception)
async def exception_handler(request: Request, exception: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "an error occurred?"},
    )


@app.exception_handler(StarletteHTTPException)
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exception: Exception):
    status_code = getattr(exception, "status_code", 500)
    detail = getattr(exception, "detail", "an error occurred?")
    headers = getattr(exception, "headers", None)

    return JSONResponse(
        status_code=status_code,
        content={"message": detail},
        headers=headers,
    )


app.include_router(api, prefix="/api")

app.mount("/_app", StaticFiles(directory=BUILD_DIR / "_app"))
app.mount("/assets", StaticFiles(directory=BUILD_DIR / "assets"))


@app.get("/")
async def _root():
    return FileResponse(INDEX_FILE)


@app.get("/favicon.ico")
async def _favicon():
    if FAVICON_FILE.exists():
        return FileResponse(FAVICON_FILE)

    return Response(status_code=204)


@app.get("/{path:path}")
async def _spa(path: str):
    return FileResponse(INDEX_FILE)
