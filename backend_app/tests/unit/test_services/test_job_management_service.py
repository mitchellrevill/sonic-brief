"""
Unit tests for JobManagementService

Tests job lifecycle management operations including soft delete, restore, 
permanent delete, and admin job management functionality.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from app.services.jobs.job_management_service import JobManagementService
from app.core.config import DatabaseError


@pytest.fixture
def mock_cosmos_service():
    """Mock CosmosService"""
    mock = Mock()
    mock.get_job_by_id_async = AsyncMock()
    mock.update_job_async = AsyncMock()
    mock.delete_job_async = AsyncMock()
    mock.jobs_container = Mock()
    mock.jobs_container.query_items = Mock()
    return mock


@pytest.fixture
def mock_job_service():
    """Mock JobService"""
    mock = Mock()
    mock.enrich_job_file_urls = Mock(side_effect=lambda job: job)
    return mock


@pytest.fixture
def job_management_service(mock_cosmos_service, mock_job_service):
    """Create JobManagementService instance with mocked dependencies"""
    return JobManagementService(
        cosmos_service=mock_cosmos_service,
        job_service=mock_job_service
    )


@pytest.fixture
def sample_job():
    """Sample job data"""
    return {
        'id': 'job-123',
        'user_id': 'user-456',
        'title': 'Test Job',
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00Z',
        'deleted': False,
        'type': 'job'
    }


@pytest.fixture
def sample_deleted_job():
    """Sample deleted job data"""
    return {
        'id': 'job-789',
        'user_id': 'user-456',
        'title': 'Deleted Job',
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00Z',
        'deleted': True,
        'deleted_at': '2024-01-10T00:00:00Z',
        'deleted_by': 'user-456',
        'type': 'job'
    }


class TestSoftDeleteJob:
    """Tests for soft_delete_job method"""

    @pytest.mark.asyncio
    async def test_soft_delete_job_success_as_owner(self, job_management_service, mock_cosmos_service, sample_job):
        """Test successful soft delete by job owner"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        result = await job_management_service.soft_delete_job('job-123', 'user-456', is_admin=False)

        assert result['status'] == 'success'
        assert result['message'] == 'Job deleted successfully'
        assert result['job_id'] == 'job-123'
        assert 'deleted_at' in result
        
        # Verify update was called with deleted flag
        mock_cosmos_service.update_job_async.assert_called_once()
        call_args = mock_cosmos_service.update_job_async.call_args
        assert call_args[0][0] == 'job-123'
        updated_job = call_args[0][1]
        assert updated_job['deleted'] is True
        assert 'deleted_at' in updated_job
        assert updated_job['deleted_by'] == 'user-456'

    @pytest.mark.asyncio
    async def test_soft_delete_job_success_as_admin(self, job_management_service, mock_cosmos_service, sample_job):
        """Test successful soft delete by admin (not owner)"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        result = await job_management_service.soft_delete_job('job-123', 'admin-user', is_admin=True)

        assert result['status'] == 'success'
        mock_cosmos_service.update_job_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_job_not_found(self, job_management_service, mock_cosmos_service):
        """Test soft delete when job doesn't exist"""
        mock_cosmos_service.get_job_by_id_async.return_value = None

        result = await job_management_service.soft_delete_job('nonexistent', 'user-456')

        assert result['status'] == 'error'
        assert result['message'] == 'Job not found'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_soft_delete_job_access_denied(self, job_management_service, mock_cosmos_service, sample_job):
        """Test soft delete access denied for non-owner"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        result = await job_management_service.soft_delete_job('job-123', 'other-user', is_admin=False)

        assert result['status'] == 'error'
        assert result['message'] == 'Access denied: not job owner'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_soft_delete_job_already_deleted(self, job_management_service, mock_cosmos_service, sample_deleted_job):
        """Test soft delete when job is already deleted"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_deleted_job.copy()

        result = await job_management_service.soft_delete_job('job-789', 'user-456')

        assert result['status'] == 'error'
        assert result['message'] == 'Job is already deleted'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_soft_delete_job_database_error(self, job_management_service, mock_cosmos_service, sample_job):
        """Test soft delete handles database errors"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()
        mock_cosmos_service.update_job_async.side_effect = DatabaseError("Database connection failed")

        result = await job_management_service.soft_delete_job('job-123', 'user-456')

        assert result['status'] == 'error'
        assert result['message'] == 'Database service unavailable'


class TestRestoreJob:
    """Tests for restore_job method"""

    @pytest.mark.asyncio
    async def test_restore_job_success(self, job_management_service, mock_cosmos_service, sample_deleted_job):
        """Test successful job restoration by admin"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_deleted_job.copy()

        result = await job_management_service.restore_job('job-789', 'admin-user', is_admin=True)

        assert result['status'] == 'success'
        assert result['message'] == 'Job restored successfully'
        
        # Verify update was called with restored flag
        mock_cosmos_service.update_job_async.assert_called_once()
        call_args = mock_cosmos_service.update_job_async.call_args
        updated_job = call_args[0][1]
        assert updated_job['deleted'] is False
        assert 'restored_at' in updated_job
        assert updated_job['restored_by'] == 'admin-user'

    @pytest.mark.asyncio
    async def test_restore_job_access_denied_non_admin(self, job_management_service, mock_cosmos_service):
        """Test restore job requires admin privileges"""
        result = await job_management_service.restore_job('job-789', 'user-456', is_admin=False)

        assert result['status'] == 'error'
        assert result['message'] == 'Access denied: admin privileges required'
        mock_cosmos_service.get_job_by_id_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_job_not_found(self, job_management_service, mock_cosmos_service):
        """Test restore when job doesn't exist"""
        mock_cosmos_service.get_job_by_id_async.return_value = None

        result = await job_management_service.restore_job('nonexistent', 'admin-user', is_admin=True)

        assert result['status'] == 'error'
        assert result['message'] == 'Job not found'

    @pytest.mark.asyncio
    async def test_restore_job_not_deleted(self, job_management_service, mock_cosmos_service, sample_job):
        """Test restore when job is not deleted"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        result = await job_management_service.restore_job('job-123', 'admin-user', is_admin=True)

        assert result['status'] == 'error'
        assert result['message'] == 'Job is not deleted'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_job_database_error(self, job_management_service, mock_cosmos_service, sample_deleted_job):
        """Test restore handles database errors"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_deleted_job.copy()
        mock_cosmos_service.update_job_async.side_effect = DatabaseError("Database error")

        result = await job_management_service.restore_job('job-789', 'admin-user', is_admin=True)

        assert result['status'] == 'error'
        assert result['message'] == 'Database service unavailable'


