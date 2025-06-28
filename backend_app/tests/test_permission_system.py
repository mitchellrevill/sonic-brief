"""
Tests for the new resource-based permission system
"""
import pytest
from unittest.mock import patch, MagicMock
from app.models.permissions import (
    PermissionLevel, 
    PermissionCapability,
    can_user_perform_action,
    get_user_capabilities,
    merge_custom_capabilities
)
from app.services.permissions import PermissionService
from app.utils.permission_cache import InMemoryPermissionCache

class TestPermissionModels:
    """Test permission models and utility functions"""
    
    def test_permission_hierarchy(self):
        """Test that permission hierarchy is working correctly"""
        # User permissions
        assert can_user_perform_action(PermissionLevel.USER, PermissionCapability.CAN_VIEW_OWN_JOBS) == True
        assert can_user_perform_action(PermissionLevel.USER, PermissionCapability.CAN_CREATE_JOBS) == True
        assert can_user_perform_action(PermissionLevel.USER, PermissionCapability.CAN_MANAGE_USERS) == False
        
        # Editor permissions  
        assert can_user_perform_action(PermissionLevel.EDITOR, PermissionCapability.CAN_VIEW_OWN_JOBS) == True
        assert can_user_perform_action(PermissionLevel.EDITOR, PermissionCapability.CAN_EDIT_SHARED_JOBS) == True
        assert can_user_perform_action(PermissionLevel.EDITOR, PermissionCapability.CAN_MANAGE_USERS) == False
        
        # Admin permissions
        assert can_user_perform_action(PermissionLevel.ADMIN, PermissionCapability.CAN_VIEW_OWN_JOBS) == True
        assert can_user_perform_action(PermissionLevel.ADMIN, PermissionCapability.CAN_MANAGE_USERS) == True
        assert can_user_perform_action(PermissionLevel.ADMIN, PermissionCapability.CAN_MANAGE_SYSTEM) == True
    
    def test_get_user_capabilities(self):
        """Test getting capabilities for each permission level"""
        user_caps = get_user_capabilities(PermissionLevel.USER)
        assert user_caps[PermissionCapability.CAN_VIEW_OWN_JOBS] == True
        assert user_caps.get(PermissionCapability.CAN_MANAGE_USERS, False) == False
        
        admin_caps = get_user_capabilities(PermissionLevel.ADMIN)
        assert admin_caps[PermissionCapability.CAN_MANAGE_USERS] == True
        assert admin_caps[PermissionCapability.CAN_MANAGE_SYSTEM] == True
    
    def test_merge_custom_capabilities(self):
        """Test merging custom capabilities with base capabilities"""
        base_caps = get_user_capabilities(PermissionLevel.USER)
        custom_caps = {PermissionCapability.CAN_MANAGE_USERS: True}
        
        merged = merge_custom_capabilities(base_caps, custom_caps)
        assert merged[PermissionCapability.CAN_VIEW_OWN_JOBS] == True  # From base
        assert merged[PermissionCapability.CAN_MANAGE_USERS] == True   # From custom

class TestPermissionService:
    """Test permission service functionality"""
    
    @pytest.fixture
    def permission_cache(self):
        return InMemoryPermissionCache()
    
    @pytest.fixture  
    def permission_service(self, permission_cache):
        return PermissionService(permission_cache)
    
    @pytest.mark.asyncio
    async def test_has_permission_level(self, permission_service):
        """Test permission level hierarchy checking"""
        assert permission_service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.USER) == True
        assert permission_service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.EDITOR) == True
        assert permission_service.has_permission_level(PermissionLevel.ADMIN, PermissionLevel.ADMIN) == True
        
        assert permission_service.has_permission_level(PermissionLevel.EDITOR, PermissionLevel.USER) == True
        assert permission_service.has_permission_level(PermissionLevel.EDITOR, PermissionLevel.EDITOR) == True
        assert permission_service.has_permission_level(PermissionLevel.EDITOR, PermissionLevel.ADMIN) == False
        
        assert permission_service.has_permission_level(PermissionLevel.USER, PermissionLevel.USER) == True
        assert permission_service.has_permission_level(PermissionLevel.USER, PermissionLevel.EDITOR) == False
        assert permission_service.has_permission_level(PermissionLevel.USER, PermissionLevel.ADMIN) == False
    
    @pytest.mark.asyncio
    async def test_can_method(self, permission_service):
        """Test the can method for capability checking"""
        assert permission_service.can(PermissionLevel.USER, PermissionCapability.CAN_VIEW_OWN_JOBS) == True
        assert permission_service.can(PermissionLevel.USER, PermissionCapability.CAN_MANAGE_USERS) == False
        assert permission_service.can(PermissionLevel.ADMIN, PermissionCapability.CAN_MANAGE_USERS) == True

class TestPermissionCache:
    """Test permission caching functionality"""
    
    @pytest.fixture
    def cache(self):
        return InMemoryPermissionCache()
    
    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, cache):
        """Test basic cache set/get operations"""
        user_id = "test_user_123"
        permission = PermissionLevel.EDITOR
        
        # Test setting and getting
        await cache.set_user_permission(user_id, permission)
        cached_permission = await cache.get_user_permission(user_id)
        assert cached_permission == permission
        
        # Test cache miss
        missing_permission = await cache.get_user_permission("nonexistent_user")
        assert missing_permission is None
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache):
        """Test cache invalidation"""
        user_id = "test_user_123"
        permission = PermissionLevel.ADMIN
        
        await cache.set_user_permission(user_id, permission)
        await cache.invalidate_user_cache(user_id)
        
        cached_permission = await cache.get_user_permission(user_id)
        assert cached_permission is None
    
    @pytest.mark.asyncio
    async def test_multiple_permissions(self, cache):
        """Test bulk permission operations"""
        permissions = {
            "user1": PermissionLevel.USER,
            "user2": PermissionLevel.EDITOR,
            "user3": PermissionLevel.ADMIN
        }
        
        await cache.set_multiple_permissions(permissions)
        
        # Test retrieving multiple
        user_ids = list(permissions.keys())
        cached_permissions = await cache.get_multiple_permissions(user_ids)
        
        for user_id, expected_permission in permissions.items():
            assert cached_permissions[user_id] == expected_permission

# Integration test (requires actual database)
class TestPermissionIntegration:
    """Integration tests for permission system"""
    
    @pytest.mark.asyncio
    @patch('app.core.config.CosmosDB')
    async def test_permission_service_with_db_fallback(self, mock_cosmos_db):
        """Test permission service with database fallback"""
        # Mock user data
        mock_user = {
            "id": "test_user",
            "permission": PermissionLevel.EDITOR,
            "custom_capabilities": {PermissionCapability.CAN_MANAGE_USERS: True}
        }
        
        # Setup mocks
        mock_cosmos_instance = MagicMock()
        mock_cosmos_instance.get_user_by_id.return_value = mock_user
        mock_cosmos_db.return_value = mock_cosmos_instance
        
        # Test service
        cache = InMemoryPermissionCache()
        service = PermissionService(cache, mock_cosmos_instance)
        
        # Should hit database first time
        permission = await service.get_user_permission("test_user")
        assert permission == PermissionLevel.EDITOR
        
        # Should hit cache second time
        permission_cached = await service.get_user_permission("test_user")
        assert permission_cached == PermissionLevel.EDITOR
        
        # Database should only be called once due to caching
        mock_cosmos_instance.get_user_by_id.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__])
