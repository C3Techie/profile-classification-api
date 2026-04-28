import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_state_token,
    generate_refresh_token,
    hash_token,
    verify_access_token,
    verify_state_token,
)
from app.core import utils
from app.db.session import get_db
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import CLICallbackBody, RefreshRequest, TokenResponse, UserOut

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _exchange_github_code(
    code: str,
    redirect_uri: str,
    code_verifier: Optional[str] = None,
) -> str:
    """Exchange a GitHub OAuth code for an access token."""
    payload = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json=payload,
            headers={"Accept": "application/json"},
        )
    data = resp.json()
    if "access_token" not in data:
        raise HTTPException(status_code=400, detail="GitHub OAuth token exchange failed")
    return data["access_token"]


async def _get_github_user(github_token: str) -> dict:
    """Fetch the authenticated user's profile from GitHub."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
    return resp.json()


async def _get_or_create_user(db: AsyncSession, gh: dict) -> User:
    """Find an existing user by github_id or create a new analyst account."""
    github_id = str(gh.get("id", ""))
    stmt = select(User).where(User.github_id == github_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if user:
        # Refresh mutable fields
        user.username = gh.get("login", user.username)
        user.email = gh.get("email") or user.email
        user.avatar_url = gh.get("avatar_url") or user.avatar_url
        user.last_login_at = now
        await db.commit()
        await db.refresh(user)
        return user

    new_user = User(
        id=utils.generate_uuidv7(),
        github_id=github_id,
        username=gh.get("login", ""),
        email=gh.get("email"),
        avatar_url=gh.get("avatar_url"),
        role="analyst",         # default role
        is_active=True,
        last_login_at=now,
        created_at=now,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def _store_refresh_token(db: AsyncSession, user_id: str) -> str:
    """Generate, hash, and persist a refresh token. Returns the raw token."""
    raw = generate_refresh_token()
    token_hash = hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    rt = RefreshToken(
        id=utils.generate_uuidv7(),
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(rt)
    await db.commit()
    return raw


async def _revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    """Mark a refresh token as revoked."""
    token_hash = hash_token(raw_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        await db.commit()


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/github")
async def github_login(
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    state: Optional[str] = None,
    redirect_uri: Optional[str] = None,
):
    """
    Redirect to GitHub OAuth.

    CLI flow  : pass code_challenge, code_challenge_method, state, redirect_uri
    Web flow  : no parameters — backend generates a signed state
    """
    if code_challenge:
        # ── CLI / PKCE flow ────────────────────────────────────────────────────
        if not state:
            raise HTTPException(status_code=400, detail="state is required for PKCE flow")
        url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={settings.GITHUB_CLIENT_ID}"
            f"&scope=user:email"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method={code_challenge_method or 'S256'}"
        )
        if redirect_uri:
            url += f"&redirect_uri={redirect_uri}"
        return RedirectResponse(url)

    # ── Web / browser flow ─────────────────────────────────────────────────────
    signed_state = create_state_token("web")
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=user:email"
        f"&state={signed_state}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
    )
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_web_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """
    GitHub redirects here for the **web portal** flow.
    Validates state, exchanges code, creates/updates user,
    sets HTTP-only cookies, then redirects to the portal dashboard.
    """
    if not verify_state_token(state, "web"):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    gh_token = await _exchange_github_code(code, settings.GITHUB_REDIRECT_URI)
    gh_user = await _get_github_user(gh_token)
    user = await _get_or_create_user(db, gh_user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = create_access_token(user.id, user.role)
    refresh_token = await _store_refresh_token(db, user.id)

    response = RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard", status_code=302)
    response.set_cookie(
        "insighta_access",
        access_token,
        httponly=True,
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.FRONTEND_URL.startswith("https"),
    )
    response.set_cookie(
        "insighta_refresh",
        refresh_token,
        httponly=True,
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.FRONTEND_URL.startswith("https"),
    )
    return response


@router.post("/github/callback")
async def github_cli_callback(
    body: CLICallbackBody,
    db: AsyncSession = Depends(get_db),
):
    """
    The **CLI** calls this after capturing the GitHub redirect on localhost.
    Accepts code + code_verifier, exchanges with GitHub (PKCE), returns tokens.
    """
    gh_token = await _exchange_github_code(
        code=body.code,
        redirect_uri=body.redirect_uri,
        code_verifier=body.code_verifier,
    )
    gh_user = await _get_github_user(gh_token)
    user = await _get_or_create_user(db, gh_user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = create_access_token(user.id, user.role)
    refresh_token = await _store_refresh_token(db, user.id)

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "username": user.username,
        "role": user.role,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    body: RefreshRequest,
    insighta_refresh: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Issue a new access + refresh token pair.
    Accepts the refresh token from:
      - JSON body  (CLI)
      - HTTP-only cookie  (web portal)
    The old refresh token is immediately revoked (rotation).
    """
    raw_token = body.refresh_token or insighta_refresh
    if not raw_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(stmt)
    rt = result.scalar_one_or_none()

    if not rt or rt.revoked or rt.expires_at < now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Rotate — revoke old token immediately
    rt.revoked = True
    await db.commit()

    # Fetch user
    user_stmt = select(User).where(User.id == rt.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    new_access = create_access_token(user.id, user.role)
    new_refresh = await _store_refresh_token(db, user.id)

    return TokenResponse(
        status="success",
        access_token=new_access,
        refresh_token=new_refresh,
    )


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    insighta_refresh: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Invalidate the refresh token server-side.
    Clears the HTTP-only cookie for web portal sessions.
    """
    raw_token = body.refresh_token or insighta_refresh
    if raw_token:
        await _revoke_refresh_token(db, raw_token)

    response = JSONResponse(content={"status": "success", "message": "Logged out"})
    response.delete_cookie("insighta_access")
    response.delete_cookie("insighta_refresh")
    return response


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
