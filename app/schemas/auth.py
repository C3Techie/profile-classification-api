from datetime import datetime
from pydantic import BaseModel
from typing import Optional


# ── Auth Schemas ───────────────────────────────────────────────────────────────

class CLICallbackBody(BaseModel):
    """Body sent by the CLI after capturing the GitHub callback locally."""
    code: str
    code_verifier: Optional[str] = None
    redirect_uri: str
    state: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None  # CLI sends this; web portal uses cookie


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 180
    role: Optional[str] = None


class UserOut(BaseModel):
    id: str
    github_id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
