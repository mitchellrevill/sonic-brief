"""
Service Interfaces - Abstract Base Classes for core services

These interfaces define the contracts for key services, enabling:
- Easy mocking and testing
- Swapping implementations (e.g., in-memory vs database)
- Cleaner dependency injection patterns
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class SessionServiceInterface(ABC):
    """
    DEPRECATED INTERFACE: No longer used or implemented by any classes.
    
    This interface defined the legacy contract for a monolithic session tracking service.
    It has been replaced by:
    - SessionTrackingService: For session lifecycle management
    - AuditLoggingService: For security audit logging
    - AuthenticationService: For JWT handling
    
    This interface is kept ONLY for documentation purposes and should not be implemented
    or referenced in new code. It will be removed in a future release.
    """
    
    @abstractmethod
    async def get_or_create_session(
        self,
        user_id: str,
        user_email: Optional[str] = None,
        request_path: str = "/",
        user_agent: str = "",
        ip_address: str = "",
        timestamp: Optional[datetime] = None
    ) -> Optional[str]:
        """Get existing session or create a new one."""
        pass
    
    @abstractmethod
    async def update_heartbeat(
        self,
        session_id: str,
        user_id: str,
        request_path: str = "/",
        user_agent: str = "",
        ip_address: str = "",
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Update session heartbeat and activity."""
        pass
    
    @abstractmethod
    async def create_audit_log(
        self,
        user_id: str,
        user_email: Optional[str],
        event_type: str,
        endpoint: str,
        method: str,
        ip_address: str = "",
        user_agent: str = "",
        user_permission: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> Optional[str]:
        """Create an audit log entry."""
        pass
    
    @abstractmethod
    async def resolve_canonical_id(self, email: str) -> Optional[str]:
        """Resolve email to canonical GUID."""
        pass
    
    @abstractmethod
    def is_audit_endpoint(self, path: str) -> bool:
        """Check if endpoint should be audited."""
        pass
    
    @abstractmethod
    def determine_audit_event_type(self, path: str, method: str) -> str:
        """Determine audit event type from path and method."""
        pass


class AnalyticsServiceInterface(ABC):
    """
    Interface for analytics and metrics services.
    
    Defines the contract for collecting and querying analytics data.
    """
    
    @abstractmethod
    async def record_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Record an analytics event."""
        pass
    
    @abstractmethod
    async def get_user_analytics(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics data for a specific user."""
        pass
    
    @abstractmethod
    async def get_system_metrics(
        self,
        metric_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get system-wide metrics."""
        pass


class StorageServiceInterface(ABC):
    """
    Interface for file storage and blob operations.
    
    Defines the contract for storing and retrieving files.
    """
    
    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload a file and return the file ID."""
        pass
    
    @abstractmethod
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file content by file ID."""
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file by file ID."""
        pass
    
    @abstractmethod
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata by file ID."""
        pass
    
    @abstractmethod
    async def list_user_files(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List files owned by a user."""
        pass


class SystemHealthServiceInterface(ABC):
    """
    Interface for system health and monitoring services.
    
    Defines the contract for checking system health status.
    """
    
    @abstractmethod
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        pass
    
    @abstractmethod
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information."""
        pass
    
    @abstractmethod
    async def get_quick_health(self) -> Dict[str, Any]:
        """Get quick health check."""
        pass


class ExportServiceInterface(ABC):
    """
    Interface for data export services.
    
    Defines the contract for exporting analytics and user data.
    """
    
    @abstractmethod
    async def export_user_data(
        self,
        user_id: str,
        export_format: str = "json",
        include_analytics: bool = True
    ) -> Dict[str, Any]:
        """Export all data for a user."""
        pass
    
    @abstractmethod
    async def export_analytics_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        export_format: str = "json"
    ) -> Dict[str, Any]:
        """Export analytics data for a date range."""
        pass


class PromptServiceInterface(ABC):
    """
    Interface for prompt management services.
    
    Defines the contract for managing AI prompts and templates.
    """
    
    @abstractmethod
    async def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get a prompt by ID."""
        pass
    
    @abstractmethod
    async def create_prompt(
        self,
        prompt_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """Create a new prompt and return its ID."""
        pass
    
    @abstractmethod
    async def update_prompt(
        self,
        prompt_id: str,
        updates: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> bool:
        """Update an existing prompt."""
        pass
    
    @abstractmethod
    async def delete_prompt(
        self,
        prompt_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Delete a prompt."""
        pass
    
    @abstractmethod
    async def list_prompts(
        self,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List available prompts."""
        pass


class TalkingPointsServiceInterface(ABC):
    """
    Interface for talking points validation and processing services.
    
    Defines the contract for managing talking points structure validation,
    format conversion, and legacy migration.
    """
    
    @abstractmethod
    def validate_talking_points_structure(
        self, 
        talking_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and convert talking points to database format.
        
        Args:
            talking_points: List of talking point sections from frontend
            
        Returns:
            List of validated talking point sections
        """
        pass
    
    @abstractmethod
    def convert_talking_points_to_response(
        self, 
        talking_points_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert database talking points to response format.
        
        Args:
            talking_points_data: Talking points from database
            
        Returns:
            Formatted talking points for frontend
        """
        pass
    
    @abstractmethod
    def migrate_legacy_talking_points(
        self, 
        legacy_points: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Migrate legacy talking points format to new structured format.
        
        Args:
            legacy_points: List of strings or mixed format (old format)
            
        Returns:
            List of TalkingPointSection objects (new format)
        """
        pass
    
    @abstractmethod
    def ensure_talking_points_structure(
        self, 
        subcategory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ensure talking points are in the correct format, migrating if necessary.
        
        Args:
            subcategory_data: Subcategory data from database
            
        Returns:
            Subcategory data with properly formatted talking points
        """
        pass