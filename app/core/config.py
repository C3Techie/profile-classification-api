import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Profile Classification API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    @property
    def DATABASE_URL(self) -> str:
        if os.getenv("TESTING") == "True":
            return "sqlite+aiosqlite:///./test_profiles.db"
        
        url = os.getenv("DATABASE_URL", "")
        if not url:
            url = "sqlite+aiosqlite:///./profiles.db"
            
        # Sanitize common Vercel pasting errors (spaces or quotes)
        url = url.strip().strip('"').strip("'")
            
        # Ensure we use the asyncpg driver
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    # External API Base URLs
    GENDERIZE_URL: str = "https://api.genderize.io"
    AGIFY_URL: str = "https://api.agify.io"
    NATIONALIZE_URL: str = "https://api.nationalize.io"

settings = Settings()
