from typing import Dict, Any, Optional
from ...models.permissions import PermissionLevel, has_permission_level
import logging

logger = logging.getLogger(__name__)


def check_job_access(job: Dict[str, Any], current_user: Dict[str, Any], required_permission: str = "view") -> bool:
    # Keep behaviour compatible with legacy router usage
    if job.get("deleted", False):
        return False

    # Admin shortcut
    is_admin = False
    if "permission" in current_user:
        is_admin = str(current_user["permission"]).lower() == "admin"
    elif "permissions" in current_user:
        perms = current_user["permissions"]
        if isinstance(perms, list):
            is_admin = any(str(p).lower() == "admin" for p in perms)
    if is_admin:
        return True

    if job.get("user_id") == current_user.get("id"):
        return True

    if "shared_with" in job:
        for share in job["shared_with"]:
            if share.get("user_id") == current_user.get("id"):
                levels = {"view": 1, "edit": 2, "admin": 3}
                return levels.get(share.get("permission_level"), 0) >= levels.get(required_permission, 0)

    return False
    


def check_job_permission_level(current_user: Dict[str, Any], job: Dict[str, Any], required_permission: str = "view") -> bool:
    """
    Check if user has required permission level for a job using simple hierarchical permissions.
    
    Args:
        current_user: User dict with permission level
        job: Job dict
        required_permission: "view", "edit", or "admin"
    
    Returns:
        bool: True if user has sufficient permission
    """
    user_permission = current_user.get("permission", "User")
    
    # Admin users can do everything
    if user_permission == PermissionLevel.ADMIN.value:
        return True
    
    # Check if user owns the job
    if job.get("user_id") == current_user.get("id"):
        return True
    
    # Check shared permissions
    if "shared_with" in job:
        for share in job["shared_with"]:
            if share.get("user_id") == current_user.get("id"):
                share_permission = share.get("permission_level", "view")
                permission_levels = {"view": 1, "edit": 2, "admin": 3}
                user_level = permission_levels.get(share_permission, 0)
                required_level = permission_levels.get(required_permission, 0)
                return user_level >= required_level
    
    return False


def get_user_job_permission(job: Dict[str, Any], current_user: Dict[str, Any]) -> Optional[str]:
    if job.get("user_id") == current_user.get("id"):
        return "owner"
    if "shared_with" in job:
        for share in job["shared_with"]:
            if share.get("user_id") == current_user.get("id"):
                return share.get("permission_level")
    return None


class JobPermissions:
    """Compatibility wrapper used by routers as a dependency provider.

    Provides async methods with the expected names. Where possible these
    delegate to the module-level helper functions. This keeps routers
    decoupled from the implementation details and preserves backwards
    compatibility during the refactor.
    """

    async def check_job_access(self, job_or_id: Any, current_user: Dict[str, Any], required_permission: str = "view") -> bool:
        """Check whether the current_user has the required_permission on job.

        Accepts either a job dict or a job id. If a dict is provided, delegate
        to the existing `check_job_access` helper. If an id is provided we
        cannot fetch the job from here, so fall back to a permissive check
        based on the user's admin flag. This is intentionally conservative
        for development; production callers should use the JobService to
        fetch the job and call the helper directly.
        """
        try:
            if isinstance(job_or_id, dict):
                return check_job_access(job_or_id, current_user, required_permission)
        except Exception:
            # If delegation fails, continue to fallback logic below
            pass

        # Fallback: allow if user appears to be admin
        if isinstance(current_user, dict):
            perm = current_user.get("permission") or current_user.get("permissions")
            if isinstance(perm, str) and perm.lower() == "admin":
                return True
            if isinstance(perm, list) and any(str(p).lower() == "admin" for p in perm):
                return True

        # Otherwise conservatively deny (can't verify ownership without job)
        try:
            uid = current_user.get('id') if isinstance(current_user, dict) else None
            logger.info(f"Denying job access fallback for user={uid} job_or_id={job_or_id} required={required_permission}")
        except Exception:
            logger.info("Denying job access fallback (unable to stringify user/job)")
        return False

    async def check_user_admin_privileges(self, current_user: Dict[str, Any]) -> bool:
        """Return True if the user has an admin permission entry."""
        if not isinstance(current_user, dict):
            return False
        perm = current_user.get("permission") or current_user.get("permissions")
        if isinstance(perm, str):
            return str(perm).lower() == "admin"
        if isinstance(perm, list):
            return any(str(p).lower() == "admin" for p in perm)
        return False
