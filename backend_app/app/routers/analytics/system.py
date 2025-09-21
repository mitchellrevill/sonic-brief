from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException
from ...core.dependencies import get_analytics_service, require_analytics_access
from ...services.analytics.export_service import ExportService
from ...core.config import get_app_config, get_cosmos_db_cached
from ...core.async_utils import run_sync

router = APIRouter(prefix="/api", tags=["analytics.system"])


@router.get("/analytics/system")
async def get_system_analytics(days: int = Query(30, ge=1, le=365), current_user=Depends(require_analytics_access), analytics_svc=Depends(get_analytics_service)):
    try:
        system = await analytics_svc.get_system_analytics(days) if hasattr(analytics_svc, 'get_system_analytics') else None
        # Fallback summary using analytics container directly
        if system is None:
            cfg = get_app_config()
            cosmos = get_cosmos_db_cached(cfg)
            # simple defensive aggregation
            total_minutes = 0.0
            total_jobs = 0
            if hasattr(cosmos, 'analytics_container') and cosmos.analytics_container is not None:
                query = "SELECT c.audio_duration_minutes, c.audio_duration_seconds FROM c WHERE c.timestamp >= @start"
                from datetime import timedelta
                end_date = datetime.now(timezone.utc)
                start = end_date - timedelta(days=days)
                params = [{"name": "@start", "value": start.isoformat()}]
                try:
                    items = await run_sync(lambda: list(cosmos.analytics_container.query_items(query=query, parameters=params, enable_cross_partition_query=True)))
                    for it in items:
                        m = it.get('audio_duration_minutes')
                        if m is None and it.get('audio_duration_seconds') is not None:
                            m = float(it.get('audio_duration_seconds')) / 60.0
                        if isinstance(m, (int, float)):
                            total_minutes += float(m)
                            total_jobs += 1
                except Exception:
                    pass
            system = {"period_days": days, "start_date": start.isoformat(), "end_date": end_date.isoformat(), "total_minutes": total_minutes, "total_jobs": total_jobs, "active_users": 0, "peak_active_users": 0, "analytics": {"records": [], "total_minutes": total_minutes, "total_jobs": total_jobs, "active_users": 0, "peak_active_users": 0}}
        return system
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/health")
async def get_system_health(current_user=Depends(require_analytics_access)):
    try:
        # Use SystemHealthService if available elsewhere; minimal probe here
        return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
