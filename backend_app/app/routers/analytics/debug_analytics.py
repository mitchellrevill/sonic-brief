"""
Debug Analytics Router - Debug endpoints for troubleshooting and development
Handles debug endpoints for session tracking, user data analysis, and system diagnostics
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
import os

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from ...core.dependencies import get_current_user
from app.core.debug_utils import require_debug_access, debug_endpoint_required
from app.models.permissions import PermissionLevel, PermissionCapability, get_user_capabilities

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["debug-analytics"])


@router.get("/debug/sessions")
@debug_endpoint_required
async def debug_sessions(
    current_user: Dict[str, Any] = Depends(require_debug_access)
):
    """Debug endpoint to check session data directly"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        debug_info = {
            "has_sessions_container": hasattr(cosmos_db, 'sessions_container'),
            "container_available": getattr(cosmos_db, 'sessions_container', None) is not None,
            "total_sessions": 0,
            "sample_sessions": [],
            "container_info": {}
        }
        
        if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
            try:
                # Count total sessions
                count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'session'"
                count_result = list(cosmos_db.sessions_container.query_items(
                    query=count_query,
                    enable_cross_partition_query=True
                ))
                debug_info["total_sessions"] = count_result[0] if count_result else 0
                
                # Get recent sessions sample
                sample_query = "SELECT TOP 5 c.id, c.user_id, c.created_at, c.status FROM c WHERE c.type = 'session' ORDER BY c.created_at DESC"
                sample_sessions = list(cosmos_db.sessions_container.query_items(
                    query=sample_query,
                    enable_cross_partition_query=True
                ))
                debug_info["sample_sessions"] = sample_sessions
                
                # Check if there are any documents at all
                any_query = "SELECT TOP 5 c.id, c.type FROM c"
                any_docs = list(cosmos_db.sessions_container.query_items(
                    query=any_query,
                    enable_cross_partition_query=True
                ))
                debug_info["any_documents"] = any_docs
                debug_info["total_documents"] = len(any_docs)
                
            except Exception as query_error:
                debug_info["query_error"] = str(query_error)
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Debug sessions error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/debug/user-sessions/{user_id}")
@debug_endpoint_required
async def debug_user_sessions(
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_debug_access)
):
    """Debug endpoint to check specific user's session data for troubleshooting dashboard display"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        debug_info = {
            "target_user_id": user_id,
            "has_sessions_container": hasattr(cosmos_db, 'sessions_container'),
            "container_available": getattr(cosmos_db, 'sessions_container', None) is not None,
            "user_sessions": [],
            "possible_user_id_formats": [],
            "queries_attempted": [],
            "all_user_samples": []
        }
        
        if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
            try:
                # Try different user_id variations
                user_id_variations = [
                    user_id,
                    user_id.lower(),
                    user_id.upper(),
                    f"user_{user_id}",
                    user_id.replace("-", ""),
                    user_id.replace("_", "-")
                ]
                
                for variation in user_id_variations:
                    debug_info["possible_user_id_formats"].append(variation)
                    
                    # Query for this variation
                    query = """
                    SELECT * FROM c 
                    WHERE c.type = 'session' 
                    AND (
                        c.user_id = @user_id
                        OR c.user_email = @user_id
                        OR c.user_id_original = @user_id
                    )
                    ORDER BY c.created_at DESC
                    OFFSET 0 LIMIT 10
                    """
                    
                    parameters = [{"name": "@user_id", "value": variation}]
                    debug_info["queries_attempted"].append({
                        "variation": variation,
                        "query": query,
                        "parameters": parameters
                    })
                    
                    try:
                        sessions = list(cosmos_db.sessions_container.query_items(
                            query=query,
                            parameters=parameters,
                            enable_cross_partition_query=True
                        ))
                        
                        if sessions:
                            debug_info["user_sessions"].extend(sessions)
                            debug_info["found_with_variation"] = variation
                            break
                    except Exception as variation_error:
                        debug_info["queries_attempted"][-1]["error"] = str(variation_error)
                
                # If no sessions found, get sample of all users for comparison
                if not debug_info["user_sessions"]:
                    all_users_query = """
                    SELECT DISTINCT c.user_id, c.user_email, c.id, c.created_at 
                    FROM c WHERE c.type = 'session'
                    ORDER BY c.created_at DESC
                    OFFSET 0 LIMIT 20
                    """
                    
                    all_users = list(cosmos_db.sessions_container.query_items(
                        query=all_users_query,
                        enable_cross_partition_query=True
                    ))
                    debug_info["all_user_samples"] = all_users[:20]  # First 20 unique users
                
            except Exception as query_error:
                debug_info["query_error"] = str(query_error)
                import traceback
                debug_info["query_traceback"] = traceback.format_exc()
        
        return debug_info
        
    except Exception as e:
        logger.error(f"Debug user sessions error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/debug/session-summary")
@debug_endpoint_required
async def debug_session_summary(
    current_user: Dict[str, Any] = Depends(require_debug_access)
):
    """Debug endpoint to get overview of session tracking system for dashboard troubleshooting"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        
        summary = {
            "session_tracking_status": "unknown",
            "containers": {
                "sessions_container": False,
                "audit_container": False
            },
            "session_stats": {},
            "recent_activity": [],
            "middleware_status": "unknown"
        }
        
        # Check container availability
        if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container:
            summary["containers"]["sessions_container"] = True
            
            try:
                # Get session statistics
                stats_query = """
                SELECT 
                    c.status,
                    COUNT(1) as count
                FROM c 
                WHERE c.type = 'session'
                GROUP BY c.status
                """
                
                stats_result = list(cosmos_db.sessions_container.query_items(
                    query=stats_query,
                    enable_cross_partition_query=True
                ))
                
                for stat in stats_result:
                    summary["session_stats"][stat["status"]] = stat["count"]
                
                # Get recent session activity
                recent_query = """
                SELECT TOP 10 c.id, c.user_id, c.created_at, c.last_heartbeat, 
                       c.status, c.activity_count, c.last_endpoint
                FROM c 
                WHERE c.type = 'session'
                ORDER BY c.last_heartbeat DESC
                """
                
                recent_sessions = list(cosmos_db.sessions_container.query_items(
                    query=recent_query,
                    enable_cross_partition_query=True
                ))
                
                summary["recent_activity"] = recent_sessions
                summary["session_tracking_status"] = "active"
                
            except Exception as session_error:
                summary["session_tracking_status"] = f"error: {session_error}"
        
        if hasattr(cosmos_db, 'audit_container') and cosmos_db.audit_container:
            summary["containers"]["audit_container"] = True
        
        # Check for middleware indicators
        try:
            # Look for recent session heartbeats as indicator of middleware activity
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            recent_heartbeat_query = f"""
            SELECT VALUE COUNT(1) 
            FROM c 
            WHERE c.type = 'session' 
            AND c.last_heartbeat >= '{cutoff_time.isoformat()}'
            """
            
            recent_count = list(cosmos_db.sessions_container.query_items(
                query=recent_heartbeat_query,
                enable_cross_partition_query=True
            ))
            
            if recent_count and recent_count[0] > 0:
                summary["middleware_status"] = f"active ({recent_count[0]} recent heartbeats)"
            else:
                summary["middleware_status"] = "no recent activity"
                
        except Exception as middleware_error:
            summary["middleware_status"] = f"check failed: {middleware_error}"
        
        return summary
        
    except Exception as e:
        logger.error(f"Debug session summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/debug/environment")
