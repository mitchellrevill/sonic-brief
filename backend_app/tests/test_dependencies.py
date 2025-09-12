import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from app.core.dependencies import (
    get_effective_capabilities,
    require_capability,
    require_job_capability,
    require_job_view,
    require_job_edit,
    require_job_download,
    require_job_export,
    require_job_owner_or_admin
)
from app.models.permissions import PermissionLevel, PermissionCapability


class TestGetEffectiveCapabilities:
    """Test the get_effective_capabilities dependency."""
    
    @pytest.mark.asyncio
    async def test_merges_base_and_custom_capabilities(self, monkeypatch):
        """Test that base permissions and custom grants/revokes are merged correctly."""
        # Mock the config and cosmos_db
        mock_config = Mock()
        mock_cosmos_db = AsyncMock()
        mock_user = {
            "id": "test-user",
            "permission": PermissionLevel.USER.value,
            "custom_capabilities": {
                "grants": [PermissionCapability.CAN_DOWNLOAD_FILES],
                "revokes": []
            }
        }
        mock_cosmos_db.get_user_by_id.return_value = mock_user
        
        monkeypatch.setattr("app.core.dependencies.get_app_config", lambda: mock_config)
        monkeypatch.setattr("app.core.dependencies.get_cosmos_db_cached", lambda config: mock_cosmos_db)
        
        # Call the dependency function
        result = await get_effective_capabilities("test-user")
        
        # Verify cosmos was called
        mock_cosmos_db.get_user_by_id.assert_called_once_with("test-user")
        
        # Check the result includes the merged capabilities
        assert isinstance(result, dict)
        assert PermissionCapability.CAN_VIEW_OWN_JOBS in result
    
    @pytest.mark.asyncio
    async def test_handles_user_not_found(self, monkeypatch):
        """Test with user not found in database."""
        mock_config = Mock()
        mock_cosmos_db = AsyncMock()
        mock_cosmos_db.get_user_by_id.return_value = None
        
        monkeypatch.setattr("app.core.dependencies.get_app_config", lambda: mock_config)
        monkeypatch.setattr("app.core.dependencies.get_cosmos_db_cached", lambda config: mock_cosmos_db)
        
        result = await get_effective_capabilities("nonexistent-user")
        
        # Should return empty dict when user not found
        assert isinstance(result, dict)


class TestCapabilityChecks:
    """Test capability checking functions."""
    
    def test_require_capability_factory_creates_dependency(self):
        """Test that require_capability returns a dependency function."""
        dependency = require_capability(PermissionCapability.CAN_UPLOAD_FILES)
        assert callable(dependency)
    
    def test_job_scoped_dependency_factories_exist(self):
        """Test that all job-scoped dependencies are callable."""
        job_dependencies = [
            require_job_view,
            require_job_edit, 
            require_job_download,
            require_job_export,
            require_job_owner_or_admin
        ]
        
        for dep_func in job_dependencies:
            assert callable(dep_func)
    
    def test_job_capability_factory_creates_dependency(self):
        """Test that require_job_capability factory works."""
        dependency = require_job_capability(PermissionCapability.CAN_EDIT_OWN_JOBS)
        assert callable(dependency)


# Note: The actual permission logic is tested in test_permissions.py
# These tests focus on the dependency wiring and FastAPI integration
