from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from datetime import datetime, timezone
import logging

from ...core.config import get_config
from ...core.dependencies import CosmosService
from ..storage.blob_service import StorageService
import uuid
from ...utils.async_utils import run_sync

logger = logging.getLogger(__name__)


class JobService:
    """Encapsulates job-related DB access and light enrichment (SAS tokens, metadata).

    Designed to be used as a lightweight per-request instance created via DI.
    """

    def __init__(self, cosmos_service: CosmosService, storage_service: StorageService):
        self.cosmos = cosmos_service
        self.storage = storage_service

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.cosmos.get_job(job_id)
        except Exception:
            return None

    async def async_get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return await run_sync(lambda: self.get_job(job_id))

    def query_jobs(self, query: str, parameters: List[Dict[str, Any]]):
        return list(self.cosmos.jobs_container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

    async def async_query_jobs(self, query: str, parameters: List[Dict[str, Any]]):
        return await run_sync(lambda: self.query_jobs(query, parameters))

    def enrich_job_file_urls(self, job: Dict[str, Any]):
        if job.get("file_path"):
            file_path = job["file_path"]
            path_parts = urlparse(file_path).path.strip("/").split("/")
            job["file_name"] = path_parts[-1] if path_parts else None
            job["file_path"] = self.storage.add_sas_token_to_url(file_path)
        # Provide a stable alias expected by some frontend pages (e.g. admin/Deleted recordings)
        # Without overwriting existing explicit values if already set differently.
        if job.get("file_name") and not job.get("filename"):
            job["filename"] = job["file_name"]
        # Add displayname fallback: use stored displayname, or fallback to file_name, or filename
        if not job.get("displayname"):
            job["displayname"] = job.get("file_name") or job.get("filename") or "Untitled Recording"
        if job.get("transcription_file_path"):
            job["transcription_file_path"] = self.storage.add_sas_token_to_url(job["transcription_file_path"])
        if job.get("analysis_file_path"):
            job["analysis_file_path"] = self.storage.add_sas_token_to_url(job["analysis_file_path"])
        return job

    def close(self):
        # No persistent resources to close, but provide hook for DI resets
        logger.info("JobService.close: no resources to close")

    def upload_and_create_job(self, file_path: str, original_filename: str, owner_user: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Upload a file to storage and create a minimal job record in Cosmos.

        Returns the created job document.
        """
        if metadata is None:
            metadata = {}

        # Upload file to blob storage
        blob_url = self.storage.upload_file(file_path, original_filename)

        # Build job document
        job_doc = {
            # Ensure Cosmos DB required 'id' is present
            "id": str(uuid.uuid4()),
            "type": "job",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": owner_user.get("id"),
            "user_email": owner_user.get("email"),
            "file_name": original_filename,
            "file_path": blob_url,
            "status": "uploaded",
        }

        # Merge additional metadata if provided
        job_doc.update(metadata)

        # Persist to Cosmos (uses cosmos helper if available)
        try:
            created = self.cosmos.create_job(job_doc)
            # Enrich returned document with SAS tokens
            self.enrich_job_file_urls(created)
            return created
        except Exception as e:
            logger.error(f"Failed to create job document after upload: {str(e)}")
            # On failure, attempt best-effort cleanup: remove uploaded blob is intentionally omitted
            raise

    async def async_upload_and_create_job(self, file_path: str, original_filename: str, owner_user: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        return await run_sync(lambda: self.upload_and_create_job(file_path, original_filename, owner_user, metadata))
