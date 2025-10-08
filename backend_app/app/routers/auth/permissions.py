"""
Permissions Router - Permission and capability management
Handles role assignments, custom capabilities, and permission queries
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Body, Query
import logging

from ...core.dependencies import (
    CosmosService,
    get_cosmos_service,
    get_current_user,
    get_audit_service,
    get_error_handler,
)
from ...services.monitoring.audit_logging_service import AuditLoggingService as AuditService
from .user_management import require_admin_user, require_user_view_access, require_user_edit_access
from ...models.permissions import PermissionLevel, PermissionCapability, get_user_capabilities
from ...core.errors import (
    ApplicationError,
    ErrorCode,
    ErrorHandler,
    ValidationError,
    PermissionError,
    ResourceNotFoundError,
)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="", tags=["permissions"])

def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    message: str | None = None,
    details: dict | None = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        message=message,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )

def _query_container(
    container,
    *,
    action: str,
    query: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    details: Optional[Dict[str, Any]] = None,
    error_handler: ErrorHandler,
) -> List[Dict[str, Any]]:
    try:
        return list(
            container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
    except ApplicationError:
        raise
    except Exception as exc:
        error_handler.raise_internal(
            action,
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            extra=details,
        )


async def require_analytics_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require analytics viewing capability and return the full user object
    """
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})

    # Get effective capabilities (base + custom)
    effective_capabilities = get_user_capabilities(user_permission, custom_capabilities)

    # Check if user has analytics viewing access (admin or specific analytics capability)
    if not (
        effective_capabilities.get(PermissionCapability.CAN_VIEW_ANALYTICS.value, False)
        or user_permission == PermissionLevel.ADMIN.value
    ):
        raise PermissionError(
            "Analytics access required",
            details={
                "required_capability": PermissionCapability.CAN_VIEW_ANALYTICS.value,
                "user_permission": user_permission,
            },
        )
    return current_user

@router.get("/users/me/permissions")
async def get_my_permissions(
    current_user: Dict[str, Any] = Depends(get_current_user),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Return current user's permission level, custom capabilities and effective capabilities.

    This endpoint is used by the frontend to determine feature access. Previously missing,
    resulting in 404 responses and session tracking errors attempting to resolve capabilities.
    """
    try:
        user_permission = current_user.get("permission")
        custom_capabilities = current_user.get("custom_capabilities", {})

        all_caps = [
            "can_view_own_jobs",
            "can_create_jobs",
            "can_edit_own_jobs",
            "can_delete_own_jobs",
            "can_view_shared_jobs",
            "can_edit_shared_jobs",
            "can_delete_shared_jobs",
            "can_share_jobs",
            "can_view_all_jobs",
            "can_edit_all_jobs",
            "can_delete_all_jobs",
            "can_view_prompts",
            "can_create_prompts",
            "can_edit_prompts",
            "can_delete_prompts",
            "can_create_templates",
            "can_view_users",
            "can_create_users",
            "can_edit_users",
            "can_delete_users",
            "can_manage_users",
            "can_view_settings",
            "can_edit_settings",
            "can_view_analytics",
            "can_manage_system",
            "can_upload_files",
            "can_download_files",
            "can_export_data",
            "can_import_data",
        ]

        from ...models.permissions import capabilities_for_permission

        base_caps = capabilities_for_permission(user_permission, all_caps)

        effective_capabilities = base_caps.copy()
        for key, value in custom_capabilities.items():
            effective_capabilities[key] = bool(value)

        return {
            "status": 200,
            "data": {
                "user_id": current_user.get("id"),
                "email": current_user.get("email"),
                "permission": user_permission,
                "capabilities": effective_capabilities,
                "custom_capabilities": custom_capabilities,
            },
        }
    except ApplicationError:
        raise
    except Exception as exc:
            _handle_internal_error(
                error_handler,
                "resolve current user permissions",
                exc,
                details={"user_id": current_user.get("id")},
            )


@router.get("/users/by-permission/{permission_level}")
async def get_users_by_permission(
    permission_level: str,
    current_user: Dict[str, Any] = Depends(require_user_view_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get all users with a specific permission level (requires user viewing capability)."""
    try:
        PermissionLevel(permission_level)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid permission level: {permission_level}",
            details={"permission_level": permission_level},
        ) from exc

    users = _query_container(
        cosmos_service.users_container,
        action="query users by permission",
        query="SELECT * FROM c WHERE c.type = 'user' AND c.permission = @permission",
        parameters=[{"name": "@permission", "value": permission_level}],
        details={"permission_level": permission_level},
        error_handler=error_handler,
    )

    for user in users:
        user.pop("hashed_password", None)

    return {
        "status": 200,
        "users": users,
        "count": len(users),
        "permission_level": permission_level,
    }


