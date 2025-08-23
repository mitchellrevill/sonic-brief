import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query, Response, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.config import AppConfig, CosmosDB, DatabaseError, get_cosmos_db
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
    SystemHealthResponse,
    JobAnalyticsResponse,
    UserMinutesResponse
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


# Deprecated external analytics event endpoint removed as part of cleanup.


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
        # Defensive: ensure all required fields are present
        analytics = analytics_data.get('analytics', {})
        if not analytics:
            analytics = {
                "transcription_stats": {"total_minutes": 0.0, "total_jobs": 0, "average_job_duration": 0.0},
                "activity_stats": {"login_count": 0, "jobs_created": 0, "last_activity": None},
                "usage_patterns": {"most_active_hours": [], "most_used_transcription_method": None, "file_upload_count": 0, "text_input_count": 0}
            }
        return {
            "user_id": user_id,
            "period_days": analytics_data.get("period_days", days),
            "start_date": analytics_data.get("start_date"),
            "end_date": analytics_data.get("end_date"),
            "analytics": analytics
        }
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
        # Query the analytics table for system-wide analytics (voice_analytics)
        # Use the analytics_container as in other endpoints
        query = (
            "SELECT * FROM c WHERE c.timestamp >= @start_date"
        )
        from datetime import datetime, timedelta, timezone
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        parameters = [
            {"name": "@start_date", "value": start_date.isoformat()}
        ]
        items = []
        try:
            container = cosmos_db.analytics_container
            items_iter = container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
            for item in items_iter:
                items.append(item)
        except Exception as e:
            logger.error(f"Error querying analytics container: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error querying analytics data: {str(e)}"
            )

        # Defensive: ensure analytics is a list
        analytics = items

        # Calculate total minutes and total jobs
        total_minutes = 0.0
        total_jobs = 0
        for item in analytics:
            # Defensive: only count if field exists and is a number
            minutes = item.get("audio_duration_minutes")
            if isinstance(minutes, (int, float)):
                total_minutes += minutes
            total_jobs += 1

        # Defensive: analytics must be a dict for SystemAnalyticsResponse
        # Provide summary stats in analytics, and raw records as a separate field
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_minutes": total_minutes,
            "total_jobs": total_jobs,
            "analytics": {
                "records": analytics,
                "total_minutes": total_minutes,
                "total_jobs": total_jobs
            }
        }
    except Exception as e:
        logger.error(f"Error getting system analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system analytics: {str(e)}"
        )


