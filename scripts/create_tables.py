"""
scripts/create_tables.py
─────────────────────────
Run this ONCE to create the new Stage 3 tables in your Neon PostgreSQL database
before deploying. Safe to re-run — uses CREATE TABLE IF NOT EXISTS.

Usage:
    python scripts/create_tables.py
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine
from app.db.base import Base  # imports all models via side-effect


async def create_tables():
    url = os.getenv("DATABASE_URL", "")
    url = url.strip().strip('"').strip("'")

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if not url:
        print("ERROR: DATABASE_URL is not set.")
        return

    connect_args = {}
    if "postgresql+asyncpg" in url:
        connect_args = {"ssl": "require", "statement_cache_size": 0}

    engine = create_async_engine(url, connect_args=connect_args)

    print("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Done! All tables created (or already exist).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_tables())
