"""
User Analytics Router - User-specific analytics and session tracking
Handles user analytics, session metrics, detailed session analysis, and user activity tracking
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
)
from pydantic import BaseModel
import logging

from ...core.dependencies import (
    get_current_user,
    require_analytics_access,
    require_admin,
    get_cosmos_service,
    CosmosService,
    get_error_handler,
)
from ...core.errors import ApplicationError, ErrorCode, ErrorHandler
from ...services.analytics import AnalyticsService
from ...services.analytics import ExportService
from ...models.analytics_models import (
    UserAnalyticsResponse,
    UserDetailsResponse,
    ExportRequest,
    ExportResponse,
    UserMinutesResponse,
    UserMinuteRecord
)
from ...models.permissions import PermissionLevel, has_permission_level

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(prefix="", tags=["user-analytics"])


def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )


def _query_container(
    container,
    *,
    action: str,
    query: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    details: Optional[Dict[str, Any]] = None,
    error_handler: ErrorHandler,
):
    try:
        return list(
            container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            action,
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            details=details,
        )


@router.get("/users/{user_id}/analytics", response_model=UserAnalyticsResponse)
async def get_user_analytics(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get analytics for a specific user (Admin only)"""
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # Query analytics data for the user
        query = "SELECT * FROM c WHERE c.user_id = @user_id AND c.created_at >= @start_time"
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@start_time", "value": start_time.isoformat()}
        ]
        
        items = _query_container(
            cosmos_service.analytics_container,
            action="query user analytics",
            query=query,
            parameters=parameters,
            details={"user_id": user_id, "days": days},
            error_handler=error_handler,
        )
        
        # Calculate analytics
        total_minutes = 0.0
        total_jobs = 0
        for item in items:
            minutes = item.get("audio_duration_minutes")
            if isinstance(minutes, (int, float)):
                total_minutes += minutes
            total_jobs += 1

        # Prepare analytics data
        analytics_data = {
            "total_minutes": total_minutes,
            "total_jobs": total_jobs,
            "average_duration": total_minutes / total_jobs if total_jobs > 0 else 0,
            "records": items,
            "overview": {
                "total_transcription_minutes": total_minutes,
                "total_jobs": total_jobs,
                "average_job_duration": total_minutes / total_jobs if total_jobs > 0 else 0,
                "active_days": len(set(item.get("created_at", "").split("T")[0] for item in items if item.get("created_at")))
            }
        }

        return UserAnalyticsResponse(
            user_id=user_id,
            period_days=days,
            start_date=start_time.isoformat(),
            end_date=end_time.isoformat(),
            analytics=analytics_data
        )
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get user analytics",
            exc,
            details={"user_id": user_id, "days": days},
        )


