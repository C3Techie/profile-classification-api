import os
os.environ["TESTING"] = "True"

import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import engine
from app.db.base import Base

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

@pytest.fixture(scope="function", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_create_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test valid creation
        response = await ac.post("/api/profiles", json={"name": "ella"})
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "ella"
        assert "id" in data["data"]
        assert data["data"]["country_name"] == "United States"
        
        # Test idempotency (same name)
        response2 = await ac.post("/api/profiles", json={"name": "ella"})
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["message"] == "Profile already exists"
        assert data2["data"]["id"] == data["data"]["id"]

@pytest.mark.asyncio
async def test_get_profiles_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a few
        await ac.post("/api/profiles", json={"name": "ella"})
        await ac.post("/api/profiles", json={"name": "john"})
        
        response = await ac.get("/api/profiles?page=1&limit=1")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 1
        assert data["total"] == 2
        assert len(data["data"]) == 1

@pytest.mark.asyncio
async def test_nlq_search():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create sample
        await ac.post("/api/profiles", json={"name": "ella"})
        
        # Test search
        response = await ac.get("/api/profiles/search?q=females from united states")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["data"][0]["gender"] == "female"
        
        # Test invalid search
        response2 = await ac.get("/api/profiles/search?q=unknown query")
        assert response2.status_code == 400
        assert response2.json()["status"] == "error"

@pytest.mark.asyncio
async def test_get_single_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create one first
        await ac.post("/api/profiles", json={"name": "ella"})
        
        # Get all first to find an ID
        list_res = await ac.get("/api/profiles")
        profile_id = list_res.json()["data"][0]["id"]
        
        response = await ac.get(f"/api/profiles/{profile_id}")
        assert response.status_code == 200
        assert response.json()["data"]["id"] == profile_id

@pytest.mark.asyncio
async def test_delete_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create one to delete
        res = await ac.post("/api/profiles", json={"name": "john"})
        pid = res.json()["data"]["id"]
        
        response = await ac.delete(f"/api/profiles/{pid}")
        assert response.status_code == 204
        
        # Verify 404
        response2 = await ac.get(f"/api/profiles/{pid}")
        assert response2.status_code == 404
