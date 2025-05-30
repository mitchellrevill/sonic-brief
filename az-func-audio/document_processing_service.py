import logging
import json
import io
import tempfile
from typing import Dict, Any, Optional
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import os
import sys

# Document processing imports
try:
    import docx2txt
    from docx import Document
    import PyPDF2
    DOC_PROCESSING_AVAILABLE = True
except ImportError:
    DOC_PROCESSING_AVAILABLE = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import AppConfig
from storage_service import StorageService


class DocumentProcessingService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.storage_service = StorageService(config)
        self.credential = DefaultAzureCredential()
        self.logger.info(
            "Initialized DocumentProcessingService",
            extra={
                "supported_document_extensions": [".pdf", ".doc", ".docx"],
            },
        )

    def is_document_file(self, file_extension: str) -> bool:
        """Check if the file extension indicates a document file"""
        document_extensions = {".pdf", ".doc", ".docx", ".rtf"}
        is_document = file_extension.lower() in document_extensions
        self.logger.debug(
            "Document file type check",
            extra={
                "file_extension": file_extension,
                "is_document_file": is_document,
            },
        )
        return is_document

    def process_document_file(self, blob_url: str, file_extension: str) -> str:
        """
        Process document files - extract text from PDF, DOC, and DOCX files
        """
        self.logger.info(
            "Document processing requested",
            extra={
                "blob_url": blob_url,
                "file_extension": file_extension,
                "doc_processing_available": DOC_PROCESSING_AVAILABLE,
            },
        )
        
        if not DOC_PROCESSING_AVAILABLE:
            return self._get_processing_unavailable_message(blob_url, file_extension)
        
        try:
            # Download the file from blob storage
            file_content = self._download_blob_content(blob_url)
            
            # Extract text based on file type
            if file_extension.lower() == '.pdf':
                extracted_text = self._extract_pdf_text(file_content)
            elif file_extension.lower() == '.docx':
                extracted_text = self._extract_docx_text(file_content)
            elif file_extension.lower() == '.doc':
                extracted_text = self._extract_doc_text(file_content)
            else:
                raise ValueError(f"Unsupported document type: {file_extension}")
            
            if not extracted_text or not extracted_text.strip():
                self.logger.warning(
                    "No text extracted from document",
                    extra={
                        "blob_url": blob_url,
                        "file_extension": file_extension,
                    },
                )
                return f"Document processed but no text content was found in {file_extension} file."
            
            self.logger.info(
                "Document processing completed",
                extra={
                    "blob_url": blob_url,
                    "file_extension": file_extension,
                    "text_length": len(extracted_text),
                    "status": "success",
                },
            )
            
            return extracted_text.strip()
            
        except Exception as e:
            self.logger.error(
                "Document processing failed",
                extra={
                    "blob_url": blob_url,
                    "file_extension": file_extension,
                    "error": str(e),
                },                exc_info=True,
            )
            return f"Error processing {file_extension} document: {str(e)}"

    def _get_processing_unavailable_message(self, blob_url: str, file_extension: str) -> str:
        """Return message when document processing libraries are not available"""
        return f"""
--- Document Processing Unavailable ---
File: {blob_url}
Type: {file_extension}
Status: Document processing libraries not installed.

To enable document processing, install the required dependencies:
pip install python-docx docx2txt PyPDF2

Missing libraries prevent automatic text extraction.
Please convert to a text format (.txt, .srt, .vtt, .json) for analysis.
""".strip()

    def _download_blob_content(self, blob_url: str) -> bytes:
        """Download file content from Azure Blob Storage"""
        try:
            # Extract container and blob name from URL
            # Expected format: https://account.blob.core.windows.net/container/blob
            url_parts = blob_url.replace('https://', '').split('/')
            account_name = url_parts[0].split('.')[0]
            container_name = url_parts[1]
            blob_name = '/'.join(url_parts[2:])
            
            # Create blob service client
            blob_service_client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=self.credential
            )
            
            # Download blob content
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            return blob_client.download_blob().readall()
            
        except Exception as e:
            self.logger.error(
                "Failed to download blob content",
                extra={
                    "blob_url": blob_url,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            # Create a PDF reader from bytes
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
                except Exception as e:
                    self.logger.warning(
                        "Failed to extract text from PDF page",
                        extra={
                            "page_number": page_num,
                            "error": str(e),
                        },
                    )
                    continue
            
            return '\n\n'.join(text_parts)
            
        except Exception as e:
            self.logger.error(
                "PDF text extraction failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def _extract_docx_text(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            # Method 1: Try with python-docx for better formatting
            try:
                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file.flush()
                    
                    doc = Document(tmp_file.name)
                    text_parts = []
                    
                    for paragraph in doc.paragraphs:
                        if paragraph.text.strip():
                            text_parts.append(paragraph.text)
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
                    
                    return '\n'.join(text_parts)
                    
            except Exception:
                # Method 2: Fallback to docx2txt
                with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file.flush()
                    
                    text = docx2txt.process(tmp_file.name)
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
                    
                    return text or ""
                    
        except Exception as e:
            self.logger.error(
                "DOCX text extraction failed",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def _extract_doc_text(self, file_content: bytes) -> str:
        """Extract text from legacy DOC file"""
        try:
            # For .doc files, we'll use docx2txt which has some support for legacy formats
            # Note: This may not work perfectly for all .doc files as they use a different format
            with tempfile.NamedTemporaryFile(suffix='.doc', delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                
                try:
                    # Try to process as if it's a docx (sometimes works)
                    text = docx2txt.process(tmp_file.name)
                    if text and text.strip():
                        return text
                except Exception:
                    pass
                
                # Clean up temp file
                os.unlink(tmp_file.name)
                
                # If extraction fails, provide helpful message
                raise ValueError(
                    "Legacy .doc format requires additional processing. "
                    "Please convert to .docx or .txt format for better compatibility."
                )
                
        except Exception as e:
            self.logger.error(
                "DOC text extraction failed",
                                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def get_supported_formats_info(self) -> Dict[str, Any]:
        """Return information about supported formats"""
        return {
            "audio_formats": {
                "supported": True,
                "processing": "Automatic transcription via Azure Speech Service",
                "extensions": [".mp3", ".wav", ".m4a", ".webm", ".flac", ".ogg", ".opus", ".aac", ".mp4"],
            },
            "text_formats": {
                "supported": True,
                "processing": "Direct text analysis",
                "extensions": [".txt", ".srt", ".vtt", ".json", ".md", ".rtf", ".csv"],
            },            "document_formats": {
                "supported": DOC_PROCESSING_AVAILABLE,
                "processing": "Text extraction from PDF, DOC, and DOCX files" if DOC_PROCESSING_AVAILABLE else "Document processing libraries not installed",
                "extensions": [".pdf", ".doc", ".docx"],
                "recommendation": "Install python-docx, docx2txt, and PyPDF2 for document processing" if not DOC_PROCESSING_AVAILABLE else "Supported formats for automatic text extraction",
            },
            "image_formats": {
                "supported": False,
                "processing": "OCR (not yet implemented)",
                "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
                "recommendation": "Extract text manually and save as .txt",
            },
        }
