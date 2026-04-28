from pydantic import BaseModel
from typing import Optional


# ── Auth Schemas ───────────────────────────────────────────────────────────────

class CLICallbackBody(BaseModel):
    """Body sent by the CLI after capturing the GitHub callback locally."""
    code: str
    code_verifier: Optional[str] = None
    redirect_uri: str
    state: str


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None  # CLI sends this; web portal uses cookie


class TokenResponse(BaseModel):
    status: str = "success"
    access_token: str
    refresh_token: str


class UserOut(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
