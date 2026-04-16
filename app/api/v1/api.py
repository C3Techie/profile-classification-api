from fastapi import APIRouter
from app.api.v1.endpoints import profiles

api_router = APIRouter()
api_router.include_router(profiles.router, tags=["profiles"])
