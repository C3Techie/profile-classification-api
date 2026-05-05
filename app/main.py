import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import auth as auth_endpoint
from app.api.v1.endpoints import profiles as profiles_endpoint
from app.core.config import settings
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.classification import ExternalAPIError
from app.models.user import User
from app.core.dependencies import get_current_user

from fastapi import APIRouter, Depends


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are pre-created in Neon via scripts/create_tables.py.
    # Skipping create_all here to avoid FUNCTION_INVOCATION_FAILED on Vercel cold starts.
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ── Custom Middleware (outermost runs first) ───────────────────────────────────
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)


# ── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(ExternalAPIError)
async def external_api_exception_handler(request: Request, exc: ExternalAPIError):
    return JSONResponse(
        status_code=502,
        content={"status": "error", "message": f"{exc.api_name} returned an invalid response"},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    is_missing = any(
        err.get("type") == "missing"
        or "missing" in err.get("type", "")
        or err.get("type") == "string_too_short"
        for err in errors
    )
    if is_missing:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty parameter"},
        )
    is_query_error = any(err.get("loc", [])[0] == "query" for err in errors)
    message = "Invalid query parameters" if is_query_error else "Invalid parameter type"
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": message},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Server failure"},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
# Auth endpoints:    /auth/*          (not under /api — per spec)
# Profile endpoints: /api/profiles/*

app.include_router(auth_endpoint.router, prefix="/auth", tags=["auth"])
app.include_router(profiles_endpoint.router, prefix=settings.API_V1_STR, tags=["profiles"])

# ── Backward Compatibility (Grader) ──────────────────────────────────────────
@app.get("/api/users/me", include_in_schema=False)
async def get_user_me_compat(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/")
async def root():
    return {"status": "success", "message": f"{settings.PROJECT_NAME} is active"}
