"""
Unit tests for PromptService (Phase 2 - Integration & Service Layer)

Tests cover:
- Category CRUD operations (create, list, get, update, delete)
- Subcategory CRUD operations
- Hierarchy retrieval
- Async method wrappers
- Error handling and edge cases
- Timestamp generation and parent category relationships

Coverage target: 90%+ on app/services/prompts/prompt_service.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from app.services.prompts.prompt_service import PromptService
from app.core.dependencies import CosmosService


# ============================================================================
# Test Class: Category Operations
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestCategoryOperations:
    """Test category CRUD operations"""
    
    def test_create_category_success(self, mock_cosmos_service, mock_prompt_container):
        """Test successful category creation"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            result = service.create_category(name="Business Strategy")
        
        # Assert
        assert result is not None
        assert result["name"] == "Business Strategy"
        assert result["type"] == "prompt_category"
        assert "id" in result
        assert result["id"].startswith("category_")
        assert result["parent_category_id"] is None
        mock_prompt_container.create_item.assert_called_once()
    
    def test_create_category_with_parent(self, mock_cosmos_service, mock_prompt_container):
        """Test category creation with parent relationship"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        parent_id = "category_parent_123"
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            result = service.create_category(
                name="Sub-strategy",
                parent_category_id=parent_id
            )
        
        # Assert
        assert result["parent_category_id"] == parent_id
        assert result["name"] == "Sub-strategy"
    
    def test_create_category_generates_timestamp(self, mock_cosmos_service, mock_prompt_container):
        """Test that category creation generates created_at and updated_at timestamps"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        expected_timestamp = 1234567890123  # milliseconds
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            result = service.create_category(name="Test")
        
        # Assert
        assert result["created_at"] == expected_timestamp
        assert result["updated_at"] == expected_timestamp
    
    def test_list_categories_success(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test listing all categories"""
        # Arrange
        categories = [
            category_factory(name="Category 1"),
            category_factory(name="Category 2"),
        ]
        mock_prompt_container.query_items = Mock(return_value=categories)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.list_categories()
        
        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "Category 1"
        assert result[1]["name"] == "Category 2"
        # Verify query
        mock_prompt_container.query_items.assert_called_once()
        call_kwargs = mock_prompt_container.query_items.call_args[1]
        assert "prompt_category" in call_kwargs["query"]
    
    def test_list_categories_empty(self, mock_cosmos_service, mock_prompt_container):
        """Test listing categories when none exist"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.list_categories()
        
        # Assert
        assert result == []
    
    def test_get_category_success(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test retrieving a specific category by ID"""
        # Arrange
        category = category_factory(category_id="cat_123", name="Found Category")
        mock_prompt_container.query_items = Mock(return_value=[category])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.get_category("cat_123")
        
        # Assert
        assert result is not None
        assert result["id"] == "cat_123"
        assert result["name"] == "Found Category"
        # Verify parameterized query
        call_args = mock_prompt_container.query_items.call_args
        assert call_args[1]["parameters"][0]["value"] == "cat_123"
    
    def test_get_category_not_found(self, mock_cosmos_service, mock_prompt_container):
        """Test retrieving non-existent category returns None"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.get_category("nonexistent_id")
        
        # Assert
        assert result is None
    
    def test_update_category_success(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test updating an existing category"""
        # Arrange
        existing_category = category_factory(
            category_id="cat_123",
            name="Old Name",
            parent_category_id=None
        )
        mock_prompt_container.query_items = Mock(return_value=[existing_category])
        mock_prompt_container.upsert_item = Mock(side_effect=lambda body: body)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 9999999999.999
            result = service.update_category(
                category_id="cat_123",
                name="New Name",
                parent_category_id="parent_456"
            )
        
        # Assert
        assert result is not None
        assert result["name"] == "New Name"
        assert result["parent_category_id"] == "parent_456"
        assert result["updated_at"] == 9999999999999  # Updated timestamp
        mock_prompt_container.upsert_item.assert_called_once()
    
    def test_update_category_not_found(self, mock_cosmos_service, mock_prompt_container):
        """Test updating non-existent category returns None"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.update_category(
            category_id="nonexistent",
            name="New Name"
        )
        
        # Assert
        assert result is None
        mock_prompt_container.upsert_item.assert_not_called()
    
    def test_delete_category_and_subcategories_success(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test deleting a category and its subcategories"""
        # Arrange
        subcategories = [
            subcategory_factory(subcategory_id="sub_1", category_id="cat_123"),
            subcategory_factory(subcategory_id="sub_2", category_id="cat_123"),
        ]
        mock_prompt_container.query_items = Mock(return_value=subcategories)
        mock_prompt_container.delete_item = Mock(return_value=None)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        service.delete_category_and_subcategories("cat_123")
        
        # Assert
        # Should delete 2 subcategories + 1 category = 3 delete calls
        assert mock_prompt_container.delete_item.call_count == 3
        # Verify subcategories deleted first
        calls = mock_prompt_container.delete_item.call_args_list
        assert calls[0][1]["item"] == "sub_1"
        assert calls[1][1]["item"] == "sub_2"
        assert calls[2][1]["item"] == "cat_123"
    
    def test_delete_category_without_subcategories(self, mock_cosmos_service, mock_prompt_container):
        """Test deleting a category with no subcategories"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_prompt_container.delete_item = Mock(return_value=None)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        service.delete_category_and_subcategories("cat_123")
        
        # Assert
        # Should only delete the category itself
        assert mock_prompt_container.delete_item.call_count == 1
        mock_prompt_container.delete_item.assert_called_with(
            item="cat_123",
            partition_key="cat_123"
        )


# ============================================================================
# Test Class: Subcategory Operations
# ============================================================================

@pytest.mark.unit
@pytest.mark.critical
class TestSubcategoryOperations:
    """Test subcategory CRUD operations"""
    
    def test_create_subcategory_success(self, mock_cosmos_service, mock_prompt_container):
        """Test successful subcategory creation"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        prompts = {"greeting": "Hello!", "question": "How are you?"}
        pre_session = [{"field": "notes"}]
        in_session = [{"field": "actions"}]
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            with patch('app.services.prompts.prompt_service.uuid') as mock_uuid:
                mock_uuid.uuid4.return_value.hex = "abc123def456"
                result = service.create_subcategory(
                    category_id="cat_123",
                    name="Sales Meeting",
                    prompts=prompts,
                    pre=pre_session,
                    in_session=in_session
                )
        
        # Assert
        assert result is not None
        assert result["name"] == "Sales Meeting"
        assert result["type"] == "prompt_subcategory"
        assert result["category_id"] == "cat_123"
        assert result["prompts"] == prompts
        assert result["preSessionTalkingPoints"] == pre_session
        assert result["inSessionTalkingPoints"] == in_session
        assert "subcategory_" in result["id"]
        assert "abc123def456" in result["id"]
        mock_prompt_container.create_item.assert_called_once()
    
    def test_create_subcategory_with_empty_data(self, mock_cosmos_service, mock_prompt_container):
        """Test subcategory creation with empty/None data"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            result = service.create_subcategory(
                category_id="cat_123",
                name="Empty Sub",
                prompts=None,
                pre=None,
                in_session=None
            )
        
        # Assert
        assert result["prompts"] == {}
        assert result["preSessionTalkingPoints"] == []
        assert result["inSessionTalkingPoints"] == []
    
    def test_list_subcategories_all(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test listing all subcategories (no category filter)"""
        # Arrange
        subcategories = [
            subcategory_factory(name="Sub 1", category_id="cat_1"),
            subcategory_factory(name="Sub 2", category_id="cat_2"),
        ]
        mock_prompt_container.query_items = Mock(return_value=subcategories)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.list_subcategories()
        
        # Assert
        assert len(result) == 2
        # Verify query doesn't filter by category
        call_kwargs = mock_prompt_container.query_items.call_args[1]
        assert "category_id" not in call_kwargs["query"]
    
    def test_list_subcategories_by_category(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test listing subcategories filtered by category"""
        # Arrange
        subcategories = [
            subcategory_factory(name="Sub 1", category_id="cat_123"),
        ]
        mock_prompt_container.query_items = Mock(return_value=subcategories)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.list_subcategories(category_id="cat_123")
        
        # Assert
        assert len(result) == 1
        assert result[0]["category_id"] == "cat_123"
        # Verify parameterized query with category filter
        call_args = mock_prompt_container.query_items.call_args
        assert call_args[1]["parameters"][0]["value"] == "cat_123"
    
    def test_get_subcategory_success(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test retrieving a specific subcategory by ID"""
        # Arrange
        subcategory = subcategory_factory(subcategory_id="sub_123", name="Found Sub")
        mock_prompt_container.query_items = Mock(return_value=[subcategory])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.get_subcategory("sub_123")
        
        # Assert
        assert result is not None
        assert result["id"] == "sub_123"
        assert result["name"] == "Found Sub"
    
    def test_get_subcategory_not_found(self, mock_cosmos_service, mock_prompt_container):
        """Test retrieving non-existent subcategory returns None"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.get_subcategory("nonexistent_id")
        
        # Assert
        assert result is None
    
    def test_update_subcategory_success(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test updating an existing subcategory"""
        # Arrange
        existing_sub = subcategory_factory(
            subcategory_id="sub_123",
            name="Old Name",
            prompts={"old": "data"}
        )
        mock_prompt_container.query_items = Mock(return_value=[existing_sub])
        mock_prompt_container.upsert_item = Mock(side_effect=lambda body: body)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        new_prompts = {"new": "prompts"}
        new_pre = [{"field": "updated"}]
        new_in = [{"field": "in_session"}]
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 9999999999.999
            result = service.update_subcategory(
                subcategory_id="sub_123",
                name="New Name",
                prompts=new_prompts,
                pre=new_pre,
                in_session=new_in
            )
        
        # Assert
        assert result is not None
        assert result["name"] == "New Name"
        assert result["prompts"] == new_prompts
        assert result["preSessionTalkingPoints"] == new_pre
        assert result["inSessionTalkingPoints"] == new_in
        assert result["updated_at"] == 9999999999999
        mock_prompt_container.upsert_item.assert_called_once()
    
    def test_update_subcategory_not_found(self, mock_cosmos_service, mock_prompt_container):
        """Test updating non-existent subcategory returns None"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.update_subcategory(
            subcategory_id="nonexistent",
            name="New Name",
            prompts={},
            pre=[],
            in_session=[]
        )
        
        # Assert
        assert result is None
        mock_prompt_container.upsert_item.assert_not_called()
    
    def test_delete_subcategory_success(self, mock_cosmos_service, mock_prompt_container):
        """Test deleting a subcategory"""
        # Arrange
        mock_prompt_container.delete_item = Mock(return_value=None)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        service.delete_subcategory("sub_123")
        
        # Assert
        mock_prompt_container.delete_item.assert_called_once_with(
            item="sub_123",
            partition_key="sub_123"
        )


# ============================================================================
# Test Class: Hierarchy Retrieval
# ============================================================================

@pytest.mark.unit
class TestHierarchyRetrieval:
    """Test prompts hierarchy retrieval"""
    
    def test_retrieve_prompts_hierarchy_success(self, mock_cosmos_service, mock_prompt_container, category_factory, subcategory_factory):
        """Test retrieving complete prompts hierarchy"""
        # Arrange
        categories = [
            category_factory(category_id="cat_1", name="Category 1"),
            category_factory(category_id="cat_2", name="Category 2"),
        ]
        subcategories = [
            subcategory_factory(
                subcategory_id="sub_1",
                category_id="cat_1",
                name="Sub 1",
                prompts={"prompt1": "text1"},
                pre_session=[{"field": "pre"}],
                in_session=[{"field": "in"}]
            ),
            subcategory_factory(
                subcategory_id="sub_2",
                category_id="cat_1",
                name="Sub 2"
            ),
            subcategory_factory(
                subcategory_id="sub_3",
                category_id="cat_2",
                name="Sub 3"
            ),
        ]
        
        # Mock query_items to return categories first, then subcategories
        mock_prompt_container.query_items = Mock(side_effect=[categories, subcategories])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.retrieve_prompts_hierarchy()
        
        # Assert
        assert len(result) == 2
        
        # Check first category
        cat1 = next(c for c in result if c["category_id"] == "cat_1")
        assert cat1["category_name"] == "Category 1"
        assert len(cat1["subcategories"]) == 2
        
        # Check subcategory data structure
        sub1 = next(s for s in cat1["subcategories"] if s["subcategory_id"] == "sub_1")
        assert sub1["subcategory_name"] == "Sub 1"
        assert sub1["prompts"] == {"prompt1": "text1"}
        assert sub1["preSessionTalkingPoints"] == [{"field": "pre"}]
        assert sub1["inSessionTalkingPoints"] == [{"field": "in"}]
        
        # Check second category
        cat2 = next(c for c in result if c["category_id"] == "cat_2")
        assert cat2["category_name"] == "Category 2"
        assert len(cat2["subcategories"]) == 1
    
    def test_retrieve_prompts_hierarchy_empty(self, mock_cosmos_service, mock_prompt_container):
        """Test retrieving hierarchy when no data exists"""
        # Arrange
        mock_prompt_container.query_items = Mock(side_effect=[[], []])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.retrieve_prompts_hierarchy()
        
        # Assert
        assert result == []
    
    def test_retrieve_prompts_hierarchy_categories_without_subcategories(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test hierarchy with categories but no subcategories"""
        # Arrange
        categories = [category_factory(category_id="cat_1", name="Lonely Category")]
        mock_prompt_container.query_items = Mock(side_effect=[categories, []])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.retrieve_prompts_hierarchy()
        
        # Assert
        assert len(result) == 1
        assert result[0]["category_name"] == "Lonely Category"
        assert result[0]["subcategories"] == []
    
    def test_retrieve_prompts_hierarchy_with_parent_categories(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test hierarchy includes parent_category_id in response"""
        # Arrange
        categories = [
            category_factory(category_id="cat_1", name="Parent", parent_category_id=None),
            category_factory(category_id="cat_2", name="Child", parent_category_id="cat_1"),
        ]
        mock_prompt_container.query_items = Mock(side_effect=[categories, []])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = service.retrieve_prompts_hierarchy()
        
        # Assert
        parent = next(c for c in result if c["category_id"] == "cat_1")
        child = next(c for c in result if c["category_id"] == "cat_2")
        assert parent["parent_category_id"] is None
        assert child["parent_category_id"] == "cat_1"


# ============================================================================
# Test Class: Async Operations
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async method wrappers"""
    
    async def test_async_create_category(self, mock_cosmos_service, mock_prompt_container):
        """Test async category creation"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            result = await service.async_create_category(name="Async Category")
        
        # Assert
        assert result is not None
        assert result["name"] == "Async Category"
    
    async def test_async_list_categories(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test async category listing"""
        # Arrange
        categories = [category_factory(name="Cat 1")]
        mock_prompt_container.query_items = Mock(return_value=categories)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = await service.async_list_categories()
        
        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "Cat 1"
    
    async def test_async_get_category(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test async category retrieval"""
        # Arrange
        category = category_factory(category_id="cat_123")
        mock_prompt_container.query_items = Mock(return_value=[category])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = await service.async_get_category("cat_123")
        
        # Assert
        assert result is not None
        assert result["id"] == "cat_123"
    
    async def test_async_update_category(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test async category update"""
        # Arrange
        existing = category_factory(category_id="cat_123", name="Old")
        mock_prompt_container.query_items = Mock(return_value=[existing])
        mock_prompt_container.upsert_item = Mock(side_effect=lambda body: body)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 9999999999.999
            result = await service.async_update_category("cat_123", "New Name")
        
        # Assert
        assert result["name"] == "New Name"
    
    async def test_async_delete_category_and_subcategories(self, mock_cosmos_service, mock_prompt_container):
        """Test async category deletion"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_prompt_container.delete_item = Mock(return_value=None)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        await service.async_delete_category_and_subcategories("cat_123")
        
        # Assert
        mock_prompt_container.delete_item.assert_called_once()
    
    async def test_async_create_subcategory(self, mock_cosmos_service, mock_prompt_container):
        """Test async subcategory creation"""
        # Arrange
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1234567890.123
            result = await service.async_create_subcategory(
                category_id="cat_123",
                name="Async Sub",
                prompts={},
                pre=[],
                in_session=[]
            )
        
        # Assert
        assert result is not None
        assert result["name"] == "Async Sub"
    
    async def test_async_list_subcategories(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test async subcategory listing"""
        # Arrange
        subs = [subcategory_factory(name="Sub 1")]
        mock_prompt_container.query_items = Mock(return_value=subs)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = await service.async_list_subcategories()
        
        # Assert
        assert len(result) == 1
    
    async def test_async_get_subcategory(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test async subcategory retrieval"""
        # Arrange
        sub = subcategory_factory(subcategory_id="sub_123")
        mock_prompt_container.query_items = Mock(return_value=[sub])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = await service.async_get_subcategory("sub_123")
        
        # Assert
        assert result is not None
        assert result["id"] == "sub_123"
    
    async def test_async_update_subcategory(self, mock_cosmos_service, mock_prompt_container, subcategory_factory):
        """Test async subcategory update"""
        # Arrange
        existing = subcategory_factory(subcategory_id="sub_123", name="Old")
        mock_prompt_container.query_items = Mock(return_value=[existing])
        mock_prompt_container.upsert_item = Mock(side_effect=lambda body: body)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        with patch('app.services.prompts.prompt_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 9999999999.999
            result = await service.async_update_subcategory(
                subcategory_id="sub_123",
                name="New Name",
                prompts={},
                pre=[],
                in_session=[]
            )
        
        # Assert
        assert result["name"] == "New Name"
    
    async def test_async_delete_subcategory(self, mock_cosmos_service, mock_prompt_container):
        """Test async subcategory deletion"""
        # Arrange
        mock_prompt_container.delete_item = Mock(return_value=None)
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        await service.async_delete_subcategory("sub_123")
        
        # Assert
        mock_prompt_container.delete_item.assert_called_once()
    
    async def test_async_retrieve_prompts_hierarchy(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test async hierarchy retrieval"""
        # Arrange
        categories = [category_factory(name="Cat 1")]
        mock_prompt_container.query_items = Mock(side_effect=[categories, []])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act
        result = await service.async_retrieve_prompts_hierarchy()
        
        # Assert
        assert len(result) == 1
        assert result[0]["category_name"] == "Cat 1"


# ============================================================================
# Test Class: Error Handling
# ============================================================================

@pytest.mark.unit
class TestPromptServiceErrorHandling:
    """Test error handling and edge cases"""
    
    def test_create_category_cosmos_error(self, mock_cosmos_service, mock_prompt_container):
        """Test category creation when Cosmos raises error"""
        # Arrange
        mock_prompt_container.create_item = Mock(side_effect=Exception("Cosmos error"))
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act & Assert
        with pytest.raises(Exception, match="Cosmos error"):
            service.create_category(name="Test")
    
    def test_update_category_cosmos_upsert_error(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test update category when upsert fails"""
        # Arrange
        existing = category_factory(category_id="cat_123")
        mock_prompt_container.query_items = Mock(return_value=[existing])
        mock_prompt_container.upsert_item = Mock(side_effect=Exception("Upsert failed"))
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act & Assert
        with pytest.raises(Exception, match="Upsert failed"):
            service.update_category("cat_123", "New Name")
    
    def test_delete_category_cosmos_error(self, mock_cosmos_service, mock_prompt_container):
        """Test delete category when Cosmos raises error"""
        # Arrange
        mock_prompt_container.query_items = Mock(return_value=[])
        mock_prompt_container.delete_item = Mock(side_effect=Exception("Delete failed"))
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act & Assert
        with pytest.raises(Exception, match="Delete failed"):
            service.delete_category_and_subcategories("cat_123")
    
    def test_list_categories_query_error(self, mock_cosmos_service, mock_prompt_container):
        """Test list categories when query fails"""
        # Arrange
        mock_prompt_container.query_items = Mock(side_effect=Exception("Query failed"))
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act & Assert
        with pytest.raises(Exception, match="Query failed"):
            service.list_categories()
    
    def test_retrieve_hierarchy_partial_failure(self, mock_cosmos_service, mock_prompt_container, category_factory):
        """Test hierarchy retrieval when subcategory query fails"""
        # Arrange
        categories = [category_factory(name="Cat 1")]
        mock_prompt_container.query_items = Mock(side_effect=[categories, Exception("Sub query failed")])
        mock_cosmos_service.get_container = Mock(return_value=mock_prompt_container)
        service = PromptService(mock_cosmos_service)
        
        # Act & Assert
        with pytest.raises(Exception, match="Sub query failed"):
            service.retrieve_prompts_hierarchy()
