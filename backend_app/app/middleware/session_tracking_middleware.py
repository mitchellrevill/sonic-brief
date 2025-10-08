"""Session tracking middleware wired through dependency injection.

This module exposes a single middleware class that requires fully constructed
service dependencies at initialization time. The FastAPI application should
resolve those dependencies (typically through providers in
``app.core.dependencies``) and supply them via ``app.add_middleware``.
"""

from datetime import datetime, timezone
from typing import Dict, Any, TYPE_CHECKING
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..utils.logging_config import get_logger

if TYPE_CHECKING:
    from ..services.monitoring.audit_logging_service import AuditLoggingService
    from ..services.monitoring.session_tracking_service import SessionTrackingService
    from ..services.auth.authentication_service import AuthenticationService


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
        session_service: "SessionTrackingService",
        audit_service: "AuditLoggingService",
        auth_service: "AuthenticationService",
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
            self.logger.error("Session tracking middleware error: %s", e, exc_info=True)
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