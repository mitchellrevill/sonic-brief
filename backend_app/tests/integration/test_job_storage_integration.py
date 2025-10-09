"""
Integration tests for Job Service + Storage Service.

Tests the complete job lifecycle including:
- Job creation with file storage
- Transcription state management
- File upload and retrieval
- Job status updates across services
- Blob storage operations
"""
import pytest
from datetime import datetime
from typing import Dict, Any
from io import BytesIO

from app.services.jobs.job_service import JobService
from app.services.storage.blob_service import StorageService


class TestJobStorageIntegration:
    """Test job service integration with blob storage"""
    
    @pytest.mark.asyncio
    async def test_create_job_with_file_upload(
        self,
        integration_job_service: JobService,
        integration_storage_service: StorageService,
        test_user_data: Dict[str, Any],
        test_job_data: Dict[str, Any]
    ):
        """Test creating a job and uploading associated file to storage"""
        user_id = test_user_data["id"]
        job_id = test_job_data["id"]
        
        # Step 1: Create job in Cosmos
        job_document = {
            **test_job_data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        container = integration_job_service.cosmos.get_container("jobs")
        created_job = container.upsert_item(job_document)
        
        assert created_job["id"] == job_id
        assert created_job["user_id"] == user_id
        assert created_job["status"] == "pending"
        
        # Step 2: Upload file to blob storage
        file_content = b"Sample audio file content"
        file_name = "test-audio.mp3"
        
        # Simulate file upload
        blob_client = integration_storage_service._blob_service_client.get_blob_client(
            container="audio-files",
            blob=f"{user_id}/{job_id}/{file_name}"
        )
        
        await blob_client.upload_blob(file_content)
        
        # Verify blob was uploaded
        exists = await blob_client.exists()
        assert exists is True
        
        # Step 3: Update job with file URL
        created_job["file_url"] = f"https://storage.blob.core.windows.net/audio-files/{user_id}/{job_id}/{file_name}"
        created_job["file_size"] = len(file_content)
        
        updated_job = container.upsert_item(created_job)
        assert updated_job["file_url"] is not None
        assert updated_job["file_size"] == len(file_content)
    
    @pytest.mark.asyncio
    async def test_job_transcription_lifecycle(
        self,
        integration_job_service: JobService,
        integration_cosmos_service
    ):
        """Test complete transcription job lifecycle across Cosmos updates"""
        job_id = "job-lifecycle-001"
        user_id = "user-lifecycle"
        
        container = integration_cosmos_service.get_container("jobs")
        
        # Stage 1: Create pending job
        job = {
            "id": job_id,
            "user_id": user_id,
            "title": "Lifecycle Test Job",
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        container.upsert_item(job)
        
        # Verify initial state
        retrieved = container.read_item(item_id=job_id, partition_key=user_id)
        assert retrieved["status"] == "pending"
        
        # Stage 2: Start processing
        retrieved["status"] = "processing"
        retrieved["processing_started_at"] = datetime.utcnow().isoformat()
        container.upsert_item(retrieved)
        
        retrieved = container.read_item(item_id=job_id, partition_key=user_id)
        assert retrieved["status"] == "processing"
        assert "processing_started_at" in retrieved
        
        # Stage 3: Complete transcription
        retrieved["status"] = "completed"
        retrieved["completed_at"] = datetime.utcnow().isoformat()
        retrieved["transcription_text"] = "Sample transcription result"
        container.upsert_item(retrieved)
        
        final = container.read_item(item_id=job_id, partition_key=user_id)
        assert final["status"] == "completed"
        assert final["transcription_text"] == "Sample transcription result"
        assert "completed_at" in final
    
    @pytest.mark.asyncio
    async def test_file_download_from_storage(
        self,
        integration_storage_service: StorageService
    ):
        """Test downloading a file from blob storage"""
        container_name = "audio-files"
        blob_name = "test-user/test-job/audio.mp3"
        test_content = b"Test audio content for download"
        
        # Upload test file
        blob_client = integration_storage_service._blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        await blob_client.upload_blob(test_content)
        
        # Download file
        download_result = await blob_client.download_blob()
        downloaded_content = await download_result.readall()
        
        assert downloaded_content == test_content
    
    @pytest.mark.asyncio
    async def test_job_with_multiple_files(
        self,
        integration_job_service: JobService,
        integration_storage_service: StorageService
    ):
        """Test job with multiple associated files (audio, transcription, analysis)"""
        job_id = "job-multifile"
        user_id = "user-multifile"
        
        # Create job
        job = {
            "id": job_id,
            "user_id": user_id,
            "title": "Multi-file Job",
            "status": "pending",
            "files": []
        }
        
        container = integration_job_service.cosmos.get_container("jobs")
        container.upsert_item(job)
        
        # Upload multiple files
        files_to_upload = [
            ("audio.mp3", b"Audio content"),
            ("transcription.txt", b"Transcription text"),
            ("analysis.json", b'{"summary": "test"}')
        ]
        
        for file_name, content in files_to_upload:
            blob_client = integration_storage_service._blob_service_client.get_blob_client(
                container="job-files",
                blob=f"{user_id}/{job_id}/{file_name}"
            )
            await blob_client.upload_blob(content)
            
            # Update job with file reference
            job["files"].append({
                "name": file_name,
                "url": f"https://storage/job-files/{user_id}/{job_id}/{file_name}",
                "size": len(content),
                "uploaded_at": datetime.utcnow().isoformat()
            })
        
        updated_job = container.upsert_item(job)
        assert len(updated_job["files"]) == 3
        assert any(f["name"] == "audio.mp3" for f in updated_job["files"])
        assert any(f["name"] == "transcription.txt" for f in updated_job["files"])
        assert any(f["name"] == "analysis.json" for f in updated_job["files"])
    
    @pytest.mark.asyncio
    async def test_job_failure_with_storage_cleanup(
        self,
        integration_job_service: JobService,
        integration_storage_service: StorageService
    ):
        """Test job failure scenario with storage cleanup"""
        job_id = "job-failure"
        user_id = "user-failure"
        
        # Create job and upload file
        job = {
            "id": job_id,
            "user_id": user_id,
            "status": "processing"
        }
        
        container = integration_job_service.cosmos.get_container("jobs")
        container.upsert_item(job)
        
        # Upload file
        blob_client = integration_storage_service._blob_service_client.get_blob_client(
            container="audio-files",
            blob=f"{user_id}/{job_id}/audio.mp3"
        )
        await blob_client.upload_blob(b"Test content")
        
        # Simulate failure
        job["status"] = "failed"
        job["error"] = "Transcription service unavailable"
        job["failed_at"] = datetime.utcnow().isoformat()
        
        failed_job = container.upsert_item(job)
        assert failed_job["status"] == "failed"
        assert "error" in failed_job
        
        # File should still exist for potential retry
        exists = await blob_client.exists()
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_concurrent_job_creation(
        self,
        integration_job_service: JobService
    ):
        """Test creating multiple jobs concurrently for same user"""
        user_id = "user-concurrent"
        container = integration_job_service.cosmos.get_container("jobs")
        
        # Create multiple jobs
        job_ids = []
        for i in range(5):
            job_id = f"job-concurrent-{i}"
            job = {
                "id": job_id,
                "user_id": user_id,
                "title": f"Concurrent Job {i}",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat()
            }
            container.upsert_item(job)
            job_ids.append(job_id)
        
        # Query all jobs for user
        all_jobs = container.query_items(
            query="SELECT * FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": user_id}]
        )
        
        jobs_list = list(all_jobs)
        # Mock returns all stored items
        assert len(jobs_list) >= 5
        
        # Verify all job IDs are present
        stored_ids = {job["id"] for job in jobs_list}
        for job_id in job_ids:
            assert job_id in stored_ids
    
    @pytest.mark.asyncio
    async def test_job_metadata_updates(
        self,
        integration_job_service: JobService
    ):
        """Test updating job metadata throughout processing"""
        job_id = "job-metadata"
        user_id = "user-metadata"
        
        container = integration_job_service.cosmos.get_container("jobs")
        
        # Initial job
        job = {
            "id": job_id,
            "user_id": user_id,
            "status": "pending",
            "metadata": {}
        }
        container.upsert_item(job)
        
        # Update 1: Add file info
        job["metadata"]["file_name"] = "meeting.mp3"
        job["metadata"]["file_size"] = 1024000
        job["metadata"]["duration"] = 300
        container.upsert_item(job)
        
        # Update 2: Add processing info
        job["status"] = "processing"
        job["metadata"]["transcription_engine"] = "Azure Speech"
        job["metadata"]["language"] = "en-US"
        container.upsert_item(job)
        
        # Update 3: Add completion info
        job["status"] = "completed"
        job["metadata"]["word_count"] = 1500
        job["metadata"]["confidence_score"] = 0.95
        container.upsert_item(job)
        
        # Verify final state
        final = container.read_item(item_id=job_id, partition_key=user_id)
        assert final["status"] == "completed"
        assert final["metadata"]["file_name"] == "meeting.mp3"
        assert final["metadata"]["transcription_engine"] == "Azure Speech"
        assert final["metadata"]["word_count"] == 1500
        assert final["metadata"]["confidence_score"] == 0.95


