# System Analytics Router - Split from monolithic analytics.py  
from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Optional, Dict, Any
from app.core.dependencies import require_admin, get_current_user
from app.models.analytics_models import SystemAnalyticsResponse, SystemHealthResponse
from app.services.analytics_service import analytics_service
from app.utils.logging_config import get_logger

router = APIRouter(prefix="/analytics/system", tags=["System Analytics"])
logger = get_logger(__name__)

@router.get("", response_model=SystemAnalyticsResponse)
async def get_system_analytics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Get system-wide analytics data"""
    try:
        return await analytics_service.get_system_analytics(date_from, date_to)
    except Exception as e:
        logger.error(f"Error getting system analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system analytics")

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: dict = Depends(require_admin)
):
    """Get system health metrics"""
    try:
        return await analytics_service.get_system_health()
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system health")

@router.get("/export/csv")
async def export_system_csv(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Export system analytics to CSV"""
    try:
        csv_data = await analytics_service.export_system_csv(date_from, date_to)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=system_analytics.csv"}
        )
    except Exception as e:
        logger.error(f"Error exporting system CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to export system analytics")

# Additional system endpoints would be moved here