class TestPermanentDeleteJob:
    """Tests for permanent_delete_job method"""

    @pytest.mark.asyncio
    async def test_permanent_delete_job_success(self, job_management_service, mock_cosmos_service, sample_deleted_job):
        """Test successful permanent deletion of soft-deleted job"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_deleted_job.copy()
        mock_cosmos_service.delete_job = AsyncMock()

        result = await job_management_service.permanent_delete_job('job-789', 'admin-user', is_admin=True)

        assert result['status'] == 'success'
        mock_cosmos_service.delete_job.assert_called_once_with('job-789')

    @pytest.mark.asyncio
    async def test_permanent_delete_job_access_denied(self, job_management_service):
        """Test permanent delete requires admin privileges"""
        result = await job_management_service.permanent_delete_job('job-789', 'user-456', is_admin=False)

        assert result['status'] == 'error'
        assert 'admin' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_permanent_delete_job_not_soft_deleted(self, job_management_service, mock_cosmos_service, sample_job):
        """Test permanent delete only works on soft-deleted jobs"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        result = await job_management_service.permanent_delete_job('job-123', 'admin-user', is_admin=True)

        # Should fail because job is not soft-deleted first
        assert result['status'] == 'error'
        mock_cosmos_service.delete_job_async.assert_not_called()


