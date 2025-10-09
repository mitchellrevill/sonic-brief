"""
Integration test fixtures for Sonic Brief backend.

Provides fixtures for testing service interactions with real or semi-real dependencies.
Unlike unit tests which mock everything, integration tests use actual service instances
with test-specific configurations.
"""
import asyncio
import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.core.config import AppConfig
from app.core.dependencies import CosmosService
from app.services.storage.blob_service import StorageService
from app.services.jobs.job_service import JobService
from app.services.auth.authentication_service import AuthenticationService
from app.services.analytics.analytics_service import AnalyticsService
from app.services.prompts.prompt_service import PromptService
from app.services.prompts.talking_points_service import TalkingPointsService
from app.services.processing.background_service import BackgroundProcessingService


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def integration_config() -> AppConfig:
    """
    Integration test configuration.
    Uses test-specific values to avoid impacting production data.
    """
    config = AppConfig()
    
    # Override with test-specific values
    config.cosmos_database_name = "test_sonic_brief_db"
    config.storage_account_name = "teststorageaccount"
    config.azure_openai_endpoint = "https://test-openai.openai.azure.com/"
    config.azure_openai_deployment = "test-gpt-4"
    config.azure_functions_base_url = "https://test-functions.azurewebsites.net"
    
    return config


# ============================================================================
# Cosmos Service Fixtures (Semi-Real)
# ============================================================================

@pytest.fixture
def mock_cosmos_container():
    """Mock Cosmos container with realistic query/upsert behavior"""
    container = Mock()
    
    # In-memory storage for test data
    container._test_data: Dict[str, Dict[str, Any]] = {}
    
    def upsert_item(item: Dict[str, Any]):
        """Store item in memory"""
        item_id = item.get("id")
        if item_id:
            container._test_data[item_id] = item
        return item
    
    def query_items(query: str, **kwargs):
        """Return stored items matching query (simplified)"""
        # Simple implementation - return all items
        return list(container._test_data.values())
    
    def read_item(item_id: str, partition_key: str):
        """Read specific item"""
        if item_id in container._test_data:
            return container._test_data[item_id]
        raise Exception(f"Item {item_id} not found")
    
    container.upsert_item = Mock(side_effect=upsert_item)
    container.query_items = Mock(side_effect=query_items)
    container.read_item = Mock(side_effect=read_item)
    
    return container


@pytest.fixture
def integration_cosmos_service(integration_config, mock_cosmos_container) -> CosmosService:
    """
    Cosmos service for integration tests.
    Uses mocked containers but realistic service logic.
    """
    service = CosmosService(integration_config)
    
    # Mock the client and database
    service._client = Mock()
    service._database = Mock()
    service._is_available = True
    
    # Return our mock container for all container requests
    def get_container(name: str):
        return mock_cosmos_container
    
    service._database.get_container_client = Mock(side_effect=get_container)
    
    return service


# ============================================================================
# Storage Service Fixtures
# ============================================================================

@pytest.fixture
def mock_blob_service_client():
    """Mock Azure Blob Service Client for integration tests"""
    client = Mock()
    
    # In-memory blob storage
    test_blobs = {}
    
    def get_blob_client(container: str, blob: str):
        blob_client = Mock()
        blob_path = f"{container}/{blob}"
        
        async def upload_blob(data, **kwargs):
            if asyncio.iscoroutine(data):
                data = await data
            elif hasattr(data, 'read'):
                data = data.read()
            test_blobs[blob_path] = data
            return {"etag": "test-etag", "last_modified": datetime.utcnow()}
        
        async def download_blob():
            mock_download = AsyncMock()
            mock_download.readall = AsyncMock(return_value=test_blobs.get(blob_path, b""))
            return mock_download
        
        async def check_exists():
            return blob_path in test_blobs
        
        blob_client.upload_blob = AsyncMock(side_effect=upload_blob)
        blob_client.download_blob = AsyncMock(side_effect=download_blob)
        blob_client.exists = AsyncMock(side_effect=check_exists)
        
        return blob_client
    
    client.get_blob_client = Mock(side_effect=get_blob_client)
    client._test_blobs = test_blobs  # Expose for debugging
    
    return client


