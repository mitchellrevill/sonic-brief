# Unified Permission Dependencies
from functools import wraps
from typing import Callable, List, Optional
from fastapi import HTTPException, status, Depends
from ..middleware.permission_middleware import get_current_user_id
from ..models.permissions import PermissionLevel, PermissionCapability, PERMISSION_HIERARCHY, get_user_capabilities, merge_custom_capabilities
from ..core.config import get_app_config, get_cosmos_db_cached
from ..utils.audit_logger import audit_logger, AuditEventType
from ..core.permissions import user_has_capability_for_job

# Level-based permission dependencies
async def require_admin(user_id: str = Depends(get_current_user_id)) -> str:
    """Require ADMIN level permissions"""
    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)
    user = await cosmos_db.get_user_by_id(user_id)
    user_perm = None
    if user:
        user_perm = user.get("permission")
    if not user_perm or PERMISSION_HIERARCHY.get(user_perm, 0) < PERMISSION_HIERARCHY.get(PermissionLevel.ADMIN.value, 999):
        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="endpoint",
            resource_id="admin_endpoint",
            event_type=AuditEventType.ACCESS_DENIED
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user_id

async def require_editor(user_id: str = Depends(get_current_user_id)) -> str:
    """Require EDITOR level permissions or higher"""
    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)
    user = await cosmos_db.get_user_by_id(user_id)
    user_perm = None
    if user:
        user_perm = user.get("permission")
    if not user_perm or PERMISSION_HIERARCHY.get(user_perm, 0) < PERMISSION_HIERARCHY.get(PermissionLevel.EDITOR.value, 0):
        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="endpoint", 
            resource_id="editor_endpoint",
            event_type=AuditEventType.ACCESS_DENIED
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor privileges required"
        )
    return user_id

async def require_user(user_id: str = Depends(get_current_user_id)) -> str:
    """Require any authenticated user (USER level or higher)"""
    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)
    user = await cosmos_db.get_user_by_id(user_id)
    user_perm = None
    if user:
        user_perm = user.get("permission")
    if not user_perm or PERMISSION_HIERARCHY.get(user_perm, 0) < PERMISSION_HIERARCHY.get(PermissionLevel.USER.value, 0):
        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="endpoint",
            resource_id="user_endpoint", 
            event_type=AuditEventType.ACCESS_DENIED
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    return user_id

