# Security Middleware for Input Validation and Rate Limiting
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Any
import re
import time
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for input validation and attack prevention"""
    
    def __init__(self, app, max_requests_per_minute: int = 60, max_upload_size: int = 100*1024*1024):
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        self.max_upload_size = max_upload_size
        self.rate_limit_cache = defaultdict(lambda: deque())
        
        # Dangerous patterns to block
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # XSS
            r'on\w+\s*=',  # Event handlers
            r'\.\./|\.\\\.',  # Path traversal
            r'union\s+select',  # SQL injection (though we use NoSQL)
            r'exec\s*\(',  # Code execution
            r'eval\s*\(',  # Code execution
            r'system\s*\(',  # System calls
            r'__import__',  # Python imports
            r'<\s*iframe',  # Iframe injection
        ]
        self.pattern_regex = re.compile('|'.join(self.dangerous_patterns), re.IGNORECASE)
    
    async def dispatch(self, request: Request, call_next):
        # Rate limiting
        client_ip = self._get_client_ip(request)
        if not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after": 60}
            )
        
        # Content length validation
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > self.max_upload_size:
                logger.warning(f"Upload size exceeded: {content_length} bytes from {client_ip}")
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request entity too large"}
                )
        
        # Input validation for query parameters
        for param, value in request.query_params.items():
            if self._contains_dangerous_pattern(str(value)):
                logger.warning(f"Dangerous pattern detected in query param '{param}': {value[:100]}... from {client_ip}")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid input detected", "parameter": param}
                )
        
        # Input validation for path parameters
        if self._contains_dangerous_pattern(str(request.url.path)):
            logger.warning(f"Dangerous pattern detected in path: {request.url.path} from {client_ip}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid path detected"}
            )
        
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.openai.com https://*.azure.com; "
            "frame-ancestors 'none';"
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxy headers"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limit"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        while self.rate_limit_cache[client_ip] and self.rate_limit_cache[client_ip][0] < minute_ago:
            self.rate_limit_cache[client_ip].popleft()
        
        # Check current count
        if len(self.rate_limit_cache[client_ip]) >= self.max_requests_per_minute:
            return False
        
        # Add current request
        self.rate_limit_cache[client_ip].append(now)
        return True
    
    def _contains_dangerous_pattern(self, text: str) -> bool:
        """Check if text contains dangerous patterns"""
        return bool(self.pattern_regex.search(text))

class SecureResponseMiddleware(BaseHTTPMiddleware):
    """Middleware to sanitize error responses and prevent information disclosure"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the full error for debugging
            logger.exception(f"Unhandled exception in {request.url.path}")
            
            # Return generic error to client
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred. Please try again later.",
                    "request_id": request.headers.get("x-request-id", "unknown")
                }
            )
