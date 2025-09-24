"""
Audit Configuration - Central definition of audit endpoints and rules

This module defines which endpoints should be audited and their corresponding event types.
Having this in one place eliminates duplicate code and ensures consistency.
"""

from typing import Dict, Set

# Endpoints that should create audit logs (ONLY security-critical actions)
# Format: (path, method) -> event_type or path -> event_type for all methods
AUDIT_ENDPOINTS: Dict[str, str] = {
    # Authentication events
    '/api/auth/login': 'user_login',
    '/api/auth/logout': 'user_logout',
    
    # Password changes
    '/api/auth/change-password': 'password_change',
    '/api/auth/users/*/password': 'password_change',
    
    # Permission and capability changes (CRITICAL)
    '/api/auth/users/*/permission': 'permission_change',
    '/api/auth/users/*/capabilities': 'capability_change',
    '/api/auth/permissions/grant': 'permission_grant',
    '/api/auth/permissions/revoke': 'permission_revoke',
    
    # User management (creating/deleting users) - distinguish by method
    '/api/auth/register': 'user_registered',
    '/api/auth/users/*/delete': 'user_deleted',
    
    # Job sharing (security-relevant as it affects access control)
    '/api/jobs/*/share': 'job_shared',
    '/api/jobs/*/unshare': 'job_unshared',
    
    # System administration (high-privilege actions)
    '/api/admin/*': 'admin_action',
    '/api/system/*': 'system_action',
}

# Method-specific audit endpoints: (path, method) -> event_type
METHOD_SPECIFIC_AUDIT_ENDPOINTS = {
    ('/api/auth/users', 'POST'): 'user_created',  # Only POST to create user should be audited
    ('/api/auth/users/*', 'DELETE'): 'user_deleted',  # DELETE to delete specific user
}

# Endpoints that are sensitive and need detailed logging
SENSITIVE_ENDPOINTS: Set[str] = {
    '/api/auth/permissions',
    '/api/admin'
}

# Session configuration
DEFAULT_SESSION_TIMEOUT_MINUTES = 15
DEFAULT_HEARTBEAT_INTERVAL_MINUTES = 5