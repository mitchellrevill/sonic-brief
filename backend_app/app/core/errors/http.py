from fastapi import HTTPException
from fastapi.responses import JSONResponse
from typing import Dict

from .domain import ApplicationError


def to_http_exception(error: ApplicationError) -> HTTPException:
    """Convert an ``ApplicationError`` into FastAPI's ``HTTPException``."""
    return HTTPException(status_code=error.status_code, detail=error.as_dict())


def application_error_response(error: ApplicationError) -> JSONResponse:
    """Build a JSON response for the given ``ApplicationError``."""
    payload: Dict[str, object] = {
        "message": error.message,
        "error_code": error.error_code.value,
        "details": error.details,
    }
    return JSONResponse(status_code=error.status_code, content=payload)
