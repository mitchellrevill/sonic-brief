from typing import Optional
import httpx

_client: Optional[httpx.AsyncClient] = None

def get_client() -> httpx.AsyncClient:
    """Return the shared AsyncClient. Must be initialized during app startup."""
    global _client
    if _client is None:
        # Lazily create if startup didn't run (safe fallback)
        _client = httpx.AsyncClient(timeout=30.0)
    return _client

async def startup(timeout: float = 30.0):
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=timeout)

async def shutdown():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
