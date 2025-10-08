"""
User Management Router - CRUD operations for users
Handles user creation, retrieval, updates, and deletion
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Request, Body, Query
from pydantic import BaseModel
import logging
import uuid

from app.core.config import get_config
from app.core.dependencies import get_current_user, get_cosmos_service, get_error_handler
from app.routers.auth.authentication import get_password_hash
from app.models.permissions import (
    PermissionLevel,
    has_permission_level,
    PERMISSION_HIERARCHY,
)
from app.core.errors import (
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

router = APIRouter(prefix="", tags=["user-management"])

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


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str
    created_at: str
    updated_at: str


class ChangePasswordRequest(BaseModel):
    new_password: str


async def require_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require admin permission and return the full user object
    """
    user_permission = current_user.get("permission")
    try:
        user_level = PERMISSION_HIERARCHY.get(user_permission, 0)
    except Exception:
        user_level = PERMISSION_HIERARCHY.get(PermissionLevel.USER.value, 0)
    if user_level < PERMISSION_HIERARCHY.get(PermissionLevel.ADMIN.value, 0):
        raise PermissionError(
            "Admin access required",
            details={"required_permission": PermissionLevel.ADMIN.value, "user_permission": user_permission},
        )
    return current_user


async def require_user_view_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require user viewing capability and return the full user object
    """
    # Check if user has editor permission or higher (needed to view users)
    user_permission = current_user.get("permission")
    
    # Check permission level - only editors and admins can view users
    if not has_permission_level(user_permission, PermissionLevel.EDITOR):
        raise PermissionError(
            "Editor permission or higher required to view users",
            details={"required_permission": PermissionLevel.EDITOR.value, "user_permission": user_permission},
        )
    return current_user


async def require_user_edit_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require admin permission and return the full user object
    """
    # Check if user has admin permission (needed to edit users)
    user_permission = current_user.get("permission")
    
    # Check permission level - only admins can edit users
    if not has_permission_level(user_permission, PermissionLevel.ADMIN):
        raise PermissionError(
            "Admin permission required to edit users",
            details={"required_permission": PermissionLevel.ADMIN.value, "user_permission": user_permission},
        )
    return current_user


@router.get("/users")
async def get_all_users(
    current_user: Dict[str, Any] = Depends(require_user_view_access),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get all users (requires user viewing capability)
    """
    try:
        users = await cosmos_service.get_all_users()
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "fetch all users",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )

    for user in users:
        user.pop("hashed_password", None)

    return {"status": 200, "users": users}


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_user_view_access),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Get a specific user by ID (requires user viewing capability)
    """
    try:
        user = await cosmos_service.get_user_by_id(user_id)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "fetch user by id",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"user_id": user_id},
        )

    if not user:
        raise ResourceNotFoundError("user", user_id)

    user.pop("hashed_password", None)
    return {"status": 200, "user": user}


@router.get("/users/by-email")
async def get_user_by_email(
    email: str = Query(..., description="User's email address"), 
    current_user: Dict[str, Any] = Depends(require_user_view_access),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    try:
        user = await cosmos_service.get_user_by_email(email)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "fetch user by email",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"email": email},
        )

    if not user:
        raise ResourceNotFoundError("user", email)

    user.pop("hashed_password", None)
    return {"status": 200, "user": user}


@router.post("/register")
async def register_user(
    request: Request, 
    current_user: Dict[str, Any] = Depends(require_admin_user),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    email: Optional[str] = None
    try:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        missing_fields = [
            field for field, value in {"email": email, "password": password}.items() if not value
        ]
        if missing_fields:
            logger.warning("Registration attempt with missing fields: %s", missing_fields)
            raise ValidationError(
                "Email and password are required",
                details={"missing_fields": missing_fields},
            )

        try:
            existing_user = await cosmos_service.get_user_by_email(email)
        except ApplicationError:
            raise
        except Exception as exc:
            _handle_internal_error(
                error_handler,
                "check existing user",
                exc,
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                details={"email": email},
            )

        if existing_user:
            logger.warning("Registration attempt for existing email: %s", email)
            raise ApplicationError(
                "Email already registered",
                ErrorCode.RESOURCE_CONFLICT,
                status_code=409,
                details={"email": email},
            )

        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        user_data = {
            "id": f"user_{timestamp}",
            "type": "user",
            "email": email,
            "hashed_password": get_password_hash(password),
            "permission": PermissionLevel.USER.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            created_user = await cosmos_service.create_user(user_data)
        except ApplicationError:
            raise
        except Exception as exc:
            _handle_internal_error(
                error_handler,
                "create user",
                exc,
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                details={"email": email},
            )

        logger.info("User created with ID: %s", created_user["id"])
        return {"status": 200, "message": f"User {email} created successfully"}

    except ApplicationError:
        raise
    except Exception as exc:
        details = {"email": email} if email else None
        error_handler.raise_internal("register user", exc, extra=details)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str, 
    update_data: dict = Body(...), 
    current_user: Dict[str, Any] = Depends(require_admin_user),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    try:
        updated_user = await cosmos_service.update_user(user_id, update_data)
    except ApplicationError:
        raise
    except ValueError as exc:
        raise ResourceNotFoundError("user", user_id) from exc
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "update user",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"user_id": user_id},
        )

    updated_user.pop("hashed_password", None)
    return {"status": 200, "user": updated_user}


@router.patch("/users/{user_id}/password")
async def change_user_password(
    user_id: str,
    password_data: ChangePasswordRequest = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin_user),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Change user password. Admin only.
    """
    hashed_password = get_password_hash(password_data.new_password)

    update_data = {
        "hashed_password": hashed_password,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        await cosmos_service.update_user(user_id, update_data)
    except ApplicationError:
        raise
    except ValueError as exc:
        raise ResourceNotFoundError("user", user_id) from exc
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "change user password",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"user_id": user_id},
        )

    logger.info("Password changed for user %s by admin %s", user_id, current_user["id"])
    return {
        "status": "success",
        "message": "Password changed successfully"
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_user),
    cosmos_service = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """
    Delete a user account. Admin only.
    """
    if user_id == current_user["id"]:
        raise ApplicationError(
            "Cannot delete your own account",
            ErrorCode.OPERATION_NOT_ALLOWED,
            status_code=400,
            details={"user_id": user_id},
        )

    try:
        user = await cosmos_service.get_user_by_id(user_id)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "fetch user before deletion",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"user_id": user_id},
        )

    if not user:
        raise ResourceNotFoundError("user", user_id)

    try:
        await cosmos_service.delete_user(user_id)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "delete user",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details={"user_id": user_id},
        )

    logger.info("User %s deleted by admin %s", user_id, current_user["id"])
    return {
        "status": "success",
        "message": f"User {user.get('email', user_id)} deleted successfully"
    }
