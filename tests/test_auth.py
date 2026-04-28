import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import engine
from app.db.base import Base
from unittest.mock import patch, AsyncMock
from app.core.dependencies import get_current_user

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    # CRITICAL: Clear overrides so auth tests don't "inherit" logged-in status
    app.dependency_overrides.clear()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_auth_github_redirect():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/github")
        # Accept 302 or 307
        assert response.status_code in [302, 307]
        assert "github.com/login/oauth/authorize" in response.headers["location"]

@pytest.mark.asyncio
async def test_auth_me_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/auth/me")
        # Now that we clear overrides, this will correctly return 401
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_auth_logout():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/logout", json={"refresh_token": "dummy"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_auth_refresh_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/auth/refresh", json={"refresh_token": "invalid-token"})
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_cli_callback_mock():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        with patch("app.api.v1.endpoints.auth._exchange_github_code", new_callable=AsyncMock) as mock_exchange, \
             patch("app.api.v1.endpoints.auth._get_github_user", new_callable=AsyncMock) as mock_user:
            
            mock_exchange.return_value = "gh_token_123"
            mock_user.return_value = {
                "id": "12345",
                "login": "testuser",
                "email": "test@example.com",
                "avatar_url": "http://image.com"
            }
            
            payload = {
                "code": "test_code",
                "code_verifier": "test_verifier",
                "redirect_uri": "http://localhost:8000/callback",
                "state": "test_state"
            }
            response = await ac.post("/auth/github/callback", json=payload)
            
            assert response.status_code == 200
            assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_web_callback_cookies():
    """Verify that the web callback sets HTTP-only cookies."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        with patch("app.api.v1.endpoints.auth._exchange_github_code", new_callable=AsyncMock) as mock_exchange, \
             patch("app.api.v1.endpoints.auth._get_github_user", new_callable=AsyncMock) as mock_user, \
             patch("app.api.v1.endpoints.auth.verify_state_token") as mock_state:
            
            mock_exchange.return_value = "gh_token_123"
            mock_user.return_value = {"id": "123", "login": "webuser"}
            mock_state.return_value = True
            
            response = await ac.get("/auth/github/callback?code=abc&state=xyz")
            
            # Should redirect to dashboard
            assert response.status_code == 302
            assert "dashboard" in response.headers["location"]
            
            # Should set cookies
            cookies = response.cookies
            assert "insighta_access" in cookies
            assert "insighta_refresh" in cookies
            
            set_cookie = response.headers["set-cookie"]
            assert "HttpOnly" in set_cookie
            assert "SameSite=strict" in set_cookie
