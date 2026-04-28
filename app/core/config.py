import os
import secrets
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Insighta Labs+ API"
    VERSION: str = "3.0.0"
    API_V1_STR: str = "/api"

    @property
    def DATABASE_URL(self) -> str:
        if os.getenv("TESTING") == "True":
            return "sqlite+aiosqlite:///./test_profiles.db"

        url = os.getenv("DATABASE_URL", "")
        if not url:
            url = "sqlite+aiosqlite:///./profiles.db"

        url = url.strip().strip('"').strip("'")

        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # External Classification APIs
    GENDERIZE_URL: str = "https://api.genderize.io"
    AGIFY_URL: str = "https://api.agify.io"
    NATIONALIZE_URL: str = "https://api.nationalize.io"

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    # Backend callback URL for the web portal flow
    GITHUB_REDIRECT_URI: str = os.getenv(
        "GITHUB_REDIRECT_URI",
        "http://localhost:8000/auth/github/callback"
    )

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 5

    # Web portal origin (for CORS + post-login redirect)
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Rate limits
    AUTH_RATE_LIMIT: int = 100    # requests per minute for /auth/*
    API_RATE_LIMIT: int = 500     # requests per minute for everything else

settings = Settings()
