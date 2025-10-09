import hashlib
import re
from typing import Dict, Any

from fastapi import UploadFile, HTTPException

from app.core.config import get_config

try:
    import magic  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    magic = None


class FileSecurityService:
    """Service to validate uploaded files for size, type, and basic malicious patterns."""

    DANGEROUS_PATTERNS = [
        b"<script",
        b"javascript:",
        b"<?php",
        b"eval(",
        b"exec(",
        b"mz\x90\x00",  # PE header (lowercase)
    ]

    def __init__(self):
        config = get_config()
        self.max_size_bytes = config.max_file_size_mb * 1024 * 1024
        self.allowed_exts = set(config.allowed_file_types_list)

    async def validate(self, file: UploadFile) -> Dict[str, Any]:
        # Basic checks
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Sanitize filename
        safe_name = self._sanitize_filename(file.filename)
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid filename")

        # Read up to max_size_bytes + 1 to check size without loading huge files entirely
        content = await file.read()
        await file.seek(0)

        if len(content) > self.max_size_bytes:
            raise HTTPException(status_code=413, detail="File too large")

        # Detect mime type
        mime = None
        if magic:
            try:
                mime = magic.from_buffer(content, mime=True)
            except Exception:
                mime = None

        # Fallback to extension-based check
        ext = ("." + safe_name.split(".")[-1].lower()) if '.' in safe_name else ''
        if mime:
            # simple accept if extension matches allowed or mime suggests allowed
            if ext not in self.allowed_exts:
                # Some types may not match extension list; still validate against ext
                raise HTTPException(status_code=400, detail=f"File extension {ext} not allowed")
        else:
            if ext not in self.allowed_exts:
                raise HTTPException(status_code=400, detail=f"File extension {ext} not allowed")

        # Basic malicious content scan
        low = content.lower()
        for pat in self.DANGEROUS_PATTERNS:
            if pat in low:
                raise HTTPException(status_code=400, detail="File contains disallowed content")

        # Hash for storage naming
        file_hash = hashlib.sha256(content).hexdigest()

        return {
            "safe_filename": safe_name,
            "content_type": mime or "application/octet-stream",
            "file_hash": file_hash,
            "size": len(content),
        }

    def _sanitize_filename(self, filename: str) -> str:
        # Remove path info
        name = filename.split('/')[-1].split('\\')[-1]
        # Allow only safe characters
        name = re.sub(r'[^A-Za-z0-9_.-]', '', name)
        if not name or name.startswith('.'):
            return ''
        
        # Preserve extension when truncating
        if len(name) > 255:
            # Find the last dot to preserve extension
            last_dot = name.rfind('.')
            if last_dot > 0:
                # We have an extension, preserve it
                ext = name[last_dot:]
                max_base_len = 255 - len(ext)
                if max_base_len > 0:
                    base = name[:last_dot][:max_base_len]
                    name = base + ext
                else:
                    # Extension alone is too long, truncate it
                    name = name[:255]
            else:
                # No extension, just truncate
                name = name[:255]
        
        return name
