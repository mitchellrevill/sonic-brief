import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query, Response, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.config import AppConfig, CosmosDB, get_cosmos_db, DatabaseError
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService
from app.services.system_health_service import SystemHealthService
from app.models.analytics_models import (
    AnalyticsEventRequest,
    UserAnalyticsResponse,
    SystemAnalyticsResponse,
    UserDetailsResponse,
    ExportRequest,
    ExportResponse,
    SystemHealthResponse
)
from app.routers.auth import get_current_user, require_analytics_access, require_user_view_access
from app.middleware.permission_middleware import get_current_user_id
from app.services.permissions import permission_service
from app.models.permissions import PermissionLevel
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analytics"])


# Custom admin dependency that returns full user object
async def require_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require admin permission and return the full user object
    """
    user_permission = current_user.get("permission")
    if not permission_service.has_permission_level(user_permission, PermissionLevel.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin permission required"
        )
    return current_user


# Capability-based dependencies for analytics access
async def require_analytics_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require analytics viewing capability and return the full user object
    """
    from app.models.permissions import PermissionCapability
    from app.services.permissions import permission_service
    
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})
    
    # Get effective capabilities (base + custom)
    effective_capabilities = permission_service.get_user_capabilities(user_permission, custom_capabilities)
    
    # Check if user has analytics access
    if not effective_capabilities.get(PermissionCapability.CAN_VIEW_ANALYTICS, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Analytics access required. You need the 'can_view_analytics' capability."
        )
    return current_user


async def require_system_management_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require system management capability and return the full user object
    """
    from app.models.permissions import PermissionCapability
    from app.services.permissions import permission_service
    
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})
    
    # Get effective capabilities (base + custom)
    effective_capabilities = permission_service.get_user_capabilities(user_permission, custom_capabilities)
    
    # Check if user has system management access
    if not effective_capabilities.get(PermissionCapability.CAN_MANAGE_SYSTEM, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="System management access required. You need the 'can_manage_system' capability."
        )
    return current_user


async def require_user_management_access(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Require user viewing capability and return the full user object
    """
    from app.models.permissions import PermissionCapability
    from app.services.permissions import permission_service
    
    user_permission = current_user.get("permission")
    custom_capabilities = current_user.get("custom_capabilities", {})
    
    # Get effective capabilities (base + custom)
    effective_capabilities = permission_service.get_user_capabilities(user_permission, custom_capabilities)
    
    # Check if user has user management access
    if not effective_capabilities.get(PermissionCapability.CAN_VIEW_USERS, False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User management access required. You need the 'can_view_users' capability."
        )
    return current_user


@router.post("/analytics/event")
async def track_analytics_event(
    event_request: AnalyticsEventRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Track an analytics event
    Note: This is typically called internally by other endpoints
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        event_id = await analytics_service.track_event(
            event_type=event_request.event_type,
            user_id=current_user["id"],
            metadata=event_request.metadata,
            job_id=event_request.job_id
        )
        
        return {
            "status": "success",
            "event_id": event_id,
            "message": "Analytics event tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error tracking analytics event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error tracking analytics event: {str(e)}"
        )


@router.get("/analytics/users/{user_id}", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_user_management_access)
):
    """
    Get analytics for a specific user (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        analytics_data = await analytics_service.get_user_analytics(user_id, days)
        
        return UserAnalyticsResponse(**analytics_data)
        
    except Exception as e:
        logger.error(f"Error getting user analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user analytics: {str(e)}"
        )


@router.get("/analytics/system", response_model=SystemAnalyticsResponse)
async def get_system_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Get system-wide analytics (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        analytics_data = await analytics_service.get_system_analytics(days)
        
        return SystemAnalyticsResponse(**analytics_data)
        
    except Exception as e:
        logger.error(f"Error getting system analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system analytics: {str(e)}"
        )


@router.get("/auth/users/{user_id}/details", response_model=UserDetailsResponse)
async def get_user_details(
    user_id: str,
    include_analytics: bool = Query(True),
    current_user: Dict[str, Any] = Depends(require_user_management_access)
):
    """
    Get detailed information about a specific user (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        
        # Get user data
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get analytics if requested
        analytics = None
        if include_analytics:
            analytics_service = AnalyticsService(cosmos_db)
            analytics_data = await analytics_service.get_user_analytics(user_id, days=30)
            analytics = analytics_data.get('analytics', {})
        
        # Build response
        user_details = {
            "id": user.get("id"),
            "email": user.get("email"),
            "full_name": user.get("full_name"),
            "permission": user.get("permission"),
            "source": user.get("source"),
            "microsoft_oid": user.get("microsoft_oid"),
            "tenant_id": user.get("tenant_id"),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login"),
            "is_active": user.get("is_active", True),
            "permission_changed_at": user.get("permission_changed_at"),
            "permission_changed_by": user.get("permission_changed_by"),
            "permission_history": user.get("permission_history", []),
            "updated_at": user.get("updated_at"),
            "analytics": analytics
        }
        
        return UserDetailsResponse(**user_details)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user details: {str(e)}"
        )


