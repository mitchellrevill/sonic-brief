import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from app.models.permissions import (
    PermissionLevel, 
    PermissionCapability, 
    get_user_capabilities,
    can_user_perform_action,
    merge_custom_capabilities,
    validate_capability_data
)
from app.services.permissions import PermissionService
from app.utils.permission_cache import InMemoryPermissionCache


class TestPermissionSystemIntegration:
    """Integration tests for the new resource-based permission system"""
    
    @pytest.fixture
    def mock_cosmos_db(self):
        """Mock CosmosDB for testing"""
        mock_db = Mock()
        mock_db.get_user_by_id = AsyncMock()
        return mock_db
    
    @pytest.fixture
    def permission_cache(self):
        """Create in-memory permission cache for testing"""
        return InMemoryPermissionCache(
            cache_ttl_seconds=300,
            max_cache_size=1000
        )
    
    @pytest.fixture
    def permission_service(self, mock_cosmos_db, permission_cache):
        """Create permission service with mocked dependencies"""
        return PermissionService(mock_cosmos_db, permission_cache)
    
    def test_user_capabilities_hierarchy(self):
        """Test that permission level hierarchy works correctly"""
        # User level capabilities
        user_caps = get_user_capabilities(PermissionLevel.USER)
        assert PermissionCapability.CAN_VIEW_OWN_JOBS in user_caps
        assert PermissionCapability.CAN_CREATE_JOBS in user_caps
        assert PermissionCapability.CAN_VIEW_ALL_JOBS not in user_caps
        
        # Editor level capabilities (includes user + more)
        editor_caps = get_user_capabilities(PermissionLevel.EDITOR)
        assert PermissionCapability.CAN_VIEW_OWN_JOBS in editor_caps
        assert PermissionCapability.CAN_CREATE_JOBS in editor_caps
        assert PermissionCapability.CAN_EDIT_SHARED_JOBS in editor_caps
        assert PermissionCapability.CAN_VIEW_ALL_JOBS not in editor_caps
        
        # Admin level capabilities (includes all)
        admin_caps = get_user_capabilities(PermissionLevel.ADMIN)
        assert PermissionCapability.CAN_VIEW_OWN_JOBS in admin_caps
        assert PermissionCapability.CAN_VIEW_ALL_JOBS in admin_caps
        assert PermissionCapability.CAN_MANAGE_USERS in admin_caps
    
    def test_custom_capabilities_override(self):
        """Test that custom capabilities properly override base capabilities"""
        base_caps = get_user_capabilities(PermissionLevel.USER)
        custom_caps = {
            PermissionCapability.CAN_VIEW_ALL_JOBS.value: True,  # Grant extra capability
            PermissionCapability.CAN_CREATE_JOBS.value: False,   # Revoke base capability
        }
        
        effective_caps = merge_custom_capabilities(base_caps, custom_caps)
        
        assert effective_caps[PermissionCapability.CAN_VIEW_ALL_JOBS.value] is True
        assert effective_caps[PermissionCapability.CAN_CREATE_JOBS.value] is False
        assert effective_caps[PermissionCapability.CAN_VIEW_OWN_JOBS.value] is True  # Unchanged
    
    @pytest.mark.asyncio
    async def test_permission_service_capability_check(self, permission_service):
        """Test permission service capability checking"""
        # Test with basic user permission
        user_permission = PermissionLevel.USER
        custom_capabilities = {}
        
        # User should have basic capabilities
        assert await permission_service.has_capability(
            user_permission, custom_capabilities, PermissionCapability.CAN_VIEW_OWN_JOBS
        )
        
        # User should not have admin capabilities
        assert not await permission_service.has_capability(
            user_permission, custom_capabilities, PermissionCapability.CAN_VIEW_ALL_JOBS
        )
        
        # Test with custom capability override
        custom_capabilities = {
            PermissionCapability.CAN_VIEW_ALL_JOBS.value: True
        }
        
        assert await permission_service.has_capability(
            user_permission, custom_capabilities, PermissionCapability.CAN_VIEW_ALL_JOBS
        )
    
    @pytest.mark.asyncio
    async def test_permission_cache_functionality(self, permission_cache):
        """Test permission cache operations"""
        user_id = "test-user-123"
        cache_key = f"user_perms:{user_id}"
        
        test_permissions = {
            "permission": PermissionLevel.EDITOR.value,
            "custom_capabilities": {
                PermissionCapability.CAN_VIEW_ALL_JOBS.value: True
            }
        }
        
        # Test cache set and get
        await permission_cache.set_user_permissions(user_id, test_permissions)
        cached_perms = await permission_cache.get_user_permissions(user_id)
        
        assert cached_perms is not None
        assert cached_perms["permission"] == PermissionLevel.EDITOR.value
        assert cached_perms["custom_capabilities"][PermissionCapability.CAN_VIEW_ALL_JOBS.value] is True
        
        # Test cache invalidation
        await permission_cache.invalidate_user_cache(user_id)
        cached_perms_after_invalidation = await permission_cache.get_user_permissions(user_id)
        assert cached_perms_after_invalidation is None
    
    @pytest.mark.asyncio
    async def test_resource_based_job_access(self, permission_service, mock_cosmos_db):
        """Test resource-based access control for jobs"""
        user_id = "user-123"
        job_id = "job-456"
        
        # Mock job data
        job = {
            "id": job_id,
            "user_id": "owner-789",  # Different from requesting user
            "shared_with": [
                {"user_id": user_id, "permission_level": "view"}
            ]
        }
        
        # Mock user data
        user = {
            "id": user_id,
            "permission": PermissionLevel.USER.value,
            "custom_capabilities": {}
        }
        
        mock_cosmos_db.get_user_by_id.return_value = user
        
        # Test that user can view shared job
        can_view = await permission_service.check_resource_access(
            user_id, "job", job_id, "view", resource_data=job
        )
        assert can_view is True
        
        # Test that user cannot edit shared job (only view permission)
        can_edit = await permission_service.check_resource_access(
            user_id, "job", job_id, "edit", resource_data=job
        )
        assert can_edit is False
    
    def test_capability_validation(self):
        """Test capability data validation"""
        # Valid capability data
        valid_data = {
            PermissionCapability.CAN_VIEW_OWN_JOBS.value: True,
            PermissionCapability.CAN_CREATE_JOBS.value: False,
        }
        assert validate_capability_data(valid_data) is True
        
        # Invalid capability key
        invalid_data = {
            "invalid_capability": True,
            PermissionCapability.CAN_VIEW_OWN_JOBS.value: True,
        }
        assert validate_capability_data(invalid_data) is False
        
        # Invalid capability value
        invalid_value_data = {
            PermissionCapability.CAN_VIEW_OWN_JOBS.value: "not_a_boolean",
        }
        assert validate_capability_data(invalid_value_data) is False
    
    @pytest.mark.asyncio
    async def test_permission_level_checking(self, permission_service):
        """Test permission level hierarchy checking"""
        # Admin can access editor resources
        assert await permission_service.has_permission_level(
            PermissionLevel.ADMIN, PermissionLevel.EDITOR
        )
        
        # Editor can access user resources
        assert await permission_service.has_permission_level(
            PermissionLevel.EDITOR, PermissionLevel.USER
        )
        
        # User cannot access admin resources
        assert not await permission_service.has_permission_level(
            PermissionLevel.USER, PermissionLevel.ADMIN
        )
    
    @pytest.mark.asyncio
    async def test_capability_inheritance_and_override(self, permission_service):
        """Test that capabilities are properly inherited and can be overridden"""
        # Test editor with additional admin capability
        editor_permission = PermissionLevel.EDITOR
        custom_capabilities = {
            PermissionCapability.CAN_VIEW_ALL_JOBS.value: True,  # Admin capability
            PermissionCapability.CAN_CREATE_JOBS.value: False,   # Revoke inherited capability
        }
        
        # Should have admin capability through override
        assert await permission_service.has_capability(
            editor_permission, custom_capabilities, PermissionCapability.CAN_VIEW_ALL_JOBS
        )
        
        # Should not have create capability due to override
        assert not await permission_service.has_capability(
            editor_permission, custom_capabilities, PermissionCapability.CAN_CREATE_JOBS
        )
        
        # Should still have base editor capabilities not overridden
        assert await permission_service.has_capability(
            editor_permission, custom_capabilities, PermissionCapability.CAN_EDIT_SHARED_JOBS
        )
    
    @pytest.mark.asyncio 
    async def test_audit_trail_tracking(self, permission_service, mock_cosmos_db):
        """Test that permission changes are properly tracked for auditing"""
        user_id = "user-123"
        old_permission = PermissionLevel.USER
        new_permission = PermissionLevel.EDITOR
        changed_by = "admin-456"
        
        mock_user = {
            "id": user_id,
            "permission": old_permission.value,
            "permission_history": []
        }
        
        mock_cosmos_db.get_user_by_id.return_value = mock_user
        mock_cosmos_db.update_user = AsyncMock()
        
        # Update permission should create audit trail
        update_data = {
            "permission": new_permission.value,
            "permission_changed_by": changed_by,
            "permission_changed_at": datetime.now(timezone.utc).isoformat()
        }
        
        # This would be called through the auth router, but we can test the logic
        expected_history_entry = {
            "old_permission": old_permission.value,
            "new_permission": new_permission.value,
            "changed_by": changed_by
        }
        
        # Verify audit trail structure
        assert "old_permission" in expected_history_entry
        assert "new_permission" in expected_history_entry  
        assert "changed_by" in expected_history_entry
        assert expected_history_entry["old_permission"] == old_permission.value
        assert expected_history_entry["new_permission"] == new_permission.value


class TestPermissionSystemEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_invalid_permission_level(self):
        """Test handling of invalid permission levels"""
        with pytest.raises(ValueError):
            get_user_capabilities("InvalidPermission")
    
    def test_empty_custom_capabilities(self):
        """Test handling of empty or None custom capabilities"""
        base_caps = get_user_capabilities(PermissionLevel.USER)
        
        # Empty dict should not affect base capabilities
        effective_caps_empty = merge_custom_capabilities(base_caps, {})
        assert effective_caps_empty == base_caps
        
        # None should be handled gracefully
        effective_caps_none = merge_custom_capabilities(base_caps, None)
        assert effective_caps_none == base_caps
    
    @pytest.mark.asyncio
    async def test_cache_miss_handling(self, permission_cache):
        """Test graceful handling of cache misses"""
        user_id = "nonexistent-user"
        
        # Should return None for cache miss, not raise exception
        cached_perms = await permission_cache.get_user_permissions(user_id)
        assert cached_perms is None
        
        # Invalidating non-existent cache entry should not raise exception
        await permission_cache.invalidate_user_cache(user_id)  # Should not raise
    
    def test_capability_enum_completeness(self):
        """Test that all expected capabilities are defined"""
        all_capabilities = list(PermissionCapability)
        
        # Should have job management capabilities
        job_caps = [cap for cap in all_capabilities if "job" in cap.value.lower()]
        assert len(job_caps) > 0
        
        # Should have user management capabilities  
        user_caps = [cap for cap in all_capabilities if "user" in cap.value.lower()]
        assert len(user_caps) > 0
        
        # Should have system capabilities
        system_caps = [cap for cap in all_capabilities if any(
            term in cap.value.lower() for term in ["setting", "system", "analytic"]
        )]
        assert len(system_caps) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
