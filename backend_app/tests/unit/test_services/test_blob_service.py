"""
Unit tests for StorageService (BlobService).

Tests cover file upload operations, SAS token generation, DOCX generation,
blob streaming, error handling, and Azure Storage interactions.

Coverage target: 90%+
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open, MagicMock
from datetime import datetime, timedelta
from urllib.parse import urlparse
from io import BytesIO
import os

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions
from azure.identity import DefaultAzureCredential

from app.services.storage.blob_service import StorageService


# ============================================================================
# Test StorageService Initialization
# ============================================================================

class TestStorageServiceInitialization:
    """Test StorageService initialization with different credential types"""

    def test_init_with_storage_key(self, storage_config):
        """Should initialize with key-based authentication"""
        service = StorageService(storage_config)
        
        assert service.config == storage_config
        assert service.credential == storage_config.azure_storage_key
        assert service.blob_service_client is not None

    def test_init_with_managed_identity(self, storage_config):
        """Should initialize with managed identity when no key provided"""
        storage_config.azure_storage_key = None
        
        with patch('app.services.storage.blob_service.DefaultAzureCredential') as mock_cred:
            mock_cred.return_value = Mock()
            service = StorageService(storage_config)
            
            assert service.credential is not None
            assert isinstance(service.credential, Mock)
            mock_cred.assert_called_once()


# ============================================================================
# Test SAS Token Generation
# ============================================================================

class TestSASTokenGeneration:
    """Test SAS token generation for blob URLs"""

    def test_generate_sas_token_with_key_auth(self, storage_config):
        """Should generate SAS token using account key"""
        service = StorageService(storage_config)
        blob_url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
        
        with patch('app.services.storage.blob_service.generate_blob_sas') as mock_gen_sas:
            mock_gen_sas.return_value = "sv=2022-11-02&sr=b&sig=test-signature"
            
            sas_token = service.generate_sas_token(blob_url)
            
            assert sas_token is not None
            assert "sv=" in sas_token
            mock_gen_sas.assert_called_once()
            
            # Verify correct parameters
            call_kwargs = mock_gen_sas.call_args.kwargs
            assert call_kwargs['account_name'] == 'teststorage'
            assert call_kwargs['container_name'] == 'recordings'
            assert call_kwargs['blob_name'] == 'test.mp3'
            assert call_kwargs['account_key'] == storage_config.azure_storage_key

    def test_generate_sas_token_with_managed_identity(self, storage_config):
        """Should generate SAS token using user delegation key"""
        storage_config.azure_storage_key = None
        
        with patch('app.services.storage.blob_service.DefaultAzureCredential'):
            service = StorageService(storage_config)
            service.credential = Mock(spec=DefaultAzureCredential)
            
            # Mock user delegation key
            mock_delegation_key = Mock()
            service.blob_service_client.get_user_delegation_key = Mock(return_value=mock_delegation_key)
            
            blob_url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
            
            with patch('app.services.storage.blob_service.generate_blob_sas') as mock_gen_sas:
                mock_gen_sas.return_value = "sv=2022-11-02&sr=b&sig=test-signature"
                
                sas_token = service.generate_sas_token(blob_url)
                
                assert sas_token is not None
                service.blob_service_client.get_user_delegation_key.assert_called_once()
                mock_gen_sas.assert_called_once()
                
                # Verify user_delegation_key was passed
                call_kwargs = mock_gen_sas.call_args.kwargs
                assert 'user_delegation_key' in call_kwargs

    def test_generate_sas_token_empty_url(self, storage_config):
        """Should return None for empty blob URL"""
        service = StorageService(storage_config)
        
        sas_token = service.generate_sas_token("")
        assert sas_token is None
        
        sas_token = service.generate_sas_token(None)
        assert sas_token is None

    def test_generate_sas_token_invalid_url(self, storage_config):
        """Should return None for invalid blob URL"""
        service = StorageService(storage_config)
        
        # URL with only container, no blob name
        sas_token = service.generate_sas_token("https://teststorage.blob.core.windows.net/recordings")
        assert sas_token is None

    def test_generate_sas_token_error_handling(self, storage_config):
        """Should return None and log error on exception"""
        service = StorageService(storage_config)
        blob_url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
        
        with patch('app.services.storage.blob_service.generate_blob_sas') as mock_gen_sas:
            mock_gen_sas.side_effect = Exception("SAS generation failed")
            
            sas_token = service.generate_sas_token(blob_url)
            
            assert sas_token is None

    def test_add_sas_token_to_url_success(self, storage_config):
        """Should add SAS token to blob URL"""
        service = StorageService(storage_config)
        blob_url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
        
        with patch.object(service, 'generate_sas_token') as mock_gen:
            mock_gen.return_value = "sv=2022-11-02&sr=b&sig=test-signature"
            
            url_with_sas = service.add_sas_token_to_url(blob_url)
            
            assert url_with_sas == f"{blob_url}?sv=2022-11-02&sr=b&sig=test-signature"
            mock_gen.assert_called_once_with(blob_url)

    def test_add_sas_token_to_url_no_token_generated(self, storage_config):
        """Should return original URL if SAS token not generated"""
        service = StorageService(storage_config)
        blob_url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
        
        with patch.object(service, 'generate_sas_token') as mock_gen:
            mock_gen.return_value = None
            
            url_with_sas = service.add_sas_token_to_url(blob_url)
            
            assert url_with_sas == blob_url

    def test_add_sas_token_to_url_empty_url(self, storage_config):
        """Should return empty URL unchanged"""
        service = StorageService(storage_config)
        
        assert service.add_sas_token_to_url("") == ""
        assert service.add_sas_token_to_url(None) is None


# ============================================================================
# Test File Upload Operations
# ============================================================================

class TestFileUploadOperations:
    """Test file upload functionality"""

    def test_upload_file_success(self, storage_config, mock_blob_service_client):
        """Should successfully upload file to blob storage"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            # Create a temporary test file
            test_file_path = "test_audio.mp3"
            test_content = b"test audio content"
            
            with patch('builtins.open', mock_open(read_data=test_content)):
                with patch('app.services.storage.blob_service.datetime') as mock_datetime:
                    mock_now = Mock()
                    mock_now.strftime = Mock(side_effect=lambda fmt: "2025-10-08" if "Y" in fmt else "120530_123")
                    mock_datetime.now.return_value = mock_now
                    
                    blob_url = service.upload_file(test_file_path, "my test file.mp3")
                    
                    assert blob_url == "https://teststorage.blob.core.windows.net/recordings/test.mp3"
                    mock_blob_service_client.get_container_client.assert_called_once_with("recordings")
                    
                    # Verify blob name sanitization and structure
                    container_client = mock_blob_service_client.get_container_client.return_value
                    container_client.get_blob_client.assert_called_once()
                    
                    # Check that spaces were replaced with underscores
                    blob_name = container_client.get_blob_client.call_args[0][0]
                    assert " " not in blob_name
                    assert blob_name.startswith("2025-10-08/")

    def test_upload_file_sanitizes_filename(self, storage_config, mock_blob_service_client):
        """Should sanitize filename by replacing spaces with underscores"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            test_file_path = "test.mp3"
            
            with patch('builtins.open', mock_open(read_data=b"test")):
                with patch('app.services.storage.blob_service.datetime') as mock_datetime:
                    mock_now = Mock()
                    mock_now.strftime = Mock(side_effect=lambda fmt: "2025-10-08" if "Y" in fmt else "120530_123")
                    mock_datetime.now.return_value = mock_now
                    
                    service.upload_file(test_file_path, "my audio file with spaces.mp3")
                    
                    container_client = mock_blob_service_client.get_container_client.return_value
                    blob_name = container_client.get_blob_client.call_args[0][0]
                    
                    # Verify sanitization
                    assert "my_audio_file_with_spaces" in blob_name

    def test_upload_file_creates_timestamped_structure(self, storage_config, mock_blob_service_client):
        """Should create date-based folder structure with timestamp for uniqueness"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            test_file_path = "test.mp3"
            
            with patch('builtins.open', mock_open(read_data=b"test")):
                with patch('app.services.storage.blob_service.datetime') as mock_datetime:
                    mock_now = Mock()
                    # Two calls to strftime - first for date, second for timestamp
                    # strftime("%H%M%S_%f")[:-3] extracts last 3 digits from microseconds
                    def mock_strftime(fmt):
                        if "%Y" in fmt:
                            return "2025-10-08"
                        elif "%H" in fmt:
                            return "143022_456789"  # Will be sliced to "143022_456"
                    mock_now.strftime = mock_strftime
                    mock_datetime.now.return_value = mock_now
                    
                    service.upload_file(test_file_path, "audio.mp3")
                    
                    container_client = mock_blob_service_client.get_container_client.return_value
                    blob_name = container_client.get_blob_client.call_args[0][0]
                    
                    # Verify structure: YYYY-MM-DD/filename_timestamp/filename
                    # Note: timestamp = strftime("%H%M%S_%f")[:-3] so "143022_456789" becomes "143022_456"
                    assert blob_name.startswith("2025-10-08/audio_143022_")

    def test_upload_file_azure_error(self, storage_config, mock_blob_service_client):
        """Should raise AzureError on upload failure"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            # Mock upload to raise AzureError
            mock_blob_client = mock_blob_service_client.get_container_client.return_value.get_blob_client.return_value
            mock_blob_client.upload_blob = Mock(side_effect=AzureError("Storage unavailable"))
            
            with patch('builtins.open', mock_open(read_data=b"test")):
                with pytest.raises(AzureError):
                    service.upload_file("test.mp3", "test.mp3")

    def test_upload_file_general_exception(self, storage_config, mock_blob_service_client):
        """Should raise exception on unexpected error"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            # Mock file open to raise exception
            with patch('builtins.open', side_effect=IOError("File not found")):
                with pytest.raises(IOError):
                    service.upload_file("nonexistent.mp3", "nonexistent.mp3")


