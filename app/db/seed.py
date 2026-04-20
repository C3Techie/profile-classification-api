import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import List

from app.models.profile import Profile
from app.db.session import AsyncSessionLocal
from app.core import utils

async def seed_data(file_path: str = "seed_profiles.json"):
    """
    Seeds the database with profiles from a JSON file using optimized bulk inserts.
    """
    # Ensure tables are created
    from app.db.session import engine as app_engine
    from app.db.base import Base
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    import os
    
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./profiles.db")
    
    # Disable statement caching for poolers (Neon) if applicable
    seed_engine = create_async_engine(
        db_url,
        connect_args={"ssl": "require", "statement_cache_size": 0} if "postgresql" in db_url else {}
    )
    seed_session = async_sessionmaker(seed_engine, expire_on_commit=False, class_=AsyncSession)

    async with seed_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    profiles_data = data.get("profiles", [])
    if not profiles_data:
        print("No profiles found in seed data.")
        return

    async with seed_session() as session:
        # Optimization: Fetch all existing names at once
        print("Checking for existing records...")
        stmt = select(Profile.name)
        result = await session.execute(stmt)
        existing_names = set(result.scalars().all())
        
        new_profiles = []
        for p in profiles_data:
            name_lower = p["name"].lower()
            if name_lower in existing_names:
                continue
            
            new_profile = Profile(
                id=utils.generate_uuidv7(),
                name=name_lower,
                gender=p["gender"],
                gender_probability=p["gender_probability"],
                age=p["age"],
                age_group=p["age_group"],
                country_id=p["country_id"],
                country_name=p["country_name"],
                country_probability=p["country_probability"],
                created_at=datetime.now(timezone.utc)
            )
            new_profiles.append(new_profile)
            # Prevent existing_names from being stale if there are duplicates in the JSON itself
            existing_names.add(name_lower)

        if not new_profiles:
            print("No new profiles to add.")
            return

        print(f"Adding {len(new_profiles)} new profiles...")
        # Bulk insert
        session.add_all(new_profiles)
        await session.commit()
        print("Seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_data())
