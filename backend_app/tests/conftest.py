"""
Shared pytest fixtures and configuration for Sonic Brief backend tests.

This file provides common test fixtures, mocks, and utilities used across
all test files in the test suite.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import uuid

# Set test environment variables before importing app modules
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["AZURE_COSMOS_ENDPOINT"] = "https://test-cosmos.documents.azure.com:443/"
os.environ["AZURE_COSMOS_KEY"] = "test-cosmos-key"
os.environ["AZURE_COSMOS_DATABASE_NAME"] = "test-database"
os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=testkey;EndpointSuffix=core.windows.net"

from app.core.config import AppConfig
from app.core.dependencies import CosmosService
from app.services.auth.authentication_service import AuthenticationService
from app.services.jobs.job_service import JobService


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Provide test configuration."""
    config = AppConfig()
    config.cosmos_endpoint = "https://test-cosmos.documents.azure.com:443/"
    config.cosmos_key = "test-cosmos-key"
    config.cosmos_database_name = "test-database"
    config.cosmos_jobs_container_name = "jobs"
    config.cosmos_permissions_container_name = "permissions"
    config.storage_connection_string = "DefaultEndpointsProtocol=https;AccountName=teststorage;AccountKey=testkey;EndpointSuffix=core.windows.net"
    config.storage_container_name = "test-uploads"
    
    return config


@pytest.fixture
def mock_config():
    """Provide a mock AppConfig for testing (legacy compatibility)"""
    config = Mock(spec=AppConfig)
    config.cosmos_endpoint = "https://test-cosmos.documents.azure.com:443/"
    config.cosmos_key = "test-cosmos-key-12345"
    config.cosmos_database = "test-db"
    config.cosmos_containers = {
        "jobs": "test-jobs",
        "auth": "test-auth",
        "analytics": "test-analytics",
        "user_sessions": "test-sessions",
        "audit_logs": "test-audit"
    }
    config.storage_account_name = "teststorage"
    config.storage_container_name = "test-files"
    config.storage_connection_string = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test=="
    return config


# ============================================================================
# Azure Cosmos DB Mocking Fixtures
# ============================================================================

@pytest.fixture
def mock_cosmos_client():
    """Mock CosmosClient from Azure SDK."""
    client = Mock()
    
    # Mock database
    database = Mock()
    client.get_database_client.return_value = database
    
    # Mock containers
    jobs_container = Mock()
    permissions_container = Mock()
    
    database.get_container_client.side_effect = lambda name: {
        "jobs": jobs_container,
        "permissions": permissions_container,
    }.get(name, Mock())
    
    # Setup default container behaviors
    jobs_container.query_items.return_value = []
    jobs_container.read_item.side_effect = lambda item, partition_key: {
        "id": item,
        "type": "job",
        "status": "completed"
    }
    
    permissions_container.query_items.return_value = []
    
    return client


@pytest.fixture
def mock_cosmos_container():
    """Mock Cosmos DB container with common operations"""
    container = Mock()
    
    # Mock query_items to return empty list by default
    container.query_items.return_value = []
    
    # Mock create_item to return the created item
    def create_item_side_effect(body):
        return {**body, "_rid": "test-rid", "_etag": "test-etag"}
    container.create_item.side_effect = create_item_side_effect
    
    # Mock replace_item to return the updated item
    def replace_item_side_effect(item, body):
        return {**body, "_rid": "test-rid", "_etag": "test-etag-2"}
    container.replace_item.side_effect = replace_item_side_effect
    
    # Mock delete_item to succeed silently
    container.delete_item.return_value = None
    
    return container


@pytest.fixture
def mock_cosmos_database(mock_cosmos_container):
    """Mock Cosmos DB database"""
    database = Mock()
    database.get_container_client.return_value = mock_cosmos_container
    return database


@pytest.fixture
def cosmos_service(mock_config, mock_cosmos_client, mock_cosmos_database):
    """Provide a CosmosService instance with mocked dependencies"""
    service = CosmosService(mock_config)
    service._client = mock_cosmos_client
    service._database = mock_cosmos_database
    service._is_available = True
    
    # Setup container cache
    service._containers = {
        "jobs": mock_cosmos_database.get_container_client("test-jobs"),
        "auth": mock_cosmos_database.get_container_client("test-auth"),
        "analytics": mock_cosmos_database.get_container_client("test-analytics"),
        "user_sessions": mock_cosmos_database.get_container_client("test-sessions"),
        "audit_logs": mock_cosmos_database.get_container_client("test-audit")
    }
    
    return service


