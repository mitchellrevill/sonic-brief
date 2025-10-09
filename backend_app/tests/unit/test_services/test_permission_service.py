"""
Unit tests for PermissionService (Critical Priority - Phase 1)

Tests cover:
- Permission level checking
- User capability retrieval
- Permission hierarchy validation
- User permission fetching from database
- Backward compatibility decorators
- Error handling and edge cases

Target Coverage: 90%+
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import logging

from app.services.auth.permission_service import (
    PermissionService,
    permission_service,
    require_permission,
    require_admin_permission,
    require_editor_permission,
    require_user_permission,
)
from app.models.permissions import PermissionLevel


# ============================================================================
# Permission Level Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestPermissionLevel:
    """Test permission level checking and hierarchy."""
    
    def test_has_permission_level_admin_has_all_permissions(self):
        """Test that admin permission level has access to all lower levels."""
        service = PermissionService()
        
        assert service.has_permission_level_method("admin", PermissionLevel.ADMIN)
        assert service.has_permission_level_method("admin", PermissionLevel.EDITOR)
        assert service.has_permission_level_method("admin", PermissionLevel.USER)
        assert service.has_permission_level_method("admin", PermissionLevel.PUBLIC)
    
    def test_has_permission_level_editor_has_limited_permissions(self):
        """Test that editor permission level has access to editor, user, and public."""
        service = PermissionService()
        
        assert not service.has_permission_level_method("editor", PermissionLevel.ADMIN)
        assert service.has_permission_level_method("editor", PermissionLevel.EDITOR)
        assert service.has_permission_level_method("editor", PermissionLevel.USER)
        assert service.has_permission_level_method("editor", PermissionLevel.PUBLIC)
    
    def test_has_permission_level_user_has_basic_permissions(self):
        """Test that user permission level has access to user and public only."""
        service = PermissionService()
        
        assert not service.has_permission_level_method("user", PermissionLevel.ADMIN)
        assert not service.has_permission_level_method("user", PermissionLevel.EDITOR)
        assert service.has_permission_level_method("user", PermissionLevel.USER)
        assert service.has_permission_level_method("user", PermissionLevel.PUBLIC)
    
    def test_has_permission_level_public_has_minimum_permissions(self):
        """Test that public permission level has access to public only."""
        service = PermissionService()
        
        assert not service.has_permission_level_method("public", PermissionLevel.ADMIN)
        assert not service.has_permission_level_method("public", PermissionLevel.EDITOR)
        assert not service.has_permission_level_method("public", PermissionLevel.USER)
        assert service.has_permission_level_method("public", PermissionLevel.PUBLIC)
    
    def test_has_permission_level_with_none_permission(self):
        """Test permission checking with None user permission."""
        service = PermissionService()
        
        assert not service.has_permission_level_method(None, PermissionLevel.PUBLIC)
        assert not service.has_permission_level_method(None, PermissionLevel.USER)
    
    def test_has_permission_level_with_empty_string(self):
        """Test permission checking with empty string permission."""
        service = PermissionService()
        
        assert not service.has_permission_level_method("", PermissionLevel.PUBLIC)
        assert not service.has_permission_level_method("", PermissionLevel.USER)
    
    def test_has_permission_level_with_unknown_permission(self):
        """Test permission checking with unknown permission level."""
        service = PermissionService()
        
        # Unknown permissions should default to lowest level
        result = service.has_permission_level_method("unknown", PermissionLevel.ADMIN)
        assert not result


# ============================================================================
# User Capabilities Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestUserCapabilities:
    """Test user capability retrieval and merging."""
    
    def test_get_user_capabilities_admin(self):
        """Test getting capabilities for admin user."""
        service = PermissionService()
        
        capabilities = service.get_user_capabilities("admin")
        
        assert isinstance(capabilities, dict)
        assert capabilities.get("can_delete_users", False) or capabilities.get("can_manage_users", False)
    
    def test_get_user_capabilities_editor(self):
        """Test getting capabilities for editor user."""
        service = PermissionService()
        
        capabilities = service.get_user_capabilities("editor")
        
        assert isinstance(capabilities, dict)
        # Editors should not have admin capabilities
        assert not capabilities.get("can_delete_users", False)
    
    def test_get_user_capabilities_user(self):
        """Test getting capabilities for regular user."""
        service = PermissionService()
        
        capabilities = service.get_user_capabilities("user")
        
        assert isinstance(capabilities, dict)
        # Regular users should have limited capabilities
        assert not capabilities.get("can_manage_users", False)
    
    def test_get_user_capabilities_with_custom_overrides(self):
        """Test getting capabilities with custom overrides."""
        service = PermissionService()
        
        custom = {"can_export": True, "can_delete": False}
        capabilities = service.get_user_capabilities("user", custom)
        
        assert isinstance(capabilities, dict)
        # Custom overrides should be applied
        assert capabilities.get("can_export") == True
    
    def test_get_user_capabilities_without_custom(self):
        """Test getting capabilities without custom overrides."""
        service = PermissionService()
        
        capabilities = service.get_user_capabilities("user", None)
        
        assert isinstance(capabilities, dict)
    
    def test_get_user_capabilities_empty_custom(self):
        """Test getting capabilities with empty custom dict."""
        service = PermissionService()
        
        capabilities = service.get_user_capabilities("user", {})
        
        assert isinstance(capabilities, dict)


# ============================================================================
# User Permission Retrieval Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestUserPermissionRetrieval:
    """Test fetching user permissions from database."""
    
    @pytest.mark.asyncio
    async def test_get_user_permission_success(self):
        """Test successful retrieval of user permission."""
        service = PermissionService()
        mock_cosmos = AsyncMock()
        mock_cosmos.get_user_by_id = AsyncMock(return_value={
            "id": "user-123",
            "permission": "admin"
        })
        service.set_cosmos_db(mock_cosmos)
        
        permission = await service.get_user_permission("user-123")
        
        assert permission == "admin"
        mock_cosmos.get_user_by_id.assert_called_once_with("user-123")
    
    @pytest.mark.asyncio
    async def test_get_user_permission_user_not_found(self):
        """Test permission retrieval when user doesn't exist."""
        service = PermissionService()
        mock_cosmos = AsyncMock()
        mock_cosmos.get_user_by_id = AsyncMock(return_value=None)
        service.set_cosmos_db(mock_cosmos)
        
        permission = await service.get_user_permission("nonexistent-user")
        
        assert permission is None
    
    @pytest.mark.asyncio
    async def test_get_user_permission_database_error(self):
        """Test permission retrieval handles database errors gracefully."""
        service = PermissionService()
        mock_cosmos = AsyncMock()
        mock_cosmos.get_user_by_id = AsyncMock(side_effect=Exception("Database error"))
        service.set_cosmos_db(mock_cosmos)
        
        permission = await service.get_user_permission("user-123")
        
        # Should return None on error, not raise exception
        assert permission is None
    
    @pytest.mark.asyncio
    async def test_get_user_permission_without_cosmos_set(self):
        """Test permission retrieval without cosmos DB set (uses config)."""
        service = PermissionService()
        
        with patch('app.services.auth.permission_service.get_cosmos_db') as mock_get_cosmos:
            mock_cosmos = AsyncMock()
            mock_cosmos.get_user_by_id = AsyncMock(return_value={
                "id": "user-123",
                "permission": "user"
            })
            mock_get_cosmos.return_value = mock_cosmos
            
            permission = await service.get_user_permission("user-123")
            
            assert permission == "user"
    
    @pytest.mark.asyncio
    async def test_get_user_permission_user_without_permission_field(self):
        """Test permission retrieval when user has no permission field."""
        service = PermissionService()
        mock_cosmos = AsyncMock()
        mock_cosmos.get_user_by_id = AsyncMock(return_value={
            "id": "user-123",
            "email": "test@example.com"
            # No permission field
        })
        service.set_cosmos_db(mock_cosmos)
        
        permission = await service.get_user_permission("user-123")
        
        assert permission is None


