"""
Clean dependency injection system for Sonic Brief API.
Replaces all singleton patterns with proper FastAPI dependency injection.
"""
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from azure.cosmos import CosmosClient, ContainerProxy
from azure.identity import DefaultAzureCredential
import logging

from .config import AppConfig, get_config
from .jwt_utils import decode_token, TokenDecodeError
from ..models.permissions import PermissionLevel, PERMISSION_HIERARCHY
from ..middleware.permission_middleware import get_current_user_id


security = HTTPBearer()


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
        except Exception:
            # Any exception means Cosmos is not available
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
                    except Exception:
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
                except Exception as ex:
                    logger.error("Failed to initialize Cosmos client with DefaultAzureCredential: %s", ex)
                    # Surface a clearer error for callers
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
            except Exception as e:
                endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT")
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
            except Exception as e:
                # Try raw container name as a fallback (in case environment uses different prefix)
                try:
                    logger.warning("Failed to get prefixed container '%s' (%s). Trying raw container name...", actual_name, str(e))
                    self._containers[container_name] = self.database.get_container_client(container_name)
                    logger.info("Fell back to raw container name '%s' for logical container '%s'", container_name, container_name)
                except Exception as e2:
                    endpoint = self.config.cosmos_endpoint or os.getenv("AZURE_COSMOS_ENDPOINT")
                    db = self.config.cosmos_database or os.getenv("AZURE_COSMOS_DB")
                    raise RuntimeError(
                        f"Failed to get Cosmos container '{actual_name}' or fallback '{container_name}'. Endpoint={endpoint!r}, Database={db!r}. Originals: {e}; {e2}"
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
        except Exception:
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
        except Exception:
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
        except Exception:
            return None

    async def create_user(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user document in the auth container."""
        try:
            container = self.get_container("auth")
            created = container.create_item(body=user_doc)
            return created
        except Exception as e:
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
        except Exception as e:
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
        except Exception:
            return None
    
    def create_job(self, job_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new job document"""
        try:
            container = self.get_container("jobs")
            return container.create_item(body=job_doc)
        except Exception as e:
            raise

    def update_job(self, job_id: str, job_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing job document (sync version)"""
        try:
            container = self.get_container("jobs")
            return container.replace_item(item=job_id, body=job_doc)
        except Exception as e:
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
        except Exception:
            return None

    async def update_job_async(self, job_id: str, job_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing job document (async version)"""
        try:
            container = self.get_container("jobs")
            return container.replace_item(item=job_id, body=job_doc)
        except Exception as e:
            raise


# Global instance for singleton pattern
_cosmos_service_instance: Optional[CosmosService] = None

def get_cosmos_service(config: AppConfig = Depends(get_app_config)) -> CosmosService:
    """Get CosmosDB service (singleton pattern)"""
    global _cosmos_service_instance
    if _cosmos_service_instance is None:
        _cosmos_service_instance = CosmosService(config)
    return _cosmos_service_instance


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
        except Exception as e:
            # Log audit failures but don't break the application
            print(f"Audit logging failed: {e}")


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
    except Exception as e:
        # Catch-all for unexpected errors
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


# === Legacy Service Stubs ===
# These maintain compatibility while we migrate the full application
# TODO: Remove these once all services are migrated to new architecture

def get_analytics_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Compatibility shim: return an AnalyticsService instance using CosmosService.
    
    This service was previously throwing NotImplementedError during migration.
    """
    from ..services.analytics.analytics_service import AnalyticsService
    return AnalyticsService(cosmos_service)


def get_file_security_service():
    """Provide FileSecurityService instance for dependency injection."""
    from ..services.storage import FileSecurityService
    return FileSecurityService()

# Global instance for singleton pattern
_storage_service_instance: Optional[Any] = None

def get_storage_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide StorageService instance for dependency injection (singleton pattern)."""
    global _storage_service_instance
    if _storage_service_instance is None:
        from ..services.storage import StorageService
        _storage_service_instance = StorageService(cosmos_service.config)
    return _storage_service_instance

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

def get_job_management_service(cosmos_service: CosmosService = Depends(get_cosmos_service), storage_service = Depends(get_storage_service)):
    """Provide JobManagementService with dependency injection"""
    from ..services.jobs.job_management_service import JobManagementService
    from ..services.storage import StorageService
    return JobManagementService(cosmos_service, storage_service)

def get_job_sharing_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide JobSharingService with dependency injection"""
    from ..services.jobs.job_sharing_service import JobSharingService
    return JobSharingService(cosmos_service)

def get_analysis_refinement_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide AnalysisRefinementService with dependency injection"""
    from ..services.jobs.analysis_refinement_service import AnalysisRefinementService
    return AnalysisRefinementService(cosmos_service)


# === New Modular Session Services ===

def get_session_tracking_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide SessionTrackingService with dependency injection - focused on session lifecycle only"""
    from app.services.monitoring.session_tracking_service import SessionTrackingService
    return SessionTrackingService(cosmos_service)


def get_audit_logging_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide AuditLoggingService with dependency injection - focused on audit logging only"""
    from ..services.monitoring.audit_logging_service import AuditLoggingService
    return AuditLoggingService(cosmos_service)


def get_authentication_service():
    """Provide AuthenticationService with dependency injection - focused on JWT handling only"""
    from ..services.auth.authentication_service import AuthenticationService
    return AuthenticationService()


# === Legacy Session Service (deprecated) ===

def get_session_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide SessionService with dependency injection
    
    DEPRECATED: Use get_session_tracking_service, get_audit_logging_service, 
    and get_authentication_service instead for better separation of concerns.
    
    Returns a SessionTrackingService instance that handles session tracking.
    This function now returns the newer SessionTrackingService for backwards compatibility.
    """
    from app.services.monitoring.session_tracking_service import SessionTrackingService
    from app.utils.logging_config import get_logger
    logger = get_logger(__name__)
    logger.warning("Legacy session service function called - using new SessionTrackingService instead")
    return SessionTrackingService(cosmos_service)


def get_export_service(cosmos_service: CosmosService = Depends(get_cosmos_service)):
    """Provide ExportService with dependency injection
    
    Returns an ExportService instance for data export operations.
    """
    from ..services.analytics.export_service import ExportService
    return ExportService(cosmos_service)


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
    "get_session_service",
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
]