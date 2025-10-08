from fastapi import APIRouter, Depends
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging
from ...core.config import DatabaseError
from ...core.dependencies import (
    get_current_user,
    require_user,
    require_editor,
    get_prompt_service,
    get_talking_points_service,
    get_error_handler,
)
from ...core.errors import (
    ApplicationError,
    ValidationError,
    ErrorCode,
    ErrorHandler,
    ResourceNotFoundError,
)
from ...models.permissions import PermissionLevel, has_permission_level
from ...services.prompts.talking_points_service import TalkingPointSection
from ...services.interfaces import PromptServiceInterface, TalkingPointsServiceInterface
from ...utils.async_utils import run_sync

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="", tags=["prompts"])


"""
Prompts router: expose CRUD and retrieval endpoints for prompt categories and subcategories.

This module delegates validation and conversion of talking points to
the talking_points_service and persistence to prompt_service.
"""


# Talking Points Models
# Use TalkingPointSection from talking_points_service for Pydantic models


# Validation and conversion functions for talking points
def validate_talking_points_structure(
    talking_points: List[TalkingPointSection], 
    talking_points_service: TalkingPointsServiceInterface
) -> List[Dict[str, Any]]:
    # Delegate to talking_points_service which contains robust validation
    # Accept either Pydantic sections or raw dicts
    try:
        # If Pydantic models were passed, convert to dicts
        raw = [s.dict() if hasattr(s, "dict") else s for s in talking_points]
        return talking_points_service.validate_talking_points_structure(raw)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(str(e))


def convert_talking_points_to_response(
    talking_points_data: List[Dict[str, Any]], 
    talking_points_service: TalkingPointsServiceInterface
) -> List[Dict[str, Any]]:
    # Return the service-converted structure (dicts) to keep router light
    return talking_points_service.convert_talking_points_to_response(talking_points_data)


def migrate_legacy_talking_points(
    legacy_points: list, 
    talking_points_service: TalkingPointsServiceInterface
) -> list:
    """
    Migrate legacy talking points format to new structured format
    
    Args:
        legacy_points: List of strings (old format)
        
    Returns:
        List of structured talking points (new format)
    """
    # Delegate to service implementation which handles legacy formats
    return talking_points_service.migrate_legacy_talking_points(legacy_points)


def ensure_talking_points_structure(
    subcategory_data: dict, 
    talking_points_service: TalkingPointsServiceInterface
) -> dict:
    """
    Ensure talking points are in the correct format, migrating if necessary
    """
    return talking_points_service.ensure_talking_points_structure(subcategory_data)


def _handle_internal_error(
    error_handler: ErrorHandler,
    action: str,
    exc: Exception,
    *,
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    status_code: int = 500,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    error_handler.raise_internal(
        action,
        exc,
        message=message,
        error_code=error_code,
        status_code=status_code,
        extra=details,
    )


class PromptKey(BaseModel):
    key: str
    prompt: str


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    parent_category_id: Optional[str] = None


class CategoryUpdate(CategoryBase):
    parent_category_id: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: str
    created_at: int
    updated_at: int
    parent_category_id: Optional[str] = None


class SubcategoryBase(BaseModel):
    name: str
    prompts: Dict[str, str]
    preSessionTalkingPoints: List[TalkingPointSection] = Field(default_factory=list)
    inSessionTalkingPoints: List[TalkingPointSection] = Field(default_factory=list)


class SubcategoryCreate(SubcategoryBase):
    category_id: str


class SubcategoryUpdate(SubcategoryBase):
    pass


class SubcategoryResponse(SubcategoryBase):
    id: str
    category_id: str
    created_at: int
    updated_at: int


# Category CRUD operations
@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category: CategoryCreate,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_editor),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    """Create a new prompt category (requires prompt management capability)."""
    try:
        created = await run_sync(
            prompt_service.create_category,
            category.name,
            getattr(category, "parent_category_id", None),
        )
        return created
    except DatabaseError as exc:
        _handle_internal_error(
            error_handler,
            "create prompt category",
            exc,
            message="Database service unavailable",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
            details={"category": category.dict()},
        )
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "create prompt category",
            exc,
            details={"category": category.dict()},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_user: dict = Depends(get_current_user), 
    auth_context: str = Depends(require_user),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> List[Dict[str, Any]]:
    """List all prompt categories (requires CAN_VIEW_PROMPTS capability)."""
    try:
        return await run_sync(prompt_service.list_categories)
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "list prompt categories",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str, 
    current_user: dict = Depends(get_current_user), 
    auth_context: str = Depends(require_user),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        item = await run_sync(prompt_service.get_category, category_id)
        if not item:
            raise ResourceNotFoundError("Prompt category", category_id)
        return item
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "retrieve prompt category",
            exc,
            details={"category_id": category_id},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category: CategoryUpdate,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_editor),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        updated = await run_sync(
            prompt_service.update_category,
            category_id,
            category.name,
            getattr(category, "parent_category_id", None),
        )
        if not updated:
            raise ResourceNotFoundError("Prompt category", category_id)
        return updated
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "update prompt category",
            exc,
            details={"category_id": category_id, "payload": category.dict()},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_editor),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        # Ensure category exists first to provide clear 404 when absent
        existing = await run_sync(prompt_service.get_category, category_id)
        if not existing:
            raise ResourceNotFoundError("Prompt category", category_id)
        await run_sync(prompt_service.delete_category_and_subcategories, category_id)
        return {"status": 200, "message": f"Category '{category_id}' and its subcategories deleted successfully"}
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "delete prompt category",
            exc,
            details={"category_id": category_id},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.post("/subcategories", response_model=SubcategoryResponse)
