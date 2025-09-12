"""
System Analytics Router - System-wide metrics and monitoring
Handles system analytics, dashboard data, health monitoring, and active user tracking
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Query,
    Response,
)
from pydantic import BaseModel
import logging

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from ...services.content import AnalyticsService
from ...services.monitoring import SystemHealthService
from app.models.analytics_models import (
    SystemAnalyticsResponse,
    SystemHealthResponse,
    JobAnalyticsResponse
)
from app.core.dependencies import get_current_user, require_analytics_access
from app.models.permissions import PermissionLevel, PermissionCapability, get_user_capabilities

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["system-analytics"])


@router.get("/system", response_model=SystemAnalyticsResponse)
async def get_system_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get system-wide analytics (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # Query all analytics data for the period
        query = "SELECT * FROM c WHERE c.created_at >= @start_time"
        parameters = [{"name": "@start_time", "value": start_time.isoformat()}]
        
        try:
            items_iter = cosmos_db.analytics_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
            items = []
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
        unique_users = set()
        
        for item in analytics:
            # Defensive: only count if field exists and is a number
            minutes = item.get("audio_duration_minutes")
            if isinstance(minutes, (int, float)):
                total_minutes += minutes
            total_jobs += 1
            
            user_id = item.get("user_id")
            if user_id:
                unique_users.add(user_id)

        return SystemAnalyticsResponse(
            total_minutes=total_minutes,
            total_jobs=total_jobs,
            unique_users=len(unique_users),
            period_days=days,
            average_duration=total_minutes / total_jobs if total_jobs > 0 else 0,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system analytics: {str(e)}"
        )


@router.get("/dashboard")
async def get_analytics_dashboard(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get comprehensive analytics dashboard data (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # Initialize dashboard data structure
        dashboard = {
            "period": {
                "days": days,
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat()
            },
            "overview": {
                "total_jobs": 0,
                "total_minutes": 0.0,
                "unique_users": 0,
                "average_duration": 0.0
            },
            "trends": {
                "daily_activity": {},
                "hourly_distribution": {},
                "user_activity": {}
            },
            "system_metrics": {
                "active_sessions": 0,
                "total_sessions": 0,
                "avg_session_duration": 0.0
            },
            "user_metrics": {
                "most_active_users": [],
                "new_users": 0,
                "returning_users": 0
            },
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Get analytics data
        analytics_query = "SELECT * FROM c WHERE c.created_at >= @start_time"
        analytics_params = [{"name": "@start_time", "value": start_time.isoformat()}]
        
        try:
            analytics_items = list(cosmos_db.analytics_container.query_items(
                query=analytics_query,
                parameters=analytics_params,
                enable_cross_partition_query=True,
            ))
        except Exception as e:
            logger.error(f"Error querying analytics: {str(e)}")
            analytics_items = []
        
        # Process analytics data
        unique_users = set()
        daily_activity = {}
        user_minutes = {}
        
        for item in analytics_items:
            # Overview metrics
            minutes = item.get("audio_duration_minutes", 0)
            if isinstance(minutes, (int, float)):
                dashboard["overview"]["total_minutes"] += minutes
            dashboard["overview"]["total_jobs"] += 1
            
            user_id = item.get("user_id")
            if user_id:
                unique_users.add(user_id)
                user_minutes[user_id] = user_minutes.get(user_id, 0) + minutes
            
            # Daily activity trends
            created_at = item.get("created_at")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_key = dt.date().isoformat()
                    daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
                except Exception:
                    continue
        
        # Update overview
        dashboard["overview"]["unique_users"] = len(unique_users)
        if dashboard["overview"]["total_jobs"] > 0:
            dashboard["overview"]["average_duration"] = dashboard["overview"]["total_minutes"] / dashboard["overview"]["total_jobs"]
        
        dashboard["trends"]["daily_activity"] = daily_activity
        
        # Get most active users
        sorted_users = sorted(user_minutes.items(), key=lambda x: x[1], reverse=True)[:10]
        dashboard["user_metrics"]["most_active_users"] = [
            {"user_id": user_id, "total_minutes": minutes} 
            for user_id, minutes in sorted_users
        ]
        
        # Get session data
        try:
            session_query = """
            SELECT c.id, c.user_id, c.created_at, c.last_heartbeat, c.status
            FROM c 
            WHERE c.type = 'session' 
            AND c.created_at >= @start_time
            """
            
            sessions = list(cosmos_db.sessions_container.query_items(
                query=session_query,
                parameters=analytics_params,
                enable_cross_partition_query=True
            ))
            
            dashboard["system_metrics"]["total_sessions"] = len(sessions)
            dashboard["system_metrics"]["active_sessions"] = len([
                s for s in sessions if s.get("status") == "active"
            ])
            
            # Calculate average session duration
            session_durations = []
            for session in sessions:
                try:
                    created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                    last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                    duration_minutes = (last_heartbeat - created_at).total_seconds() / 60
                    session_durations.append(duration_minutes)
                except Exception:
                    continue
            
            if session_durations:
                dashboard["system_metrics"]["avg_session_duration"] = sum(session_durations) / len(session_durations)
        
        except Exception as session_error:
            logger.warning(f"Could not fetch session data: {session_error}")
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting analytics dashboard: {str(e)}"
        )


@router.get("/active-users")
async def get_active_users(
    minutes: int = Query(default=5, description="Minutes to look back for active users"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get active users based on session heartbeats from the session tracking system"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        # Calculate cutoff time for active users
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        # Query for sessions with recent heartbeats
        query = """
        SELECT DISTINCT c.user_id, c.last_heartbeat, c.session_metadata
        FROM c 
        WHERE c.type = 'session' 
        AND c.status = 'active'
        AND c.last_heartbeat >= @cutoff_time
        """
        
        parameters = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
        
        try:
            active_sessions = list(cosmos_db.sessions_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Process active users
            active_users = []
            unique_users = set()
            
            for session in active_sessions:
                user_id = session.get("user_id")
                if user_id and user_id not in unique_users:
                    unique_users.add(user_id)
                    
                    metadata = session.get("session_metadata", {})
                    active_users.append({
                        "user_id": user_id,
                        "last_activity": session["last_heartbeat"],
                        "browser": metadata.get("browser", "Unknown"),
                        "platform": metadata.get("platform", "Unknown")
                    })
            
            return {
                "status": "success",
                "active_users": active_users,
                "count": len(active_users),
                "query_params": {
                    "lookback_minutes": minutes,
                    "cutoff_time": cutoff_time.isoformat(),
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as query_error:
            logger.error(f"Error querying active sessions: {str(query_error)}")
            return {
                "status": "error",
                "active_users": [],
                "count": 0,
                "error": str(query_error),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.error(f"Error getting active users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting active users: {str(e)}"
        )


@router.get("/session-metrics")
async def get_session_metrics(
    days: int = Query(default=7, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get system-wide session metrics from the session tracking system"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        # Calculate time range
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query for sessions in the timeframe
        query = """
        SELECT c.id, c.user_id, c.created_at, c.last_heartbeat, c.status, 
               c.activity_count, c.session_metadata
        FROM c 
        WHERE c.type = 'session' 
        AND c.created_at >= @cutoff_time
        ORDER BY c.created_at DESC
        """
        
        parameters = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
        
        try:
            sessions = list(cosmos_db.sessions_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Calculate metrics
            metrics = {
                "period_days": days,
                "total_sessions": len(sessions),
                "active_sessions": 0,
                "completed_sessions": 0,
                "total_activity_events": 0,
                "unique_users": set(),
                "session_durations": [],
                "browser_stats": {},
                "platform_stats": {},
                "hourly_distribution": {},
                "daily_distribution": {}
            }
            
            for session in sessions:
                # Status metrics
                status = session.get("status", "unknown")
                if status == "active":
                    metrics["active_sessions"] += 1
                elif status == "completed":
                    metrics["completed_sessions"] += 1
                
                # Activity metrics
                metrics["total_activity_events"] += session.get("activity_count", 0)
                
                # User tracking
                user_id = session.get("user_id")
                if user_id:
                    metrics["unique_users"].add(user_id)
                
                # Session duration
                try:
                    created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                    last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                    duration_minutes = (last_heartbeat - created_at).total_seconds() / 60
                    metrics["session_durations"].append(duration_minutes)
                    
                    # Time distribution
                    hour = created_at.hour
                    date_str = created_at.date().isoformat()
                    metrics["hourly_distribution"][hour] = metrics["hourly_distribution"].get(hour, 0) + 1
                    metrics["daily_distribution"][date_str] = metrics["daily_distribution"].get(date_str, 0) + 1
                    
                except Exception:
                    continue
                
                # Client stats
                metadata = session.get("session_metadata", {})
                browser = metadata.get("browser", "Unknown")
                platform = metadata.get("platform", "Unknown")
                
                metrics["browser_stats"][browser] = metrics["browser_stats"].get(browser, 0) + 1
                metrics["platform_stats"][platform] = metrics["platform_stats"].get(platform, 0) + 1
            
            # Finalize metrics
            metrics["unique_users"] = len(metrics["unique_users"])
            
            # Duration statistics
            if metrics["session_durations"]:
                durations = metrics["session_durations"]
                metrics["avg_session_duration"] = sum(durations) / len(durations)
                metrics["max_session_duration"] = max(durations)
                metrics["min_session_duration"] = min(durations)
            else:
                metrics["avg_session_duration"] = 0
                metrics["max_session_duration"] = 0
                metrics["min_session_duration"] = 0
            
            # Remove raw durations from response
            del metrics["session_durations"]
            
            return {
                "status": "success",
                "metrics": metrics,
                "query_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as query_error:
            logger.error(f"Error querying session metrics: {str(query_error)}")
            return {
                "status": "error",
                "metrics": {},
                "error": str(query_error),
                "query_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting session metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting session metrics: {str(e)}"
        )


@router.get("/health")
async def analytics_health_check(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Health check endpoint for analytics services and containers"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "containers": {},
            "services": {}
        }
        
        # Check analytics container
        try:
            test_query = "SELECT TOP 1 c.id FROM c"
            list(cosmos_db.analytics_container.query_items(query=test_query, enable_cross_partition_query=True))
            health_status["containers"]["analytics"] = "healthy"
        except Exception as e:
            health_status["containers"]["analytics"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check sessions container
        try:
            if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
                test_query = "SELECT TOP 1 c.id FROM c WHERE c.type = 'session'"
                list(cosmos_db.sessions_container.query_items(query=test_query, enable_cross_partition_query=True))
                health_status["containers"]["sessions"] = "healthy"
            else:
                health_status["containers"]["sessions"] = "not available"
        except Exception as e:
            health_status["containers"]["sessions"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check audit container if available
        try:
            if hasattr(cosmos_db, 'audit_container') and cosmos_db.audit_container:
                test_query = "SELECT TOP 1 c.id FROM c WHERE c.type = 'audit'"
                list(cosmos_db.audit_container.query_items(query=test_query, enable_cross_partition_query=True))
                health_status["containers"]["audit"] = "healthy"
            else:
                health_status["containers"]["audit"] = "not available"
        except Exception as e:
            health_status["containers"]["audit"] = f"unhealthy: {str(e)}"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/jobs", response_model=JobAnalyticsResponse)
async def get_recent_jobs(
    limit: int = Query(10, ge=1, le=100),
    prompt_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get recent job analytics for monitoring (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        # Build query
        query = "SELECT * FROM c WHERE c.type = 'job'"
        parameters = []
        
        if prompt_id:
            query += " AND c.prompt_id = @prompt_id"
            parameters.append({"name": "@prompt_id", "value": prompt_id})
        
        query += " ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
        parameters.append({"name": "@limit", "value": limit})
        
        try:
            jobs = list(cosmos_db.jobs_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            ))
        except Exception as e:
            logger.error(f"Error querying jobs container: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error querying jobs data: {str(e)}"
            )
        
        # Process jobs for analytics
        analytics_data = []
        for job in jobs:
            job_data = {
                "id": job.get("id"),
                "user_id": job.get("user_id"),
                "status": job.get("status"),
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
                "file_size": job.get("file_size"),
                "duration_minutes": job.get("audio_duration_minutes", 0),
                "prompt_id": job.get("prompt_id")
            }
            analytics_data.append(job_data)
        
        return JobAnalyticsResponse(
            jobs=analytics_data,
            count=len(analytics_data),
            query_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting job analytics: {str(e)}"
        )


@router.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get comprehensive system health metrics (Admin only)"""
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
