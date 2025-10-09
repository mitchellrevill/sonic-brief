"""
Unit tests for SessionTrackingService (Phase 3 - Monitoring Services)

Tests cover:
- Session creation and updates
- Heartbeat tracking
- Session expiration logic
- One-session-per-user pattern
- Container unavailability handling

Coverage target: 90%+ on app/services/monitoring/session_tracking_service.py
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone, timedelta
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from app.services.monitoring.session_tracking_service import SessionTrackingService
from app.core.dependencies import CosmosService


# ============================================================================
# Test Class: Session Creation
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
class TestSessionCreation:
    """Test session creation and management"""
    
    async def test_get_or_create_session_new_session(self, mock_cosmos_service, mock_sessions_container, session_factory):
        """Test creating a new session"""
        # Arrange
        mock_sessions_container.read_item = Mock(side_effect=CosmosResourceNotFoundError(status_code=404, message="Not found"))
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        session_id = await service.get_or_create_session(
            user_id="user-123",
            user_email="test@example.com",
            request_path="/api/jobs",
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1"
        )
        
        # Assert
        assert session_id == "user-123"  # Session ID = User ID
        mock_sessions_container.upsert_item.assert_called_once()
        call_args = mock_sessions_container.upsert_item.call_args[0][0]
        assert call_args["id"] == "user-123"
        assert call_args["user_id"] == "user-123"
        assert call_args["status"] == "active"
        assert call_args["request_count"] == 1
    
    async def test_get_or_create_session_update_existing(self, mock_cosmos_service, mock_sessions_container, session_factory):
        """Test updating an existing session"""
        # Arrange
        existing_session = session_factory(user_id="user-123")
        existing_session["request_count"] = 5  # Manually add request_count field
        existing_session["endpoints_accessed"] = ["/api/jobs"]
        mock_sessions_container.read_item = Mock(return_value=existing_session)
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        session_id = await service.get_or_create_session(
            user_id="user-123",
            user_email="test@example.com",
            request_path="/api/prompts",
            ip_address="192.168.1.1"
        )
        
        # Assert
        assert session_id == "user-123"
        call_args = mock_sessions_container.upsert_item.call_args[0][0]
        assert call_args["request_count"] == 6  # Incremented from 5
    
    async def test_get_or_create_session_no_container(self, mock_cosmos_service):
        """Test session creation when container unavailable"""
        # Arrange
        mock_cosmos_service.sessions_container = None
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        session_id = await service.get_or_create_session(
            user_id="user-123",
            user_email="test@example.com"
        )
        
        # Assert
        assert session_id is None
    
    async def test_get_or_create_session_custom_timeout(self, mock_cosmos_service, mock_sessions_container):
        """Test session with custom timeout"""
        # Arrange
        mock_sessions_container.read_item = Mock(side_effect=CosmosResourceNotFoundError(status_code=404, message="Not found"))
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service, session_timeout_minutes=60)
        
        # Act
        await service.get_or_create_session(user_id="user-123", user_email="test@example.com")
        
        # Assert
        assert service.session_timeout_minutes == 60
    
    async def test_get_or_create_session_tracks_endpoints(self, mock_cosmos_service, mock_sessions_container):
        """Test session tracks accessed endpoints"""
        # Arrange
        mock_sessions_container.read_item = Mock(side_effect=CosmosResourceNotFoundError(status_code=404, message="Not found"))
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        await service.get_or_create_session(
            user_id="user-123",
            user_email="test@example.com",
            request_path="/api/jobs/123"
        )
        
        # Assert
        call_args = mock_sessions_container.upsert_item.call_args[0][0]
        assert "/api/jobs/123" in call_args["endpoints_accessed"]
    
    async def test_get_or_create_session_handles_cosmos_error(self, mock_cosmos_service, mock_sessions_container):
        """Test session creation handles Cosmos errors"""
        # Arrange
        mock_sessions_container.read_item = Mock(side_effect=CosmosResourceNotFoundError(status_code=404, message="Not found"))
        mock_sessions_container.upsert_item = Mock(side_effect=CosmosHttpResponseError(status_code=500, message="Error"))
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        session_id = await service.get_or_create_session(
            user_id="user-123",
            user_email="test@example.com"
        )
        
        # Assert - should return None on error
        assert session_id is None


# ============================================================================
# Test Class: Session Deactivation
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionDeactivation:
    """Test session deactivation/logout"""
    
    async def test_deactivate_session_success(self, mock_cosmos_service, mock_sessions_container, session_factory):
        """Test successful session deactivation"""
        # Arrange
        existing_session = session_factory(user_id="user-123", status="active")
        mock_sessions_container.read_item = Mock(return_value=existing_session)
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.deactivate_session(session_id="user-123")
        
        # Assert
        assert result is True
        call_args = mock_sessions_container.upsert_item.call_args[0][0]
        assert call_args["status"] == "closed"
        assert "ended_at" in call_args
        assert call_args["end_reason"] == "user_logout"
    
    async def test_deactivate_session_no_container(self, mock_cosmos_service):
        """Test deactivation when container unavailable"""
        # Arrange
        mock_cosmos_service.sessions_container = None
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.deactivate_session(session_id="user-123")
        
        # Assert
        assert result is False
    
    async def test_deactivate_session_not_found(self, mock_cosmos_service, mock_sessions_container):
        """Test deactivating non-existent session"""
        # Arrange
        mock_sessions_container.read_item = Mock(side_effect=CosmosResourceNotFoundError(status_code=404, message="Not found"))
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.deactivate_session(session_id="user-123")
        
        # Assert
        assert result is False


# ============================================================================
# Test Class: Session Info Retrieval
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionInfo:
    """Test session information retrieval"""
    
    async def test_get_session_info_success(self, mock_cosmos_service, mock_sessions_container, session_factory):
        """Test getting session info"""
        # Arrange
        existing_session = session_factory(user_id="user-123")
        mock_sessions_container.read_item = Mock(return_value=existing_session)
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.get_session_info(user_id="user-123")
        
        # Assert
        assert result is not None
        assert result["user_id"] == "user-123"
    
    async def test_is_session_active_yes(self, mock_cosmos_service, mock_sessions_container):
        """Test checking if session is active (yes)"""
        # Arrange
        from datetime import timedelta
        future_time = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        session = {
            "id": "user-123",
            "user_id": "user-123",
            "status": "active",
            "expires_at": future_time
        }
        mock_sessions_container.read_item = Mock(return_value=session)
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.is_session_active(user_id="user-123")
        
        # Assert
        assert result is True
    
    async def test_is_session_active_expired(self, mock_cosmos_service, mock_sessions_container):
        """Test checking if session is active (expired)"""
        # Arrange
        from datetime import timedelta
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        session = {
            "id": "user-123",
            "user_id": "user-123",
            "status": "active",
            "expires_at": past_time
        }
        mock_sessions_container.read_item = Mock(return_value=session)
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.is_session_active(user_id="user-123")
        
        # Assert
        assert result is False
    
    async def test_is_session_active_not_found(self, mock_cosmos_service, mock_sessions_container):
        """Test checking if session active when not found"""
        # Arrange
        mock_sessions_container.read_item = Mock(side_effect=CosmosResourceNotFoundError(status_code=404, message="Not found"))
        mock_cosmos_service.sessions_container = mock_sessions_container
        service = SessionTrackingService(mock_cosmos_service)
        
        # Act
        result = await service.is_session_active(user_id="user-123")
        
        # Assert
        assert result is False