@pytest.fixture
def mock_cosmos_service(mock_config, mock_cosmos_container):
    """Mock CosmosService for job service tests"""
    service = Mock(spec=CosmosService)
    service.get_container = Mock(return_value=mock_cosmos_container)
    service.jobs_container = mock_cosmos_container
    service.get_job = Mock(return_value=None)
    service.create_job = Mock(side_effect=lambda doc: {**doc, "_etag": "test-etag"})
    service.update_job = Mock(side_effect=lambda job_id, doc: {**doc, "_etag": "new-etag"})
    service.is_available = Mock(return_value=True)
    
    # Add config for services that need it (like BackgroundProcessingService)
    service.config = mock_config
    service.config.azure_functions = {"base_url": "https://test-func.azurewebsites.net"}
    service.config.azure_functions_base_url = "https://test-func.azurewebsites.net"
    
    return service


# ===== Authentication Fixtures =====

@pytest.fixture
def mock_jwt_secret():
    """Mock JWT secret key"""
    return "test-secret-key-for-jwt-signing-123456"


@pytest.fixture
def mock_request():
    """Mock FastAPI request object"""
    request = Mock()
    request.headers = {}
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"
    return request


@pytest.fixture
def valid_jwt_token(mock_jwt_secret):
    """Generate a valid JWT token for testing"""
    from jose import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "permission": "User",
        "custom_capabilities": {},
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()
    }
    
    return jwt.encode(payload, mock_jwt_secret, algorithm="HS256")


@pytest.fixture
def expired_jwt_token(mock_jwt_secret):
    """Generate an expired JWT token for testing"""
    from jose import jwt
    from datetime import datetime, timedelta
    
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "permission": "User",
        "iat": (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp(),
        "exp": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
    }
    
    return jwt.encode(payload, mock_jwt_secret, algorithm="HS256")


@pytest.fixture
def authentication_service(mock_jwt_secret):
    """Provide an AuthenticationService instance with mocked JWT secret"""
    with patch.dict('os.environ', {
        'JWT_SECRET_KEY': mock_jwt_secret,
        'JWT_ALGORITHM': 'HS256'
    }):
        service = AuthenticationService()
        return service


# ===== Job Service Fixtures =====

@pytest.fixture
def mock_storage_service():
    """Mock StorageService for JobService tests"""
    storage = Mock()
    storage.upload_file.return_value = "https://test-storage.blob.core.windows.net/test-files/test-file.mp3"
    storage.add_sas_token_to_url.side_effect = lambda url: f"{url}?sas=test-token"
    storage.delete_file.return_value = True
    return storage


@pytest.fixture
def job_service(cosmos_service, mock_storage_service):
    """Provide a JobService instance with mocked dependencies"""
    return JobService(cosmos_service, mock_storage_service)


# ===== Test Data Fixtures =====

@pytest.fixture
def sample_user():
    """Sample user document"""
    return {
        "id": "user-123",
        "type": "user",
        "email": "test@example.com",
        "permission": "User",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "custom_capabilities": {}
    }


@pytest.fixture
def sample_admin_user():
    """Sample admin user document"""
    return {
        "id": "admin-123",
        "type": "user",
        "email": "admin@example.com",
        "permission": "Admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "custom_capabilities": {}
    }


@pytest.fixture
def sample_job():
    """Sample job document"""
    job_id = str(uuid.uuid4())
    return {
        "id": job_id,
        "type": "job",
        "user_id": "user-123",
        "user_email": "test@example.com",
        "file_name": "test-recording.mp3",
        "file_path": "https://test-storage.blob.core.windows.net/test-files/test-recording.mp3",
        "status": "uploaded",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "displayname": "Test Recording"
    }


