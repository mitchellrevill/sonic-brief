"""
Unit tests for AnalyticsService (Phase 3 - Analytics & Monitoring)

Tests cover:
- Event tracking (track_event, track_job_event)
- User analytics queries (get_user_analytics, get_user_minutes_records)
- System analytics (get_system_analytics)
- Container availability handling
- Error handling and fallback mechanisms
- Audio duration calculations (seconds to minutes)

Coverage target: 90%+ on app/services/analytics/analytics_service.py
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from app.services.analytics.analytics_service import AnalyticsService
from app.core.dependencies import CosmosService


# ============================================================================
# Test Class: Event Tracking
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
class TestEventTracking:
    """Test event tracking functionality"""
    
    async def test_track_event_success(self, mock_cosmos_service, mock_events_container):
        """Test successful event tracking"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        with patch('app.services.analytics.analytics_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = "2025-10-08T12:00:00+00:00"
            with patch('app.services.analytics.analytics_service.uuid') as mock_uuid:
                mock_uuid.uuid4.return_value = Mock(hex="test-event-id-123")
                event_id = await service.track_event(
                    event_type="user_login",
                    user_id="user-123",
                    metadata={"ip": "192.168.1.1"}
                )
        
        # Assert
        assert event_id != ""
        mock_events_container.create_item.assert_called_once()
        call_args = mock_events_container.create_item.call_args[1]
        event = call_args["body"]
        assert event["event_type"] == "user_login"
        assert event["user_id"] == "user-123"
        assert event["metadata"] == {"ip": "192.168.1.1"}
        assert event["partition_key"] == "user-123"
    
    async def test_track_event_with_job_id(self, mock_cosmos_service, mock_events_container):
        """Test event tracking with job_id"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_event(
            event_type="job_created",
            user_id="user-123",
            job_id="job-456"
        )
        
        # Assert
        assert event_id != ""
        event = mock_events_container.create_item.call_args[1]["body"]
        assert event["job_id"] == "job-456"
    
    async def test_track_event_missing_event_type(self, mock_cosmos_service, mock_events_container):
        """Test track_event returns empty string for missing event_type"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_event(
            event_type="",
            user_id="user-123"
        )
        
        # Assert
        assert event_id == ""
        mock_events_container.create_item.assert_not_called()
    
    async def test_track_event_missing_user_id(self, mock_cosmos_service, mock_events_container):
        """Test track_event returns empty string for missing user_id"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_event(
            event_type="test_event",
            user_id=""
        )
        
        # Assert
        assert event_id == ""
        mock_events_container.create_item.assert_not_called()
    
    async def test_track_event_container_unavailable(self, mock_cosmos_service):
        """Test track_event handles missing events container"""
        # Arrange
        mock_cosmos_service.events_container = None
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_event(
            event_type="test_event",
            user_id="user-123"
        )
        
        # Assert
        assert event_id == ""
    
    async def test_track_event_cosmos_error(self, mock_cosmos_service, mock_events_container):
        """Test track_event handles Cosmos errors"""
        # Arrange
        error = CosmosHttpResponseError(status_code=500, message="Server error")
        mock_events_container.create_item = Mock(side_effect=error)  # Use Mock, not AsyncMock (run_sync handles it)
        mock_cosmos_service.events_container = mock_events_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_event(
            event_type="test_event",
            user_id="user-123"
        )
        
        # Assert
        assert event_id == ""
    
    async def test_track_event_unexpected_error(self, mock_cosmos_service, mock_events_container):
        """Test track_event handles unexpected errors"""
        # Arrange
        mock_events_container.create_item = Mock(side_effect=Exception("Unexpected"))  # Use Mock, not AsyncMock
        mock_cosmos_service.events_container = mock_events_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_event(
            event_type="test_event",
            user_id="user-123"
        )
        
        # Assert
        assert event_id == ""


# ============================================================================
# Test Class: Job Event Tracking
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
@pytest.mark.asyncio
class TestJobEventTracking:
    """Test job-specific event tracking with legacy analytics"""
    
    async def test_track_job_event_basic(self, mock_cosmos_service, mock_events_container):
        """Test basic job event tracking"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        mock_cosmos_service.analytics_container = None  # No analytics container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_job_event(
            job_id="job-123",
            user_id="user-456",
            event_type="job_created"
        )
        
        # Assert
        assert event_id != ""
        mock_events_container.create_item.assert_called_once()
    
    async def test_track_job_event_with_audio_metadata(self, mock_cosmos_service, mock_events_container, mock_analytics_container):
        """Test job event creates analytics document with audio metadata"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        metadata = {
            "audio_duration_seconds": 300,
            "file_name": "test.mp3"
        }
        
        # Act
        with patch('app.services.analytics.analytics_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1696780800.0
            mock_datetime.now.return_value.isoformat.return_value = "2023-10-08T12:00:00+00:00"
            event_id = await service.track_job_event(
                job_id="job-123",
                user_id="user-456",
                event_type="job_created",
                metadata=metadata
            )
        
        # Assert
        assert event_id != ""
        assert mock_events_container.create_item.call_count == 1
        assert mock_analytics_container.create_item.call_count == 1
        
        # Verify analytics document
        analytics_doc = mock_analytics_container.create_item.call_args[1]["body"]
        assert analytics_doc["type"] == "transcription_analytics"
        assert analytics_doc["job_id"] == "job-123"
        assert analytics_doc["user_id"] == "user-456"
        assert analytics_doc["audio_duration_seconds"] == 300.0
        assert analytics_doc["audio_duration_minutes"] == 5.0  # 300 / 60
    
    async def test_track_job_event_audio_minutes_calculation(self, mock_cosmos_service, mock_events_container, mock_analytics_container):
        """Test audio duration conversion from seconds to minutes"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        await service.track_job_event(
            job_id="job-123",
            user_id="user-456",
            event_type="job_created",
            metadata={"audio_duration_seconds": 150}
        )
        
        # Assert
        analytics_doc = mock_analytics_container.create_item.call_args[1]["body"]
        assert analytics_doc["audio_duration_minutes"] == 2.5  # 150 / 60
    
    async def test_track_job_event_audio_minutes_provided(self, mock_cosmos_service, mock_events_container, mock_analytics_container):
        """Test audio duration when minutes already provided"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        await service.track_job_event(
            job_id="job-123",
            user_id="user-456",
            event_type="job_created",
            metadata={"audio_duration_minutes": 10.5}
        )
        
        # Assert
        analytics_doc = mock_analytics_container.create_item.call_args[1]["body"]
        assert analytics_doc["audio_duration_minutes"] == 10.5
    
    async def test_track_job_event_prompt_metadata(self, mock_cosmos_service, mock_events_container, mock_analytics_container):
        """Test job event with prompt category/subcategory metadata"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        metadata = {
            "prompt_category_id": "cat-123",
            "prompt_subcategory_id": "subcat-456"
        }
        
        # Act
        await service.track_job_event(
            job_id="job-123",
            user_id="user-456",
            event_type="job_created",
            metadata=metadata
        )
        
        # Assert
        analytics_doc = mock_analytics_container.create_item.call_args[1]["body"]
        assert analytics_doc["prompt_category_id"] == "cat-123"
        assert analytics_doc["prompt_subcategory_id"] == "subcat-456"
    
    async def test_track_job_event_analytics_cosmos_error(self, mock_cosmos_service, mock_events_container, mock_analytics_container):
        """Test job event continues when analytics container fails"""
        # Arrange
        mock_cosmos_service.events_container = mock_events_container
        mock_analytics_container.create_item = AsyncMock(side_effect=CosmosHttpResponseError(status_code=500, message="Error"))
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        event_id = await service.track_job_event(
            job_id="job-123",
            user_id="user-456",
            event_type="job_created",
            metadata={"audio_duration_seconds": 100}
        )
        
        # Assert - event should still be created
        assert event_id != ""
        mock_events_container.create_item.assert_called_once()