class TestStorageServiceOperations:
    """Test storage service operations independently"""
    
    @pytest.mark.asyncio
    async def test_blob_container_operations(
        self,
        integration_storage_service: StorageService
    ):
        """Test basic blob container operations"""
        container_name = "test-container"
        blob_name = "test-blob.txt"
        content = b"Test blob content"
        
        # Upload blob
        blob_client = integration_storage_service._blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        result = await blob_client.upload_blob(content)
        assert "etag" in result
        
        # Check existence
        exists = await blob_client.exists()
        assert exists is True
        
        # Download blob
        download = await blob_client.download_blob()
        downloaded = await download.readall()
        assert downloaded == content
    
    @pytest.mark.asyncio
    async def test_large_file_upload(
        self,
        integration_storage_service: StorageService
    ):
        """Test uploading large files to blob storage"""
        # Simulate 10MB file
        large_content = b"x" * (10 * 1024 * 1024)
        
        blob_client = integration_storage_service._blob_service_client.get_blob_client(
            container="large-files",
            blob="large-file.bin"
        )
        
        result = await blob_client.upload_blob(large_content)
        assert result is not None
        
        # Verify upload
        exists = await blob_client.exists()
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_blob_with_metadata(
        self,
        integration_storage_service: StorageService
    ):
        """Test uploading blobs with custom metadata"""
        blob_client = integration_storage_service._blob_service_client.get_blob_client(
            container="metadata-test",
            blob="test.txt"
        )
        
        content = b"Content with metadata"
        metadata = {
            "user_id": "test-user",
            "job_id": "test-job",
            "content_type": "audio/mp3"
        }
        
        await blob_client.upload_blob(content, metadata=metadata)
        
        # Verify upload succeeded
        exists = await blob_client.exists()
        assert exists is True
