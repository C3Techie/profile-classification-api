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
        "pool_size": 5,
        "max_overflow": 0,
        "pool_recycle": 10,
        "pool_pre_ping": True,
        "connect_args": {
            "ssl": "require",
            "statement_cache_size": 0,
            "timeout": 30
        }
    })

# Use NullPool for testing to avoid connection interference
if os.getenv("TESTING") == "True":
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