# ============================================================================
# Test DOCX Generation and Upload
# ============================================================================

class TestDOCXGenerationAndUpload:
    """Test DOCX document generation from analysis text"""

    def test_generate_and_upload_docx_success(self, storage_config, mock_blob_service_client):
        """Should generate DOCX from text and upload to blob storage"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            analysis_text = """
# Summary

This is the analysis summary.

## Key Points

- Point one
- Point two
- Point three
"""
            
            # Document is imported inside the method, so patch it there
            with patch('docx.Document') as mock_doc_cls:
                mock_doc = Mock()
                mock_doc_cls.return_value = mock_doc
                mock_doc.add_heading = Mock()
                mock_doc.add_paragraph = Mock()
                mock_doc.save = Mock()
                
                blob_url = service.generate_and_upload_docx(analysis_text, "report.docx")
                
                assert blob_url == "https://teststorage.blob.core.windows.net/recordings/test.mp3"
                mock_doc.add_heading.assert_called()  # Should add title
                mock_doc.add_paragraph.assert_called()  # Should add content
                
                # Verify blob client was called
                container_client = mock_blob_service_client.get_container_client.return_value
                container_client.get_blob_client.assert_called_with("report.docx")

    def test_generate_and_upload_docx_handles_markdown(self, storage_config, mock_blob_service_client):
        """Should properly parse and format markdown content"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            analysis_text = """
