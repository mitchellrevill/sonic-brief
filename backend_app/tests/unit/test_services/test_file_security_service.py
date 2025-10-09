"""
Unit tests for FileSecurityService (Medium Priority - Phase 3)

Tests cover:
- File size validation
- File type validation (extensions)
- Filename sanitization
- Malicious content detection
- MIME type detection
- File hash generation
- Edge cases and error handling

Target Coverage: 90%+
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import UploadFile, HTTPException
import hashlib

from app.services.file_security_service import FileSecurityService


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Mock configuration for file security."""
    config = Mock()
    config.max_file_size_mb = 10
    config.allowed_file_types_list = ['.pdf', '.docx', '.txt', '.mp3', '.wav', '.m4a']
    return config


@pytest.fixture
def file_security_service(mock_config):
    """Create FileSecurityService with mocked config."""
    with patch('app.services.file_security_service.get_config', return_value=mock_config):
        return FileSecurityService()


def create_upload_file(filename: str, content: bytes) -> UploadFile:
    """Helper to create a mock UploadFile."""
    file = Mock(spec=UploadFile)
    file.filename = filename
    file.read = AsyncMock(return_value=content)
    file.seek = AsyncMock()
    return file


# ============================================================================
# File Size Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestFileSizeValidation:
    """Test file size validation."""
    
    @pytest.mark.asyncio
    async def test_validate_file_within_size_limit(self, file_security_service):
        """Test validation passes for file within size limit."""
        content = b"This is test content"
        file = create_upload_file("test.txt", content)
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        assert result["size"] == len(content)
    
    @pytest.mark.asyncio
    async def test_validate_file_exceeds_size_limit(self, file_security_service):
        """Test validation fails for file exceeding size limit."""
        # Create content larger than 10MB limit
        large_content = b"x" * (11 * 1024 * 1024)
        file = create_upload_file("large.txt", large_content)
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_validate_file_at_size_limit(self, file_security_service):
        """Test validation at exactly the size limit."""
        # Create content exactly at 10MB limit
        content = b"x" * (10 * 1024 * 1024)
        file = create_upload_file("exact.txt", content)
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        assert result["size"] == len(content)
    
    @pytest.mark.asyncio
    async def test_validate_empty_file(self, file_security_service):
        """Test validation of empty file."""
        file = create_upload_file("empty.txt", b"")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        assert result["size"] == 0