# Capability-based permission dependencies
def require_capability(capability: PermissionCapability):
    """Factory function to create capability-based permission dependency"""
    async def dependency(user_id: str = Depends(get_current_user_id)) -> str:
        # Fetch user and compute effective capabilities (base + custom)
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            await audit_logger.log_access_denied(
                user_id=user_id,
                resource_type="capability",
                resource_id=capability.value,
                event_type=AuditEventType.ACCESS_DENIED
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Required capability: {capability.value}")

        user_permission = user.get("permission")
        custom_capabilities = user.get("custom_capabilities", {})
        effective = get_user_capabilities(user_permission, custom_capabilities)
        if not effective.get(capability.value, False):
            await audit_logger.log_access_denied(
                user_id=user_id,
                resource_type="capability",
                resource_id=capability.value,
                event_type=AuditEventType.ACCESS_DENIED
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Required capability: {capability.value}")
        return user_id
    return dependency

def require_any_capability(capabilities: List[PermissionCapability]):
    """Require any one of the specified capabilities"""
    async def dependency(user_id: str = Depends(get_current_user_id)) -> str:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            await audit_logger.log_access_denied(
                user_id=user_id,
                resource_type="capabilities",
                resource_id=",".join([c.value for c in capabilities]),
                event_type=AuditEventType.ACCESS_DENIED
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Required one of: {', '.join([c.value for c in capabilities])}")

        user_permission = user.get("permission")
        custom_capabilities = user.get("custom_capabilities", {})
        effective = get_user_capabilities(user_permission, custom_capabilities)
        for capability in capabilities:
            if effective.get(capability.value, False):
                return user_id

        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="capabilities",
            resource_id=",".join([c.value for c in capabilities]),
            event_type=AuditEventType.ACCESS_DENIED
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Required one of: {', '.join([c.value for c in capabilities])}")
    return dependency

# Specific domain dependencies
# Analytics capability exists directly on the enum
require_analytics_access = require_capability(PermissionCapability.CAN_VIEW_ANALYTICS)
# Prompt management is represented by create/edit/delete prompt capabilities;
# require any of those to manage prompts
require_prompt_management = require_any_capability([
    PermissionCapability.CAN_CREATE_PROMPTS,
    PermissionCapability.CAN_EDIT_PROMPTS,
    PermissionCapability.CAN_DELETE_PROMPTS,
])
# Uploading files uses the CAN_UPLOAD_FILES capability
require_job_upload = require_capability(PermissionCapability.CAN_UPLOAD_FILES)
# Job management is represented by the set of all-jobs capabilities
require_job_management = require_any_capability([
    PermissionCapability.CAN_VIEW_ALL_JOBS,
    PermissionCapability.CAN_EDIT_ALL_JOBS,
    PermissionCapability.CAN_DELETE_ALL_JOBS,
    PermissionCapability.CAN_SHARE_JOBS,
])

# Friendly alias (requested): require_can_upload is the same as require_job_upload
require_can_upload = require_job_upload


# Job-scoped dependency: require that the caller is the job owner or an admin
async def require_job_owner_or_admin(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Ensure the current user is the owner of the job or has admin/all-jobs capabilities.

    Returns the full `current_user` dict on success (so handlers keep using the same shape).
    Raises HTTPException(404) if job not found and 403 if access denied.
    """
    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)

    # Build current_user object (same shape as get_current_user)
    user = await cosmos_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=403, detail="Authentication required")

    permission = user.get("permission")
    custom_capabilities = user.get("custom_capabilities", {})
    effective = get_user_capabilities(permission, custom_capabilities)
    current_user = {
        "id": user_id,
        "permission": permission,
        "custom_capabilities": custom_capabilities,
        "capabilities": [k for k, v in effective.items() if v],
    }

    # Attempt to load the job (many DB helpers are synchronous)
    try:
        job = cosmos_db.get_job_by_id(job_id)
    except Exception:
        job = None

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Owner shortcut
    if job.get("user_id") == current_user.get("id"):
        return current_user

    # Admin by explicit level
    if current_user.get("permission") == PermissionLevel.ADMIN.value:
        return current_user

    # Effective capabilities (base + custom) may grant all-jobs rights
    base_caps = get_user_capabilities(current_user.get("permission"))
    effective = merge_custom_capabilities(base_caps, current_user.get("custom_capabilities", {}))
    if any(effective.get(cap, False) for cap in (
        PermissionCapability.CAN_VIEW_ALL_JOBS.value,
        PermissionCapability.CAN_EDIT_ALL_JOBS.value,
        PermissionCapability.CAN_DELETE_ALL_JOBS.value,
        PermissionCapability.CAN_SHARE_JOBS.value,
    )):
        return current_user

    # Deny and audit
    await audit_logger.log_access_denied(
        user_id=current_user.get("id"),
        resource_type="job",
        resource_id=job_id,
        event_type=AuditEventType.ACCESS_DENIED,
    )

    raise HTTPException(status_code=403, detail="Owner or admin access required for this job")


# Job-scoped capability dependency factory
def require_job_capability(capability: PermissionCapability):
    """Return a dependency that loads the job and ensures the current user has the given capability for that job.

    The dependency returns the loaded job dict on success. It will raise 404 if job missing, 403 if unauthorized.
    """
    async def dependency(job_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)

        # Load user and job
        user = await cosmos_db.get_user_by_id(user_id)
        try:
            job = cosmos_db.get_job_by_id(job_id)
        except Exception:
            job = None

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # Owner passes
        if job.get("user_id") == user_id:
            return job

        # Admin passes
        if user and user.get("permission") == PermissionLevel.ADMIN.value:
            return job

        # Otherwise use consolidated check
        if user and user_has_capability_for_job(user, job, capability.value):
            return job

        await audit_logger.log_access_denied(
            user_id=user_id,
            resource_type="job",
            resource_id=job_id,
            event_type=AuditEventType.ACCESS_DENIED,
        )
        raise HTTPException(status_code=403, detail=f"Required capability: {capability.value}")

    return dependency


# Convenience job-level dependencies
require_job_view = require_job_capability(PermissionCapability.CAN_VIEW_OWN_JOBS)
require_job_edit = require_job_capability(PermissionCapability.CAN_EDIT_OWN_JOBS)
require_job_download = require_job_capability(PermissionCapability.CAN_DOWNLOAD_FILES)
require_job_export = require_job_capability(PermissionCapability.CAN_EXPORT_DATA)

# User context dependencies
async def get_current_user(user_id: str = Depends(get_current_user_id)) -> dict:
    """Get full user context including permissions.

    Returns a normalized dictionary with:
      id: user id
      permission: primary permission level
      custom_capabilities: overrides map
      capabilities: flattened list of enabled capability strings
    """
    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)
    user = await cosmos_db.get_user_by_id(user_id)
    if not user:
        # This should rarely happen since get_current_user_id already validated the token.
        return {"id": user_id, "permission": None, "custom_capabilities": {}, "capabilities": []}

    permission = user.get("permission")
    custom_capabilities = user.get("custom_capabilities", {})
    effective = get_user_capabilities(permission, custom_capabilities)
    return {
        "id": user_id,
        "permission": permission,
        "custom_capabilities": custom_capabilities,
        "capabilities": [k for k, v in effective.items() if v]
    }


async def get_effective_capabilities(user_id: str = Depends(get_current_user_id)) -> dict:
    """Return the merged effective capabilities (base + custom) for the current user.

    Use this in list endpoints where handlers need the capability map to build queries or annotations.
    """
    config = get_app_config()
    cosmos_db = get_cosmos_db_cached(config)
    user = await cosmos_db.get_user_by_id(user_id)
    permission = user.get("permission") if user else None
    custom_capabilities = user.get("custom_capabilities", {}) if user else {}
    base_caps = get_user_capabilities(permission)
    effective = merge_custom_capabilities(base_caps, custom_capabilities)
    return effective

__all__ = [
    "get_current_user",
    "get_current_user_id",
    "require_admin",
    "require_editor",
    "require_user",
    "require_capability",
    "require_any_capability",
    "require_analytics_access",
    "require_prompt_management",
    "require_job_upload",
    "require_job_management",
    "get_effective_capabilities",
]