**Bold Section**

This is *italic* text with **bold** formatting.

- Bullet one
- Bullet two
"""
            
            # Document is imported inside the method
            with patch('docx.Document') as mock_doc_cls:
                mock_doc = Mock()
                mock_doc_cls.return_value = mock_doc
                mock_doc.add_heading = Mock()
                mock_doc.add_paragraph = Mock()
                mock_doc.save = Mock()
                
                service.generate_and_upload_docx(analysis_text, "report.docx")
                
                # Verify markdown was processed
                mock_doc.add_heading.assert_called()
                mock_doc.add_paragraph.assert_called()

    def test_generate_and_upload_docx_error_handling(self, storage_config, mock_blob_service_client):
        """Should raise exception on DOCX generation error"""
        with patch('app.services.storage.blob_service.BlobServiceClient', return_value=mock_blob_service_client):
            service = StorageService(storage_config)
            service.blob_service_client = mock_blob_service_client
            
            # Document is imported inside the method
            with patch('docx.Document', side_effect=ImportError("docx not installed")):
                with pytest.raises(ImportError):
                    service.generate_and_upload_docx("test text", "report.docx")


# ============================================================================
# Test Blob Streaming
# ============================================================================

class TestBlobStreaming:
    """Test async blob content streaming"""

    @pytest.mark.asyncio
    async def test_stream_blob_content_success(self, storage_config):
        """Should stream blob content in chunks"""
        with patch('app.services.storage.blob_service.BlobServiceClient'):
            service = StorageService(storage_config)
            
            blob_url = "https://teststorage.blob.core.windows.net/recordings/2025-10-08/test_audio/test.mp3"
            
            with patch('app.services.storage.blob_service.AsyncBlobClient') as mock_async_client_cls:
                # Setup mock async blob client
                mock_async_client = AsyncMock()
                mock_async_client_cls.return_value = mock_async_client
                
                # Mock downloader with chunks
                mock_downloader = AsyncMock()
                async def mock_chunks():
                    yield b"chunk1"
                    yield b"chunk2"
                    yield b"chunk3"
                mock_downloader.chunks = mock_chunks
                
                mock_async_client.download_blob = AsyncMock(return_value=mock_downloader)
                mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
                mock_async_client.__aexit__ = AsyncMock(return_value=None)
                
                # Stream and collect chunks
                chunks = []
                async for chunk in service.stream_blob_content(blob_url):
                    chunks.append(chunk)
                
                assert len(chunks) == 3
                assert chunks[0] == b"chunk1"
                assert chunks[1] == b"chunk2"
                assert chunks[2] == b"chunk3"

    @pytest.mark.asyncio
    async def test_stream_blob_content_empty_url(self, storage_config):
        """Should raise ValueError for empty URL"""
        with patch('app.services.storage.blob_service.BlobServiceClient'):
            service = StorageService(storage_config)
            
            with pytest.raises(ValueError, match="Blob URL cannot be empty"):
                async for _ in service.stream_blob_content(""):
                    pass

    @pytest.mark.asyncio
    async def test_stream_blob_content_invalid_url(self, storage_config):
        """Should raise ValueError for invalid URL"""
        with patch('app.services.storage.blob_service.BlobServiceClient'):
            service = StorageService(storage_config)
            
            # Error message varies: "Invalid blob URL" or "Blob URL path format not recognized"
            with pytest.raises(ValueError):
                async for _ in service.stream_blob_content("https://teststorage.blob.core.windows.net/"):
                    pass

    @pytest.mark.asyncio
    async def test_stream_blob_content_blob_not_found(self, storage_config):
        """Should raise ResourceNotFoundError for non-existent blob"""
        with patch('app.services.storage.blob_service.BlobServiceClient'):
            service = StorageService(storage_config)
            
            blob_url = "https://teststorage.blob.core.windows.net/recordings/nonexistent.mp3"
            
            with patch('app.services.storage.blob_service.AsyncBlobClient') as mock_async_client_cls:
                mock_async_client = AsyncMock()
                mock_async_client_cls.return_value = mock_async_client
                
                mock_async_client.download_blob = AsyncMock(side_effect=ResourceNotFoundError("Blob not found"))
                mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
                mock_async_client.__aexit__ = AsyncMock(return_value=None)
                
                with pytest.raises(ResourceNotFoundError):
                    async for _ in service.stream_blob_content(blob_url):
                        pass

    @pytest.mark.asyncio
    async def test_stream_blob_content_different_container(self, storage_config):
        """Should handle blobs from different containers"""
        with patch('app.services.storage.blob_service.BlobServiceClient'):
            service = StorageService(storage_config)
            
            # URL with different container
            blob_url = "https://teststorage.blob.core.windows.net/transcriptions/test.json"
            
            with patch('app.services.storage.blob_service.AsyncBlobClient') as mock_async_client_cls:
                mock_async_client = AsyncMock()
                mock_async_client_cls.return_value = mock_async_client
                
                mock_downloader = AsyncMock()
                async def mock_chunks():
                    yield b"data"
                mock_downloader.chunks = mock_chunks
                
                mock_async_client.download_blob = AsyncMock(return_value=mock_downloader)
                mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
                mock_async_client.__aexit__ = AsyncMock(return_value=None)
                
                # Should extract container and blob name from URL
                chunks = []
                async for chunk in service.stream_blob_content(blob_url):
                    chunks.append(chunk)
                
                assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_stream_blob_content_unexpected_error(self, storage_config):
        """Should raise exception on unexpected error"""
        with patch('app.services.storage.blob_service.BlobServiceClient'):
            service = StorageService(storage_config)
            
            blob_url = "https://teststorage.blob.core.windows.net/recordings/test.mp3"
            
            with patch('app.services.storage.blob_service.AsyncBlobClient') as mock_async_client_cls:
                mock_async_client = AsyncMock()
                mock_async_client_cls.return_value = mock_async_client
                
                mock_async_client.download_blob = AsyncMock(side_effect=Exception("Unexpected error"))
                mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
                mock_async_client.__aexit__ = AsyncMock(return_value=None)
                
                with pytest.raises(Exception, match="Unexpected error"):
                    async for _ in service.stream_blob_content(blob_url):
                        pass


# ============================================================================
# Test Service Properties
# ============================================================================

class TestServiceProperties:
    """Test service properties and configuration"""

    def test_service_has_logger(self, storage_config):
        """Should have logger configured"""
        service = StorageService(storage_config)
        assert service.logger is not None

    def test_service_has_config(self, storage_config):
        """Should store configuration"""
        service = StorageService(storage_config)
        assert service.config == storage_config

    def test_service_has_blob_service_client(self, storage_config):
        """Should initialize BlobServiceClient"""
        service = StorageService(storage_config)
        assert service.blob_service_client is not None
