#!/usr/bin/env python3
"""
Unit tests for DocumentProcessingService
"""
import os
import sys
import unittest
import tempfile
import io
from unittest.mock import patch, MagicMock, Mock

# Add the parent directory to the system path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from config import AppConfig
from document_processing_service import DocumentProcessingService
from azure.identity import DefaultAzureCredential

# Load test environment
load_dotenv(dotenv_path=".env")

class TestDocumentProcessingService(unittest.TestCase):
    """Test cases for DocumentProcessingService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = AppConfig()
        self.service = DocumentProcessingService(self.config)
    
    def test_service_initialization(self):
        """Test that the service initializes correctly"""
        self.assertIsInstance(self.service.config, AppConfig)
        self.assertIsNotNone(self.service.logger)
        self.assertIsNotNone(self.service.storage_service)
        self.assertIsInstance(self.service.credential, DefaultAzureCredential)
    
    def test_is_document_file_valid_extensions(self):
        """Test document file type detection for valid extensions"""
        valid_extensions = ['.pdf', '.doc', '.docx', '.rtf']
        
        for ext in valid_extensions:
            with self.subTest(extension=ext):
                result = self.service.is_document_file(ext)
                self.assertTrue(result, f"Extension {ext} should be recognized as document")
    
    def test_is_document_file_invalid_extensions(self):
        """Test document file type detection for invalid extensions"""
        invalid_extensions = ['.txt', '.mp3', '.jpg', '.wav', '.json', '.unknown']
        
        for ext in invalid_extensions:
            with self.subTest(extension=ext):
                result = self.service.is_document_file(ext)
                self.assertFalse(result, f"Extension {ext} should not be recognized as document")
    
    def test_is_document_file_case_insensitive(self):
        """Test that file extension detection is case insensitive"""
        test_cases = [
            ('.PDF', True),
            ('.Pdf', True),
            ('.DOCX', True),
            ('.DocX', True),
            ('.DOC', True),
            ('.RTF', True),
            ('.TXT', False),
            ('.MP3', False)
        ]
        
        for ext, expected in test_cases:
            with self.subTest(extension=ext):
                result = self.service.is_document_file(ext)
                self.assertEqual(result, expected, f"Extension {ext} detection failed")
    
    def test_get_supported_formats_info(self):
        """Test that supported formats info is returned correctly"""
        info = self.service.get_supported_formats_info()
        
        # Check structure
        self.assertIn('audio_formats', info)
        self.assertIn('text_formats', info)
        self.assertIn('document_formats', info)
        self.assertIn('image_formats', info)
        
        # Check document formats
        doc_info = info['document_formats']
        self.assertIn('supported', doc_info)
        self.assertIn('processing', doc_info)
        self.assertIn('extensions', doc_info)
        
        # Check that document extensions are listed
        expected_doc_exts = ['.pdf', '.doc', '.docx']
        self.assertEqual(doc_info['extensions'], expected_doc_exts)
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', False)
    def test_process_document_file_libraries_unavailable(self):
        """Test document processing when libraries are not available"""
        blob_url = "https://test.blob.core.windows.net/container/test.pdf"
        file_extension = ".pdf"
        
        result = self.service.process_document_file(blob_url, file_extension)
        
        self.assertIn("Document Processing Unavailable", result)
        self.assertIn("Document processing libraries not installed", result)
        self.assertIn("pip install python-docx docx2txt PyPDF2", result)
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', True)
    @patch.object(DocumentProcessingService, '_download_blob_content')
    @patch.object(DocumentProcessingService, '_extract_pdf_text')
    def test_process_pdf_document_success(self, mock_extract_pdf, mock_download):
        """Test successful PDF document processing"""
        # Arrange
        blob_url = "https://test.blob.core.windows.net/container/test.pdf"
        file_extension = ".pdf"
        expected_text = "This is extracted PDF text content."
        
        mock_download.return_value = b"fake pdf content"
        mock_extract_pdf.return_value = expected_text
        
        # Act
        result = self.service.process_document_file(blob_url, file_extension)
        
        # Assert
        self.assertEqual(result, expected_text)
        mock_download.assert_called_once_with(blob_url)
        mock_extract_pdf.assert_called_once_with(b"fake pdf content")
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', True)
    @patch.object(DocumentProcessingService, '_download_blob_content')
    @patch.object(DocumentProcessingService, '_extract_docx_text')
    def test_process_docx_document_success(self, mock_extract_docx, mock_download):
        """Test successful DOCX document processing"""
        # Arrange
        blob_url = "https://test.blob.core.windows.net/container/test.docx"
        file_extension = ".docx"
        expected_text = "This is extracted DOCX text content."
        
        mock_download.return_value = b"fake docx content"
        mock_extract_docx.return_value = expected_text
        
        # Act
        result = self.service.process_document_file(blob_url, file_extension)
        
        # Assert
        self.assertEqual(result, expected_text)
        mock_download.assert_called_once_with(blob_url)
        mock_extract_docx.assert_called_once_with(b"fake docx content")
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', True)
    @patch.object(DocumentProcessingService, '_download_blob_content')
    @patch.object(DocumentProcessingService, '_extract_doc_text')
    def test_process_doc_document_success(self, mock_extract_doc, mock_download):
        """Test successful DOC document processing"""
        # Arrange
        blob_url = "https://test.blob.core.windows.net/container/test.doc"
        file_extension = ".doc"
        expected_text = "This is extracted DOC text content."
        
        mock_download.return_value = b"fake doc content"
        mock_extract_doc.return_value = expected_text
        
        # Act
        result = self.service.process_document_file(blob_url, file_extension)
        
        # Assert
        self.assertEqual(result, expected_text)
        mock_download.assert_called_once_with(blob_url)
        mock_extract_doc.assert_called_once_with(b"fake doc content")
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', True)
    @patch.object(DocumentProcessingService, '_download_blob_content')
    def test_process_document_unsupported_extension(self, mock_download):
        """Test processing document with unsupported extension"""
        # Arrange
        blob_url = "https://test.blob.core.windows.net/container/test.xyz"
        file_extension = ".xyz"
        
        mock_download.return_value = b"fake content"
        
        # Act
        result = self.service.process_document_file(blob_url, file_extension)
        
        # Assert
        self.assertIn("Error processing .xyz document", result)
        self.assertIn("Unsupported document type", result)
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', True)
    @patch.object(DocumentProcessingService, '_download_blob_content')
    @patch.object(DocumentProcessingService, '_extract_pdf_text')
    def test_process_document_empty_text(self, mock_extract_pdf, mock_download):
        """Test processing document that returns empty text"""
        # Arrange
        blob_url = "https://test.blob.core.windows.net/container/empty.pdf"
        file_extension = ".pdf"
        
        mock_download.return_value = b"fake pdf content"
        mock_extract_pdf.return_value = ""  # Empty text
        
        # Act
        result = self.service.process_document_file(blob_url, file_extension)
        
        # Assert
        self.assertIn("Document processed but no text content was found", result)
    
    @patch('document_processing_service.DOC_PROCESSING_AVAILABLE', True)
    @patch.object(DocumentProcessingService, '_download_blob_content')
    def test_process_document_download_error(self, mock_download):
        """Test processing document when download fails"""
        # Arrange
        blob_url = "https://test.blob.core.windows.net/container/test.pdf"
        file_extension = ".pdf"
        
        mock_download.side_effect = Exception("Blob not found")
        
        # Act
        result = self.service.process_document_file(blob_url, file_extension)
        
        # Assert
        self.assertIn("Error processing .pdf document", result)
        self.assertIn("Blob not found", result)
    
    @patch('azure.storage.blob.BlobServiceClient')
    @patch('azure.identity.DefaultAzureCredential')
    def test_download_blob_content_success(self, mock_credential, mock_blob_service):
        """Test successful blob content download"""
        # Arrange
        blob_url = "https://testaccount.blob.core.windows.net/container/test.pdf"
        expected_content = b"fake file content"
        
        mock_blob_client = Mock()
        mock_blob_client.download_blob().readall.return_value = expected_content
        mock_blob_service.return_value.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = self.service._download_blob_content(blob_url)
        
        # Assert
        self.assertEqual(result, expected_content)
        mock_blob_service.assert_called_once()
        mock_blob_client.download_blob().readall.assert_called_once()
    
    @patch('azure.storage.blob.BlobServiceClient')
    def test_download_blob_content_error(self, mock_blob_service):
        """Test blob content download with error"""
        # Arrange
        blob_url = "https://testaccount.blob.core.windows.net/container/test.pdf"
        mock_blob_service.side_effect = Exception("Storage error")
        
        # Act & Assert
        with self.assertRaises(Exception):
            self.service._download_blob_content(blob_url)
    
    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_text_success(self, mock_pdf_reader):
        """Test successful PDF text extraction"""
        # Arrange
        file_content = b"fake pdf content"
        expected_text = "Page 1 content\n\nPage 2 content"
        
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader_instance = Mock()
        mock_reader_instance.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Act
        result = self.service._extract_pdf_text(file_content)
        
        # Assert
        self.assertEqual(result, expected_text)
        mock_pdf_reader.assert_called_once()
    
    @patch('PyPDF2.PdfReader')
    def test_extract_pdf_text_error(self, mock_pdf_reader):
        """Test PDF text extraction with error"""
        # Arrange
        file_content = b"invalid pdf content"
        mock_pdf_reader.side_effect = Exception("Invalid PDF")
        
        # Act & Assert
        with self.assertRaises(Exception):
            self.service._extract_pdf_text(file_content)
    
    @patch('tempfile.NamedTemporaryFile')
    @patch('docx.Document')
    @patch('os.unlink')
    def test_extract_docx_text_success(self, mock_unlink, mock_document, mock_temp_file):
        """Test successful DOCX text extraction"""
        # Arrange
        file_content = b"fake docx content"
        
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.docx"
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp_file.return_value = mock_temp
        
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Second paragraph"
        
        mock_doc = Mock()
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_document.return_value = mock_doc
        
        # Act
        result = self.service._extract_docx_text(file_content)
        
        # Assert
        self.assertEqual(result, "First paragraph\nSecond paragraph")
        mock_temp.write.assert_called_once_with(file_content)
        mock_temp.flush.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/test.docx")
    
    @patch('tempfile.NamedTemporaryFile')
    @patch('docx2txt.process')
    @patch('os.unlink')
    def test_extract_doc_text_success(self, mock_unlink, mock_docx2txt, mock_temp_file):
        """Test successful DOC text extraction"""
        # Arrange
        file_content = b"fake doc content"
        expected_text = "Extracted DOC text content"
        
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.doc"
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp_file.return_value = mock_temp
        
        mock_docx2txt.return_value = expected_text
        
        # Act
        result = self.service._extract_doc_text(file_content)
        
        # Assert
        self.assertEqual(result, expected_text)
        mock_temp.write.assert_called_once_with(file_content)
        mock_temp.flush.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/test.doc")
    
    @patch('tempfile.NamedTemporaryFile')
    @patch('docx2txt.process')
    @patch('os.unlink')
    def test_extract_doc_text_extraction_failure(self, mock_unlink, mock_docx2txt, mock_temp_file):
        """Test DOC text extraction failure"""
        # Arrange
        file_content = b"fake doc content"
        
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.doc"
        mock_temp.__enter__.return_value = mock_temp
        mock_temp.__exit__.return_value = None
        mock_temp_file.return_value = mock_temp
        
        mock_docx2txt.side_effect = Exception("Extraction failed")
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.service._extract_doc_text(file_content)
        
        self.assertIn("Legacy .doc format requires additional processing", str(context.exception))


if __name__ == "__main__":
    unittest.main()
