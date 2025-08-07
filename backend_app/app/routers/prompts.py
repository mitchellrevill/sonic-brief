from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
import logging
from datetime import datetime, timezone
import uuid

from app.core.config import AppConfig, CosmosDB, get_cosmos_db, DatabaseError
from app.routers.auth import get_current_user
from app.routers.auth import get_current_user
from app.services.talking_points_service import (
    talking_points_service,
    TalkingPointField,
    TalkingPointSection,
    TalkingPointsData
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter(prefix="/api", tags=["prompts"])


# Talking Points Models
class TalkingPointField(BaseModel):
    """Individual field within a talking point section"""
    name: str = Field(..., description="Field name/identifier")
    type: str = Field(..., description="Field type: text, date, markdown, checkbox, number, select")
    value: Union[str, bool, float, None] = Field(None, description="Field value")
    label: Optional[str] = Field(None, description="Display label for the field")
    placeholder: Optional[str] = Field(None, description="Placeholder text for input fields")
    description: Optional[str] = Field(None, description="Help text describing the field")
    required: Optional[bool] = Field(False, description="Whether the field is required")
    options: Optional[str] = Field(None, description="Comma-separated options for select fields")


class TalkingPointSection(BaseModel):
    """A section containing multiple fields"""
    fields: List[TalkingPointField] = Field(default_factory=list, description="List of fields in this section")


# Validation and conversion functions for talking points
def validate_talking_points_structure(talking_points: List[TalkingPointSection]) -> List[Dict[str, Any]]:
    """
    Validate and convert talking points to database format
    """
    validated_points = []
    
    for section in talking_points:
        validated_fields = []
        
        for field in section.fields:
            # Validate field type
            if field.type not in ['text', 'date', 'markdown', 'checkbox', 'number', 'select']:
                raise ValueError(f"Invalid field type: {field.type}")
            
            # Validate field value based on type
            validated_value = field.value
            if field.type == 'checkbox':
                validated_value = bool(field.value) if field.value is not None else False
            elif field.type == 'date':
                # Additional date validation could be added here
                validated_value = str(field.value) if field.value is not None else ""
            elif field.type == 'number':
                try:
                    validated_value = float(field.value) if field.value is not None else 0
                except (ValueError, TypeError):
                    validated_value = 0
            elif field.type in ['text', 'markdown', 'select']:
                validated_value = str(field.value) if field.value is not None else ""
            
            validated_fields.append({
                "name": field.name.strip(),
                "type": field.type,
                "value": validated_value,
                "label": field.label or "",
                "placeholder": field.placeholder or "",
                "description": field.description or "",
                "required": field.required or False,
                "options": field.options or ""
            })
        
        if validated_fields:  # Only add sections with fields
            validated_points.append({
                "fields": validated_fields
            })
    
    return validated_points


def convert_talking_points_to_response(talking_points_data: List[Dict[str, Any]]) -> List[TalkingPointSection]:
    """
    Convert database talking points to response format
    """
    sections = []
    
    for section_data in talking_points_data:
        fields = []
        for field_data in section_data.get("fields", []):
            fields.append(TalkingPointField(
                name=field_data.get("name", ""),
                type=field_data.get("type", "text"),
                value=field_data.get("value"),
                label=field_data.get("label", ""),
                placeholder=field_data.get("placeholder", ""),
                description=field_data.get("description", ""),
                required=field_data.get("required", False),
                options=field_data.get("options", "")
            ))
        
        sections.append(TalkingPointSection(fields=fields))
    
    return sections


def migrate_legacy_talking_points(legacy_points: list) -> list:
    """
    Migrate legacy talking points format to new structured format
    
    Args:
        legacy_points: List of strings (old format)
        
    Returns:
        List of structured talking points (new format)
    """
    migrated_points = []
    
    for i, point in enumerate(legacy_points):
        if isinstance(point, str):
            # Legacy format: simple string
            migrated_points.append({
                "fields": [
                    {
                        "name": f"Point {i + 1}",
                        "type": "text",
                        "value": point,
                        "label": f"Point {i + 1}",
                        "placeholder": "",
                        "description": "",
                        "required": False,
                        "options": ""
                    }
                ]
            })
        elif isinstance(point, dict) and "fields" in point:
            # Already in new format, but ensure all fields have the new properties
            migrated_fields = []
            for field in point.get("fields", []):
                migrated_field = {
                    "name": field.get("name", f"Field {len(migrated_fields) + 1}"),
                    "type": field.get("type", "text"),
                    "value": field.get("value", ""),
                    "label": field.get("label", field.get("name", f"Field {len(migrated_fields) + 1}")),
                    "placeholder": field.get("placeholder", ""),
                    "description": field.get("description", ""),
                    "required": field.get("required", False),
                    "options": field.get("options", "")
                }
                migrated_fields.append(migrated_field)
            migrated_points.append({"fields": migrated_fields})
        else:
            # Unknown format, create default text field
            migrated_points.append({
                "fields": [
                    {
                        "name": f"Point {i + 1}",
                        "type": "text", 
                        "value": str(point),
                        "label": f"Point {i + 1}",
                        "placeholder": "",
                        "description": "",
                        "required": False,
                        "options": ""
                    }
                ]
            })
    
    return migrated_points


def ensure_talking_points_structure(subcategory_data: dict) -> dict:
    """
    Ensure talking points are in the correct format, migrating if necessary
    """
    # Migrate pre-session talking points
    pre_session = subcategory_data.get("preSessionTalkingPoints", [])
    if pre_session and len(pre_session) > 0:
        # Check if it's legacy format (list of strings)
        if isinstance(pre_session[0], str):
            subcategory_data["preSessionTalkingPoints"] = migrate_legacy_talking_points(pre_session)
    
    # Migrate in-session talking points  
    in_session = subcategory_data.get("inSessionTalkingPoints", [])
    if in_session and len(in_session) > 0:
        # Check if it's legacy format (list of strings)
        if isinstance(in_session[0], str):
            subcategory_data["inSessionTalkingPoints"] = migrate_legacy_talking_points(in_session)
    
    return subcategory_data


class PromptKey(BaseModel):
    key: str
    prompt: str


class CategoryBase(BaseModel):
    name: str


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: str
    created_at: int
    updated_at: int


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
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new prompt category"""
    try:
        config = AppConfig()
        try:
            cosmos_db = get_cosmos_db(config)
            logger.debug("CosmosDB client initialized for category creation")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)

        # Check if category already exists
        existing_category_query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_category' AND c.name = @name",
            "parameters": [{"name": "@name", "value": category.name}],
        }
        existing_categories = list(
            cosmos_db.prompts_container.query_items(
                query=existing_category_query["query"],
                parameters=existing_category_query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        if existing_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Category with name '{category.name}' already exists",
            )

        category_id = f"category_{timestamp}"
        category_data = {
            "id": category_id,
            "type": "prompt_category",
            "name": category.name,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        created_category = cosmos_db.prompts_container.create_item(body=category_data)
        return created_category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create category: {str(e)}",
        )


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all prompt categories"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        query = "SELECT * FROM c WHERE c.type = 'prompt_category'"
        categories = list(
            cosmos_db.prompts_container.query_items(
                query=query,
                enable_cross_partition_query=True,
            )
        )

        return categories

    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list categories: {str(e)}",
        )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a specific prompt category"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_category' AND c.id = @id",
            "parameters": [{"name": "@id", "value": category_id}],
        }

        categories = list(
            cosmos_db.prompts_container.query_items(
                query=query["query"],
                parameters=query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        if not categories:
            raise HTTPException(
                status_code=404,
                detail=f"Category with id '{category_id}' not found",
            )

        return categories[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve category: {str(e)}",
        )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category: CategoryUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a prompt category"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        # Check if category exists
        query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_category' AND c.id = @id",
            "parameters": [{"name": "@id", "value": category_id}],
        }

        categories = list(
            cosmos_db.prompts_container.query_items(
                query=query["query"],
                parameters=query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        if not categories:
            raise HTTPException(
                status_code=404,
                detail=f"Category with id '{category_id}' not found",
            )

        category_data = categories[0]
        category_data["name"] = category.name
        category_data["updated_at"] = int(datetime.now(timezone.utc).timestamp() * 1000)

        updated_category = cosmos_db.prompts_container.upsert_item(body=category_data)
        return updated_category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update category: {str(e)}",
        )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a prompt category and all its subcategories"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        # Delete all subcategories first
        subcategories_query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.category_id = @category_id",
            "parameters": [{"name": "@category_id", "value": category_id}],
        }

        subcategories = list(
            cosmos_db.prompts_container.query_items(
                query=subcategories_query["query"],
                parameters=subcategories_query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        for subcategory in subcategories:
            cosmos_db.prompts_container.delete_item(
                item=subcategory["id"],
                partition_key=subcategory["id"],
            )

        # Delete the category
        try:
            cosmos_db.prompts_container.delete_item(
                item=category_id,
                partition_key=category_id,
            )
        except Exception as e:
            if "404" in str(e):
                raise HTTPException(
                    status_code=404,
                    detail=f"Category with id '{category_id}' not found",
                )
            raise

        return {
            "status": 200,
            "message": f"Category '{category_id}' and its subcategories deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete category: {str(e)}",
        )


@router.post("/subcategories", response_model=SubcategoryResponse)
async def create_subcategory(
    subcategory: SubcategoryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new prompt subcategory"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        # Check if category exists
        category_query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_category' AND c.id = @id",
            "parameters": [{"name": "@id", "value": subcategory.category_id}],
        }

        categories = list(
            cosmos_db.prompts_container.query_items(
                query=category_query["query"],
                parameters=category_query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        if not categories:
            raise HTTPException(
                status_code=404,
                detail=f"Category with id '{subcategory.category_id}' not found",
            )

        # Validate and convert talking points using the service
        try:
            # Convert Pydantic models to dict format for validation
            pre_session_dict = [section.dict() for section in subcategory.preSessionTalkingPoints]
            in_session_dict = [section.dict() for section in subcategory.inSessionTalkingPoints]
            
            validated_pre_session = talking_points_service.validate_talking_points_structure(pre_session_dict)
            validated_in_session = talking_points_service.validate_talking_points_structure(in_session_dict)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid talking points structure: {str(e)}"
            )

        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        subcategory_id = f"subcategory_{timestamp}_{subcategory.name}"

        subcategory_data = {
            "id": subcategory_id,
            "type": "prompt_subcategory",
            "category_id": subcategory.category_id,
            "name": subcategory.name,
            "prompts": subcategory.prompts,
            "preSessionTalkingPoints": validated_pre_session,
            "inSessionTalkingPoints": validated_in_session,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        created_subcategory = cosmos_db.prompts_container.create_item(
            body=subcategory_data
        )
        
        # Ensure proper format for response
        created_subcategory = talking_points_service.ensure_talking_points_structure(created_subcategory)
        
        return created_subcategory

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subcategory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subcategory: {str(e)}",
        )


@router.get("/subcategories", response_model=List[SubcategoryResponse])
async def list_subcategories(
    category_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List all prompt subcategories, optionally filtered by category_id"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        if category_id:
            query = {
                "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.category_id = @category_id",
                "parameters": [{"name": "@category_id", "value": category_id}],
            }
            subcategories = list(
                cosmos_db.prompts_container.query_items(
                    query=query["query"],
                    parameters=query["parameters"],
                    enable_cross_partition_query=True,
                )
            )
        else:
            query = "SELECT * FROM c WHERE c.type = 'prompt_subcategory'"
            subcategories = list(
                cosmos_db.prompts_container.query_items(
                    query=query,
                    enable_cross_partition_query=True,
                )
            )

        # Ensure proper talking points structure for all subcategories
        subcategories = [talking_points_service.ensure_talking_points_structure(sub) for sub in subcategories]
        
        return subcategories

    except Exception as e:
        logger.error(f"Error listing subcategories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list subcategories: {str(e)}",
        )


@router.get("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
async def get_subcategory(
    subcategory_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a specific prompt subcategory"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.id = @id",
            "parameters": [{"name": "@id", "value": subcategory_id}],
        }

        subcategories = list(
            cosmos_db.prompts_container.query_items(
                query=query["query"],
                parameters=query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        if not subcategories:
            raise HTTPException(
                status_code=404,
                detail=f"Subcategory with id '{subcategory_id}' not found",
            )

        # Ensure proper talking points structure
        subcategory = talking_points_service.ensure_talking_points_structure(subcategories[0])
        
        return subcategory

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving subcategory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve subcategory: {str(e)}",
        )


@router.put("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
async def update_subcategory(
    subcategory_id: str,
    subcategory: SubcategoryUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update a prompt subcategory"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        # Check if subcategory exists
        query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.id = @id",
            "parameters": [{"name": "@id", "value": subcategory_id}],
        }

        subcategories = list(
            cosmos_db.prompts_container.query_items(
                query=query["query"],
                parameters=query["parameters"],
                enable_cross_partition_query=True,
            )
        )

        if not subcategories:
            raise HTTPException(
                status_code=404,
                detail=f"Subcategory with id '{subcategory_id}' not found",
            )

        # Validate and convert talking points using the service
        try:
            # Convert Pydantic models to dict format for validation
            pre_session_dict = [section.dict() for section in subcategory.preSessionTalkingPoints]
            in_session_dict = [section.dict() for section in subcategory.inSessionTalkingPoints]
            
            validated_pre_session = talking_points_service.validate_talking_points_structure(pre_session_dict)
            validated_in_session = talking_points_service.validate_talking_points_structure(in_session_dict)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid talking points structure: {str(e)}"
            )

        subcategory_data = subcategories[0]
        subcategory_data["name"] = subcategory.name
        subcategory_data["prompts"] = subcategory.prompts
        subcategory_data["preSessionTalkingPoints"] = validated_pre_session
        subcategory_data["inSessionTalkingPoints"] = validated_in_session
        subcategory_data["updated_at"] = int(
            datetime.now(timezone.utc).timestamp() * 1000
        )

        updated_subcategory = cosmos_db.prompts_container.upsert_item(
            body=subcategory_data
        )
        
        # Ensure proper format for response
        updated_subcategory = talking_points_service.ensure_talking_points_structure(updated_subcategory)
        
        return updated_subcategory

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subcategory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update subcategory: {str(e)}",
        )


@router.delete("/subcategories/{subcategory_id}")
async def delete_subcategory(
    subcategory_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a prompt subcategory"""
    try:
        config = AppConfig()
        cosmos_db = get_cosmos_db(config)

        try:
            cosmos_db.prompts_container.delete_item(
                item=subcategory_id,
                partition_key=subcategory_id,
            )
        except Exception as e:
            if "404" in str(e):
                raise HTTPException(
                    status_code=404,
                    detail=f"Subcategory with id '{subcategory_id}' not found",
                )
            raise

        return {
            "status": 200,
            "message": f"Subcategory '{subcategory_id}' deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting subcategory: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete subcategory: {str(e)}",
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
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieve all prompts, categories, and subcategories in a hierarchical structure"""
    try:
        config = AppConfig()
        try:
            cosmos_db = get_cosmos_db(config)
            logger.debug("CosmosDB client initialized for retrieval")
        except DatabaseError as e:
            logger.error(f"Database initialization failed: {str(e)}")
            return {"status": 503, "message": "Database service unavailable"}

        # Query all categories
        categories_query = "SELECT * FROM c WHERE c.type = 'prompt_category'"
        categories = list(
            cosmos_db.prompts_container.query_items(
                query=categories_query, enable_cross_partition_query=True
            )
        )

        # Query all subcategories
        subcategories_query = "SELECT * FROM c WHERE c.type = 'prompt_subcategory'"
        subcategories = list(
            cosmos_db.prompts_container.query_items(
                query=subcategories_query, enable_cross_partition_query=True
            )
        )

        # Organize data
        results = []
        for category in categories:
            category_data = {
                "category_name": category["name"],
                "category_id": category["id"],
                "subcategories": [],
            }
            for subcategory in subcategories:
                if subcategory["category_id"] == category["id"]:
                    category_data["subcategories"].append(
                        {
                            "subcategory_name": subcategory["name"],
                            "subcategory_id": subcategory["id"],
                            "prompts": subcategory["prompts"],
                            "preSessionTalkingPoints": subcategory.get("preSessionTalkingPoints", []),
                            "inSessionTalkingPoints": subcategory.get("inSessionTalkingPoints", []),
                        }
                    )
            results.append(category_data)

        return {"status": 200, "data": results}

    except Exception as e:
        logger.error(f"Error retrieving prompts: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve prompts: {str(e)}",
        )
