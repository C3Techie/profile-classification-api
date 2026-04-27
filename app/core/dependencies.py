from typing import Optional
from fastapi import Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import verify_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


# ── API Version Header ─────────────────────────────────────────────────────────

async def require_api_version(x_api_version: Optional[str] = Header(None, alias="X-API-Version")):
    """Reject requests that don't include X-API-Version: 1."""
    if x_api_version != "1":
        raise HTTPException(
            status_code=400,
            detail="API version header required"
        )


# ── Auth Dependencies ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate JWT Bearer token and return the authenticated User.
    Raises 401 if missing/invalid, 403 if user is inactive.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require the authenticated user to have the 'admin' role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


async def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    """Allow any authenticated user (admin or analyst)."""
    return current_user
