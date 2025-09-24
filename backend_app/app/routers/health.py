from fastapi import APIRouter, status, Depends
from ..core.dependencies import (
    CosmosService,
    get_cosmos_service,
    get_storage_service,
    require_user
)
from ..core.config import get_config

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic liveness check - no external dependencies (safe for public)."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check(
    current_user=Depends(require_user),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
):
    """Authenticated readiness probe (reduced detail for security)."""
    config = get_config()
    result = {"ready": True, "components": {}}
    # Minimal checks without exposing errors publicly
    try:
        storage_service = get_storage_service(config)
        result["components"]["storage"] = bool(storage_service)
    except Exception:
        result["components"]["storage"] = False
        result["ready"] = False
    # Commented out until background service is implemented
    # try:
    #     bg_service = get_background_service(config)
    #     result["components"]["background"] = bool(bg_service)
    # except Exception:
    #     result["components"]["background"] = False
    #     result["ready"] = False
    try:
        cosmos_ok = getattr(cosmos_service, "is_available", lambda: True)()
        result["components"]["cosmos"] = bool(cosmos_ok)
        if not cosmos_ok:
            result["ready"] = False
    except Exception:
        result["components"]["cosmos"] = False
        result["ready"] = False
    return result, (status.HTTP_200_OK if result["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE)
