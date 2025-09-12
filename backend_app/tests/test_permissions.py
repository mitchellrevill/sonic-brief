import pytest
from app.core.permissions import (
    get_user_capabilities,
    merge_custom_capabilities,
    user_has_capability_for_job
)
from app.models.permissions import (
    PermissionLevel,
    PermissionCapability,
    PERMISSION_CAPABILITIES
)


class TestGetUserCapabilities:
    """Test the get_user_capabilities function."""
    
    def test_admin_has_all_capabilities(self):
        """Test that ADMIN users have all capabilities."""
        capabilities = get_user_capabilities(PermissionLevel.ADMIN)
        
        # Admin should have all capabilities in the map
        admin_caps = PERMISSION_CAPABILITIES[PermissionLevel.ADMIN]
        for capability in admin_caps:
            assert capabilities[capability] is True
    
    def test_editor_has_expected_capabilities(self):
        """Test that EDITOR users have the correct capabilities."""
        capabilities = get_user_capabilities(PermissionLevel.EDITOR)
        
        editor_caps = PERMISSION_CAPABILITIES[PermissionLevel.EDITOR]
        for capability in editor_caps:
            assert capabilities[capability] is True
            
        # Editor should not have admin-only capabilities
        assert capabilities.get(PermissionCapability.CAN_DELETE_ALL_JOBS, False) is False
    
    def test_user_has_basic_capabilities(self):
        """Test that USER level has basic capabilities."""
        capabilities = get_user_capabilities(PermissionLevel.USER)
        
        user_caps = PERMISSION_CAPABILITIES[PermissionLevel.USER]
        for capability in user_caps:
            assert capabilities[capability] is True
            
        # User should not have admin/editor capabilities
        assert capabilities.get(PermissionCapability.CAN_VIEW_ALL_JOBS, False) is False
        assert capabilities.get(PermissionCapability.CAN_EDIT_ALL_JOBS, False) is False
    
    def test_capability_hierarchy_consistency(self):
        """Test that higher permission levels include lower level capabilities."""
        user_caps = get_user_capabilities(PermissionLevel.USER)
        editor_caps = get_user_capabilities(PermissionLevel.EDITOR) 
        admin_caps = get_user_capabilities(PermissionLevel.ADMIN)
        
        # Editor should have all user capabilities
        for capability, has_cap in user_caps.items():
            if has_cap:
                assert editor_caps.get(capability, False) is True, f"Editor missing user capability: {capability}"
        
        # Admin should have all editor capabilities
        for capability, has_cap in editor_caps.items():
            if has_cap:
                assert admin_caps.get(capability, False) is True, f"Admin missing editor capability: {capability}"


class TestMergeCustomCapabilities:
    """Test the merge_custom_capabilities function."""
    
    def test_custom_grants_override_base_denials(self):
        """Test that custom grants can override base permission denials."""
        base_capabilities = {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
            PermissionCapability.CAN_EXPORT_DATA: False,
            PermissionCapability.CAN_DELETE_ALL_JOBS: False,
        }
        
        custom_permissions = {
            "grants": [PermissionCapability.CAN_EXPORT_DATA],
            "revokes": []
        }
        
        result = merge_custom_capabilities(base_capabilities, custom_permissions)
        
        assert result[PermissionCapability.CAN_VIEW_OWN_JOBS] is True  # Unchanged
        assert result[PermissionCapability.CAN_EXPORT_DATA] is True    # Custom grant
        assert result[PermissionCapability.CAN_DELETE_ALL_JOBS] is False  # Still denied
    
    def test_custom_revokes_override_base_grants(self):
        """Test that custom revokes can remove base permissions."""
        base_capabilities = {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
            PermissionCapability.CAN_EDIT_OWN_JOBS: True,
            PermissionCapability.CAN_UPLOAD_FILES: True,
        }
        
        custom_permissions = {
            "grants": [],
            "revokes": [PermissionCapability.CAN_UPLOAD_FILES]
        }
        
        result = merge_custom_capabilities(base_capabilities, custom_permissions)
        
        assert result[PermissionCapability.CAN_VIEW_OWN_JOBS] is True   # Unchanged
        assert result[PermissionCapability.CAN_EDIT_OWN_JOBS] is True   # Unchanged  
        assert result[PermissionCapability.CAN_UPLOAD_FILES] is False   # Custom revoke
    
    def test_grants_and_revokes_together(self):
        """Test behavior when both grants and revokes are present."""
        base_capabilities = {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
            PermissionCapability.CAN_EXPORT_DATA: False,
            PermissionCapability.CAN_UPLOAD_FILES: True,
        }
        
        custom_permissions = {
            "grants": [PermissionCapability.CAN_EXPORT_DATA],
            "revokes": [PermissionCapability.CAN_UPLOAD_FILES]
        }
        
        result = merge_custom_capabilities(base_capabilities, custom_permissions)
        
        assert result[PermissionCapability.CAN_VIEW_OWN_JOBS] is True   # Unchanged
        assert result[PermissionCapability.CAN_EXPORT_DATA] is True     # Custom grant
        assert result[PermissionCapability.CAN_UPLOAD_FILES] is False   # Custom revoke
    
    def test_empty_custom_permissions(self):
        """Test that empty custom permissions don't change base capabilities."""
        base_capabilities = {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
            PermissionCapability.CAN_EXPORT_DATA: False,
        }
        
        # Test with empty dict
        result1 = merge_custom_capabilities(base_capabilities, {})
        assert result1 == base_capabilities
        
        # Test with empty grants/revokes
        result2 = merge_custom_capabilities(base_capabilities, {"grants": [], "revokes": []})
        assert result2 == base_capabilities
    
    def test_unknown_capabilities_ignored(self):
        """Test that unknown capabilities in custom permissions are ignored."""
        base_capabilities = {
            PermissionCapability.CAN_VIEW_OWN_JOBS: True,
        }
        
        custom_permissions = {
            "grants": ["UNKNOWN_CAPABILITY"],
            "revokes": []
        }
        
        # Should not raise an error and should preserve base capabilities
        result = merge_custom_capabilities(base_capabilities, custom_permissions)
        assert result[PermissionCapability.CAN_VIEW_OWN_JOBS] is True


