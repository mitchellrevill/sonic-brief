from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Standardized error codes used across the application."""

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
    """Base application exception that captures rich error context."""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details: Dict[str, Any] = details or {}

    def as_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "error_code": self.error_code.value,
            "details": self.details,
        }


class AuthenticationError(ApplicationError):
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.UNAUTHORIZED, 401, details)


class PermissionError(ApplicationError):
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.INSUFFICIENT_PERMISSIONS, 403, details)


class ResourceNotFoundError(ApplicationError):
    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        message = f"{resource_type} with ID '{resource_id}' not found"
        enriched_details = {"resource_type": resource_type, "resource_id": resource_id}
        if details:
            enriched_details.update(details)
        super().__init__(message, ErrorCode.RESOURCE_NOT_FOUND, 404, enriched_details)


class ValidationError(ApplicationError):
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        details_dict: Dict[str, Any] = details.copy() if details else {}
        if field:
            details_dict.setdefault("field", field)
        super().__init__(message, ErrorCode.INVALID_INPUT, 400, details_dict)


class ResourceNotReadyError(ApplicationError):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, ErrorCode.RESOURCE_LOCKED, 409, details)
