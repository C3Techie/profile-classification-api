from fastapi import APIRouter
from app.api.v1.endpoints import profiles, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles.router, tags=["profiles"])
