import os
import logging
from typing import Optional
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError
from datetime import datetime, timedelta
from urllib.parse import urlparse

from app.core.config import AppConfig


class StorageService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.credential = DefaultAzureCredential()

        # Initialize blob service client
        self.blob_service_client = BlobServiceClient(
            account_url=self.config.storage.account_url, credential=self.credential
        )

    def generate_sas_token(self, blob_url: str) -> Optional[str]:
        """Generate SAS token for a blob URL using managed identity"""
        try:
            if not blob_url:
                return None

            # Parse blob URL to get container and blob name
            parsed_url = urlparse(blob_url)
            path_parts = parsed_url.path.strip("/").split("/")
            if len(path_parts) < 2:
                return None

            container_name = path_parts[0]
            blob_name = "/".join(path_parts[1:])

            # Get user delegation key using managed identity
            user_delegation_key = self.blob_service_client.get_user_delegation_key(
                key_start_time=datetime.utcnow() - timedelta(minutes=5),
                key_expiry_time=datetime.utcnow() + timedelta(hours=8),
            )

            # Generate SAS token using user delegation key
            sas_token = generate_blob_sas(
                account_name=parsed_url.netloc.split(".")[0],
                container_name=container_name,
                blob_name=blob_name,
                user_delegation_key=user_delegation_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=8),
            )

            return sas_token

        except Exception as e:
            self.logger.error(f"Error generating SAS token: {str(e)}")
            return None

    def add_sas_token_to_url(self, blob_url: str) -> str:
        """Add SAS token to blob URL if not already present"""
        if not blob_url:
            return blob_url

        sas_token = self.generate_sas_token(blob_url)
        if sas_token:
            return f"{blob_url}?{sas_token}"
        return blob_url

    def upload_file(self, file_path: str, original_filename: str) -> str:
        """Upload a file to blob storage"""
        try:
            container_client = self.blob_service_client.get_container_client(
                self.config.storage.recordings_container
            )

            # Generate blob name with date and nested structure
            current_date = datetime.now().strftime("%Y-%m-%d")
            file_name_without_ext = os.path.splitext(original_filename)[0]
            blob_name = f"{current_date}/{file_name_without_ext}/{original_filename}"

            blob_client = container_client.get_blob_client(blob_name)

            # Upload the file
            self.logger.info(f"Uploading file to blob storage: {blob_name}")
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            return blob_client.url

        except AzureError as e:
            self.logger.error(f"Azure storage error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error uploading file: {str(e)}")
            raise
