# Abstract base classes for service layer consistency
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from app.models.permissions import PermissionLevel, PermissionCapability

class BaseService(ABC):
    """Base service interface for common patterns"""
    
    def __init__(self):
        self.logger = self._get_logger()
    
    @abstractmethod
    def _get_logger(self):
        """Get service-specific logger"""
        pass

class PermissionServiceInterface(ABC):
    """Interface for permission-related operations"""
    
    @abstractmethod
    async def get_user_permission(self, user_id: str) -> Dict[str, Any]:
        """Get user's permission level and capabilities"""
        pass
    
    @abstractmethod
    async def has_permission_level(self, user_perm: Dict, required_level: PermissionLevel) -> bool:
        """Check if user has required permission level"""
        pass
    
    @abstractmethod
    async def has_capability(self, user_id: str, capability: PermissionCapability) -> bool:
        """Check if user has specific capability"""
        pass
    
    @abstractmethod
    async def update_user_permissions(self, user_id: str, new_permissions: Dict) -> bool:
        """Update user's permissions"""
        pass

class JobServiceInterface(ABC):
    """Interface for job-related operations"""
    
    @abstractmethod
    async def get_jobs(self, skip: int = 0, limit: int = 10, user_id: Optional[str] = None) -> List[Dict]:
        """Get jobs list"""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str, user_id: str) -> Dict[str, Any]:
        """Get specific job"""
        pass
    
    @abstractmethod
    async def create_job(self, job_data: Dict, user_id: str) -> Dict[str, Any]:
        """Create new job"""
        pass
    
    @abstractmethod
    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """Delete job"""
        pass

class AnalyticsServiceInterface(ABC):
    """Interface for analytics operations"""
    
    @abstractmethod
    async def get_user_analytics(self, user_id: str, date_from: Optional[str], date_to: Optional[str]) -> Dict:
        """Get user analytics data"""
        pass
    
    @abstractmethod
    async def get_system_analytics(self, date_from: Optional[str], date_to: Optional[str]) -> Dict:
        """Get system analytics data"""
        pass
    
    @abstractmethod
    async def record_event(self, event_data: Dict) -> bool:
        """Record analytics event"""
        pass
