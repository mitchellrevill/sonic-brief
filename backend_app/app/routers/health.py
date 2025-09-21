from fastapi import APIRouter, status
from ..core.config import get_app_config, get_cosmos_db_cached
from ..core.dependencies import get_storage_service, get_background_service, require_analytics_access

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic liveness check - no external dependencies (safe for public)."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check(current_user=require_analytics_access):
    """Authenticated readiness probe (reduced detail for security)."""
    cfg = get_app_config()
    cosmos = get_cosmos_db_cached(cfg)
    result = {"ready": True, "components": {}}
    # Minimal checks without exposing errors publicly
    try:
        storage = get_storage_service(cfg)
        result["components"]["storage"] = bool(storage)
    except Exception:
        result["components"]["storage"] = False
        result["ready"] = False
    try:
        bg = get_background_service(cfg)
        result["components"]["background"] = bool(bg)
    except Exception:
        result["components"]["background"] = False
        result["ready"] = False
    try:
        cosmos_ok = getattr(cosmos, "is_available", lambda: True)()
        result["components"]["cosmos"] = bool(cosmos_ok)
        if not cosmos_ok:
            result["ready"] = False
    except Exception:
        result["components"]["cosmos"] = False
        result["ready"] = False
    return result, (status.HTTP_200_OK if result["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE)
