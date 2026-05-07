import os
os.environ["TESTING"] = "True"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import engine
from app.db.base import Base
from app.core.dependencies import get_current_user, require_admin, require_analyst
from app.models.user import User
from app.core.cache import query_cache

# Mock Admin
MOCK_ADMIN = User(id="admin-id", username="admin", role="admin", is_active=True)

# Headers
HEADERS = {"X-API-Version": "1"}

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_stage4():
    # Setup auth override
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    app.dependency_overrides[require_admin] = lambda: MOCK_ADMIN
    app.dependency_overrides[require_analyst] = lambda: MOCK_ADMIN
    
    # Clear cache
    query_cache.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_aggregation_stats():
    """Verify that the aggregation endpoint returns the correct summary."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Seed some data
        profiles = [
            {"name": "Alice", "gender": "female", "age": 25, "age_group": "adult", "country_id": "NG", "country_name": "Nigeria", "gender_probability": 1.0, "country_probability": 1.0},
            {"name": "Bob", "gender": "male", "age": 30, "age_group": "adult", "country_id": "NG", "country_name": "Nigeria", "gender_probability": 1.0, "country_probability": 1.0},
            {"name": "Charlie", "gender": "male", "age": 15, "age_group": "teenager", "country_id": "US", "country_name": "United States", "gender_probability": 1.0, "country_probability": 1.0},
        ]
        
        # We need to use the DB session directly or a bypass for seed since the API is rule-based
        from app.db.session import AsyncSessionLocal
        from app.models.profile import Profile
        from app.core.utils import generate_uuidv7
        from datetime import datetime, timezone
        
        async with AsyncSessionLocal() as db:
            for p in profiles:
                db.add(Profile(id=generate_uuidv7(), created_at=datetime.now(timezone.utc), **p))
            await db.commit()

        # 2. Call stats
        response = await ac.get("/api/v1/profiles/stats", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_profiles"] == 3
        assert data["by_gender"]["female"] == 1
        assert data["by_gender"]["male"] == 2
        assert data["by_age_group"]["adult"] == 2
        assert data["top_countries"][0]["country_id"] == "NG"
        assert data["top_countries"][0]["count"] == 2

@pytest.mark.asyncio
async def test_query_normalization_caching():
    """Verify that normalized filters hit the cache regardless of param order."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. First call - should populate cache
        await ac.get("/api/v1/profiles?gender=male&country_id=NG", headers=HEADERS)
        
        # Check cache manually
        from app.core.parser import normalize_filters
        key = normalize_filters({"gender": "male", "country_id": "NG", "sort_by": "created_at", "order": "desc", "page": 1, "limit": 10})
        assert query_cache.get(key) is not None
        
        # 2. Second call with reordered params - should hit cache
        # We can't easily "prove" it hit cache from the response alone without a spy,
        # but we can verify the normalization logic in isolation or check cache keys.
        reordered_key = normalize_filters({"country_id": "NG", "gender": "male", "sort_by": "created_at", "order": "desc", "page": 1, "limit": 10})
        assert key == reordered_key

@pytest.mark.asyncio
async def test_csv_ingestion_resilience():
    """Verify that CSV ingestion handles duplicates and returns the correct report."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a "duplicate" entry first
        from app.db.session import AsyncSessionLocal
        from app.models.profile import Profile
        from app.core.utils import generate_uuidv7
        from datetime import datetime, timezone
        
        async with AsyncSessionLocal() as db:
            db.add(Profile(
                id=generate_uuidv7(), 
                name="duplicate_user", 
                gender="male", 
                age=20, 
                age_group="adult", 
                country_id="NG", 
                country_name="Nigeria",
                gender_probability=1.0,
                country_probability=1.0,
                created_at=datetime.now(timezone.utc)
            ))
            await db.commit()

        # 2. Prepare CSV with: 1 valid, 1 duplicate, 1 invalid age, 1 missing field
        csv_content = (
            "name,gender,age,country_id,gender_probability,country_probability\n"
            "new_user,female,25,US,0.9,0.9\n"      # Valid
            "duplicate_user,male,20,NG,1.0,1.0\n" # Duplicate (should be skipped)
            "bad_age,female,-5,GB,1.0,1.0\n"      # Invalid age
            ",female,30,CA,1.0,1.0\n"             # Missing name
        )
        
        files = {"file": ("test.csv", csv_content, "text/csv")}
        response = await ac.post("/api/v1/profiles/upload", files=files, headers=HEADERS)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 4
        assert data["inserted"] == 1
        assert data["skipped"] == 3
        assert data["reasons"]["duplicate_name"] == 1
        assert data["reasons"]["invalid_age"] == 1
        assert data["reasons"]["missing_fields"] == 1
