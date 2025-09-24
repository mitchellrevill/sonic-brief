"""
Session Tracking Middleware - Lightweight HTTP coordination layer

This middleware handles ONLY HTTP request coordination:
- Extracting user information from requests
- Coordinating with dedicated services
- Managing request/response flow

All business logic is delegated to specialized services:
- SessionTrackingService: Session lifecycle management
- AuditLoggingService: Security audit logging
- AuthenticationService: JWT token handling
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


from ..services.monitoring.audit_logging_service import AuditLoggingService
from ..services.monitoring.session_tracking_service import SessionTrackingService
from ..services.auth.authentication_service import AuthenticationService
from ..utils.logging_config import get_logger


class LazySessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Lazy-loading session tracking middleware that gets services from app.state.
    
    This middleware can be added during FastAPI app creation and automatically
    discovers services from app.state during request processing.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger(__name__)
        
        self.logger.info("🔍 Lazy session tracking middleware created (will discover services from app.state)")

    async def dispatch(self, request: Request, call_next):
        """
        Main middleware coordination logic with automatic service discovery.
        
        If services are not available in app.state, requests pass through without session tracking.
        """
        start_time = datetime.now(timezone.utc)
        
        # Get services from app.state (available after startup)
        app_state = getattr(request.app, 'state', None)
        if not app_state:
            self.logger.debug("No app.state available, passing request through")
            response = await call_next(request)
            return response
            
        session_service = getattr(app_state, 'session_tracking_service', None)
        audit_service = getattr(app_state, 'audit_logging_service', None)
        auth_service = getattr(app_state, 'authentication_service', None)
        
        # If services not configured yet, pass through without session tracking
        missing = []
        if not session_service:
            missing.append("session_tracking_service")
        if not audit_service:
            missing.append("audit_logging_service")
        if not auth_service:
            missing.append("authentication_service")

        if missing:
            # Attempt to show what's available in app.state for debugging
            try:
                available = [k for k in dir(app_state) if not k.startswith("_")]
            except Exception:
                available = []
            self.logger.debug(
                "Session tracking services not configured on app.state; missing=%s; available_state_attrs=%s",
                missing,
                available,
            )
            response = await call_next(request)
            return response
        
        user_info = None
        session_id = None
        
        try:
            # Extract user information using AuthenticationService
            user_info = await auth_service.extract_user_from_request(request)
            
            if user_info:
                # Normalize user id from common claim shapes
                user_id = (
                    user_info.get("id") or user_info.get("user_id") or user_info.get("userId") or user_info.get("sub")
                )
                # Extract request metadata
                ip_address = auth_service.extract_ip_address(request)
                user_agent = auth_service.extract_user_agent(request)
                request_path = str(request.url.path)

                # Track session activity using SessionTrackingService
                try:
                    session_id = await session_service.get_or_create_session(
                        user_id=user_id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        request_path=request_path,
                    )
                except Exception as e:
                    session_id = None
                    self.logger.error(
                        "SessionTrackingService.get_or_create_session failed for user_id=%s: %s",
                        user_id,
                        e,
                        exc_info=True,
                    )

                # Log security audit event (non-fatal if audit fails)
                try:
                    await audit_service.log_user_activity(
                        user_id=user_id,
                        session_id=session_id,
                        action="request",
                        resource=request_path,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        additional_context={
                            "method": request.method,
                            "query_params": dict(request.query_params),
                        },
                    )
                except Exception as e:
                    self.logger.debug("Audit log failed in middleware (non-fatal): %s", e)
            
            # Process the request
            response = await call_next(request)
            
            # Update session if we had a session
            if session_id and session_service:
                try:
                    updated = await session_service.update_heartbeat(
                        session_id=session_id,
                        user_id=user_id,
                        request_path=str(request.url.path),
                        user_agent=user_agent,
                        ip_address=ip_address,
                        timestamp=datetime.now(timezone.utc),
                    )
                    if not updated:
                        self.logger.debug(
                            "SessionTrackingService.update_heartbeat returned False for session_id=%s user_id=%s",
                            session_id,
                            user_id,
                        )
                except Exception as e:
                    self.logger.error("Session heartbeat update failed (non-fatal): %s", e, exc_info=True)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Session tracking middleware error: {str(e)}")
            # Always ensure request is processed even if session tracking fails
            response = await call_next(request)
            return response


class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware for session tracking coordination.
    
    This middleware coordinates between HTTP requests and business services.
    It delegates all business logic to specialized services for clean separation of concerns.
    
    Responsibilities:
    - Extract request information (IP, user agent, etc.)
    - Coordinate with SessionTrackingService for session management
    - Coordinate with AuditLoggingService for security logging
    - Coordinate with AuthenticationService for user identification
    
    NOT responsible for:
    - Business logic (delegated to services)
    - Database operations (handled by services)
    - JWT parsing (handled by AuthenticationService)
    - Memory diagnostics (separate concern)
    """
    
    def __init__(
        self,
        app: ASGIApp,
        session_service: SessionTrackingService,
        audit_service: AuditLoggingService,
        auth_service: AuthenticationService
    ):
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.session_service = session_service
        self.audit_service = audit_service
        self.auth_service = auth_service
        
        self.logger.info("🔍 Session tracking middleware initialized with proper DI")

    async def dispatch(self, request: Request, call_next):
        """
        Main middleware coordination logic.
        
        Coordinates between HTTP request and specialized services.
        """
        start_time = datetime.now(timezone.utc)
        user_info = None
        session_id = None
        
        try:
            # Extract user information using AuthenticationService
            user_info = await self.auth_service.extract_user_from_request(request)
            
            if user_info:
                # Extract request metadata
                ip_address = self.auth_service.extract_ip_address(request)
                user_agent = self.auth_service.extract_user_agent(request)
                request_path = str(request.url.path)
                
                # Track session activity using SessionTrackingService
                session_id = await self.session_service.get_or_create_session(
                    user_id=user_info["id"],
                    user_email=user_info.get("email"),
                    request_path=request_path,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    timestamp=start_time
                )
                
                # Check if this endpoint should be audited using AuditLoggingService
                if self.audit_service.is_audit_endpoint(request_path):
                    await self._log_audit_event(
                        user_info, request, ip_address, user_agent, start_time
                    )
            
            # Process the actual request
            response = await call_next(request)
            
            # Log completion for audit endpoints if user is authenticated
            if user_info and self.audit_service.is_audit_endpoint(str(request.url.path)):
                await self._log_audit_completion(
                    user_info, request, response, start_time
                )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Session tracking middleware error: {str(e)}")
            # Don't let middleware errors break the application
            return await call_next(request)

    async def _log_audit_event(
        self,
        user_info: Dict[str, Any],
        request: Request,
        ip_address: str,
        user_agent: str,
        timestamp: datetime
    ) -> None:
        """Log audit event for security-critical endpoints."""
        try:
            event_type = self.audit_service.determine_audit_event_type(
                str(request.url.path), request.method
            )
            
            await self.audit_service.create_audit_log(
                user_id=user_info["id"],
                user_email=user_info.get("email"),
                event_type=event_type,
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=ip_address,
                user_agent=user_agent,
                user_permission=user_info.get("permission"),
                timestamp=timestamp
            )
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {str(e)}")

    async def _log_audit_completion(
        self,
        user_info: Dict[str, Any],
        request: Request,
        response: Response,
        start_time: datetime
    ) -> None:
        """Log completion of audit-worthy operations."""
        try:
            end_time = datetime.now(timezone.utc)
            processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            ip_address = self.auth_service.extract_ip_address(request)
            user_agent = self.auth_service.extract_user_agent(request)
            
            await self.audit_service.log_audit_completion(
                user_id=user_info["id"],
                user_email=user_info.get("email"),
                endpoint=str(request.url.path),
                method=request.method,
                status_code=response.status_code,
                ip_address=ip_address,
                user_agent=user_agent,
                processing_time_ms=processing_time_ms,
                timestamp=end_time
            )
        except Exception as e:
            self.logger.error(f"Failed to log audit completion: {str(e)}")