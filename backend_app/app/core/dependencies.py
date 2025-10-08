"""
Clean dependency injection system for Sonic Brief API.
Replaces all singleton patterns with proper FastAPI dependency injection.
"""
import os
from functools import lru_cache
from typing import Optional, Dict, Any, TYPE_CHECKING
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from azure.cosmos import CosmosClient, ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
import logging

from .config import AppConfig, get_config
from .errors.handler import DefaultErrorHandler, ErrorHandler
from ..utils.jwt_utils import decode_token, TokenDecodeError
from ..models.permissions import PermissionLevel, PERMISSION_HIERARCHY
from ..middleware.permission_middleware import get_current_user_id

if TYPE_CHECKING:
    from ..services.monitoring.session_tracking_service import SessionTrackingService
    from ..services.monitoring.audit_logging_service import AuditLoggingService
    from ..services.auth.authentication_service import AuthenticationService


security = HTTPBearer()


def get_error_handler(request: Request) -> ErrorHandler:
    """Provide a request-scoped error handler with structured context."""

    endpoint = request.scope.get("endpoint")
    module_name = getattr(endpoint, "__module__", "sonic_brief") if endpoint else "sonic_brief"
    logger_name = f"{module_name}.errors"
    base_context = {
        "path": request.url.path,
        "method": request.method,
    }
    return DefaultErrorHandler(lambda: logging.getLogger(logger_name), base_context=base_context)


# === Configuration Dependencies ===
def get_app_config() -> AppConfig:
    """Get application configuration - replaces old singleton pattern"""
    return get_config()


