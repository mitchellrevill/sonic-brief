# Secure Input Validation Utilities
import re
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from pathlib import Path
import html
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """Centralized input validation and sanitization"""
    
    # Regex patterns for validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._\-\s()]+$')
    
    # Dangerous patterns (more comprehensive)
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # XSS
        r'vbscript:',  # XSS
        r'on\w+\s*=',  # Event handlers
        r'<\s*iframe',  # Iframe injection
        r'<\s*object',  # Object injection
        r'<\s*embed',  # Embed injection
        r'<\s*applet',  # Applet injection
        r'<\s*meta',  # Meta injection
        r'<\s*link',  # Link injection
        r'<\s*style',  # Style injection
        r'\.\./|\.\\\.',  # Path traversal
        r'[/\\]etc[/\\]passwd',  # Unix system files
        r'[/\\]proc[/\\]',  # Unix proc filesystem
        r'\\\\[a-zA-Z$]',  # Windows UNC paths
        r'union\s+select',  # SQL injection
        r'insert\s+into',  # SQL injection
        r'delete\s+from',  # SQL injection
        r'drop\s+table',  # SQL injection
        r'exec\s*\(',  # Code execution
        r'eval\s*\(',  # Code execution
        r'system\s*\(',  # System calls
        r'shell_exec\s*\(',  # System calls
        r'passthru\s*\(',  # System calls
        r'__import__',  # Python imports
        r'subprocess',  # Python subprocess
        r'os\.system',  # Python system calls
        r'file_get_contents',  # File inclusion
        r'include\s*\(',  # File inclusion
        r'require\s*\(',  # File inclusion
    ]
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        if not email or len(email) > 254:  # RFC 5321 limit
            return False
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_uuid(cls, uuid_str: str) -> bool:
        """Validate UUID format"""
        if not uuid_str:
            return False
        return bool(cls.UUID_PATTERN.match(uuid_str))
    
    @classmethod
    def validate_filename(cls, filename: str) -> bool:
        """Validate filename is safe"""
        if not filename or len(filename) > 255:
            return False
        # Check for dangerous patterns
        if cls.contains_dangerous_patterns(filename):
            return False
        return bool(cls.FILENAME_PATTERN.match(filename))
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename by removing dangerous characters"""
        if not filename:
            return "unnamed"
        
        # Remove path components
        filename = Path(filename).name
        
        # Remove or replace dangerous characters
        sanitized = re.sub(r'[^\w\-_\.\s]', '_', filename)
        
        # Limit length
        if len(sanitized) > 100:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[:95] + ext
        
        return sanitized or "unnamed"
    
    @classmethod
    def contains_dangerous_patterns(cls, text: str) -> bool:
        """Check if text contains dangerous patterns"""
        if not text:
            return False
        
        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return True
        return False
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """Sanitize HTML content"""
        if not text:
            return ""
        return html.escape(text)
    
    @classmethod
    def validate_json_size(cls, data: Dict[str, Any], max_keys: int = 100, max_depth: int = 10) -> bool:
        """Validate JSON data size and complexity"""
        def count_keys_and_depth(obj, current_depth=0):
            if current_depth > max_depth:
                return float('inf'), current_depth
            
            key_count = 0
            max_child_depth = current_depth
            
            if isinstance(obj, dict):
                key_count += len(obj)
                for value in obj.values():
                    child_keys, child_depth = count_keys_and_depth(value, current_depth + 1)
                    key_count += child_keys
                    max_child_depth = max(max_child_depth, child_depth)
            elif isinstance(obj, list):
                for item in obj:
                    child_keys, child_depth = count_keys_and_depth(item, current_depth + 1)
                    key_count += child_keys
                    max_child_depth = max(max_child_depth, child_depth)
            
            return key_count, max_child_depth
        
        total_keys, depth = count_keys_and_depth(data)
        return total_keys <= max_keys and depth <= max_depth
    
    @classmethod
    def validate_string_length(cls, text: str, min_length: int = 0, max_length: int = 1000) -> bool:
        """Validate string length"""
        if not isinstance(text, str):
            return False
        return min_length <= len(text) <= max_length
    
    @classmethod
    def validate_and_sanitize_user_input(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive validation and sanitization of user input"""
        sanitized = {}
        
        for key, value in data.items():
            # Validate key
            if cls.contains_dangerous_patterns(key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid field name: {key}"
                )
            
            # Sanitize value based on type
            if isinstance(value, str):
                if cls.contains_dangerous_patterns(value):
                    logger.warning(f"Dangerous pattern in field '{key}': {value[:100]}...")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid content in field: {key}"
                    )
                sanitized[key] = cls.sanitize_html(value)
            elif isinstance(value, dict):
                sanitized[key] = cls.validate_and_sanitize_user_input(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.validate_and_sanitize_user_input(item) if isinstance(item, dict)
                    else cls.sanitize_html(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized

# Validation decorators for common use cases
def validate_uuid_param(param_name: str = "id"):
    """Decorator to validate UUID parameters"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            param_value = kwargs.get(param_name)
            if param_value and not InputValidator.validate_uuid(param_value):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {param_name} format"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_email_param(param_name: str = "email"):
    """Decorator to validate email parameters"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            param_value = kwargs.get(param_name)
            if param_value and not InputValidator.validate_email(param_value):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid {param_name} format"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