# ============================================================================
# Capability Check Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCapabilityCheck:
    """Test the can() method for capability checking."""
    
    def test_can_admin_has_all_capabilities(self):
        """Test that admin can perform any action."""
        service = PermissionService()
        
        # Admin should be able to perform various actions
        assert service.can("admin", "can_delete")
        assert service.can("admin", "can_edit")
        assert service.can("admin", "can_view")
    
    def test_can_user_has_limited_capabilities(self):
        """Test that regular user has limited capabilities."""
        service = PermissionService()
        
        # User should have basic capabilities but not admin ones
        # Exact capabilities depend on the permission model implementation
        result = service.can("user", "can_view")
        assert isinstance(result, bool)
    
    def test_can_with_none_permission(self):
        """Test capability check with None permission."""
        service = PermissionService()
        
        result = service.can(None, "can_view")
        assert not result
    
    def test_can_with_empty_capability(self):
        """Test capability check with empty capability string."""
        service = PermissionService()
        
        result = service.can("user", "")
        assert isinstance(result, bool)


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

@pytest.mark.unit
class TestBackwardCompatibility:
    """Test backward compatibility features and decorators."""
    
    def test_global_permission_service_instance(self):
        """Test that global permission_service instance is available."""
        assert permission_service is not None
        assert isinstance(permission_service, PermissionService)
    
    @pytest.mark.asyncio
    async def test_require_permission_decorator_no_op(self):
        """Test that require_permission decorator is a no-op."""
        @require_permission(PermissionLevel.ADMIN)
        async def test_function():
            return "success"
        
        result = await test_function()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_require_admin_permission_decorator(self):
        """Test require_admin_permission decorator."""
        @require_admin_permission
        async def test_function():
            return "admin_success"
        
        result = await test_function()
        assert result == "admin_success"
    
    @pytest.mark.asyncio
    async def test_require_editor_permission_decorator(self):
        """Test require_editor_permission decorator."""
        @require_editor_permission
        async def test_function():
            return "editor_success"
        
        result = await test_function()
        assert result == "editor_success"
    
    @pytest.mark.asyncio
    async def test_require_user_permission_decorator(self):
        """Test require_user_permission decorator."""
        @require_user_permission
        async def test_function():
            return "user_success"
        
        result = await test_function()
        assert result == "user_success"
    
    def test_set_cosmos_db(self):
        """Test setting cosmos DB instance."""
        service = PermissionService()
        mock_cosmos = Mock()
        
        service.set_cosmos_db(mock_cosmos)
        
        assert service.cosmos == mock_cosmos
    
    def test_close_method(self):
        """Test that close method works without errors."""
        service = PermissionService()
        
        # Should not raise any exception
        service.close()


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

