import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.models.user import User
from app.core.dependencies import require_admin, require_analyst, get_current_user
from app.db.session import engine
from app.db.base import Base
from unittest.mock import patch, AsyncMock

@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    # Clear overrides at the start of each test for isolation
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Mock Users
MOCK_ADMIN = User(id="admin-id", username="admin", role="admin", is_active=True)
MOCK_ANALYST = User(id="analyst-id", username="analyst", role="analyst", is_active=True)

# Helper for headers
HEADERS = {"X-API-Version": "1"}

@pytest.mark.asyncio
async def test_api_version_header_required():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # No header
        response = await ac.get("/api/profiles")
        assert response.status_code == 400
        # Check standard error format
        assert response.json()["status"] == "error"
        assert "API version header required" in response.json()["message"]

@pytest.mark.asyncio
async def test_rbac_analyst_cannot_create():
    # Override auth to return an analyst
    app.dependency_overrides[get_current_user] = lambda: MOCK_ANALYST
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/profiles", json={"name": "test"}, headers=HEADERS)
        assert response.status_code == 403
        assert "Admin access required" in response.json()["message"]

@pytest.mark.asyncio
async def test_rbac_admin_can_create():
    # Override auth to return an admin
    app.dependency_overrides[get_current_user] = lambda: MOCK_ADMIN
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Mocking external API with full data to satisfy NOT NULL constraints
        with patch("app.api.v1.endpoints.profiles.fetch_classification_data", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "gender": "male",
                "gender_probability": 0.95,
                "age": 25,
                "age_group": "adult",
                "country_id": "US",
                "country_name": "United States",
                "country_probability": 0.90
            }
            response = await ac.post("/api/profiles", json={"name": "admin-test"}, headers=HEADERS)
            assert response.status_code == 201

@pytest.mark.asyncio
async def test_rate_limiting_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Send 10 requests (the limit)
        for _ in range(10):
            await ac.get("/auth/github")
        
        # 11th should be rate limited
        response = await ac.get("/auth/github")
        assert response.status_code == 429
        assert response.json()["status"] == "error"
        assert "Too many requests" in response.json()["message"]

@pytest.mark.asyncio
async def test_unauthenticated_access():
    # No auth override here, so it should default to 401
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/profiles", headers=HEADERS)
        assert response.status_code == 401