# ============================================================================
# Test Class: User Analytics
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestUserAnalytics:
    """Test user analytics queries"""
    
    async def test_get_user_analytics_from_analytics_container(self, mock_cosmos_service, mock_analytics_container, analytics_factory):
        """Test user analytics from analytics container"""
        # Arrange
        analytics_docs = [
            analytics_factory(user_id="user-123", audio_duration_minutes=5.0),
            analytics_factory(user_id="user-123", audio_duration_minutes=10.0),
        ]
        mock_analytics_container.query_items = Mock(return_value=analytics_docs)
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_analytics(user_id="user-123", days=30)
        
        # Assert
        assert result["user_id"] == "user-123"
        assert result["period_days"] == 30
        assert result["analytics"]["transcription_stats"]["total_minutes"] == 15.0
        assert result["analytics"]["transcription_stats"]["total_jobs"] == 2
        assert result["analytics"]["transcription_stats"]["average_job_duration"] == 7.5
    
    async def test_get_user_analytics_audio_seconds_conversion(self, mock_cosmos_service, mock_analytics_container):
        """Test analytics converts seconds to minutes"""
        # Arrange
        analytics_docs = [
            {"audio_duration_seconds": 300},  # 5 minutes
            {"audio_duration_seconds": 600},  # 10 minutes
        ]
        mock_analytics_container.query_items = Mock(return_value=analytics_docs)
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_analytics(user_id="user-123", days=30)
        
        # Assert
        assert result["analytics"]["transcription_stats"]["total_minutes"] == 15.0
    
    async def test_get_user_analytics_fallback_to_jobs(self, mock_cosmos_service, mock_analytics_container):
        """Test analytics falls back to jobs container when no analytics"""
        # Arrange
        mock_analytics_container.query_items = Mock(return_value=[])
        mock_cosmos_service.analytics_container = mock_analytics_container
        
        mock_jobs_container = Mock()
        jobs_docs = [
            {"audio_duration_minutes": 3.0},
            {"audio_duration_seconds": 240},  # 4 minutes
        ]
        mock_jobs_container.query_items = Mock(return_value=jobs_docs)
        mock_cosmos_service.jobs_container = mock_jobs_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_analytics(user_id="user-123", days=30)
        
        # Assert
        assert result["analytics"]["transcription_stats"]["total_minutes"] == 7.0
        assert result["analytics"]["transcription_stats"]["total_jobs"] == 2
    
    async def test_get_user_analytics_empty_results(self, mock_cosmos_service, mock_analytics_container):
        """Test user analytics with no data"""
        # Arrange
        mock_analytics_container.query_items = Mock(return_value=[])
        mock_cosmos_service.analytics_container = mock_analytics_container
        mock_cosmos_service.jobs_container = None
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_analytics(user_id="user-123", days=30)
        
        # Assert
        assert result["analytics"]["transcription_stats"]["total_minutes"] == 0.0
        assert result["analytics"]["transcription_stats"]["total_jobs"] == 0
        assert result["analytics"]["transcription_stats"]["average_job_duration"] == 0.0
    
    async def test_get_user_analytics_cosmos_error(self, mock_cosmos_service, mock_analytics_container):
        """Test user analytics handles Cosmos errors gracefully"""
        # Arrange
        mock_analytics_container.query_items = Mock(side_effect=CosmosHttpResponseError(status_code=500, message="Error"))
        mock_cosmos_service.analytics_container = mock_analytics_container
        mock_cosmos_service.jobs_container = None
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_analytics(user_id="user-123", days=30)
        
        # Assert - should return empty results, not raise
        assert result["analytics"]["transcription_stats"]["total_minutes"] == 0.0
        assert result["analytics"]["transcription_stats"]["total_jobs"] == 0
    
    async def test_get_user_minutes_records_success(self, mock_cosmos_service, mock_analytics_container, analytics_factory):
        """Test get_user_minutes_records returns detailed records"""
        # Arrange
        analytics_docs = [
            analytics_factory(
                job_id="job-1",
                user_id="user-123",
                audio_duration_minutes=5.0,
                file_name="file1.mp3",
                prompt_category_id="cat-1"
            ),
            analytics_factory(
                job_id="job-2",
                user_id="user-123",
                audio_duration_seconds=300,
                file_name="file2.mp3"
            ),
        ]
        mock_analytics_container.query_items = Mock(return_value=analytics_docs)
        mock_cosmos_service.analytics_container = mock_analytics_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_minutes_records(user_id="user-123", days=30)
        
        # Assert
        assert result["user_id"] == "user-123"
        assert result["total_minutes"] == 10.0
        assert result["total_records"] == 2
        assert len(result["records"]) == 2
        assert result["records"][0]["job_id"] in ["job-1", "job-2"]
    
    async def test_get_user_minutes_records_no_fallback(self, mock_cosmos_service, mock_analytics_container):
        """Test get_user_minutes_records does NOT fall back to jobs container"""
        # Arrange
        mock_analytics_container.query_items = Mock(return_value=[])
        mock_cosmos_service.analytics_container = mock_analytics_container
        
        mock_jobs_container = Mock()
        mock_cosmos_service.jobs_container = mock_jobs_container
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_user_minutes_records(user_id="user-123", days=30)
        
        # Assert - should have empty records, NOT query jobs
        assert result["total_records"] == 0
        mock_jobs_container.query_items.assert_not_called()


