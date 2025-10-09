"""
Unit tests for CosmosService (Critical Priority - Phase 1)

Tests cover:
- Connection & availability checks
- CRUD operations (Create, Read, Update, Delete)
- Query operations with pagination
- Error handling (timeouts, permission denied, connection errors)
- Soft delete operations

Target Coverage: 90%+
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from datetime import datetime, timezone
import uuid

from app.core.dependencies import CosmosService
from app.core.config import AppConfig


# ============================================================================
# Connection & Availability Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosAvailability:
    """Test Cosmos DB connection and availability checks."""
    
    def test_cosmos_available_with_valid_credentials(self, test_config):
        """Test that CosmosService reports available with valid credentials."""
        service = CosmosService(test_config)
        
        assert service.is_available() is True
    
    def test_cosmos_unavailable_without_endpoint(self):
        """Test that CosmosService reports unavailable without endpoint."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        # Patch environment to ensure no fallback
        with patch.dict('os.environ', {}, clear=True):
            config = AppConfig(
                cosmos_endpoint=None,
                cosmos_key="fake-key",
                cosmos_database="test-db"
            )
            service = CosmosService(config)
            
            assert service.is_available() is False
    
    def test_cosmos_unavailable_without_credentials(self):
        """Test that CosmosService reports unavailable without key."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        # Patch environment to ensure no fallback
        with patch.dict('os.environ', {}, clear=True):
            config = AppConfig(
                cosmos_endpoint="https://test.documents.azure.com:443/",
                cosmos_key=None,
                cosmos_database="test-db"
            )
            service = CosmosService(config)
            
            assert service.is_available() is False
    
    def test_cosmos_availability_cached(self, test_config):
        """Test that availability check is cached after first call."""
        service = CosmosService(test_config)
        
        # First call
        result1 = service.is_available()
        # Second call should use cached value
        result2 = service.is_available()
        
        assert result1 == result2
        assert result1 is True


# ============================================================================
# Job Retrieval Tests (Read Operations)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosJobRetrieval:
    """Test job retrieval operations."""
    
    @pytest.mark.asyncio
    async def test_get_job_by_id_success(self, test_config, mock_cosmos_container, job_factory):
        """Test successful job retrieval by ID."""
        job = job_factory(job_id="test-job-123")
        # Mock query_items to return the job
        mock_cosmos_container.query_items.return_value = [job]
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = await service.get_job_by_id_async("test-job-123")
            
            assert result is not None
            assert result["id"] == "test-job-123"
            mock_cosmos_container.query_items.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_job_by_id_not_found(self, test_config, mock_cosmos_container):
        """Test job retrieval when job doesn't exist."""
        # Return empty list when job not found
        mock_cosmos_container.query_items.return_value = []
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = await service.get_job_by_id_async("nonexistent-job")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_job_by_id_cosmos_error(self, test_config, mock_cosmos_container):
        """Test job retrieval with Cosmos DB error."""
        # Mock error during query
        mock_cosmos_container.query_items.side_effect = CosmosHttpResponseError(
            status_code=500,
            message="Internal Server Error"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            # The actual implementation returns None on error, not raises
            result = await service.get_job_by_id_async("test-job-123")
            assert result is None


# ============================================================================
# Job Query Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosJobQueries:
    """Test job query operations using get_job method."""
    
    def test_get_job_sync_success(self, test_config, mock_cosmos_container, job_factory):
        """Test successful synchronous job retrieval."""
        job = job_factory(job_id="sync-job-123")
        mock_cosmos_container.query_items.return_value = [job]
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = service.get_job("sync-job-123")
            
            assert result is not None
            assert result["id"] == "sync-job-123"
    
    def test_get_job_not_found(self, test_config, mock_cosmos_container):
        """Test job retrieval returning None when not found."""
        mock_cosmos_container.query_items.return_value = []
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = service.get_job("nonexistent-job")
            
            assert result is None
    
    def test_get_job_with_cosmos_error(self, test_config, mock_cosmos_container):
        """Test job retrieval handling Cosmos DB error gracefully."""
        mock_cosmos_container.query_items.side_effect = CosmosHttpResponseError(
            status_code=500,
            message="Internal Server Error"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = service.get_job("test-job-123")
            
            # Service returns None on error
            assert result is None


# ============================================================================
# Job Creation Tests (Create Operations)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosJobCreation:
    """Test job creation operations."""
    
    def test_create_job_success(self, test_config, mock_cosmos_container, job_factory):
        """Test successful job creation."""
        job_data = job_factory()
        mock_cosmos_container.create_item.return_value = {
            **job_data,
            "_etag": "test-etag",
            "_ts": int(datetime.now(timezone.utc).timestamp())
        }
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = service.create_job(job_data)
            
            assert result is not None
            assert result["id"] == job_data["id"]
            assert "_etag" in result
            mock_cosmos_container.create_item.assert_called_once_with(body=job_data)
    
    def test_create_job_validation_error(self, test_config, mock_cosmos_container):
        """Test job creation with validation error."""
        invalid_job = {"type": "job"}  # Missing required 'id' field
        
        mock_cosmos_container.create_item.side_effect = CosmosHttpResponseError(
            status_code=400,
            message="Bad Request - Invalid document"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            with pytest.raises(CosmosHttpResponseError) as exc_info:
                service.create_job(invalid_job)
            
            assert exc_info.value.status_code == 400
    
    def test_create_job_duplicate_id(self, test_config, mock_cosmos_container, job_factory):
        """Test job creation with duplicate ID."""
        job_data = job_factory(job_id="duplicate-job-123")
        
        mock_cosmos_container.create_item.side_effect = CosmosHttpResponseError(
            status_code=409,
            message="Conflict - Document with same ID already exists"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            with pytest.raises(CosmosHttpResponseError) as exc_info:
                service.create_job(job_data)
            
            assert exc_info.value.status_code == 409


# ============================================================================
# Job Update Tests (Update Operations)
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosJobUpdates:
    """Test job update operations."""
    
    def test_update_job_success(self, test_config, mock_cosmos_container, job_factory):
        """Test successful job update."""
        original_job = job_factory(status="pending")
        updated_job = {**original_job, "status": "completed"}
        
        mock_cosmos_container.replace_item.return_value = {
            **updated_job,
            "_etag": "new-etag",
            "_ts": int(datetime.now(timezone.utc).timestamp())
        }
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = service.update_job(original_job["id"], updated_job)
            
            assert result is not None
            assert result["status"] == "completed"
            mock_cosmos_container.replace_item.assert_called_once()
    
    def test_update_job_partial_fields(self, test_config, mock_cosmos_container, job_factory):
        """Test updating specific fields only."""
        job = job_factory(job_id="test-job-123", status="pending")
        updates = {**job, "status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()}
        
        mock_cosmos_container.replace_item.return_value = {**updates, "_etag": "new-etag"}
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            result = service.update_job(job["id"], updates)
            
            assert result["status"] == "processing"
            assert "updated_at" in result
    
    def test_update_job_not_found(self, test_config, mock_cosmos_container):
        """Test updating non-existent job."""
        updates = {"id": "nonexistent-job", "status": "completed"}
        
        mock_cosmos_container.replace_item.side_effect = CosmosResourceNotFoundError(
            status_code=404,
            message="Resource not found"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            with pytest.raises(CosmosResourceNotFoundError):
                service.update_job("nonexistent-job", updates)
    
    def test_update_job_concurrent_modification(self, test_config, mock_cosmos_container, job_factory):
        """Test concurrent modification (etag mismatch)."""
        job = job_factory()
        
        mock_cosmos_container.replace_item.side_effect = CosmosHttpResponseError(
            status_code=412,
            message="Precondition Failed - ETag mismatch"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            with pytest.raises(CosmosHttpResponseError) as exc_info:
                service.update_job(job["id"], job)
            
            assert exc_info.value.status_code == 412


# ============================================================================
# Soft Delete Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosSoftDelete:
    """Test soft delete operations (via update_job with is_deleted flag)."""
    
    def test_soft_delete_job_success(self, test_config, mock_cosmos_container, job_factory):
        """Test successful soft delete via update."""
        job = job_factory(job_id="test-job-123", is_deleted=False)
        deleted_job = {**job, "is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}
        
        mock_cosmos_container.replace_item.return_value = {**deleted_job, "_etag": "new-etag"}
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            # Simulate soft delete by updating is_deleted flag
            result = service.update_job(job["id"], deleted_job)
            
            assert result["is_deleted"] is True
            assert "deleted_at" in result


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosErrorHandling:
    """Test error handling scenarios."""
    
    def test_cosmos_get_job_error_returns_none(self, test_config, mock_cosmos_container):
        """Test get_job returns None on error."""
        mock_cosmos_container.query_items.side_effect = Exception("Connection timeout")
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            # Service logs error and returns None
            result = service.get_job("test-job-123")
            
            assert result is None
    
    def test_cosmos_create_job_error_propagates(self, test_config, mock_cosmos_container, job_factory):
        """Test create_job propagates errors."""
        job = job_factory()
        mock_cosmos_container.create_item.side_effect = CosmosHttpResponseError(
            status_code=408,
            message="Request Timeout"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            with pytest.raises(CosmosHttpResponseError) as exc_info:
                service.create_job(job)
            
            assert exc_info.value.status_code == 408
    
    def test_cosmos_permission_denied_handling(self, test_config, mock_cosmos_container, job_factory):
        """Test handling of permission denied errors."""
        job = job_factory()
        mock_cosmos_container.create_item.side_effect = CosmosHttpResponseError(
            status_code=403,
            message="Forbidden - Insufficient permissions"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            with pytest.raises(CosmosHttpResponseError) as exc_info:
                service.create_job(job)
            
            assert exc_info.value.status_code == 403
    
    def test_cosmos_rate_limit_handling(self, test_config, mock_cosmos_container):
        """Test handling of rate limit (429) errors on get_job."""
        mock_cosmos_container.query_items.side_effect = CosmosHttpResponseError(
            status_code=429,
            message="Too Many Requests"
        )
        
        with patch('app.core.dependencies.CosmosClient'):
            service = CosmosService(test_config)
            service._containers = {"jobs": mock_cosmos_container}
            service._is_available = True
            
            # get_job handles errors and returns None
            result = service.get_job("test-job-123")
            
            assert result is None


# ============================================================================
# Client Initialization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosClientInitialization:
    """Test Cosmos client initialization with different authentication methods."""
    
    def test_client_initialization_with_key_string(self):
        """Test client initialization with direct key string."""
        from app.core.config import AppConfig
        
        config = AppConfig(
            cosmos_endpoint="https://test.documents.azure.com:443/",
            cosmos_key="test-master-key-string==",
            cosmos_database="test-db"
        )
        
        with patch('app.core.dependencies.CosmosClient') as mock_client:
            service = CosmosService(config)
            _ = service.client
            
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs['url'] == "https://test.documents.azure.com:443/"
            assert call_kwargs['credential'] == "test-master-key-string=="
    
    def test_client_initialization_with_key_dict(self):
        """Test client initialization with key as dict (primaryMasterKey) passed through environment."""
        from app.core.config import AppConfig
        from unittest.mock import patch, Mock
        
        # Since AppConfig validates cosmos_key as string, test the actual code path
        # where the key extraction happens inside dependencies.py client property
        config = AppConfig(
            cosmos_endpoint="https://test.documents.azure.com:443/",
            cosmos_key="test-key-string",  # Start with string key
            cosmos_database="test-db"
        )
        
        with patch('app.core.dependencies.CosmosClient') as mock_client:
            service = CosmosService(config)
            # Simulate dict key scenario by modifying the config after creation
            # This tests the code path in dependencies.py that handles dict keys
            service.config = Mock()
            service.config.cosmos_key = {"primaryMasterKey": "extracted-key-from-dict=="}
            service.config.cosmos_endpoint = "https://test.documents.azure.com:443/"
            
            _ = service.client
            
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs['credential'] == "extracted-key-from-dict=="
    
    def test_client_initialization_with_default_azure_credential(self):
        """Test client initialization fallback to DefaultAzureCredential."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        with patch.dict('os.environ', {}, clear=True):
            config = AppConfig(
                cosmos_endpoint="https://test.documents.azure.com:443/",
                cosmos_key=None,  # No key, should use DefaultAzureCredential
                cosmos_database="test-db"
            )
            
            with patch('app.core.dependencies.CosmosClient') as mock_client, \
                 patch('app.core.dependencies.DefaultAzureCredential') as mock_credential:
                service = CosmosService(config)
                _ = service.client
                
                mock_credential.assert_called_once()
                mock_client.assert_called_once()
    
    def test_client_initialization_invalid_key_format(self):
        """Test client initialization with invalid key format raises error."""
        from app.core.config import AppConfig
        from unittest.mock import Mock
        
        config = AppConfig(
            cosmos_endpoint="https://test.documents.azure.com:443/",
            cosmos_key="test-key",  # Start with valid key
            cosmos_database="test-db"
        )
        
        service = CosmosService(config)
        # Simulate invalid dict key by modifying after creation
        service.config = Mock()
        service.config.cosmos_key = {"invalid_key_field": "value"}  # Wrong dict structure
        service.config.cosmos_endpoint = "https://test.documents.azure.com:443/"
        
        with pytest.raises(RuntimeError, match="Unrecognized Cosmos DB key format"):
            _ = service.client
    
    def test_client_initialization_missing_endpoint(self):
        """Test client initialization without endpoint raises error."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        with patch.dict('os.environ', {}, clear=True):
            config = AppConfig(
                cosmos_endpoint=None,
                cosmos_key="test-key",
                cosmos_database="test-db"
            )
            
            service = CosmosService(config)
            
            with pytest.raises(RuntimeError, match="Cosmos DB endpoint not configured"):
                _ = service.client
    
    def test_client_initialization_cached(self):
        """Test that client is cached after first initialization."""
        from app.core.config import AppConfig
        
        config = AppConfig(
            cosmos_endpoint="https://test.documents.azure.com:443/",
            cosmos_key="test-key",
            cosmos_database="test-db"
        )
        
        with patch('app.core.dependencies.CosmosClient') as mock_client:
            service = CosmosService(config)
            
            # Access client twice
            _ = service.client
            _ = service.client
            
            # Should only be called once due to caching
            assert mock_client.call_count == 1


# ============================================================================
# Database Property Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosDatabaseProperty:
    """Test database property and initialization."""
    
    def test_database_property_initialization(self):
        """Test database property initializes correctly."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        with patch.dict('os.environ', {'AZURE_COSMOS_DB': 'test-database'}):
            config = AppConfig(
                cosmos_endpoint="https://test.documents.azure.com:443/",
                cosmos_key="test-key",
                cosmos_database="fallback-db"
            )
            
            mock_client = Mock()
            mock_db = Mock()
            mock_client.get_database_client.return_value = mock_db
            
            service = CosmosService(config)
            service._client = mock_client
            
            result = service.database
            
            assert result == mock_db
            mock_client.get_database_client.assert_called_once_with('test-database')
    
    def test_database_property_fallback_to_config(self):
        """Test database property falls back to config when env var not set."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        with patch.dict('os.environ', {}, clear=True):
            config = AppConfig(
                cosmos_endpoint="https://test.documents.azure.com:443/",
                cosmos_key="test-key",
                cosmos_database="config-database"
            )
            
            mock_client = Mock()
            mock_db = Mock()
            mock_client.get_database_client.return_value = mock_db
            
            service = CosmosService(config)
            service._client = mock_client
            
            result = service.database
            
            mock_client.get_database_client.assert_called_once_with('config-database')
    
    def test_database_property_missing_name_raises_error(self):
        """Test database property raises error when database name not configured."""
        from app.core.config import AppConfig
        from unittest.mock import patch
        
        # Clear environment variables to simulate missing database name
        with patch.dict('os.environ', {}, clear=True):
            config = AppConfig(
                cosmos_endpoint="https://test.documents.azure.com:443/",
                cosmos_key="test-key",
                cosmos_database="VoiceDB"  # Valid default
            )
            
            mock_client = Mock()
            service = CosmosService(config)
            service._client = mock_client
            # Simulate missing database name by clearing config
            service.config.cosmos_database = None
            
            with pytest.raises(RuntimeError, match="Cosmos DB name not configured"):
                _ = service.database
    
    def test_database_property_cached(self):
        """Test database property is cached after first access."""
        from app.core.config import AppConfig
        
        config = AppConfig(
            cosmos_endpoint="https://test.documents.azure.com:443/",
            cosmos_key="test-key",
            cosmos_database="test-db"
        )
        
        mock_client = Mock()
        mock_db = Mock()
        mock_client.get_database_client.return_value = mock_db
        
        service = CosmosService(config)
        service._client = mock_client
        
        # Access twice
        _ = service.database
        _ = service.database
        
        # Should only be called once
        assert mock_client.get_database_client.call_count == 1
    
    def test_database_property_cosmos_error_handling(self):
        """Test database property handles Cosmos errors properly."""
        from app.core.config import AppConfig
        
        config = AppConfig(
            cosmos_endpoint="https://test.documents.azure.com:443/",
            cosmos_key="test-key",
            cosmos_database="test-db"
        )
        
        mock_client = Mock()
        mock_client.get_database_client.side_effect = CosmosHttpResponseError(
            status_code=404,
            message="Database not found"
        )
        
        service = CosmosService(config)
        service._client = mock_client
        
        with pytest.raises(RuntimeError, match="Failed to get Cosmos database client"):
            _ = service.database


# ============================================================================
# Container Retrieval Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosContainerRetrieval:
    """Test container retrieval with prefixing and fallback logic."""
    
    def test_get_container_with_prefix(self, test_config):
        """Test container retrieval uses prefixed name from config."""
        mock_db = Mock()
        mock_container = Mock()
        mock_db.get_container_client.return_value = mock_container
        
        service = CosmosService(test_config)
        service._database = mock_db
        
        # Config has a cosmos_containers property that generates prefixed names
        # Based on cosmos_prefix + container name (e.g., "voice_jobs")
        result = service.get_container("jobs")
        
        assert result == mock_container
        # Should be called with prefixed name from config.cosmos_containers
        expected_name = test_config.cosmos_containers.get("jobs", "jobs")
        mock_db.get_container_client.assert_called_once_with(expected_name)
    
    def test_get_container_fallback_to_raw_name(self, test_config):
        """Test container retrieval falls back to raw name when prefixed not found."""
        mock_db = Mock()
        mock_container = Mock()
        
        # First call fails (prefixed name not found), second succeeds (raw name)
        mock_db.get_container_client.side_effect = [
            CosmosResourceNotFoundError(status_code=404, message="Not found"),
            mock_container
        ]
        
        service = CosmosService(test_config)
        service._database = mock_db
        
        result = service.get_container("jobs")
        
        assert result == mock_container
        # Should try prefixed name first, then fall back to raw name
        assert mock_db.get_container_client.call_count == 2
    
    def test_get_container_cached_after_first_access(self, test_config):
        """Test container is cached after first successful retrieval."""
        mock_db = Mock()
        mock_container = Mock()
        mock_db.get_container_client.return_value = mock_container
        
        service = CosmosService(test_config)
        service._database = mock_db
        
        # Access container twice
        result1 = service.get_container("jobs")
        result2 = service.get_container("jobs")
        
        assert result1 == result2
        # Should only call once due to caching
        assert mock_db.get_container_client.call_count == 1
    
    def test_get_container_not_found_raises_error(self, test_config):
        """Test container retrieval raises error when container doesn't exist."""
        mock_db = Mock()
        
        # Both prefixed and raw name fail
        mock_db.get_container_client.side_effect = CosmosHttpResponseError(
            status_code=404,
            message="Container not found"
        )
        
        service = CosmosService(test_config)
        service._database = mock_db
        
        with pytest.raises(RuntimeError, match="Container not found"):
            service.get_container("jobs")


# ============================================================================
# User Operations Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCosmosUserOperations:
    """Test user CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, test_config, mock_cosmos_container):
        """Test successful user retrieval by ID."""
        user = {
            "id": "user-123",
            "type": "user",
            "email": "test@example.com",
            "permission": "User"
        }
        mock_cosmos_container.query_items.return_value = [user]
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.get_user_by_id("user-123")
        
        assert result == user
        mock_cosmos_container.query_items.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self, test_config, mock_cosmos_container):
        """Test successful user retrieval by email."""
        user = {
            "id": "user-123",
            "type": "user",
            "email": "test@example.com",
            "permission": "User"
        }
        mock_cosmos_container.query_items.return_value = [user]
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.get_user_by_email("test@example.com")
        
        assert result == user
        assert result["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_get_all_users_success(self, test_config, mock_cosmos_container):
        """Test retrieving all users."""
        users = [
            {"id": "user-1", "type": "user", "email": "user1@example.com"},
            {"id": "user-2", "type": "user", "email": "user2@example.com"}
        ]
        mock_cosmos_container.query_items.return_value = users
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.get_all_users()
        
        assert len(result) == 2
        assert result == users
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, test_config, mock_cosmos_container):
        """Test successful user creation."""
        user_doc = {
            "id": "new-user-123",
            "type": "user",
            "email": "newuser@example.com",
            "permission": "User"
        }
        mock_cosmos_container.create_item.return_value = {**user_doc, "_etag": "etag123"}
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.create_user(user_doc)
        
        assert result["id"] == "new-user-123"
        assert "_etag" in result
        mock_cosmos_container.create_item.assert_called_once_with(body=user_doc)
    
    @pytest.mark.asyncio
    async def test_update_user_success(self, test_config, mock_cosmos_container):
        """Test successful user update."""
        existing_user = {
            "id": "user-123",
            "type": "user",
            "email": "test@example.com",
            "permission": "User"
        }
        updated_user = {**existing_user, "permission": "Editor"}
        
        # Mock get_user_by_id to return existing user
        mock_cosmos_container.query_items.return_value = [existing_user]
        mock_cosmos_container.replace_item.return_value = updated_user
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.update_user("user-123", {"permission": "Editor"})
        
        assert result["permission"] == "Editor"
        mock_cosmos_container.replace_item.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_not_found_raises_error(self, test_config, mock_cosmos_container):
        """Test updating non-existent user raises ValueError."""
        mock_cosmos_container.query_items.return_value = []
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        with pytest.raises(ValueError, match="User with id .* not found"):
            await service.update_user("nonexistent-user", {"permission": "Admin"})
    
    @pytest.mark.asyncio
    async def test_delete_user_success(self, test_config, mock_cosmos_container):
        """Test successful user deletion."""
        mock_cosmos_container.delete_item.return_value = None
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.delete_user("user-123")
        
        assert result is True
        mock_cosmos_container.delete_item.assert_called_once_with(
            item="user-123",
            partition_key="user-123"
        )
    
    @pytest.mark.asyncio
    async def test_delete_user_not_found_returns_false(self, test_config, mock_cosmos_container):
        """Test deleting non-existent user returns False."""
        mock_cosmos_container.delete_item.side_effect = CosmosResourceNotFoundError(
            status_code=404,
            message="Not found"
        )
        
        service = CosmosService(test_config)
        service._containers = {"auth": mock_cosmos_container}
        
        result = await service.delete_user("nonexistent-user")
        
        assert result is False


# ============================================================================
# Container Property Tests
# ============================================================================

@pytest.mark.unit
class TestCosmosContainerProperties:
    """Test container property accessors."""
    
    def test_jobs_container_property(self, test_config):
        """Test jobs_container property returns correct container."""
        mock_container = Mock()
        
        service = CosmosService(test_config)
        service._containers = {"jobs": mock_container}
        
        result = service.jobs_container
        
        assert result == mock_container
    
    def test_analytics_container_property(self, test_config):
        """Test analytics_container property returns correct container."""
        mock_container = Mock()
        
        service = CosmosService(test_config)
        service._containers = {"analytics": mock_container}
        
        result = service.analytics_container
        
        assert result == mock_container
    
    def test_sessions_container_property(self, test_config):
        """Test sessions_container property returns correct container."""
        mock_container = Mock()
        
        service = CosmosService(test_config)
        service._containers = {"user_sessions": mock_container}
        
        result = service.sessions_container
        
        assert result == mock_container
    
    def test_audit_container_property(self, test_config):
        """Test audit_container property returns correct container."""
        mock_container = Mock()
        
        service = CosmosService(test_config)
        service._containers = {"audit_logs": mock_container}
        
        result = service.audit_container
        
        assert result == mock_container
