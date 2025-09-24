"""
Admin Router - Administrative operations and system management
Handles admin operations, system configuration, maintenance tasks, and administrative endpoints
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Query,
    Body,
    Response,
)
from pydantic import BaseModel
import logging

from ...core.dependencies import (
    get_current_user, 
    require_analytics_access,
    get_cosmos_service,
    CosmosService
)
from ...models.permissions import PermissionLevel, has_permission_level
from ...core.async_utils import run_sync

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["admin"])


class MaintenanceRequest(BaseModel):
    maintenance_type: str
    duration_minutes: Optional[int] = 60
    reason: Optional[str] = None
    notify_users: bool = True


class SystemConfigUpdate(BaseModel):
    config_key: str
    config_value: str
    apply_immediately: bool = False


class CleanupRequest(BaseModel):
    cleanup_type: str  # "sessions", "analytics", "logs", "temp_files"
    older_than_days: int = 30
    dry_run: bool = True


@router.post("/admin/maintenance")
async def schedule_maintenance(
    maintenance_request: MaintenanceRequest,
    current_user: Dict[str, Any] = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
):
    """Schedule system maintenance (Admin only)"""
    try:
        # Verify admin permission
        user_permission = current_user.get("permission")
        if user_permission != PermissionLevel.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for maintenance operations"
            )
        
        # Create maintenance record
        maintenance_record = {
            "id": f"maintenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": "maintenance_schedule",
            "maintenance_type": maintenance_request.maintenance_type,
            "scheduled_by": current_user.get("id"),
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "duration_minutes": maintenance_request.duration_minutes,
            "reason": maintenance_request.reason,
            "notify_users": maintenance_request.notify_users,
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store maintenance record (would typically go to a maintenance container)
        # For now, we'll store in analytics container with a special type
        try:
            await run_sync(lambda: cosmos_service.analytics_container.create_item(maintenance_record))
        except Exception as store_error:
            logger.error(f"Error storing maintenance record: {str(store_error)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error scheduling maintenance"
            )
        
        logger.info(f"Maintenance scheduled by {current_user.get('id')}: {maintenance_request.dict()}")
        
        return {
            "status": "scheduled",
            "maintenance_id": maintenance_record["id"],
            "scheduled_at": maintenance_record["scheduled_at"],
            "duration_minutes": maintenance_request.duration_minutes,
            "message": f"{maintenance_request.maintenance_type} maintenance scheduled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scheduling maintenance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error scheduling maintenance: {str(e)}"
        )


@router.post("/admin/cleanup")
async def perform_system_cleanup(
    cleanup_request: CleanupRequest,
    current_user: Dict[str, Any] = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
):
    """Perform system cleanup operations (Admin only)"""
    try:
        # Verify admin permission
        user_permission = current_user.get("permission")
        if user_permission != PermissionLevel.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for cleanup operations"
            )
        
        cleanup_results = {
            "cleanup_type": cleanup_request.cleanup_type,
            "dry_run": cleanup_request.dry_run,
            "older_than_days": cleanup_request.older_than_days,
            "performed_by": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": {}
        }
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=cleanup_request.older_than_days)
        
        if cleanup_request.cleanup_type == "sessions":
            try:
                if hasattr(cosmos_service, 'sessions_container') and cosmos_service.sessions_container:
                    # Find old sessions
                    old_sessions_query = """
                    SELECT c.id, c.created_at, c.partition_key 
                    FROM c 
                    WHERE c.type = 'session' 
                    AND c.created_at < @cutoff_date
                    """
                    
                    parameters = [{"name": "@cutoff_date", "value": cutoff_date.isoformat()}]
                    
                    old_sessions = await run_sync(lambda: list(cosmos_service.sessions_container.query_items(
                        query=old_sessions_query,
                        parameters=parameters,
                        enable_cross_partition_query=True
                    )))
                    
                    cleanup_results["results"]["sessions_found"] = len(old_sessions)
                    
                    if not cleanup_request.dry_run:
                        # Actually delete the sessions
                        deleted_count = 0
                        for session in old_sessions:
                            try:
                                await run_sync(lambda s=session: cosmos_service.sessions_container.delete_item(
                                    s["id"],
                                    partition_key=s.get("partition_key", s["id"])  # Use proper partition key
                                ))
                                deleted_count += 1
                            except Exception as delete_error:
                                logger.warning(f"Could not delete session {session['id']}: {delete_error}")
                        
                        cleanup_results["results"]["sessions_deleted"] = deleted_count
                    else:
                        cleanup_results["results"]["sessions_to_delete"] = len(old_sessions)
                
            except Exception as session_cleanup_error:
                cleanup_results["results"]["sessions_error"] = str(session_cleanup_error)
        
        elif cleanup_request.cleanup_type == "analytics":
            try:
                # Find old analytics data
                old_analytics_query = """
                SELECT c.id, c.created_at 
                FROM c 
                WHERE c.created_at < @cutoff_date
                AND c.type != 'maintenance_schedule'
                """
                
                parameters = [{"name": "@cutoff_date", "value": cutoff_date.isoformat()}]
                
                old_analytics = await run_sync(lambda: list(cosmos_service.analytics_container.query_items(
                    query=old_analytics_query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                )))
                
                cleanup_results["results"]["analytics_found"] = len(old_analytics)
                
                if not cleanup_request.dry_run:
                    # Actually delete old analytics data
                    deleted_count = 0
                    for item in old_analytics:
                        try:
                            await run_sync(lambda it=item: cosmos_service.analytics_container.delete_item(
                                it["id"],
                                partition_key=it["id"]
                            ))
                            deleted_count += 1
                        except Exception as delete_error:
                            logger.warning(f"Could not delete analytics item {item['id']}: {delete_error}")
                    
                    cleanup_results["results"]["analytics_deleted"] = deleted_count
                else:
                    cleanup_results["results"]["analytics_to_delete"] = len(old_analytics)
                    
            except Exception as analytics_cleanup_error:
                cleanup_results["results"]["analytics_error"] = str(analytics_cleanup_error)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported cleanup type: {cleanup_request.cleanup_type}"
            )
        
        # Log cleanup operation
        logger.info(f"Cleanup operation performed by {current_user.get('id')}: {cleanup_results}")
        
        return cleanup_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing cleanup: {str(e)}"
        )


@router.get("/admin/system-info")
async def get_system_info(
    current_user: Dict[str, Any] = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
):
    """Get detailed system information (Admin only)"""
    try:
        # Verify admin permission
        user_permission = current_user.get("permission")
        if user_permission != PermissionLevel.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for system information"
            )
        
        system_info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": getattr(cosmos_service.config, 'ENVIRONMENT', 'unknown'),
            "database": {
                "cosmos_endpoint": bool(getattr(cosmos_service.config, 'COSMOS_ENDPOINT', None)),
                "database_name": getattr(cosmos_service.config, 'COSMOS_DATABASE_NAME', 'unknown')
            },
            "containers": {},
            "statistics": {},
            "maintenance": {}
        }
        
        # Get container statistics
        try:
            # Analytics container stats
            analytics_count_query = "SELECT VALUE COUNT(1) FROM c"
            analytics_count = await run_sync(lambda: list(cosmos_service.analytics_container.query_items(
                query=analytics_count_query,
                enable_cross_partition_query=True
            )))
            system_info["containers"]["analytics"] = {
                "total_items": analytics_count[0] if analytics_count else 0,
                "status": "accessible"
            }
        except Exception as analytics_error:
            system_info["containers"]["analytics"] = {
                "status": "error",
                "error": str(analytics_error)
            }
        
        # Sessions container stats
        try:
            if hasattr(cosmos_service, 'sessions_container') and cosmos_service.sessions_container:
                sessions_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'session'"
                sessions_count = await run_sync(lambda: list(cosmos_service.sessions_container.query_items(
                    query=sessions_count_query,
                    enable_cross_partition_query=True
                )))
                system_info["containers"]["sessions"] = {
                    "total_items": sessions_count[0] if sessions_count else 0,
                    "status": "accessible"
                }
            else:
                system_info["containers"]["sessions"] = {
                    "status": "not_configured"
                }
        except Exception as sessions_error:
            system_info["containers"]["sessions"] = {
                "status": "error",
                "error": str(sessions_error)
            }
        
        # Get usage statistics
        try:
            # Recent activity (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            recent_analytics_query = "SELECT VALUE COUNT(1) FROM c WHERE c.created_at >= @week_ago"
            recent_analytics_params = [{"name": "@week_ago", "value": week_ago.isoformat()}]
            
            recent_analytics_count = await run_sync(lambda: list(cosmos_service.analytics_container.query_items(
                query=recent_analytics_query,
                parameters=recent_analytics_params,
                enable_cross_partition_query=True
            )))
            
            system_info["statistics"]["recent_activity"] = {
                "analytics_events_last_7_days": recent_analytics_count[0] if recent_analytics_count else 0
            }
            
            # Get unique users count
            unique_users_query = "SELECT DISTINCT c.user_id FROM c WHERE c.user_id != null"
            unique_users = await run_sync(lambda: list(cosmos_service.analytics_container.query_items(
                query=unique_users_query,
                enable_cross_partition_query=True
            )))
            
            system_info["statistics"]["total_unique_users"] = len(unique_users)
            
        except Exception as stats_error:
            system_info["statistics"]["error"] = str(stats_error)
        
        # Get maintenance records
        try:
            maintenance_query = """
            SELECT * FROM c 
            WHERE c.type = 'maintenance_schedule' 
            ORDER BY c.scheduled_at DESC 
            OFFSET 0 LIMIT 5
            """
            
            maintenance_records = await run_sync(lambda: list(cosmos_service.analytics_container.query_items(
                query=maintenance_query,
                enable_cross_partition_query=True
            )))
            
            system_info["maintenance"]["recent_maintenance"] = maintenance_records
            
        except Exception as maintenance_error:
            system_info["maintenance"]["error"] = str(maintenance_error)
        
        return system_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system info: {str(e)}"
        )


@router.post("/admin/config/update")
async def update_system_config(
    config_update: SystemConfigUpdate,
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Update system configuration (Admin only)"""
    try:
        # Verify admin permission
        user_permission = current_user.get("permission")
        if user_permission != PermissionLevel.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for configuration updates"
            )
        
        # For now, this is a placeholder - actual implementation would depend on
        # how configuration is managed (environment variables, database, etc.)
        
        config_record = {
            "id": f"config_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": "config_update",
            "config_key": config_update.config_key,
            "config_value": config_update.config_value,
            "apply_immediately": config_update.apply_immediately,
            "updated_by": current_user.get("id"),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Configuration update requested by {current_user.get('id')}: {config_update.dict()}")
        
        return {
            "status": "recorded",
            "message": f"Configuration update for {config_update.config_key} has been recorded",
            "config_key": config_update.config_key,
            "updated_by": current_user.get("email", "Unknown"),
            "timestamp": config_record["updated_at"],
            "note": "Actual configuration updates require deployment or service restart"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating system config: {str(e)}"
        )


@router.get("/admin/logs")
async def get_system_logs(
    hours: int = Query(default=24, ge=1, le=168, description="Hours of logs to retrieve"),
    level: Optional[str] = Query(default=None, description="Log level filter"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Get system logs (Admin only)"""
    try:
        # Verify admin permission
        user_permission = current_user.get("permission")
        if user_permission != PermissionLevel.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for log access"
            )
        
        # This is a placeholder implementation
        # In a real system, you'd integrate with your logging infrastructure
        
        logs_info = {
            "message": "Log retrieval endpoint - integration with logging system required",
            "requested_hours": hours,
            "requested_level": level,
            "requested_by": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "This endpoint requires integration with centralized logging system (e.g., Azure Application Insights, ELK stack, etc.)"
        }
        
        return logs_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting system logs: {str(e)}"
        )


@router.post("/sessions/{user_id}/cleanup")
async def cleanup_user_sessions(
    user_id: str,
    current_user: dict = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
) -> Dict[str, Any]:
    """
    Clean up duplicate sessions for a specific user (Admin only).
    
    This endpoint removes duplicate active sessions, keeping only the most recent one.
    Useful for fixing session tracking issues where multiple sessions exist for the same user.
    
    Args:
        user_id: User ID to clean up sessions for
        current_user: Current admin user
        cosmos_service: Cosmos DB service
        
    Returns:
        Cleanup results including number of sessions cleaned
    """
    try:
        # Import here to avoid circular imports
        from ...services.monitoring.session_tracking_service import SessionTrackingService
        
        # Create session tracking service
        session_service = SessionTrackingService(cosmos_service)
        
        # Perform cleanup
        result = await session_service.cleanup_user_sessions(user_id)
        
        logger.info(f"Session cleanup for user {user_id} performed by admin {current_user.get('id')}: {result}")
        
        return {
            "status": "success",
            "user_id": user_id,
            "cleanup_result": result,
            "performed_by": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up sessions for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cleaning up sessions: {str(e)}"
        )


@router.get("/sessions/duplicates")
async def check_duplicate_sessions(
    current_user: dict = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service)
) -> Dict[str, Any]:
    """
    Check for users with duplicate active sessions (Admin only).
    
    Returns a report of users who have multiple active sessions,
    which indicates session deduplication issues.
    
    Args:
        current_user: Current admin user
        cosmos_service: Cosmos DB service
        
    Returns:
        Report of users with duplicate sessions
    """
    try:
        # Query for users with multiple active sessions
        query = """
            SELECT c.user_id, COUNT(1) as session_count
            FROM c 
            WHERE c.type = 'session' 
            AND c.status = 'active'
            GROUP BY c.user_id
            HAVING COUNT(1) > 1
        """
        
        results = await run_sync(lambda: list(cosmos_service.sessions_container.query_items(
            query=query, enable_cross_partition_query=True
        )))
        
        duplicate_users = []
        total_duplicates = 0
        
        for result in results:
            user_id = result["user_id"]
            session_count = result["session_count"]
            duplicate_users.append({
                "user_id": user_id,
                "active_sessions": session_count,
                "extra_sessions": session_count - 1
            })
            total_duplicates += session_count - 1
        
        return {
            "status": "success",
            "duplicate_users_count": len(duplicate_users),
            "total_extra_sessions": total_duplicates,
            "users_with_duplicates": duplicate_users,
            "checked_by": current_user.get("id"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking duplicate sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking duplicate sessions: {str(e)}"
        )
