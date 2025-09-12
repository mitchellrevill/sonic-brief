"""
Permissions Router - Permission and capability management
Handles role assignments, custom capabilities, and permission queries
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from pydantic import BaseModel
import logging

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB
from .authentication import get_current_user
from .user_management import require_admin_user, require_user_view_access, require_user_edit_access
from ...models.permissions import PermissionLevel, PermissionCapability, get_user_capabilities, merge_custom_capabilities

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="", tags=["permissions"])


async def require_analytics_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require analytics viewing capability and return the full user object
    """
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})

    # Get effective capabilities (base + custom)
    effective_capabilities = get_user_capabilities(user_permission, custom_capabilities)

    # Check if user has analytics viewing access (admin or specific analytics capability)
    if not (effective_capabilities.get(PermissionCapability.CAN_VIEW_ANALYTICS.value, False) or 
            user_permission == PermissionLevel.ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Analytics access required. You need admin permission or the 'can_view_analytics' capability."
        )
    return current_user

@router.get("/users/me/permissions")
async def get_my_permissions(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return current user's permission level, custom capabilities and effective capabilities.

    This endpoint is used by the frontend to determine feature access. Previously missing,
    resulting in 404 responses and session tracking errors attempting to resolve capabilities.
    """
    try:
        user_permission = current_user.get("permission")
        custom_capabilities = current_user.get("custom_capabilities", {})
        effective_capabilities = get_user_capabilities(user_permission, custom_capabilities)
        return {
            "status": 200,
            "permission_level": user_permission,
            "custom_capabilities": custom_capabilities,
            "effective_capabilities": effective_capabilities,
        }
    except Exception as e:
        logger.error(f"Error resolving current user permissions: {e}")
        return {"status": 500, "message": f"Error resolving permissions: {e}"}


@router.get("/users/by-permission/{permission_level}")
async def get_users_by_permission(
    permission_level: str,
    current_user: Dict[str, Any] = Depends(require_user_view_access)
):
    """Get all users with a specific permission level (requires user viewing capability)."""
    # Validate permission level
    try:
        PermissionLevel(permission_level)
    except ValueError:
        return {"status": 400, "message": f"Invalid permission level: {permission_level}"}

    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        query = "SELECT * FROM c WHERE c.type = 'user' AND c.permission = @permission"
        parameters = [{"name": "@permission", "value": permission_level}]
        users = list(
            cosmos_db.users_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        for user in users:
            user.pop("hashed_password", None)
        return {
            "status": 200,
            "users": users,
            "count": len(users),
            "permission_level": permission_level,
        }
    except Exception as e:
        logger.error(f"Error fetching users by permission: {e}", exc_info=True)
        return {"status": 500, "message": f"Error fetching users: {e}"}


@router.patch("/users/{user_id}/permission")
async def update_user_permission(
    user_id: str,
    permission_data: Dict[str, str] = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Update a user's permission level. Admin only.
    """
    try:
        new_permission = permission_data.get("permission")
        if not new_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Permission field is required"
            )

        # Validate permission level
        try:
            PermissionLevel(new_permission)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission level: {new_permission}"
            )

        # Prevent self-permission changes to avoid lockout
        if user_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own permission level"
            )

        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)

        # Update user permission
        from datetime import datetime, timezone
        update_data = {
            "permission": new_permission,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        updated_user = await cosmos_db.update_user(user_id, update_data)

        # Log audit entry for permission change
        try:
            from ...services.auth.audit_service import AuditService
            audit_service = AuditService(cosmos_db)
            await audit_service.log_administrative_action(
                action_type="permission_changed",
                admin_user_id=current_user.get("id"),
                target_resource_type="user",
                target_resource_id=user_id,
                changes={
                    "old_permission": "unknown",  # Would need to fetch from DB first
                    "new_permission": new_permission
                },
                metadata={
                    "admin_email": current_user.get("email"),
                    "target_user_email": updated_user.get("email")
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log permission change audit: {str(e)}")

        logger.info(f"Permission changed for user {user_id} to {new_permission} by admin {current_user['id']}")

        # Remove sensitive data
        updated_user.pop("hashed_password", None)

        return {
            "status": "success",
            "message": f"User permission updated to {new_permission}",
            "user": updated_user
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"User not found for permission update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(f"Error updating user permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating permission: {str(e)}"
        )


@router.get("/users/{user_id}/capabilities")
async def get_user_capabilities_endpoint(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_user_view_access)
):
    """
    Get user's effective capabilities (base + custom). Admin only.
    """
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)

        # Get user
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get effective capabilities
        user_permission = user.get("permission")
        custom_capabilities = user.get("custom_capabilities", {})
        effective_capabilities = get_user_capabilities(user_permission, custom_capabilities)

        return {
            "status": "success",
            "user_id": user_id,
            "permission_level": user_permission,
            "custom_capabilities": custom_capabilities,
            "effective_capabilities": effective_capabilities
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user capabilities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting capabilities: {str(e)}"
        )


@router.patch("/users/{user_id}/capabilities")
async def update_user_capabilities(
    user_id: str,
    capability_data: Dict[str, Any] = Body(...),
    current_user: Dict[str, Any] = Depends(require_user_edit_access)
):
    """
    Update user's custom capabilities. Admin only.
    """
    try:
        custom_capabilities = capability_data.get("custom_capabilities", {})

        # Validate that all capability keys are valid
        valid_capabilities = set(cap.value for cap in PermissionCapability)
        for capability in custom_capabilities.keys():
            if capability not in valid_capabilities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid capability: {capability}"
                )

        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)

        # Update user capabilities
        from datetime import datetime, timezone
        update_data = {
            "custom_capabilities": custom_capabilities,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        updated_user = await cosmos_db.update_user(user_id, update_data)

        logger.info(f"Capabilities updated for user {user_id} by admin {current_user['id']}")

        # Remove sensitive data
        updated_user.pop("hashed_password", None)

        return {
            "status": "success",
            "message": "User capabilities updated successfully",
            "user": updated_user,
            "custom_capabilities": custom_capabilities
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"User not found for capability update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(f"Error updating user capabilities: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating capabilities: {str(e)}"
        )
