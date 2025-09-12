import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_permissions_me_unauthenticated():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/users/me/permissions")
        # Should be 401 due to dependency chain requiring authentication
        assert resp.status_code in (401, 403)
