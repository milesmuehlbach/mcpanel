from fastapi import FastAPI, HTTPException as FastAPIHTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api

app = FastAPI(title="mcpanel")

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

app.mount("/_app", StaticFiles(directory="build/_app"))
# app.mount("/assets", StaticFiles(directory="build/assets")) // miles, 3/20/26, this was causing issues with python and you were locked in on the fort so I commented this out so I could test my ui.

@app.get("/")
async def _root():
    return FileResponse("build/index.html")

@app.get("/favicon.ico")
async def _favicon():
    return FileResponse("build/assets/favicon.ico")