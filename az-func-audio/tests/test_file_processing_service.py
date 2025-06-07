import os
import pytest
from unittest.mock import patch, MagicMock
from config import AppConfig
from services.file_processing_service import FileProcessingService, SYSTEM_GENERATED_TAG

# Dummy blob URL generator for test purposes
def make_blob_url(container, blob):
    # This should match the expected Azure blob URL format in your service
    account_url = os.environ.get('TEST_STORAGE_ACCOUNT_URL', 'https://dummyaccount.blob.core.windows.net')
    return f"{account_url}/{container}/{blob}"

@pytest.fixture
def file_processing_service():
    config = AppConfig()
    # Patch StorageService and DefaultAzureCredential to avoid Azure calls
    with patch('file_processing_service.StorageService', MagicMock()), \
         patch('file_processing_service.DefaultAzureCredential', MagicMock()), \
         patch('file_processing_service.BlobServiceClient', MagicMock()):
        yield FileProcessingService(config)

def test_get_file_type(file_processing_service):
    # Test various file extensions
    assert file_processing_service.get_file_type('.txt') == 'text'
    assert file_processing_service.get_file_type('.srt') == 'text'
    assert file_processing_service.get_file_type('.vtt') == 'text'
    assert file_processing_service.get_file_type('.json') == 'text'
    assert file_processing_service.get_file_type('.pdf') == 'document'
    assert file_processing_service.get_file_type('.docx') == 'document'
    assert file_processing_service.get_file_type('.doc') == 'document'
    assert file_processing_service.get_file_type('.mp3') == 'audio'
    assert file_processing_service.get_file_type('.wav') == 'audio'
    assert file_processing_service.get_file_type('.jpg') == 'image'
    assert file_processing_service.get_file_type('.unknown') == 'unsupported'

def test_is_system_generated_file():
    from services.file_processing_service import FileProcessingService
    assert FileProcessingService.is_system_generated_file(f"foo_{SYSTEM_GENERATED_TAG}_bar.txt")
    assert FileProcessingService.is_system_generated_file(f"{SYSTEM_GENERATED_TAG}_file.txt")
    assert not FileProcessingService.is_system_generated_file("user_uploaded_file.txt")
    assert not FileProcessingService.is_system_generated_file("foo_bar.txt")

# You can add more tests for process_file if you have test blobs or mock the blob download methods.
# For now, this test focuses on file type detection logic.
