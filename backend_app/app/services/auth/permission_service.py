"""Compatibility wrapper for legacy permission_service API.

This module provides a thin adapter to the refactored permission model so
that any remaining imports don't immediately break. It intentionally keeps
behaviour minimal and defers to the new helpers in `app.models.permissions`
and `app.core.permissions`.
"""
from typing import Optional, Dict, Any
import logging
from ...core.config import AppConfig
from ...models.permissions import (
    PermissionLevel,
    has_permission_level,
    get_user_capabilities as model_get_user_capabilities,
)

logger = logging.getLogger(__name__)


def get_cosmos_db():
    """Get cosmos DB service - for testing purposes."""
    return None


class PermissionService:
    """Minimal compatibility PermissionService delegating to model helpers."""

    def __init__(self):
        self.cosmos = None

    def set_cosmos_db(self, cosmos_db):
        self.cosmos = cosmos_db

    async def get_user_permission(self, user_id: str) -> Optional[str]:
        try:
            if self.cosmos:
                user = await self.cosmos.get_user_by_id(user_id)
            else:
                # Try to get cosmos from global function if available
                cosmos = get_cosmos_db()
                if cosmos:
                    user = await cosmos.get_user_by_id(user_id)
                else:
                    # Fallback not available without cosmos instance
                    logger.warning(f"No cosmos instance available for user {user_id}")
                    return None
            return user.get("permission") if user else None
        except Exception as e:
            logger.warning(f"get_user_permission error for {user_id}: {e}")
            return None

    def has_permission_level_method(self, user_permission: str, required_permission: PermissionLevel) -> bool:
        """Check if user has required permission level using the model helper."""
        if not user_permission:
            return False
        return has_permission_level(user_permission, required_permission.value)

    def get_user_capabilities(self, permission: str, custom: Dict[str, bool] = None) -> Dict[str, bool]:
        """Return merged capability map for a permission + optional custom overrides.

        Note: Legacy code sometimes called this without passing custom overrides.
        """
        try:
            return model_get_user_capabilities(permission, custom or {})
        except TypeError:
            # Backwards compatibility if model_get_user_capabilities signature differs
            return model_get_user_capabilities(permission)

    def can(self, user_permission: str, capability: str) -> bool:
        """Check if user can perform a capability (simplified check)."""
        # Admin can do anything
        if user_permission and user_permission.title() == "Admin":
            return True
        
        # This is a simplified check - in reality you'd want more sophisticated logic
        caps = self.get_user_capabilities(user_permission, {})
        return caps.get(capability, False)

    def close(self):
        # no-op close for compatibility with DI lifecycle
        logger.info("PermissionService.close: no resources to close")


# Expose a global instance for backward compatibility
permission_service = PermissionService()

# Backwards-compatible convenience aliases (no-op decorators retained)
def require_permission(required_permission: PermissionLevel):
    """Deprecated no-op decorator retained for backward compatibility.

    Emits a debug log so remaining usages can be discovered and migrated to
    FastAPI dependency-based enforcement.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger.debug(
                "[DEPRECATED] require_permission decorator is a no-op. Replace with FastAPI dependency for %s.",
                required_permission.value,
            )
            return await func(*args, **kwargs)
        return wrapper
    return decorator

require_admin_permission = require_permission(PermissionLevel.ADMIN)
require_editor_permission = require_permission(PermissionLevel.EDITOR)
require_user_permission = require_permission(PermissionLevel.USER)
