"""
Simplified, consolidated configuration system.
Replaces both the old config.py AppConfig singleton and settings.py complexity.
"""
import os
from typing import Dict, List, Optional, Any
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from pydantic import Field
import os
from pathlib import Path


class DatabaseError(Exception):
    """Custom exception for database-related errors"""
    pass


class AppConfig(BaseSettings):
    """
    Single source of truth for all application configuration.
    Eliminates the config.py/settings.py duplication and singleton patterns.
    """
    
    # Allow extra fields for compatibility during migration
    model_config = {
        "extra": "allow",
        "env_file": ".env", 
        "case_sensitive": False
    }
    
    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    app_name: str = Field("Sonic Brief API", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    
    # Cosmos DB (temporary optional for minimal server testing)
    # Use uppercase AZURE_* env names by default but allow older lowercase during migration
    cosmos_endpoint: Optional[str] = Field(None, env="AZURE_COSMOS_ENDPOINT")
    cosmos_key: Optional[str] = Field(None, env="AZURE_COSMOS_KEY")
    cosmos_database: str = Field("VoiceDB", env="AZURE_COSMOS_DB")
    cosmos_prefix: str = Field("voice_", env="AZURE_COSMOS_DB_PREFIX")
    
    # Authentication
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256")
    jwt_access_token_expire_minutes: int = Field(60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Microsoft SSO (optional)
    microsoft_client_id: Optional[str] = Field(None, env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(None, env="MICROSOFT_CLIENT_SECRET")
    microsoft_tenant_id: Optional[str] = Field(None, env="MICROSOFT_TENANT_ID")
    
    # Azure Storage
    azure_storage_account_url: str = Field(..., env="AZURE_STORAGE_ACCOUNT_URL")
    azure_storage_key: Optional[str] = Field(None, env="AZURE_STORAGE_KEY")
    azure_storage_recordings_container: str = Field("uploads", env="AZURE_STORAGE_RECORDINGS_CONTAINER")
    
    # Azure OpenAI
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: Optional[str] = Field(None, env="AZURE_OPENAI_KEY")
    azure_openai_deployment: str = Field("gpt-4", env="AZURE_OPENAI_DEPLOYMENT")
    
    @property
    def storage(self) -> Dict[str, Any]:
        """Backward-compatible storage configuration for legacy StorageService"""
        return {
            "account_url": self.azure_storage_account_url,
            "recordings_container": self.azure_storage_recordings_container,
        }
    
    # Azure Speech Service
    azure_speech_key: Optional[str] = Field(None, env="AZURE_SPEECH_KEY")
    azure_speech_region: Optional[str] = Field(None, env="AZURE_SPEECH_REGION")
    
    # Azure Functions
    azure_functions_base_url: str = Field("http://localhost:7071", env="AZURE_FUNCTIONS_BASE_URL")
    azure_functions_key: str = Field(..., env="AZURE_FUNCTIONS_KEY")
    
    # CORS - SECURITY: Set CORS_ORIGINS to your frontend domain(s) in production
    # Example: "https://your-frontend.azurewebsites.net,https://custom-domain.com"
    # DO NOT use "*" in production - it allows any website to make authenticated requests
    # Default allows localhost for development - set CORS_ORIGINS env var for production
    frontend_url: Optional[str] = Field(None, env="FRONTEND_URL")
    cors_origins: str = Field(
        "http://localhost:3000",
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    
    # File Processing
    max_file_size_mb: int = Field(100, env="MAX_FILE_SIZE_MB")
    allowed_file_types: str = Field(".mp3,.wav,.mp4,.m4a,.ogg", env="ALLOWED_FILE_TYPES")
    
    # Session Management
    session_timeout_minutes: int = Field(15, env="SESSION_TIMEOUT_MINUTES")
    session_heartbeat_interval_minutes: int = Field(5, env="SESSION_HEARTBEAT_INTERVAL")
    
    # Background Processing
    max_concurrent_jobs: int = Field(5, env="MAX_CONCURRENT_JOBS")
    job_retry_attempts: int = Field(3, env="JOB_RETRY_ATTEMPTS")
    job_retry_delay_seconds: int = Field(60, env="JOB_RETRY_DELAY")
    
    # Cache Settings
    cache_type: str = Field("in_memory", env="CACHE_TYPE")
    cache_default_ttl: int = Field(300, env="CACHE_DEFAULT_TTL")
    cache_redis_url: Optional[str] = Field(None, env="REDIS_URL")
    cache_key_prefix: str = Field("permission:", env="CACHE_KEY_PREFIX")
    
    @property
    def cosmos_containers(self) -> Dict[str, str]:
        """Get all cosmos container names with prefix"""
        return {
            "auth": f"{self.cosmos_prefix}auth",
            "jobs": f"{self.cosmos_prefix}jobs",
            "prompts": f"{self.cosmos_prefix}prompts",
            "analytics": f"{self.cosmos_prefix}analytics",
            "events": f"{self.cosmos_prefix}events",
            "user_sessions": f"{self.cosmos_prefix}user_sessions",
            "audit_logs": f"{self.cosmos_prefix}audit_logs",
        }
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types from comma-separated string"""
        return [ext.strip() for ext in self.allowed_file_types.split(",")]

    @property
    def auth(self) -> Dict[str, Any]:
        """Backward-compatible mapping for legacy code expecting `config.auth[...]`"""
        return {
            "jwt_access_token_expire_minutes": self.jwt_access_token_expire_minutes,
            "jwt_refresh_token_expire_days": self.jwt_refresh_token_expire_days,
            "jwt_secret_key": self.jwt_secret_key,
            "jwt_algorithm": self.jwt_algorithm,
        }


@lru_cache()
def get_config() -> AppConfig:
    """
    Get application configuration.
    
    Uses @lru_cache to ensure single instance, but unlike the old singleton pattern,
    this can be easily mocked for testing and doesn't create global state.
    """
    # Ensure we load the `.env` file located in the repository `backend_app` directory
    # regardless of current working directory when the process starts.
    try:
        # Path: backend_app/app/core/config.py -> ../../.env
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            # Load .env into environment as a best-effort fallback so pydantic
            # BaseSettings can pick values even if python-dotenv isn't installed
            try:
                with env_path.open("r", encoding="utf-8") as fh:
                    for raw in fh:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Support lines like: KEY=VALUE or export KEY=VALUE
                        if line.lower().startswith("export "):
                            line = line[7:].strip()
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('\"').strip("\'")
                        # Only set if not already present in environment
                        if k and os.environ.get(k) is None:
                            os.environ[k] = v
            except Exception:
                pass

            return AppConfig()
    except Exception:
        pass

    # Fallback to default behaviour
    return AppConfig()