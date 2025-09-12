from functools import wraps
from fastapi import HTTPException, Depends
from typing import Callable, Any

from .settings import get_settings
from .dependencies import require_admin


def debug_endpoint_required(func: Callable) -> Callable:
    """Decorator to disable debug endpoints unless enabled via settings and admin access."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        settings = get_settings()
        if not getattr(settings, "enable_debug_endpoints", False):
            # Return not found to avoid advertising the endpoint
            raise HTTPException(status_code=404, detail="Not found")
        return await func(*args, **kwargs)

    return wrapper


async def require_debug_access(current_user: dict = Depends(require_admin)) -> dict:
    """Dependency: only allow access when debug endpoints enabled and user is admin."""
    settings = get_settings()
    if not getattr(settings, "enable_debug_endpoints", False):
        raise HTTPException(status_code=404, detail="Not found")
    return current_user
