import logging
import json
import csv
import io
from typing import Dict, Any, Optional
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import AppConfig
from storage_service import StorageService


class TextProcessingService:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.storage_service = StorageService(config)
        self.credential = DefaultAzureCredential()
        self.logger.info(
            "Initialized TextProcessingService",
            extra={
                "supported_text_extensions": list(config.supported_text_extensions),
            },
        )

    def is_text_file(self, file_extension: str) -> bool:
        """Check if the file extension indicates a text file"""
        is_text = file_extension.lower() in self.config.supported_text_extensions
        self.logger.debug(
            "File type check",
            extra={
                "file_extension": file_extension,
                "is_text_file": is_text,
            },
        )
        return is_text

    def is_audio_file(self, file_extension: str) -> bool:
        """Check if the file extension indicates an audio file"""
        is_audio = file_extension.lower() in self.config.supported_audio_extensions
        self.logger.debug(
            "File type check",
            extra={
                "file_extension": file_extension,
                "is_audio_file": is_audio,
            },
        )
        return is_audio

    def get_file_type(self, file_extension: str) -> str:
        """Determine the file type based on extension"""
        if self.is_audio_file(file_extension):
            return "audio"
        elif self.is_text_file(file_extension):
            return "text"
        elif file_extension.lower() in self.config.supported_document_extensions:
            return "document"
        elif file_extension.lower() in self.config.supported_image_extensions:
            return "image"
        else:
            return "unsupported"

    def get_file_info(self, file_extension: str) -> Dict[str, Any]:
        """Get comprehensive information about a file type"""
        file_type = self.get_file_type(file_extension)
        
        info = {
            "file_type": file_type,
            "extension": file_extension,
            "can_process": file_type in ["audio", "text"],
            "processing_method": None,
            "requirements": None,
        }
        
        if file_type == "audio":
            info.update({
                "processing_method": "transcription",
                "service": "Azure Speech Service",
                "requirements": "Transcription and analysis workflow",
            })
        elif file_type == "text":
            info.update({
                "processing_method": "direct_analysis",
                "service": "Text Processing Service",
                "requirements": "Direct analysis workflow",
            })
        elif file_type == "document":
            info.update({
                "processing_method": "ocr_extraction",
                "service": "Azure Document Intelligence (not implemented)",
                "requirements": "Document text extraction service",
                "recommendation": "Convert to .txt format for immediate processing",
            })
        elif file_type == "image":
            info.update({
                "processing_method": "ocr_extraction",
                "service": "Azure Computer Vision OCR (not implemented)",
                "requirements": "Image text extraction service",
                "recommendation": "Extract text manually and save as .txt",
            })
        else:
            info.update({
                "processing_method": "unsupported",
                "service": "None",
                "requirements": "File format not supported",
                "recommendation": "Convert to supported format (.txt, .srt, .json, or audio format)",
            })
        
        self.logger.debug(
            "File type analysis completed",
            extra={
                "file_extension": file_extension,
                "analysis_result": info,
            },
        )
        
        return info

    def _download_text_file(self, blob_url: str) -> str:
        """Download and read content from a text file in blob storage"""
        try:
            self.logger.info("Downloading text file", extra={"blob_url": blob_url})
            
            # Parse the blob URL to get container and blob name
            # URL format: https://account.blob.core.windows.net/container/blob
            url_parts = blob_url.replace("https://", "").split("/")
            account_name = url_parts[0].split(".")[0]
            container_name = url_parts[1]
            blob_name = "/".join(url_parts[2:])
            
            self.logger.debug(
                "Parsed blob URL",
                extra={
                    "account_name": account_name,
                    "container_name": container_name,
                    "blob_name": blob_name,
                },
            )

            # Create blob service client
            blob_service_client = BlobServiceClient(
                account_url=self.config.storage_account_url,
                credential=self.credential,
            )

            # Download blob content
            blob_client = blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            
            blob_data = blob_client.download_blob()
            content = blob_data.readall().decode('utf-8')
            
            self.logger.info(
                "Successfully downloaded text file",
                extra={
                    "content_length": len(content),
                    "blob_name": blob_name,
                },
            )
            
            return content

        except Exception as e:
            self.logger.error(
                "Failed to download text file",
                extra={
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "blob_url": blob_url,
                },
                exc_info=True,
            )
            raise

    def _process_srt_content(self, content: str) -> str:
        """Process SRT subtitle file content to extract just the text"""
        try:
            self.logger.debug("Processing SRT content")
            lines = content.strip().split('\n')
            text_lines = []
            current_speaker = None
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip sequence numbers
                if line.isdigit():
                    i += 1
                    continue
                
                # Skip timestamp lines (contain --> )
                if '-->' in line:
                    i += 1
                    continue
                
                # Empty lines separate subtitle blocks
                if not line:
                    i += 1
                    continue
                
                # This should be subtitle text
                if line:
                    # Check if line contains speaker information
                    if ':' in line and len(line.split(':', 1)) == 2:
                        speaker, text = line.split(':', 1)
                        speaker = speaker.strip()
                        text = text.strip()
                        
                        if speaker != current_speaker:
                            text_lines.append(f"\n--- {speaker} ---")
                            current_speaker = speaker
                        text_lines.append(f"  {text}")
                    else:
                        text_lines.append(f"  {line}")
                
                i += 1
            
            processed_text = '\n'.join(text_lines)
            self.logger.info(
                "SRT content processed",
                extra={
                    "original_length": len(content),
                    "processed_length": len(processed_text),
                    "unique_speakers": len(set(speaker for speaker in [current_speaker] if speaker)),
                },
            )
            
            return processed_text
            
        except Exception as e:
            self.logger.error(
                "Failed to process SRT content",
                extra={
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                exc_info=True,
            )
            # Return original content if processing fails
            return content

    def _process_vtt_content(self, content: str) -> str:
        """Process VTT subtitle file content to extract just the text"""
        try:
            self.logger.debug("Processing VTT content")
            lines = content.strip().split('\n')
            text_lines = []
            current_speaker = None
            
            # Skip header lines until we find content
            start_processing = False
            
            for line in lines:
                line = line.strip()
                
                # Skip WEBVTT header and metadata
                if line.startswith('WEBVTT') or line.startswith('NOTE'):
                    continue
                
                # Skip timestamp lines (contain --> )
                if '-->' in line:
                    start_processing = True
                    continue
                
                # Empty lines separate subtitle blocks
                if not line:
                    continue
                
                # Process text content
                if start_processing and line:
                    # Remove VTT formatting tags like <v Speaker>
                    clean_line = line
                    if '<v ' in line and '>' in line:
                        # Extract speaker from <v Speaker> tags
                        start_tag = line.find('<v ')
                        if start_tag != -1:
                            end_tag = line.find('>', start_tag)
                            if end_tag != -1:
                                speaker = line[start_tag + 3:end_tag].strip()
                                clean_line = line[end_tag + 1:].strip()
                                
                                if speaker != current_speaker:
                                    text_lines.append(f"\n--- {speaker} ---")
                                    current_speaker = speaker
                                text_lines.append(f"  {clean_line}")
                                continue
                    
                    # Remove other VTT tags
                    import re
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    text_lines.append(f"  {clean_line}")
            
            processed_text = '\n'.join(text_lines)
            self.logger.info(
                "VTT content processed",
                extra={
                    "original_length": len(content),
                    "processed_length": len(processed_text),
                },
            )
            
            return processed_text
            
        except Exception as e:
            self.logger.error(
                "Failed to process VTT content",
                extra={
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                exc_info=True,
            )
            # Return original content if processing fails
            return content

    def _process_json_content(self, content: str) -> str:
        """Process JSON file content that might contain transcript data"""
        try:
            self.logger.debug("Processing JSON content")
            data = json.loads(content)
            
            # Try to extract text from common JSON transcript formats
            text_lines = []
            
            # Format 1: Array of transcript segments
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        # Common fields for transcript segments
                        text = item.get('text', item.get('content', item.get('transcript', '')))
                        speaker = item.get('speaker', item.get('name', item.get('user', '')))
                        
                        if text:
                            if speaker:
                                text_lines.append(f"--- {speaker} ---")
                            text_lines.append(f"  {text}")
            
            # Format 2: Object with transcript array
            elif isinstance(data, dict):
                # Check for common transcript array keys
                transcript_keys = ['transcript', 'segments', 'results', 'utterances', 'messages']
                
                for key in transcript_keys:
                    if key in data and isinstance(data[key], list):
                        for item in data[key]:
                            if isinstance(item, dict):
                                text = item.get('text', item.get('content', item.get('message', '')))
                                speaker = item.get('speaker', item.get('name', item.get('user', '')))
                                
                                if text:
                                    if speaker:
                                        text_lines.append(f"--- {speaker} ---")
                                    text_lines.append(f"  {text}")
                        break
                
                # If no transcript array found, try to extract any text content
                if not text_lines:
                    if 'text' in data:
                        text_lines.append(str(data['text']))
                    elif 'content' in data:
                        text_lines.append(str(data['content']))
            
            # If we couldn't parse as structured transcript, return the raw JSON as text
            if not text_lines:
                text_lines.append(json.dumps(data, indent=2))
            
            processed_text = '\n'.join(text_lines)
            self.logger.info(
                "JSON content processed",
                extra={
                    "original_length": len(content),
                    "processed_length": len(processed_text),
                    "segments_found": len([line for line in text_lines if line.strip().startswith('---')]),
                },
            )
            
            return processed_text
            
        except json.JSONDecodeError as e:
            self.logger.warning(
                "Failed to parse JSON, treating as plain text",
                extra={
                    "error_details": str(e),
                },
            )
            return content
        except Exception as e:
            self.logger.error(
                "Failed to process JSON content",
                extra={
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
                exc_info=True,
            )
            return content

    def process_text_file(self, blob_url: str, file_extension: str) -> str:
        """Process a text file and return formatted content ready for analysis"""
        try:
            self.logger.info(
                "Starting text file processing",
                extra={
                    "blob_url": blob_url,
                    "file_extension": file_extension,
                },
            )
            
            # Download the file content
            content = self._download_text_file(blob_url)
            
            # Process based on file type
            if file_extension.lower() == '.srt':
                processed_content = self._process_srt_content(content)
            elif file_extension.lower() == '.vtt':
                processed_content = self._process_vtt_content(content)
            elif file_extension.lower() == '.json':
                processed_content = self._process_json_content(content)
            else:
                # For .txt, .md, .rtf, .csv and other text files, use content as-is
                processed_content = content
                self.logger.info(
                    "Using content as-is for text file",
                    extra={
                        "file_extension": file_extension,
                        "content_length": len(content),
                    },
                )
            
            self.logger.info(
                "Text file processing completed",
                extra={
                    "original_length": len(content),
                    "processed_length": len(processed_content),
                    "file_extension": file_extension,
                },
            )
            
            return processed_content
            
        except Exception as e:
            self.logger.error(
                "Failed to process text file",
                extra={
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                    "blob_url": blob_url,
                    "file_extension": file_extension,
                },
                exc_info=True,
            )
            raise
