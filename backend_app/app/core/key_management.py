import logging
from typing import Optional
from .config import get_app_config

logger = logging.getLogger(__name__)


def get_functions_key() -> str:
    """Return the Azure Functions key from AppConfig, raising if missing."""
    config = get_app_config()
    key = getattr(config, 'azure_functions', {}).get('key')
    if not key:
        logger.error("Azure Functions key is not configured")
        raise ValueError("Azure Functions key not configured")
    return key


def validate_functions_key(candidate_key: str) -> bool:
    """Validate a provided key against the configured key (time-constant comparison recommended)."""
    real = get_functions_key()
    # Use simple comparison here; in production use hmac.compare_digest
    import hmac
    return hmac.compare_digest(real, candidate_key)


def rotate_functions_key(new_key: str) -> None:
    """Rotation stub: In production this should integrate with secret manager (KeyVault) and scheduling.
    This function intentionally does not modify runtime env; it is a placeholder for rotation flows.
    """
    logger.info("rotate_functions_key called - implement KeyVault rotation flow here")
    # TODO: Integrate with Azure Key Vault to rotate keys and update AppConfig via secure channel