class TestGetMyJobs:
    """Tests for get_my_jobs method"""

    @pytest.mark.asyncio
    async def test_get_my_jobs_success(self, job_management_service, mock_cosmos_service):
        """Test getting user's own jobs"""
        sample_jobs = [
            {'id': 'job-1', 'user_id': 'user-456', 'type': 'job', 'deleted': False},
            {'id': 'job-2', 'user_id': 'user-456', 'type': 'job', 'deleted': False}
        ]
        
        with patch('app.services.jobs.job_management_service.run_sync', return_value=sample_jobs):
            result = await job_management_service.get_my_jobs('user-456')

        assert len(result) == 2
        assert all(job['user_id'] == 'user-456' for job in result)

    @pytest.mark.asyncio
    async def test_get_my_jobs_empty_list(self, job_management_service, mock_cosmos_service):
        """Test getting jobs when user has none"""
        with patch('app.services.jobs.job_management_service.run_sync', return_value=[]):
            result = await job_management_service.get_my_jobs('user-456')

        assert result == []

    @pytest.mark.asyncio
    async def test_get_my_jobs_database_error(self, job_management_service, mock_cosmos_service):
        """Test get_my_jobs handles database errors"""
        with patch('app.services.jobs.job_management_service.run_sync', side_effect=DatabaseError("DB error")):
            with pytest.raises(DatabaseError):
                await job_management_service.get_my_jobs('user-456')


class TestTriggerAnalysisProcessing:
    """Tests for trigger_analysis_processing method"""

    @pytest.mark.asyncio
    async def test_trigger_analysis_processing_success(self, job_management_service, mock_cosmos_service):
        """Test triggering analysis processing for text-only job"""
        job_with_text = {
            'id': 'job-123',
            'user_id': 'user-456',
            'text_content': 'Some text to analyze',
            'status': 'completed',
            'type': 'job'
        }
        mock_cosmos_service.get_job_by_id_async.return_value = job_with_text.copy()

        result = await job_management_service.trigger_analysis_processing('job-123', 'user-456', is_admin=False)

        assert result['status'] == 'success'
        assert result['message'] == 'Analysis processing initiated'
        assert result['job_id'] == 'job-123'
        assert 'processing_started_at' in result
        
        # Verify job was updated with processing status
        mock_cosmos_service.update_job_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_trigger_analysis_processing_job_not_found(self, job_management_service, mock_cosmos_service):
        """Test analysis processing when job doesn't exist"""
        mock_cosmos_service.get_job_by_id_async.return_value = None

        result = await job_management_service.trigger_analysis_processing('nonexistent', 'user-456')

        assert result['status'] == 'error'
        assert result['message'] == 'Job not found'

    @pytest.mark.asyncio
    async def test_trigger_analysis_processing_access_denied(self, job_management_service, mock_cosmos_service):
        """Test analysis processing access control"""
        job = {
            'id': 'job-123',
            'user_id': 'user-456',
            'text_content': 'Some text',
            'type': 'job'
        }
        mock_cosmos_service.get_job_by_id_async.return_value = job

        result = await job_management_service.trigger_analysis_processing('job-123', 'other-user', is_admin=False)

        assert result['status'] == 'error'
        assert result['message'] == 'Access denied'

    @pytest.mark.asyncio
    async def test_trigger_analysis_processing_no_text_content(self, job_management_service, mock_cosmos_service):
        """Test analysis processing when job has no text content"""
        job_without_text = {
            'id': 'job-123',
            'user_id': 'user-456',
            'status': 'uploaded',
            'type': 'job'
        }
        mock_cosmos_service.get_job_by_id_async.return_value = job_without_text

        result = await job_management_service.trigger_analysis_processing('job-123', 'user-456')

        assert result['status'] == 'error'
        assert 'No text content' in result['message']

    @pytest.mark.asyncio
    async def test_trigger_analysis_processing_admin_bypass(self, job_management_service, mock_cosmos_service):
        """Test admin can trigger analysis for any job"""
        job = {
            'id': 'job-123',
            'user_id': 'user-456',
            'text_content': 'Some text',
            'type': 'job'
        }
        mock_cosmos_service.get_job_by_id_async.return_value = job

        result = await job_management_service.trigger_analysis_processing('job-123', 'admin-user', is_admin=True)

        assert result['status'] == 'success'


