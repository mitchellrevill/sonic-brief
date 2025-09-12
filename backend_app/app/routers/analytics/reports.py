"""
Reports Router - Export and reporting functionality
Handles PDF exports, user reports, system reports, and analytics data exports
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
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging

from ...core.config import get_app_config, get_cosmos_db_cached, CosmosDB, DatabaseError
from ...services.content import AnalyticsService, ExportService
from app.models.analytics_models import (
    UserDetailsResponse,
    ExportRequest,
    ExportResponse
)
from app.core.dependencies import get_current_user, require_analytics_access, require_user
from app.models.permissions import PermissionLevel, PermissionCapability, get_user_capabilities

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["reports"])


@router.get("/export/users/{user_id}/pdf")
async def export_user_details_pdf(
    user_id: str,
    include_analytics: bool = Query(True),
    days: int = Query(30, ge=1, le=365, description="Analytics scope in days"),
    current_user: Dict[str, Any] = Depends(require_user)
):
    """Export individual user details as PDF (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        export_service = ExportService(config)
        
        # Get user details
        user = await cosmos_db.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prepare export data
        export_data = {
            "user_id": user_id,
            "user_email": user.get("email", "N/A"),
            "user_name": user.get("name", "N/A"),
            "permission_level": user.get("permission", "N/A"),
            "created_at": user.get("created_at"),
            "last_login": user.get("last_login"),
            "export_generated_at": datetime.now(timezone.utc).isoformat(),
            "export_generated_by": current_user.get("email", "Unknown")
        }
        
        # Add analytics data if requested
        if include_analytics:
            try:
                # Get analytics data
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=days)
                
                analytics_query = "SELECT * FROM c WHERE c.user_id = @user_id AND c.created_at >= @start_time"
                analytics_params = [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@start_time", "value": start_time.isoformat()}
                ]
                
                analytics_items = list(cosmos_db.analytics_container.query_items(
                    query=analytics_query,
                    parameters=analytics_params,
                    enable_cross_partition_query=True,
                ))
                
                # Calculate analytics metrics
                total_minutes = sum(
                    item.get("audio_duration_minutes", 0) 
                    for item in analytics_items 
                    if isinstance(item.get("audio_duration_minutes"), (int, float))
                )
                total_jobs = len(analytics_items)
                
                export_data["analytics"] = {
                    "period_days": days,
                    "total_minutes": total_minutes,
                    "total_jobs": total_jobs,
                    "average_duration": total_minutes / total_jobs if total_jobs > 0 else 0,
                    "recent_activity": analytics_items[:10]  # Last 10 activities
                }
                
                # Get session data if available
                if hasattr(cosmos_db, 'sessions_container'):
                    try:
                        session_query = """
                        SELECT c.id, c.created_at, c.last_heartbeat, c.status, 
                               c.activity_count, c.session_metadata
                        FROM c 
                        WHERE c.type = 'session' 
                        AND c.user_id = @user_id 
                        AND c.created_at >= @start_time
                        ORDER BY c.created_at DESC
                        OFFSET 0 LIMIT 20
                        """
                        
                        sessions = list(cosmos_db.sessions_container.query_items(
                            query=session_query,
                            parameters=analytics_params,
                            enable_cross_partition_query=True
                        ))
                        
                        export_data["session_data"] = {
                            "total_sessions": len(sessions),
                            "recent_sessions": sessions
                        }
                        
                    except Exception as session_error:
                        logger.warning(f"Could not fetch session data for export: {session_error}")
                        
            except Exception as analytics_error:
                logger.warning(f"Could not fetch analytics for export: {analytics_error}")
                export_data["analytics_error"] = str(analytics_error)
        
        # Generate PDF export
        pdf_content = await export_service.generate_user_pdf_report(export_data)
        
        # Create response
        filename = f"user_report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        logger.info(f"Generated PDF export for user {user_id} by {current_user.get('id')}")
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating user PDF export: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF export: {str(e)}"
        )


