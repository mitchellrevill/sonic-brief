import os
import json
import time
import logging
from typing import Optional
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


AZURE_STORAGE_ACCOUNT_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
AZURE_STORAGE_RECORDINGS_CONTAINER = os.getenv("AZURE_STORAGE_RECORDINGS_CONTAINER", "recordingcontainer")
AUDIO_FOLDER = os.getenv("AUDIO_FOLDER", "audios")
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=AZURE_STORAGE_ACCOUNT_URL, credential=credential)

# Configure logging for the module (you can adjust as needed)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_blob_client(blob_name: str, container_name: str = AZURE_STORAGE_RECORDINGS_CONTAINER):
    """
    Return the BlobClient for a given blob name within a container.
    """
    return blob_service_client.get_blob_client(container=container_name, blob=blob_name)

# azure_storage.py  ───────────────
def download_blob_to_local_file(blob_name: str,
                                local_path: Optional[str] = None,
                                overwrite: bool = False,
                                max_retries: int = 5,
                                initial_backoff: float = 1.0) -> str:
    """Download a blob to a local file with logging and retry/backoff."""
    logger.info(f"Resolved blob_name: {blob_name}")
    logger.info(f"Resolved local_path: {local_path}")
    logger.info(f"Resolved AZURE_STORAGE_ACCOUNT_URL: {AZURE_STORAGE_ACCOUNT_URL}")
    logger.info(f"Resolved AZURE_STORAGE_RECORDINGS_CONTAINER: {AZURE_STORAGE_RECORDINGS_CONTAINER}")
    if not local_path:
        local_path = os.path.join('/tmp', os.path.basename(blob_name))
    else:
        # Force caller-supplied path into /tmp, to stay writable
        local_path = os.path.join('/tmp', os.path.basename(local_path))

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    logger.info(f"Resolved local path: {local_path}")
    print(f"[INFO] Resolved local path: {local_path}")

    if not overwrite and os.path.exists(local_path):
        logger.info(f"File already exists at {local_path} and overwrite is False. Skipping download.")
        print(f"[INFO] File exists at {local_path}, skipping.")
        return local_path

    attempt = 0
    backoff = initial_backoff

    while attempt < max_retries:
        try:
            logger.info(f"Attempting to download blob '{blob_name}' (attempt {attempt+1}/{max_retries})...")
            print(f"[INFO] Downloading blob '{blob_name}' (attempt {attempt+1}/{max_retries})...")

            client = get_blob_client(blob_name)  # Assumed function

            if client.exists():
                with open(local_path, "wb") as download_file:
                    download_file.write(client.download_blob().readall())
                print(f"Downloaded to {local_path}")
            else:
                print(f"Blob '{blob_name}' does not exist in container '{AZURE_STORAGE_RECORDINGS_CONTAINER}' SA: {AZURE_STORAGE_ACCOUNT_URL}.")


            logger.info(f"Downloaded blob '{blob_name}' to '{local_path}'.")
            print(f"[SUCCESS] Downloaded '{blob_name}' to '{local_path}'.")
            return local_path

        except Exception as e:
            logger.error(f"Failed to download blob '{blob_name}' on attempt {attempt+1}: {e}", exc_info=True)
            print(f"[ERROR] Attempt {attempt+1} failed: {e}")
            attempt += 1
            if attempt < max_retries:
                logger.info(f"Retrying in {backoff} seconds...")
                print(f"[INFO] Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries} attempts failed.")
                print(f"[FAIL] All {max_retries} attempts failed.")
                raise  # Reraise the last exception

    return local_path  # This line should never be reached


def download_audio_to_local_file(blob_name):
    return download_blob_to_local_file(blob_name)