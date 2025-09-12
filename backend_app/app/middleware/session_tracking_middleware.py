from typing import Callable
from starlette.types import ASGIApp, Receive, Scope, Send
import time
from fastapi import Request


class SessionTrackingMiddleware:
    """Minimal session tracking middleware shim.

    This implementation records a simple heartbeat timestamp on the request state
    and logs duration. It matches the constructor used in `main.py`:
        SessionTrackingMiddleware(session_timeout_minutes=..., heartbeat_interval_minutes=...)

    It's intentionally lightweight to avoid changing behavior during the refactor.
    """

    def __init__(self, app: ASGIApp, session_timeout_minutes: int = 15, heartbeat_interval_minutes: int = 5):
        self.app = app
        self.session_timeout_minutes = session_timeout_minutes
        self.heartbeat_interval_minutes = heartbeat_interval_minutes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Only handle http requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.time()

        async def send_wrapper(message):
            # pass-through
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # simple post-request work (non-blocking)
        duration = time.time() - start
        # store on scope to allow later inspection if needed
        scope.setdefault("session_tracking", {})
        scope["session_tracking"]["last_request_duration"] = duration
"""
Comprehensive User Session Tracking Middleware

This middleware automatically tracks user sessions without requiring separate endpoints.
It logs session activity to the User Sessions container and audit events to the Audit Logs container.

Key Features:
- Automatic session creation and heartbeat tracking
- Separate audit logging for security events
- Clean separation between session data and audit data
- Efficient middleware that doesn't block requests
- Works with the session cleanup Azure Function
"""

import logging
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncio
import json
import os
import platform
import gc

# Optional memory tooling: prefer psutil when available; fallback to tracemalloc for Python-level
try:
    import psutil
except Exception:
    psutil = None

try:
    import tracemalloc
except Exception:
    tracemalloc = None

# Import permission utilities
from app.models.permissions import PermissionLevel, PermissionCapability
from app.core.config import get_app_config, get_cosmos_db_cached
from app.utils.logging_config import get_logger


