from enum import Enum
from typing import Dict, Any

class PermissionLevel(str, Enum):
    """Permission levels in hierarchical order"""
    USER = "User"
    EDITOR = "Editor"
    ADMIN = "Admin"

class PermissionCapability(str, Enum):
    """Available permission capabilities for all resources and features"""
    # Job/Transcription Management
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
    # Prompt/Template Management
    CAN_VIEW_PROMPTS = "can_view_prompts"
    CAN_CREATE_PROMPTS = "can_create_prompts"
    CAN_EDIT_PROMPTS = "can_edit_prompts"
    CAN_DELETE_PROMPTS = "can_delete_prompts"
    CAN_CREATE_TEMPLATES = "can_create_templates"
    # User Management
    CAN_VIEW_USERS = "can_view_users"
    CAN_CREATE_USERS = "can_create_users"
    CAN_EDIT_USERS = "can_edit_users"
    CAN_DELETE_USERS = "can_delete_users"
    CAN_MANAGE_USERS = "can_manage_users"
    # System/Settings
    CAN_VIEW_SETTINGS = "can_view_settings"
    CAN_EDIT_SETTINGS = "can_edit_settings"
    CAN_VIEW_ANALYTICS = "can_view_analytics"
    CAN_MANAGE_SYSTEM = "can_manage_system"
    # File Operations
    CAN_UPLOAD_FILES = "can_upload_files"
    CAN_DOWNLOAD_FILES = "can_download_files"
    CAN_EXPORT_DATA = "can_export_data"
    CAN_IMPORT_DATA = "can_import_data"

# Permission hierarchy (higher number = more permissions)
PERMISSION_HIERARCHY = {
    PermissionLevel.USER: 1,
    PermissionLevel.EDITOR: 2,
    PermissionLevel.ADMIN: 3,
}

# Permission capabilities for each level
# (Expand as needed for your app's features)
def _perm_caps() -> Dict[PermissionLevel, Dict[str, bool]]:
    return {
        PermissionLevel.USER: {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
            PermissionCapability.CAN_CREATE_JOBS: True,
            PermissionCapability.CAN_EDIT_OWN_JOBS: True,
            PermissionCapability.CAN_DELETE_OWN_JOBS: True,
            PermissionCapability.CAN_VIEW_SHARED_JOBS: True,
            PermissionCapability.CAN_VIEW_PROMPTS: True,
            PermissionCapability.CAN_VIEW_SETTINGS: True,
            PermissionCapability.CAN_UPLOAD_FILES: True,
            PermissionCapability.CAN_DOWNLOAD_FILES: True,
        },
        PermissionLevel.EDITOR: {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
            PermissionCapability.CAN_CREATE_JOBS: True,
            PermissionCapability.CAN_EDIT_OWN_JOBS: True,
            PermissionCapability.CAN_DELETE_OWN_JOBS: True,
            PermissionCapability.CAN_VIEW_SHARED_JOBS: True,
            PermissionCapability.CAN_EDIT_SHARED_JOBS: True,
            PermissionCapability.CAN_DELETE_SHARED_JOBS: True,
            PermissionCapability.CAN_SHARE_JOBS: True,
            PermissionCapability.CAN_VIEW_PROMPTS: True,
            PermissionCapability.CAN_CREATE_PROMPTS: True,
            PermissionCapability.CAN_EDIT_PROMPTS: True,
            PermissionCapability.CAN_CREATE_TEMPLATES: True,
            PermissionCapability.CAN_VIEW_SETTINGS: True,
            PermissionCapability.CAN_EDIT_SETTINGS: True,
            PermissionCapability.CAN_UPLOAD_FILES: True,
            PermissionCapability.CAN_DOWNLOAD_FILES: True,
            PermissionCapability.CAN_EXPORT_DATA: True,
        },
        PermissionLevel.ADMIN: {
            # All capabilities enabled
            **{cap.value: True for cap in PermissionCapability}
        },
    }

PERMISSION_CAPABILITIES = _perm_caps()

# Utility functions for permission checking
def can_user_perform_action(user_permission: str, capability: str) -> bool:
    """
    Check if a user with the given permission level can perform a specific action.
    
    Args:
        user_permission: The user's permission level (e.g., 'Admin', 'Editor', 'User')
        capability: The capability to check (e.g., 'can_manage_users')
    
    Returns:
        bool: True if the user can perform the action, False otherwise
    """
    if not user_permission or user_permission not in PERMISSION_CAPABILITIES:
        return False
    return PERMISSION_CAPABILITIES[user_permission].get(capability, False)

def get_user_capabilities(user_permission: str) -> Dict[str, bool]:
    """
    Get all capabilities for a user's permission level.
    
    Args:
        user_permission: The user's permission level
    
    Returns:
        Dict[str, bool]: Dictionary of capabilities and their allowed status
    """
    if not user_permission or user_permission not in PERMISSION_CAPABILITIES:
        return PERMISSION_CAPABILITIES[PermissionLevel.USER]
    return PERMISSION_CAPABILITIES[user_permission]

def merge_custom_capabilities(base_capabilities: Dict[str, bool], custom_capabilities: Dict[str, bool] = None) -> Dict[str, bool]:
    """
    Merge custom capabilities with base capabilities.
    Custom capabilities can override base capabilities.
    
    Args:
        base_capabilities: Base capabilities from permission level
        custom_capabilities: Custom capabilities to override/add
    
    Returns:
        Dict[str, bool]: Merged capabilities
    """
    if not custom_capabilities:
        return base_capabilities
    
    merged = base_capabilities.copy()
    merged.update(custom_capabilities)
    return merged

def validate_capability_data(capability_data: Dict[str, bool]) -> bool:
    """
    Validate that capability data contains only valid capabilities with boolean values.
    
    Args:
        capability_data: Dictionary of capability -> boolean mappings
        
    Returns:
        True if all capabilities are valid, False otherwise
    """
    if not isinstance(capability_data, dict):
        return False
    
    valid_capabilities = set(cap.value for cap in PermissionCapability)
    
    for capability, value in capability_data.items():
        if capability not in valid_capabilities:
            return False
        if not isinstance(value, bool):
            return False
    
    return True
