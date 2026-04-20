import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.base import Base
from app.models.profile import Profile
from app.services.classification import ExternalAPIError

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip DB initialization on startup in Serverless environments (Vercel)
    # The database is already created and seeded via seed.py.
    # Connecting to DB during cold start can cause FUNCTION_INVOCATION_FAILED.
    yield
    # Shutdown logic if needed

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
@app.exception_handler(ExternalAPIError)
async def external_api_exception_handler(request: Request, exc: ExternalAPIError):
    return JSONResponse(
        status_code=502,
        content={"status": "error", "message": f"{exc.api_name} returned an invalid response"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    
    # Check if it's a 'field required' error (Missing parameter)
    # Pydantic v2 returns 'string_too_short' for min_length violations (empty strings)
    is_missing = any(
        err.get("type") == "missing" or 
        "missing" in err.get("type", "") or 
        err.get("type") == "string_too_short" 
        for err in errors
    )
    if is_missing:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty parameter"}
        )

    # Check if the error is in the query parameters
    is_query_error = any(err.get("loc", [])[0] == "query" for err in errors)
    message = "Invalid query parameters" if is_query_error else "Invalid parameter type"
    
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": message}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the real exception internally here if needed
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Server failure"}
    )

# Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"status": "success", "message": f"{settings.PROJECT_NAME} is active"}
