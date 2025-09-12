"""
Background Processing Service for handling long-running operations with retry logic and circuit breaker patterns.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
import json
from contextlib import asynccontextmanager

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
    RetryError
)
import httpx
from fastapi import BackgroundTasks

from ...core.config import AppConfig, get_cosmos_db_cached
from ..storage.blob_service import StorageService
from ..content import AnalyticsService

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class BackgroundTask:
    """Represents a background task with status tracking."""
    
    def __init__(self, task_id: str, task_type: str, user_id: str, metadata: Dict[str, Any] = None):
        self.task_id = task_id
        self.task_type = task_type
        self.user_id = user_id
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = self.created_at
        self.metadata = metadata or {}
        self.error_message = None
        self.retry_count = 0
        self.max_retries = 3
        self.result = None

    def update_status(self, status: TaskStatus, error_message: str = None, result: Any = None):
        """Update task status and metadata."""
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
        if error_message:
            self.error_message = error_message
        if result is not None:
            self.result = result
        logger.info(f"Task {self.task_id} status updated to {status.value}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result
        }

class CircuitBreaker:
    """Simple circuit breaker implementation for Azure Functions calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == "OPEN":
            if datetime.now().timestamp() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker transitioning to HALF_OPEN state")
                return False
            return True
        return False
    
    def record_success(self):
        """Record a successful operation."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker transitioning to CLOSED state")
    
    def record_failure(self):
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker OPEN after {self.failure_count} failures")

class BackgroundProcessingService:
    """Service for handling background processing with retry logic and circuit breaker patterns."""
    
    def __init__(self, storage_service: StorageService, config: AppConfig):
        self.storage_service = storage_service
        self.config = config
        self.tasks: Dict[str, BackgroundTask] = {}
        self.circuit_breaker = CircuitBreaker()
        
    async def submit_task(
        self, 
        task_id: str, 
        task_type: str, 
        user_id: str, 
        task_func: Callable,
        background_tasks: BackgroundTasks,
        metadata: Dict[str, Any] = None,
        *args, 
        **kwargs
    ) -> BackgroundTask:
        """Submit a task for background processing."""
        task = BackgroundTask(task_id, task_type, user_id, metadata)
        self.tasks[task_id] = task
        
        # Add the task to FastAPI's background tasks
        background_tasks.add_task(
            self._execute_task_with_retry,
            task,
            task_func,
            *args,
            **kwargs
        )
        
        logger.info(f"Submitted background task {task_id} of type {task_type}")
        return task
    
    async def _execute_task_with_retry(
        self, 
        task: BackgroundTask, 
        task_func: Callable, 
        *args, 
        **kwargs
    ):
        """Execute a task with retry logic."""
        task.update_status(TaskStatus.RUNNING)
        
        try:
            result = await self._retry_with_circuit_breaker(task_func, *args, **kwargs)
            task.update_status(TaskStatus.COMPLETED, result=result)
            logger.info(f"Task {task.task_id} completed successfully")
            
        except RetryError as e:
            error_msg = f"Task failed after all retries: {str(e)}"
            task.update_status(TaskStatus.FAILED, error_message=error_msg)
            logger.error(f"Task {task.task_id} failed permanently: {error_msg}")
            
        except Exception as e:
            error_msg = f"Unexpected error in task execution: {str(e)}"
            task.update_status(TaskStatus.FAILED, error_message=error_msg)
            logger.error(f"Task {task.task_id} failed with unexpected error: {error_msg}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )
    async def _retry_with_circuit_breaker(self, task_func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.circuit_breaker.is_open():
            raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = await task_func(*args, **kwargs)
            self.circuit_breaker.record_success()
            return result
            
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Function execution failed: {str(e)}")
            raise
    
    async def call_azure_function(
        self, 
        function_url: str, 
        payload: Dict[str, Any],
        headers: Dict[str, str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Make a resilient call to Azure Functions with retry and circuit breaker."""
        if self.circuit_breaker.is_open():
            raise Exception("Azure Functions service unavailable - circuit breaker is OPEN")
        
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "SonicBrief-Backend/1.0"
        }
        if headers:
            default_headers.update(headers)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    function_url,
                    json=payload,
                    headers=default_headers
                )
                response.raise_for_status()
                
                self.circuit_breaker.record_success()
                return response.json()
                
            except httpx.HTTPError as e:
                self.circuit_breaker.record_failure()
                logger.error(f"Azure Function call failed: {str(e)}")
                raise
            except Exception as e:
                self.circuit_breaker.record_failure()
                logger.error(f"Unexpected error calling Azure Function: {str(e)}")
                raise
    
    async def process_audio_analysis(
        self, 
        file_path: str, 
        job_id: str, 
        user_id: str,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Process audio analysis using Azure Functions."""
        logger.info(f"Starting audio analysis for job {job_id}")
          # Prepare payload for Azure Function
        payload = {
            "file_path": file_path,
            "job_id": job_id,
            "user_id": user_id,
            "analysis_type": analysis_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Call Azure Function for audio analysis
        function_url = f"{self.config.azure_functions_base_url}/api/analyze-audio"
        result = await self.call_azure_function(function_url, payload)
        
        logger.info(f"Audio analysis completed for job {job_id}")
        return result
    
    async def process_text_refinement(
        self, 
        text: str, 
        refinement_prompt: str,
        job_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process text refinement using Azure Functions."""
        logger.info(f"Starting text refinement for job {job_id}")
        
        payload = {
            "text": text,
            "refinement_prompt": refinement_prompt,
            "job_id": job_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        function_url = f"{self.config.azure_functions_base_url}/api/refine-text"
        result = await self.call_azure_function(function_url, payload)
        
        logger.info(f"Text refinement completed for job {job_id}")
        return result
    
    async def perform_text_analysis(self, job_id: str):
        """Legacy method to perform text analysis for compatibility."""
        try:
            logger.info(f"Starting legacy text analysis for job {job_id}")
            
            # Get job details from database
            
            cosmos_db = get_cosmos_db_cached(self.config)
            job = cosmos_db.get_job(job_id)
            
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            # Update job status
            update_fields = {
                "status": "analyzing",
                "message": "Processing text analysis...",
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            cosmos_db.update_job(job_id, update_fields)
            
            # Call Azure Function for analysis (placeholder - adapt based on your actual Azure Function)
            payload = {
                "job_id": job_id,
                "user_id": job.get("user_id"),
                "content": job.get("content", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            function_url = f"{self.config.azure_functions_base_url}/api/analyze-text"
            result = await self.call_azure_function(function_url, payload, timeout=120)
            
            # Update job with results
            start_time = job.get("created_at", 0)
            end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            duration_seconds = (end_time - start_time) / 1000.0 if start_time else 0
            
            update_fields = {
                "status": "completed",
                "message": "Analysis completed successfully",
                "analysis_result": result,
                "updated_at": end_time,
            }
            cosmos_db.update_job(job_id, update_fields)
            
            # Track job completion analytics
            try:
                analytics_service = AnalyticsService(cosmos_db)
                
                # Include audio duration in completion analytics if available
                completion_metadata = {
                    "duration_seconds": duration_seconds,
                    "transcription_method": job.get("transcription_method", "unknown"),
                    "content_length": len(job.get("content", "")),
                    "analysis_type": "text"
                }
                
                # Include audio duration if stored in job record
                if job.get("audio_duration_seconds"):
                    completion_metadata["audio_duration_seconds"] = job["audio_duration_seconds"]
                    completion_metadata["audio_duration_minutes"] = job.get("audio_duration_minutes", job["audio_duration_seconds"] / 60.0)
                
                await analytics_service.track_job_event(
                    job_id=job_id,
                    user_id=job.get("user_id"),
                    event_type="job_completed",
                    metadata=completion_metadata
                )
            except Exception as e:
                logger.warning(f"Failed to track job completion analytics: {str(e)}")
            
            logger.info(f"Text analysis completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error in text analysis for job {job_id}: {str(e)}")
            
            # Update job with error status
            try:
                
                cosmos_db = get_cosmos_db_cached(self.config)
                update_fields = {
                    "status": "failed",
                    "message": f"Analysis failed: {str(e)}",
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                cosmos_db.update_job(job_id, update_fields)
            except Exception as db_error:
                logger.error(f"Failed to update job status after error: {str(db_error)}")
    
    async def process_file_upload(self, file, job_id: str, config):
        """Process file upload in background."""
        import tempfile
        import os
        from azure.core.exceptions import AzureError
        
        try:
            logger.info(f"Starting background file upload for job {job_id}")
            
            # Initialize services
            
            cosmos_db = get_cosmos_db_cached(self.config)
            
            # Update job status to uploading
            update_fields = {
                "status": "uploading",
                "message": "Uploading file to storage...",
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            cosmos_db.update_job(job_id, update_fields)
            
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(file.filename)[1]
            ) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Upload file to blob storage
            blob_url = self.storage_service.upload_file(temp_file_path, file.filename)
            logger.info(f"File uploaded to blob storage: {blob_url}")

            # Clean up temporary file
            os.unlink(temp_file_path)
            
            # Update job with file path and status
            update_fields = {
                "status": "uploaded",
                "message": "File uploaded successfully, waiting for transcription",
                "file_path": blob_url,
                "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
            }
            cosmos_db.update_job(job_id, update_fields)
            
            logger.info(f"File upload completed for job {job_id}")
            
        except AzureError as e:
            logger.error(f"Storage error for job {job_id}: {str(e)}")
            
            # Update job with error status
            try:
                update_fields = {
                    "status": "failed",
                    "message": f"Storage service unavailable: {str(e)}",
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                cosmos_db.update_job(job_id, update_fields)
            except Exception as db_error:
                logger.error(f"Failed to update job status after storage error: {str(db_error)}")
        except Exception as e:
            logger.error(f"Error in file upload for job {job_id}: {str(e)}")
            
            # Update job with error status
            try:
                
                cosmos_db = get_cosmos_db_cached(self.config)
                update_fields = {
                    "status": "failed",
                    "message": f"File upload failed: {str(e)}",
                    "updated_at": int(datetime.now(timezone.utc).timestamp() * 1000),
                }
                cosmos_db.update_job(job_id, update_fields)
            except Exception as db_error:
                logger.error(f"Failed to update job status after upload error: {str(db_error)}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a background task."""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None
    
    def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all tasks for a specific user."""
        user_tasks = [
            task.to_dict() 
            for task in self.tasks.values() 
            if task.user_id == user_id
        ]
        return sorted(user_tasks, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up tasks older than specified hours."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        tasks_to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.created_at.timestamp() < cutoff_time and 
            task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
        ]
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            
        if tasks_to_remove:
            logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "failure_threshold": self.circuit_breaker.failure_threshold,
            "last_failure_time": self.circuit_breaker.last_failure_time,
            "recovery_timeout": self.circuit_breaker.recovery_timeout
        }

# Global service instance
_background_service: Optional[BackgroundProcessingService] = None

def get_background_service() -> BackgroundProcessingService:
    """Get the global background processing service instance."""
    global _background_service
    if _background_service is None:
        raise RuntimeError("Background service not initialized. Call initialize_background_service() first.")
    return _background_service

def initialize_background_service(storage_service: StorageService, config: AppConfig):
    """Initialize the global background processing service."""
    global _background_service
    _background_service = BackgroundProcessingService(storage_service, config)
    logger.info("Background processing service initialized")

async def cleanup_background_service():
    """Cleanup background service resources."""
    global _background_service
    if _background_service:
        _background_service.cleanup_old_tasks()
        logger.info("Background processing service cleaned up")