@router.get("/export/system/csv")
async def export_system_analytics_csv(
    days: int = Query(30, ge=1, le=365, description="Analytics scope in days"),
    include_users: bool = Query(True, description="Include user details"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Export system analytics as CSV (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        export_service = ExportService(config)
        
        # Get analytics data
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        analytics_query = "SELECT * FROM c WHERE c.created_at >= @start_time"
        analytics_params = [{"name": "@start_time", "value": start_time.isoformat()}]
        
        analytics_items = list(cosmos_db.analytics_container.query_items(
            query=analytics_query,
            parameters=analytics_params,
            enable_cross_partition_query=True,
        ))
        
        # Prepare CSV data
        csv_data = []
        for item in analytics_items:
            row = {
                "user_id": item.get("user_id", ""),
                "created_at": item.get("created_at", ""),
                "audio_duration_minutes": item.get("audio_duration_minutes", 0),
                "file_size": item.get("file_size", 0),
                "status": item.get("status", ""),
                "job_id": item.get("job_id", ""),
                "prompt_id": item.get("prompt_id", "")
            }
            
            # Add user details if requested
            if include_users:
                try:
                    user = await cosmos_db.get_user_by_id(item.get("user_id", ""))
                    if user:
                        row["user_email"] = user.get("email", "")
                        row["user_permission"] = user.get("permission", "")
                except Exception:
                    row["user_email"] = "N/A"
                    row["user_permission"] = "N/A"
            
            csv_data.append(row)
        
        # Generate CSV
        csv_content = await export_service.generate_csv_export(csv_data)
        
        # Create response
        filename = f"system_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(f"Generated CSV export for system analytics by {current_user.get('id')}")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        logger.error(f"Error generating CSV export: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating CSV export: {str(e)}"
        )


@router.get("/export/sessions/csv")
async def export_sessions_csv(
    days: int = Query(7, ge=1, le=365, description="Session data scope in days"),
    user_id: Optional[str] = Query(None, description="Specific user ID to export"),
    current_user: Dict[str, Any] = Depends(require_analytics_access)
):
    """Export session data as CSV (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        export_service = ExportService(config)
        
        if not hasattr(cosmos_db, 'sessions_container') or not cosmos_db.sessions_container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session data not available"
            )
        
        # Build query
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        if user_id:
            query = """
            SELECT * FROM c 
            WHERE c.type = 'session' 
            AND c.user_id = @user_id
            AND c.created_at >= @cutoff_time
            ORDER BY c.created_at DESC
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
            ]
        else:
            query = """
            SELECT * FROM c 
            WHERE c.type = 'session' 
            AND c.created_at >= @cutoff_time
            ORDER BY c.created_at DESC
            """
            parameters = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
        
        sessions = list(cosmos_db.sessions_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        # Prepare CSV data
        csv_data = []
        for session in sessions:
            try:
                created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                duration_minutes = (last_heartbeat - created_at).total_seconds() / 60
                
                metadata = session.get("session_metadata", {})
                
                row = {
                    "session_id": session.get("id", ""),
                    "user_id": session.get("user_id", ""),
                    "created_at": session["created_at"],
                    "last_heartbeat": session["last_heartbeat"],
                    "status": session.get("status", ""),
                    "duration_minutes": round(duration_minutes, 2),
                    "activity_count": session.get("activity_count", 0),
                    "total_requests": session.get("total_requests", 0),
                    "browser": metadata.get("browser", ""),
                    "platform": metadata.get("platform", ""),
                    "ip_address": metadata.get("ip_address", ""),
                    "unique_endpoints": len(session.get("endpoints_accessed", [])),
                    "last_endpoint": session.get("last_endpoint", "")
                }
                
                csv_data.append(row)
                
            except Exception as session_error:
                logger.warning(f"Error processing session for CSV export: {session_error}")
                continue
        
        # Generate CSV
        csv_content = await export_service.generate_csv_export(csv_data)
        
        # Create filename
        if user_id:
            filename = f"sessions_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            filename = f"sessions_all_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(f"Generated sessions CSV export by {current_user.get('id')}")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating sessions CSV export: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating sessions CSV export: {str(e)}"
        )


@router.post("/export/custom")
async def create_custom_export(
    export_request: ExportRequest,
    current_user: Dict[str, Any] = Depends(require_analytics_access)
) -> ExportResponse:
    """Create a custom analytics export based on specified parameters (Admin only)"""
    try:
        config = get_app_config()
        cosmos_db = get_cosmos_db_cached(config)
        export_service = ExportService(config)
        
        # Validate export request
        if not export_request.data_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one data source must be specified"
            )
        
        # Collect data from requested sources
        export_data = {
            "metadata": {
                "export_type": "custom",
                "requested_by": current_user.get("email", "Unknown"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "parameters": export_request.dict()
            },
            "data": {}
        }
        
        # Get analytics data if requested
        if "analytics" in export_request.data_sources:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(days=export_request.days)
            
            query = "SELECT * FROM c WHERE c.created_at >= @start_time"
            parameters = [{"name": "@start_time", "value": start_time.isoformat()}]
            
            if export_request.user_id:
                query += " AND c.user_id = @user_id"
                parameters.append({"name": "@user_id", "value": export_request.user_id})
            
            analytics_items = list(cosmos_db.analytics_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            ))
            
            export_data["data"]["analytics"] = analytics_items
        
        # Get session data if requested
        if "sessions" in export_request.data_sources and hasattr(cosmos_db, 'sessions_container'):
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=export_request.days)
            
            session_query = """
            SELECT * FROM c 
            WHERE c.type = 'session' 
            AND c.created_at >= @cutoff_time
            """
            session_params = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
            
            if export_request.user_id:
                session_query += " AND c.user_id = @user_id"
                session_params.append({"name": "@user_id", "value": export_request.user_id})
            
            sessions = list(cosmos_db.sessions_container.query_items(
                query=session_query,
                parameters=session_params,
                enable_cross_partition_query=True
            ))
            
            export_data["data"]["sessions"] = sessions
        
        # Get user data if requested
        if "users" in export_request.data_sources:
            if export_request.user_id:
                user = await cosmos_db.get_user_by_id(export_request.user_id)
                export_data["data"]["users"] = [user] if user else []
            else:
                # Get all users (admin only)
                users_query = "SELECT * FROM c WHERE c.type = 'user'"
                users = list(cosmos_db.users_container.query_items(
                    query=users_query,
                    enable_cross_partition_query=True
                ))
                export_data["data"]["users"] = users
        
        # Generate export in requested format
        if export_request.format.lower() == "json":
            content = await export_service.generate_json_export(export_data)
            media_type = "application/json"
            file_extension = "json"
        elif export_request.format.lower() == "csv":
            content = await export_service.generate_csv_export(export_data)
            media_type = "text/csv"
            file_extension = "csv"
        elif export_request.format.lower() == "pdf":
            content = await export_service.generate_pdf_export(export_data)
            media_type = "application/pdf"
            file_extension = "pdf"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported export format. Use json, csv, or pdf."
            )
        
        # Create filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"custom_export_{timestamp}.{file_extension}"
        
        logger.info(f"Generated custom export by {current_user.get('id')}: {export_request.dict()}")
        
        return ExportResponse(
            export_id=f"custom_{timestamp}",
            filename=filename,
            format=export_request.format,
            size=len(content),
            generated_at=datetime.now(timezone.utc).isoformat(),
            download_url=f"/api/analytics/export/download/{filename}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom export: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating custom export: {str(e)}"
        )