async def create_subcategory(
    subcategory: SubcategoryCreate,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_editor),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    talking_points_service: TalkingPointsServiceInterface = Depends(get_talking_points_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    """Create a new prompt subcategory (requires prompt management capability)."""
    try:
        # Validate talking points via service
        pre_session_dict = [section.dict() for section in subcategory.preSessionTalkingPoints]
        in_session_dict = [section.dict() for section in subcategory.inSessionTalkingPoints]
        try:
            validated_pre = talking_points_service.validate_talking_points_structure(pre_session_dict)
            validated_in = talking_points_service.validate_talking_points_structure(in_session_dict)
        except ValueError as exc:
            logger.warning("Invalid talking points structure while creating subcategory: %s", exc)
            raise ValidationError(
                "Invalid talking points structure",
                details={"error": str(exc)},
            )

        # Ensure category exists
        cat = await run_sync(prompt_service.get_category, subcategory.category_id)
        if not cat:
            raise ResourceNotFoundError("Prompt category", subcategory.category_id)

        created = await run_sync(
            prompt_service.create_subcategory,
            subcategory.category_id,
            subcategory.name,
            subcategory.prompts,
            validated_pre,
            validated_in,
        )
        created = ensure_talking_points_structure(created, talking_points_service)
        return created
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "create prompt subcategory",
            exc,
            details={
                "category_id": subcategory.category_id,
                "subcategory": subcategory.dict(),
            },
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/subcategories", response_model=List[SubcategoryResponse])
async def list_subcategories(
    category_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_user),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    talking_points_service: TalkingPointsServiceInterface = Depends(get_talking_points_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> List[Dict[str, Any]]:
    try:
        subs = await run_sync(prompt_service.list_subcategories, category_id)
        subs = [ensure_talking_points_structure(s, talking_points_service) for s in subs]
        return subs
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "list prompt subcategories",
            exc,
            details={"category_id": category_id},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.get("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
async def get_subcategory(
    subcategory_id: str,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_user),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    talking_points_service: TalkingPointsServiceInterface = Depends(get_talking_points_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        sub = await run_sync(prompt_service.get_subcategory, subcategory_id)
        if not sub:
            raise ResourceNotFoundError("Prompt subcategory", subcategory_id)
        sub = ensure_talking_points_structure(sub, talking_points_service)
        return sub
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "retrieve prompt subcategory",
            exc,
            details={"subcategory_id": subcategory_id},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.put("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
async def update_subcategory(
    subcategory_id: str,
    subcategory: SubcategoryUpdate,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_editor),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    talking_points_service: TalkingPointsServiceInterface = Depends(get_talking_points_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        pre_session_dict = [section.dict() for section in subcategory.preSessionTalkingPoints]
        in_session_dict = [section.dict() for section in subcategory.inSessionTalkingPoints]
        try:
            validated_pre = talking_points_service.validate_talking_points_structure(pre_session_dict)
            validated_in = talking_points_service.validate_talking_points_structure(in_session_dict)
        except ValueError as exc:
            logger.warning("Invalid talking points structure while updating subcategory: %s", exc)
            raise ValidationError(
                "Invalid talking points structure",
                details={"error": str(exc)},
            )

        updated = await run_sync(
            prompt_service.update_subcategory,
            subcategory_id,
            subcategory.name,
            subcategory.prompts,
            validated_pre,
            validated_in,
        )
        if not updated:
            raise ResourceNotFoundError("Prompt subcategory", subcategory_id)
        updated = ensure_talking_points_structure(updated, talking_points_service)
        return updated
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "update prompt subcategory",
            exc,
            details={
                "subcategory_id": subcategory_id,
                "payload": subcategory.dict(),
            },
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


@router.delete("/subcategories/{subcategory_id}")
async def delete_subcategory(
    subcategory_id: str,
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_editor),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        # Ensure subcategory exists first for clear 404 mapping
        existing = await run_sync(prompt_service.get_subcategory, subcategory_id)
        if not existing:
            raise ResourceNotFoundError("Prompt subcategory", subcategory_id)
        await run_sync(prompt_service.delete_subcategory, subcategory_id)
        return {"status": 200, "message": f"Subcategory '{subcategory_id}' deleted successfully"}
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "delete prompt subcategory",
            exc,
            details={"subcategory_id": subcategory_id},
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )


# Hierarchical API for retrieving all data
class PromptSubcategoryResponse(BaseModel):
    subcategory_name: str
    subcategory_id: str
    prompts: Dict[str, str]
    preSessionTalkingPoints: Optional[list] = []
    inSessionTalkingPoints: Optional[list] = []


class PromptCategoryResponse(BaseModel):
    category_name: str
    category_id: str
    subcategories: List[PromptSubcategoryResponse]


class AllPromptsResponse(BaseModel):
    status: int
    data: List[PromptCategoryResponse]


@router.get("/retrieve_prompts", response_model=AllPromptsResponse)
async def retrieve_prompts(
    current_user: dict = Depends(get_current_user),
    auth_context: str = Depends(require_user),
    prompt_service: PromptServiceInterface = Depends(get_prompt_service),
    error_handler: ErrorHandler = Depends(get_error_handler),
) -> Dict[str, Any]:
    try:
        data = await run_sync(prompt_service.retrieve_prompts_hierarchy)
        return {"status": 200, "data": data}
    except DatabaseError as exc:
        _handle_internal_error(
            error_handler,
            "retrieve prompt hierarchy",
            exc,
            message="Database service unavailable",
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=503,
        )
    except ApplicationError:
        raise
    except Exception as exc:
        _handle_internal_error(
            error_handler,
            "retrieve prompt hierarchy",
            exc,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
        )
