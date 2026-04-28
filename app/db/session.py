import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Use NullPool for tests to prevent asyncpg "another operation in progress" errors
engine_kwargs = {"pool_pre_ping": True}

# If using asyncpg with a remote server (like Neon), we handle SSL via connect_args
# and disable the statement cache. We also use NullPool to ensure connections
# are fresh and not killed by the remote pooler.
if settings.DATABASE_URL.startswith("postgresql+asyncpg"):
    engine_kwargs.update({
        "poolclass": NullPool,
        "connect_args": {
            "ssl": "require",
            "statement_cache_size": 0,
            "timeout": 30
        }
    })

# Use NullPool for testing to avoid connection interference
database_url = settings.DATABASE_URL
if os.getenv("TESTING") == "True":
    engine_kwargs["poolclass"] = NullPool
    database_url = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
