import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from app.models.permissions import PermissionLevel, PERMISSION_HIERARCHY, PERMISSION_CAPABILITIES
from app.utils.permission_cache import InMemoryPermissionCache
from app.services.permissions import PermissionService

@pytest.mark.asyncio
async def test_permission_cache_set_and_get():
    cache = InMemoryPermissionCache()
    await cache.set_user_permission("user1", PermissionLevel.EDITOR)
    result = await cache.get_user_permission("user1")
    assert result == PermissionLevel.EDITOR

@pytest.mark.asyncio
async def test_permission_service_hierarchy():
    service = PermissionService()
    assert service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.EDITOR)
    assert not service.has_permission_level(PermissionLevel.USER, PermissionLevel.ADMIN)

@pytest.mark.asyncio
async def test_permission_capabilities():
    assert PERMISSION_CAPABILITIES[PermissionLevel.ADMIN]["can_manage_users"]
    assert not PERMISSION_CAPABILITIES[PermissionLevel.USER].get("can_manage_users", False)

def test_permission_hierarchy():
    assert PERMISSION_HIERARCHY[PermissionLevel.USER] < PERMISSION_HIERARCHY[PermissionLevel.EDITOR]
    assert PERMISSION_HIERARCHY[PermissionLevel.EDITOR] < PERMISSION_HIERARCHY[PermissionLevel.ADMIN]
    assert PERMISSION_HIERARCHY[PermissionLevel.ADMIN] > PERMISSION_HIERARCHY[PermissionLevel.USER]

def test_permission_capabilities_keys():
    # All levels should be present
    for level in [PermissionLevel.USER, PermissionLevel.EDITOR, PermissionLevel.ADMIN]:
        assert level in PERMISSION_CAPABILITIES

def test_admin_has_all_capabilities():
    admin_caps = PERMISSION_CAPABILITIES[PermissionLevel.ADMIN]
    assert admin_caps["can_manage_users"]
    assert admin_caps["can_view_all_jobs"]
    assert admin_caps["can_edit_all_jobs"]
    assert admin_caps["can_delete_all_jobs"]

def test_editor_capabilities_subset_of_admin():
    editor_caps = set(PERMISSION_CAPABILITIES[PermissionLevel.EDITOR].keys())
    admin_caps = set(PERMISSION_CAPABILITIES[PermissionLevel.ADMIN].keys())
    assert editor_caps.issubset(admin_caps)

def test_user_capabilities_subset_of_editor():
    user_caps = set(PERMISSION_CAPABILITIES[PermissionLevel.USER].keys())
    editor_caps = set(PERMISSION_CAPABILITIES[PermissionLevel.EDITOR].keys())
    assert user_caps.issubset(editor_caps)
