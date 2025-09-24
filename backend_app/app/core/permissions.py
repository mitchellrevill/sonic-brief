"""
Centralized permission helpers for resource-scoped permission checks.
Simplified to use only hierarchical permissions (USER/EDITOR/ADMIN).
"""
from typing import Dict, Any
from app.models.permissions import (
    PermissionLevel,
    has_permission_level,
    PERMISSION_HIERARCHY,
)


def user_has_permission_for_job(user: Dict[str, Any], job: Dict[str, Any], required_level: PermissionLevel) -> bool:
    """Check if a user has the required permission level for a job/resource.

    Evaluation order:
      - Permission level hierarchy check (ADMIN > EDITOR > USER)
      - Owner of the job  
      - Job.shared_with entries (permission: 'read' or 'write')
    """
    user_permission = user.get("permission")
    
    # Check if user has required permission level
    if has_permission_level(user_permission, required_level):
        return True

    # Owner always has access
    if job.get("user_id") == user.get("id"):
        return True

    # Check shared-with entries
    for share in job.get("shared_with", []):
        if share.get("user_id") == user.get("id"):
            share_permission = share.get("permission", "read")
            
            # Read permission allows viewing
            if required_level == PermissionLevel.USER and share_permission in ["read", "write"]:
                return True
            
            # Write permission allows editing  
            if required_level == PermissionLevel.EDITOR and share_permission == "write":
                return True

    return False


def user_can_view_job(user: Dict[str, Any], job: Dict[str, Any]) -> bool:
    """Check if user can view a job"""
    return user_has_permission_for_job(user, job, PermissionLevel.USER)


def user_can_edit_job(user: Dict[str, Any], job: Dict[str, Any]) -> bool:
    """Check if user can edit a job"""
    return user_has_permission_for_job(user, job, PermissionLevel.EDITOR)


def user_can_delete_job(user: Dict[str, Any], job: Dict[str, Any]) -> bool:
    """Check if user can delete a job (admin only or owner)"""
    user_permission = user.get("permission")
    
    # Admin can delete any job
    if user_permission == PermissionLevel.ADMIN.value:
        return True
    
    # Owner can delete their own job
    return job.get("user_id") == user.get("id")
