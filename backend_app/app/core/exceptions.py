# Standardized Exception Handling
from fastapi import HTTPException, status
from typing import Any, Dict, Optional
import logging
from enum import Enum

class ErrorCode(Enum):
    """Standardized error codes"""
    # Authentication & Authorization
    UNAUTHORIZED = "AUTH_001"
    FORBIDDEN = "AUTH_002"
    INVALID_TOKEN = "AUTH_003"
    
    # Resource Errors
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_CONFLICT = "RES_002"
    RESOURCE_LOCKED = "RES_003"
    
    # Validation Errors
    INVALID_INPUT = "VAL_001"
    MISSING_REQUIRED_FIELD = "VAL_002"
    INVALID_FORMAT = "VAL_003"
    
    # Business Logic
    INSUFFICIENT_PERMISSIONS = "BIZ_001"
    QUOTA_EXCEEDED = "BIZ_002"
    OPERATION_NOT_ALLOWED = "BIZ_003"
    
    # System Errors
    INTERNAL_ERROR = "SYS_001"
    SERVICE_UNAVAILABLE = "SYS_002"
    EXTERNAL_SERVICE_ERROR = "SYS_003"

class ApplicationError(Exception):
    """Base application exception"""
    def __init__(self, message: str, error_code: ErrorCode, status_code: int = 500, details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

class AuthenticationError(ApplicationError):
    def __init__(self, message: str = "Authentication required", details: Optional[Dict] = None):
        super().__init__(message, ErrorCode.UNAUTHORIZED, 401, details)

class PermissionError(ApplicationError):
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict] = None):
        super().__init__(message, ErrorCode.INSUFFICIENT_PERMISSIONS, 403, details)

class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict] = None):
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(message, ErrorCode.RESOURCE_NOT_FOUND, 404, details)

class ValidationError(ApplicationError):
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, ErrorCode.INVALID_INPUT, 400, details)

def create_http_exception(error: ApplicationError) -> HTTPException:
    """Convert ApplicationError to HTTPException"""
    return HTTPException(
        status_code=error.status_code,
        detail={
            "message": error.message,
            "error_code": error.error_code.value,
            "details": error.details
        }
    )

def handle_service_error(func):
    """Decorator to standardize service error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ApplicationError:
            raise  # Re-raise application errors as-is
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.exception(f"Unexpected error in {func.__name__}")
            raise ApplicationError(
                "Internal server error", 
                ErrorCode.INTERNAL_ERROR, 
                500,
                {"original_error": str(e)}
            )
    return wrapper

async def handle_async_service_error(func):
    """Async version of service error handler"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ApplicationError:
            raise
        except Exception as e:
            logger = logging.getLogger(func.__module__)
            logger.exception(f"Unexpected error in {func.__name__}")
            raise ApplicationError(
                "Internal server error",
                ErrorCode.INTERNAL_ERROR,
                500, 
                {"original_error": str(e)}
            )
    return wrapper
