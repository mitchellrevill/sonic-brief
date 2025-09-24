"""
Authentication Service - JWT token parsing and validation

This service handles ONLY authentication-related operations:
- JWT token extraction from requests
- Token validation and decoding
- User information extraction

Session tracking and audit logging are handled by separate services.
"""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import Request

from ...utils.logging_config import get_logger


class AuthenticationService:
    """
    Dedicated service for JWT authentication operations.
    
    Responsibilities:
    - Extract JWT tokens from HTTP requests
    - Validate and decode JWT tokens
    - Extract user information from token payloads
    
    NOT responsible for:
    - Session lifecycle management (handled by SessionTrackingService)
    - Audit logging (handled by AuditLoggingService)
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
        if not self.jwt_secret_key:
            self.logger.warning("JWT_SECRET_KEY not set, JWT authentication will fail")

    async def extract_user_from_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract user information from JWT token in request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User information dictionary if valid token found, None otherwise
        """
        try:
            # Get Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None
            
            token = auth_header.split(" ")[1]
            return await self.decode_jwt_token(token)
            
        except Exception as e:
            self.logger.debug(f"Error extracting user from request: {str(e)}")
            return None

    async def decode_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            User information dictionary if valid token, None otherwise
        """
        try:
            if not self.jwt_secret_key:
                self.logger.debug("JWT_SECRET_KEY not available, cannot decode token")
                return None
            
            # Decode JWT token
            from jose import jwt, JWTError
            
            payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
            
            user_id = payload.get("sub")
            if not user_id:
                self.logger.debug("JWT token missing 'sub' field")
                return None
            
            # Extract user information from payload
            user_info = {
                "id": user_id,
                "email": payload.get("email"),
                "permission": payload.get("permission"),
                "custom_capabilities": payload.get("custom_capabilities", {}),
                "token_issued_at": payload.get("iat"),
                "token_expires_at": payload.get("exp")
            }
            
            self.logger.debug(f"Successfully decoded JWT for user {user_id}")
            return user_info
            
        except JWTError as e:
            self.logger.debug(f"JWT decode error: {str(e)}")
            return None
        except Exception as e:
            self.logger.debug(f"Unexpected error decoding JWT: {str(e)}")
            return None

    def extract_ip_address(self, request: Request) -> str:
        """
        Extract client IP address from request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address string
        """
        # Check for forwarded headers first (for load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to client host
        client_host = getattr(request.client, 'host', 'unknown') if request.client else 'unknown'
        return client_host

    def extract_user_agent(self, request: Request) -> str:
        """
        Extract user agent string from request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User agent string
        """
        return request.headers.get("User-Agent", "Unknown")

    def parse_platform_from_user_agent(self, user_agent: str) -> str:
        """
        Parse platform information from user agent string.
        
        Args:
            user_agent: User agent string
            
        Returns:
            Platform name (Windows, macOS, Linux, etc.)
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

    def is_token_expired(self, user_info: Dict[str, Any]) -> bool:
        """
        Check if a decoded JWT token is expired.
        
        Args:
            user_info: User information from decoded JWT
            
        Returns:
            True if token is expired, False otherwise
        """
        try:
            import time
            exp = user_info.get("token_expires_at")
            if not exp:
                return False  # No expiration set
            
            current_time = time.time()
            return current_time > exp
            
        except Exception:
            return False  # Assume not expired if we can't determine