# ============================================================================
# File Type Validation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestFileTypeValidation:
    """Test file type/extension validation."""
    
    @pytest.mark.asyncio
    async def test_validate_allowed_pdf_extension(self, file_security_service):
        """Test validation passes for allowed PDF extension."""
        file = create_upload_file("document.pdf", b"PDF content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        assert result["safe_filename"] == "document.pdf"
    
    @pytest.mark.asyncio
    async def test_validate_allowed_docx_extension(self, file_security_service):
        """Test validation passes for allowed DOCX extension."""
        file = create_upload_file("document.docx", b"DOCX content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_validate_allowed_audio_extensions(self, file_security_service):
        """Test validation passes for allowed audio extensions."""
        audio_files = [
            ("audio.mp3", b"MP3 content"),
            ("audio.wav", b"WAV content"),
            ("audio.m4a", b"M4A content"),
        ]
        
        for filename, content in audio_files:
            file = create_upload_file(filename, content)
            result = await file_security_service.validate(file)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_validate_disallowed_extension(self, file_security_service):
        """Test validation fails for disallowed extension."""
        file = create_upload_file("malicious.exe", b"EXE content")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
        assert "not allowed" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_validate_file_without_extension(self, file_security_service):
        """Test validation of file without extension."""
        file = create_upload_file("noextension", b"content")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_validate_case_insensitive_extension(self, file_security_service):
        """Test validation is case-insensitive for extensions."""
        file = create_upload_file("Document.PDF", b"PDF content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None


# ============================================================================
# Filename Sanitization Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestFilenameSanitization:
    """Test filename sanitization."""
    
    @pytest.mark.asyncio
    async def test_sanitize_filename_with_path(self, file_security_service):
        """Test sanitization removes path components."""
        file = create_upload_file("../../etc/passwd.txt", b"content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        assert result["safe_filename"] == "passwd.txt"
        assert "../" not in result["safe_filename"]
    
    @pytest.mark.asyncio
    async def test_sanitize_filename_with_windows_path(self, file_security_service):
        """Test sanitization removes Windows path components."""
        file = create_upload_file("C:\\Windows\\System32\\file.txt", b"content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        assert result["safe_filename"] == "file.txt"
    
    @pytest.mark.asyncio
    async def test_sanitize_filename_with_special_characters(self, file_security_service):
        """Test sanitization removes special characters."""
        file = create_upload_file("file!@#$%^&*().txt", b"content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        # Should only contain alphanumeric, dots, dashes, underscores
        assert result["safe_filename"] == "file.txt"
    
    @pytest.mark.asyncio
    async def test_sanitize_filename_with_spaces(self, file_security_service):
        """Test sanitization removes spaces."""
        file = create_upload_file("my document.txt", b"content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        # Spaces should be removed
        assert " " not in result["safe_filename"]
    
    @pytest.mark.asyncio
    async def test_sanitize_filename_starting_with_dot(self, file_security_service):
        """Test validation fails for filename starting with dot."""
        file = create_upload_file(".hidden.txt", b"content")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_sanitize_very_long_filename(self, file_security_service):
        """Test sanitization truncates very long filenames."""
        long_name = "a" * 300 + ".txt"
        file = create_upload_file(long_name, b"content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        # Should be truncated to 255 characters
        assert len(result["safe_filename"]) <= 255


# ============================================================================
# Malicious Content Detection Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestMaliciousContentDetection:
    """Test malicious content detection."""
    
    @pytest.mark.asyncio
    async def test_detect_script_tag(self, file_security_service):
        """Test detection of script tags."""
        file = create_upload_file("malicious.txt", b"<script>alert('xss')</script>")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
        assert "disallowed content" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_detect_javascript_protocol(self, file_security_service):
        """Test detection of javascript: protocol."""
        file = create_upload_file("malicious.txt", b"<a href='javascript:alert(1)'>click</a>")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_detect_php_tag(self, file_security_service):
        """Test detection of PHP tags."""
        file = create_upload_file("malicious.txt", b"<?php system('rm -rf /'); ?>")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_detect_eval_function(self, file_security_service):
        """Test detection of eval() function."""
        file = create_upload_file("malicious.txt", b"eval('malicious code')")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_detect_exec_function(self, file_security_service):
        """Test detection of exec() function."""
        file = create_upload_file("malicious.txt", b"exec('malicious code')")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_detect_pe_header(self, file_security_service):
        """Test detection of PE (Windows executable) header."""
        file = create_upload_file("malicious.txt", b"MZ\x90\x00" + b"rest of PE file")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_case_insensitive_pattern_detection(self, file_security_service):
        """Test that pattern detection is case-insensitive."""
        file = create_upload_file("malicious.txt", b"<SCRIPT>alert('xss')</SCRIPT>")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_safe_content_passes(self, file_security_service):
        """Test that safe content passes validation."""
        file = create_upload_file("safe.txt", b"This is safe content without any dangerous patterns")
        
        result = await file_security_service.validate(file)
        
        assert result is not None


# ============================================================================
# File Hash Generation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestFileHashGeneration:
    """Test file hash generation."""
    
    @pytest.mark.asyncio
    async def test_generate_file_hash(self, file_security_service):
        """Test that file hash is generated correctly."""
        content = b"test content"
        file = create_upload_file("test.txt", content)
        
        result = await file_security_service.validate(file)
        
        expected_hash = hashlib.sha256(content).hexdigest()
        assert result["file_hash"] == expected_hash
    
    @pytest.mark.asyncio
    async def test_different_content_different_hash(self, file_security_service):
        """Test that different content produces different hashes."""
        file1 = create_upload_file("test1.txt", b"content1")
        file2 = create_upload_file("test2.txt", b"content2")
        
        result1 = await file_security_service.validate(file1)
        result2 = await file_security_service.validate(file2)
        
        assert result1["file_hash"] != result2["file_hash"]
    
    @pytest.mark.asyncio
    async def test_same_content_same_hash(self, file_security_service):
        """Test that same content produces same hash."""
        content = b"identical content"
        file1 = create_upload_file("file1.txt", content)
        file2 = create_upload_file("file2.txt", content)
        
        result1 = await file_security_service.validate(file1)
        result2 = await file_security_service.validate(file2)
        
        assert result1["file_hash"] == result2["file_hash"]


# ============================================================================
# MIME Type Detection Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestMIMETypeDetection:
    """Test MIME type detection."""
    
    @pytest.mark.asyncio
    async def test_mime_type_detection_with_magic(self, file_security_service):
        """Test MIME type detection when magic library is available."""
        file = create_upload_file("test.txt", b"text content")
        
        with patch('app.services.file_security_service.magic') as mock_magic:
            mock_magic.from_buffer = Mock(return_value="text/plain")
            
            result = await file_security_service.validate(file)
            
            assert result["content_type"] == "text/plain"
    
    @pytest.mark.asyncio
    async def test_mime_type_fallback_without_magic(self, file_security_service):
        """Test MIME type fallback when magic library is not available."""
        file = create_upload_file("test.txt", b"text content")
        
        with patch('app.services.file_security_service.magic', None):
            result = await file_security_service.validate(file)
            
            # Should fallback to default MIME type
            assert result["content_type"] == "application/octet-stream"
    
    @pytest.mark.asyncio
    async def test_mime_type_detection_error(self, file_security_service):
        """Test MIME type detection handles errors gracefully."""
        file = create_upload_file("test.txt", b"content")
        
        with patch('app.services.file_security_service.magic') as mock_magic:
            mock_magic.from_buffer = Mock(side_effect=Exception("Magic error"))
            
            result = await file_security_service.validate(file)
            
            # Should fallback to default MIME type
            assert result["content_type"] == "application/octet-stream"


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.medium
class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_validate_no_file_provided(self, file_security_service):
        """Test validation fails when no file is provided."""
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(None)
        
        assert exc_info.value.status_code == 400
        assert "no file" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_validate_file_without_filename(self, file_security_service):
        """Test validation fails when file has no filename."""
        file = Mock(spec=UploadFile)
        file.filename = None
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_validate_file_with_empty_filename(self, file_security_service):
        """Test validation fails when filename is empty."""
        file = create_upload_file("", b"content")
        
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_validate_file_with_only_special_characters(self, file_security_service):
        """Test validation fails when filename contains only special characters."""
        file = create_upload_file("!@#$%^&*.txt", b"content")
        
        # After sanitization, only .txt should remain
        with pytest.raises(HTTPException) as exc_info:
            await file_security_service.validate(file)
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_file_read_seek_called(self, file_security_service):
        """Test that file read and seek are called properly."""
        file = create_upload_file("test.txt", b"content")
        
        await file_security_service.validate(file)
        
        file.read.assert_called_once()
        file.seek.assert_called_once_with(0)
    
    @pytest.mark.asyncio
    async def test_validate_multiple_extensions(self, file_security_service):
        """Test validation with multiple extensions."""
        file = create_upload_file("document.backup.txt", b"content")
        
        result = await file_security_service.validate(file)
        
        assert result is not None
        # Should use the last extension
        assert ".txt" in result["safe_filename"]
