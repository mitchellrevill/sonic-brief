import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from typing import Optional
from ...core.dependencies import require_analytics_access, get_export_service, get_error_handler
from ...services.interfaces import ExportServiceInterface
from ...core.errors import ApplicationError, ErrorCode, ErrorHandler, ValidationError

router = APIRouter(prefix="/export", tags=["analytics.export"])
logger = logging.getLogger(__name__)

def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    message: str | None = None,
    details: dict | None = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        message=message,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )

@router.get("/system/csv")
async def export_system_csv(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(require_analytics_access),
    export_service: ExportServiceInterface = Depends(get_export_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    def _handle_internal_error(
        error_handler: ErrorHandler,
        action: str,
        exc: Exception,
        *,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        message: str | None = None,
        details: dict | None = None,
    ) -> None:
        error_handler.raise_internal(
            action,
            exc,
            message=message,
            error_code=error_code,
            status_code=status_code,
            extra=details,
        )

    try:
        result = await export_service.export_system_analytics_csv(days)
        if result.get("status") != "success":
            raise ApplicationError(
                result.get("message", "Export failed."),
                ErrorCode.EXTERNAL_SERVICE_ERROR,
                status_code=500,
                details={
                    "operation": "export_system_analytics_csv",
                    "days": days,
                },
            )

        return FileResponse(
            path=result["file_path"],
            media_type=result["content_type"],
            filename=result["filename"],
            background=lambda: export_service.cleanup_temp_file(result["file_path"]),
        )
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(error_handler, "export system analytics csv", exc, details={"days": days})


@router.post("/users/{format}")
async def export_users(
    format: str, 
    export_request: Optional[dict] = None, 
    current_user=Depends(require_analytics_access),
    export_service: ExportServiceInterface = Depends(get_export_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    if format not in ("csv", "pdf"):
        raise ValidationError(
            "Format must be 'csv' or 'pdf'",
            field="format",
            details={"provided": format},
        )
    try:
        filters = export_request.get("filters") if export_request else None
        if format == "csv":
            result = await export_service.export_users_csv(filters)
        else:
            raise ApplicationError(
                "PDF export not implemented",
                ErrorCode.OPERATION_NOT_ALLOWED,
                status_code=501,
                details={"format": format},
            )

        if result.get("status") == "error":
            raise ApplicationError(
                result.get("message", "Export failed."),
                ErrorCode.EXTERNAL_SERVICE_ERROR,
                status_code=500,
                details={
                    "operation": "export_users_csv",
                    "format": format,
                    "filters": filters,
                },
            )

        return FileResponse(
            path=result["file_path"],
            media_type=result["content_type"],
            filename=result["filename"],
            background=lambda: export_service.cleanup_temp_file(result["file_path"]),
        )
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(error_handler, "export users", exc, details={"format": format})


@router.get("/users/{user_id}/pdf")
async def export_user_pdf(
    user_id: str, 
    include_analytics: bool = Query(True), 
    days: int = Query(30, ge=1, le=365), 
    current_user=Depends(require_analytics_access),
    export_service: ExportServiceInterface = Depends(get_export_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
):
    try:
        result = await export_service.export_user_details_pdf(user_id, include_analytics, days)
        if result.get("status") == "error":
            raise ApplicationError(
                result.get("message", "Export failed."),
                ErrorCode.EXTERNAL_SERVICE_ERROR,
                status_code=500,
                details={
                    "operation": "export_user_details_pdf",
                    "user_id": user_id,
                    "include_analytics": include_analytics,
                    "days": days,
                },
            )

        return FileResponse(
            path=result["file_path"],
            media_type=result["content_type"],
            filename=result["filename"],
            background=lambda: export_service.cleanup_temp_file(result["file_path"]),
        )
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "export user pdf",
            exc,
            details={
                "user_id": user_id,
                "include_analytics": include_analytics,
                "days": days,
            },
        )
