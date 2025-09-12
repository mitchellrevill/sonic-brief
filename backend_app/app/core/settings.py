# Enhanced Centralized Settings Management
# pydantic 2.5 moved BaseSettings to the separate `pydantic-settings` package.
# Import from that package when available, otherwise fall back to the
# older location so this module works across developer environments.
try:
    # preferred for pydantic >=2.5 environments
    from pydantic_settings import BaseSettings
except Exception:
    # older pydantic versions still expose BaseSettings here
    from pydantic import BaseSettings

from pydantic import Field
from typing import Dict, Any, Optional, List
import os
from functools import lru_cache

class CosmosSettings(BaseSettings):
    endpoint: str = Field(..., env="AZURE_COSMOS_ENDPOINT")
    key: str = Field(..., env="AZURE_COSMOS_KEY")
    database: str = Field("VoiceDB", env="AZURE_COSMOS_DB")
    prefix: str = Field("voice_", env="AZURE_COSMOS_DB_PREFIX")
    
    @property
    def containers(self) -> Dict[str, str]:
        return {
            "auth": f"{self.prefix}auth",
            "jobs": f"{self.prefix}jobs",
            "prompts": f"{self.prefix}prompts",
            "analytics": f"{self.prefix}analytics",
            "events": f"{self.prefix}events",
            "user_sessions": f"{self.prefix}user_sessions",
        }

class AuthSettings(BaseSettings):
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256")
    jwt_access_token_expire_minutes: int = Field(60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Microsoft SSO
    microsoft_client_id: Optional[str] = Field(None, env="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: Optional[str] = Field(None, env="MICROSOFT_CLIENT_SECRET")
    microsoft_tenant_id: Optional[str] = Field(None, env="MICROSOFT_TENANT_ID")

class CacheSettings(BaseSettings):
    cache_type: str = Field("in_memory", env="CACHE_TYPE")  # "in_memory" or "redis"
    default_ttl: int = Field(300, env="CACHE_DEFAULT_TTL")  # 5 minutes
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    key_prefix: str = Field("permission:", env="CACHE_KEY_PREFIX")

class AzureSettings(BaseSettings):
    """Azure services configuration"""
    storage_account_name: str = Field(..., env="AZURE_STORAGE_ACCOUNT_NAME")
    storage_account_key: str = Field(..., env="AZURE_STORAGE_ACCOUNT_KEY")
    storage_container_name: str = Field("uploads", env="AZURE_STORAGE_CONTAINER")
    
    # OpenAI/Cognitive Services
    openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    openai_key: str = Field(..., env="AZURE_OPENAI_KEY")
    openai_deployment_name: str = Field("gpt-4", env="AZURE_OPENAI_DEPLOYMENT")
    
    # Speech Service
    speech_service_key: str = Field(..., env="AZURE_SPEECH_KEY")
    speech_service_region: str = Field(..., env="AZURE_SPEECH_REGION")

class AppSettings(BaseSettings):
    """Application configuration"""
    app_name: str = Field("Sonic Brief API", env="APP_NAME")
    app_version: str = Field("1.0.0", env="APP_VERSION")
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    
    # CORS
    cors_origins: str = Field("*", env="CORS_ORIGINS")  # Comma-separated string
    cors_allow_credentials: bool = Field(True, env="CORS_ALLOW_CREDENTIALS")
    
    # Session Management
    session_timeout_minutes: int = Field(15, env="SESSION_TIMEOUT_MINUTES")
    session_heartbeat_interval_minutes: int = Field(5, env="SESSION_HEARTBEAT_INTERVAL")
    
    # File Processing
    max_file_size_mb: int = Field(100, env="MAX_FILE_SIZE_MB")
    allowed_file_types: str = Field(".mp3,.wav,.mp4,.m4a,.ogg", env="ALLOWED_FILE_TYPES")
    
    # Background Processing
    max_concurrent_jobs: int = Field(5, env="MAX_CONCURRENT_JOBS")
    job_retry_attempts: int = Field(3, env="JOB_RETRY_ATTEMPTS")
    job_retry_delay_seconds: int = Field(60, env="JOB_RETRY_DELAY")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Parse allowed file types from comma-separated string"""
        return [ext.strip() for ext in self.allowed_file_types.split(",")]

class Settings(BaseSettings):
    environment: str = Field("development", env="ENVIRONMENT")
    # Avoid constructing nested settings at import time since they may
    # require environment variables not present in local dev. Make them
    # optional and construct lazily in get_settings().
    cosmos: Optional[CosmosSettings] = None
    auth: Optional[AuthSettings] = None
    cache: Optional[CacheSettings] = None
    azure: Optional[AzureSettings] = None
    app: Optional[AppSettings] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    # Use .construct() to avoid triggering BaseSettings validation which
    # reads environment variables and can raise errors for unknown/extra
    # keys in developer .env files. We'll populate nested objects manually.
    s = Settings.construct()
    # Lazily construct CosmosSettings so missing AZURE_COSMOS_* env vars don't
    # break module import during local development. If validation fails, create
    # a small fallback object with the attributes used by callers.
    # Ensure .env is loaded into the process environment so BaseSettings
    # can pick up values when constructed directly. We avoid adding a
    # new dependency by reading the .env file if present.
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    # Don't overwrite existing env vars
                    os.environ.setdefault(k, v)
        except Exception:
            pass

    # Construct cosmos if missing
    if s.cosmos is None:
        # Ensure .env is loaded into the process environment so BaseSettings
        # can pick up values when constructed directly. We avoid adding a
        # new dependency by reading the .env file if present.
        try:
            s.cosmos = CosmosSettings()
        except Exception:
            class _FallbackCosmos:
                def __init__(self):
                    self.endpoint = os.getenv("AZURE_COSMOS_ENDPOINT", "")
                    self.key = os.getenv("AZURE_COSMOS_KEY", "")
                    self.database = os.getenv("AZURE_COSMOS_DB", "VoiceDB")
                    self.prefix = os.getenv("AZURE_COSMOS_DB_PREFIX", "voice_")

                @property
                def containers(self) -> Dict[str, str]:
                    p = self.prefix
                    return {
                        "auth": f"{p}auth",
                        "jobs": f"{p}jobs",
                        "prompts": f"{p}prompts",
                        "analytics": f"{p}analytics",
                        "events": f"{p}events",
                        "user_sessions": f"{p}user_sessions",
                    }

            s.cosmos = _FallbackCosmos()

    # Construct azure settings if missing (may be absent in local dev)
    if s.azure is None:
        try:
            s.azure = AzureSettings()
        except Exception:
            class _FallbackAzure:
                def __init__(self):
                    self.storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
                    self.storage_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
                    self.storage_container_name = os.getenv("AZURE_STORAGE_CONTAINER", "uploads")
                    self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
                    self.openai_key = os.getenv("AZURE_OPENAI_KEY", "")
                    self.openai_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
                    self.speech_service_key = os.getenv("AZURE_SPEECH_KEY", "")
                    self.speech_service_region = os.getenv("AZURE_SPEECH_REGION", "")

                # Add any properties callers expect here if needed

            s.azure = _FallbackAzure()

    # Construct defaults for other nested blocks if missing
    if s.auth is None:
        try:
            s.auth = AuthSettings()
        except Exception:
            s.auth = AuthSettings.construct()

    if s.cache is None:
        s.cache = CacheSettings.construct()

    if s.app is None:
        try:
            s.app = AppSettings()
        except Exception:
            s.app = AppSettings.construct()

    return s
