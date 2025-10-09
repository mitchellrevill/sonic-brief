"""
Unit tests for BackgroundProcessingService.

Tests cover background task scheduling, execution with retry logic, circuit breaker patterns,
Azure Functions integration, task status tracking, and error handling.

Coverage target: 90%+
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import asyncio

import httpx
from tenacity import RetryError
from fastapi import BackgroundTasks

from app.services.processing.background_service import (
    BackgroundProcessingService,
    BackgroundTask,
    TaskStatus,
    CircuitBreaker
)


# ============================================================================
# Test BackgroundTask Model
# ============================================================================

class TestBackgroundTaskModel:
    """Test BackgroundTask model and status tracking"""

    def test_background_task_initialization(self):
        """Should initialize BackgroundTask with default values"""
        task = BackgroundTask("task-123", "file_upload", "user-456")
        
        assert task.task_id == "task-123"
        assert task.task_type == "file_upload"
        assert task.user_id == "user-456"
        assert task.status == TaskStatus.PENDING
        assert task.error_message is None
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.result is None

    def test_background_task_with_metadata(self):
        """Should store task metadata"""
        metadata = {"file_name": "test.mp3", "file_size": 1024}
        task = BackgroundTask("task-123", "file_upload", "user-456", metadata=metadata)
        
        assert task.metadata == metadata

    def test_update_status_success(self):
        """Should update task status"""
        task = BackgroundTask("task-123", "file_upload", "user-456")
        
        task.update_status(TaskStatus.RUNNING)
        assert task.status == TaskStatus.RUNNING
        
        task.update_status(TaskStatus.COMPLETED, result={"url": "https://example.com/file.mp3"})
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"url": "https://example.com/file.mp3"}

    def test_update_status_with_error(self):
        """Should update task status with error message"""
        task = BackgroundTask("task-123", "file_upload", "user-456")
        
        task.update_status(TaskStatus.FAILED, error_message="Upload failed")
        
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Upload failed"

    def test_to_dict_conversion(self):
        """Should convert task to dictionary"""
        task = BackgroundTask("task-123", "file_upload", "user-456")
        task.update_status(TaskStatus.COMPLETED, result={"url": "https://example.com/file.mp3"})
        
        task_dict = task.to_dict()
        
        assert task_dict["task_id"] == "task-123"
        assert task_dict["task_type"] == "file_upload"
        assert task_dict["user_id"] == "user-456"
        assert task_dict["status"] == "completed"
        assert task_dict["result"] == {"url": "https://example.com/file.mp3"}
        assert "created_at" in task_dict
        assert "updated_at" in task_dict


# ============================================================================
# Test CircuitBreaker
# ============================================================================

class TestCircuitBreaker:
    """Test CircuitBreaker pattern implementation"""

    def test_circuit_breaker_initialization(self):
        """Should initialize circuit breaker with default values"""
        breaker = CircuitBreaker()
        
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.failure_count == 0
        assert breaker.state == "CLOSED"

    def test_circuit_breaker_custom_thresholds(self):
        """Should initialize with custom thresholds"""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 30

    def test_circuit_breaker_opens_after_threshold(self):
        """Should open circuit after reaching failure threshold"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        assert not breaker.is_open()
        
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_failure()
        
        assert breaker.is_open()
        assert breaker.state == "OPEN"

    def test_circuit_breaker_resets_on_success(self):
        """Should reset failure count on successful operation"""
        breaker = CircuitBreaker(failure_threshold=3)
        
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2
        
        breaker.record_success()
        assert breaker.failure_count == 0

    def test_circuit_breaker_half_open_after_timeout(self):
        """Should transition to HALF_OPEN after recovery timeout"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        # Wait for recovery timeout
        import time
        time.sleep(1.1)
        
        # Calling is_open() triggers the state check
        is_open = breaker.is_open()
        assert not is_open
        assert breaker.state == "HALF_OPEN"

    def test_circuit_breaker_closes_on_success_from_half_open(self):
        """Should close circuit on successful operation from HALF_OPEN"""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        import time
        time.sleep(1.1)
        
        # Trigger state check by calling is_open()
        breaker.is_open()
        assert breaker.state == "HALF_OPEN"
        
        breaker.record_success()
        assert breaker.state == "CLOSED"


# ============================================================================
# Test BackgroundProcessingService Initialization
# ============================================================================

class TestBackgroundProcessingServiceInitialization:
    """Test service initialization and configuration"""

    def test_service_initialization(self, mock_cosmos_service):
        """Should initialize service with dependencies"""
        storage_service = Mock()
        analytics_service = Mock()
        
        service = BackgroundProcessingService(
            storage_service=storage_service,
            cosmos_service=mock_cosmos_service,
            analytics_service=analytics_service
        )
        
        assert service.storage_service == storage_service
        assert service.cosmos_service == mock_cosmos_service
        assert service.analytics_service == analytics_service
        assert service.circuit_breaker is not None
        assert service.tasks == {}

    def test_azure_functions_base_url_from_config(self, mock_cosmos_service):
        """Should extract Azure Functions base URL from config"""
        mock_cosmos_service.config.azure_functions = {"base_url": "https://func-app.azurewebsites.net"}
        
        storage_service = Mock()
        analytics_service = Mock()
        
        service = BackgroundProcessingService(
            storage_service=storage_service,
            cosmos_service=mock_cosmos_service,
            analytics_service=analytics_service
        )
        
        assert service.azure_functions_base_url == "https://func-app.azurewebsites.net"

    def test_azure_functions_base_url_fallback(self):
        """Should fallback to localhost if no config provided"""
        # Create a mock cosmos service with no azure_functions config
        mock_cosmos = Mock()
        mock_cosmos.config = Mock()
        mock_cosmos.config.azure_functions = None
        # Ensure getattr fallback also returns None
        type(mock_cosmos.config).azure_functions_base_url = property(lambda self: None)
        
        storage_service = Mock()
        analytics_service = Mock()
        
        service = BackgroundProcessingService(
            storage_service=storage_service,
            cosmos_service=mock_cosmos,
            analytics_service=analytics_service
        )
        
        assert service.azure_functions_base_url == "http://localhost:7071"


# ============================================================================
# Test Task Submission and Execution
# ============================================================================

class TestTaskSubmissionAndExecution:
    """Test task submission and background execution"""

    @pytest.mark.asyncio
    async def test_submit_task_creates_task(self, mock_cosmos_service):
        """Should create and track background task"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        background_tasks = BackgroundTasks()
        async def mock_task_func(arg1, arg2):
            return {"result": "success"}
        
        task = await service.submit_task(
            task_id="task-123",
            task_type="test_task",
            user_id="user-456",
            task_func=mock_task_func,
            background_tasks=background_tasks,
            metadata={"key": "value"},
            arg1="value1",
            arg2="value2"
        )
        
        assert task.task_id == "task-123"
        assert task.task_type == "test_task"
        assert task.user_id == "user-456"
        assert task.status == TaskStatus.PENDING
        assert task.metadata == {"key": "value"}
        assert "task-123" in service.tasks

    @pytest.mark.asyncio
    async def test_execute_task_with_retry_success(self, mock_cosmos_service):
        """Should execute task successfully"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        task = BackgroundTask("task-123", "test_task", "user-456")
        service.tasks["task-123"] = task
        
        async def mock_task_func():
            return {"result": "success"}
        
        await service._execute_task_with_retry(task, mock_task_func)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"result": "success"}
        assert task.error_message is None

    @pytest.mark.asyncio
    async def test_execute_task_with_retry_failure(self, mock_cosmos_service):
        """Should handle task failure after retries"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        task = BackgroundTask("task-123", "test_task", "user-456")
        service.tasks["task-123"] = task
        
        async def mock_task_func():
            raise Exception("Task failed")
        
        # Mock the retry decorator to fail immediately
        with patch.object(service, '_retry_with_circuit_breaker', side_effect=RetryError("Max retries exceeded")):
            await service._execute_task_with_retry(task, mock_task_func)
        
        assert task.status == TaskStatus.FAILED
        assert "retries" in task.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_task_unexpected_error(self, mock_cosmos_service):
        """Should handle unexpected errors during task execution"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        task = BackgroundTask("task-123", "test_task", "user-456")
        service.tasks["task-123"] = task
        
        async def mock_task_func():
            raise ValueError("Unexpected error")
        
        with patch.object(service, '_retry_with_circuit_breaker', side_effect=ValueError("Unexpected error")):
            await service._execute_task_with_retry(task, mock_task_func)
        
        assert task.status == TaskStatus.FAILED
        assert "Unexpected error" in task.error_message


# ============================================================================
# Test Azure Functions Integration
# ============================================================================

class TestAzureFunctionsIntegration:
    """Test Azure Functions API calls with retry and circuit breaker"""

    @pytest.mark.asyncio
    async def test_call_azure_function_success(self, mock_cosmos_service, mock_httpx_client):
        """Should successfully call Azure Function"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        payload = {"job_id": "job-123", "user_id": "user-456"}
        
        # Patch get_client from the correct import path
        with patch('app.core.http_client.get_client', return_value=mock_httpx_client):
            result = await service.call_azure_function(
                "https://func-app.azurewebsites.net/api/test",
                payload
            )
        
        assert result == {"status": "success"}
        mock_httpx_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_azure_function_circuit_breaker_open(self, mock_cosmos_service):
        """Should raise exception when circuit breaker is open"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        # Open the circuit breaker
        service.circuit_breaker.state = "OPEN"
        service.circuit_breaker.last_failure_time = datetime.now().timestamp()
        
        payload = {"job_id": "job-123"}
        
        with pytest.raises(Exception, match="circuit breaker is OPEN"):
            await service.call_azure_function("https://func-app.azurewebsites.net/api/test", payload)

    @pytest.mark.asyncio
    async def test_call_azure_function_http_error(self, mock_cosmos_service, mock_httpx_client):
        """Should handle HTTP errors and record circuit breaker failure"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        mock_httpx_client.post = AsyncMock(side_effect=httpx.HTTPError("Request failed"))
        
        payload = {"job_id": "job-123"}
        
        with patch('app.core.http_client.get_client', return_value=mock_httpx_client):
            with pytest.raises(httpx.HTTPError):
                await service.call_azure_function("https://func-app.azurewebsites.net/api/test", payload)
        
        assert service.circuit_breaker.failure_count > 0

    @pytest.mark.asyncio
    async def test_call_azure_function_with_custom_headers(self, mock_cosmos_service, mock_httpx_client):
        """Should include custom headers in request"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        payload = {"job_id": "job-123"}
        custom_headers = {"X-Custom-Header": "test-value"}
        
        with patch('app.core.http_client.get_client', return_value=mock_httpx_client):
            await service.call_azure_function(
                "https://func-app.azurewebsites.net/api/test",
                payload,
                headers=custom_headers
            )
        
        call_args = mock_httpx_client.post.call_args
        assert "X-Custom-Header" in call_args.kwargs['headers']


# ============================================================================
# Test Processing Methods
# ============================================================================

class TestProcessingMethods:
    """Test specific processing methods"""

    @pytest.mark.asyncio
    async def test_process_audio_analysis(self, mock_cosmos_service, mock_httpx_client):
        """Should process audio analysis request"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        service.config.azure_functions_base_url = "https://func-app.azurewebsites.net"
        
        with patch('app.core.http_client.get_client', return_value=mock_httpx_client):
            result = await service.process_audio_analysis(
                file_path="https://storage.blob.core.windows.net/recordings/test.mp3",
                job_id="job-123",
                user_id="user-456",
                analysis_type="comprehensive"
            )
        
        assert result == {"status": "success"}
        
        # Verify payload structure
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs['json']
        assert payload["job_id"] == "job-123"
        assert payload["user_id"] == "user-456"
        assert payload["analysis_type"] == "comprehensive"

    @pytest.mark.asyncio
    async def test_process_text_refinement(self, mock_cosmos_service, mock_httpx_client):
        """Should process text refinement request"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        service.config.azure_functions_base_url = "https://func-app.azurewebsites.net"
        
        with patch('app.core.http_client.get_client', return_value=mock_httpx_client):
            result = await service.process_text_refinement(
                text="Original text",
                refinement_prompt="Make it better",
                job_id="job-123",
                user_id="user-456"
            )
        
        assert result == {"status": "success"}
        
        # Verify payload structure
        call_args = mock_httpx_client.post.call_args
        payload = call_args.kwargs['json']
        assert payload["text"] == "Original text"
        assert payload["refinement_prompt"] == "Make it better"


# ============================================================================
# Test Task Status Tracking
# ============================================================================

class TestTaskStatusTracking:
    """Test task status retrieval and filtering"""

    def test_get_task_status_existing(self, mock_cosmos_service):
        """Should retrieve status for existing task"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        task = BackgroundTask("task-123", "file_upload", "user-456")
        service.tasks["task-123"] = task
        
        status = service.get_task_status("task-123")
        
        assert status is not None
        assert status["task_id"] == "task-123"
        assert status["task_type"] == "file_upload"

    def test_get_task_status_nonexistent(self, mock_cosmos_service):
        """Should return None for nonexistent task"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        status = service.get_task_status("nonexistent-task")
        
        assert status is None

    def test_get_user_tasks(self, mock_cosmos_service):
        """Should retrieve all tasks for a user"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        task1 = BackgroundTask("task-1", "file_upload", "user-456")
        task2 = BackgroundTask("task-2", "analysis", "user-456")
        task3 = BackgroundTask("task-3", "file_upload", "user-789")
        
        service.tasks["task-1"] = task1
        service.tasks["task-2"] = task2
        service.tasks["task-3"] = task3
        
        user_tasks = service.get_user_tasks("user-456")
        
        assert len(user_tasks) == 2
        assert all(t["user_id"] == "user-456" for t in user_tasks)

    def test_get_user_tasks_sorted_by_created_at(self, mock_cosmos_service):
        """Should return user tasks sorted by creation time (newest first)"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        task1 = BackgroundTask("task-1", "file_upload", "user-456")
        task2 = BackgroundTask("task-2", "analysis", "user-456")
        
        # Manually set creation times
        task1.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        task2.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        service.tasks["task-1"] = task1
        service.tasks["task-2"] = task2
        
        user_tasks = service.get_user_tasks("user-456")
        
        # Should be sorted newest first
        assert user_tasks[0]["task_id"] == "task-2"
        assert user_tasks[1]["task_id"] == "task-1"


# ============================================================================
# Test Task Cleanup
# ============================================================================

class TestTaskCleanup:
    """Test task cleanup and maintenance"""

    def test_cleanup_old_completed_tasks(self, mock_cosmos_service):
        """Should remove old completed tasks"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        old_task = BackgroundTask("task-old", "file_upload", "user-456")
        old_task.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
        old_task.update_status(TaskStatus.COMPLETED)
        
        recent_task = BackgroundTask("task-recent", "analysis", "user-456")
        recent_task.update_status(TaskStatus.COMPLETED)
        
        service.tasks["task-old"] = old_task
        service.tasks["task-recent"] = recent_task
        
        service.cleanup_old_tasks(max_age_hours=24)
        
        assert "task-old" not in service.tasks
        assert "task-recent" in service.tasks

    def test_cleanup_old_failed_tasks(self, mock_cosmos_service):
        """Should remove old failed tasks"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        old_failed_task = BackgroundTask("task-failed", "file_upload", "user-456")
        old_failed_task.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
        old_failed_task.update_status(TaskStatus.FAILED, error_message="Upload failed")
        
        service.tasks["task-failed"] = old_failed_task
        
        service.cleanup_old_tasks(max_age_hours=24)
        
        assert "task-failed" not in service.tasks

    def test_cleanup_preserves_pending_and_running_tasks(self, mock_cosmos_service):
        """Should not remove pending or running tasks regardless of age"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        old_pending = BackgroundTask("task-pending", "file_upload", "user-456")
        old_pending.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
        
        old_running = BackgroundTask("task-running", "analysis", "user-456")
        old_running.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
        old_running.update_status(TaskStatus.RUNNING)
        
        service.tasks["task-pending"] = old_pending
        service.tasks["task-running"] = old_running
        
        service.cleanup_old_tasks(max_age_hours=24)
        
        # Should preserve pending and running tasks
        assert "task-pending" in service.tasks
        assert "task-running" in service.tasks


# ============================================================================
# Test Circuit Breaker Status
# ============================================================================

class TestCircuitBreakerStatus:
    """Test circuit breaker status retrieval"""

    def test_get_circuit_breaker_status(self, mock_cosmos_service):
        """Should return circuit breaker status"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        status = service.get_circuit_breaker_status()
        
        assert "state" in status
        assert "failure_count" in status
        assert "failure_threshold" in status
        assert status["state"] == "CLOSED"
        assert status["failure_count"] == 0

    def test_get_circuit_breaker_status_after_failures(self, mock_cosmos_service):
        """Should reflect current circuit breaker state"""
        storage_service = Mock()
        analytics_service = Mock()
        service = BackgroundProcessingService(storage_service, mock_cosmos_service, analytics_service)
        
        service.circuit_breaker.record_failure()
        service.circuit_breaker.record_failure()
        
        status = service.get_circuit_breaker_status()
        
        assert status["failure_count"] == 2
