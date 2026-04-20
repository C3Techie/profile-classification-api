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
        
        url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./profiles.db")
        # Ensure we use the asyncpg driver, even if the user pasted a standard postgresql URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    
    # External API Base URLs
    GENDERIZE_URL: str = "https://api.genderize.io"
    AGIFY_URL: str = "https://api.agify.io"
    NATIONALIZE_URL: str = "https://api.nationalize.io"

settings = Settings()