@pytest.fixture
def integration_storage_service(integration_config, mock_blob_service_client) -> StorageService:
    """
    Storage service for integration tests.
    Uses mocked blob client but real service logic.
    """
    service = StorageService(integration_config)
    service._blob_service_client = mock_blob_service_client
    
    return service


# ============================================================================
# Job Service Fixtures
# ============================================================================

@pytest.fixture
def integration_job_service(
    integration_cosmos_service,
    integration_storage_service
) -> JobService:
    """
    Job service for integration tests.
    Combines real cosmos and storage services.
    """
    return JobService(
        cosmos_service=integration_cosmos_service,
        storage_service=integration_storage_service
    )


# ============================================================================
# Authentication Service Fixtures
# ============================================================================

@pytest.fixture
def integration_auth_service() -> AuthenticationService:
    """
    Authentication service for integration tests.
    Note: AuthenticationService doesn't depend on Cosmos directly.
    """
    return AuthenticationService()


# ============================================================================
# Analytics Service Fixtures
# ============================================================================

@pytest.fixture
def integration_analytics_service(integration_cosmos_service) -> AnalyticsService:
    """
    Analytics service for integration tests.
    """
    return AnalyticsService(cosmos_service=integration_cosmos_service)


# ============================================================================
# AI Service Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for integration tests"""
    client = Mock()
    
    # Mock chat completions
    async def create_completion(*args, **kwargs):
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message = Mock()
        response.choices[0].message.content = "Test AI response"
        return response
    
    client.chat = Mock()
    client.chat.completions = Mock()
    client.chat.completions.create = AsyncMock(side_effect=create_completion)
    
    return client


@pytest.fixture
def integration_prompt_service(
    integration_cosmos_service,
    mock_openai_client
) -> PromptService:
    """
    Prompt service for integration tests.
    """
    service = PromptService(cosmos_service=integration_cosmos_service)
    service._client = mock_openai_client
    
    return service


@pytest.fixture
def integration_talking_points_service(
    integration_cosmos_service,
    mock_openai_client
) -> TalkingPointsService:
    """
    Talking points service for integration tests.
    """
    service = TalkingPointsService(cosmos_service=integration_cosmos_service)
    service._client = mock_openai_client
    
    return service


# ============================================================================
# Background Processing Fixtures
# ============================================================================

@pytest.fixture
def mock_httpx_client_integration():
    """Mock httpx client for background service integration tests"""
    client = AsyncMock()
    
    # Default successful response
    response = AsyncMock()
    response.status_code = 200
    response.json = AsyncMock(return_value={"status": "success"})
    response.raise_for_status = Mock()
    
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)
    
    return client


@pytest.fixture
def integration_background_service(
    integration_cosmos_service,
    mock_httpx_client_integration,
    integration_config
) -> BackgroundProcessingService:
    """
    Background processing service for integration tests.
    """
    # Ensure config has azure_functions attributes
    if not hasattr(integration_config, 'azure_functions'):
        integration_config.azure_functions = type('obj', (object,), {
            'base_url': 'https://test-functions.azurewebsites.net'
        })()
    if not hasattr(integration_config, 'azure_functions_base_url'):
        integration_config.azure_functions_base_url = 'https://test-functions.azurewebsites.net'
    
    service = BackgroundProcessingService(cosmos_service=integration_cosmos_service)
    
    # Inject mock HTTP client
    import app.core.http_client as http_client_module
    http_client_module._client = mock_httpx_client_integration
    
    return service


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Sample user data for integration tests"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "permissions": ["read", "write"],
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def test_job_data() -> Dict[str, Any]:
    """Sample job data for integration tests"""
    return {
        "id": "test-job-123",
        "user_id": "test-user-123",
        "title": "Test Transcription Job",
        "status": "pending",
        "file_url": "https://test-storage.blob.core.windows.net/test/audio.mp3",
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def test_analytics_event() -> Dict[str, Any]:
    """Sample analytics event for integration tests"""
    return {
        "event_type": "job_created",
        "user_id": "test-user-123",
        "job_id": "test-job-123",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "source": "web",
            "duration": 120
        }
    }