class TestUserHasCapabilityForJob:
    """Test the user_has_capability_for_job function."""
    
    def test_owner_has_own_job_capabilities(self):
        """Test that job owners have capabilities for their own jobs."""
        user = {
            "id": "user-123",
            "permission_level": PermissionLevel.USER,
            "custom_permissions": {}
        }
        
        job = {
            "id": "job-456",
            "owner_id": "user-123",
            "shared_with": []
        }
        
        # Owner should have view and edit capabilities for own job
        assert user_has_capability_for_job(user, job, PermissionCapability.CAN_VIEW_OWN_JOBS) is True
        assert user_has_capability_for_job(user, job, PermissionCapability.CAN_EDIT_OWN_JOBS) is True
    
    def test_admin_has_all_job_capabilities(self):
        """Test that admin users have all capabilities for any job."""
        admin_user = {
            "id": "admin-123",
            "permission_level": PermissionLevel.ADMIN,
            "custom_permissions": {}
        }
        
        other_user_job = {
            "id": "job-456", 
            "owner_id": "other-user-789",
            "shared_with": []
        }
        
        # Admin should have all capabilities for any job
        assert user_has_capability_for_job(admin_user, other_user_job, PermissionCapability.CAN_VIEW_ALL_JOBS) is True
        assert user_has_capability_for_job(admin_user, other_user_job, PermissionCapability.CAN_EDIT_ALL_JOBS) is True
        assert user_has_capability_for_job(admin_user, other_user_job, PermissionCapability.CAN_DELETE_ALL_JOBS) is True
    
    def test_shared_job_access_with_capability(self):
        """Test that users can access shared jobs if they have the required capability."""
        user = {
            "id": "user-123",
            "permission_level": PermissionLevel.EDITOR,  # Has view_all capability
            "custom_permissions": {}
        }
        
        shared_job = {
            "id": "job-456",
            "owner_id": "other-user-789", 
            "shared_with": ["user-123"]
        }
        
        # User should be able to view shared job if they have view_all capability
        assert user_has_capability_for_job(user, shared_job, PermissionCapability.CAN_VIEW_ALL_JOBS) is True
    
    def test_no_access_to_other_jobs_without_capability(self):
        """Test that users cannot access other users' jobs without proper capabilities."""
        user = {
            "id": "user-123",
            "permission_level": PermissionLevel.USER,  # No view_all capability
            "custom_permissions": {}
        }
        
        other_job = {
            "id": "job-456",
            "owner_id": "other-user-789",
            "shared_with": []
        }
        
        # User should not be able to access other's job without view_all capability
        assert user_has_capability_for_job(user, other_job, PermissionCapability.CAN_VIEW_ALL_JOBS) is False
        assert user_has_capability_for_job(user, other_job, PermissionCapability.CAN_EDIT_ALL_JOBS) is False
    
    def test_custom_permissions_affect_job_access(self):
        """Test that custom permissions affect job access capabilities."""
        user = {
            "id": "user-123", 
            "permission_level": PermissionLevel.USER,
            "custom_permissions": {
                "grants": [PermissionCapability.CAN_VIEW_ALL_JOBS],
                "revokes": []
            }
        }
        
        other_job = {
            "id": "job-456",
            "owner_id": "other-user-789",
            "shared_with": []
        }
        
        # User should be able to view other's job due to custom grant
        assert user_has_capability_for_job(user, other_job, PermissionCapability.CAN_VIEW_ALL_JOBS) is True