class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive user session and audit tracking
    
    This middleware:
    1. Tracks user sessions automatically in the user_sessions container
    2. Logs security/audit events in the audit_logs container
    3. Updates session heartbeats for active users
    4. Creates audit trails for important actions
    """
    
    def __init__(
        self, 
        app: ASGIApp,
        session_timeout_minutes: int = 15,
        heartbeat_interval_minutes: int = 5,
        batch_interval_seconds: int = 2,
        max_batch_size: int = 200
    ):
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.session_timeout_minutes = session_timeout_minutes
        self.heartbeat_interval_minutes = heartbeat_interval_minutes

        # Background batching configuration
        self._batch_interval_seconds = batch_interval_seconds
        self._max_batch_size = max_batch_size

        # Pending upserts: session_id -> (session_item, container)
        self._pending_upserts = {}
        # Upsert event and background task initialized lazily when event loop is available
        self._upsert_event = None
        self._batch_task = None

        # Track which endpoints should create audit logs (ONLY security-critical actions)
        self.audit_endpoints = {
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
            
            # User management (creating/deleting users)
            '/api/auth/users': 'user_created',  # POST to create user
            '/api/auth/register': 'user_registered',
            '/api/auth/users/*/delete': 'user_deleted',
            
            # Job sharing (security-relevant as it affects access control)
            '/api/upload/*/share': 'job_shared',
            '/api/upload/*/unshare': 'job_unshared',
            '/api/jobs/*/share': 'job_shared',
            '/api/jobs/*/unshare': 'job_unshared',
            
            # System administration (high-privilege actions)
            '/api/admin/*': 'admin_action',
            '/api/system/*': 'system_action',
        }
        
        # Track which endpoints are sensitive and need detailed logging
        # NOTE: keep this focused to truly sensitive routes so that simple GETs
        # (e.g. listing users) do not trigger completion audit logs unnecessarily.
        self.sensitive_endpoints = {
            '/api/auth/permissions',
            '/api/admin'
        }
        
        self.logger.info("🔍 Session tracking middleware initialized")
        self.logger.info(f"   Session timeout: {session_timeout_minutes} minutes")
        self.logger.info(f"   Heartbeat interval: {heartbeat_interval_minutes} minutes")

        # Memory diagnostics (opt-in via env var ENABLE_SESSION_MEMORY_DIAG=true)
        self.enable_memory_diag = os.getenv("ENABLE_SESSION_MEMORY_DIAG", "false").lower() in ("1", "true", "yes")
        # Optional threshold to warn when pending upserts exceed this size
        try:
            self._memory_diag_pending_threshold = int(os.getenv("SESSION_PENDING_UPSERTS_WARN", "200"))
        except Exception:
            self._memory_diag_pending_threshold = 200

        if self.enable_memory_diag:
            self.logger.info("🧭 Session memory diagnostics enabled")
            # Start tracemalloc if available to capture Python allocation snapshots
            if tracemalloc and not tracemalloc.is_tracing():
                try:
                    tracemalloc.start()
                    self.logger.debug("tracemalloc started for Python allocation tracking")
                except Exception as e:
                    self.logger.debug(f"Could not start tracemalloc: {e}")

    def _get_memory_info(self) -> Dict[str, Any]:
        """
        Collect memory information from the running process.
        Prefers psutil (RSS/VMS). Falls back to tracemalloc snapshot for Python-level allocations.
        """
        info: Dict[str, Any] = {"platform": platform.system()}
        try:
            pid = os.getpid()
            info["pid"] = pid
        except Exception:
            info["pid"] = None

        # psutil: system-level process memory
        try:
            if psutil:
                p = psutil.Process(os.getpid())
                mem = p.memory_info()
                info.update({
                    "rss": getattr(mem, "rss", None),
                    "vms": getattr(mem, "vms", None),
                    "uss": getattr(mem, "uss", None) if hasattr(mem, "uss") else None,
                    "python_objs": None,
                })
                return info
        except Exception as e:
            # ignore and fallback
            self.logger.debug(f"psutil memory read failed: {e}")

        # tracemalloc: Python allocations
        try:
            if tracemalloc and tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                stats = snapshot.statistics('filename')
                top = stats[0] if stats else None
                info.update({
                    "rss": None,
                    "vms": None,
                    "python_objs": top.size if top else None,
                    "python_top_file": top.traceback[0].filename if top and top.traceback else None,
                })
                return info
        except Exception as e:
            self.logger.debug(f"tracemalloc snapshot failed: {e}")

        # Final fallback: lightweight GC-based info
        try:
            info["gc_objects"] = len(gc.get_objects())
        except Exception:
            info["gc_objects"] = None

        return info

    def _log_memory_snapshot(self, context: str):
        """
        Convenience wrapper to log memory snapshot with a short context label.
        """
        try:
            mem = self._get_memory_info()
            # Format values for readability
            rss = mem.get("rss")
            rss_mb = f"{rss/1024/1024:.1f}MB" if isinstance(rss, (int, float)) else None
            python_objs = mem.get("python_objs") or mem.get("gc_objects")
            self.logger.info(f"[MEM] {context} pid={mem.get('pid')} rss={rss_mb} python_objs={python_objs} platform={mem.get('platform')}")
        except Exception as e:
            self.logger.debug(f"Failed to log memory snapshot: {e}")

    async def _session_batch_worker(self):
        """
        Background worker that flushes pending session upserts in batches.
        It wakes either when signaled or after the batch interval timeout.
        """
        self.logger.info("Session batch worker started")
        if self.enable_memory_diag:
            self._log_memory_snapshot("batch_worker_start")
        try:
            while True:
                # Ensure event exists
                if self._upsert_event is None:
                    self._upsert_event = asyncio.Event()

                try:
                    # Wait until signaled or timeout
                    await asyncio.wait_for(self._upsert_event.wait(), timeout=self._batch_interval_seconds)
                except asyncio.TimeoutError:
                    # Timeout is expected; proceed to flush if any pending
                    pass

                # Clear the event so we can wait for the next signal
                try:
                    self._upsert_event.clear()
                except Exception:
                    # Ignore if event cleared concurrently
                    pass

                # Collect up to max_batch_size pending upserts
                if not self._pending_upserts:
                    continue

                if self.enable_memory_diag and len(self._pending_upserts) >= self._memory_diag_pending_threshold:
                    self._log_memory_snapshot(f"batch_worker_pending_{len(self._pending_upserts)}")

                batch_items = []
                for i, (sess_id, val) in enumerate(list(self._pending_upserts.items())):
                    if i >= self._max_batch_size:
                        break
                    batch_items.append((sess_id, val[0], val[1]))

                # Remove these from pending map
                for sess_id, _, _ in batch_items:
                    self._pending_upserts.pop(sess_id, None)

                # Perform upserts sequentially in threads to avoid blocking the loop
                for sess_id, session_item, container in batch_items:
                    try:
                        await asyncio.to_thread(container.upsert_item, session_item)
                        self.logger.debug(f"Batch upserted session {sess_id}")
                    except Exception as e:
                        self.logger.exception(f"Failed batch upserting session {sess_id}: {e}")

                if self.enable_memory_diag:
                    self._log_memory_snapshot("batch_worker_after_flush")

        except asyncio.CancelledError:
            self.logger.info("Session batch worker cancelled and exiting")
            raise
        except Exception as e:
            self.logger.exception(f"Session batch worker exiting due to unexpected error: {e}")
            # Reset task marker so it can be restarted later
            self._batch_task = None
    
    async def dispatch(self, request: Request, call_next):
        """
        Main middleware logic - processes each request
        """
        start_time = datetime.now(timezone.utc)
        user_info = None
        session_id = None
        if self.enable_memory_diag:
            # Log at request entry to capture memory baseline per request
            self._log_memory_snapshot(f"request_start {request.method} {request.url.path}")
        
        try:
            # Extract user information from JWT token if present
            user_info = await self._extract_user_from_request(request)
            
            if user_info:
                # Track session activity
                session_id = await self._track_session_activity(request, user_info, start_time)
                
                # Check if this is an audit-worthy endpoint
                await self._check_and_log_audit_event(request, user_info, start_time)
            
            # Process the actual request
            response = await call_next(request)
            
            # Log completion for audit endpoints
            if user_info and self._is_audit_endpoint(request.url.path):
                await self._log_audit_completion(request, user_info, response.status_code, start_time)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Session tracking middleware error: {str(e)}")
            if self.enable_memory_diag:
                self._log_memory_snapshot("middleware_exception")
            # Don't let middleware errors break the application
            response = await call_next(request)
            return response
    
    async def _extract_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract user information from JWT token
        """
        try:
            # Get Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            
            # Decode JWT token
            from jose import jwt, JWTError
            import os
            jwt_secret_key = os.getenv("JWT_SECRET_KEY")
            jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
            
            payload = jwt.decode(token, jwt_secret_key, algorithms=[jwt_algorithm])
            
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Get additional user info from payload
            return {
                "id": user_id,
                "email": payload.get("email"),
                "permission": payload.get("permission"),
                "custom_capabilities": payload.get("custom_capabilities", {}),
                "token_issued_at": payload.get("iat"),
                "token_expires_at": payload.get("exp")
            }
            
        except JWTError:
            return None
        except Exception as e:
            self.logger.debug(f"Error extracting user from request: {str(e)}")
            return None
    
    async def _track_session_activity(
        self, 
        request: Request, 
        user_info: Dict[str, Any], 
        timestamp: datetime
    ) -> Optional[str]:
        """
        Track user session activity in the user_sessions container
        """
        try:
            from app.core.config import get_cosmos_db, AppConfig
            
            config = get_app_config()
            cosmos_db = get_cosmos_db_cached(config)
            
            if not hasattr(cosmos_db, 'sessions_container') or cosmos_db.sessions_container is None:
                self.logger.warning("Sessions container not available")
                return None
            
            # Extract user identifiers from JWT payload
            user_email_or_id = user_info.get("id")  # This is the JWT 'sub' field (usually email)
            user_email = user_info.get("email") or user_email_or_id
            
            # Try to resolve email to GUID for session tracking
            user_id_for_session = user_email_or_id
            try:
                if user_email and not self._is_guid(user_email_or_id):
                    # Only try to resolve if we don't already have a GUID
                    resolved = await self._resolve_canonical_id(cosmos_db, user_email)
                    if resolved and self._is_guid(resolved):
                        user_id_for_session = resolved
                        self.logger.debug(f"✅ Resolved GUID {user_id_for_session} for email {user_email}")
                
                # If we still don't have a GUID, skip session tracking
                if not self._is_guid(user_id_for_session):
                    self.logger.warning(f"⚠️ Skipping session tracking - no GUID available for user {user_email}")
                    return None
                    
            except Exception as e:
                self.logger.error(f"❌ Error resolving user GUID: {e}")
                return None

            # Create or update session using GUID
            session_id = await self._get_or_create_session(cosmos_db, user_id_for_session, request, timestamp, user_email=user_email)

            # Update session heartbeat
            await self._update_session_heartbeat(cosmos_db, session_id, user_id_for_session, request, timestamp)
            
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error tracking session activity: {str(e)}")
            return None
    
    async def _get_or_create_session(
        self, 
        cosmos_db, 
        user_id: str, 
        request: Request, 
        timestamp: datetime,
        user_email: Optional[str] = None
    ) -> str:
        """
        Get existing active session or create a new one
        """
        try:
            # Look for existing active session
            cutoff_time = timestamp - timedelta(minutes=self.session_timeout_minutes)
            
            # Try to find an active session by canonical user id or by email
            query = """
            SELECT TOP 1 * FROM c
            WHERE c.type = 'session'
            AND c.status = 'active'
            AND c.last_heartbeat >= @cutoff_time
            AND (
                c.user_id = @user_id
                OR (c.user_email = @user_email)
            )
            ORDER BY c.last_heartbeat DESC
            """

            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@user_email", "value": user_email or ""},
                {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
            ]

            # Run cross-partition query in a thread
            items = await asyncio.to_thread(
                lambda: list(cosmos_db.sessions_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
            )
            
            if items:
                # Return existing session
                return items[0]["id"]
            else:
                # Create new session
                return await self._create_new_session(cosmos_db, user_id, request, timestamp, user_email=user_email)
                
        except Exception as e:
            self.logger.error(f"Error getting or creating session: {str(e)}")
            # Fallback to creating a new session
            return await self._create_new_session(cosmos_db, user_id, request, timestamp)

    async def _resolve_canonical_id(self, cosmos_db, email: str) -> Optional[str]:
        """
        Attempt to resolve a canonical GUID for a user by email using the auth container.
        Returns the GUID string if found, otherwise None.
        """
        try:
            if not hasattr(cosmos_db, 'auth_container') or cosmos_db.auth_container is None:
                self.logger.debug("Auth container not available for canonical id resolution")
                return None

            auth_query = "SELECT TOP 1 c.id FROM c WHERE c.email = @email"
            auth_params = [{"name": "@email", "value": email}]

            self.logger.debug(f"🔍 Querying auth container for email: {email}")
            res = await asyncio.to_thread(
                lambda: list(cosmos_db.auth_container.query_items(query=auth_query, parameters=auth_params, enable_cross_partition_query=True))
            )
            
            if res:
                self.logger.debug(f"🔍 Auth query returned {len(res)} results: {res}")
                if isinstance(res[0], dict) and res[0].get('id'):
                    candidate = res[0].get('id')
                    if self._is_guid(candidate):
                        self.logger.info(f"✅ Found canonical GUID {candidate} for email {email}")
                        return candidate
                    else:
                        self.logger.warning(f"⚠️ Auth record ID {candidate} is not a valid GUID")
            else:
                self.logger.warning(f"⚠️ No auth record found for email {email}")
            return None
        except Exception as e:
            self.logger.exception(f"❌ Exception resolving canonical id for {email}: {e}")
            return None

    def _is_guid(self, val: Optional[str]) -> bool:
        if not val:
            return False
        guid_pattern = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        return bool(guid_pattern.match(str(val)))
    
    async def _create_new_session(
        self, 
        cosmos_db, 
        user_id: str, 
        request: Request, 
        timestamp: datetime,
        user_email: Optional[str] = None
    ) -> str:
        """
        Create a new user session
        """
        session_id = str(uuid.uuid4())
        
        # Extract request metadata
        user_agent = request.headers.get("User-Agent", "")
        ip_address = self._get_client_ip(request)
        
        # Create session data structure with GUID user_id
        session_data = {
            "id": session_id,
            "type": "session",
            "user_id": user_id,  # This is now guaranteed to be a GUID
            "user_email": None,  # Will be populated below if available
            "status": "active",
            "created_at": timestamp.isoformat(),
            "last_heartbeat": timestamp.isoformat(),
            "last_activity": timestamp.isoformat(),
            "last_endpoint": request.url.path,
            "session_metadata": {
                "user_agent": user_agent,
                "ip_address": ip_address,
                "start_page": request.url.path,
                "browser": self._parse_browser_info(user_agent),
                "platform": self._parse_platform_info(user_agent)
            },
            "activity_count": 1,
            "endpoints_accessed": [request.url.path]
        }

        # Attach email field if provided
        if user_email:
            session_data["user_email"] = user_email
        
        # Use thread to run blocking SDK call
        try:
            self.logger.info(f"📝 Creating session with data:")
            self.logger.info(f"   - session_id: {session_id}")
            self.logger.info(f"   - user_id: {user_id}")
            self.logger.info(f"   - user_email: {user_email}")
            self.logger.info(f"   - endpoint: {request.url.path}")
            
            await asyncio.to_thread(cosmos_db.sessions_container.create_item, session_data)
            self.logger.info(f"🟢 Successfully created session {session_id} for user {user_id}")
            
            # Verify the session was created by querying it back
            try:
                verify_query = "SELECT c.id, c.user_id, c.user_email, c.created_at FROM c WHERE c.id = @session_id"
                verify_params = [{"name": "@session_id", "value": session_id}]
                verify_result = list(cosmos_db.sessions_container.query_items(
                    query=verify_query,
                    parameters=verify_params,
                    enable_cross_partition_query=True
                ))
                if verify_result:
                    session_doc = verify_result[0]
                    self.logger.info(f"✅ Session verification successful:")
                    self.logger.info(f"   - Stored user_id: {session_doc.get('user_id')}")
                    self.logger.info(f"   - Stored user_email: {session_doc.get('user_email')}")
                else:
                    self.logger.error(f"❌ Session {session_id} not found after creation")
            except Exception as verify_error:
                self.logger.error(f"❌ Session verification failed: {verify_error}")
                
        except Exception as e:
            self.logger.exception(f"❌ Failed creating session {session_id} for user {user_id}: {e}")
        
        return session_id
    
    async def _update_session_heartbeat(
        self, 
        cosmos_db, 
        session_id: str, 
        user_id: str, 
        request: Request, 
        timestamp: datetime
    ):
        """
        Update session heartbeat and activity
        """
        try:
            # Read the current session (blocking call in a thread)
            session_item = await asyncio.to_thread(cosmos_db.sessions_container.read_item, session_id, user_id)

            # Parse previous heartbeat and decide whether to enqueue an upsert
            last_heartbeat_str = session_item.get("last_heartbeat")
            should_write = True
            if last_heartbeat_str:
                try:
                    last_heartbeat_dt = datetime.fromisoformat(last_heartbeat_str)
                    delta = timestamp - last_heartbeat_dt
                    # Only enqueue if heartbeat interval has passed
                    if delta.total_seconds() < (self.heartbeat_interval_minutes * 60):
                        should_write = False
                except Exception:
                    should_write = True

            # Always update in-memory session_item for latest activity; we'll enqueue the upsert when appropriate
            session_item["last_heartbeat"] = timestamp.isoformat()
            session_item["last_activity"] = timestamp.isoformat()
            session_item["last_endpoint"] = request.url.path
            session_item["activity_count"] = session_item.get("activity_count", 0) + 1

            endpoints_accessed = session_item.get("endpoints_accessed", [])
            if request.url.path not in endpoints_accessed:
                endpoints_accessed.append(request.url.path)
                session_item["endpoints_accessed"] = endpoints_accessed

            if not should_write:
                # If we're within heartbeat interval, just store pending state and return
                # Ensure background worker is running
                if self._batch_task is None:
                    # Lazily create event and start worker on the running loop
                    self._upsert_event = asyncio.Event()
                    self._batch_task = asyncio.create_task(self._session_batch_worker())

                # Store latest session item to be upserted later
                self._pending_upserts[session_id] = (session_item, cosmos_db.sessions_container)
                # Signal worker
                if self._upsert_event:
                    self._upsert_event.set()
                self.logger.debug(f"Queued heartbeat update for session {session_id} (debounced)")
                # Emit diagnostic if pending queue grows
                if self.enable_memory_diag:
                    pending_count = len(self._pending_upserts)
                    if pending_count >= self._memory_diag_pending_threshold:
                        self.logger.warning(f"Pending upserts count high: {pending_count}")
                        self._log_memory_snapshot(f"pending_queue_grew_{pending_count}")
                return

            # If we should write immediately (heartbeat interval passed), enqueue and signal
            if self._batch_task is None:
                self._upsert_event = asyncio.Event()
                self._batch_task = asyncio.create_task(self._session_batch_worker())

            self._pending_upserts[session_id] = (session_item, cosmos_db.sessions_container)
            if self._upsert_event:
                self._upsert_event.set()
            self.logger.debug(f"Enqueued heartbeat update for session {session_id}")
            if self.enable_memory_diag:
                pending_count = len(self._pending_upserts)
                if pending_count >= self._memory_diag_pending_threshold:
                    self.logger.warning(f"Pending upserts count high after enqueue: {pending_count}")
                    self._log_memory_snapshot(f"pending_queue_enqueued_{pending_count}")
            
        except Exception as e:
            self.logger.error(f"Error updating session heartbeat: {str(e)}")
    
    async def _check_and_log_audit_event(
        self, 
        request: Request, 
        user_info: Dict[str, Any], 
        timestamp: datetime
    ):
        """
        Check if this request should create an audit log entry
        """
        try:
            endpoint_path = request.url.path
            method = request.method
            
            # Only log certain methods and endpoints
            if method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
                self.logger.debug(f"Skipping audit log for method {method} on {endpoint_path}")
                return
            
            is_audit_endpoint = self._is_audit_endpoint(endpoint_path)
            self.logger.debug(f"Checking audit for {method} {endpoint_path}: is_audit_endpoint={is_audit_endpoint}")
            
            if not is_audit_endpoint:
                self.logger.debug(f"Path {endpoint_path} not in audit endpoints, skipping audit log")
                return
            
            # This is an audit-worthy event
            self.logger.info(f"🔍 Creating audit log for {method} {endpoint_path} by user {user_info['id']}")
            await self._create_audit_log(request, user_info, timestamp)
            
        except Exception as e:
            self.logger.error(f"Error checking audit event: {str(e)}")
    
    async def _create_audit_log(
        self, 
        request: Request, 
        user_info: Dict[str, Any], 
        timestamp: datetime
    ):
        """
        Create an audit log entry in the audit_logs container
        """
        try:
            from app.core.config import get_cosmos_db, AppConfig
            
            config = get_app_config()
            cosmos_db = get_cosmos_db_cached(config)
            
            # Use audit container if available, otherwise sessions container as fallback
            container = None
            container_name = ""
            
            if hasattr(cosmos_db, 'audit_container') and cosmos_db.audit_container is not None:
                container = cosmos_db.audit_container
                container_name = "audit_logs"
            elif hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container is not None:
                container = cosmos_db.sessions_container
                container_name = "user_sessions"
            else:
                self.logger.warning("No container available for audit logging")
                return
            
            # Resolve user email to GUID for audit logs as well
            user_email = user_info.get("email") or user_info.get("id")  # JWT 'sub' field may be in 'id'
            canonical_user_id = None
            
            try:
                if user_email:
                    resolved = await self._resolve_canonical_id(cosmos_db, user_email)
                    if resolved and self._is_guid(resolved):
                        canonical_user_id = resolved
                    elif self._is_guid(user_info.get("id")):
                        canonical_user_id = user_info.get("id")
                    else:
                        self.logger.warning(f"⚠️ Cannot resolve GUID for audit log, using email as fallback: {user_email}")
                        canonical_user_id = user_email  # Last resort fallback
            except Exception as e:
                self.logger.error(f"❌ Error resolving user GUID for audit log: {e}")
                canonical_user_id = user_email or user_info.get("id", "unknown")
            
            audit_id = str(uuid.uuid4())
            
            # Determine event type
            event_type = self._determine_audit_event_type(request.url.path, request.method)
            
            # Extract request details
            ip_address = self._get_client_ip(request)
            user_agent = request.headers.get("User-Agent", "")
            
            audit_data = {
                "id": audit_id,
                "type": "audit",
                "event_type": event_type,
                "user_id": canonical_user_id,
                "user_email": user_email,
                "timestamp": timestamp.isoformat(),
                "endpoint": request.url.path,
                "method": request.method,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "user_permission": user_info.get("permission"),
                "resource_type": self._extract_resource_type(request.url.path),
                "resource_id": self._extract_resource_id(request.url.path),
                "request_metadata": {
                    "headers": dict(request.headers),
                    "query_params": dict(request.query_params),
                    "content_type": request.headers.get("Content-Type")
                }
            }
            
            try:
                await asyncio.to_thread(container.create_item, audit_data)
                self.logger.info(f"📋 Created audit log {audit_id} for {event_type} by user {canonical_user_id} (email: {user_email})")
            except Exception as e:
                self.logger.exception(f"Failed to create audit log {audit_id}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error creating audit log: {str(e)}")
    
    async def _log_audit_completion(
        self, 
        request: Request, 
        user_info: Dict[str, Any], 
        status_code: int, 
        start_time: datetime
    ):
        """
        Log the completion of an audit-worthy request
        """
        try:
            completion_time = datetime.now(timezone.utc)
            duration_ms = int((completion_time - start_time).total_seconds() * 1000)
            
            # Only log failures and sensitive operations
            if status_code >= 400 or self._is_sensitive_endpoint(request.url.path):
                from app.core.config import get_cosmos_db, AppConfig
                
                config = get_app_config()
                cosmos_db = get_cosmos_db_cached(config)
                
                container = None
                if hasattr(cosmos_db, 'audit_container') and cosmos_db.audit_container is not None:
                    container = cosmos_db.audit_container
                elif hasattr(cosmos_db, 'sessions_container'):
                    container = cosmos_db.sessions_container
                
                if container:
                    # Resolve user email to GUID for audit completion logs as well
                    user_email = user_info.get("email") or user_info.get("id")
                    canonical_user_id = None
                    
                    try:
                        if user_email:
                            resolved = await self._resolve_canonical_id(cosmos_db, user_email)
                            if resolved and self._is_guid(resolved):
                                canonical_user_id = resolved
                            elif self._is_guid(user_info.get("id")):
                                canonical_user_id = user_info.get("id")
                            else:
                                canonical_user_id = user_email  # Fallback
                    except Exception as e:
                        canonical_user_id = user_email or user_info.get("id", "unknown")
                    
                    completion_id = str(uuid.uuid4())
                    
                    completion_data = {
                        "id": completion_id,
                        "type": "audit_completion",
                        "user_id": canonical_user_id,
                        "user_email": user_email,
                        "timestamp": completion_time.isoformat(),
                        "endpoint": request.url.path,
                        "method": request.method,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "success": status_code < 400
                    }
                    
                    try:
                        await asyncio.to_thread(container.create_item, completion_data)
                    except Exception as e:
                        self.logger.exception(f"Failed to create audit completion record: {e}")
                    
                    if status_code >= 400:
                        self.logger.warning(f"🚨 Audit completion logged - Failed request: {request.method} {request.url.path} - Status: {status_code}")
            
        except Exception as e:
            self.logger.error(f"Error logging audit completion: {str(e)}")
    
    def _is_audit_endpoint(self, path: str) -> bool:
        """
        Check if an endpoint should be audited
        """
        import re
        
        # Check exact matches first
        if path in self.audit_endpoints:
            self.logger.debug(f"Exact match found for audit endpoint: {path}")
            return True
        
        # Check pattern matches
        for pattern in self.audit_endpoints.keys():
            if '*' in pattern:
                # Replace * with regex pattern to match UUIDs, strings, etc.
                pattern_regex = pattern.replace('*', '[0-9a-f-]+|[^/]+')
                try:
                    if re.match(f"^{pattern_regex}$", path):
                        self.logger.debug(f"Pattern match found for audit endpoint: {path} matches {pattern}")
                        return True
                except re.error:
                    self.logger.warning(f"Invalid regex pattern: {pattern_regex}")
                    continue
        
        # Check for common audit patterns not explicitly listed (ONLY security-critical)
        audit_path_patterns = [
            r'^/api/auth/users/[^/]+/password$',      # Password changes
            r'^/api/auth/users/[^/]+/permission$',    # Permission changes
            r'^/api/auth/users/[^/]+/capabilities$',  # Capability changes
            r'^/api/auth/users/[^/]+/delete$',        # User deletion
            r'^/api/jobs/[^/]+/share$',               # Job sharing (access control)
            r'^/api/jobs/[^/]+/unshare$',             # Job unsharing (access control)
            r'^/api/upload/[^/]+/share$',             # Upload sharing (access control)
            r'^/api/upload/[^/]+/unshare$',           # Upload unsharing (access control)
            r'^/api/admin/',                          # Any admin action
            # Note: intentionally not matching '^/api/auth/users$' to avoid auditing GET user lists
        ]
        
        for audit_pattern in audit_path_patterns:
            try:
                if re.match(audit_pattern, path):
                    self.logger.debug(f"Dynamic pattern match found for audit endpoint: {path} matches {audit_pattern}")
                    return True
            except re.error:
                continue
        
        self.logger.debug(f"No audit pattern matched for path: {path}")
        return False
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """
        Check if an endpoint is sensitive and needs detailed logging
        """
        return any(sensitive in path for sensitive in self.sensitive_endpoints)
    
    def _determine_audit_event_type(self, path: str, method: str) -> str:
        """
        Determine the audit event type based on endpoint and method
        """
        # Check exact matches first
        if path in self.audit_endpoints:
            return self.audit_endpoints[path]
        
        # Check pattern matches
        for pattern, event_type in self.audit_endpoints.items():
            if '*' in pattern:
                pattern_regex = pattern.replace('*', '[^/]+')
                import re
                if re.match(f"^{pattern_regex}$", path):
                    return event_type
        
        # Fallback based on method and path patterns (ONLY for security-critical paths)
        if '/auth/users' in path and '/password' in path:
            return 'password_change'
        elif '/auth/users' in path and '/permission' in path:
            return 'permission_change'
        elif '/auth/users' in path and '/capabilities' in path:
            return 'capability_change'
        elif '/auth/users' in path and method == 'POST':
            return 'user_created'
        elif '/auth/users' in path and method == 'DELETE':
            return 'user_deleted'
        elif '/share' in path:
            return 'job_shared'
        elif '/unshare' in path:
            return 'job_unshared'
        elif '/admin/' in path:
            return 'admin_action'
        else:
            return f"security_{method.lower()}"
    
    def _extract_resource_type(self, path: str) -> str:
        """
        Extract the resource type from the endpoint path (ONLY for security-relevant resources)
        """
        if '/auth/users' in path:
            return 'user'
        elif '/jobs/' in path or '/upload/' in path:
            return 'job'
        elif '/admin/' in path:
            return 'system'
        elif '/auth/' in path:
            return 'auth'
        else:
            return 'security_resource'
    
    def _extract_resource_id(self, path: str) -> Optional[str]:
        """
        Extract the resource ID from the endpoint path
        """
        import re
        # Look for UUID patterns in the path
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        matches = re.findall(uuid_pattern, path, re.IGNORECASE)
        return matches[0] if matches else None
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request
        """
        # Check common headers for real IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return "unknown"
    
    def _parse_browser_info(self, user_agent: str) -> str:
        """
        Parse browser information from user agent string
        """
        user_agent_lower = user_agent.lower()
        
        if 'chrome' in user_agent_lower:
            return 'Chrome'
        elif 'firefox' in user_agent_lower:
            return 'Firefox'
        elif 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
            return 'Safari'
        elif 'edge' in user_agent_lower:
            return 'Edge'
        elif 'opera' in user_agent_lower:
            return 'Opera'
        else:
            return 'Unknown'
    
    def _parse_platform_info(self, user_agent: str) -> str:
        """
        Parse platform information from user agent string
        """
        user_agent_lower = user_agent.lower()
        
        if 'windows' in user_agent_lower:
            return 'Windows'
        elif 'mac' in user_agent_lower:
            return 'macOS'
        elif 'linux' in user_agent_lower:
            return 'Linux'
        elif 'android' in user_agent_lower:
            return 'Android'
        elif 'ios' in user_agent_lower or 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            return 'iOS'
        else:
            return 'Unknown'