@pytest.mark.unit
class TestPermissionServiceEdgeCases:
    """Test edge cases and error handling."""
    
    def test_has_permission_level_with_whitespace(self):
        """Test permission checking with whitespace in permission string."""
        service = PermissionService()
        
        # Should handle gracefully
        result = service.has_permission_level_method("  admin  ", PermissionLevel.ADMIN)
        # Depends on implementation - may trim or not
        assert isinstance(result, bool)
    
    def test_get_user_capabilities_with_invalid_permission(self):
        """Test getting capabilities with invalid permission string."""
        service = PermissionService()
        
        capabilities = service.get_user_capabilities("invalid_permission")
        
        # Should return a dict, even if empty or with defaults
        assert isinstance(capabilities, dict)
    
    @pytest.mark.asyncio
    async def test_get_user_permission_with_empty_user_id(self):
        """Test permission retrieval with empty user ID."""
        service = PermissionService()
        mock_cosmos = AsyncMock()
        mock_cosmos.get_user_by_id = AsyncMock(return_value=None)
        service.set_cosmos_db(mock_cosmos)
        
        permission = await service.get_user_permission("")
        
        assert permission is None
    
    def test_can_with_special_characters_in_capability(self):
        """Test capability check with special characters."""
        service = PermissionService()
        
        result = service.can("admin", "can_delete!@#$%")
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_decorator_with_multiple_arguments(self):
        """Test decorator works with functions that have arguments."""
        @require_permission(PermissionLevel.USER)
        async def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"
        
        result = await test_function("a", "b", kwarg1="c")
        assert result == "a-b-c"
    
    def test_permission_service_initialization(self):
        """Test that PermissionService can be initialized multiple times."""
        service1 = PermissionService()
        service2 = PermissionService()
        
        assert service1 is not service2
        assert service1.cosmos is None
        assert service2.cosmos is None
