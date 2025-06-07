from typing import Dict, Any, Optional
from datetime import datetime
import logging
from azure.cosmos import CosmosClient
from config import AppConfig
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class CosmosServiceError(Exception):
    """Custom exception for Cosmos service errors."""
    pass

class CosmosService:
    def __init__(
        self,
        config: AppConfig,
        credential: DefaultAzureCredential = None,
        cosmos_client: CosmosClient = None,
    ) -> None:
        """Initialize the CosmosService with config, optional credential, and cosmos client."""
        self.config = config
        self.credential = (
            credential
            if credential is not None
            else DefaultAzureCredential(logging_enable=True)
        )
        self.client = (
            cosmos_client
            if cosmos_client is not None
            else CosmosClient(url=config.cosmos_endpoint, credential=self.credential)
        )
        self.database = self.client.get_database_client(config.cosmos_database)
        self.jobs_container = self.database.get_container_client(
            config.cosmos_jobs_container
        )
        self.prompts_container = self.database.get_container_client(
            config.cosmos_prompts_container
        )

    def get_file_by_blob_url(self, blob_url: str) -> Optional[Dict[str, Any]]:
        """Get file document by blob URL."""
        try:
            query = "SELECT * FROM c WHERE c.file_path = @file_path"
            files = list(
                self.jobs_container.query_items(
                    query=query,
                    parameters=[{"name": "@file_path", "value": blob_url}],
                    enable_cross_partition_query=True,
                )
            )
            return files[0] if files else None
        except Exception as e:
            logger.error(f"Error retrieving file by blob url: {str(e)}")
            raise CosmosServiceError(f"Error retrieving file by blob url: {str(e)}") from e

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        try:
            job = self.jobs_container.read_item(item=job_id, partition_key=job_id)
            return job if job else None
        except Exception as e:
            logger.error(f"Error retrieving job by id: {str(e)}")
            raise CosmosServiceError(f"Error retrieving job by id: {str(e)}") from e

    def update_job_status(
        self, job_id: str, status: str, **kwargs
    ) -> Dict[str, Any]:
        """Update job status and additional fields."""
        try:
            job = self.get_job_by_id(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            updates = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
                **kwargs,
            }
            job.update(updates)
            return self.jobs_container.upsert_item(body=job)
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
            raise CosmosServiceError(f"Error updating job status: {str(e)}") from e

    def get_prompts(self, subcategory_id: str) -> Dict[str, Any]:
        """Get prompts for a subcategory."""
        try:
            query = """
                SELECT * FROM c 
                WHERE c.type = 'prompt_subcategory' 
                AND c.id = @subcategory_id
            """
            prompts = list(
                self.prompts_container.query_items(
                    query=query,
                    parameters=[{"name": "@subcategory_id", "value": subcategory_id}],
                    enable_cross_partition_query=True,
                )
            )

            if not prompts:
                raise ValueError(f"No prompts found for subcategory: {subcategory_id}")

            # Get all prompts from the prompts object
            prompt_data = prompts[0].get("prompts", {})

            if not prompt_data:
                raise ValueError("No prompts found in subcategory")

            # Get the first (and only) value from the prompts object
            prompt_text = next(iter(prompt_data.values()))

            # Return the entire prompts object along with metadata
            return prompt_text

        except Exception as e:
            logger.error(f"Error retrieving prompts: {str(e)}")
            raise CosmosServiceError(f"Error retrieving prompts: {str(e)}") from e