@debug_endpoint_required
async def debug_environment(
    current_user: Dict[str, Any] = Depends(require_debug_access)
):
    """Debug endpoint to check environment and configuration status"""
    try:
        config = get_app_config()
        
        env_info = {
            "environment": {
                "debug_enabled": os.getenv("DEBUG_ENDPOINTS_ENABLED", "false").lower() == "true",
                "environment": os.getenv("ENVIRONMENT", "unknown"),
                "app_environment": getattr(config, 'ENVIRONMENT', 'unknown')
            },
            "database": {
                "cosmos_endpoint": bool(getattr(config, 'COSMOS_ENDPOINT', None)),
                "cosmos_key": bool(getattr(config, 'COSMOS_KEY', None)),
                "database_name": getattr(config, 'COSMOS_DATABASE_NAME', 'unknown')
            },
            "containers": {
                "analytics_container": getattr(config, 'COSMOS_ANALYTICS_CONTAINER', 'unknown'),
                "sessions_container": getattr(config, 'COSMOS_SESSIONS_CONTAINER', 'unknown'),
                "audit_container": getattr(config, 'COSMOS_AUDIT_CONTAINER', 'unknown')
            },
            "current_user": {
                "id": current_user.get("id", "unknown"),
                "permission": current_user.get("permission", "unknown"),
                "custom_capabilities": current_user.get("custom_capabilities", {})
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Test database connection
        try:
            cosmos_db = get_cosmos_db_cached(config)
            env_info["database"]["connection_status"] = "connected"
            
            # Test container access
            if hasattr(cosmos_db, 'analytics_container'):
                try:
                    list(cosmos_db.analytics_container.query_items(
                        query="SELECT TOP 1 c.id FROM c",
                        enable_cross_partition_query=True
                    ))
                    env_info["containers"]["analytics_status"] = "accessible"
                except Exception as e:
                    env_info["containers"]["analytics_status"] = f"error: {str(e)}"
            
            if hasattr(cosmos_db, 'sessions_container'):
                try:
                    list(cosmos_db.sessions_container.query_items(
                        query="SELECT TOP 1 c.id FROM c",
                        enable_cross_partition_query=True
                    ))
                    env_info["containers"]["sessions_status"] = "accessible"
                except Exception as e:
                    env_info["containers"]["sessions_status"] = f"error: {str(e)}"
                    
        except Exception as db_error:
            env_info["database"]["connection_status"] = f"error: {str(db_error)}"
        
        return env_info
        
    except Exception as e:
        logger.error(f"Debug environment error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/debug/permissions")
@debug_endpoint_required
async def debug_permissions(
    current_user: Dict[str, Any] = Depends(require_debug_access)
):
    """Debug endpoint to check permission system status and user capabilities"""
    try:
        permission_info = {
            "current_user": {
                "id": current_user.get("id"),
                "email": current_user.get("email"),
                "permission": current_user.get("permission"),
                "custom_capabilities": current_user.get("custom_capabilities", {})
            },
            "effective_capabilities": {},
            "debug_access": {
                "has_debug_access": True,  # Since this endpoint ran, they have debug access
                "debug_capability": None
            },
            "permission_levels": {
                "admin": PermissionLevel.ADMIN.value,
                "elevated": PermissionLevel.ELEVATED.value,
                "standard": PermissionLevel.STANDARD.value,
                "restricted": PermissionLevel.RESTRICTED.value
            },
            "available_capabilities": [cap.value for cap in PermissionCapability],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Get effective capabilities
        user_permission = current_user.get("permission")
        custom_capabilities = current_user.get("custom_capabilities", {})
        
        try:
            effective_caps = get_user_capabilities(user_permission, custom_capabilities)
            permission_info["effective_capabilities"] = effective_caps
            # Check specific debug capability
            debug_cap = effective_caps.get(PermissionCapability.CAN_ACCESS_DEBUG_ENDPOINTS.value, False)
            permission_info["debug_access"]["debug_capability"] = debug_cap
        except Exception as perm_error:
            permission_info["permission_service_error"] = str(perm_error)
        
        return permission_info
        
    except Exception as e:
        logger.error(f"Debug permissions error: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/debug/recent-errors")
@debug_endpoint_required
async def debug_recent_errors(
    hours: int = Query(default=24, description="Hours to look back for errors"),
    current_user: Dict[str, Any] = Depends(require_debug_access)
):
    """Debug endpoint to check recent error logs and system issues"""
    try:
        # This would typically integrate with a logging service or error tracking system
        # For now, provide a basic structure that could be expanded
        
        error_info = {
            "lookback_hours": hours,
            "error_sources": {
                "database_errors": [],
                "authentication_errors": [],
                "permission_errors": [],
                "api_errors": []
            },
            "summary": {
                "total_errors": 0,
                "error_types": {},
                "most_common_errors": []
            },
            "system_status": {
                "containers_accessible": True,
                "authentication_working": True,
                "permissions_working": True
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Basic system checks
        try:
            config = get_app_config()
            cosmos_db = get_cosmos_db_cached(config)
            
            # Test database access
            list(cosmos_db.analytics_container.query_items(
                query="SELECT TOP 1 c.id FROM c",
                enable_cross_partition_query=True
            ))
            
        except Exception as db_error:
            error_info["system_status"]["containers_accessible"] = False
            error_info["error_sources"]["database_errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(db_error),
                "context": "database_connectivity_check"
            })
            error_info["summary"]["total_errors"] += 1
        
        # Note: In a production system, this would query actual error logs
        # from a centralized logging system, error tracking service, or database
        
        return error_info
        
    except Exception as e:
        logger.error(f"Debug recent errors check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")
