"""
Storage-specific exceptions for Azure Blob Storage operations.

This module provides a hierarchy of exceptions for storage operations,
enabling specific error handling instead of catching generic Exception.
"""
from typing import Optional, Dict, Any
from .domain import ApplicationError, ErrorCode


class StorageError(ApplicationError):
    """Base exception for all storage-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.EXTERNAL_SERVICE_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message, error_code, status_code, details)


class BlobNotFoundError(StorageError):
    """Raised when a requested blob doesn't exist."""
    
    def __init__(
        self,
        blob_name: str,
        container: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Blob '{blob_name}' not found"
        if container:
            message += f" in container '{container}'"
        
        enriched_details = {
            "blob_name": blob_name,
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


class BlobUploadError(StorageError):
    """Raised when blob upload fails."""
    
    def __init__(
        self,
        blob_name: str,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Failed to upload blob '{blob_name}'"
        if reason:
            message += f": {reason}"
        
        enriched_details = {"blob_name": blob_name}
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            500,
            enriched_details
        )


class BlobDownloadError(StorageError):
    """Raised when blob download fails."""
    
    def __init__(
        self,
        blob_name: str,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Failed to download blob '{blob_name}'"
        if reason:
            message += f": {reason}"
        
        enriched_details = {"blob_name": blob_name}
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            500,
            enriched_details
        )


class BlobDeleteError(StorageError):
    """Raised when blob deletion fails."""
    
    def __init__(
        self,
        blob_name: str,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Failed to delete blob '{blob_name}'"
        if reason:
            message += f": {reason}"
        
        enriched_details = {"blob_name": blob_name}
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            500,
            enriched_details
        )


class SASTokenError(StorageError):
    """Raised when SAS token generation or validation fails."""
    
    def __init__(
        self,
        reason: str,
        blob_url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"SAS token error: {reason}"
        
        enriched_details: Dict[str, Any] = {}
        if blob_url:
            # Don't include full URL with potential tokens
            enriched_details["blob_url"] = blob_url.split('?')[0]
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.EXTERNAL_SERVICE_ERROR,
            500,
            enriched_details
        )


class ContainerNotFoundError(StorageError):
    """Raised when a requested container doesn't exist."""
    
    def __init__(
        self,
        container_name: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Storage container '{container_name}' not found"
        
        enriched_details = {"container_name": container_name}
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.RESOURCE_NOT_FOUND,
            404,
            enriched_details
        )


class StorageAuthenticationError(StorageError):
    """Raised when storage authentication fails."""
    
    def __init__(
        self,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = "Storage authentication failed"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message,
            ErrorCode.UNAUTHORIZED,
            401,
            details
        )


class StoragePermissionError(StorageError):
    """Raised when storage operation is not permitted."""
    
    def __init__(
        self,
        operation: str,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Permission denied for storage operation '{operation}'"
        if resource:
            message += f" on resource '{resource}'"
        
        enriched_details = {
            "operation": operation,
            "resource": resource
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.FORBIDDEN,
            403,
            enriched_details
        )


class StorageQuotaExceededError(StorageError):
    """Raised when storage quota is exceeded."""
    
    def __init__(
        self,
        quota_type: str,
        current_value: Optional[int] = None,
        limit: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Storage quota exceeded: {quota_type}"
        if current_value and limit:
            message += f" ({current_value}/{limit})"
        
        enriched_details = {
            "quota_type": quota_type,
            "current_value": current_value,
            "limit": limit
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.QUOTA_EXCEEDED,
            429,
            enriched_details
        )


class BlobTooLargeError(StorageError):
    """Raised when attempting to upload a blob that exceeds size limits."""
    
    def __init__(
        self,
        blob_name: str,
        size_bytes: int,
        max_size_bytes: int,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        size_mb = size_bytes / (1024 * 1024)
        max_mb = max_size_bytes / (1024 * 1024)
        message = f"Blob '{blob_name}' too large ({size_mb:.1f}MB exceeds limit of {max_mb:.1f}MB)"
        
        enriched_details = {
            "blob_name": blob_name,
            "size_bytes": size_bytes,
            "size_mb": round(size_mb, 2),
            "max_size_bytes": max_size_bytes,
            "max_size_mb": round(max_mb, 2)
        }
        if details:
            enriched_details.update(details)
        
        super().__init__(
            message,
            ErrorCode.INVALID_INPUT,
            413,  # Payload Too Large
            enriched_details
        )


__all__ = [
    "StorageError",
    "BlobNotFoundError",
    "BlobUploadError",
    "BlobDownloadError",
    "BlobDeleteError",
    "SASTokenError",
    "ContainerNotFoundError",
    "StorageAuthenticationError",
    "StoragePermissionError",
    "StorageQuotaExceededError",
    "BlobTooLargeError",
]
