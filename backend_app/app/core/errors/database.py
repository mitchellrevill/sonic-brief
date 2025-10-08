"""
Database-specific exceptions for Cosmos DB operations.

This module provides a hierarchy of exceptions for database operations,
enabling specific error handling instead of catching generic Exception.
"""
from typing import Optional, Dict, Any
from .domain import ApplicationError, ErrorCode


class DatabaseError(ApplicationError):
    """Base exception for all database-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, error_code, status_code, details)


class ConnectionError(DatabaseError):
    """Raised when cannot connect to Cosmos DB."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Cannot connect to Cosmos DB"
        if endpoint:
            message += f" at {endpoint}"
        
        enriched_details = {"endpoint": endpoint} if endpoint else {}
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            503,
            enriched_details
        )


class AuthenticationError(DatabaseError):
    """Raised when Cosmos DB authentication fails."""
    
    def __init__(
        self,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = "Cosmos DB authentication failed"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message,
            ErrorCode.UNAUTHORIZED,
            401,
            details
        )


class QueryError(DatabaseError):
    """Raised when a Cosmos DB query fails."""
    
    def __init__(
        self,
        query: Optional[str] = None,
        container: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = "Database query failed"
        if reason:
            message += f": {reason}"
        
        enriched_details: Dict[str, Any] = {}
        if query:
            # Truncate long queries for logging
            enriched_details["query"] = query[:200] + "..." if len(query) > 200 else query
        if container:
            enriched_details["container"] = container
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            500,
            enriched_details
        )


class DocumentNotFoundError(DatabaseError):
    """Raised when a requested document doesn't exist."""
    
    def __init__(
        self,
        document_id: str,
        container: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Document '{document_id}' not found"
        if container:
            message += f" in container '{container}'"
        
        enriched_details = {
            "document_id": document_id,
            "container": container
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.RESOURCE_NOT_FOUND,
            404,
            enriched_details
        )


class ConflictError(DatabaseError):
    """Raised when a document operation conflicts (duplicate key, ETag mismatch, etc.)."""
    
    def __init__(
        self,
        reason: str,
        document_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Database conflict: {reason}"
        
        enriched_details: Dict[str, Any] = {}
        if document_id:
            enriched_details["document_id"] = document_id
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.RESOURCE_CONFLICT,
            409,
            enriched_details
        )


class PermissionDeniedError(DatabaseError):
    """Raised when access to a container or operation is denied."""
    
    def __init__(
        self,
        resource: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Permission denied for resource '{resource}'"
        if operation:
            message += f" (operation: {operation})"
        
        enriched_details = {
            "resource": resource,
            "operation": operation
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.FORBIDDEN,
            403,
            enriched_details
        )


class ContainerNotFoundError(DatabaseError):
    """Raised when a requested container doesn't exist."""
    
    def __init__(
        self,
        container_name: str,
        database: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Container '{container_name}' not found"
        if database:
            message += f" in database '{database}'"
        
        enriched_details = {
            "container_name": container_name,
            "database": database
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.RESOURCE_NOT_FOUND,
            404,
            enriched_details
        )


class ThrottlingError(DatabaseError):
    """Raised when Cosmos DB throttles requests (429 Too Many Requests)."""
    
    def __init__(
        self,
        retry_after_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = "Database request throttled"
        if retry_after_ms:
            message += f" (retry after {retry_after_ms}ms)"
        
        enriched_details: Dict[str, Any] = {}
        if retry_after_ms:
            enriched_details["retry_after_ms"] = retry_after_ms
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.QUOTA_EXCEEDED,
            429,
            enriched_details
        )


class TimeoutError(DatabaseError):
    """Raised when a database operation times out."""
    
    def __init__(
        self,
        operation: str,
        timeout_seconds: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Database operation '{operation}' timed out"
        if timeout_seconds:
            message += f" after {timeout_seconds}s"
        
        enriched_details = {
            "operation": operation,
            "timeout_seconds": timeout_seconds
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            504,
            enriched_details
        )


__all__ = [
    "DatabaseError",
    "ConnectionError",
    "AuthenticationError",
    "QueryError",
    "DocumentNotFoundError",
    "ConflictError",
    "PermissionDeniedError",
    "ContainerNotFoundError",
    "ThrottlingError",
    "TimeoutError",
]
