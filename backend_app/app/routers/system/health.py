"""
Health Router - System health monitoring and diagnostics
Handles health checks, system status, monitoring, and uptime tracking
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
import logging

from ...models.analytics_models import SystemHealthResponse
from ...core.dependencies import (
    get_current_user,
    require_analytics_access,
    get_cosmos_service,
    get_system_health_service,
    get_error_handler,
    CosmosService,
)
from ...core.errors import (
    ApplicationError,
    ErrorCode,
    ErrorHandler,
    PermissionError,
)
from ...services.interfaces import SystemHealthServiceInterface
from ...models.permissions import PermissionLevel, has_permission_level
from ...utils.async_utils import run_sync

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["system-health"])


def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    message: str | None = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        message=message,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )


def _require_admin_permission(current_user: Dict[str, Any], action: str) -> None:
    user_permission = current_user.get("permission")
    if not has_permission_level(user_permission, PermissionLevel.ADMIN):
        raise PermissionError(
            f"Admin permission required to {action}",
            details={
                "action": action,
                "required_permission": PermissionLevel.ADMIN.value,
                "user_permission": user_permission,
            },
        )


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: Dict[str, Any] = Depends(require_analytics_access),
    system_service: SystemHealthServiceInterface = Depends(get_system_health_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get comprehensive system health metrics (Admin only)"""
    try:
        _require_admin_permission(current_user, "view system health")

        health_data = await system_service.get_system_health()

        return health_data

    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get system health",
            exc,
            details={"requested_by": current_user.get("id")},
        )