@pytest.fixture
def sample_completed_job(sample_job):
    """Sample completed job document"""
    return {
        **sample_job,
        "status": "completed",
        "transcription_file_path": "https://test-storage.blob.core.windows.net/test-files/transcription.json",
        "analysis_file_path": "https://test-storage.blob.core.windows.net/test-files/analysis.json",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Utility Functions =====

def create_mock_cosmos_error(status_code: int, message: str = "Cosmos error"):
    """Helper to create mock Cosmos HTTP response errors"""
    from azure.cosmos.exceptions import CosmosHttpResponseError
    
    error = Mock(spec=CosmosHttpResponseError)
    error.status_code = status_code
    error.message = message
    error.__str__ = Mock(return_value=message)
    return error


@pytest.fixture
def cosmos_error_factory():
    """Factory fixture for creating Cosmos errors"""
    return create_mock_cosmos_error


# ============================================================================
# Authentication & JWT Token Fixtures
# ============================================================================

@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token for testing."""
    from jose import jwt
    
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "permission": "user",
        "custom_capabilities": {},
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return token


@pytest.fixture
def expired_jwt_token():
    """Generate an expired JWT token for testing."""
    from jose import jwt
    
    payload = {
        "sub": "test-user-123",
        "email": "test@example.com",
        "permission": "user",
        "iat": int((datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
    }
    
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return token


@pytest.fixture
def admin_jwt_token():
    """Generate an admin JWT token for testing."""
    from jose import jwt
    
    payload = {
        "sub": "admin-user-123",
        "email": "admin@example.com",
        "permission": "admin",
        "custom_capabilities": {"can_manage_users": True},
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    }
    
    token = jwt.encode(payload, "test-secret-key-for-testing-only", algorithm="HS256")
    return token


@pytest.fixture
def malformed_jwt_token():
    """Generate a malformed JWT token for testing."""
    return "not.a.valid.jwt.token.at.all"


@pytest.fixture
def mock_request_with_auth(valid_jwt_token):
    """Mock FastAPI Request with valid authentication."""
    request = Mock()
    headers_dict = {
        "Authorization": f"Bearer {valid_jwt_token}",
        "User-Agent": "Mozilla/5.0 Test Browser",
        "X-Forwarded-For": "192.168.1.1"
    }
    request.headers = MagicMock()
    request.headers.get = Mock(side_effect=lambda key, default=None: headers_dict.get(key, default))
    request.client = Mock()
    request.client.host = "127.0.0.1"
    
    return request


@pytest.fixture
def mock_request_without_auth():
    """Mock FastAPI Request without authentication."""
    request = Mock()
    headers_dict = {
        "User-Agent": "Mozilla/5.0 Test Browser"
    }
    request.headers = MagicMock()
    request.headers.get = Mock(side_effect=lambda key, default=None: headers_dict.get(key, default))
    request.client = Mock()
    request.client.host = "127.0.0.1"
    
    return request


# ============================================================================
# Test Data Factories
# ============================================================================

@pytest.fixture
def job_factory():
    """Factory for creating test job documents."""
    def _create_job(
        job_id: Optional[str] = None,
        user_id: str = "test-user-123",
        status: str = "pending",
        **kwargs
    ) -> Dict[str, Any]:
        job = {
            "id": job_id or str(uuid.uuid4()),
            "type": "job",
            "user_id": user_id,
            "user_email": f"{user_id}@example.com",
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_name": "test-audio.mp3",
            "file_path": "https://teststorage.blob.core.windows.net/uploads/test-audio.mp3",
            "displayname": "Test Recording",
            "is_deleted": False
        }
        job.update(kwargs)
        return job
    
    return _create_job


@pytest.fixture
def user_factory():
    """Factory for creating test user documents."""
    def _create_user(
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        permission: str = "user",
        **kwargs
    ) -> Dict[str, Any]:
        uid = user_id or str(uuid.uuid4())
        user = {
            "id": uid,
            "email": email or f"{uid}@example.com",
            "permission": permission,
            "custom_capabilities": {},
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        user.update(kwargs)
        return user
    
    return _create_user


@pytest.fixture
def permission_factory():
    """Factory for creating test permission documents."""
    def _create_permission(
        permission_id: Optional[str] = None,
        resource_id: str = "test-job-123",
        user_id: str = "test-user-123",
        permission_level: str = "owner",
        **kwargs
    ) -> Dict[str, Any]:
        perm = {
            "id": permission_id or str(uuid.uuid4()),
            "type": "permission",
            "resource_id": resource_id,
            "resource_type": "job",
            "user_id": user_id,
            "permission_level": permission_level,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        perm.update(kwargs)
        return perm
    
    return _create_permission


# ============================================================================
# Phase 2: Prompt Service Fixtures
# ============================================================================

@pytest.fixture
def mock_prompt_container():
    """Mock Cosmos container for prompts."""
    container = Mock()
    container.create_item = Mock(side_effect=lambda body: body)
    container.upsert_item = Mock(side_effect=lambda body: body)
    container.delete_item = Mock(return_value=None)
    container.query_items = Mock(return_value=[])
    return container


@pytest.fixture
def category_factory():
    """Factory for creating test category documents."""
    def _create_category(
        category_id: Optional[str] = None,
        name: str = "Test Category",
        parent_category_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        category = {
            "id": category_id or f"category_{timestamp}",
            "type": "prompt_category",
            "name": name,
            "created_at": timestamp,
            "updated_at": timestamp,
            "parent_category_id": parent_category_id,
        }
        category.update(kwargs)
        return category
    
    return _create_category


@pytest.fixture
def subcategory_factory():
    """Factory for creating test subcategory documents."""
    def _create_subcategory(
        subcategory_id: Optional[str] = None,
        category_id: str = "category_1234567890",
        name: str = "Test Subcategory",
        prompts: Optional[Dict[str, str]] = None,
        pre_session: Optional[list] = None,
        in_session: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        subcategory = {
            "id": subcategory_id or f"subcategory_{timestamp}_{uuid.uuid4().hex}",
            "type": "prompt_subcategory",
            "category_id": category_id,
            "name": name,
            "prompts": prompts or {"key1": "prompt1", "key2": "prompt2"},
            "preSessionTalkingPoints": pre_session or [],
            "inSessionTalkingPoints": in_session or [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        subcategory.update(kwargs)
        return subcategory
    
    return _create_subcategory


# ============================================================================
# Phase 3: Analytics & Monitoring Service Fixtures
# ============================================================================

@pytest.fixture
def mock_analytics_container():
    """Mock Cosmos container for analytics."""
    container = Mock()
    container.create_item = Mock(side_effect=lambda body: body)
    container.query_items = Mock(return_value=[])
    return container


@pytest.fixture
def mock_events_container():
    """Mock Cosmos container for events."""
    container = Mock()
    container.create_item = Mock(side_effect=lambda body: body)
    container.query_items = Mock(return_value=[])
    return container


@pytest.fixture
def event_factory():
    """Factory for creating test event documents."""
    def _create_event(
        event_id: Optional[str] = None,
        event_type: str = "test_event",
        user_id: str = "test-user-123",
        job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        event = {
            "id": event_id or str(uuid.uuid4()),
            "type": "event",
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "partition_key": user_id,
        }
        if job_id:
            event["job_id"] = job_id
        event.update(kwargs)
        return event
    
    return _create_event


@pytest.fixture
def analytics_factory():
    """Factory for creating test analytics documents."""
    def _create_analytics(
        analytics_id: Optional[str] = None,
        user_id: str = "test-user-123",
        job_id: str = "test-job-123",
        event_type: str = "job_created",
        audio_duration_seconds: Optional[float] = None,
        audio_duration_minutes: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc)
        analytics = {
            "id": analytics_id or f"analytics_job_{int(timestamp.timestamp() * 1000)}",
            "type": "transcription_analytics",
            "user_id": user_id,
            "job_id": job_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "partition_key": user_id,
        }
        if audio_duration_minutes is not None:
            analytics["audio_duration_minutes"] = float(audio_duration_minutes)
        if audio_duration_seconds is not None:
            analytics["audio_duration_seconds"] = float(audio_duration_seconds)
        analytics.update(kwargs)
        # Remove None values
        return {k: v for k, v in analytics.items() if v is not None}
    
    return _create_analytics


# ===== Additional Phase 3 Fixtures =====

@pytest.fixture
def mock_audit_container():
    """Mock for audit container with common methods"""
    container = Mock()
    container.upsert_item = Mock(return_value={"id": "audit-123"})
    container.query_items = Mock(return_value=[])
    return container


@pytest.fixture
def mock_sessions_container():
    """Mock for sessions container with common methods"""
    container = Mock()
    container.upsert_item = Mock(return_value={"id": "session-123"})
    container.read_item = Mock(return_value={"id": "session-123", "status": "active"})
    container.query_items = Mock(return_value=[])
    return container


@pytest.fixture
def user_factory():
    """Factory for creating test user documents"""
    def _create_user(
        user_id: str = None,
        email: str = "test@example.com",
        full_name: str = "Test User",
        permission: str = "user",
        source: str = "microsoft",
        microsoft_oid: str = None,
        is_active: bool = True
    ):
        if user_id is None:
            user_id = f"user-{uuid.uuid4().hex[:8]}"
        if microsoft_oid is None:
            microsoft_oid = str(uuid.uuid4())
        
        return {
            "id": user_id,
            "type": "user",
            "email": email,
            "full_name": full_name,
            "permission": permission,
            "source": source,
            "microsoft_oid": microsoft_oid,
            "tenant_id": "tenant-123",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "is_active": is_active,
            "partition_key": user_id
        }
    return _create_user


@pytest.fixture
def session_factory():
    """Factory for creating test session documents"""
    def _create_session(
        user_id: str = "user-123",
        user_email: str = "test@example.com",
        status: str = "active",
        created_at: str = None,
        last_activity: str = None
    ):
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()
        if last_activity is None:
            last_activity = datetime.now(timezone.utc).isoformat()
        
        return {
            "id": user_id,
            "user_id": user_id,
            "user_email": user_email,
            "type": "session",
            "status": status,
            "created_at": created_at,
            "last_activity": last_activity,
            "last_heartbeat": last_activity,
            "partition_key": user_id,
            "endpoints_accessed": [],
            "request_count": 1
        }
    return _create_session


# ============================================================================
# Phase 4: Storage & Processing Service Fixtures
# ============================================================================

@pytest.fixture
def mock_blob_service_client():
    """Mock BlobServiceClient for testing"""
    mock_client = Mock()
    mock_container_client = Mock()
    mock_blob_client = Mock()
    
    # Setup container client
    mock_client.get_container_client = Mock(return_value=mock_container_client)
    mock_container_client.get_blob_client = Mock(return_value=mock_blob_client)
    
    # Setup blob client
    mock_blob_client.url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
    mock_blob_client.upload_blob = Mock()
    mock_blob_client.download_blob = Mock()
    mock_blob_client.delete_blob = Mock()
    
    return mock_client


@pytest.fixture
def mock_async_blob_client():
    """Mock AsyncBlobClient for streaming operations"""
    mock_client = AsyncMock()
    
    # Setup download blob with async chunks
    mock_downloader = AsyncMock()
    async def mock_chunks():
        yield b"chunk1"
        yield b"chunk2"
        yield b"chunk3"
    mock_downloader.chunks = mock_chunks
    mock_client.download_blob = AsyncMock(return_value=mock_downloader)
    
    # Setup async context manager
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    return mock_client


@pytest.fixture
def storage_config():
    """Configuration for StorageService testing"""
    config = Mock()
    config.azure_storage_account_url = "https://teststorage.blob.core.windows.net"
    config.azure_storage_key = "test-storage-key-base64encoded=="
    config.azure_storage_recordings_container = "recordings"
    return config


@pytest.fixture
def mock_background_task():
    """Factory for creating mock BackgroundTask objects"""
    def _create_task(
        task_id: str = "task-123",
        task_type: str = "file_upload",
        user_id: str = "user-123",
        status: str = "pending"
    ):
        from app.services.processing.background_service import BackgroundTask, TaskStatus
        task = BackgroundTask(task_id, task_type, user_id)
        task.status = TaskStatus[status.upper()]
        return task
    return _create_task


@pytest.fixture
def mock_circuit_breaker():
    """Mock CircuitBreaker for testing"""
    from app.services.processing.background_service import CircuitBreaker
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    return breaker


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for Azure Functions calls"""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json = Mock(return_value={"status": "success"})
    mock_response.raise_for_status = Mock()
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


# ===== Async Test Configuration =====

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "critical: mark test as testing critical functionality")


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset any singleton state between tests."""
    yield
    # Add any singleton cleanup here if needed
