import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import select, func
from app.models.profile import Profile

load_dotenv()

async def check():
    url = os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(select(func.count()).select_from(Profile))
            print(f"Profiles in DB: {res.scalar()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
