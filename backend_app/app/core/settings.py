from pydantic import BaseSettings, Field
from typing import Dict, Any, Optional
import os
from functools import lru_cache

class CosmosSettings(BaseSettings):
    endpoint: str = Field(..., env="AZURE_COSMOS_ENDPOINT")
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

class CacheSettings(BaseSettings):
    cache_type: str = Field("in_memory", env="CACHE_TYPE")  # "in_memory" or "redis"
    default_ttl: int = Field(300, env="CACHE_DEFAULT_TTL")  # 5 minutes
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    key_prefix: str = Field("permission:", env="CACHE_KEY_PREFIX")

class Settings(BaseSettings):
    environment: str = Field("development", env="ENVIRONMENT")
    cosmos: CosmosSettings = CosmosSettings()
    auth: AuthSettings = AuthSettings()
    cache: CacheSettings = CacheSettings()
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
