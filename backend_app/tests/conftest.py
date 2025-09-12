import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
from app.main import app
from app.core.dependencies import get_current_user
from app.models.permissions import PermissionLevel, PermissionCapability


@pytest.fixture
def fake_user():
    """Standard test user with USER permission level."""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "permission_level": PermissionLevel.USER,
        "custom_permissions": {}
    }


@pytest.fixture
def fake_admin_user():
    """Admin user for testing admin-only features."""
    return {
        "id": "admin-user-456",
        "email": "admin@example.com", 
        "permission_level": PermissionLevel.ADMIN,
        "custom_permissions": {}
    }


@pytest.fixture
def fake_editor_user():
    """Editor user for testing editor capabilities."""
    return {
        "id": "editor-user-789",
        "email": "editor@example.com",
        "permission_level": PermissionLevel.EDITOR,
        "custom_permissions": {}
    }


@pytest.fixture
def fake_job():
    """Standard test job owned by fake_user."""
    return {
        "id": "job-abc-123",
        "owner_id": "test-user-123",
        "status": "completed",
        "title": "Test Job",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def other_user_job():
    """Job owned by a different user."""
    return {
        "id": "job-xyz-789", 
        "owner_id": "other-user-999",
        "status": "completed",
        "title": "Other User Job",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def mock_cosmos_service(monkeypatch):
    """Mock cosmos service with common return values."""
    mock_service = Mock()
    mock_service.get_job_by_id.return_value = None
    mock_service.query_jobs_for_user.return_value = []
    mock_service.update_job.return_value = True
    
    monkeypatch.setattr("app.services.cosmos_service", mock_service)
    return mock_service


@pytest.fixture
def mock_storage_service(monkeypatch):
    """Mock storage service for file operations."""
    mock_service = Mock()
    mock_service.upload_blob.return_value = {"blob_url": "https://test.blob/file"}
    mock_service.get_blob_stream.return_value = b"test file content"
    
    monkeypatch.setattr("app.services.storage_service", mock_service)
    return mock_service


@pytest.fixture
def mock_analysis_service(monkeypatch):
    """Mock analysis service for processing operations."""
    mock_service = Mock()
    mock_service.process_refine.return_value = {"status": "completed"}
    mock_service.generate_talking_points.return_value = {"talking_points": ["point1", "point2"]}
    
    monkeypatch.setattr("app.services.analysis_service", mock_service)
    return mock_service


@pytest.fixture
def mock_export_service(monkeypatch):
    """Mock export service for export operations."""
    mock_service = Mock()
    mock_service.export_job.return_value = b"exported content"
    
    monkeypatch.setattr("app.services.export_service", mock_service)
    return mock_service


def override_get_current_user(client: TestClient, user: dict):
    """Helper to override the get_current_user dependency with a test user."""
    app.dependency_overrides[get_current_user] = lambda: user


def clear_dependency_overrides(client: TestClient):
    """Helper to clear all dependency overrides."""
    app.dependency_overrides.clear()


@pytest.fixture
def app_client():
    """FastAPI TestClient for route testing."""
    client = TestClient(app)
    yield client
    # Clean up dependency overrides after each test
    clear_dependency_overrides(client)


@pytest.fixture
def capability_map():
    """Sample capability map for testing."""
    return {
        PermissionCapability.CAN_VIEW_OWN_JOBS: True,
        PermissionCapability.CAN_EDIT_OWN_JOBS: True,
        PermissionCapability.CAN_DOWNLOAD_FILES: True,
        PermissionCapability.CAN_EXPORT_DATA: False,
        PermissionCapability.CAN_UPLOAD_FILES: True,
        PermissionCapability.CAN_VIEW_ALL_JOBS: False,
        PermissionCapability.CAN_EDIT_ALL_JOBS: False,
        PermissionCapability.CAN_DELETE_ALL_JOBS: False,
        PermissionCapability.CAN_SHARE_JOBS: False,
    }
