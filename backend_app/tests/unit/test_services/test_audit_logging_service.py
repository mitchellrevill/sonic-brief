"""
Unit tests for AuditLoggingService (Phase 3 - Monitoring Services)

Tests cover:
- Audit log creation
- Container fallback logic (audit → sessions)
- User activity logging
- Endpoint audit determination
- Error handling

Coverage target: 90%+ on app/services/monitoring/audit_logging_service.py
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from azure.cosmos.exceptions import CosmosHttpResponseError

from app.services.monitoring.audit_logging_service import AuditLoggingService
from app.core.dependencies import CosmosService


# ============================================================================
# Test Class: Audit Log Creation
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
class TestAuditLogCreation:
    """Test audit log entry creation"""
    
    async def test_create_audit_log_success_with_audit_container(self, mock_cosmos_service, mock_audit_container):
        """Test successful audit log creation with audit container"""
        # Arrange
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        with patch('app.services.monitoring.audit_logging_service.uuid') as mock_uuid:
            mock_uuid.uuid4.return_value = Mock(hex="audit-id-123")
            mock_uuid.uuid4.return_value.__str__ = Mock(return_value="audit-id-123")
            
            audit_id = await service.create_audit_log(
                user_id="user-123",
                user_email="test@example.com",
                event_type="user_login",
                endpoint="/api/auth/login",
                method="POST",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                user_permission="user"
            )
        
        # Assert
        assert audit_id is not None
        mock_audit_container.upsert_item.assert_called_once()
        call_args = mock_audit_container.upsert_item.call_args[0][0]
        assert call_args["type"] == "audit_log"
        assert call_args["user_id"] == "user-123"
        assert call_args["event_type"] == "user_login"
        assert call_args["endpoint"] == "/api/auth/login"
        assert call_args["method"] == "POST"
    
    async def test_create_audit_log_fallback_to_sessions_container(self, mock_cosmos_service, mock_sessions_container):
        """Test audit log falls back to sessions container when audit container unavailable"""
        # Arrange
        mock_cosmos_service.audit_container = None
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="resource_access",
            endpoint="/api/jobs",
            method="GET"
        )
        
        # Assert
        assert audit_id is not None
        mock_sessions_container.upsert_item.assert_called_once()
    
    async def test_create_audit_log_no_container_available(self, mock_cosmos_service):
        """Test audit log returns None when no container available"""
        # Arrange
        mock_cosmos_service.audit_container = None
        mock_cosmos_service.sessions_container = None
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="test_event",
            endpoint="/test",
            method="GET"
        )
        
        # Assert
        assert audit_id is None
    
    async def test_create_audit_log_with_metadata(self, mock_cosmos_service, mock_audit_container):
        """Test audit log includes metadata"""
        # Arrange
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        metadata = {"action": "delete", "resource_name": "test.mp3"}
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="file_deleted",
            endpoint="/api/files/123",
            method="DELETE",
            metadata=metadata
        )
        
        # Assert
        assert audit_id is not None
        call_args = mock_audit_container.upsert_item.call_args[0][0]
        assert call_args["metadata"] == metadata
    
    async def test_create_audit_log_with_resource_info(self, mock_cosmos_service, mock_audit_container):
        """Test audit log includes resource type and ID"""
        # Arrange
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="resource_modified",
            endpoint="/api/jobs/job-456",
            method="PATCH",
            resource_type="job",
            resource_id="job-456"
        )
        
        # Assert
        call_args = mock_audit_container.upsert_item.call_args[0][0]
        assert call_args["resource_type"] == "job"
        assert call_args["resource_id"] == "job-456"
    
    async def test_create_audit_log_custom_timestamp(self, mock_cosmos_service, mock_audit_container):
        """Test audit log with custom timestamp"""
        # Arrange
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="test_event",
            endpoint="/test",
            method="GET",
            timestamp=custom_time
        )
        
        # Assert
        call_args = mock_audit_container.upsert_item.call_args[0][0]
        assert call_args["timestamp"] == custom_time.isoformat()
    
    async def test_create_audit_log_handles_cosmos_error(self, mock_cosmos_service, mock_audit_container):
        """Test audit log handles Cosmos errors gracefully"""
        # Arrange
        error = CosmosHttpResponseError(status_code=500, message="Server error")
        mock_audit_container.upsert_item = Mock(side_effect=error)
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="test_event",
            endpoint="/test",
            method="GET"
        )
        
        # Assert - should return None, not raise
        assert audit_id is None
    
    async def test_create_audit_log_handles_unexpected_error(self, mock_cosmos_service, mock_audit_container):
        """Test audit log handles unexpected errors"""
        # Arrange
        mock_audit_container.upsert_item = Mock(side_effect=Exception("Unexpected"))
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email="test@example.com",
            event_type="test_event",
            endpoint="/test",
            method="GET"
        )
        
        # Assert
        assert audit_id is None


# ============================================================================
# Test Class: Service Properties
# ============================================================================

@pytest.mark.unit
class TestServiceProperties:
    """Test service properties and initialization"""
    
    def test_service_has_cosmos_reference(self, mock_cosmos_service):
        """Test service initializes with cosmos reference"""
        # Arrange & Act
        service = AuditLoggingService(mock_cosmos_service)
        
        # Assert
        assert hasattr(service, '_cosmos')
        assert service._cosmos == mock_cosmos_service


@pytest.mark.unit
@pytest.mark.asyncio
class TestAuditLogEmailDefaults:
    """Test audit log email default behavior"""
    
    async def test_audit_log_email_defaults_to_user_id(self, mock_cosmos_service, mock_audit_container):
        """Test audit log uses user_id when email not provided"""
        # Arrange
        mock_cosmos_service.audit_container = mock_audit_container
        service = AuditLoggingService(mock_cosmos_service)
        
        # Act
        audit_id = await service.create_audit_log(
            user_id="user-123",
            user_email=None,
            event_type="test_event",
            endpoint="/test",
            method="GET"
        )
        
        # Assert
        call_args = mock_audit_container.upsert_item.call_args[0][0]
        assert call_args["user_email"] == "user-123"  # Should default to user_id
