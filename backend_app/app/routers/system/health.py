"""
Health Router - System health monitoring and diagnostics
Handles health checks, system status, monitoring, and uptime tracking
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
from ...services.monitoring import SystemHealthService
from app.models.analytics_models import SystemHealthResponse
from app.core.dependencies import get_current_user, require_analytics_access
from app.models.permissions import PermissionLevel, PermissionCapability, get_user_capabilities

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["system-health"])


@router.get("/health", response_model=SystemHealthResponse)
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


@router.get("/health/detailed")
async def get_detailed_health_check(
    include_performance: bool = Query(default=True, description="Include performance metrics"),
    include_dependencies: bool = Query(default=True, description="Include dependency status"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get detailed system health with performance metrics and dependency status"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        health_check = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy",
            "services": {},
            "dependencies": {},
            "performance": {},
            "uptime": {},
            "version_info": {}
        }
        
        # Check core services
        service_checks = {
            "database": False,
            "analytics_container": False,
            "sessions_container": False,
            "storage": False,
            "authentication": False
        }
        
        # Database connectivity check
        try:
            test_query = "SELECT TOP 1 c.id FROM c"
            list(cosmos_db.analytics_container.query_items(
                query=test_query,
                enable_cross_partition_query=True
            ))
            service_checks["database"] = True
            service_checks["analytics_container"] = True
            health_check["services"]["database"] = {
                "status": "healthy",
                "response_time_ms": None,  # Could add timing
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        except Exception as db_error:
            health_check["services"]["database"] = {
                "status": "unhealthy",
                "error": str(db_error),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            health_check["overall_status"] = "degraded"
        
        # Sessions container check
        try:
            if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
                test_session_query = "SELECT TOP 1 c.id FROM c WHERE c.type = 'session'"
                list(cosmos_db.sessions_container.query_items(
                    query=test_session_query,
                    enable_cross_partition_query=True
                ))
                service_checks["sessions_container"] = True
                health_check["services"]["sessions"] = {
                    "status": "healthy",
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
            else:
                health_check["services"]["sessions"] = {
                    "status": "not_available",
                    "message": "Sessions container not configured",
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
        except Exception as session_error:
            health_check["services"]["sessions"] = {
                "status": "unhealthy",
                "error": str(session_error),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        
        # Authentication service check
        try:
            # Simple check - if we got here, auth is working
            service_checks["authentication"] = True
            health_check["services"]["authentication"] = {
                "status": "healthy",
                "current_user": current_user.get("id", "unknown"),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        except Exception as auth_error:
            health_check["services"]["authentication"] = {
                "status": "unhealthy",
                "error": str(auth_error),
                "last_check": datetime.now(timezone.utc).isoformat()
            }
        
        # Performance metrics
        if include_performance:
            try:
                # Get recent activity metrics
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=15)
                
                # Check recent analytics activity
                recent_analytics_query = "SELECT VALUE COUNT(1) FROM c WHERE c.created_at >= @cutoff_time"
                recent_analytics_params = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
                
                recent_analytics_count = list(cosmos_db.analytics_container.query_items(
                    query=recent_analytics_query,
                    parameters=recent_analytics_params,
                    enable_cross_partition_query=True
                ))
                
                health_check["performance"]["recent_analytics_events"] = recent_analytics_count[0] if recent_analytics_count else 0
                
                # Check session activity if available
                if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
                    recent_sessions_query = """
                    SELECT VALUE COUNT(1) 
                    FROM c 
                    WHERE c.type = 'session' 
                    AND c.last_heartbeat >= @cutoff_time
                    """
                    
                    recent_sessions_count = list(cosmos_db.sessions_container.query_items(
                        query=recent_sessions_query,
                        parameters=recent_analytics_params,
                        enable_cross_partition_query=True
                    ))
                    
                    health_check["performance"]["active_sessions_last_15min"] = recent_sessions_count[0] if recent_sessions_count else 0
                
            except Exception as perf_error:
                health_check["performance"]["error"] = str(perf_error)
        
        # Dependency status
        if include_dependencies:
            health_check["dependencies"] = {
                "cosmos_db": "healthy" if service_checks["database"] else "unhealthy",
                "analytics_container": "healthy" if service_checks["analytics_container"] else "unhealthy", 
                "sessions_container": "healthy" if service_checks["sessions_container"] else "not_available",
                "storage_account": "unknown",  # Would need storage service check
                "openai_api": "unknown"  # Would need API check
            }
        
        # System uptime and version info
        health_check["version_info"] = {
            "api_version": "1.0.0",  # Could be from config
            "python_version": None,  # Could add sys.version
            "deployment_time": None  # Could track deployment timestamp
        }
        
        # Determine overall status
        unhealthy_services = [
            name for name, status in health_check["services"].items() 
            if isinstance(status, dict) and status.get("status") == "unhealthy"
        ]
        
        if unhealthy_services:
            health_check["overall_status"] = "unhealthy" if len(unhealthy_services) > 1 else "degraded"
            health_check["issues"] = unhealthy_services
        
        return health_check
        
    except Exception as e:
        logger.error(f"Error in detailed health check: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in detailed health check: {str(e)}"
        )


@router.get("/health/quick")
async def get_quick_health_check():
    """Quick health check endpoint - no authentication required"""
    try:
        # Simple connectivity check
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        # Quick database ping
        test_query = "SELECT TOP 1 c.id FROM c"
        list(cosmos_db.analytics_container.query_items(
            query=test_query,
            enable_cross_partition_query=True
        ))
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "analytics_api",
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Quick health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "analytics_api",
            "version": "1.0.0"
        }


@router.get("/status")
async def get_system_status(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get basic system status information"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        status_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_time": datetime.now(timezone.utc).isoformat(),
            "environment": getattr(config, 'ENVIRONMENT', 'unknown'),
            "api_version": "1.0.0",
            "database_status": "unknown",
            "containers_status": {},
            "user_info": {
                "current_user_id": current_user.get("id"),
                "permission_level": current_user.get("permission"),
                "authenticated": True
            }
        }
        
        # Check database status
        try:
            test_query = "SELECT TOP 1 c.id FROM c"
            list(cosmos_db.analytics_container.query_items(
                query=test_query,
                enable_cross_partition_query=True
            ))
            status_info["database_status"] = "connected"
            status_info["containers_status"]["analytics"] = "accessible"
        except Exception as db_error:
            status_info["database_status"] = "error"
            status_info["database_error"] = str(db_error)
            status_info["containers_status"]["analytics"] = "inaccessible"
        
        # Check sessions container
        try:
            if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
                session_query = "SELECT TOP 1 c.id FROM c WHERE c.type = 'session'"
                list(cosmos_db.sessions_container.query_items(
                    query=session_query,
                    enable_cross_partition_query=True
                ))
                status_info["containers_status"]["sessions"] = "accessible"
            else:
                status_info["containers_status"]["sessions"] = "not_configured"
        except Exception:
            status_info["containers_status"]["sessions"] = "inaccessible"
        
        # Check audit container if available
        try:
            if hasattr(cosmos_db, 'audit_container') and cosmos_db.audit_container:
                audit_query = "SELECT TOP 1 c.id FROM c WHERE c.type = 'audit'"
                list(cosmos_db.audit_container.query_items(
                    query=audit_query,
                    enable_cross_partition_query=True
                ))
                status_info["containers_status"]["audit"] = "accessible"
            else:
                status_info["containers_status"]["audit"] = "not_configured"
        except Exception:
            status_info["containers_status"]["audit"] = "inaccessible"
        
        return status_info
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e),
            "system_time": datetime.now(timezone.utc).isoformat()
        }


@router.get("/monitoring/metrics")
async def get_monitoring_metrics(
    hours: int = Query(default=24, ge=1, le=168, description="Hours of metrics to retrieve"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get system monitoring metrics for the specified time period"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        metrics = {
            "period_hours": hours,
            "start_time": cutoff_time.isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "analytics_metrics": {},
            "session_metrics": {},
            "system_metrics": {},
            "error_metrics": {}
        }
        
        # Analytics activity metrics
        try:
            analytics_query = "SELECT * FROM c WHERE c.created_at >= @cutoff_time"
            analytics_params = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
            
            analytics_items = list(cosmos_db.analytics_container.query_items(
                query=analytics_query,
                parameters=analytics_params,
                enable_cross_partition_query=True
            ))
            
            metrics["analytics_metrics"] = {
                "total_events": len(analytics_items),
                "unique_users": len(set(item.get("user_id") for item in analytics_items if item.get("user_id"))),
                "total_minutes_processed": sum(
                    item.get("audio_duration_minutes", 0) 
                    for item in analytics_items 
                    if isinstance(item.get("audio_duration_minutes"), (int, float))
                )
            }
        except Exception as analytics_error:
            metrics["analytics_metrics"]["error"] = str(analytics_error)
        
        # Session activity metrics
        try:
            if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
                session_query = """
                SELECT c.id, c.user_id, c.created_at, c.last_heartbeat, 
                       c.status, c.activity_count
                FROM c 
                WHERE c.type = 'session' 
                AND c.created_at >= @cutoff_time
                """
                
                sessions = list(cosmos_db.sessions_container.query_items(
                    query=session_query,
                    parameters=analytics_params,
                    enable_cross_partition_query=True
                ))
                
                active_sessions = [s for s in sessions if s.get("status") == "active"]
                total_activity = sum(s.get("activity_count", 0) for s in sessions)
                
                metrics["session_metrics"] = {
                    "total_sessions": len(sessions),
                    "active_sessions": len(active_sessions),
                    "unique_active_users": len(set(s.get("user_id") for s in active_sessions if s.get("user_id"))),
                    "total_activity_events": total_activity
                }
        except Exception as session_error:
            metrics["session_metrics"]["error"] = str(session_error)
        
        # System performance indicators
        metrics["system_metrics"] = {
            "query_timestamp": datetime.now(timezone.utc).isoformat(),
            "database_responsive": True,  # If we got here, it's responsive
            "containers_accessible": len([
                k for k, v in {
                    "analytics": True,  # We queried it successfully
                    "sessions": hasattr(cosmos_db, 'sessions_container'),
                    "audit": hasattr(cosmos_db, 'audit_container')
                }.items() if v
            ])
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting monitoring metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting monitoring metrics: {str(e)}"
        )