@router.post("/export/users/{format}")
async def export_users(
    format: str,
    export_request: Optional[ExportRequest] = None,
    current_user: Dict[str, Any] = Depends(require_user_management_access)
):
    """
    Export users data in specified format (Admin only)
    """
    if format not in ['csv', 'pdf']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format must be 'csv' or 'pdf'"
        )
    
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        export_service = ExportService(cosmos_db)
        
        filters = None
        if export_request:
            filters = export_request.filters
        
        if format == 'csv':
            result = await export_service.export_users_csv(filters)
        else:
            # For PDF, we'll export a summary report
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="PDF export for all users not yet implemented"
            )
        
        if result['status'] == 'error':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        # Return file for download
        return FileResponse(
            path=result['file_path'],
            media_type=result['content_type'],
            filename=result['filename'],
            background=lambda: export_service.cleanup_temp_file(result['file_path'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting users: {str(e)}"
        )


@router.get("/export/users/{user_id}/pdf")
async def export_user_details_pdf(
    user_id: str,
    include_analytics: bool = Query(True),
    current_user: Dict[str, Any] = Depends(require_user_view_access)
):
    """
    Export individual user details as PDF (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        export_service = ExportService(cosmos_db)
        
        result = await export_service.export_user_details_pdf(user_id, include_analytics)
        
        if result['status'] == 'error':
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        # Return file for download
        return FileResponse(
            path=result['file_path'],
            media_type=result['content_type'],
            filename=result['filename'],
            background=lambda: export_service.cleanup_temp_file(result['file_path'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting user details PDF: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting user details PDF: {str(e)}"
        )


@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Get comprehensive analytics dashboard data (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        # Get system analytics
        system_analytics = await analytics_service.get_system_analytics(days)
        
        # Get user permission stats (existing functionality)
        optimizer = cosmos_db.permission_optimizer
        permission_stats = await optimizer.get_permission_counts()
        
        # Combine data for dashboard
        dashboard_data = {
            "system_analytics": system_analytics,
            "permission_stats": permission_stats,
            "period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting analytics dashboard: {str(e)}"
        )


class SessionEventRequest(BaseModel):
    action: str  # start, heartbeat, end, focus, blur, page_view
    page: Optional[str] = None
    timestamp: Optional[str] = None
    session_duration: Optional[int] = None


@router.post("/analytics/session")
async def track_session_event(
    session_request: SessionEventRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Track user session events
    
    Actions:
    - start: User session started
    - heartbeat: User is actively using the app
    - end: User session ended
    - focus: User focused on the app window
    - blur: User switched away from the app
    - page_view: User navigated to a new page
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        # Extract request metadata
        user_agent = request.headers.get("User-Agent")
        ip_address = request.headers.get("X-Forwarded-For") or request.client.host
        
        session_event_id = await analytics_service.track_user_session(
            user_id=current_user["id"],
            action=session_request.action,
            page=session_request.page,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        return {
            "status": "success",
            "session_event_id": session_event_id,
            "message": f"Session {session_request.action} tracked successfully"
        }
        
    except Exception as e:
        logger.error(f"Error tracking session event: {str(e)}")
        # Don't fail the request if session tracking fails
        return {
            "status": "error",
            "message": "Session tracking failed but request continues"
        }


@router.get("/analytics/active-users")
async def get_active_users(
    minutes: int = Query(default=5, description="Minutes to look back for active users"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Get list of currently active users (users with recent session activity)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        active_user_ids = await analytics_service.get_active_users(minutes=minutes)
        
        return {
            "status": "success",
            "data": {
                "active_users": active_user_ids,
                "count": len(active_user_ids),
                "period_minutes": minutes,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting active users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving active users: {str(e)}"
        )


@router.get("/analytics/user-session-duration/{user_id}")
async def get_user_session_duration(
    user_id: str,
    days: int = Query(default=1, description="Number of days to look back"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Get total session duration for a specific user
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        duration_minutes = await analytics_service.get_user_session_duration(
            user_id=user_id, 
            days=days
        )
        
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "total_session_duration_minutes": duration_minutes,
                "period_days": days,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user session duration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving session duration: {str(e)}"
        )


@router.get("/analytics/debug/container-status")
async def check_analytics_container_status(
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Check if the analytics events container is working properly (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        # Verify container
        container_working = await analytics_service.verify_events_container()
        
        # Count existing events
        events_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'event'"
        events_counts = list(cosmos_db.events_container.query_items(
            query=events_count_query,
            enable_cross_partition_query=True
        ))
        events_count = events_counts[0] if events_counts else 0
        
        return {
            "status": "success",
            "data": {
                "container_accessible": container_working,
                "total_events": events_count,
                "container_name": getattr(cosmos_db.events_container, 'id', 'unknown'),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error checking analytics container status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking container status: {str(e)}"
        )


@router.post("/analytics/debug/backfill-events")
async def backfill_analytics_events(
    limit: int = Query(default=10, description="Maximum number of jobs to backfill"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Backfill analytics events for existing jobs (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        events_created = await analytics_service.create_job_events_for_existing_jobs(limit)
        
        return {
            "status": "success",
            "data": {
                "events_created": events_created,
                "jobs_processed": limit,
                "message": f"Backfilled {events_created} analytics events"
            }
        }
        
    except Exception as e:
        logger.error(f"Error backfilling analytics events: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error backfilling events: {str(e)}"
        )


@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Get comprehensive system health metrics (Admin only)
    """
    try:
        health_service = SystemHealthService()
        health_data = await health_service.get_system_health()
        
        return health_data
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system health: {str(e)}"
        )


@router.get("/analytics/debug/data-sources")
async def diagnose_analytics_data_sources(
    days: int = Query(default=30, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Comprehensive diagnostic of analytics data sources (Admin only)
    Helps understand why the system might be returning mock data
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        diagnostic_data = await analytics_service.diagnose_analytics_data_sources(days)
        
        return {
            "status": "success",
            "data": diagnostic_data
        }
        
    except Exception as e:
        logger.error(f"Error running analytics diagnostics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running diagnostics: {str(e)}"
        )


@router.get("/analytics/debug/quick-summary")
async def get_quick_data_summary(
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Quick summary of data availability across containers (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        
        summary = await analytics_service.get_quick_data_summary()
        
        return {
            "status": "success",
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting quick data summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting summary: {str(e)}"
        )
