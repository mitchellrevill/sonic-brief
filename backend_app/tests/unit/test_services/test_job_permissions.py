"""
Unit tests for JobPermissions (High Priority - Phase 2)

Tests cover:
- Job access validation
- Permission level checking
- User job permission retrieval
- Admin privilege checking
- Ownership verification
- Shared job permissions
- Edge cases and error handling

Target Coverage: 90%+
"""

import pytest
from unittest.mock import Mock, AsyncMock
import logging

from app.services.jobs.job_permissions import (
    check_job_access,
    check_job_permission_level,
    get_user_job_permission,
    JobPermissions,
)
from app.models.permissions import PermissionLevel


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def admin_user():
    """Create an admin user."""
    return {
        "id": "admin-123",
        "email": "admin@example.com",
        "permission": "Admin"
    }


@pytest.fixture
def regular_user():
    """Create a regular user."""
    return {
        "id": "user-456",
        "email": "user@example.com",
        "permission": "User"
    }


@pytest.fixture
def editor_user():
    """Create an editor user."""
    return {
        "id": "editor-789",
        "email": "editor@example.com",
        "permission": "Editor"
    }


@pytest.fixture
def owner_job():
    """Create a job owned by user-456."""
    return {
        "id": "job-001",
        "user_id": "user-456",
        "title": "Test Job",
        "deleted": False
    }


@pytest.fixture
def shared_job():
    """Create a job shared with multiple users."""
    return {
        "id": "job-002",
        "user_id": "owner-999",
        "title": "Shared Job",
        "deleted": False,
        "shared_with": [
            {"user_id": "user-456", "permission_level": "view"},
            {"user_id": "editor-789", "permission_level": "edit"}
        ]
    }


@pytest.fixture
def deleted_job():
    """Create a deleted job."""
    return {
        "id": "job-003",
        "user_id": "user-456",
        "title": "Deleted Job",
        "deleted": True
    }


# ============================================================================
# Job Access Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.high
class TestJobAccessValidation:
    """Test job access validation."""
    
    def test_admin_can_access_any_job(self, admin_user, owner_job):
        """Test that admin users can access any job."""
        result = check_job_access(owner_job, admin_user)
        
        assert result is True
    
    def test_owner_can_access_own_job(self, regular_user, owner_job):
        """Test that job owner can access their own job."""
        result = check_job_access(owner_job, regular_user)
        
        assert result is True
    
    def test_non_owner_cannot_access_job(self, editor_user, owner_job):
        """Test that non-owner cannot access job without sharing."""
        result = check_job_access(owner_job, editor_user)
        
        assert result is False
    
    def test_shared_user_can_access_with_view_permission(self, regular_user, shared_job):
        """Test that user with view permission can access shared job."""
        result = check_job_access(shared_job, regular_user, "view")
        
        assert result is True
    
    def test_shared_user_can_access_with_edit_permission(self, editor_user, shared_job):
        """Test that user with edit permission can access shared job."""
        result = check_job_access(shared_job, editor_user, "edit")
        
        assert result is True
    
    def test_view_user_cannot_edit_shared_job(self, regular_user, shared_job):
        """Test that user with only view permission cannot edit."""
        result = check_job_access(shared_job, regular_user, "edit")
        
        assert result is False
    
    def test_deleted_job_access_denied(self, regular_user, deleted_job):
        """Test that deleted jobs cannot be accessed."""
        result = check_job_access(deleted_job, regular_user)
        
        assert result is False
    
    def test_deleted_job_access_denied_for_admin(self, admin_user, deleted_job):
        """Test that even admins cannot access deleted jobs."""
        result = check_job_access(deleted_job, admin_user)
        
        assert result is False
    
    def test_admin_with_permissions_list(self, owner_job):
        """Test admin recognition with permissions as list."""
        user = {
            "id": "admin-999",
            "permissions": ["Admin", "User"]
        }
        
        result = check_job_access(owner_job, user)
        
        assert result is True
    
    def test_job_without_shared_with_field(self, regular_user):
        """Test job access without shared_with field."""
        job = {
            "id": "job-004",
            "user_id": "other-user",
            "deleted": False
        }
        
        result = check_job_access(job, regular_user)
        
        assert result is False


