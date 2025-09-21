from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, Query, HTTPException
from ...core.dependencies import get_analytics_service, get_current_user
from ...models.analytics_models import UserAnalyticsResponse, UserMinutesResponse, UserDetailsResponse
from ...core.dependencies import require_analytics_access, require_user
from ...core.config import get_cosmos_db_cached, get_app_config

router = APIRouter(prefix="/api", tags=["analytics.users"])


@router.get("/analytics/users/{user_id}", response_model=UserAnalyticsResponse)
async def get_user_analytics(user_id: str, days: int = Query(30, ge=1, le=365), current_user: Dict[str, Any] = Depends(require_analytics_access), analytics_svc=Depends(get_analytics_service)):
    try:
        data = await analytics_svc.get_user_analytics(user_id, days)
        return {
            "user_id": user_id,
            "period_days": data.get("period_days", days),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "analytics": data.get("analytics", {}),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/users/{user_id}/minutes", response_model=UserMinutesResponse)
async def get_user_minutes(user_id: str, days: int = Query(30, ge=1, le=365), current_user=Depends(require_analytics_access), analytics_svc=Depends(get_analytics_service)):
    try:
        data = await analytics_svc.get_user_minutes_records(user_id, days)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/auth/users/{user_id}/details", response_model=UserDetailsResponse)
async def get_user_details(user_id: str, include_analytics: bool = Query(True), current_user=Depends(require_analytics_access), analytics_svc=Depends(get_analytics_service)):
    try:
        cfg = get_app_config()
        cosmos = get_cosmos_db_cached(cfg)
        user = await cosmos.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        analytics = None
        if include_analytics:
            analytics_data = await analytics_svc.get_user_analytics(user_id, days=30)
            analytics = analytics_data.get('analytics', {})
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
            "analytics": analytics,
        }
        return UserDetailsResponse(**user_details)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
