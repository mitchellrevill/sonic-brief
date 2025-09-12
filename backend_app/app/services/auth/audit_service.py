"""
Audit Service for managing security and compliance audit logs

This service is separate from user session tracking and focuses on:
- Security events (login, logout, permission changes)
- Administrative actions (user management, system changes)
- Compliance-related activities (data access, sharing)
- System security monitoring

Session tracking is now handled by SessionTrackingMiddleware.
"""

import logging
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from app.utils.logging_config import get_logger


class AuditService:
    """Service for managing audit logs and compliance tracking"""
    
    def __init__(self, cosmos_db):
        self.cosmos_db = cosmos_db
        self.logger = get_logger(__name__)
        
        # Check if audit container is available
        if hasattr(cosmos_db, 'audit_container') and cosmos_db.audit_container is not None:
            self.logger.info("✓ Audit container is available")
            self._audit_container_available = True
        else:
            self.logger.warning("⚠️ Audit container not available - using sessions container for audit trail")
            self._audit_container_available = False
            
        # Check if sessions container is available as fallback
        if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container is not None:
            self.logger.info("✓ Sessions container is available for audit trail fallback")
            self._sessions_container_available = True
        else:
            self.logger.error("❌ Sessions container not available - audit trail will not work")
            self._sessions_container_available = False
    
    async def log_security_event(
        self,
        event_type: str,
        user_id: str,
        event_details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Log a security-related audit event
        
        Args:
            event_type: Type of security event (e.g., 'login_success', 'login_failed', 'permission_escalation')
            user_id: ID of the user performing the action
            event_details: Details specific to the security event
            ip_address: User's IP address
            user_agent: User's browser/client information
            
        Returns:
            Audit event ID
        """
        return await self.log_audit_event(
            event_type=event_type,
            user_id=user_id,
            resource_type="security",
            resource_id=None,
            details={
                **event_details,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "security_classification": "high"
            }
        )
    
    async def log_administrative_action(
        self,
        action_type: str,
        admin_user_id: str,
        target_resource_type: str,
        target_resource_id: str,
        action_details: Dict[str, Any]
    ) -> str:
        """
        Log an administrative action for compliance
        
        Args:
            action_type: Type of admin action (e.g., 'user_created', 'permission_granted', 'data_exported')
            admin_user_id: ID of the admin performing the action
            target_resource_type: Type of resource being modified
            target_resource_id: ID of the resource being modified
            action_details: Details about the action
            
        Returns:
            Audit event ID
        """
        return await self.log_audit_event(
            event_type=action_type,
            user_id=admin_user_id,
            resource_type=target_resource_type,
            resource_id=target_resource_id,
            details={
                **action_details,
                "administrative_action": True,
                "compliance_required": True
            }
        )
    
    async def log_data_access_event(
        self,
        access_type: str,
        user_id: str,
        data_type: str,
        data_id: str,
        access_details: Dict[str, Any]
    ) -> str:
        """
        Log data access for compliance and security monitoring
        
        Args:
            access_type: Type of access (e.g., 'view', 'download', 'share', 'delete')
            user_id: ID of the user accessing data
            data_type: Type of data being accessed
            data_id: ID of the specific data
            access_details: Details about the access
            
        Returns:
            Audit event ID
        """
        return await self.log_audit_event(
            event_type=f"data_{access_type}",
            user_id=user_id,
            resource_type=data_type,
            resource_id=data_id,
            details={
                **access_details,
                "data_access_event": True,
                "requires_retention": True
            }
        )
    
    async def log_audit_event(
        self,
        event_type: str,
        user_id: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event (e.g., 'session_start', 'login', 'job_created')
            user_id: ID of the user performing the action
            resource_type: Type of resource affected (e.g., 'job', 'user')
            resource_id: ID of the resource affected
            details: Additional event details
            
        Returns:
            Audit event ID
        """
        try:
            audit_event_id = str(uuid.uuid4())
            
            audit_event = {
                "id": audit_event_id,
                "type": "audit",
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details or {},
                "partition_key": user_id
            }
            
            # Use audit container if available, otherwise use sessions container
            if self._audit_container_available:
                container = self.cosmos_db.audit_container
                container_name = "audit_container"
            elif self._sessions_container_available:
                container = self.cosmos_db.sessions_container
                container_name = "sessions_container"
            else:
                raise Exception("No container available for audit logging")
            
            self.logger.info(f"📝 Storing audit event in {container_name}...")
            try:
                # Run the synchronous SDK call in a thread to avoid blocking the event loop
                await asyncio.to_thread(container.create_item, body=audit_event)
                self.logger.info(f"✅ Audit event stored: {event_type} for user {user_id}")
            except Exception:
                # Log full exception with stack trace and re-raise for visibility
                self.logger.exception(f"Failed to store audit event in {container_name}")
                raise
            
            return audit_event_id
            
        except Exception as e:
            # Ensure any error is fully logged with stack trace to aid debugging
            self.logger.exception(f"❌ Error logging audit event: {str(e)}")
            raise Exception(f"Audit logging failed: {str(e)}")
    
    async def get_user_audit_logs(
        self,
        user_id: str,
        days: int = 30,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for a specific user
        
        Args:
            user_id: User ID to get logs for
            days: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()
            
            # Try audit container first, then sessions container
            containers_to_try = []
            if self._audit_container_available:
                containers_to_try.append((self.cosmos_db.audit_container, "audit"))
            if self._sessions_container_available:
                containers_to_try.append((self.cosmos_db.sessions_container, "sessions"))
            
            all_records = []
            
            for container, container_type in containers_to_try:
                try:
                    # Query for audit events and session events
                    if container_type == "audit":
                        query = """
                        SELECT c.id, c.event_type, c.timestamp, c.resource_type, c.resource_id, c.details
                        FROM c 
                        WHERE c.user_id = @user_id 
                        AND c.timestamp >= @cutoff_date
                        AND c.type = 'audit'
                        ORDER BY c.timestamp DESC
                        """
                    else:  # sessions container
                        query = """
                        SELECT c.id, c.event_type, c.timestamp, 'session' as resource_type, c.id as resource_id, c.metadata as details
                        FROM c 
                        WHERE c.user_id = @user_id 
                        AND c.timestamp >= @cutoff_date
                        AND c.type = 'session'
                        ORDER BY c.timestamp DESC
                        """
                    
                    parameters = [
                        {"name": "@user_id", "value": user_id},
                        {"name": "@cutoff_date", "value": cutoff_iso}
                    ]
                    
                    items = list(container.query_items(
                        query=query,
                        parameters=parameters,
                        enable_cross_partition_query=True
                    ))
                    
                    all_records.extend(items)
                    
                except Exception as e:
                    self.logger.warning(f"Error querying {container_type} container: {str(e)}")
                    continue
            
            # Sort by timestamp and limit
            all_records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return all_records[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting user audit logs: {str(e)}")
            return []