# ============================================================================
# Test Class: System Analytics
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestSystemAnalytics:
    """Test system-wide analytics"""
    
    async def test_get_system_analytics_success(self, mock_cosmos_service, mock_analytics_container, analytics_factory):
        """Test system analytics aggregates all users"""
        # Arrange
        analytics_docs = [
            analytics_factory(user_id="user-1", audio_duration_minutes=5.0),
            analytics_factory(user_id="user-2", audio_duration_minutes=10.0),
            analytics_factory(user_id="user-3", audio_duration_minutes=3.0),
        ]
        mock_analytics_container.query_items = Mock(return_value=analytics_docs)
        mock_cosmos_service.analytics_container = mock_analytics_container
        
        # Mock sessions_container to return empty list (so active users calculation completes)
        mock_sessions_container = Mock()
        mock_sessions_container.query_items = Mock(return_value=[])
        mock_cosmos_service.sessions_container = mock_sessions_container
        
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_system_analytics(days=30)
        
        # Assert
        assert result["period_days"] == 30
        assert result["total_minutes"] == 18.0
        assert result["total_jobs"] == 3
        assert result["analytics"]["total_minutes"] == 18.0
        assert len(result["analytics"]["records"]) == 3
    
    async def test_get_system_analytics_seconds_conversion(self, mock_cosmos_service, mock_analytics_container):
        """Test system analytics converts seconds to minutes"""
        # Arrange
        analytics_docs = [
            {"audio_duration_seconds": 600, "timestamp": "2025-10-08T12:00:00+00:00"},  # 10 minutes
            {"audio_duration_seconds": 300, "timestamp": "2025-10-08T13:00:00+00:00"},  # 5 minutes
        ]
        mock_analytics_container.query_items = Mock(return_value=analytics_docs)
        mock_cosmos_service.analytics_container = mock_analytics_container
        
        # Mock sessions_container to return empty list
        mock_sessions_container = Mock()
        mock_sessions_container.query_items = Mock(return_value=[])
        mock_cosmos_service.sessions_container = mock_sessions_container
        
        service = AnalyticsService(mock_cosmos_service)
        
        # Act
        result = await service.get_system_analytics(days=30)
        
        # Assert
        assert result["total_minutes"] == 15.0
        assert result["analytics"]["total_minutes"] == 15.0


# ============================================================================
# Test Class: Container Availability
# ============================================================================

@pytest.mark.unit
class TestContainerAvailability:
    """Test container availability handling"""
    
    def test_service_initialization_with_containers(self, mock_cosmos_service, mock_analytics_container, mock_events_container):
        """Test service initializes availability flags correctly"""
        # Arrange
        mock_cosmos_service.analytics_container = mock_analytics_container
        mock_cosmos_service.events_container = mock_events_container
        
        # Act
        service = AnalyticsService(mock_cosmos_service)
        
        # Assert
        assert service._analytics_container_available is True
        assert service._events_container_available is True
    
    def test_service_initialization_without_containers(self, mock_cosmos_service):
        """Test service handles missing containers"""
        # Arrange - explicitly set containers to None
        mock_cosmos_service.analytics_container = None
        mock_cosmos_service.events_container = None
        
        # Act
        service = AnalyticsService(mock_cosmos_service)
        
        # Assert
        assert service._analytics_container_available is False
        assert service._events_container_available is False
    
    def test_close_method(self, mock_cosmos_service):
        """Test graceful shutdown"""
        # Arrange
        service = AnalyticsService(mock_cosmos_service)
        
        # Act & Assert - should not raise
        service.close()
