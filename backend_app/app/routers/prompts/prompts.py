from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
import logging
from ...core.config import DatabaseError
from ...core.dependencies import get_current_user, require_prompt_management, require_user, require_editor
from ...services.prompts.talking_points_service import talking_points_service, TalkingPointSection
from ...services.prompts.prompt_service import prompt_service
from ...core.async_utils import run_sync

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
def validate_talking_points_structure(talking_points: List[TalkingPointSection]) -> List[Dict[str, Any]]:
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


def convert_talking_points_to_response(talking_points_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Return the service-converted structure (dicts) to keep router light
    return talking_points_service.convert_talking_points_to_response(talking_points_data)


def migrate_legacy_talking_points(legacy_points: list) -> list:
    """
    Migrate legacy talking points format to new structured format
    
    Args:
        legacy_points: List of strings (old format)
        
    Returns:
        List of structured talking points (new format)
    """
    # Delegate to service implementation which handles legacy formats
    return talking_points_service.migrate_legacy_talking_points(legacy_points)


def ensure_talking_points_structure(subcategory_data: dict) -> dict:
    """
    Ensure talking points are in the correct format, migrating if necessary
    """
    return talking_points_service.ensure_talking_points_structure(subcategory_data)


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
    _auth: str = Depends(require_prompt_management),
) -> Dict[str, Any]:
    """Create a new prompt category (requires prompt management capability)."""
    try:
        # Reuse service which uses cached DB client
        created = await run_sync(prompt_service.create_category, category.name, getattr(category, "parent_category_id", None))
        return created
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating category", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(current_user: dict = Depends(get_current_user), _auth: str = Depends(require_user)) -> List[Dict[str, Any]]:
    """List all prompt categories (any authenticated user)."""
    try:
        return await run_sync(prompt_service.list_categories)
    except Exception as e:
        logger.error("Error listing categories", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_user)) -> Dict[str, Any]:
    try:
        item = await run_sync(prompt_service.get_category, category_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Category with id '{category_id}' not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving category", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: str, category: CategoryUpdate, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_prompt_management)) -> Dict[str, Any]:
    try:
        updated = await run_sync(prompt_service.update_category, category_id, category.name, getattr(category, "parent_category_id", None))
        if not updated:
            raise HTTPException(status_code=404, detail=f"Category with id '{category_id}' not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating category", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_prompt_management)) -> Dict[str, Any]:
    try:
        # Ensure category exists first to provide clear 404 when absent
        existing = await run_sync(prompt_service.get_category, category_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Category with id '{category_id}' not found")
        await run_sync(prompt_service.delete_category_and_subcategories, category_id)
        return {"status": 200, "message": f"Category '{category_id}' and its subcategories deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting category", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subcategories", response_model=SubcategoryResponse)
async def create_subcategory(subcategory: SubcategoryCreate, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_prompt_management)) -> Dict[str, Any]:
    """Create a new prompt subcategory (requires prompt management capability)."""
    try:
        # Validate talking points via service
        pre_session_dict = [section.dict() for section in subcategory.preSessionTalkingPoints]
        in_session_dict = [section.dict() for section in subcategory.inSessionTalkingPoints]
        try:
            validated_pre = talking_points_service.validate_talking_points_structure(pre_session_dict)
            validated_in = talking_points_service.validate_talking_points_structure(in_session_dict)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid talking points structure: {str(e)}")

        # Ensure category exists
        cat = await run_sync(prompt_service.get_category, subcategory.category_id)
        if not cat:
            raise HTTPException(status_code=404, detail=f"Category with id '{subcategory.category_id}' not found")

        created = await run_sync(prompt_service.create_subcategory, subcategory.category_id, subcategory.name, subcategory.prompts, validated_pre, validated_in)
        created = talking_points_service.ensure_talking_points_structure(created)
        return created
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating subcategory", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subcategories", response_model=List[SubcategoryResponse])
async def list_subcategories(category_id: Optional[str] = None, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_user)) -> List[Dict[str, Any]]:
    try:
        subs = await run_sync(prompt_service.list_subcategories, category_id)
        subs = [talking_points_service.ensure_talking_points_structure(s) for s in subs]
        return subs
    except Exception as e:
        logger.error("Error listing subcategories", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
async def get_subcategory(subcategory_id: str, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_user)) -> Dict[str, Any]:
    try:
        sub = await run_sync(prompt_service.get_subcategory, subcategory_id)
        if not sub:
            raise HTTPException(status_code=404, detail=f"Subcategory with id '{subcategory_id}' not found")
        sub = talking_points_service.ensure_talking_points_structure(sub)
        return sub
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving subcategory", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
async def update_subcategory(subcategory_id: str, subcategory: SubcategoryUpdate, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_prompt_management)) -> Dict[str, Any]:
    try:
        pre_session_dict = [section.dict() for section in subcategory.preSessionTalkingPoints]
        in_session_dict = [section.dict() for section in subcategory.inSessionTalkingPoints]
        try:
            validated_pre = talking_points_service.validate_talking_points_structure(pre_session_dict)
            validated_in = talking_points_service.validate_talking_points_structure(in_session_dict)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid talking points structure: {str(e)}")

        updated = await run_sync(prompt_service.update_subcategory, subcategory_id, subcategory.name, subcategory.prompts, validated_pre, validated_in)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Subcategory with id '{subcategory_id}' not found")
        updated = talking_points_service.ensure_talking_points_structure(updated)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating subcategory", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/subcategories/{subcategory_id}")
async def delete_subcategory(subcategory_id: str, current_user: dict = Depends(get_current_user), _auth: str = Depends(require_prompt_management)) -> Dict[str, Any]:
    try:
        # Ensure subcategory exists first for clear 404 mapping
        existing = await run_sync(prompt_service.get_subcategory, subcategory_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Subcategory with id '{subcategory_id}' not found")
        await run_sync(prompt_service.delete_subcategory, subcategory_id)
        return {"status": 200, "message": f"Subcategory '{subcategory_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting subcategory", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
async def retrieve_prompts(current_user: dict = Depends(get_current_user), _auth: str = Depends(require_user)) -> Dict[str, Any]:
    try:
        data = await run_sync(prompt_service.retrieve_prompts_hierarchy)
        return {"status": 200, "data": data}
    except DatabaseError:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    except Exception as e:
        logger.error("Error retrieving prompts", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
