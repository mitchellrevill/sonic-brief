from enum import Enum
from typing import Dict, Any
from typing import List

class PermissionLevel(str, Enum):
    """Permission levels in hierarchical order"""
    USER = "User"
    EDITOR = "Editor"
    ADMIN = "Admin"

# Permission hierarchy (higher number = more permissions)
PERMISSION_HIERARCHY = {
    PermissionLevel.USER.value: 1,    # "User": 1
    PermissionLevel.EDITOR.value: 2,  # "Editor": 2
    PermissionLevel.ADMIN.value: 3,   # "Admin": 3
}

def get_permission_level(permission_string: str) -> int:
    """
    Get the numeric level for a permission string.
    
    Args:
        permission_string: The permission level as a string (e.g., 'Admin', 'Editor', 'User')
    
    Returns:
        int: The numeric permission level (1-3), or 0 if invalid
    """
    return PERMISSION_HIERARCHY.get(permission_string, 0)

def has_permission_level(user_permission: str, required_permission: str) -> bool:
    """
    Check if a user has the required permission level or higher.
    
    Args:
        user_permission: The user's permission level string
        required_permission: The required permission level string
    
    Returns:
        bool: True if user has sufficient permissions, False otherwise
    """
    user_level = get_permission_level(user_permission)
    required_level = get_permission_level(required_permission)
    return user_level >= required_level


# Default capability lists (keep concise; frontend files enumerate expected keys)
DEFAULT_CAPABILITIES: Dict[str, List[str]] = {
    PermissionLevel.USER.value: [
        "can_view_prompts",
        "can_create_prompts",
        "can_upload_files",
    ],
    PermissionLevel.EDITOR.value: [
        "can_view_prompts",
        "can_create_prompts",
        "can_edit_prompts",
        "can_upload_files",
        "can_download_files",
    ],
    PermissionLevel.ADMIN.value: [
        # Admin gets every known capability; callers may convert this to full map
    ],
}


def capabilities_for_permission(permission: str, all_capabilities: List[str]) -> Dict[str, bool]:
    """Return a mapping of capability -> bool for a given permission level.

    - Admin: all capabilities True
    - Editor: defaults from DEFAULT_CAPABILITIES[Editor]
    - User: defaults from DEFAULT_CAPABILITIES[User]
    """
    if permission == PermissionLevel.ADMIN.value:
        return {cap: True for cap in all_capabilities}

    enabled = set(DEFAULT_CAPABILITIES.get(permission, []))
    return {cap: (cap in enabled) for cap in all_capabilities}


# --- Backwards compatibility: PermissionCapability enum and helpers ---
class PermissionCapability(str, Enum):
    CAN_VIEW_OWN_JOBS = "can_view_own_jobs"
    CAN_CREATE_JOBS = "can_create_jobs"
    CAN_EDIT_OWN_JOBS = "can_edit_own_jobs"
    CAN_DELETE_OWN_JOBS = "can_delete_own_jobs"
    CAN_VIEW_SHARED_JOBS = "can_view_shared_jobs"
    CAN_EDIT_SHARED_JOBS = "can_edit_shared_jobs"
    CAN_DELETE_SHARED_JOBS = "can_delete_shared_jobs"
    CAN_SHARE_JOBS = "can_share_jobs"
    CAN_VIEW_ALL_JOBS = "can_view_all_jobs"
    CAN_EDIT_ALL_JOBS = "can_edit_all_jobs"
    CAN_DELETE_ALL_JOBS = "can_delete_all_jobs"
    CAN_VIEW_PROMPTS = "can_view_prompts"
    CAN_CREATE_PROMPTS = "can_create_prompts"
    CAN_EDIT_PROMPTS = "can_edit_prompts"
    CAN_DELETE_PROMPTS = "can_delete_prompts"
    CAN_CREATE_TEMPLATES = "can_create_templates"
    CAN_VIEW_USERS = "can_view_users"
    CAN_CREATE_USERS = "can_create_users"
    CAN_EDIT_USERS = "can_edit_users"
    CAN_DELETE_USERS = "can_delete_users"
    CAN_MANAGE_USERS = "can_manage_users"
    CAN_VIEW_SETTINGS = "can_view_settings"
    CAN_EDIT_SETTINGS = "can_edit_settings"
    CAN_VIEW_ANALYTICS = "can_view_analytics"
    CAN_MANAGE_SYSTEM = "can_manage_system"
    CAN_UPLOAD_FILES = "can_upload_files"
    CAN_DOWNLOAD_FILES = "can_download_files"
    CAN_EXPORT_DATA = "can_export_data"
    CAN_IMPORT_DATA = "can_import_data"


def get_user_capabilities(user_permission: str, custom_capabilities: Dict[str, Any]) -> Dict[str, bool]:
    """Return effective capability mapping (base + custom) for a user."""
    # Build all capability keys from PermissionCapability
    all_caps = [c.value for c in PermissionCapability]
    base = capabilities_for_permission(user_permission, all_caps)
    # Merge custom capabilities (override)
    for k, v in (custom_capabilities or {}).items():
        if k in base:
            base[k] = bool(v)
        else:
            base[k] = bool(v)
    return base


def merge_custom_capabilities(base_caps: Dict[str, bool], custom_caps: Dict[str, Any]) -> Dict[str, bool]:
    """Merge custom capability flags into base capability map."""
    merged = base_caps.copy()
    for k, v in (custom_caps or {}).items():
        merged[k] = bool(v)
    return merged
