"""
Audit logging utilities for permission changes and access denials
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class AuditEventType(str, Enum):
    """Types of audit events"""
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_CHANGED = "permission_changed"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    RESOURCE_SHARED = "resource_shared"
    RESOURCE_UNSHARED = "resource_unshared"

class AuditLogger:
    """
    Handles audit logging for security-sensitive operations
    """
    
    def __init__(self, cosmos_db=None):
        self.cosmos_db = cosmos_db
        self.logger = logging.getLogger(__name__)
    
    async def log_permission_event(
        self, 
        event_type: AuditEventType,
        user_id: str,
        resource_type: str = None,
        resource_id: str = None,
        permission_level: str = None,
        old_permission: str = None,
        new_permission: str = None,
        performed_by: str = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Log a permission-related audit event
        
        Args:
            event_type: Type of audit event
            user_id: ID of the user affected
            resource_type: Type of resource (e.g., 'job', 'user')
            resource_id: ID of the resource
            permission_level: Permission level involved
            old_permission: Previous permission (for changes)
            new_permission: New permission (for changes)
            performed_by: User ID who performed the action
            metadata: Additional metadata
        
        Returns:
            str: Audit log entry ID
        """
        audit_entry = {
            "id": f"audit_{datetime.now(timezone.utc).timestamp()}_{user_id}",
            "type": "audit_log",
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "permission_level": permission_level,
            "old_permission": old_permission,
            "new_permission": new_permission,
            "performed_by": performed_by,
            "metadata": metadata or {}
        }
        
        # Log to console/file logger
        self.logger.info(f"Audit: {event_type} - User: {user_id}, Resource: {resource_type}:{resource_id}")
        
        # Store in database if available
        if self.cosmos_db:
            try:
                # Store in audit container (assuming it exists)
                container = getattr(self.cosmos_db, 'audit_container', None)
                if container:
                    container.create_item(audit_entry)
                else:
                    # Fallback to events container
                    self.cosmos_db.events_container.create_item(audit_entry)
            except Exception as e:
                self.logger.error(f"Failed to store audit log: {str(e)}")
        
        return audit_entry["id"]
    
    async def log_access_denied(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        required_capability: str,
        user_permission: str,
        endpoint: str = None,
        ip_address: str = None
    ) -> str:
        """
        Log an access denied event
        """
        return await self.log_permission_event(
            event_type=AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission_level=user_permission,
            metadata={
                "required_capability": required_capability,
                "endpoint": endpoint,
                "ip_address": ip_address
            }
        )
    
    async def log_permission_change(
        self,
        user_id: str,
        old_permission: str,
        new_permission: str,
        performed_by: str,
        reason: str = None
    ) -> str:
        """
        Log a permission change event
        """
        return await self.log_permission_event(
            event_type=AuditEventType.PERMISSION_CHANGED,
            user_id=user_id,
            resource_type="user",
            resource_id=user_id,
            old_permission=old_permission,
            new_permission=new_permission,
            performed_by=performed_by,
            metadata={"reason": reason} if reason else None
        )

# Global audit logger instance
audit_logger = AuditLogger()

def set_audit_logger_db(cosmos_db):
    """Set the database for the global audit logger"""
    global audit_logger
    audit_logger.cosmos_db = cosmos_db
