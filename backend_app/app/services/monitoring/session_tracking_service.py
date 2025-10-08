"""
Session Tracking Service - Lightweight service for session lifecycle management

This service handles ONLY session-related operations:
- Creating new sessions
- Updating session heartbeats
- Session validation

Audit logging is handled by a separate AuditService.
"""

import logging
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, TYPE_CHECKING

from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

if TYPE_CHECKING:
    from ...core.dependencies import CosmosService

from ...utils.async_utils import run_sync
from ...utils.logging_config import get_logger
from ...config.audit_config import DEFAULT_SESSION_TIMEOUT_MINUTES, DEFAULT_HEARTBEAT_INTERVAL_MINUTES


class SessionTrackingService:
    """
    Lightweight service for session lifecycle management.
    
    Responsibilities:
    - Create new user sessions
    - Update session heartbeats
    - Track session activity
    
    NOT responsible for:
    - Audit logging (handled by AuditService)
    - JWT parsing (handled by AuthenticationService)
    - Memory diagnostics (separate concern)
    """
    
    def __init__(
        self, 
        cosmos_service: "CosmosService",
        session_timeout_minutes: int = DEFAULT_SESSION_TIMEOUT_MINUTES,
        heartbeat_interval_minutes: int = DEFAULT_HEARTBEAT_INTERVAL_MINUTES
    ):
        self._cosmos = cosmos_service
        self.logger = get_logger(__name__)
        self.session_timeout_minutes = session_timeout_minutes
        self.heartbeat_interval_minutes = heartbeat_interval_minutes

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
        Get existing session or create a new one.
        
        Args:
            user_id: User identifier from JWT token
            user_email: User email address
            request_path: Current request path
            user_agent: Browser/client user agent
            ip_address: Client IP address
            timestamp: Request timestamp (defaults to now)
            
        Returns:
            Session ID string if successful, None if cosmos unavailable
        """
        if not hasattr(self._cosmos, 'sessions_container') or self._cosmos.sessions_container is None:
            self.logger.debug("Sessions container unavailable, skipping session creation")
            return None
            
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        try:
            # Look for existing active session
            self.logger.debug(f"Looking for existing session for user {user_id}")
            existing_session_id = await self._find_active_session(user_id, timestamp)
            if existing_session_id:
                # Update existing session
                self.logger.debug(f"Updating existing session {existing_session_id} for user {user_id}")
                updated = await self.update_heartbeat(
                    existing_session_id, user_id, request_path, user_agent, ip_address, timestamp
                )
                if updated:
                    return existing_session_id
                else:
                    self.logger.warning(f"Failed to update existing session {existing_session_id}, creating new one")
            
            # Create new session (first deactivate any old sessions for this user)
            self.logger.debug(f"Creating new session for user {user_id}")
            await self._deactivate_old_sessions(user_id, timestamp)
            
            # Add a small delay to prevent race conditions
            await asyncio.sleep(0.01)
            
            # Check again if a session was created by another concurrent request
            existing_session_id = await self._find_active_session(user_id, timestamp)
            if existing_session_id:
                self.logger.debug(f"Found session created by concurrent request: {existing_session_id}")
                return existing_session_id
            
            session_id = str(uuid.uuid4())
            session_item = {
                "id": session_id,
                "user_id": user_id,
                "user_email": user_email or user_id,
                "partition_key": user_id,  # Required for Azure Function cleanup
                "type": "session",  # Required for Azure Function cleanup
                "status": "active",  # Required for Azure Function cleanup (string, not boolean)
                "created_at": timestamp.isoformat(),
                "last_activity": timestamp.isoformat(),
                "last_heartbeat": timestamp.isoformat(),  # Required for Azure Function cleanup
                "last_path": request_path,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "is_active": True,  # Keep for backward compatibility
                "expires_at": (timestamp + timedelta(minutes=self.session_timeout_minutes)).isoformat(),
                # Enhanced session tracking
                "endpoints_accessed": [request_path] if request_path else [],
                "request_count": 1,
                "ip_addresses": [ip_address] if ip_address else []
            }
            
            await run_sync(lambda: self._cosmos.sessions_container.upsert_item(session_item))
            self.logger.debug(f"Created new session {session_id} for user {user_id}")
            
            # Perform cleanup to remove any duplicate sessions that might have been created concurrently
            await self._cleanup_duplicate_sessions(user_id, session_id, timestamp)
            
            return session_id
            
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Failed to create/get session in Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "user_email": user_email,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            self.logger.error(
                "Unexpected error creating/getting session",
                exc_info=True,
                extra={"user_id": user_id, "user_email": user_email}
            )
            return None

    async def update_heartbeat(
        self,
        session_id: str,
        user_id: str,
        request_path: str = "/",
        user_agent: str = "",
        ip_address: str = "",
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Update session heartbeat and activity.
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            request_path: Current request path
            user_agent: Browser/client user agent
            ip_address: Client IP address
            timestamp: Request timestamp (defaults to now)
            
        Returns:
            True if update successful, False otherwise
        """
        if not hasattr(self._cosmos, 'sessions_container') or self._cosmos.sessions_container is None:
            self.logger.debug("Sessions container unavailable, skipping heartbeat update")
            return False
            
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
            
        try:
            # Query for existing session
            query = "SELECT * FROM c WHERE c.id = @session_id"
            params = [{"name": "@session_id", "value": session_id}]
            
            results = await run_sync(lambda: list(self._cosmos.sessions_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )))
            
            if not results:
                self.logger.debug(f"Session {session_id} not found for heartbeat update")
                return False
                
            session_item = results[0]
            
            # Update endpoint tracking
            endpoints_accessed = session_item.get("endpoints_accessed", [])
            if request_path and request_path not in endpoints_accessed:
                endpoints_accessed.append(request_path)
            
            ip_addresses = session_item.get("ip_addresses", [])
            if ip_address and ip_address not in ip_addresses:
                ip_addresses.append(ip_address)
            
            request_count = session_item.get("request_count", 0) + 1
            
            # Update session with new activity
            session_item.update({
                "last_activity": timestamp.isoformat(),
                "last_heartbeat": timestamp.isoformat(),  # Required for Azure Function cleanup
                "last_path": request_path,
                "user_agent": user_agent,
                "ip_address": ip_address,
                "status": "active",  # Ensure status remains active
                "expires_at": (timestamp + timedelta(minutes=self.session_timeout_minutes)).isoformat(),
                # Enhanced session tracking
                "endpoints_accessed": endpoints_accessed,
                "request_count": request_count,
                "ip_addresses": ip_addresses
            })
            
            await run_sync(lambda: self._cosmos.sessions_container.upsert_item(session_item))
            self.logger.debug(f"Updated heartbeat for session {session_id}")
            return True
            
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Failed to update session heartbeat in Cosmos DB",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return False
        except Exception as e:
            self.logger.error(
                "Unexpected error updating session heartbeat",
                exc_info=True,
                extra={"session_id": session_id, "user_id": user_id}
            )
            return False

    async def _find_active_session(self, user_id: str, current_time: datetime) -> Optional[str]:
        """
        Find an active session for the user.
        
        Args:
            user_id: User identifier
            current_time: Current timestamp
            
        Returns:
            Session ID if found, None otherwise
        """
        try:
            # Look for active sessions that haven't expired
            cutoff_time = current_time - timedelta(minutes=self.session_timeout_minutes)
            
            # Use a more permissive query to find any active sessions for this user
            query = """
                SELECT c.id, c.last_heartbeat, c.created_at FROM c 
                WHERE c.user_id = @user_id 
                AND c.status = 'active'
                AND c.type = 'session'
                ORDER BY c.last_heartbeat DESC
            """
            params = [
                {"name": "@user_id", "value": user_id}
            ]
            
            results = await run_sync(lambda: list(self._cosmos.sessions_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )))
            
            # Filter results in code to handle any timezone issues
            valid_sessions = []
            for session in results:
                try:
                    last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                    if last_heartbeat > cutoff_time:
                        valid_sessions.append(session)
                except (ValueError, KeyError) as e:
                    self.logger.warning(
                        "Error parsing session timestamp",
                        extra={
                            "session_id": session.get("id"),
                            "last_heartbeat": session.get("last_heartbeat"),
                            "error": str(e)
                        }
                    )
                    continue
                except Exception as e:
                    self.logger.error(
                        "Unexpected error parsing session data",
                        exc_info=True,
                        extra={"session_id": session.get("id")}
                    )
                    continue
            
            if valid_sessions:
                # Return the most recently active session
                most_recent = max(valid_sessions, key=lambda s: s["last_heartbeat"])
                self.logger.debug(f"Found existing active session {most_recent['id']} for user {user_id}")
                return most_recent["id"]
            
            self.logger.debug(f"No active sessions found for user {user_id} (found {len(results)} total, {len(valid_sessions)} valid)")
            return None
            
        except CosmosHttpResponseError as e:
            self.logger.warning(
                "Error querying active sessions from Cosmos DB",
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            self.logger.error(
                "Unexpected error finding active session",
                exc_info=True,
                extra={"user_id": user_id}
            )
            return None

    async def _deactivate_old_sessions(self, user_id: str, current_time: datetime) -> None:
        """
        Deactivate any existing active sessions for the user.
        This prevents session duplication when creating new sessions.
        """
        try:
            query = """
                SELECT c.id, c.partition_key FROM c 
                WHERE c.user_id = @user_id 
                AND c.status = 'active'
                AND c.type = 'session'
            """
            params = [{"name": "@user_id", "value": user_id}]
            
            results = await run_sync(lambda: list(self._cosmos.sessions_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )))
            
            for session in results:
                try:
                    # Mark session as closed
                    session["status"] = "closed"
                    session["is_active"] = False
                    session["ended_at"] = current_time.isoformat()
                    session["end_reason"] = "new_session_created"
                    
                    await run_sync(lambda s=session: self._cosmos.sessions_container.upsert_item(s))
                    self.logger.debug(f"Deactivated old session {session['id']} for user {user_id}")
                except CosmosHttpResponseError as e:
                    self.logger.warning(
                        "Failed to deactivate old session in Cosmos DB",
                        extra={
                            "session_id": session.get('id'),
                            "user_id": user_id,
                            "status_code": e.status_code,
                            "error_message": str(e)
                        }
                    )
                except Exception as e:
                    self.logger.error(
                        "Unexpected error deactivating old session",
                        exc_info=True,
                        extra={"session_id": session.get('id'), "user_id": user_id}
                    )
                    
        except CosmosHttpResponseError as e:
            self.logger.warning(
                "Error querying/deactivating old sessions in Cosmos DB",
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error deactivating old sessions",
                exc_info=True,
                extra={"user_id": user_id}
            )

    async def deactivate_session(self, session_id: str) -> bool:
        """
        Mark a session as inactive (logout).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self._cosmos, 'sessions_container') or self._cosmos.sessions_container is None:
            return False
            
        try:
            query = "SELECT * FROM c WHERE c.id = @session_id"
            params = [{"name": "@session_id", "value": session_id}]
            
            results = await run_sync(lambda: list(self._cosmos.sessions_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )))
            
            if not results:
                return False
                
            session_item = results[0]
            session_item["is_active"] = False  # Keep for backward compatibility
            session_item["status"] = "closed"  # Use correct field for Azure Function cleanup
            session_item["ended_at"] = datetime.now(timezone.utc).isoformat()
            
            await run_sync(lambda: self._cosmos.sessions_container.upsert_item(session_item))
            self.logger.debug(f"Deactivated session {session_id}")
            return True
            
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Failed to deactivate session in Cosmos DB",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
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

    async def _cleanup_duplicate_sessions(self, user_id: str, preferred_session_id: str, timestamp: datetime) -> None:
        """
        Clean up duplicate active sessions for a user, keeping only the preferred session.
        This method helps handle race conditions where multiple sessions get created simultaneously.
        
        Args:
            user_id: User identifier
            preferred_session_id: Session ID to keep active
            timestamp: Current timestamp
        """
        try:
            query = """
                SELECT c.id, c.created_at, c.partition_key FROM c 
                WHERE c.user_id = @user_id 
                AND c.status = 'active'
                AND c.type = 'session'
                AND c.id != @preferred_session_id
            """
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@preferred_session_id", "value": preferred_session_id}
            ]
            
            results = await run_sync(lambda: list(self._cosmos.sessions_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )))
            
            if results:
                self.logger.info(f"Found {len(results)} duplicate sessions for user {user_id}, cleaning up...")
                
                for session in results:
                    try:
                        # Mark duplicate session as closed
                        session["status"] = "closed"
                        session["is_active"] = False
                        session["ended_at"] = timestamp.isoformat()
                        session["end_reason"] = "duplicate_session_cleanup"
                        
                        await run_sync(lambda s=session: self._cosmos.sessions_container.upsert_item(s))
                        self.logger.debug(f"Cleaned up duplicate session {session['id']} for user {user_id}")
                        
                    except CosmosHttpResponseError as e:
                        self.logger.error(
                            "Failed to cleanup duplicate session in Cosmos DB",
                            exc_info=True,
                            extra={
                                "session_id": session['id'],
                                "user_id": user_id,
                                "status_code": e.status_code,
                                "error_message": str(e)
                            }
                        )
                    except Exception as e:
                        self.logger.error(
                            "Unexpected error cleaning up duplicate session",
                            exc_info=True,
                            extra={"session_id": session.get('id'), "user_id": user_id}
                        )
                        
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Error querying duplicate sessions from Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "preferred_session_id": preferred_session_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error during duplicate session cleanup",
                exc_info=True,
                extra={"user_id": user_id, "preferred_session_id": preferred_session_id}
            )

    async def cleanup_user_sessions(self, user_id: str) -> Dict[str, Any]:
        """
        Clean up all sessions for a user, keeping only the most recent active session.
        This is a utility method that can be called manually to fix session duplication issues.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with cleanup results
        """
        if not hasattr(self._cosmos, 'sessions_container') or self._cosmos.sessions_container is None:
            return {"error": "Sessions container unavailable"}
            
        try:
            query = """
                SELECT c.id, c.created_at, c.last_heartbeat, c.status FROM c 
                WHERE c.user_id = @user_id 
                AND c.type = 'session'
                ORDER BY c.last_heartbeat DESC
            """
            params = [{"name": "@user_id", "value": user_id}]
            
            results = await run_sync(lambda: list(self._cosmos.sessions_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            )))
            
            if not results:
                return {"message": "No sessions found", "cleaned": 0}
            
            # Keep the most recent session active, close all others
            active_sessions = [s for s in results if s.get("status") == "active"]
            
            if len(active_sessions) <= 1:
                return {"message": "No duplicate sessions found", "total_sessions": len(results), "active_sessions": len(active_sessions)}
            
            # Sort by last heartbeat and keep the most recent
            active_sessions.sort(key=lambda x: x.get("last_heartbeat", ""), reverse=True)
            keep_session = active_sessions[0]
            close_sessions = active_sessions[1:]
            
            cleaned_count = 0
            current_time = datetime.now(timezone.utc)
            
            for session in close_sessions:
                try:
                    session["status"] = "closed"
                    session["is_active"] = False
                    session["ended_at"] = current_time.isoformat()
                    session["end_reason"] = "manual_duplicate_cleanup"
                    
                    await run_sync(lambda s=session: self._cosmos.sessions_container.upsert_item(s))
                    cleaned_count += 1
                    
                except CosmosHttpResponseError as e:
                    self.logger.error(
                        "Failed to cleanup session in Cosmos DB during manual cleanup",
                        exc_info=True,
                        extra={
                            "session_id": session['id'],
                            "user_id": user_id,
                            "status_code": e.status_code,
                            "error_message": str(e)
                        }
                    )
                except Exception as e:
                    self.logger.error(
                        "Unexpected error cleaning up session during manual cleanup",
                        exc_info=True,
                        extra={"session_id": session.get('id'), "user_id": user_id}
                    )
            
            return {
                "message": f"Cleaned up {cleaned_count} duplicate sessions",
                "total_sessions": len(results),
                "active_sessions_before": len(active_sessions),
                "active_sessions_after": 1,
                "kept_session": keep_session["id"],
                "cleaned_sessions": [s["id"] for s in close_sessions[:cleaned_count]]
            }
            
        except CosmosHttpResponseError as e:
            self.logger.error(
                "Error during manual session cleanup in Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return {"error": str(e)}
        except Exception as e:
            self.logger.error(
                "Unexpected error during manual session cleanup",
                exc_info=True,
                extra={"user_id": user_id}
            )
            return {"error": str(e)}