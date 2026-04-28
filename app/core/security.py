import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.core.config import settings


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str, role: str) -> str:
    """Create a signed JWT access token (3-minute expiry)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token. Returns payload or None."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def create_state_token(flow: str) -> str:
    """
    Create a short-lived signed JWT used as the OAuth `state` parameter
    for the web browser flow. Prevents CSRF.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    payload = {
        "flow": flow,
        "nonce": secrets.token_hex(8),
        "exp": expire,
        "type": "oauth_state",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_state_token(state: str, expected_flow: str) -> bool:
    """Validate the OAuth state token."""
    try:
        payload = jwt.decode(
            state, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return (
            payload.get("type") == "oauth_state"
            and payload.get("flow") == expected_flow
        )
    except JWTError:
        return False


# ── Refresh Token ──────────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a cryptographically secure raw refresh token (stored hashed)."""
    return secrets.token_hex(32)


def hash_token(token: str) -> str:
    """SHA-256 hash a token string for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()