# === Database Service ===
class CosmosService:
    """
    CosmosDB service with proper dependency injection.
    No more singleton patterns or global state!
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self._client: Optional[CosmosClient] = None
        self._database = None
        self._containers: Dict[str, ContainerProxy] = {}
        self._is_available: Optional[bool] = None
    
    def is_available(self) -> bool:
        """Check if CosmosDB is available and accessible"""
        if self._is_available is not None:
            return self._is_available
        
        try:
            # Quick check - just try to get config values
            endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT") or os.getenv("azure_cosmos_endpoint")
            key = self.config.cosmos_key or os.getenv("AZURE_COSMOS_KEY") or os.getenv("azure_cosmos_key")
            
            if not endpoint or not key:
                # If no endpoint or key, Cosmos is not available
                self._is_available = False
                return False
            
            # For now, assume available if we have credentials
            # TODO: Could add actual connection test with timeout
            self._is_available = True
            return True
        except Exception as e:
            # Any exception means Cosmos is not available
            logger = logging.getLogger(__name__)
            logger.warning(
                "Cosmos DB availability check failed",
                extra={"error": str(e)}
            )
            self._is_available = False
            return False
    
    @property
    def client(self) -> CosmosClient:
        """Lazy-initialize Cosmos client"""
        if self._client is None:
            logger = logging.getLogger(__name__)

            # Prefer explicit key-based auth when a key is provided (common for local dev)
            key = self.config.cosmos_key or os.getenv("AZURE_COSMOS_KEY") or os.getenv("azure_cosmos_key")
            endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT") or os.getenv("azure_cosmos_endpoint")

            if key:
                # Use key-based auth
                logger.info("Using Cosmos key auth from configuration/env for Cosmos client initialization")
                extracted_key = None
                if isinstance(key, dict):
                    for candidate in (
                        "primaryMasterKey",
                        "masterKey",
                        "key",
                        "azure_cosmos_key",
                        "AZURE_COSMOS_KEY",
                        "primarymasterkey",
                    ):
                        if candidate in key and isinstance(key[candidate], str):
                            extracted_key = key[candidate]
                            break
                elif isinstance(key, str):
                    extracted_key = key
                else:
                    try:
                        extracted_key = str(key)
                    except (TypeError, ValueError) as e:
                        logger.warning(
                            "Failed to convert Cosmos key to string",
                            extra={"key_type": type(key).__name__, "error": str(e)}
                        )
                        extracted_key = None

                if not extracted_key:
                    raise RuntimeError(
                        "Unrecognized Cosmos DB key format. Provide a string master key or a TokenCredential implementation."
                    )

                if not endpoint:
                    raise RuntimeError("Cosmos DB endpoint not configured. Set 'AZURE_COSMOS_ENDPOINT' env var.")

                self._client = CosmosClient(url=endpoint, credential=extracted_key)
            else:
                # No key present; fall back to DefaultAzureCredential for managed identity / CLI-based auth
                try:
                    logger.info("No Cosmos key found in env/config; attempting DefaultAzureCredential")
                    credential = DefaultAzureCredential()
                    endpoint = endpoint
                    if not endpoint:
                        raise RuntimeError("Cosmos DB endpoint not configured. Set 'AZURE_COSMOS_ENDPOINT' env var.")
                    self._client = CosmosClient(
                        url=endpoint,
                        credential=credential
                    )
                except CosmosHttpResponseError as ex:
                    logger.error(
                        "Failed to initialize Cosmos client with DefaultAzureCredential - Cosmos error",
                        exc_info=True,
                        extra={
                            "endpoint": endpoint,
                            "status_code": ex.status_code,
                            "error_message": str(ex)
                        }
                    )
                    raise
                except Exception as ex:
                    logger.error(
                        "Failed to initialize Cosmos client with DefaultAzureCredential - Unexpected error",
                        exc_info=True,
                        extra={"endpoint": endpoint}
                    )
                    raise
        return self._client
        return self._client
    
    @property
    def database(self):
        """Get database reference"""
        if self._database is None:
            # Prefer explicit AppConfig value, but fall back to env var if present
            # Prefer explicit environment variable (deployment) over AppConfig default
            db_name = (
                os.getenv("AZURE_COSMOS_DB")
                or os.getenv("azure_cosmos_db")
                or self.config.cosmos_database
            )
            if not db_name:
                raise RuntimeError("Cosmos DB name not configured. Set 'AZURE_COSMOS_DB' env var.")

            try:
                self._database = self.client.get_database_client(db_name)
            except CosmosHttpResponseError as e:
                endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT")
                logger = logging.getLogger(__name__)
                logger.error(
                    "Failed to get Cosmos database client - Cosmos error",
                    exc_info=True,
                    extra={
                        "database_name": db_name,
                        "endpoint": endpoint,
                        "status_code": e.status_code,
                        "error_message": str(e)
                    }
                )
                raise RuntimeError(
                    f"Failed to get Cosmos database client for '{db_name}'. Endpoint={endpoint!r}. Status={e.status_code}. Original: {e}"
                )
            except Exception as e:
                endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT")
                logger = logging.getLogger(__name__)
                logger.error(
                    "Failed to get Cosmos database client - Unexpected error",
                    exc_info=True,
                    extra={"database_name": db_name, "endpoint": endpoint}
                )
                raise RuntimeError(
                    f"Failed to get Cosmos database client for '{db_name}'. Endpoint={endpoint!r}. Original: {e}"
                )
        return self._database
    
    def get_container(self, container_name: str) -> ContainerProxy:
        """Get container reference with caching"""
        if container_name not in self._containers:
            logger = logging.getLogger(__name__)
            actual_name = self.config.cosmos_containers.get(container_name, container_name)
            try:
                self._containers[container_name] = self.database.get_container_client(actual_name)
            except CosmosResourceNotFoundError as e:
                # Try raw container name as a fallback (in case environment uses different prefix)
                try:
                    logger.warning(
                        "Prefixed container not found, trying raw container name",
                        extra={
                            "prefixed_name": actual_name,
                            "raw_name": container_name,
                            "status_code": e.status_code
                        }
                    )
                    self._containers[container_name] = self.database.get_container_client(container_name)
                    logger.info(
                        "Successfully fell back to raw container name",
                        extra={"container_name": container_name}
                    )
                except CosmosHttpResponseError as e2:
                    endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT")
                    db = self.config.cosmos_database or os.getenv("AZURE_COSMOS_DB")
                    logger.error(
                        "Failed to get Cosmos container with both prefixed and raw names",
                        exc_info=True,
                        extra={
                            "prefixed_name": actual_name,
                            "raw_name": container_name,
                            "endpoint": endpoint,
                            "database": db,
                            "status_code": e2.status_code
                        }
                    )
                    raise RuntimeError(
                        f"Container not found: '{actual_name}' or '{container_name}'. Endpoint={endpoint!r}, Database={db!r}. Status={e2.status_code}"
                    )
                except Exception as e2:
                    endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT")
                    db = self.config.cosmos_database or os.getenv("AZURE_COSMOS_DB")
                    logger.error(
                        "Unexpected error during container fallback",
                        exc_info=True,
                        extra={
                            "prefixed_name": actual_name,
                            "raw_name": container_name,
                            "endpoint": endpoint,
                            "database": db
                        }
                    )
                    raise RuntimeError(
                        f"Failed to get Cosmos container '{actual_name}' or fallback '{container_name}'. Endpoint={endpoint!r}, Database={db!r}. Originals: {e}; {e2}"
                    )
            except CosmosHttpResponseError as e:
                logger.error(
                    "Cosmos error getting container",
                    exc_info=True,
                    extra={
                        "container_name": actual_name,
                        "status_code": e.status_code,
                        "error_message": str(e)
                    }
                )
                raise RuntimeError(
                    f"Failed to get Cosmos container '{actual_name}'. Status={e.status_code}. Error: {e}"
                )
            except Exception as e:
                logger.error(
                    "Unexpected error getting container",
                    exc_info=True,
                    extra={"container_name": actual_name}
                )
                raise RuntimeError(
                    f"Failed to get Cosmos container '{actual_name}'. Error: {e}"
                )
        return self._containers[container_name]
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            container = self.get_container("auth")
            query = "SELECT * FROM c WHERE c.id = @user_id AND c.type = 'user'"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@user_id", "value": user_id}],
                enable_cross_partition_query=True
            ))
            return items[0] if items else None
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to query user by ID from Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error querying user by ID",
                exc_info=True,
                extra={"user_id": user_id}
            )
            return None
    
    async def get_all_users(self) -> list:
        """Get all users"""
        try:
            container = self.get_container("auth")
            query = "SELECT * FROM c WHERE c.type = 'user'"
            return list(container.query_items(
                query=query,
                enable_cross_partition_query=True
            ))
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to query all users from Cosmos DB",
                exc_info=True,
                extra={
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return []
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error querying all users",
                exc_info=True
            )
            return []

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get a user by email address (case-insensitive where possible)."""
        try:
            container = self.get_container("auth")
            # Use parameterized query to avoid injection
            query = "SELECT * FROM c WHERE c.type = 'user' AND (LOWER(c.email) = LOWER(@email) OR c.email = @email)"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@email", "value": email}],
                enable_cross_partition_query=True
            ))
            return items[0] if items else None
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to query user by email from Cosmos DB",
                exc_info=True,
                extra={
                    "email": email,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error querying user by email",
                exc_info=True,
                extra={"email": email}
            )
            return None

    async def create_user(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user document in the auth container."""
        try:
            container = self.get_container("auth")
            created = container.create_item(body=user_doc)
            return created
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to create user in Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_doc.get("id"),
                    "email": user_doc.get("email"),
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error creating user",
                exc_info=True,
                extra={
                    "user_id": user_doc.get("id"),
                    "email": user_doc.get("email")
                }
            )
            raise

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing user document by merging fields and replacing the item.

        Raises ValueError if user not found.
        """
        try:
            container = self.get_container("auth")
            # Find existing item
            existing = await self.get_user_by_id(user_id)
            if not existing:
                raise ValueError(f"User with id {user_id} not found")

            # Merge updates into existing
            existing.update(updates)
            # Replace item in container
            replaced = container.replace_item(item=existing.get("id"), body=existing)
            return replaced
        except ValueError:
            raise
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to update user in Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error updating user",
                exc_info=True,
                extra={"user_id": user_id}
            )
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user document by ID.

        Returns True if user was deleted, False if user was not found.
        """
        try:
            container = self.get_container("auth")
            # Try to delete the item
            container.delete_item(item=user_id, partition_key=user_id)
            return True
        except CosmosResourceNotFoundError:
            # User not found - this is not an error for delete operations
            return False
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to delete user from Cosmos DB",
                exc_info=True,
                extra={
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error deleting user",
                exc_info=True,
                extra={"user_id": user_id}
            )
            raise
    
    # Job-related methods for compatibility with JobService
    @property
    def jobs_container(self):
        """Legacy compatibility: provide jobs_container property"""
        return self.get_container("jobs")
    
    @property
    def analytics_container(self):
        """Legacy compatibility: provide analytics_container property"""
        return self.get_container("analytics")

    @property
    def sessions_container(self):
        """Provide sessions container reference (user sessions)."""
        return self.get_container("user_sessions")
    
    @property
    def audit_container(self):
        """Provide audit logs container reference."""
        return self.get_container("audit_logs")
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        try:
            container = self.get_container("jobs")
            query = "SELECT * FROM c WHERE c.id = @job_id AND c.type = 'job'"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@job_id", "value": job_id}],
                enable_cross_partition_query=True
            ))
            return items[0] if items else None
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to query job by ID from Cosmos DB",
                exc_info=True,
                extra={
                    "job_id": job_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error querying job by ID",
                exc_info=True,
                extra={"job_id": job_id}
            )
            return None
    
    def create_job(self, job_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job document"""
        try:
            container = self.get_container("jobs")
            return container.create_item(body=job_doc)
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to create job in Cosmos DB",
                exc_info=True,
                extra={
                    "job_id": job_doc.get("id"),
                    "user_id": job_doc.get("user_id"),
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error creating job",
                exc_info=True,
                extra={
                    "job_id": job_doc.get("id"),
                    "user_id": job_doc.get("user_id")
                }
            )
            raise

    def update_job(self, job_id: str, job_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing job document (sync version)"""
        try:
            container = self.get_container("jobs")
            return container.replace_item(item=job_id, body=job_doc)
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to update job in Cosmos DB",
                exc_info=True,
                extra={
                    "job_id": job_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error updating job",
                exc_info=True,
                extra={"job_id": job_id}
            )
            raise

    async def get_job_by_id_async(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID (async version)"""
        try:
            container = self.get_container("jobs")
            query = "SELECT * FROM c WHERE c.id = @job_id AND c.type = 'job'"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@job_id", "value": job_id}],
                enable_cross_partition_query=True
            ))
            return items[0] if items else None
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to query job by ID (async) from Cosmos DB",
                exc_info=True,
                extra={
                    "job_id": job_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error querying job by ID (async)",
                exc_info=True,
                extra={"job_id": job_id}
            )
            return None

    async def update_job_async(self, job_id: str, job_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing job document (async version)"""
        try:
            container = self.get_container("jobs")
            return container.replace_item(item=job_id, body=job_doc)
        except CosmosHttpResponseError as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to update job (async) in Cosmos DB",
                exc_info=True,
                extra={
                    "job_id": job_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            raise
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error updating job (async)",
                exc_info=True,
                extra={"job_id": job_id}
            )
            raise


@lru_cache()
def _build_cosmos_service() -> CosmosService:
    config = get_config()
    return CosmosService(config)


def get_cosmos_service() -> CosmosService:
    """Get the cached CosmosDB service instance."""
    return _build_cosmos_service()


# === Audit Service ===
class AuditService:
    """
    Audit logging service with dependency injection.
    No more global singleton!
    """
    
    def __init__(self, cosmos_service: CosmosService):
        self.cosmos_service = cosmos_service
    
    async def log_access_denied(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        required_capability: str,
        user_permission: str,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """Log access denied event"""
        try:
            container = self.cosmos_service.get_container("audit_logs")
            
            audit_entry = {
                "id": f"audit_{user_id}_{resource_type}_{resource_id}",
                "type": "audit_log",
                "event_type": "access_denied",
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "required_capability": required_capability,
                "user_permission": user_permission,
                "endpoint": endpoint,
                "ip_address": ip_address,
                "timestamp": "datetime.utcnow().isoformat()",
            }
            
            container.create_item(body=audit_entry)
        except CosmosHttpResponseError as e:
            # Log audit failures but don't break the application
            logger = logging.getLogger(__name__)
            logger.error(
                "Failed to create audit log entry in Cosmos DB",
                exc_info=True,
                extra={
                    "event_type": "access_denied",
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
        except Exception as e:
            # Log audit failures but don't break the application
            logger = logging.getLogger(__name__)
            logger.error(
                "Unexpected error creating audit log entry",
                exc_info=True,
                extra={
                    "event_type": "access_denied",
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id
                }
            )


def get_audit_service(cosmos_service: CosmosService = Depends(get_cosmos_service)) -> AuditService:
    """Get audit logging service"""
    return AuditService(cosmos_service)


# === Authentication Dependencies ===
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
) -> Dict[str, Any]:
    """Get current authenticated user"""
    try:
        # Decode JWT token
        token = credentials.credentials
        payload = decode_token(token)

        # Try to obtain internal user id from `sub`, fall back to email if needed
        user_id = payload.get("sub")
        user_email = payload.get("email")

        if not user_id and not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject/email"
            )

        # Resolve user by id first, otherwise by email.
        # Some tokens use the email address as `sub` (legacy). If `sub` looks like
        # an email and lookup by id fails, try resolving by email.
        user = None
        if user_id:
            user = await cosmos_service.get_user_by_id(user_id)
        # If sub looks like an email, try email lookup
        if not user and isinstance(user_id, str) and "@" in user_id:
            user = await cosmos_service.get_user_by_email(user_id)
        # Fallback: explicit email claim
        if not user and user_email:
            user = await cosmos_service.get_user_by_email(user_email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        return user

    except TokenDecodeError as e:
        detail = str(e) or "Invalid token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {detail}"
        )
    except HTTPException:
        # Re-raise HTTPExceptions (like we raised above)
        raise
    except CosmosHttpResponseError as e:
        # Log Cosmos errors during user lookup
        logger = logging.getLogger(__name__)
        logger.error(
            "Cosmos DB error during user authentication",
            exc_info=True,
            extra={
                "user_id": payload.get("sub") if 'payload' in locals() else "unknown",
                "status_code": e.status_code,
                "error_message": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication service unavailable"
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger = logging.getLogger(__name__)
        logger.error(
            "Unexpected error during user authentication",
            exc_info=True,
            extra={"user_id": payload.get("sub") if 'payload' in locals() else "unknown"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication: {str(e)}"
        )


# === Permission Dependencies ===
async def require_permission(
    required_permission: PermissionLevel,
    current_user: Dict[str, Any] = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
) -> Dict[str, Any]:
    """Require user to have specific permission level"""
    user_permission = current_user.get("permission", "User")
    user_permission_level = PERMISSION_HIERARCHY.get(user_permission, 0)
    required_permission_level = PERMISSION_HIERARCHY.get(required_permission.value, 0)
    
    if user_permission_level < required_permission_level:
        # Log access denied
        await audit_service.log_access_denied(
            user_id=current_user.get("id", "unknown"),
            resource_type="permission_check",
            resource_id=required_permission.value,
            required_capability=required_permission.value,
            user_permission=user_permission
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {required_permission.value}, User has: {user_permission}"
        )
    
    return current_user


# === Specific Permission Functions ===
def create_permission_dependency(required_permission: PermissionLevel):
    """Factory function to create permission dependencies"""
    async def permission_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
        audit_service: AuditService = Depends(get_audit_service)
    ) -> Dict[str, Any]:
        return await require_permission(required_permission, current_user, audit_service)
    return permission_dependency


# Create permission dependencies
require_admin = create_permission_dependency(PermissionLevel.ADMIN)
require_editor = create_permission_dependency(PermissionLevel.EDITOR)
require_user = create_permission_dependency(PermissionLevel.USER)


# === Backward Compatibility ===
async def require_admin_user_id(current_user: Dict[str, Any] = Depends(require_admin)) -> str:
    """Backward compatibility: return user_id instead of full user object"""
    return current_user.get("id", "")

async def require_editor_user_id(current_user: Dict[str, Any] = Depends(require_editor)) -> str:
    """Backward compatibility: return user_id instead of full user object"""
    return current_user.get("id", "")

async def require_user_user_id(current_user: Dict[str, Any] = Depends(require_user)) -> str:
    """Backward compatibility: return user_id instead of full user object"""
    return current_user.get("id", "")

async def require_analytics_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require analytics viewing access (Editor or Admin level)"""
    from ..models.permissions import PermissionLevel, has_permission_level
    user_permission = current_user.get("permission")
    
    if not has_permission_level(user_permission, PermissionLevel.EDITOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics access requires Editor or Admin permission level."
        )
    return current_user


# === Service Providers ===
# Centralized factories for core domain services

@lru_cache()
def _build_analytics_service():
    from ..services.analytics.analytics_service import AnalyticsService
    cosmos_service = get_cosmos_service()
    return AnalyticsService(cosmos_service)


def get_analytics_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Compatibility shim: return a cached AnalyticsService instance."""
    return _build_analytics_service()


def get_file_security_service():
    """Provide FileSecurityService instance for dependency injection."""
    from ..services.storage import FileSecurityService
    return FileSecurityService()

@lru_cache()
def _build_storage_service():
    from ..services.storage import StorageService
    config = get_config()
    return StorageService(config)


def get_storage_service():
    """Provide StorageService instance for dependency injection."""
    return _build_storage_service()

def get_job_service(
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    storage_service = Depends(get_storage_service)
):
    """Compatibility shim: return a JobService instance using the provided services.

    Previously this raised NotImplementedError while the service migration was in
    progress. For local development and to support existing routers we return a
    JobService constructed with the DI-provided services.
    """
    from ..services.jobs.job_service import JobService
    
    return JobService(cosmos_service, storage_service)

def get_job_management_service(
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    job_service = Depends(get_job_service),
):
    """Provide JobManagementService with dependency injection"""
    from ..services.jobs.job_management_service import JobManagementService

    return JobManagementService(cosmos_service, job_service)

def get_job_sharing_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide JobSharingService with dependency injection"""
    from ..services.jobs.job_sharing_service import JobSharingService
    return JobSharingService(cosmos_service)

def get_analysis_refinement_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide AnalysisRefinementService with dependency injection"""
    from ..services.jobs.analysis_refinement_service import AnalysisRefinementService
    return AnalysisRefinementService(cosmos_service)


# === New Modular Session Services ===

@lru_cache()
def _build_session_tracking_service():
    from ..services.monitoring.session_tracking_service import SessionTrackingService
    return SessionTrackingService(get_cosmos_service())


def get_session_tracking_service() -> "SessionTrackingService":
    """Provide SessionTrackingService with dependency injection - focused on session lifecycle only"""
    return _build_session_tracking_service()


@lru_cache()
def _build_audit_logging_service():
    from ..services.monitoring.audit_logging_service import AuditLoggingService
    return AuditLoggingService(get_cosmos_service())


def get_audit_logging_service() -> "AuditLoggingService":
    """Provide AuditLoggingService with dependency injection - focused on audit logging only"""
    return _build_audit_logging_service()


@lru_cache()
def _build_authentication_service():
    from ..services.auth.authentication_service import AuthenticationService
    return AuthenticationService()


def get_authentication_service() -> "AuthenticationService":
    """Provide AuthenticationService with dependency injection - focused on JWT handling only"""
    return _build_authentication_service()


@lru_cache()
def _build_export_service():
    from ..services.analytics.export_service import ExportService
    return ExportService(
        cosmos_service=get_cosmos_service(),
        analytics_service=get_analytics_service()
    )


def get_export_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide ExportService with dependency injection using cached instances."""
    return _build_export_service()


def get_prompt_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide PromptService with dependency injection
    
    Returns a PromptService instance for prompt management operations.
    """
    from ..services.prompts.prompt_service import PromptService
    return PromptService(cosmos_service)


def get_system_health_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide SystemHealthService with dependency injection
    
    Returns a SystemHealthService instance for system health monitoring.
    Uses the shared CosmosService instance.
    """
    from ..services.monitoring.system_health_service import SystemHealthService
    return SystemHealthService(cosmos_service)


def get_talking_points_service():
    """Provide TalkingPointsService with dependency injection
    
    Returns a TalkingPointsService instance for talking points validation.
    """
    from ..services.prompts.talking_points_service import TalkingPointsService
    return TalkingPointsService()


# === Exports ===
__all__ = [
    "get_app_config",
    "get_cosmos_service", 
    "get_audit_service",
    "get_export_service",
    "get_prompt_service",
    "get_system_health_service",
    "get_talking_points_service",
    "CosmosService",
    "AuditService",
    "require_admin",
    "require_editor", 
    "require_user",
    "get_current_user",
    "require_admin_user_id",
    "require_editor_user_id",
    "require_user_user_id",
    "require_analytics_access",
    "get_job_management_service",
    "get_job_sharing_service",
    "get_analysis_refinement_service",
    "reset_dependency_caches",
]


def reset_dependency_caches() -> None:
    """Clear cached dependency instances (useful for testing)."""
    _build_cosmos_service.cache_clear()
    _build_analytics_service.cache_clear()
    _build_storage_service.cache_clear()
    _build_export_service.cache_clear()
    _build_session_tracking_service.cache_clear()
    _build_audit_logging_service.cache_clear()
    _build_authentication_service.cache_clear()