# ============================================================================
# Permission Level Checking Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.high
class TestPermissionLevelChecking:
    """Test permission level checking."""
    
    def test_admin_has_all_permissions(self, admin_user, owner_job):
        """Test that admin users have all permission levels."""
        assert check_job_permission_level(admin_user, owner_job, "view")
        assert check_job_permission_level(admin_user, owner_job, "edit")
        assert check_job_permission_level(admin_user, owner_job, "admin")
    
    def test_owner_has_all_permissions(self, regular_user, owner_job):
        """Test that job owner has all permission levels."""
        assert check_job_permission_level(regular_user, owner_job, "view")
        assert check_job_permission_level(regular_user, owner_job, "edit")
        assert check_job_permission_level(regular_user, owner_job, "admin")
    
    def test_view_permission_allows_viewing_only(self, regular_user, shared_job):
        """Test that view permission allows only viewing."""
        assert check_job_permission_level(regular_user, shared_job, "view")
        assert not check_job_permission_level(regular_user, shared_job, "edit")
        assert not check_job_permission_level(regular_user, shared_job, "admin")
    
    def test_edit_permission_allows_view_and_edit(self, editor_user, shared_job):
        """Test that edit permission allows viewing and editing."""
        assert check_job_permission_level(editor_user, shared_job, "view")
        assert check_job_permission_level(editor_user, shared_job, "edit")
        assert not check_job_permission_level(editor_user, shared_job, "admin")
    
    def test_no_permission_for_unshared_job(self):
        """Test that users have no permission on unshared jobs."""
        user = {"id": "user-999", "permission": "User"}
        job = {"id": "job-005", "user_id": "other-user"}
        
        assert not check_job_permission_level(user, job, "view")
    
    def test_permission_level_without_user_permission_field(self, owner_job):
        """Test permission checking when user has no permission field."""
        user = {"id": "user-456", "email": "user@example.com"}
        
        # Should still work based on ownership
        result = check_job_permission_level(user, owner_job, "view")
        
        assert result is True
    
    def test_shared_with_admin_permission(self):
        """Test shared with admin permission level."""
        user = {"id": "user-999", "permission": "User"}
        job = {
            "id": "job-006",
            "user_id": "other-user",
            "shared_with": [
                {"user_id": "user-999", "permission_level": "admin"}
            ]
        }
        
        assert check_job_permission_level(user, job, "view")
        assert check_job_permission_level(user, job, "edit")
        assert check_job_permission_level(user, job, "admin")


# ============================================================================
# User Job Permission Retrieval Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.high
class TestUserJobPermissionRetrieval:
    """Test retrieving user's permission on a job."""
    
    def test_get_owner_permission(self, regular_user, owner_job):
        """Test getting permission for job owner."""
        permission = get_user_job_permission(owner_job, regular_user)
        
        assert permission == "owner"
    
    def test_get_shared_view_permission(self, regular_user, shared_job):
        """Test getting view permission for shared user."""
        permission = get_user_job_permission(shared_job, regular_user)
        
        assert permission == "view"
    
    def test_get_shared_edit_permission(self, editor_user, shared_job):
        """Test getting edit permission for shared user."""
        permission = get_user_job_permission(shared_job, editor_user)
        
        assert permission == "edit"
    
    def test_get_no_permission_for_unshared_job(self, admin_user, owner_job):
        """Test getting permission for user without access."""
        permission = get_user_job_permission(owner_job, admin_user)
        
        # Admin user is not the owner and job is not shared
        assert permission is None
    
    def test_get_permission_for_job_without_shared_with(self):
        """Test getting permission for job without shared_with field."""
        user = {"id": "user-999"}
        job = {"id": "job-007", "user_id": "other-user"}
        
        permission = get_user_job_permission(job, user)
        
        assert permission is None
    
    def test_get_permission_with_empty_shared_with(self):
        """Test getting permission with empty shared_with list."""
        user = {"id": "user-999"}
        job = {
            "id": "job-008",
            "user_id": "other-user",
            "shared_with": []
        }
        
        permission = get_user_job_permission(job, user)
        
        assert permission is None


