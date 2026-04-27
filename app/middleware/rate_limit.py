from datetime import datetime, timedelta, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import verify_access_token
from app.db.session import AsyncSessionLocal
from app.models.rate_limit import RateLimitEntry


async def _check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> bool:
    """
    DB-backed sliding-window rate limiter.
    Returns True if within limit, False if exceeded.
    Uses a new session per check — safe for Vercel serverless.
    """
    now = datetime.now(timezone.utc)
    window_start_threshold = now - timedelta(seconds=window_seconds)

    async with AsyncSessionLocal() as db:
        stmt = select(RateLimitEntry).where(RateLimitEntry.key == key)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry is None:
            # First request in this window
            db.add(RateLimitEntry(key=key, window_start=now, count=1))
            await db.commit()
            return True

        if entry.window_start < window_start_threshold:
            # Window has expired — reset
            entry.window_start = now
            entry.count = 1
            await db.commit()
            return True

        if entry.count >= limit:
            return False  # Over the limit

        entry.count += 1
        await db.commit()
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces:
      - /auth/*  → 10 requests/minute  (keyed by client IP)
      - all else → 60 requests/minute  (keyed by user ID if authenticated, else IP)
    Returns 429 Too Many Requests when exceeded.
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        if path.startswith("/auth"):
            limit = settings.AUTH_RATE_LIMIT
            key = f"auth:ip:{client_ip}"
        else:
            limit = settings.API_RATE_LIMIT
            # Try to identify by user ID for a per-user limit
            identifier = client_ip
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                raw_token = auth_header[7:]
                payload = verify_access_token(raw_token)
                if payload and payload.get("sub"):
                    identifier = payload["sub"]
            key = f"api:user:{identifier}"

        allowed = await _check_rate_limit(key, limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"status": "error", "message": "Too many requests"},
            )

        return await call_next(request)