class TestGetAllJobs:
    """Tests for get_all_jobs method (admin)"""

    @pytest.mark.asyncio
    async def test_get_all_jobs_success(self, job_management_service, mock_cosmos_service, mock_job_service):
        """Test getting all jobs with pagination"""
        sample_jobs = [
            {'id': f'job-{i}', 'user_id': f'user-{i}', 'type': 'job'} 
            for i in range(5)
        ]
        
        with patch('app.services.jobs.job_management_service.run_sync') as mock_run_sync:
            mock_run_sync.side_effect = [[10], sample_jobs]  # First call returns count, second returns jobs

            result = await job_management_service.get_all_jobs(limit=5, offset=0, include_deleted=False)

        assert result['total_count'] == 10
        assert len(result['jobs']) == 5

    @pytest.mark.asyncio
    async def test_get_all_jobs_pagination(self, job_management_service, mock_cosmos_service):
        """Test pagination parameters"""
        with patch('app.services.jobs.job_management_service.run_sync') as mock_run_sync:
            mock_run_sync.side_effect = [[100], []]

            result = await job_management_service.get_all_jobs(limit=20, offset=40)

        assert 'jobs' in result
        assert 'total_count' in result

    @pytest.mark.asyncio
    async def test_get_all_jobs_include_deleted(self, job_management_service, mock_cosmos_service):
        """Test including deleted jobs in results"""
        with patch('app.services.jobs.job_management_service.run_sync') as mock_run_sync:
            mock_run_sync.side_effect = [[50], []]

            result = await job_management_service.get_all_jobs(include_deleted=True)

        assert 'jobs' in result
        assert 'total_count' in result

    @pytest.mark.asyncio
    async def test_get_all_jobs_database_error(self, job_management_service, mock_cosmos_service):
        """Test get_all_jobs handles database errors"""
        with patch('app.services.jobs.job_management_service.run_sync', side_effect=DatabaseError("DB error")):
            result = await job_management_service.get_all_jobs()

        assert result['jobs'] == []
        assert result['total_count'] == 0
        assert 'error' in result


class TestGetDeletedJobs:
    """Tests for get_deleted_jobs method (admin)"""

    @pytest.mark.asyncio
    async def test_get_deleted_jobs_success(self, job_management_service, mock_cosmos_service, mock_job_service):
        """Test getting deleted jobs"""
        deleted_jobs = [
            {'id': 'job-1', 'deleted': True, 'type': 'job'},
            {'id': 'job-2', 'deleted': True, 'type': 'job'}
        ]
        
        with patch('app.services.jobs.job_management_service.run_sync') as mock_run_sync:
            mock_run_sync.side_effect = [[2], deleted_jobs]

            result = await job_management_service.get_deleted_jobs('admin-user', limit=10, offset=0, is_admin=True)

        assert result['status'] == 'success'
        assert result['total_count'] == 2
        assert len(result['deleted_jobs']) == 2

    @pytest.mark.asyncio
    async def test_get_deleted_jobs_empty(self, job_management_service, mock_cosmos_service):
        """Test when no deleted jobs exist"""
        with patch('app.services.jobs.job_management_service.run_sync') as mock_run_sync:
            mock_run_sync.side_effect = [[0], []]

            result = await job_management_service.get_deleted_jobs('admin-user', is_admin=True)

        assert result['status'] == 'success'
        assert result['total_count'] == 0
        assert result['deleted_jobs'] == []

    @pytest.mark.asyncio
    async def test_get_deleted_jobs_database_error(self, job_management_service, mock_cosmos_service):
        """Test get_deleted_jobs handles database errors"""
        with patch('app.services.jobs.job_management_service.run_sync', side_effect=DatabaseError("DB error")):
            result = await job_management_service.get_deleted_jobs('admin-user', is_admin=True)

        assert result['status'] == 'error'
        assert result['deleted_jobs'] == []
        assert result['total_count'] == 0
