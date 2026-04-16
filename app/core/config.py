import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Profile Classification API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./profiles.db")
    
    # External API Base URLs
    GENDERIZE_URL: str = "https://api.genderize.io"
    AGIFY_URL: str = "https://api.agify.io"
    NATIONALIZE_URL: str = "https://api.nationalize.io"

settings = Settings()
