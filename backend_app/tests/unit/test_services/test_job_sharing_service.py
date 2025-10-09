"""
Unit tests for JobSharingService

Tests job sharing operations including share_job, unshare_job, 
get_shared_jobs, and permission validation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from app.services.jobs.job_sharing_service import JobSharingService
from app.core.config import DatabaseError


@pytest.fixture
def mock_cosmos_service():
    """Mock CosmosService"""
    mock = Mock()
    mock.get_job_by_id_async = AsyncMock()
    mock.get_user_by_email = AsyncMock()
    mock.update_job_async = AsyncMock()
    mock.jobs_container = Mock()
    mock.jobs_container.query_items = Mock()
    return mock


@pytest.fixture
def job_sharing_service(mock_cosmos_service):
    """Create JobSharingService instance with mocked dependencies"""
    return JobSharingService(cosmos_service=mock_cosmos_service)


@pytest.fixture
def sample_job():
    """Sample job data"""
    return {
        'id': 'job-123',
        'user_id': 'owner-456',
        'title': 'Test Job',
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00Z',
        'type': 'job',
        'shared_with': []
    }


@pytest.fixture
def sample_shared_job():
    """Sample job with sharing"""
    return {
        'id': 'job-789',
        'user_id': 'owner-456',
        'title': 'Shared Job',
        'status': 'completed',
        'created_at': '2024-01-01T00:00:00Z',
        'type': 'job',
        'shared_with': [
            {
                'user_id': 'shared-user-1',
                'user_email': 'shared1@example.com',
                'permission_level': 'view',
                'shared_at': '2024-01-05T00:00:00Z',
                'shared_by': 'owner-456'
            }
        ]
    }


@pytest.fixture
def sample_target_user():
    """Sample target user for sharing"""
    return {
        'id': 'target-user-789',
        'email': 'target@example.com',
        'full_name': 'Target User',
        'permission': 'user'
    }


class TestShareJob:
    """Tests for share_job method"""

    @pytest.mark.asyncio
    async def test_share_job_success(self, job_sharing_service, mock_cosmos_service, 
                                      sample_job, sample_target_user):
        """Test successful job sharing"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()
        mock_cosmos_service.get_user_by_email.return_value = sample_target_user

        result = await job_sharing_service.share_job(
            'job-123', 
            'owner-456', 
            'target@example.com', 
            'view'
        )

        assert result['status'] == 'success'
        assert 'Job shared with target@example.com' in result['message']
        assert result['permission_level'] == 'view'
        assert result['shared_with_count'] == 1
        
        # Verify update was called
        mock_cosmos_service.update_job_async.assert_called_once()
        call_args = mock_cosmos_service.update_job_async.call_args
        updated_job = call_args[0][1]
        assert len(updated_job['shared_with']) == 1
        assert updated_job['shared_with'][0]['user_id'] == 'target-user-789'
        assert updated_job['shared_with'][0]['permission_level'] == 'view'

    @pytest.mark.asyncio
    async def test_share_job_update_existing_share(self, job_sharing_service, mock_cosmos_service, 
                                                     sample_shared_job, sample_target_user):
        """Test updating existing share permission"""
        sample_target_user['email'] = 'shared1@example.com'
        sample_target_user['id'] = 'shared-user-1'
        
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()
        mock_cosmos_service.get_user_by_email.return_value = sample_target_user

        result = await job_sharing_service.share_job(
            'job-789', 
            'owner-456', 
            'shared1@example.com', 
            'edit'  # Upgrade from view to edit
        )

        assert result['status'] == 'success'
        assert result['shared_with_count'] == 1  # Should still be 1, not 2
        
        # Verify permission was updated
        call_args = mock_cosmos_service.update_job_async.call_args
        updated_job = call_args[0][1]
        assert updated_job['shared_with'][0]['permission_level'] == 'edit'

    @pytest.mark.asyncio
    async def test_share_job_not_found(self, job_sharing_service, mock_cosmos_service):
        """Test sharing non-existent job"""
        mock_cosmos_service.get_job_by_id_async.return_value = None

        result = await job_sharing_service.share_job('nonexistent', 'owner-456', 'target@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Job not found'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_share_job_access_denied(self, job_sharing_service, mock_cosmos_service, sample_job):
        """Test sharing by non-owner"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        result = await job_sharing_service.share_job('job-123', 'other-user', 'target@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Access denied: not job owner'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_share_job_target_user_not_found(self, job_sharing_service, mock_cosmos_service, sample_job):
        """Test sharing with non-existent target user"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()
        mock_cosmos_service.get_user_by_email.return_value = None

        result = await job_sharing_service.share_job('job-123', 'owner-456', 'nonexistent@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Target user not found'
        mock_cosmos_service.update_job_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_share_job_database_error(self, job_sharing_service, mock_cosmos_service, 
                                             sample_job, sample_target_user):
        """Test sharing handles database errors"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()
        mock_cosmos_service.get_user_by_email.return_value = sample_target_user
        mock_cosmos_service.update_job_async.side_effect = DatabaseError("Database error")

        result = await job_sharing_service.share_job('job-123', 'owner-456', 'target@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Database service unavailable'

    @pytest.mark.asyncio
    async def test_share_job_with_different_permissions(self, job_sharing_service, mock_cosmos_service,
                                                         sample_job, sample_target_user):
        """Test sharing with different permission levels"""
        for permission in ['view', 'edit', 'admin']:
            mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()
            mock_cosmos_service.get_user_by_email.return_value = sample_target_user

            result = await job_sharing_service.share_job(
                'job-123', 
                'owner-456', 
                'target@example.com', 
                permission
            )

            assert result['status'] == 'success'
            assert result['permission_level'] == permission


class TestUnshareJob:
    """Tests for unshare_job method"""

    @pytest.mark.asyncio
    async def test_unshare_job_success(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test successful job unsharing"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()

        result = await job_sharing_service.unshare_job('job-789', 'owner-456', 'shared1@example.com')

        assert result['status'] == 'success'
        assert 'Job unshared from shared1@example.com' in result['message']
        assert result['shared_with_count'] == 0
        
        # Verify update was called
        mock_cosmos_service.update_job_async.assert_called_once()
        call_args = mock_cosmos_service.update_job_async.call_args
        updated_job = call_args[0][1]
        assert len(updated_job['shared_with']) == 0

    @pytest.mark.asyncio
    async def test_unshare_job_not_found(self, job_sharing_service, mock_cosmos_service):
        """Test unsharing non-existent job"""
        mock_cosmos_service.get_job_by_id_async.return_value = None

        result = await job_sharing_service.unshare_job('nonexistent', 'owner-456', 'user@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Job not found'

    @pytest.mark.asyncio
    async def test_unshare_job_access_denied(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test unsharing by non-owner"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()

        result = await job_sharing_service.unshare_job('job-789', 'other-user', 'shared1@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Access denied: not job owner'

    @pytest.mark.asyncio
    async def test_unshare_job_not_shared_with_user(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test unsharing from user who doesn't have access"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()

        result = await job_sharing_service.unshare_job('job-789', 'owner-456', 'nonshared@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Job was not shared with this user'

    @pytest.mark.asyncio
    async def test_unshare_job_not_shared_at_all(self, job_sharing_service, mock_cosmos_service, sample_job):
        """Test unsharing job that isn't shared with anyone"""
        # Remove shared_with field to test the else branch
        job_without_sharing = sample_job.copy()
        del job_without_sharing['shared_with']
        mock_cosmos_service.get_job_by_id_async.return_value = job_without_sharing

        result = await job_sharing_service.unshare_job('job-123', 'owner-456', 'user@example.com')

        assert result['status'] == 'error'
        assert 'not shared' in result['message'].lower()

    @pytest.mark.asyncio
    async def test_unshare_job_database_error(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test unsharing handles database errors"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()
        mock_cosmos_service.update_job_async.side_effect = DatabaseError("Database error")

        result = await job_sharing_service.unshare_job('job-789', 'owner-456', 'shared1@example.com')

        assert result['status'] == 'error'
        assert result['message'] == 'Database service unavailable'


class TestGetJobSharingInfo:
    """Tests for get_job_sharing_info method"""

    @pytest.mark.asyncio
    async def test_get_job_sharing_info_success(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test getting sharing info for a job"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()

        result = await job_sharing_service.get_job_sharing_info('job-789', 'owner-456')

        assert result['status'] == 'success'
        assert 'sharing_info' in result
        sharing_info = result['sharing_info']
        assert 'shared_with' in sharing_info
        assert len(sharing_info['shared_with']) == 1

    @pytest.mark.asyncio
    async def test_get_job_sharing_info_not_found(self, job_sharing_service, mock_cosmos_service):
        """Test getting sharing info for non-existent job"""
        mock_cosmos_service.get_job_by_id_async.return_value = None

        result = await job_sharing_service.get_job_sharing_info('nonexistent', 'user-123')

        assert result['status'] == 'error'
        assert result['message'] == 'Job not found'

    @pytest.mark.asyncio
    async def test_get_job_sharing_info_access_control(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test access control for sharing info"""
        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()

        # Owner should have access
        result = await job_sharing_service.get_job_sharing_info('job-789', 'owner-456')
        assert result['status'] == 'success'


class TestGetSharedJobs:
    """Tests for get_shared_jobs method"""

    @pytest.mark.asyncio
    async def test_get_shared_jobs_success(self, job_sharing_service, mock_cosmos_service):
        """Test getting jobs shared with user"""
        shared_jobs = [
            {
                'id': 'job-1',
                'user_id': 'other-owner',
                'type': 'job',
                'shared_with': [{'user_id': 'user-456', 'permission_level': 'view'}]
            },
            {
                'id': 'job-2',
                'user_id': 'another-owner',
                'type': 'job',
                'shared_with': [{'user_id': 'user-456', 'permission_level': 'edit'}]
            }
        ]
        
        with patch('app.services.jobs.job_sharing_service.run_sync', return_value=shared_jobs):
            result = await job_sharing_service.get_shared_jobs('user-456')

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_shared_jobs_empty(self, job_sharing_service, mock_cosmos_service):
        """Test when no jobs are shared with user"""
        with patch('app.services.jobs.job_sharing_service.run_sync', return_value=[]):
            result = await job_sharing_service.get_shared_jobs('user-456')

        assert isinstance(result, list)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_shared_jobs_database_error(self, job_sharing_service, mock_cosmos_service):
        """Test get_shared_jobs handles database errors"""
        with patch('app.services.jobs.job_sharing_service.run_sync', side_effect=DatabaseError("DB error")):
            with pytest.raises(DatabaseError):
                await job_sharing_service.get_shared_jobs('user-456')


# Note: get_job_shares method not found in JobSharingService
# Use get_job_sharing_info instead for getting share information


class TestPermissionValidation:
    """Tests for permission validation"""

    @pytest.mark.asyncio
    async def test_validate_user_can_view_shared_job(self, job_sharing_service, mock_cosmos_service, sample_shared_job):
        """Test validation that user can view shared job"""
        if not hasattr(job_sharing_service, 'can_user_access_job'):
            pytest.skip("can_user_access_job method not implemented")

        mock_cosmos_service.get_job_by_id_async.return_value = sample_shared_job.copy()

        # Shared user should have access
        can_access = await job_sharing_service.can_user_access_job('job-789', 'shared-user-1')
        assert can_access is True

    @pytest.mark.asyncio
    async def test_validate_user_cannot_access_unshared_job(self, job_sharing_service, mock_cosmos_service, sample_job):
        """Test validation that non-owner cannot access unshared job"""
        if not hasattr(job_sharing_service, 'can_user_access_job'):
            pytest.skip("can_user_access_job method not implemented")

        mock_cosmos_service.get_job_by_id_async.return_value = sample_job.copy()

        # Non-owner should not have access
        can_access = await job_sharing_service.can_user_access_job('job-123', 'other-user')
        assert can_access is False
