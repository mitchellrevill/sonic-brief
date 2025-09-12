"""
Centralized permission helpers for resource-scoped capability checks.
This module consolidates the duplicated `_user_has_capability_for_job` logic
so routers can import a single, well-tested helper.
"""
from typing import Dict, Any
from app.models.permissions import (
    PermissionLevel,
    PermissionCapability,
    can_user_perform_action,
    get_user_capabilities,
    merge_custom_capabilities,
)


def get_effective_capability_map(user: Dict[str, Any]) -> Dict[str, bool]:
    """Compute the effective capability map for a user (base role + custom overrides).

    Returns a mapping of capability_value -> bool.
    """
    user_permission = user.get("permission")
    custom = user.get("custom_capabilities", {}) or {}
    base = get_user_capabilities(user_permission)
    if custom:
        return merge_custom_capabilities(base, custom)
    return base


def user_has_capability_for_job(user: Dict[str, Any], job: Dict[str, Any], capability: str) -> bool:
    """Check if a user has a given capability for a job/resource.

    Evaluation order mirrors previous router implementations:
      - Admin role override
      - Role-based capability (via can_user_perform_action)
      - Effective capability map (base + custom)
      - Explicit user 'capabilities' list
      - Owner of the job
      - Job.shared_with entries (permission: 'read' or 'write')
    """
    # Admin override
    if user.get("permission") == PermissionLevel.ADMIN.value:
        return True

    # Role-based capability (legacy helper)
    try:
        if can_user_perform_action(user.get("permission"), capability):
            return True
    except Exception:
        # Be conservative if role lookup fails
        pass

    # Effective capability map
    effective = get_effective_capability_map(user)
    if effective.get(capability, False):
        return True

    # Explicit capability flags on the user (older shape)
    user_caps = user.get("capabilities") or []
    if capability in user_caps:
        return True

    # Owner
    if job.get("user_id") == user.get("id"):
        return True

    # Shared-with entries
    for share in job.get("shared_with", []):
        if share.get("user_id") == user.get("id"):
            perm = share.get("permission", "read")
            if perm == "read" and capability in (
                PermissionCapability.CAN_VIEW_OWN_JOBS.value,
                PermissionCapability.CAN_VIEW_SHARED_JOBS.value,
                PermissionCapability.CAN_DOWNLOAD_FILES.value,
            ):
                return True
            if perm == "write" and capability in (
                PermissionCapability.CAN_EDIT_OWN_JOBS.value,
                PermissionCapability.CAN_EDIT_SHARED_JOBS.value,
                PermissionCapability.CAN_DOWNLOAD_FILES.value,
            ):
                return True

    return False
