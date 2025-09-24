"""
Audit Logging Service - Dedicated service for security audit logging

This service handles ONLY audit-related operations:
- Creating audit log entries
- Determining which endpoints should be audited
- Resolving user identifiers for audit trails

Session tracking is handled by SessionTrackingService.
"""

import logging
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.dependencies import CosmosService

from ...core.async_utils import run_sync
from ...utils.logging_config import get_logger
from ...config.audit_config import AUDIT_ENDPOINTS, METHOD_SPECIFIC_AUDIT_ENDPOINTS, SENSITIVE_ENDPOINTS


class AuditLoggingService:
    """
    Dedicated service for security audit logging.
    
    Responsibilities:
    - Create audit log entries for security events
    - Determine which endpoints should be audited
    - Resolve user identifiers
    
    NOT responsible for:
    - Session lifecycle management (handled by SessionTrackingService)
    - JWT parsing (handled by AuthenticationService)
    """
    
    def __init__(self, cosmos_service: "CosmosService"):
        self._cosmos = cosmos_service
        self.logger = get_logger(__name__)

    async def create_audit_log(
        self,
        user_id: str,
        user_email: Optional[str],
        event_type: str,
        endpoint: str,
        method: str,
        ip_address: str = "",
        user_agent: str = "",
        user_permission: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Create an audit log entry for security events.
        
        Args:
            user_id: User identifier
            user_email: User email address
            event_type: Type of event being audited
            endpoint: API endpoint path
            method: HTTP method
            ip_address: Client IP address
            user_agent: Browser/client user agent
            user_permission: User's permission level
            resource_type: Type of resource being accessed
            resource_id: Specific resource identifier
            metadata: Additional event metadata
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            Audit log ID if successful, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        try:
            # Use audit container if available, otherwise sessions container as fallback
            container = None
            if hasattr(self._cosmos, 'audit_container') and self._cosmos.audit_container:
                container = self._cosmos.audit_container
            elif hasattr(self._cosmos, 'sessions_container') and self._cosmos.sessions_container:
                container = self._cosmos.sessions_container
            else:
                self.logger.debug("No suitable container available for audit logging")
                return None
            
            audit_id = str(uuid.uuid4())
            audit_item = {
                "id": audit_id,
                "type": "audit_log",
                "user_id": user_id,
                "user_email": user_email or user_id,
                "event_type": event_type,
                "endpoint": endpoint,
                "method": method,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "user_permission": user_permission,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "metadata": metadata or {},
                "timestamp": timestamp.isoformat(),
                "created_at": timestamp.isoformat()
            }
            
            await run_sync(lambda: container.upsert_item(audit_item))
            self.logger.info(f"Created audit log {audit_id} for {event_type} by user {user_id}")
            return audit_id
            
        except Exception as e:
            self.logger.error(f"Failed to create audit log for {event_type}: {str(e)}")
            return None

    async def log_user_activity(
        self,
        user_id: str,
        session_id: str,
        action: str,
        resource: str,
        ip_address: str,
        user_agent: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log user activity for session tracking and audit purposes.
        
        Args:
            user_id: User identifier
            session_id: Session identifier 
            action: Action performed (e.g., "request", "login", "logout")
            resource: Resource accessed (e.g., endpoint path)
            ip_address: User's IP address
            user_agent: User's browser/client user agent
            additional_context: Extra metadata for the activity
            
        Returns:
            Audit log ID if successful, None if failed
        """
        try:
            # Get the HTTP method from additional context
            method = additional_context.get("method", "GET") if additional_context else "GET"
            
            # Determine if this should be audited
            if not self.is_audit_endpoint(resource, method):
                self.logger.debug(f"Skipping audit for non-audited endpoint: {resource} {method}")
                return None
            
            # Get event type based on resource and action
            event_type = self.determine_audit_event_type(resource, method)
            
            # Create audit log entry
            metadata = {
                "session_id": session_id,
                "action": action,
                "resource": resource,
                **(additional_context or {})
            }
            
            audit_id = await self.create_audit_log(
                user_id=user_id,
                user_email=None,  # Will be resolved in create_audit_log if needed
                event_type=event_type,
                endpoint=resource,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata
            )
            
            return audit_id
            
        except Exception as e:
            self.logger.error(f"Failed to log user activity for user {user_id}: {str(e)}")
            return None

    def is_audit_endpoint(self, path: str, method: str = "GET") -> bool:
        """
        Check if an endpoint should be audited.
        
        Args:
            path: API endpoint path
            method: HTTP method
            
        Returns:
            True if endpoint should be audited, False otherwise
        """
        # Check method-specific endpoints first
        for (endpoint_path, endpoint_method), event_type in METHOD_SPECIFIC_AUDIT_ENDPOINTS.items():
            if method.upper() == endpoint_method.upper() and self._matches_pattern(path, endpoint_path):
                return True
        
        # Direct match (method-agnostic)
        if path in AUDIT_ENDPOINTS:
            return True
        
        # Pattern matching for method-agnostic endpoints
        for pattern in AUDIT_ENDPOINTS.keys():
            if self._matches_pattern(path, pattern):
                return True
                
        return False

    def determine_audit_event_type(self, path: str, method: str) -> str:
        """
        Determine the audit event type for a given path and method.
        
        Args:
            path: API endpoint path
            method: HTTP method
            
        Returns:
            Event type string for audit logging
        """
        # Check method-specific endpoints first
        for (endpoint_path, endpoint_method), event_type in METHOD_SPECIFIC_AUDIT_ENDPOINTS.items():
            if method.upper() == endpoint_method.upper() and self._matches_pattern(path, endpoint_path):
                return event_type
        
        # Direct match (method-agnostic)
        if path in AUDIT_ENDPOINTS:
            return AUDIT_ENDPOINTS[path]
        
        # Pattern matching for method-agnostic endpoints
        for endpoint_pattern, event_type in AUDIT_ENDPOINTS.items():
            if self._matches_pattern(path, endpoint_pattern):
                return event_type
        
        # Fallback based on method and path (should rarely be used now)
        if method.upper() == 'POST':
            return 'resource_created'
        elif method.upper() == 'DELETE':
            return 'resource_deleted'
        elif method.upper() in ['PUT', 'PATCH']:
            return 'resource_modified'
        else:
            return 'resource_accessed'

    def is_sensitive_endpoint(self, path: str) -> bool:
        """
        Check if an endpoint is sensitive and needs detailed logging.
        
        Args:
            path: API endpoint path
            
        Returns:
            True if endpoint is sensitive, False otherwise
        """
        for sensitive_path in SENSITIVE_ENDPOINTS:
            if path.startswith(sensitive_path):
                return True
        return False

    async def resolve_canonical_id(self, email: str) -> Optional[str]:
        """
        Resolve email address to canonical user GUID.
        
        Args:
            email: User email address
            
        Returns:
            GUID string if found, None otherwise
        """
        if not hasattr(self._cosmos, 'auth_container') or self._cosmos.auth_container is None:
            self.logger.debug("Auth container not available for canonical id resolution")
            return None
            
        try:
            auth_query = "SELECT TOP 1 c.id FROM c WHERE c.email = @email"
            auth_params = [{"name": "@email", "value": email}]
            
            results = await run_sync(lambda: list(self._cosmos.auth_container.query_items(
                query=auth_query,
                parameters=auth_params,
                enable_cross_partition_query=True
            )))
            
            if results:
                return results[0]["id"]
            return None
            
        except Exception as e:
            self.logger.debug(f"Error resolving canonical ID for {email}: {str(e)}")
            return None

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if a path matches a pattern (supports wildcards).
        
        Args:
            path: Actual API path
            pattern: Pattern with potential wildcards (*)
            
        Returns:
            True if path matches pattern, False otherwise
        """
        if '*' not in pattern:
            return path == pattern
        
        # Convert pattern to regex
        regex_pattern = pattern.replace('*', '[^/]*')
        regex_pattern = f"^{regex_pattern}$"
        
        try:
            return bool(re.match(regex_pattern, path))
        except Exception:
            return False

    async def log_audit_completion(
        self,
        user_id: str,
        user_email: Optional[str],
        endpoint: str,
        method: str,
        status_code: int,
        ip_address: str = "",
        user_agent: str = "",
        processing_time_ms: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Log completion of audit-worthy operations.
        
        Args:
            user_id: User identifier
            user_email: User email address
            endpoint: API endpoint path
            method: HTTP method
            status_code: HTTP response status code
            ip_address: Client IP address
            user_agent: Browser/client user agent
            processing_time_ms: Request processing time in milliseconds
            timestamp: Completion timestamp (defaults to now)
            
        Returns:
            Audit log ID if successful, None otherwise
        """
        event_type = f"{self.determine_audit_event_type(endpoint, method)}_completed"
        
        metadata = {
            "status_code": status_code,
            "processing_time_ms": processing_time_ms,
            "completion": True
        }
        
        return await self.create_audit_log(
            user_id=user_id,
            user_email=user_email,
            event_type=event_type,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            timestamp=timestamp
        )

    async def log_login_event(
        self,
        user_id: str,
        user_email: str,
        login_method: str,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        failure_reason: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log user login attempt (successful or failed).
        
        Args:
            user_id: User identifier
            user_email: User email address
            login_method: Login method (e.g., "jwt", "oauth", "api_key")
            ip_address: User's IP address
            user_agent: User's browser/client user agent
            success: Whether login was successful
            failure_reason: Reason for failure if unsuccessful
            additional_metadata: Extra metadata for the login event
            
        Returns:
            Audit log ID if successful, None if failed
        """
        event_type = "user_login_success" if success else "user_login_failure"
        
        metadata = {
            "login_method": login_method,
            "success": success,
            **(additional_metadata or {})
        }
        
        if not success and failure_reason:
            metadata["failure_reason"] = failure_reason
        
        return await self.create_audit_log(
            user_id=user_id,
            user_email=user_email,
            event_type=event_type,
            endpoint="/api/auth/login",
            method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )

    async def log_permission_change(
        self,
        admin_user_id: str,
        admin_user_email: str,
        target_user_id: str,
        target_user_email: str,
        old_permission: str,
        new_permission: str,
        ip_address: str,
        user_agent: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log permission change event.
        
        Args:
            admin_user_id: ID of admin making the change
            admin_user_email: Email of admin making the change
            target_user_id: ID of user whose permissions are being changed
            target_user_email: Email of user whose permissions are being changed
            old_permission: Previous permission level
            new_permission: New permission level
            ip_address: Admin's IP address
            user_agent: Admin's browser/client user agent
            additional_metadata: Extra metadata for the permission change
            
        Returns:
            Audit log ID if successful, None if failed
        """
        metadata = {
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "old_permission": old_permission,
            "new_permission": new_permission,
            "action": "permission_change",
            **(additional_metadata or {})
        }
        
        return await self.create_audit_log(
            user_id=admin_user_id,
            user_email=admin_user_email,
            event_type="permission_change",
            endpoint="/api/admin/users/permissions",
            method="PATCH",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )

    async def log_new_user_creation(
        self,
        admin_user_id: str,
        admin_user_email: str,
        new_user_id: str,
        new_user_email: str,
        new_user_permission: str,
        creation_method: str,
        ip_address: str,
        user_agent: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Log new user creation event.
        
        Args:
            admin_user_id: ID of admin creating the user (can be same as new_user_id for self-registration)
            admin_user_email: Email of admin creating the user
            new_user_id: ID of newly created user
            new_user_email: Email of newly created user
            new_user_permission: Permission level assigned to new user
            creation_method: How user was created (e.g., "admin_portal", "self_registration", "api")
            ip_address: IP address of requester
            user_agent: Browser/client user agent
            additional_metadata: Extra metadata for user creation
            
        Returns:
            Audit log ID if successful, None if failed
        """
        metadata = {
            "new_user_id": new_user_id,
            "new_user_email": new_user_email,
            "new_user_permission": new_user_permission,
            "creation_method": creation_method,
            "action": "user_creation",
            **(additional_metadata or {})
        }
        
        return await self.create_audit_log(
            user_id=admin_user_id,
            user_email=admin_user_email,
            event_type="user_creation",
            endpoint="/api/admin/users",
            method="POST",
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )