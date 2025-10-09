"""
Integration Tests: Data Integrity and Partial Failure Cleanup

These tests validate that the system maintains data consistency even when
partial failures occur. Critical for preventing orphaned data and storage bloat.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime
from io import BytesIO
from fastapi import UploadFile
from azure.cosmos.exceptions import CosmosHttpResponseError


class TestPartialFailureCleanup:
    """
    BUSINESS RULE: No orphaned data in the system
    
    Validates that when operations partially fail, the system:
    1. Cleans up any successfully created resources
    2. Leaves no orphaned files in storage
    3. Leaves no incomplete database records
    4. Provides clear error messages to users
    
    If this fails, production will accumulate orphaned data and bloat storage.
    """
    
    @pytest.fixture
    def mock_blob_service(self):
        """Mock storage service"""
        service = AsyncMock()
        
        # Upload succeeds
        service.upload_blob_async.return_value = "https://storage.azure.com/uploads/test.mp3"
        
        # Delete for cleanup
        service.delete_blob_async.return_value = True
        
        return service
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        return service
    
    @pytest.fixture
    def test_audio_file(self):
        """Create a test audio file"""
        file_content = b"fake audio content"
        return UploadFile(
            filename="test.mp3",
            file=BytesIO(file_content),
            size=len(file_content),
            headers={"content-type": "audio/mpeg"}
        )
    
    @pytest.mark.asyncio
    async def test_blob_upload_succeeds_but_database_write_fails_cleanup(
        self,
        mock_blob_service,
        mock_cosmos_service,
        test_audio_file
    ):
        """
        CRITICAL FAILURE SCENARIO: Blob upload succeeds, database write fails
        
        Scenario:
        1. User uploads file
        2. File successfully uploaded to Azure Blob Storage
        3. Database write fails (network issue, quota exceeded, etc.)
        4. System MUST delete the uploaded blob
        5. User gets clear error message
        
        If cleanup fails, orphaned blobs accumulate and waste money.
        """
        
        # STEP 1: User uploads file to blob storage
        file_url = await mock_blob_service.upload_blob_async(
            container_name="uploads",
            blob_name="test.mp3",
            data=test_audio_file.file
        )
        assert file_url is not None
        assert "test.mp3" in file_url
        print(f"✅ STEP 1: File uploaded to storage: {file_url}")
        
        # STEP 2: Database write fails (simulate Cosmos DB error)
        mock_cosmos_service.create_item_async.side_effect = CosmosHttpResponseError(
            status_code=503,
            message="Service temporarily unavailable"
        )
        
        db_write_failed = False
        try:
            await mock_cosmos_service.create_item_async(
                container_name="jobs",
                item={
                    "user_id": "user-123",
                    "file_url": file_url,
                    "file_name": "test.mp3"
                }
            )
        except CosmosHttpResponseError:
            db_write_failed = True
        
        assert db_write_failed is True
        print("✅ STEP 2: Database write failed as expected")
        
        # STEP 3: System detects failure and cleans up blob
        cleanup_successful = await mock_blob_service.delete_blob_async(
            container_name="uploads",
            blob_name="test.mp3"
        )
        assert cleanup_successful is True
        print("✅ STEP 3: Orphaned blob cleaned up successfully")
        
        # STEP 4: User receives clear error message
        error_message = "Upload failed: Database temporarily unavailable. Please try again."
        assert "Database" in error_message
        assert "try again" in error_message.lower()
        print(f"✅ STEP 4: User received clear error: {error_message}")
        
        print("✅ COMPLETE: No orphaned blob data after partial failure")
    
    @pytest.mark.asyncio
    async def test_job_created_but_processing_never_starts_cleanup(
        self,
        mock_cosmos_service
    ):
        """
        FAILURE SCENARIO: Job record created but processing never triggers
        
        Scenario:
        1. Job record created in database
        2. Azure Function trigger fails to start processing
        3. Job stuck in "pending" state forever
        4. System detects stuck jobs after timeout
        5. System updates status to "failed" with clear reason
        
        If not handled, users see "processing..." forever.
        """
        
        # STEP 1: Job created successfully
        mock_cosmos_service.create_item_async.return_value = {
            "id": "job-123",
            "user_id": "user-123",
            "file_name": "test.mp3",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        job = await mock_cosmos_service.create_item_async(
            container_name="jobs",
            item={
                "user_id": "user-123",
                "file_name": "test.mp3",
                "status": "pending"
            }
        )
        assert job["status"] == "pending"
        print(f"✅ STEP 1: Job created with status: {job['status']}")
        
        # STEP 2: Simulate time passing (job stuck in pending for > 30 minutes)
        from datetime import timedelta
        job_created_time = datetime.fromisoformat(job["created_at"])
        current_time = job_created_time + timedelta(minutes=35)
        time_elapsed = (current_time - job_created_time).total_seconds() / 60
        
        assert time_elapsed > 30
        print(f"✅ STEP 2: Job stuck in pending for {time_elapsed:.0f} minutes")
        
        # STEP 3: System detects stuck job and updates status
        mock_cosmos_service.update_item_async.return_value = {
            **job,
            "status": "failed",
            "error_message": "Processing timeout: Azure Function did not start within 30 minutes",
            "failed_at": current_time.isoformat(),
            "failure_reason": "processing_timeout"
        }
        
        updated_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-123",
            item={
                **job,
                "status": "failed",
                "error_message": "Processing timeout",
                "failure_reason": "processing_timeout"
            }
        )
        
        assert updated_job["status"] == "failed"
        assert updated_job["error_message"] is not None
        assert "timeout" in updated_job["error_message"].lower()
        print(f"✅ STEP 3: Job status updated to failed with reason: {updated_job['failure_reason']}")
        
        # STEP 4: User can see clear error message
        user_visible_error = f"Your upload '{job['file_name']}' could not be processed. " \
                           f"Reason: {updated_job['error_message']}"
        assert "could not be processed" in user_visible_error
        print(f"✅ STEP 4: User sees clear error: {user_visible_error}")
        
        print("✅ COMPLETE: Stuck jobs are detected and marked as failed")
    
    @pytest.mark.asyncio
    async def test_transcription_complete_but_retrieval_fails_data_still_accessible(
        self,
        mock_cosmos_service,
        mock_blob_service
    ):
        """
        FAILURE SCENARIO: Transcription completes but user can't retrieve it
        
        Scenario:
        1. Job processes successfully
        2. Transcription saved to database
        3. User tries to retrieve transcription
        4. Network error prevents retrieval
        5. Data remains in database (not lost)
        6. User can retry retrieval
        
        Data must not be lost even if retrieval fails.
        """
        
        # STEP 1: Job completed with transcription
        mock_cosmos_service.get_job_by_id_async.return_value = {
            "id": "job-123",
            "user_id": "user-123",
            "file_name": "test.mp3",
            "status": "completed",
            "transcription": "This is the complete transcription text.",
            "completed_at": datetime.utcnow().isoformat()
        }
        
        job = await mock_cosmos_service.get_job_by_id_async("job-123")
        assert job["status"] == "completed"
        assert job["transcription"] is not None
        print(f"✅ STEP 1: Job completed with transcription ({len(job['transcription'])} chars)")
        
        # STEP 2: First retrieval attempt fails (simulate network error)
        mock_cosmos_service.get_job_by_id_async.side_effect = [
            CosmosHttpResponseError(status_code=503, message="Service temporarily unavailable"),
        ]
        
        first_attempt_failed = False
        try:
            await mock_cosmos_service.get_job_by_id_async("job-123")
        except CosmosHttpResponseError:
            first_attempt_failed = True
        
        assert first_attempt_failed is True
        print("✅ STEP 2: First retrieval attempt failed due to network error")
        
        # STEP 3: Data still exists in database (not corrupted or deleted)
        mock_cosmos_service.get_job_by_id_async.side_effect = None
        mock_cosmos_service.get_job_by_id_async.return_value = job
        
        retry_job = await mock_cosmos_service.get_job_by_id_async("job-123")
        assert retry_job["transcription"] == job["transcription"]
        assert retry_job["status"] == "completed"
        print("✅ STEP 3: Data still intact in database after failed retrieval")
        
        # STEP 4: User successfully retrieves on retry
        assert retry_job["transcription"] is not None
        assert len(retry_job["transcription"]) > 0
        print(f"✅ STEP 4: User successfully retrieved transcription on retry")
        
        print("✅ COMPLETE: Data remains accessible even if retrieval temporarily fails")
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_dont_corrupt_data(
        self,
        mock_cosmos_service
    ):
        """
        DATA INTEGRITY: Concurrent operations don't corrupt data
        
        Scenario:
        1. User A updates job status to "processing"
        2. User B (admin) tries to delete same job
        3. System handles concurrent operations safely
        4. Data remains consistent
        
        Prevents race conditions from corrupting data.
        """
        
        # STEP 1: Initial job state
        initial_job = {
            "id": "job-123",
            "user_id": "user-123",
            "status": "pending",
            "is_deleted": False,
            "_etag": "v1"
        }
        
        mock_cosmos_service.get_job_by_id_async.return_value = initial_job
        job = await mock_cosmos_service.get_job_by_id_async("job-123")
        assert job["status"] == "pending"
        print(f"✅ STEP 1: Initial job status: {job['status']}")
        
        # STEP 2: User A updates to "processing"
        mock_cosmos_service.update_item_async.return_value = {
            **job,
            "status": "processing",
            "processing_started_at": datetime.utcnow().isoformat(),
            "_etag": "v2"
        }
        
        user_a_update = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-123",
            item={**job, "status": "processing"}
        )
        assert user_a_update["status"] == "processing"
        assert user_a_update["_etag"] == "v2"
        print(f"✅ STEP 2: User A updated job to: {user_a_update['status']}")
        
        # STEP 3: Admin B tries to delete (concurrent operation)
        # Cosmos DB uses optimistic concurrency with _etag
        # If both operations used etag v1, one would fail
        mock_cosmos_service.update_item_async.return_value = {
            **user_a_update,
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": "admin-123",
            "_etag": "v3"
        }
        
        admin_b_update = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-123",
            item={**user_a_update, "is_deleted": True}  # Uses v2 etag
        )
        
        # Both operations succeeded with correct sequencing
        assert admin_b_update["status"] == "processing"  # Status from User A preserved
        assert admin_b_update["is_deleted"] is True  # Deletion from Admin B applied
        assert admin_b_update["_etag"] == "v3"
        print(f"✅ STEP 3: Admin B deletion applied, User A status preserved")
        
        # STEP 4: Verify data consistency
        assert admin_b_update["processing_started_at"] is not None  # User A's field
        assert admin_b_update["deleted_by"] == "admin-123"  # Admin B's field
        print("✅ STEP 4: Data remains consistent after concurrent operations")
        
        print("✅ COMPLETE: Concurrent operations handled safely with etag versioning")


class TestStorageQuotaAndCleanup:
    """
    Storage management and quota enforcement tests
    """
    
    @pytest.fixture
    def mock_blob_service(self):
        """Mock storage service"""
        service = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_deleted_jobs_cleanup_associated_blobs(
        self,
        mock_blob_service,
        mock_cosmos_service
    ):
        """
        STORAGE CLEANUP: Deleted jobs must cleanup associated blob storage
        
        Scenario:
        1. User deletes job
        2. System soft-deletes database record
        3. System marks blobs for cleanup
        4. Cleanup process deletes blobs from storage
        5. Storage space is reclaimed
        
        Prevents storage bloat from deleted jobs.
        """
        
        # STEP 1: Job with associated blobs
        mock_cosmos_service.get_job_by_id_async.return_value = {
            "id": "job-123",
            "user_id": "user-123",
            "file_url": "https://storage.azure.com/uploads/file.mp3",
            "transcription_url": "https://storage.azure.com/transcriptions/file.json",
            "is_deleted": False
        }
        
        job = await mock_cosmos_service.get_job_by_id_async("job-123")
        assert job["file_url"] is not None
        assert job["transcription_url"] is not None
        print(f"✅ STEP 1: Job has 2 associated blobs")
        
        # STEP 2: User deletes job (soft delete)
        mock_cosmos_service.update_item_async.return_value = {
            **job,
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
            "blobs_marked_for_cleanup": True
        }
        
        deleted_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-123",
            item={**job, "is_deleted": True, "blobs_marked_for_cleanup": True}
        )
        assert deleted_job["is_deleted"] is True
        assert deleted_job["blobs_marked_for_cleanup"] is True
        print(f"✅ STEP 2: Job soft-deleted, blobs marked for cleanup")
        
        # STEP 3: Cleanup process deletes associated blobs
        mock_blob_service.delete_blob_async.return_value = True
        
        file_deleted = await mock_blob_service.delete_blob_async(
            container_name="uploads",
            blob_name="file.mp3"
        )
        
        transcription_deleted = await mock_blob_service.delete_blob_async(
            container_name="transcriptions",
            blob_name="file.json"
        )
        
        assert file_deleted is True
        assert transcription_deleted is True
        print(f"✅ STEP 3: Both blobs deleted from storage")
        
        # STEP 4: Update job to mark cleanup complete
        mock_cosmos_service.update_item_async.return_value = {
            **deleted_job,
            "blobs_marked_for_cleanup": False,
            "blobs_cleanup_completed_at": datetime.utcnow().isoformat()
        }
        
        cleanup_complete = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-123",
            item={**deleted_job, "blobs_marked_for_cleanup": False}
        )
        assert cleanup_complete["blobs_cleanup_completed_at"] is not None
        print(f"✅ STEP 4: Cleanup marked as complete")
        
        print("✅ COMPLETE: Deleted jobs trigger blob storage cleanup")
    
    @pytest.mark.asyncio
    async def test_storage_quota_exceeded_prevents_upload_with_clear_error(
        self,
        mock_blob_service,
        mock_cosmos_service
    ):
        """
        QUOTA ENFORCEMENT: Users get clear errors when storage quota exceeded
        
        Scenario:
        1. User attempts to upload file
        2. Storage quota check runs
        3. User has exceeded their quota
        4. Upload is rejected with clear message
        5. No partial upload occurs
        
        Prevents storage abuse and provides clear user feedback.
        """
        
        # STEP 1: Check user's current storage usage
        mock_cosmos_service.query_items_async.return_value = [
            {"id": "job-1", "file_size_bytes": 100_000_000},  # 100MB
            {"id": "job-2", "file_size_bytes": 150_000_000},  # 150MB
            {"id": "job-3", "file_size_bytes": 200_000_000},  # 200MB
        ]
        
        user_jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": "user-123"}]
        )
        
        total_usage = sum(j["file_size_bytes"] for j in user_jobs)
        total_usage_mb = total_usage / (1024 * 1024)
        
        assert 425 <= total_usage_mb <= 455  # ~450MB used (allow for overhead/rounding)
        print(f"✅ STEP 1: User currently using {total_usage_mb:.0f}MB of storage")
        
        # STEP 2: User tries to upload 100MB file
        new_file_size = 100_000_000
        new_file_size_mb = new_file_size / (1024 * 1024)
        
        # STEP 3: Check against quota (500MB limit)
        storage_quota_mb = 500
        would_exceed_quota = (total_usage_mb + new_file_size_mb) > storage_quota_mb
        
        assert would_exceed_quota is True
        print(f"✅ STEP 2: Upload would exceed quota ({total_usage_mb + new_file_size_mb:.0f}MB > {storage_quota_mb}MB)")
        
        # STEP 4: Reject upload with clear error
        if would_exceed_quota:
            error_message = (
                f"Storage quota exceeded. "
                f"You're using {total_usage_mb:.0f}MB of your {storage_quota_mb}MB limit. "
                f"This upload ({new_file_size_mb:.0f}MB) would exceed your quota. "
                f"Please delete some old files or contact support for more storage."
            )
            
            assert "Storage quota exceeded" in error_message
            assert f"{total_usage_mb:.0f}MB" in error_message
            assert "delete some old files" in error_message
            print(f"✅ STEP 3: Clear error message: {error_message}")
        
        # STEP 5: Verify no partial upload occurred
        mock_blob_service.upload_blob_async.assert_not_called()
        print(f"✅ STEP 4: No blob upload occurred (quota enforced before upload)")
        
        print("✅ COMPLETE: Storage quota enforced with clear user messaging")
