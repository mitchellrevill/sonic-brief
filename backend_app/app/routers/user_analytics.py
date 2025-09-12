# User Analytics Router - Split from monolithic analytics.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, Dict, Any
from app.core.dependencies import require_analytics_access, get_current_user
from app.models.analytics_models import UserAnalyticsResponse, UserMinutesResponse, UserDetailsResponse
from app.services.analytics_service import analytics_service
from app.utils.logging_config import get_logger

router = APIRouter(prefix="/analytics/users", tags=["User Analytics"])
logger = get_logger(__name__)

@router.get("/{user_id}", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    user_id: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(require_analytics_access)
):
    """Get analytics data for a specific user"""
    try:
        # Implementation would be moved from analytics.py
        return await analytics_service.get_user_analytics(user_id, date_from, date_to)
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user analytics")

@router.get("/{user_id}/minutes", response_model=UserMinutesResponse)
async def get_user_minutes(
    user_id: str,
    current_user: dict = Depends(require_analytics_access)
):
    """Get user processing minutes data"""
    try:
        return await analytics_service.get_user_minutes(user_id)
    except Exception as e:
        logger.error(f"Error getting user minutes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user minutes")

@router.get("/{user_id}/details", response_model=UserDetailsResponse) 
async def get_user_details(
    user_id: str,
    current_user: dict = Depends(require_analytics_access)
):
    """Get detailed user information"""
    try:
        return await analytics_service.get_user_details(user_id)
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user details")

# Additional user-specific endpoints would be moved here from analytics.py
