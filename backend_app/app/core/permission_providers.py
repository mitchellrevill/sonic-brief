"""Centralized permission cache and optimizer providers.

This module builds the permission cache and PermissionQueryOptimizer from
application config. It is safe to import from both `core.config` and
`core.dependencies` without creating circular imports.
"""
from functools import lru_cache
from typing import Any
import logging

from ..utils.permission_cache import get_permission_cache as _get_permission_cache
from ..utils.permission_queries import PermissionQueryOptimizer
from .config import get_app_config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_permission_cache():
    """Return a singleton permission cache instance based on app settings."""
    try:
        # settings may be resolved from config or environment internally
        return _get_permission_cache()
    except Exception as e:
        logger.warning(f"Falling back to default permission cache: {e}")
        return _get_permission_cache()


@lru_cache(maxsize=32)
def get_permission_optimizer(container_client: Any):
    """Return a PermissionQueryOptimizer bound to a container client.

    The optimizer is cached per-container to allow reuse in tests and runtime.
    """
    try:
        return PermissionQueryOptimizer(container=container_client, permission_cache=get_permission_cache())
    except Exception as e:
        logger.warning(f"PermissionQueryOptimizer construction failed: {e}")
        # Return a minimal shim that raises on use to make errors explicit
        class _Shim:
            async def get_users_by_permission(self, *a, **k):
                raise RuntimeError("PermissionQueryOptimizer unavailable")

            async def get_permission_counts(self):
                raise RuntimeError("PermissionQueryOptimizer unavailable")

            async def bulk_check_permissions(self, *a, **k):
                raise RuntimeError("PermissionQueryOptimizer unavailable")

        return _Shim()
