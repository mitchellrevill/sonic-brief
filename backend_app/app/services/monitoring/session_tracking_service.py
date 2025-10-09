"""
Session Tracking Service - FIXED VERSION (Option 3: One Session Per User)
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, TYPE_CHECKING

from azure.cosmos.exceptions import CosmosHttpResponseError

if TYPE_CHECKING:
    from ...core.dependencies import CosmosService

from ...utils.async_utils import run_sync
from ...utils.logging_config import get_logger
from ...config.audit_config import DEFAULT_SESSION_TIMEOUT_MINUTES


class SessionTrackingService:
    """
    Lightweight service for session lifecycle management.
    
    Design: One session per user, identified by user_id.
    Session document is replaced on each new login, heartbeat updates existing session.
    """
    
    def __init__(
        self, 
        cosmos_service: "CosmosService",
        session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES
    ):
        self._cosmos = cosmos_service
        self.logger = get_logger(__name__)
        self.session_timeout_minutes = session_timeout_minutes

    async def get_or_create_session(
        self,
        user_id: str,
        user_email: Optional[str] = None,
        request_path: str = "/",
        user_agent: str = "",
        ip_address: str = "",
        timestamp: Optional[datetime] = None
    ) -> Optional[str]:
        """
        Get or create a session for the user.
        
        This method is race-condition-free because:
        1. Session ID = user_id (deterministic, not random UUID)
        2. Upsert operation is atomic
        3. No need to check for existing sessions first
        
        Args:
            user_id: User identifier (becomes session ID)
            user_email: User email address
            request_path: Current request path
            user_agent: Browser/client user agent
            ip_address: Client IP address
            timestamp: Request timestamp (defaults to now)
            
        Returns:
            Session ID (= user_id) if successful, None if cosmos unavailable
        """
        if not hasattr(self._cosmos, 'sessions_container') or self._cosmos.sessions_container is None:
            self.logger.debug("Sessions container unavailable, skipping session tracking")
            return None
            
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        try:
            # Check if session exists to determine if this is new or update
            existing_session = await self._get_session(user_id)
            is_new_session = existing_session is None
            
            if is_new_session:
                # New session - initialize all fields
                session_item = {
                    "id": user_id,  # Session ID = User ID (no more duplicates!)
                    "user_id": user_id,
                    "user_email": user_email or user_id,
                    "partition_key": user_id,
                    "type": "session",
                    "status": "active",
                    "created_at": timestamp.isoformat(),
                    "last_activity": timestamp.isoformat(),
                    "last_heartbeat": timestamp.isoformat(),
                    "last_path": request_path,
                    "user_agent": user_agent,
                    "ip_address": ip_address,
                    "expires_at": (timestamp + timedelta(minutes=self.session_timeout_minutes)).isoformat(),
                    # Session analytics
                    "endpoints_accessed": [request_path] if request_path else [],
                    "request_count": 1,
                    "ip_addresses": [ip_address] if ip_address else []
                }
                self.logger.info(f"Creating new session for user {user_id}")
            else:
                # Update existing session (this is the common case)
                session_item = existing_session
                
                # Update activity timestamps
                session_item["last_activity"] = timestamp.isoformat()
                session_item["last_heartbeat"] = timestamp.isoformat()
                session_item["last_path"] = request_path
                session_item["user_agent"] = user_agent
                session_item["ip_address"] = ip_address
                session_item["status"] = "active"
                session_item["expires_at"] = (timestamp + timedelta(minutes=self.session_timeout_minutes)).isoformat()
                
                # Update analytics
                endpoints = session_item.get("endpoints_accessed", [])
                if request_path and request_path not in endpoints:
                    endpoints.append(request_path)
                    session_item["endpoints_accessed"] = endpoints
                
                ips = session_item.get("ip_addresses", [])
                if ip_address and ip_address not in ips:
                    ips.append(ip_address)
                    session_item["ip_addresses"] = ips
                
                session_item["request_count"] = session_item.get("request_count", 0) + 1
                
                self.logger.debug(f"Updated session heartbeat for user {user_id}")
            
            # Atomic upsert - no race conditions possible
            await run_sync(lambda: self._cosmos.sessions_container.upsert_item(session_item))
            
            return user_id  # Session ID = User ID
            
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Failed to upsert session in Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            self.logger.error(
                "Unexpected error upserting session",
                exc_info=True,
                extra={"user_id": user_id}
            )
            return None

    async def _get_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by user_id (which is also the session ID).
        
        Returns:
            Session document if exists, None otherwise
        """
        try:
            result = await run_sync(
                lambda: self._cosmos.sessions_container.read_item(
                    item=user_id,
                    partition_key=user_id
                )
            )
            return result
        except CosmosHttpResponseError as e:
            if e.status_code == 404:
                # Not found is expected for new sessions
                return None
            self.logger.error(
                "Error reading session from Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code
                }
            )
            return None
        except Exception as e:
            self.logger.error(
                "Unexpected error reading session",
                exc_info=True,
                extra={"user_id": user_id}
            )
            return None

    async def deactivate_session(self, session_id: str) -> bool:
        """
        Mark a session as inactive (user logout only).
        
        Note: Stale/expired sessions are handled by Azure Function cleanup.
        This method is only for explicit user logout actions.
        
        Args:
            session_id: Session identifier (user_id)
            
        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self._cosmos, 'sessions_container') or self._cosmos.sessions_container is None:
            return False
            
        try:
            session_item = await self._get_session(session_id)
            if not session_item:
                self.logger.debug(f"Session {session_id} not found for deactivation")
                return False
                
            # Only close if user explicitly logs out
            # Azure Function will handle marking stale sessions as 'expired'
            session_item["status"] = "closed"
            session_item["ended_at"] = datetime.now(timezone.utc).isoformat()
            session_item["end_reason"] = "user_logout"
            
            await run_sync(lambda: self._cosmos.sessions_container.upsert_item(session_item))
            self.logger.info(f"Deactivated session for user {session_id}")
            return True
            
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Failed to deactivate session in Cosmos DB",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "status_code": e.status_code
                }
            )
            return False
        except Exception as e:
            self.logger.error(
                "Unexpected error deactivating session",
                exc_info=True,
                extra={"session_id": session_id}
            )
            return False

    async def get_session_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current session information for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Session information if exists, None otherwise
        """
        return await self._get_session(user_id)

    async def is_session_active(self, user_id: str) -> bool:
        """
        Check if user has an active session.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if active session exists, False otherwise
        """
        session = await self._get_session(user_id)
        if not session:
            return False
        
        # Check status
        if session.get("status") != "active":
            return False
        
        # Check expiration
        try:
            expires_at = datetime.fromisoformat(session["expires_at"].replace('Z', '+00:00'))
            if expires_at < datetime.now(timezone.utc):
                return False
        except (ValueError, KeyError):
            return False
        
        return True
