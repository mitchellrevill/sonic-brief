"""
Resource-level permission utilities for granular access control
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.models.permissions import PermissionLevel, can_user_perform_action, PermissionCapability

class ResourcePermission:
    """Represents a permission level for a specific resource"""
    
    OWNER = "owner"
    ADMIN = "admin" 
    EDIT = "edit"
    VIEW = "view"
    
    # Permission hierarchy for resources (higher number = more permissions)
    HIERARCHY = {
        VIEW: 1,
        EDIT: 2,
        ADMIN: 3,
        OWNER: 4
    }

def check_resource_access(
    resource: Dict[str, Any], 
    current_user: Dict[str, Any], 
    required_permission: str = ResourcePermission.VIEW
) -> bool:
    """
    Check if a user has the required permission level for a resource.
    
    Args:
        resource: The resource document (e.g., job, template)
        current_user: The current user object
        required_permission: Required permission level (view, edit, admin, owner)
    
    Returns:
        bool: True if user has access, False otherwise
    """
    user_id = current_user.get("id")
    user_permission = current_user.get("permission", "User")
    
    # Admins can access all resources
    if can_user_perform_action(user_permission, PermissionCapability.CAN_VIEW_ALL_JOBS):
        return True
    
    # Check if user is the owner/creator
    if resource.get("created_by") == user_id or resource.get("user_id") == user_id:
        return True  # Owners have all permissions
    
    # Check shared permissions
    shared_with = resource.get("shared_with", [])
    for share in shared_with:
        if share.get("user_id") == user_id:
            user_resource_permission = share.get("permission_level", ResourcePermission.VIEW)
            return has_resource_permission_level(user_resource_permission, required_permission)
    
    return False

def has_resource_permission_level(user_permission: str, required_permission: str) -> bool:
    """
    Check if a user's resource permission level meets or exceeds the required level.
    
    Args:
        user_permission: User's permission level for the resource
        required_permission: Required permission level
    
    Returns:
        bool: True if user permission meets or exceeds required level
    """
    user_level = ResourcePermission.HIERARCHY.get(user_permission, 0)
    required_level = ResourcePermission.HIERARCHY.get(required_permission, 0)
    return user_level >= required_level

def get_user_resource_permission(resource: Dict[str, Any], current_user: Dict[str, Any]) -> str:
    """
    Get the user's permission level for a specific resource.
    
    Args:
        resource: The resource document
        current_user: The current user object
    
    Returns:
        str: The user's permission level for the resource
    """
    user_id = current_user.get("id")
    user_permission = current_user.get("permission", "User")
    
    # Admins have admin permission on all resources
    if can_user_perform_action(user_permission, PermissionCapability.CAN_VIEW_ALL_JOBS):
        return ResourcePermission.ADMIN
    
    # Check if user is the owner/creator
    if resource.get("created_by") == user_id or resource.get("user_id") == user_id:
        return ResourcePermission.OWNER
    
    # Check shared permissions
    shared_with = resource.get("shared_with", [])
    for share in shared_with:
        if share.get("user_id") == user_id:
            return share.get("permission_level", ResourcePermission.VIEW)
    
    return None  # No access

def add_resource_share(
    resource: Dict[str, Any],
    user_id: str,
    user_email: str,
    permission_level: str,
    shared_by: str
) -> Dict[str, Any]:
    """
    Add a user to the resource's shared_with list.
    
    Args:
        resource: The resource document to modify
        user_id: ID of user to share with
        user_email: Email of user to share with
        permission_level: Permission level to grant
        shared_by: User ID who is sharing the resource
    
    Returns:
        Dict[str, Any]: Updated resource document
    """
    if "shared_with" not in resource:
        resource["shared_with"] = []
    
    # Remove existing share if it exists
    resource["shared_with"] = [
        share for share in resource["shared_with"] 
        if share.get("user_id") != user_id
    ]
    
    # Add new share
    resource["shared_with"].append({
        "user_id": user_id,
        "user_email": user_email,
        "permission_level": permission_level,
        "shared_at": datetime.now(timezone.utc).timestamp(),
        "shared_by": shared_by
    })
    
    return resource

def remove_resource_share(resource: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Remove a user from the resource's shared_with list.
    
    Args:
        resource: The resource document to modify
        user_id: ID of user to remove from sharing
    
    Returns:
        Dict[str, Any]: Updated resource document
    """
    if "shared_with" in resource:
        resource["shared_with"] = [
            share for share in resource["shared_with"] 
            if share.get("user_id") != user_id
        ]
    
    return resource

# Convenience functions for different resource types
def check_job_access(job: Dict[str, Any], current_user: Dict[str, Any], required_permission: str = ResourcePermission.VIEW) -> bool:
    """Check if user has access to a specific job"""
    return check_resource_access(job, current_user, required_permission)

def check_template_access(template: Dict[str, Any], current_user: Dict[str, Any], required_permission: str = ResourcePermission.VIEW) -> bool:
    """Check if user has access to a specific template"""
    return check_resource_access(template, current_user, required_permission)