@router.get("/users/{user_id}/session-summary")
async def get_user_session_summary(
    user_id: str,
    days: int = Query(default=30, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(require_admin),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get high-level session summary for a user"""
    try:
        # Query sessions for the user in the specified timeframe
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        query = """
        SELECT c.id, c.created_at, c.last_activity, c.last_heartbeat, c.status, 
               c.activity_count, c.session_metadata, c.total_requests
        FROM c 
        WHERE c.user_id = @user_id 
        AND c.created_at >= @cutoff_time
        ORDER BY c.created_at DESC
        """
        
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
        ]
        
        sessions = _query_container(
            cosmos_service.sessions_container,
            action="query user session summary",
            query=query,
            parameters=parameters,
            details={"user_id": user_id, "days": days},
            error_handler=error_handler,
        )
        
        # Calculate summary statistics
        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.get("status") == "active"])
        total_activity = sum(s.get("activity_count", 0) for s in sessions)
        total_requests = sum(s.get("total_requests", 0) for s in sessions)
        
        # Calculate session durations
        session_durations = []
        for session in sessions:
            try:
                created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                last_ts = session.get("last_activity") or session.get("last_heartbeat")
                last_heartbeat = datetime.fromisoformat(last_ts.replace('Z', '+00:00')) if last_ts else created_at
                duration_minutes = (last_heartbeat - created_at).total_seconds() / 60
                session_durations.append(duration_minutes)
            except Exception:
                continue
        
        avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        return {
            "user_id": user_id,
            "period_days": days,
            "summary": {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_activity_events": total_activity,
                "total_requests": total_requests,
                "average_session_duration": round(avg_duration, 2)
            },
            "query_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get user session summary",
            exc,
            details={"user_id": user_id, "days": days},
        )


@router.get("/users/{user_id}/session-analytics")
async def get_user_session_analytics(
    user_id: str,
    days: int = Query(default=30, description="Number of days to analyze"),
    current_user: Dict[str, Any] = Depends(require_admin),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get comprehensive session analytics for a user"""
    try:
        # Query sessions for the user in the specified timeframe
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = """
        SELECT *
        FROM c 
        WHERE c.type = 'session' 
        AND c.user_id = @user_id 
        AND c.created_at >= @cutoff_time
        ORDER BY c.created_at DESC
        """
        
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
        ]
        
        sessions = _query_container(
            cosmos_service.sessions_container,
            action="query user session analytics",
            query=query,
            parameters=parameters,
            details={"user_id": user_id, "days": days},
            error_handler=error_handler,
        )
        
        # Initialize comprehensive analytics structure
        analytics = {
            "user_id": user_id,
            "period_days": days,
            "total_sessions": len(sessions),
            "session_timeline": [],
            "security_insights": {
                "unique_ip_addresses": set(),
                "unique_browsers": set(),
                "unique_platforms": set(),
                "potential_security_events": []
            },
            "performance_metrics": {
                "total_requests": 0,
                "total_activity_events": 0,
                "average_session_duration": 0,
                "longest_session_duration": 0,
                "shortest_session_duration": float('inf'),
                "sessions_by_status": {}
            },
            "usage_analytics": {
                "endpoints_accessed": {},
                "hourly_distribution": {},
                "daily_distribution": {},
                "browser_distribution": {},
                "platform_distribution": {}
            },
            "engagement_metrics": {
                "highly_active_sessions": 0,  # >30 min
                "medium_active_sessions": 0,  # 5-30 min
                "brief_sessions": 0,          # <5 min
                "total_endpoints_explored": 0,
                "session_consistency_score": 0
            }
        }
        
        # Process each session for detailed analytics
        session_durations = []
        last_session_time = None
        session_gaps = []
        
        for session in sessions:
            try:
                created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                duration_minutes = (last_heartbeat - created_at).total_seconds() / 60
                session_durations.append(duration_minutes)
                
                metadata = session.get("session_metadata", {})
                ip_address = metadata.get("ip_address", "unknown")
                browser = metadata.get("browser", "unknown")
                platform = metadata.get("platform", "unknown")
                
                # Track security insights
                analytics["security_insights"]["unique_ip_addresses"].add(ip_address)
                analytics["security_insights"]["unique_browsers"].add(browser)
                analytics["security_insights"]["unique_platforms"].add(platform)
                
                # Performance metrics
                analytics["performance_metrics"]["total_requests"] += session.get("total_requests", 0)
                analytics["performance_metrics"]["total_activity_events"] += session.get("activity_count", 0)
                
                status = session.get("status", "unknown")
                analytics["performance_metrics"]["sessions_by_status"][status] = \
                    analytics["performance_metrics"]["sessions_by_status"].get(status, 0) + 1
                
                # Usage analytics
                endpoints = session.get("endpoints_accessed", [])
                for endpoint in endpoints:
                    analytics["usage_analytics"]["endpoints_accessed"][endpoint] = \
                        analytics["usage_analytics"]["endpoints_accessed"].get(endpoint, 0) + 1
                
                # Hourly and daily distribution
                hour = created_at.hour
                date_str = created_at.date().isoformat()
                analytics["usage_analytics"]["hourly_distribution"][hour] = \
                    analytics["usage_analytics"]["hourly_distribution"].get(hour, 0) + 1
                analytics["usage_analytics"]["daily_distribution"][date_str] = \
                    analytics["usage_analytics"]["daily_distribution"].get(date_str, 0) + 1
                
                # Browser and platform distribution
                analytics["usage_analytics"]["browser_distribution"][browser] = \
                    analytics["usage_analytics"]["browser_distribution"].get(browser, 0) + 1
                analytics["usage_analytics"]["platform_distribution"][platform] = \
                    analytics["usage_analytics"]["platform_distribution"].get(platform, 0) + 1
                
                # Engagement metrics
                if duration_minutes > 30:
                    analytics["engagement_metrics"]["highly_active_sessions"] += 1
                elif duration_minutes > 5:
                    analytics["engagement_metrics"]["medium_active_sessions"] += 1
                else:
                    analytics["engagement_metrics"]["brief_sessions"] += 1
                
                analytics["engagement_metrics"]["total_endpoints_explored"] += len(endpoints)
                
                # Session timeline entry
                timeline_entry = {
                    "session_id": session.get("id"),
                    "start_time": session["created_at"],
                    "end_time": session["last_heartbeat"],
                    "duration_minutes": round(duration_minutes, 2),
                    "status": status,
                    "activity_count": session.get("activity_count", 0),
                    "endpoints_count": len(endpoints),
                    "last_endpoint": session.get("last_endpoint"),
                    "client_info": {
                        "browser": browser,
                        "platform": platform,
                        "ip_address": ip_address
                    }
                }
                analytics["session_timeline"].append(timeline_entry)
                
                # Calculate session gaps for consistency
                if last_session_time:
                    gap_hours = (last_session_time - created_at).total_seconds() / 3600
                    session_gaps.append(gap_hours)
                last_session_time = created_at
                
                # Security event detection
                if len(endpoints) > 50:  # High activity might indicate automation
                    analytics["security_insights"]["potential_security_events"].append({
                        "type": "high_endpoint_activity",
                        "session_id": session.get("id"),
                        "timestamp": session["created_at"],
                        "details": f"Session accessed {len(endpoints)} endpoints"
                    })
                
                if duration_minutes > 480:  # Sessions longer than 8 hours
                    analytics["security_insights"]["potential_security_events"].append({
                        "type": "extended_session",
                        "session_id": session.get("id"),
                        "timestamp": session["created_at"],
                        "details": f"Session lasted {duration_minutes:.1f} minutes"
                    })
                
            except Exception as session_error:
                logger.warning(f"Error processing session for analytics: {session_error}")
                continue
        
        # Calculate final metrics
        if session_durations:
            analytics["performance_metrics"]["average_session_duration"] = round(sum(session_durations) / len(session_durations), 2)
            analytics["performance_metrics"]["longest_session_duration"] = round(max(session_durations), 2)
            analytics["performance_metrics"]["shortest_session_duration"] = round(min(session_durations), 2)
        
        # Convert sets to lists for JSON serialization
        analytics["security_insights"]["unique_ip_addresses"] = list(analytics["security_insights"]["unique_ip_addresses"])
        analytics["security_insights"]["unique_browsers"] = list(analytics["security_insights"]["unique_browsers"])
        analytics["security_insights"]["unique_platforms"] = list(analytics["security_insights"]["unique_platforms"])
        
        # Calculate session consistency score (lower gaps = higher consistency)
        if session_gaps:
            avg_gap = sum(session_gaps) / len(session_gaps)
            # Score from 0-100 where smaller gaps = higher score
            consistency_score = max(0, 100 - min(100, avg_gap * 2))
            analytics["engagement_metrics"]["session_consistency_score"] = round(consistency_score, 1)
        
        return analytics
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get user session analytics",
            exc,
            details={"user_id": user_id, "days": days},
        )


