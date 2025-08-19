from fastapi import APIRouter

from src.app.api.api_v1.endpoints import auth, users, files

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["onboard"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(files.router, prefix="/files", tags=["files"])