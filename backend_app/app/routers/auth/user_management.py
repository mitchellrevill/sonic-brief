"""
User Management Router - CRUD operations for users
Handles user creation, retrieval, updates, and deletion
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from pydantic import BaseModel
import logging
import uuid

from app.core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from .authentication import get_current_user, get_password_hash
from app.models.permissions import (
    PermissionLevel,
    PermissionCapability,
    get_user_capabilities,
    merge_custom_capabilities,
    PERMISSION_HIERARCHY,
)

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="", tags=["user-management"])


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
        user_level = PERMISSION_HIERARCHY.get(PermissionLevel(user_permission), 0)
    except Exception:
        user_level = PERMISSION_HIERARCHY.get(PermissionLevel.USER, 0)
    if user_level < PERMISSION_HIERARCHY.get(PermissionLevel.ADMIN, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_user_view_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require user viewing capability and return the full user object
    """
    # Get effective capabilities (base + custom)
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})
    base_caps = get_user_capabilities(user_permission)
    effective_capabilities = merge_custom_capabilities(base_caps, custom_capabilities)

    # Check if user has user viewing access
    if not effective_capabilities.get(PermissionCapability.CAN_VIEW_USERS, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User viewing access required. You need the 'can_view_users' capability."
        )
    return current_user


async def require_user_edit_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require user editing capability and return the full user object
    """
    # Get effective capabilities (base + custom)
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})
    base_caps = get_user_capabilities(user_permission)
    effective_capabilities = merge_custom_capabilities(base_caps, custom_capabilities)

    # Check if user has user editing access
    if not effective_capabilities.get(PermissionCapability.CAN_EDIT_USERS, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User editing access required. You need the 'can_edit_users' capability."
        )
    return current_user


@router.get("/users")
async def get_all_users(current_user: Dict[str, Any] = Depends(require_user_view_access)):
    """
    Get all users (requires user viewing capability)
    """
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        users = await cosmos_db.get_all_users()
        for user in users:
            user.pop("hashed_password", None)
        return {"status": 200, "users": users}
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error fetching users: {str(e)}"}


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_user_view_access)
):
    """
    Get a specific user by ID (requires user viewing capability)
    """
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            return {"status": 404, "message": f"User with ID {user_id} not found"}
        user.pop("hashed_password", None)
        return {"status": 200, "user": user}
    except Exception as e:
        logger.error(f"Error fetching user by ID: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error fetching user: {str(e)}"}


@router.get("/users/by-email")
async def get_user_by_email(
    email: str = Query(..., description="User's email address"), 
    current_user: Dict[str, Any] = Depends(require_user_view_access)
):
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        user = await cosmos_db.get_user_by_email(email)
        if not user:
            return {"status": 404, "message": f"User with email {email} not found"}
        user.pop("hashed_password", None)
        return {"status": 200, "user": user}
    except Exception as e:
        logger.error(f"Error fetching user by email: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error fetching user: {str(e)}"}


@router.post("/register")
async def register_user(request: Request, current_user: Dict[str, Any] = Depends(require_admin_user)):
    try:
        # Parse incoming JSON
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            logger.warning("Registration attempt with missing email or password")
            return {"status": 400, "message": "Email and password are required"}

        # Initialize configuration & DB
        config = get_app_config()
        try:
            cosmos_db = get_cosmos_db_cached(config)
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {e}")
            return {"status": 503, "message": "Database service unavailable"}

        # Check existing user
        try:
            existing_user = await cosmos_db.get_user_by_email(email)
            if existing_user:
                logger.warning(f"Registration attempt for existing email: {email}")
                return {"status": 400, "message": "Email already registered"}
        except Exception as e:
            logger.error(f"Error checking existing user: {e}", exc_info=True)
            return {"status": 500, "message": f"Error checking user existence: {e}"}

        # Create user document
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
            created_user = await cosmos_db.create_user(user_data)
            logger.info(f"User created with ID: {created_user['id']}")
            return {"status": 200, "message": f"User {email} created successfully"}
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return {"status": 500, "message": f"Error creating user: {e}"}

    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}", exc_info=True)
        return {"status": 500, "message": f"An unexpected error occurred: {e}"}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str, 
    update_data: dict = Body(...), 
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        updated_user = await cosmos_db.update_user(user_id, update_data)
        updated_user.pop("hashed_password", None)
        return {"status": 200, "user": updated_user}
    except ValueError as e:
        logger.error(f"User not found: {str(e)}", exc_info=True)
        return {"status": 404, "message": str(e)}
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}", exc_info=True)
        return {"status": 500, "message": f"Error updating user: {str(e)}"}


@router.patch("/users/{user_id}/password")
async def change_user_password(
    user_id: str,
    password_data: ChangePasswordRequest = Body(...),
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Change user password. Admin only.
    """
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        # Hash the new password
        hashed_password = get_password_hash(password_data.new_password)
        
        # Update user password
        update_data = {
            "hashed_password": hashed_password,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        updated_user = await cosmos_db.update_user(user_id, update_data)
        
        logger.info(f"Password changed for user {user_id} by admin {current_user['id']}")
        return {
            "status": "success",
            "message": "Password changed successfully"
        }
        
    except ValueError as e:
        logger.error(f"User not found for password change: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(f"Error changing password for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error changing password: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin_user)
):
    """
    Delete a user account. Admin only.
    """
    try:
        # Prevent self-deletion
        if user_id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        # Check if user exists
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user
        await cosmos_db.delete_user(user_id)
        
        logger.info(f"User {user_id} deleted by admin {current_user['id']}")
        return {
            "status": "success",
            "message": f"User {user.get('email', user_id)} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )
