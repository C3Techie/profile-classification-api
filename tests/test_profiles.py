import os
os.environ["TESTING"] = "True"

import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import engine
from app.db.base import Base
from app.core.dependencies import require_admin, require_analyst, get_current_user
from app.models.user import User

# Mock User for auth bypass
MOCK_USER = User(id="test-admin-id", username="testadmin", role="admin", is_active=True)

# Dependency overrides to bypass auth in tests
async def override_auth():
    return MOCK_USER

app.dependency_overrides[get_current_user] = override_auth
app.dependency_overrides[require_admin] = override_auth
app.dependency_overrides[require_analyst] = override_auth

@pytest.fixture(autouse=True)
def mock_external_apis():
    with patch("app.api.v1.endpoints.profiles.fetch_classification_data", new_callable=AsyncMock) as mock:
        mock.return_value = {
            "gender": "female",
            "gender_probability": 0.99,
            "age": 30,
            "age_group": "adult",
            "country_id": "US",
            "country_name": "United States",
            "country_probability": 0.85
        }
        yield mock

@pytest.mark.asyncio
@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Helper for common headers
HEADERS = {"X-API-Version": "1"}

@pytest.mark.asyncio
async def test_create_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test valid creation
        response = await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "ella"
        assert "id" in data["data"]
        
        # Test idempotency (same name)
        response2 = await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2.get("message") == "Profile already exists"

@pytest.mark.asyncio
async def test_get_profiles_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a few
        await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        await ac.post("/api/profiles", json={"name": "john"}, headers=HEADERS)
        
        response = await ac.get("/api/profiles?page=1&limit=1", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 1
        assert data["total"] == 2
        assert data["total_pages"] == 2
        assert "links" in data
        assert len(data["data"]) == 1

@pytest.mark.asyncio
async def test_nlq_search():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create sample
        await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        
        # Test search
        response = await ac.get("/api/profiles/search?q=females from united states", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["data"][0]["gender"] == "female"
        
        # Test invalid search
        response2 = await ac.get("/api/profiles/search?q=unknown query", headers=HEADERS)
        assert response2.status_code == 400
        assert response2.json()["status"] == "error"

@pytest.mark.asyncio
async def test_get_single_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create one first
        await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        
        # Get all first to find an ID
        list_res = await ac.get("/api/profiles", headers=HEADERS)
        profile_id = list_res.json()["data"][0]["id"]
        
        response = await ac.get(f"/api/profiles/{profile_id}", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["data"]["id"] == profile_id

@pytest.mark.asyncio
async def test_delete_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create one to delete
        res = await ac.post("/api/profiles", json={"name": "john"}, headers=HEADERS)
        pid = res.json()["data"]["id"]
        
        response = await ac.delete(f"/api/profiles/{pid}", headers=HEADERS)
        assert response.status_code == 204
        
        # Verify 404
        response2 = await ac.get(f"/api/profiles/{pid}", headers=HEADERS)
        assert response2.status_code == 404
