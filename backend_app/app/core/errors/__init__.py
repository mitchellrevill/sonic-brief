from .domain import (
    ApplicationError,
    AuthenticationError,
    ErrorCode,
    PermissionError,
    ResourceNotFoundError,
    ResourceNotReadyError,
    ValidationError,
)
from .handler import ErrorHandler, DefaultErrorHandler
from .http import application_error_response

# Database exceptions
from .database import (
    DatabaseError,
    ConnectionError as DatabaseConnectionError,
    AuthenticationError as DatabaseAuthenticationError,
    QueryError,
    DocumentNotFoundError,
    ConflictError,
    PermissionDeniedError as DatabasePermissionError,
    ContainerNotFoundError as DatabaseContainerNotFoundError,
    ThrottlingError,
    TimeoutError as DatabaseTimeoutError,
)

# Storage exceptions
from .storage import (
    StorageError,
    BlobNotFoundError,
    BlobUploadError,
    BlobDownloadError,
    BlobDeleteError,
    SASTokenError,
    ContainerNotFoundError as StorageContainerNotFoundError,
    StorageAuthenticationError,
    StoragePermissionError,
    StorageQuotaExceededError,
    BlobTooLargeError,
)

__all__ = [
    # Core errors
    "ApplicationError",
    "AuthenticationError",
    "DefaultErrorHandler",
    "ErrorCode",
    "ErrorHandler",
    "PermissionError",
    "ResourceNotFoundError",
    "ResourceNotReadyError",
    "ValidationError",
    "application_error_response",
    # Database errors
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseAuthenticationError",
    "QueryError",
    "DocumentNotFoundError",
    "ConflictError",
    "DatabasePermissionError",
    "DatabaseContainerNotFoundError",
    "ThrottlingError",
    "DatabaseTimeoutError",
    # Storage errors
    "StorageError",
    "BlobNotFoundError",
    "BlobUploadError",
    "BlobDownloadError",
    "BlobDeleteError",
    "SASTokenError",
    "StorageContainerNotFoundError",
    "StorageAuthenticationError",
    "StoragePermissionError",
    "StorageQuotaExceededError",
    "BlobTooLargeError",
]
