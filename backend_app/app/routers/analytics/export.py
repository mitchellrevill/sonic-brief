from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
from ...core.dependencies import get_analytics_service, require_analytics_access
from ...services.analytics import ExportService
from ...core.config import get_app_config, get_cosmos_db_cached

router = APIRouter(prefix="/api", tags=["analytics.export"])


@router.get("/export/system/csv")
async def export_system_csv(days: int = Query(30, ge=1, le=365), current_user=Depends(require_analytics_access)):
    try:
        cfg = get_app_config()
        cosmos = get_cosmos_db_cached(cfg)
        svc = ExportService(cosmos)
        result = await svc.export_system_analytics_csv(days)
        if result.get('status') != 'success':
            raise HTTPException(status_code=500, detail=result.get('message', 'Export failed'))
        return FileResponse(path=result['file_path'], media_type=result['content_type'], filename=result['filename'], background=lambda: svc.cleanup_temp_file(result['file_path']))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/users/{format}")
async def export_users(format: str, export_request: Optional[dict] = None, current_user=Depends(require_analytics_access)):
    if format not in ('csv', 'pdf'):
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'pdf'")
    try:
        cfg = get_app_config()
        cosmos = get_cosmos_db_cached(cfg)
        svc = ExportService(cosmos)
        filters = export_request.get('filters') if export_request else None
        if format == 'csv':
            result = await svc.export_users_csv(filters)
        else:
            raise HTTPException(status_code=501, detail='PDF export not implemented')
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('message'))
        return FileResponse(path=result['file_path'], media_type=result['content_type'], filename=result['filename'], background=lambda: svc.cleanup_temp_file(result['file_path']))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/users/{user_id}/pdf")
async def export_user_pdf(user_id: str, include_analytics: bool = Query(True), days: int = Query(30, ge=1, le=365), current_user=Depends(require_analytics_access)):
    try:
        cfg = get_app_config()
        cosmos = get_cosmos_db_cached(cfg)
        svc = ExportService(cosmos)
        result = await svc.export_user_details_pdf(user_id, include_analytics, days)
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('message'))
        return FileResponse(path=result['file_path'], media_type=result['content_type'], filename=result['filename'], background=lambda: svc.cleanup_temp_file(result['file_path']))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
