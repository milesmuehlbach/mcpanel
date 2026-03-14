from fastapi import APIRouter

api = APIRouter()

V1 = APIRouter(prefix="/v1")

@V1.get("/hello")
async def hello():
    return {"message": "hello world"}

api.include_router(V1)