@router.get("/export/system/csv")
async def export_system_analytics_csv(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Export system analytics as CSV, scoped by days."""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        export_service = ExportService(cosmos_db)
        result = await export_service.export_system_analytics_csv(days)
        if result.get('status') != 'success':
            raise HTTPException(status_code=500, detail=result.get('message', 'Export failed'))
        return FileResponse(
            path=result['file_path'],
            media_type=result['content_type'],
            filename=result['filename'],
            background=lambda: export_service.cleanup_temp_file(result['file_path'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting system analytics CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to export system analytics CSV")


@router.get("/analytics/users/{user_id}/minutes", response_model=UserMinutesResponse)
async def get_user_minutes(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_user_management_access)
):
    """Return per-job minute records for a user along with totals."""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        data = await analytics_service.get_user_minutes_records(user_id, days)
        # Ensure required fields exist
        return {
            "user_id": data.get("user_id", user_id),
            "period_days": data.get("period_days", days),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "total_minutes": data.get("total_minutes", 0.0),
            "total_records": data.get("total_records", 0),
            "records": data.get("records", []),
        }
    except Exception as e:
        logger.error(f"Error getting user minutes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting user minutes: {str(e)}"
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
    days: int = Query(30, ge=1, le=365, description="Analytics scope in days"),
    current_user: Dict[str, Any] = Depends(require_user_view_access)
):
    """
    Export individual user details as PDF (Admin only)
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        export_service = ExportService(cosmos_db)
        result = await export_service.export_user_details_pdf(user_id, include_analytics, days)
        
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

@router.get("/analytics/health")
async def analytics_health_check(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Health check endpoint for analytics services and containers."""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        
        health_status = {
            "status": "healthy",
            "containers": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check each container
        containers_to_check = [
            ("analytics_container", "Analytics"),
            ("sessions_container", "Sessions"),
            ("events_container", "Events"),
            ("jobs_container", "Jobs"),
            ("auth_container", "Auth")
        ]
        
        for container_attr, container_name in containers_to_check:
            try:
                container = getattr(cosmos_db, container_attr, None)
                if container is not None:
                    # Try to read from the container (this will test connectivity)
                    # We'll just check if we can query with a limit of 1
                    list(container.query_items(
                        query="SELECT TOP 1 c.id FROM c",
                        enable_cross_partition_query=True
                    ))
                    health_status["containers"][container_name] = {
                        "status": "available",
                        "accessible": True
                    }
                else:
                    health_status["containers"][container_name] = {
                        "status": "not_configured",
                        "accessible": False
                    }
            except Exception as e:
                health_status["containers"][container_name] = {
                    "status": "error",
                    "accessible": False,
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.post("/analytics/session")
async def post_session_event(
    session_request: SessionEventRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Track a user session event (start, heartbeat, end, focus, blur, page_view)."""
    try:
        logger.info(f"📊 Session tracking request: {session_request.action} for user {current_user['id']}")
        
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        
        # Log container availability
        logger.info(f"Sessions container available: {hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container is not None}")
        
        analytics_service = AnalyticsService(cosmos_db)

        # Extract request metadata
        user_agent = request.headers.get("User-Agent")
        ip_address = request.headers.get("X-Forwarded-For") or (request.client.host if request.client else None)

        session_event_id = await analytics_service.track_user_session(
            user_id=current_user["id"],
            action=session_request.action,
            page=session_request.page,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        logger.info(f"✅ Session event tracked successfully: ID={session_event_id}")
        
        return {
            "status": "success",
            "session_event_id": session_event_id,
            "message": f"Session {session_request.action} tracked successfully",
        }
    except Exception as e:
        logger.error(f"❌ Error tracking session event: {str(e)}")
        logger.error(f"Full error details: {repr(e)}")
        
        # Return error details for debugging
        return {
            "status": "error", 
            "session_event_id": "",
            "message": f"Session tracking failed: {str(e)}"
        }


@router.get("/analytics/active-users")
async def get_active_users(
    minutes: int = Query(default=5, description="Minutes to look back for active users"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Debug endpoint: Return the first N active user session events from the events container.
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        active_users = await analytics_service.get_active_users(minutes)
        # Defensive: always return a list and count
        if not isinstance(active_users, list):
            active_users = []
        return {
            "status": "success",
            "data": {
                "active_users": active_users,
                "count": len(active_users),
                "period_minutes": minutes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.error(f"Error getting active users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting active users: {str(e)}"
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


@router.get("/analytics/users/{user_id}/audit-logs")
async def get_user_audit_logs(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_user_management_access),
):
    """Return audit log items for a user within a date range."""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)

        items = []
        container = getattr(cosmos_db, "audit_container", None) or getattr(cosmos_db, "events_container", None)
        if container is None:
            # Fallback to jobs container directly
            jobs = []
            jq = (
                "SELECT c.id, c.created_at FROM c WHERE c.user_id = @user_id AND c.created_at >= @start_ms ORDER BY c.created_at DESC"
            )
            jp = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start_ms", "value": int(start_dt.timestamp() * 1000)},
            ]
            for j in cosmos_db.jobs_container.query_items(query=jq, parameters=jp, enable_cross_partition_query=True):
                ts_ms = j.get("created_at")
                ts_iso = (
                    datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
                    if isinstance(ts_ms, (int, float))
                    else None
                )
                items.append(
                    {
                        "id": j.get("id"),
                        "timestamp": ts_iso,
                        "event_type": "job_created",
                        "resource_type": "job",
                        "resource_id": j.get("id"),
                        "metadata": {},
                    }
                )
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "records": items,
            }

        query = (
            "SELECT c.id, c.timestamp, c.event_type, c.resource_type, c.resource_id, c.metadata "
            "FROM c WHERE c.user_id = @user_id AND c.timestamp >= @start AND c.timestamp <= @end "
            "ORDER BY c.timestamp DESC"
        )
        params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@start", "value": start_dt.isoformat()},
            {"name": "@end", "value": end_dt.isoformat()},
        ]
        try:
            for it in container.query_items(query=query, parameters=params, enable_cross_partition_query=True):
                items.append(it)
        except Exception as e:
            logger.warning(f"Audit logs query failed: {e}; falling back to jobs")
            # Fallback to jobs container if audit/events query fails
            jq = (
                "SELECT c.id, c.created_at FROM c WHERE c.user_id = @user_id AND c.created_at >= @start_ms ORDER BY c.created_at DESC"
            )
            jp = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start_ms", "value": int(start_dt.timestamp() * 1000)},
            ]
            for j in cosmos_db.jobs_container.query_items(query=jq, parameters=jp, enable_cross_partition_query=True):
                ts_ms = j.get("created_at")
                ts_iso = (
                    datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
                    if isinstance(ts_ms, (int, float))
                    else None
                )
                items.append(
                    {
                        "id": j.get("id"),
                        "timestamp": ts_iso,
                        "event_type": "job_created",
                        "resource_type": "job",
                        "resource_id": j.get("id"),
                        "metadata": {},
                    }
                )

        return {
            "user_id": user_id,
            "period_days": days,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "records": items,
        }
    except Exception as e:
        logger.error(f"Error getting user audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit logs")


@router.get("/analytics/jobs", response_model=JobAnalyticsResponse)
async def get_recent_jobs(
    limit: int = Query(10, ge=1, le=100),
    prompt_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """
    Get recent jobs for analytics dashboard (Admin only)
    Optionally filter by prompt_id
    """
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)
        analytics_service = AnalyticsService(cosmos_db)
        jobs = await analytics_service.get_recent_jobs(limit=limit, prompt_id=prompt_id)
        return {"jobs": jobs, "count": len(jobs)}
    except Exception as e:
        logger.error(f"Error getting recent jobs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recent jobs: {str(e)}"
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
