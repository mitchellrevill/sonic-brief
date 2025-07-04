import os
import logging
from typing import Optional
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError
from datetime import datetime, timedelta
from urllib.parse import urlparse

from config import AppConfig

logger = logging.getLogger(__name__)


class StorageServiceError(Exception):
    """Custom exception for storage service errors."""
    pass

class StorageService:
    def __init__(self, config: AppConfig, credential: DefaultAzureCredential = None, blob_service_client: BlobServiceClient = None) -> None:
        """Initialize the StorageService with config, optional credential, and blob service client."""
        self.config = config
        self.credential = credential if credential is not None else DefaultAzureCredential()

        # Initialize blob service client
        self.blob_service_client = blob_service_client if blob_service_client is not None else BlobServiceClient(
            account_url=self.config.storage_account_url,
            credential=self.credential,
        )

    def upload_file(self, file_path: str, original_filename: str) -> str:
        """Upload a file to blob storage and return the blob URL."""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.storage_recordings_container
            )            # Generate blob name with date and nested structure including timestamp for uniqueness
            current_date = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]  # HHMMSS_milliseconds
            file_name_without_ext = os.path.splitext(original_filename)[0]
            # Include timestamp in both folder and filename to ensure uniqueness
            blob_name = f"{current_date}/{file_name_without_ext}_{timestamp}/{original_filename}"

            blob_client = container_client.get_blob_client(blob_name)

            # Upload the file
            logger.info(f"Uploading file to blob storage: {blob_name}")
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            return blob_client.url

        except AzureError as e:
            logger.error(f"Azure storage error: {str(e)}")
            raise StorageServiceError(f"Azure storage error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise StorageServiceError(f"Error uploading file: {str(e)}") from e

    def upload_text(
        self, container_name: str, blob_name: str, text_content: str
    ) -> str:
        """Upload text content to blob storage and return the blob URL."""
        try:
            container_client = self.blob_service_client.get_container_client(
                container_name
            )
            blob_client = container_client.get_blob_client(blob_name)

            blob_client.upload_blob(text_content.encode("utf-8"), overwrite=True)
            return blob_client.url
        except Exception as e:
            logger.error(f"Error uploading text: {str(e)}")
            raise StorageServiceError(f"Error uploading text: {str(e)}") from e

    def generate_and_upload_pdf(self, analysis_text: str, blob_url: str) -> str:
        """Generate a PDF from analysis text and upload to blob storage. Return the blob URL."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            import io

            # Create PDF in memory
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)

            # Add content to PDF
            y = 750  # Starting y position
            for line in analysis_text.split("\n"):
                if y < 50:  # Start new page if near bottom
                    c.showPage()
                    y = 750
                c.drawString(50, y, line)
                y -= 15

            c.save()
            pdf_content = buffer.getvalue()

            # Upload PDF
            container_client = self.blob_service_client.get_container_client(
                self.config.storage_recordings_container
            )
            blob_client = container_client.get_blob_client(blob_url)

            blob_client.upload_blob(pdf_content, overwrite=True)
            return blob_client.url

        except Exception as e:
            logger.error(f"Error generating/uploading PDF: {str(e)}")
            raise StorageServiceError(f"Error generating/uploading PDF: {str(e)}") from e