@router.get("/users/{user_id}/detailed-sessions")
async def get_user_detailed_sessions(
    user_id: str,
    days: int = Query(default=7, description="Number of days to analyze"),
    limit: int = Query(default=50, description="Maximum number of sessions to return"),
    include_audit: bool = Query(default=True, description="Include audit log entries"),
    current_user: Dict[str, Any] = Depends(require_admin),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get detailed session information for a user with audit trail"""
    try:
        # Query sessions for the user
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = """
        SELECT *
        FROM c 
        WHERE c.type = 'session' 
        AND c.user_id = @user_id 
        AND c.created_at >= @cutoff_time
        ORDER BY c.created_at DESC
        OFFSET 0 LIMIT @limit
        """
        
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@cutoff_time", "value": cutoff_time.isoformat()},
            {"name": "@limit", "value": limit}
        ]
        
        sessions = _query_container(
            cosmos_service.sessions_container,
            action="query user detailed sessions",
            query=query,
            parameters=parameters,
            details={"user_id": user_id, "days": days, "limit": limit},
            error_handler=error_handler,
        )
        
        # Process sessions for detailed view
        detailed_sessions = []
        for session in sessions:
            try:
                created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                duration_minutes = (last_heartbeat - created_at).total_seconds() / 60
                
                metadata = session.get("session_metadata", {})
                
                detailed_session = {
                    "session_id": session.get("id"),
                    "created_at": session["created_at"],
                    "last_heartbeat": session["last_heartbeat"],
                    "status": session.get("status", "unknown"),
                    "duration_minutes": round(duration_minutes, 2),
                    "activity_count": session.get("activity_count", 0),
                    "unique_endpoints": len(session.get("endpoints_accessed", [])),
                    "endpoints_accessed": session.get("endpoints_accessed", []),
                    "client_info": {
                        "browser": metadata.get("browser", "Unknown"),
                        "platform": metadata.get("platform", "Unknown"),
                        "ip_address": metadata.get("ip_address", "Unknown"),
                        "user_agent": metadata.get("user_agent", "Unknown")
                    },
                    "last_endpoint": session.get("last_endpoint"),
                    "total_requests": session.get("total_requests", 0),
                    "is_active": session.get("status") == "active"
                }
                
                detailed_sessions.append(detailed_session)
                
            except Exception as parse_error:
                logger.warning(f"Error parsing session for detailed view: {parse_error}")
                continue
        
        # Get audit logs if requested
        audit_timeline = []
        if include_audit and hasattr(cosmos_service, "audit_container"):
            audit_container = getattr(cosmos_service, "audit_container", None)
            if audit_container is None:
                logger.debug(
                    "Audit container attribute present but value is None; skipping audit lookup",
                    extra={"context": {"user_id": user_id, "days": days}},
                )
            else:
                try:
                    audit_query = """
                    SELECT *
                    FROM c 
                    WHERE c.type = 'audit' 
                    AND c.user_id = @user_id 
                    AND c.timestamp >= @cutoff_time
                    ORDER BY c.timestamp DESC
                    OFFSET 0 LIMIT 100
                    """

                    audit_logs = _query_container(
                        audit_container,
                        action="query user audit logs",
                        query=audit_query,
                        parameters=parameters[:2],  # user_id and cutoff_time
                        details={"user_id": user_id, "days": days},
                        error_handler=error_handler,
                    )

                    # Process audit logs for timeline
                    for audit in audit_logs:
                        try:
                            audit_entry = {
                                "id": audit.get("id"),
                                "timestamp": audit.get("timestamp"),
                                "event_type": audit.get("event_type"),
                                "resource": audit.get("resource"),
                                "details": audit.get("details", {}),
                                "ip_address": audit.get("ip_address"),
                                "user_agent": audit.get("user_agent"),
                            }
                            audit_timeline.append(audit_entry)
                        except Exception as audit_error:
                            logger.warning(
                                "Error parsing audit log",
                                extra={
                                    "context": {
                                        "user_id": user_id,
                                        "days": days,
                                        "error": str(audit_error),
                                    }
                                },
                            )
                            continue
                except ApplicationError as audit_query_error:
                    logger.warning(
                        "Could not fetch audit logs",
                        extra={
                            "context": {
                                "user_id": user_id,
                                "days": days,
                                "limit": limit,
                                "error": str(audit_query_error),
                            }
                        },
                    )
        
        return {
            "user_id": user_id,
            "period_days": days,
            "query_limit": limit,
            "total_sessions_returned": len(detailed_sessions),
            "total_audit_entries": len(audit_timeline),
            "detailed_sessions": detailed_sessions,
            "audit_timeline": audit_timeline,
            "summary": {
                "total_activity_events": sum(s.get("activity_count", 0) for s in sessions),
                "total_session_duration": sum(s.get("duration_minutes", 0) for s in detailed_sessions),
                "unique_browsers": len(set(s.get("client_info", {}).get("browser") for s in detailed_sessions)),
                "unique_ip_addresses": len(set(s.get("client_info", {}).get("ip_address") for s in detailed_sessions)),
            }
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get user detailed sessions",
            exc,
            details={"user_id": user_id, "days": days, "limit": limit},
        )


@router.get("/users/{user_id}/minutes", response_model=UserMinutesResponse)
async def get_user_minutes(
    user_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_analytics_access),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get total minutes processed by a user (Admin only)"""
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # Query analytics data first (preferred source)
        total_minutes = 0.0
        records = []
        items = []
        
        # Try analytics container first with correct timestamp field
        analytics_container = getattr(cosmos_service, "analytics_container", None)
        if analytics_container is not None:
            try:
                items = _query_container(
                    analytics_container,
                    action="query user minutes analytics",
                    query="SELECT * FROM c WHERE c.user_id = @user_id AND c.timestamp >= @start_time",
                    parameters=[
                        {"name": "@user_id", "value": user_id},
                        {"name": "@start_time", "value": start_time.isoformat()},
                    ],
                    details={"user_id": user_id, "days": days},
                    error_handler=error_handler,
                )
            except ApplicationError as analytics_error:
                logger.warning(
                    "Error querying analytics container for user minutes",
                    extra={
                        "context": {
                            "user_id": user_id,
                            "days": days,
                            "error": str(analytics_error),
                        }
                    },
                )
                items = []

        
        # If no data in analytics container, try jobs container as fallback
        if not items:
            jobs_container = getattr(cosmos_service, "jobs_container", None)
            if jobs_container is not None:
                try:
                    items = _query_container(
                        jobs_container,
                        action="query user minutes jobs",
                        query="SELECT * FROM c WHERE c.user_id = @user_id AND c.created_at >= @start_time AND c.type = 'job'",
                        parameters=[
                            {"name": "@user_id", "value": user_id},
                            {"name": "@start_time", "value": start_time.isoformat()},
                        ],
                        details={"user_id": user_id, "days": days},
                        error_handler=error_handler,
                    )
                    logger.info("Found %d items in jobs container for user %s", len(items), user_id)
                except ApplicationError as jobs_error:
                    logger.error(
                        "Error querying jobs container for user minutes",
                        extra={
                            "context": {
                                "user_id": user_id,
                                "days": days,
                                "error": str(jobs_error),
                            }
                        },
                    )
                    items = []
        
        # Calculate total minutes and build records
        for item in items:
            minutes = item.get("audio_duration_minutes")
            # Convert seconds to minutes if needed
            if minutes is None and item.get("audio_duration_seconds") is not None:
                try:
                    minutes = float(item.get("audio_duration_seconds")) / 60.0
                except (ValueError, TypeError):
                    minutes = None
                    
            if isinstance(minutes, (int, float)):
                total_minutes += minutes
                
                # Create a UserMinuteRecord for each item
                record = UserMinuteRecord(
                    job_id=item.get("job_id", item.get("id", "")),
                    timestamp=item.get("timestamp", item.get("created_at", "")),
                    audio_duration_minutes=minutes,
                    event_type=item.get("event_type", "job"),
                    file_name=item.get("file_name", ""),
                    prompt_category_id=item.get("prompt_category_id"),
                    prompt_subcategory_id=item.get("prompt_subcategory_id")
                )
                records.append(record)
        
        return UserMinutesResponse(
            user_id=user_id,
            period_days=days,
            start_date=start_time.isoformat(),
            end_date=end_time.isoformat(),
            total_minutes=total_minutes,
            total_records=len(records),
            records=records
        )
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get user minutes",
            exc,
            details={"user_id": user_id, "days": days},
        )


