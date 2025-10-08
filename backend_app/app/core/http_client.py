from functools import lru_cache

import httpx


@lru_cache(maxsize=1)
def _get_cached_client(timeout: float = 30.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=timeout)


def get_client(timeout: float = 30.0) -> httpx.AsyncClient:
    """Return the shared AsyncClient. Lazily initialized on first use."""
    return _get_cached_client(timeout)


async def startup(timeout: float = 30.0) -> None:
    """Warm the shared client during application startup."""
    _get_cached_client(timeout)


async def shutdown() -> None:
    """Close the shared client during application shutdown."""
    if _get_cached_client.cache_info().currsize:
        client = _get_cached_client()
        await client.aclose()
        _get_cached_client.cache_clear()
