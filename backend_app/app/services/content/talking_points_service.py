"""
Talking Points Service

Handles validation, conversion, and migration of talking points data
for the prompt management system.
"""

import logging
from typing import Dict, Any, List, Union, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime

logger = logging.getLogger(__name__)


class TalkingPointField(BaseModel):
    """Individual field within a talking point section"""
    name: str = Field(..., description="Field name/identifier", min_length=1)
    type: str = Field(..., description="Field type: text, date, markdown, checkbox, number, select")
    value: Union[str, bool, float, None] = Field(None, description="Field value")
    label: Optional[str] = Field(None, description="Display label for the field")
    placeholder: Optional[str] = Field(None, description="Placeholder text for input fields")
    description: Optional[str] = Field(None, description="Help text describing the field")
    required: Optional[bool] = Field(False, description="Whether the field is required")
    options: Optional[str] = Field(None, description="Comma-separated options for select fields")

    class Config:
        # Allow extra fields for future extensibility
        extra = "forbid"


class TalkingPointSection(BaseModel):
    """A section containing multiple fields"""
    fields: List[TalkingPointField] = Field(
        default_factory=list, 
        description="List of fields in this section"
    )

    class Config:
        extra = "forbid"


class TalkingPointsData(BaseModel):
    """Container for both pre-session and in-session talking points"""
    preSessionTalkingPoints: List[TalkingPointSection] = Field(default_factory=list)
    inSessionTalkingPoints: List[TalkingPointSection] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class TalkingPointsService:
    """Service for handling talking points operations"""
    
    VALID_FIELD_TYPES = {"text", "date", "markdown", "checkbox", "number", "select"}
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_field_type(self, field_type: str) -> bool:
        """Validate if field type is supported"""
        return field_type in self.VALID_FIELD_TYPES
    
    def validate_field_value(self, field_type: str, value: Any) -> Any:
        """Validate and convert field value based on type"""
        if value is None:
            return None
            
        try:
            if field_type == "checkbox":
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                else:
                    return bool(value)
                    
            elif field_type == "date":
                if isinstance(value, str):
                    # Basic date format validation could be added here
                    return value.strip()
                return str(value)
                
            elif field_type == "number":
                try:
                    if isinstance(value, (int, float)):
                        return value
                    elif isinstance(value, str) and value.strip():
                        # Try to convert to int first, then float
                        if '.' in value:
                            return float(value)
                        else:
                            return int(value)
                    else:
                        return 0
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid number value: {value}")
                    return 0
                    
            elif field_type == "select":
                # For select fields, just ensure it's a string
                return str(value).strip() if value else ""
                
            elif field_type in ("text", "markdown"):
                return str(value).strip() if value else ""
                
            else:
                # Fallback to string conversion
                return str(value)
                
        except Exception as e:
            self.logger.warning(f"Error validating field value for type {field_type}: {e}")
            return str(value) if value is not None else ""
    
    def validate_talking_points_structure(
        self, 
        talking_points: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and convert talking points to database format
        
        Args:
            talking_points: List of talking point sections from frontend
            
        Returns:
            List of validated talking point sections
            
        Raises:
            ValueError: If validation fails
        """
        validated_points = []
        
        try:
            for section_idx, section in enumerate(talking_points):
                if not isinstance(section, dict):
                    raise ValueError(f"Section {section_idx} must be a dictionary")
                
                fields = section.get("fields", [])
                if not isinstance(fields, list):
                    raise ValueError(f"Section {section_idx} fields must be a list")
                
                validated_fields = []
                
                for field_idx, field in enumerate(fields):
                    if not isinstance(field, dict):
                        raise ValueError(
                            f"Section {section_idx}, field {field_idx} must be a dictionary"
                        )
                    
                    # Extract field data
                    field_name = field.get("name", "").strip()
                    field_type = field.get("type", "text").strip().lower()
                    field_value = field.get("value")
                    field_label = field.get("label", "")
                    field_placeholder = field.get("placeholder", "")
                    field_description = field.get("description", "")
                    field_required = field.get("required", False)
                    field_options = field.get("options", "")
                    
                    # Validate field name
                    if not field_name:
                        self.logger.warning(
                            f"Empty field name in section {section_idx}, field {field_idx}"
                        )
                        continue  # Skip empty field names
                    
                    # Validate field type
                    if not self.validate_field_type(field_type):
                        raise ValueError(
                            f"Invalid field type '{field_type}' in section {section_idx}, "
                            f"field {field_idx}. Must be one of: {', '.join(self.VALID_FIELD_TYPES)}"
                        )
                    
                    # Validate and convert field value
                    validated_value = self.validate_field_value(field_type, field_value)
                    
                    validated_fields.append({
                        "name": field_name,
                        "type": field_type,
                        "value": validated_value,
                        "label": field_label,
                        "placeholder": field_placeholder,
                        "description": field_description,
                        "required": bool(field_required),
                        "options": field_options
                    })
                
                # Only add sections with valid fields
                if validated_fields:
                    validated_points.append({
                        "fields": validated_fields
                    })
        
        except Exception as e:
            self.logger.error(f"Error validating talking points structure: {e}")
            raise ValueError(f"Invalid talking points structure: {e}")
        
        return validated_points
    
    def convert_talking_points_to_response(
        self, 
        talking_points_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert database talking points to response format
        
        Args:
            talking_points_data: Talking points from database
            
        Returns:
            Formatted talking points for frontend
        """
        try:
            sections = []
            
            for section_data in talking_points_data:
                if not isinstance(section_data, dict):
                    continue
                
                fields = []
                for field_data in section_data.get("fields", []):
                    if not isinstance(field_data, dict):
                        continue
                    
                    field = {
                        "name": field_data.get("name", ""),
                        "type": field_data.get("type", "text"),
                        "value": field_data.get("value"),
                        "label": field_data.get("label", ""),
                        "placeholder": field_data.get("placeholder", ""),
                        "description": field_data.get("description", ""),
                        "required": field_data.get("required", False),
                        "options": field_data.get("options", "")
                    }
                    
                    # Ensure value is properly typed
                    if field["type"] == "checkbox" and field["value"] is not None:
                        field["value"] = bool(field["value"])
                    
                    fields.append(field)
                
                if fields:  # Only add sections with fields
                    sections.append({"fields": fields})
            
            return sections
            
        except Exception as e:
            self.logger.error(f"Error converting talking points to response: {e}")
            return []
    
    def migrate_legacy_talking_points(
        self, 
        legacy_points: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Migrate legacy talking points format to new structured format
        
        Args:
            legacy_points: List of strings or mixed format (old format)
            
        Returns:
            List of TalkingPointSection objects (new format)
        """
        migrated_points = []
        
        try:
            for i, point in enumerate(legacy_points):
                if isinstance(point, str) and point.strip():
                    # Legacy format: simple string
                    migrated_points.append({
                        "fields": [
                            {
                                "name": f"Point {i + 1}",
                                "type": "text",
                                "value": point.strip(),
                                "label": f"Point {i + 1}",
                                "placeholder": "",
                                "description": "",
                                "required": False,
                                "options": ""
                            }
                        ]
                    })
                elif isinstance(point, dict) and "fields" in point:
                    # Already in new format - ensure all fields have the new properties
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
                    if migrated_fields:
                        migrated_points.append({"fields": migrated_fields})
                elif point:  # Non-empty, unknown format
                    # Convert to string
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
        
        except Exception as e:
            self.logger.error(f"Error migrating legacy talking points: {e}")
            # Return empty list on error to avoid breaking the system
            return []
        
        return migrated_points
    
    def ensure_talking_points_structure(
        self, 
        subcategory_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ensure talking points are in the correct format, migrating if necessary
        
        Args:
            subcategory_data: Subcategory data from database
            
        Returns:
            Subcategory data with properly formatted talking points
        """
        try:
            # Handle pre-session talking points
            pre_session = subcategory_data.get("preSessionTalkingPoints", [])
            if pre_session:
                # Check if we need migration (first item is string = legacy format)
                if isinstance(pre_session[0], str):
                    self.logger.info("Migrating legacy pre-session talking points")
                    subcategory_data["preSessionTalkingPoints"] = self.migrate_legacy_talking_points(pre_session)
                else:
                    # Ensure proper format
                    subcategory_data["preSessionTalkingPoints"] = self.convert_talking_points_to_response(pre_session)
            
            # Handle in-session talking points
            in_session = subcategory_data.get("inSessionTalkingPoints", [])
            if in_session:
                # Check if we need migration (first item is string = legacy format)
                if isinstance(in_session[0], str):
                    self.logger.info("Migrating legacy in-session talking points")
                    subcategory_data["inSessionTalkingPoints"] = self.migrate_legacy_talking_points(in_session)
                else:
                    # Ensure proper format
                    subcategory_data["inSessionTalkingPoints"] = self.convert_talking_points_to_response(in_session)
        
        except Exception as e:
            self.logger.error(f"Error ensuring talking points structure: {e}")
            # Set to empty lists on error to prevent breaking the response
            subcategory_data["preSessionTalkingPoints"] = []
            subcategory_data["inSessionTalkingPoints"] = []
        
        return subcategory_data
    
    def validate_pydantic_models(
        self, 
        talking_points: List[Dict[str, Any]]
    ) -> List[TalkingPointSection]:
        """
        Validate talking points using Pydantic models
        
        Args:
            talking_points: Raw talking points data
            
        Returns:
            List of validated TalkingPointSection objects
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            sections = []
            for section_data in talking_points:
                section = TalkingPointSection(**section_data)
                sections.append(section)
            return sections
        except ValidationError as e:
            self.logger.error(f"Pydantic validation error: {e}")
            raise
    
    def get_field_type_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about supported field types
        
        Returns:
            Dictionary with field type information
        """
        return {
            "text": {
                "description": "Single-line text input",
                "value_type": "string",
                "validation": "String, max 1000 characters",
                "form_builder": True
            },
            "date": {
                "description": "Date input field",
                "value_type": "string",
                "validation": "Date string in YYYY-MM-DD format",
                "form_builder": True
            },
            "markdown": {
                "description": "Multi-line markdown text",
                "value_type": "string",
                "validation": "Markdown formatted text, max 5000 characters",
                "form_builder": True
            },
            "checkbox": {
                "description": "Boolean checkbox",
                "value_type": "boolean",
                "validation": "True or false value",
                "form_builder": True
            },
            "number": {
                "description": "Numeric input field",
                "value_type": "number",
                "validation": "Integer or decimal number",
                "form_builder": True
            },
            "select": {
                "description": "Dropdown selection",
                "value_type": "string",
                "validation": "Selected option from predefined list",
                "form_builder": True
            }
        }


# Global service instance
talking_points_service = TalkingPointsService()