# ============================================================================
# JobPermissions Class Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.high
class TestJobPermissionsClass:
    """Test JobPermissions class (async wrapper)."""
    
    @pytest.mark.asyncio
    async def test_check_job_access_with_job_dict(self, regular_user, owner_job):
        """Test async check_job_access with job dictionary."""
        permissions = JobPermissions()
        
        result = await permissions.check_job_access(owner_job, regular_user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_job_access_with_job_id_as_admin(self, admin_user):
        """Test async check_job_access with job ID for admin user."""
        permissions = JobPermissions()
        
        # When job ID is passed, admin should still have access
        result = await permissions.check_job_access("job-123", admin_user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_job_access_with_job_id_as_regular_user(self, regular_user):
        """Test async check_job_access with job ID for regular user."""
        permissions = JobPermissions()
        
        # When job ID is passed, regular user is denied (cannot verify ownership)
        result = await permissions.check_job_access("job-123", regular_user)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_job_access_with_admin_permissions_list(self):
        """Test check_job_access recognizes admin in permissions list."""
        permissions = JobPermissions()
        user = {"id": "user-999", "permissions": ["Admin"]}
        
        result = await permissions.check_job_access("job-123", user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_job_access_with_lowercase_admin(self):
        """Test check_job_access recognizes lowercase admin."""
        permissions = JobPermissions()
        user = {"id": "user-999", "permission": "admin"}
        
        result = await permissions.check_job_access("job-123", user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_admin_privileges_true(self, admin_user):
        """Test checking admin privileges for admin user."""
        permissions = JobPermissions()
        
        result = await permissions.check_user_admin_privileges(admin_user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_admin_privileges_false(self, regular_user):
        """Test checking admin privileges for regular user."""
        permissions = JobPermissions()
        
        result = await permissions.check_user_admin_privileges(regular_user)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_admin_privileges_with_permissions_list(self):
        """Test checking admin privileges with permissions as list."""
        permissions = JobPermissions()
        user = {"id": "user-999", "permissions": ["Admin", "User"]}
        
        result = await permissions.check_user_admin_privileges(user)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_admin_privileges_with_non_admin_list(self):
        """Test checking admin privileges with non-admin permissions list."""
        permissions = JobPermissions()
        user = {"id": "user-999", "permissions": ["User", "Editor"]}
        
        result = await permissions.check_user_admin_privileges(user)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_admin_privileges_with_invalid_user(self):
        """Test checking admin privileges with invalid user."""
        permissions = JobPermissions()
        
        result = await permissions.check_user_admin_privileges(None)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_admin_privileges_with_string_user(self):
        """Test checking admin privileges with string instead of dict."""
        permissions = JobPermissions()
        
        result = await permissions.check_user_admin_privileges("not-a-dict")
        
        assert result is False


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.high
class TestJobPermissionsEdgeCases:
    """Test edge cases and error handling."""
    
    def test_check_job_access_with_missing_user_id(self):
        """Test job access check with missing user ID."""
        job = {"id": "job-009", "user_id": "owner-123"}
        user = {"email": "test@example.com", "permission": "User"}
        
        result = check_job_access(job, user)
        
        assert result is False
    
    def test_check_job_access_with_none_user(self, owner_job):
        """Test job access check with None user."""
        result = check_job_access(owner_job, {})
        
        assert result is False
    
    def test_check_job_access_with_malformed_shared_with(self):
        """Test job access with malformed shared_with structure."""
        job = {
            "id": "job-010",
            "user_id": "owner-123",
            "shared_with": [
                {"user_id": "user-456"}  # Missing permission_level
            ]
        }
        user = {"id": "user-456", "permission": "User"}
        
        result = check_job_access(job, user, "view")
        
        # Should handle gracefully
        assert isinstance(result, bool)
    
    def test_get_user_job_permission_with_missing_permission_level(self):
        """Test getting permission when permission_level is missing."""
        job = {
            "id": "job-011",
            "user_id": "owner-123",
            "shared_with": [
                {"user_id": "user-456"}  # Missing permission_level
            ]
        }
        user = {"id": "user-456"}
        
        permission = get_user_job_permission(job, user)
        
        # Should return None for missing permission_level
        assert permission is None
    
    def test_check_permission_level_with_unknown_level(self):
        """Test permission checking with unknown permission level."""
        user = {"id": "user-999", "permission": "User"}
        job = {
            "id": "job-012",
            "user_id": "other-user",
            "shared_with": [
                {"user_id": "user-999", "permission_level": "unknown"}
            ]
        }
        
        result = check_job_permission_level(user, job, "view")
        
        # Should handle unknown permission level gracefully
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_check_job_access_with_exception_in_delegation(self):
        """Test that exceptions in delegation are handled gracefully."""
        permissions = JobPermissions()
        malformed_job = Mock()
        malformed_job.get = Mock(side_effect=Exception("Test error"))
        user = {"id": "user-999", "permission": "admin"}
        
        # Should not raise exception, should fallback to admin check
        result = await permissions.check_job_access(malformed_job, user)
        
        assert result is True  # Admin fallback
    
    def test_admin_case_insensitive_detection(self):
        """Test that admin detection is case-insensitive."""
        job = {"id": "job-013", "user_id": "other-user"}
        
        # Test various cases
        admin_variations = [
            {"id": "user-1", "permission": "admin"},
            {"id": "user-2", "permission": "Admin"},
            {"id": "user-3", "permission": "ADMIN"},
            {"id": "user-4", "permissions": ["admin"]},
            {"id": "user-5", "permissions": ["ADMIN"]},
        ]
        
        for user in admin_variations:
            result = check_job_access(job, user)
            assert result is True, f"Failed for user: {user}"
    
    def test_shared_with_multiple_entries_same_user(self):
        """Test job sharing with duplicate user entries."""
        job = {
            "id": "job-014",
            "user_id": "owner-123",
            "shared_with": [
                {"user_id": "user-456", "permission_level": "view"},
                {"user_id": "user-456", "permission_level": "edit"}  # Duplicate
            ]
        }
        user = {"id": "user-456", "permission": "User"}
        
        # Should return permission from first match
        permission = get_user_job_permission(job, user)
        
        assert permission == "view"