@router.get("/system")
async def get_system_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(require_admin),
    cosmos_service: CosmosService = Depends(get_cosmos_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    """Get system-wide analytics (Admin only)"""
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        
        # Check if Cosmos is available
        if not cosmos_service.is_available():
            logger.warning("CosmosDB not available, returning empty analytics")
            return {
                "period_days": days,
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat(),
                "analytics": {
                    "records": [],
                    "total_minutes": 0.0,
                    "total_jobs": 0,
                    "active_users": 0
                }
            }
        
        # Query analytics data for total system metrics.
        # Analytics documents use `timestamp` for creation; some legacy docs use `created_at`.
        # Query both fields to be robust for either shape.
        analytics_query = (
            "SELECT * FROM c WHERE (IS_DEFINED(c.timestamp) AND c.timestamp >= @start_time) "
            "OR (IS_DEFINED(c.created_at) AND c.created_at >= @start_time)"
        )
        parameters = [
            {"name": "@start_time", "value": start_time.isoformat()}
        ]
        
        try:
            # Get analytics records
            analytics_container = cosmos_service.get_container("analytics")
            analytics_items = _query_container(
                analytics_container,
                action="query system analytics records",
                query=analytics_query,
                parameters=parameters,
                details={"days": days},
                error_handler=error_handler,
            )
            logger.debug("System analytics: fetched %d analytics records", len(analytics_items))
        except ApplicationError as analytics_error:
            logger.warning(
                "Error querying analytics container",
                extra={
                    "context": {
                        "days": days,
                        "error": str(analytics_error),
                    }
                },
            )
            analytics_items = []
        
        # Calculate total minutes and jobs
        total_minutes = 0.0
        total_jobs = len(analytics_items)
        for item in analytics_items:
            minutes = item.get("audio_duration_minutes")
            if isinstance(minutes, (int, float)):
                total_minutes += minutes
        
        # Get active users from sessions
        active_users = 0
        try:
            # Query for active sessions in the last 24 hours
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            session_query = """
            SELECT DISTINCT c.user_id 
            FROM c 
            WHERE ((IS_DEFINED(c.last_activity) AND c.last_activity >= @recent_cutoff) OR (IS_DEFINED(c.last_heartbeat) AND c.last_heartbeat >= @recent_cutoff))
            """
            session_parameters = [
                {"name": "@recent_cutoff", "value": recent_cutoff.isoformat()}
            ]

            try:
                sessions_container = cosmos_service.get_container("user_sessions")
                active_sessions = _query_container(
                    sessions_container,
                    action="query active user sessions",
                    query=session_query,
                    parameters=session_parameters,
                    details={"days": days},
                    error_handler=error_handler,
                )
                active_users = len(active_sessions)
                logger.debug("System analytics: found %d active session rows", len(active_sessions))
            except ApplicationError as container_error:
                logger.warning(
                    "Sessions container not available for active user count",
                    extra={"context": {"days": days, "error": str(container_error)}}
                )
                active_users = 0
        except Exception as e:
            logger.warning(f"Error getting active users: {str(e)}")
            active_users = 0
        
        return {
            "period_days": days,
            "start_date": start_time.isoformat(),
            "end_date": end_time.isoformat(),
            "analytics": {
                "records": analytics_items,
                "total_minutes": total_minutes,
                "total_jobs": total_jobs,
                "active_users": active_users
            }
        }
        
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "get system analytics",
            exc,
            details={"days": days},
        )
