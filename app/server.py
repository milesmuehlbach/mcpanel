from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import api

app = FastAPI(title="mcpanel")

@app.exception_handler(Exception)
async def exception_handler(request: Request, exception: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "an error occurred?"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exception: HTTPException):
    return JSONResponse(
        status_code=exception.status_code,
        content={"message": exception.detail},
        headers=exception.headers,
    )

app.include_router(api, prefix="/api")

app.mount("/_app", StaticFiles(directory="build/_app"))
app.mount("/assets", StaticFiles(directory="build/assets"))

@app.get("/")
async def _root():
    return FileResponse("build/landing.html")

@app.get("/app")
async def _app():
    return FileResponse("build/index.html")

@app.get("/favicon.ico")
async def _favicon():
    return FileResponse("build/assets/favicon.ico")