@router.patch("/users/{user_id}/permission")
async def update_user_permission(
    user_id: str,
    permission_data: Dict[str, str] = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin_user),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    audit_service: AuditService = Depends(get_audit_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Update a user's permission level. Admin only.
    """
    new_permission = permission_data.get("permission")
    if not new_permission:
        raise ValidationError(
            "Permission field is required",
            field="permission",
            details={"user_id": user_id},
        )

    try:
        PermissionLevel(new_permission)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid permission level: {new_permission}",
            field="permission",
            details={"user_id": user_id},
        ) from exc

    if user_id == current_user["id"]:
        raise ApplicationError(
            "Cannot change your own permission level",
            ErrorCode.OPERATION_NOT_ALLOWED,
            status_code=400,
            details={"user_id": user_id},
        )

    from datetime import datetime, timezone

    update_data = {
        "permission": new_permission,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        updated_user = await cosmos_service.update_user(user_id, update_data)
    except ApplicationError:
        raise
    except ValueError as exc:
        raise ResourceNotFoundError("user", user_id) from exc
    except Exception as exc:
        error_handler.raise_internal(
            "update user permission",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            extra={"user_id": user_id},
        )

    try:
        action_details = {
            "old_permission": "unknown",
            "new_permission": new_permission,
            "admin_email": current_user.get("email"),
            "target_user_email": updated_user.get("email"),
        }
        await audit_service.log_administrative_action(
            "permission_changed",
            current_user.get("id"),
            "user",
            user_id,
            action_details,
        )
    except Exception as exc:
        logger.warning(
            "Failed to log permission change audit: %s",
            str(exc),
        )

    logger.info(
        "Permission changed for user %s to %s by admin %s",
        user_id,
        new_permission,
        current_user["id"],
    )

    updated_user.pop("hashed_password", None)

    return {
        "status": "success",
        "message": f"User permission updated to {new_permission}",
        "user": updated_user,
    }


@router.get("/users/{user_id}/capabilities")
async def get_user_capabilities_endpoint(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_user_view_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get user's effective capabilities (base + custom). Admin only.
    """
    try:
        user = await cosmos_service.get_user_by_id(user_id)
    except ApplicationError:
        raise
    except Exception as exc:
        error_handler.raise_internal(
            "fetch user for capability lookup",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            extra={"user_id": user_id},
        )

    if not user:
        raise ResourceNotFoundError("user", user_id)

    user_permission = user.get("permission")
    custom_capabilities = user.get("custom_capabilities", {})
    effective_capabilities = get_user_capabilities(user_permission, custom_capabilities)

    return {
        "status": "success",
        "user_id": user_id,
        "permission_level": user_permission,
        "custom_capabilities": custom_capabilities,
        "effective_capabilities": effective_capabilities,
    }


@router.patch("/users/{user_id}/capabilities")
async def update_user_capabilities(
    user_id: str,
    capability_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_user_edit_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Update user's custom capabilities. Admin only.
    """
    custom_capabilities = capability_data.get("custom_capabilities", {})

    valid_capabilities = {cap.value for cap in PermissionCapability}
    invalid_capabilities = [cap for cap in custom_capabilities if cap not in valid_capabilities]
    if invalid_capabilities:
        raise ValidationError(
            "Invalid capability provided",
            details={"invalid_capabilities": invalid_capabilities, "user_id": user_id},
        )

    from datetime import datetime, timezone

    update_data = {
        "custom_capabilities": custom_capabilities,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        updated_user = await cosmos_service.update_user(user_id, update_data)
    except ApplicationError:
        raise
    except ValueError as exc:
        raise ResourceNotFoundError("user", user_id) from exc
    except Exception as exc:
        error_handler.raise_internal(
            "update user capabilities",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            extra={"user_id": user_id},
        )

    logger.info("Capabilities updated for user %s by admin %s", user_id, current_user["id"])

    updated_user.pop("hashed_password", None)

    return {
        "status": "success",
        "message": "User capabilities updated successfully",
        "user": updated_user,
        "custom_capabilities": custom_capabilities,
    }
