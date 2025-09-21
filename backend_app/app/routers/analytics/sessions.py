from datetime import datetime, timezone
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from ...core.dependencies import get_analytics_service, require_analytics_access, get_current_user, get_session_tracker

router = APIRouter(prefix="/api", tags=["analytics.sessions"])


class SessionEventIn:
    action: str
    page: Optional[str] = None


@router.post("/analytics/session")
async def post_session_event(session_request: dict, request: Request, current_user=Depends(get_current_user), analytics_svc=Depends(get_analytics_service)):
    try:
        user_agent = request.headers.get('User-Agent')
        ip = request.headers.get('X-Forwarded-For') or (request.client.host if request.client else None)
        session_tracker = get_session_tracker()
        session_id = str(uuid.uuid4())
        session_tracker.upsert(session_id, {
            "id": session_id,
            "user_id": current_user['id'],
            "action": session_request.get('action'),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "user_agent": user_agent,
                "ip_address": ip
            }
        })
        session_event_id = session_id
        return {"status": "success", "session_event_id": session_event_id, "message": f"Session {session_request.get('action')} tracked"}
    except Exception as e:
        return {"status": "error", "session_event_id": "", "message": str(e)}


@router.get("/analytics/active-users")
async def get_active_users(minutes: int = Query(5), current_user=Depends(require_analytics_access), analytics_svc=Depends(get_analytics_service)):
    try:
        users = await analytics_svc.get_active_users(minutes)
        return {"status": "success", "data": {"active_users": users, "count": len(users), "period_minutes": minutes, "timestamp": datetime.now(timezone.utc).isoformat()}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/user-session-duration/{user_id}")
async def get_user_session_duration(user_id: str, days: int = Query(1), current_user=Depends(require_analytics_access), analytics_svc=Depends(get_analytics_service)):
    try:
        duration = await analytics_svc.get_user_session_duration(user_id=user_id, days=days)
        return {"status": "success", "data": {"user_id": user_id, "total_session_duration_minutes": duration, "period_days": days, "timestamp": datetime.now(timezone.utc).isoformat()}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
