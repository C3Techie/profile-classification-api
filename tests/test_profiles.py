import os
os.environ["TESTING"] = "True"

import pytest
import pytest_asyncio
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

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    app.dependency_overrides.clear()
    # Re-apply the specific overrides for these profile tests
    app.dependency_overrides[get_current_user] = override_auth
    app.dependency_overrides[require_admin] = override_auth
    app.dependency_overrides[require_analyst] = override_auth
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
        response = await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["name"] == "ella"
        assert "id" in data["data"]

@pytest.mark.asyncio
async def test_get_profiles_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a few
        await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        await ac.post("/api/profiles", json={"name": "john"}, headers=HEADERS)

        response = await ac.get("/api/profiles?page=1&limit=1", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["page"] == 1
        assert data["total"] >= 2
        assert len(data["data"]) == 1
        assert "next" in data["links"]

@pytest.mark.asyncio
async def test_nlq_search():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        
        response = await ac.get("/api/profiles/search?q=female from US", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert data["data"][0]["gender"] == "female"

@pytest.mark.asyncio
async def test_get_single_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/profiles", json={"name": "ella"}, headers=HEADERS)
        pid = res.json()["data"]["id"]
        
        response = await ac.get(f"/api/profiles/{pid}", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "ella"

@pytest.mark.asyncio
async def test_delete_profile():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/profiles", json={"name": "john"}, headers=HEADERS)
        pid = res.json()["data"]["id"]
        
        response = await ac.delete(f"/api/profiles/{pid}", headers=HEADERS)
        assert response.status_code == 204
        
        # Verify 404
        response = await ac.get(f"/api/profiles/{pid}", headers=HEADERS)
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_export_profiles_csv():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create one to export
        await ac.post("/api/profiles", json={"name": "csv-user"}, headers=HEADERS)
        
        response = await ac.get("/api/profiles/export?format=csv", headers=HEADERS)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        
        content = response.text
        # Verify header row
        header = "id,name,gender,gender_probability,age,age_group,country_id,country_name,country_probability,created_at"
        assert content.startswith(header)
        assert "csv-user" in content
