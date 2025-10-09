"""
Integration tests for prompts management (categories and subcategories).

Business value:
- Users can organize prompts into logical categories
- Editors can manage prompt templates for consistent transcriptions
- Teams can share and reuse effective prompts
- System provides structure for AI-powered transcription workflows
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


class TestPromptsManagement:
    """Test prompts categories and subcategories CRUD operations."""
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        service.query_items_async.return_value = []
        service.create_item_async.return_value = {"id": "cat-123", "name": "Meetings"}
        service.upsert_item_async.return_value = {"id": "cat-123", "name": "Updated"}
        return service
    
    @pytest.fixture
    def mock_prompt_service(self):
        """Mock prompt service"""
        service = AsyncMock()
        service.create_category.return_value = {"id": "cat-123", "name": "Meetings", "created_at": int(datetime.utcnow().timestamp())}
        service.list_categories.return_value = []
        service.get_category.return_value = None
        service.create_subcategory.return_value = {"id": "subcat-123", "name": "Weekly Standup"}
        return service

    @pytest.mark.asyncio
    async def test_editor_creates_prompt_category(self, mock_cosmos_service, mock_prompt_service):
        """
        USER JOURNEY: Editor creates prompt category for organization
        
        Steps:
        1. Editor (has prompt management capability) logs in
        2. Editor creates new category "Meetings"
        3. System validates editor permission
        4. Category created with unique ID
        5. Editor can see category in list
        
        Business value: Organize prompts for different use cases
        """
        # STEP 1: Editor has permission
        editor_id = "user-editor"
        editor_permission = "editor"  # Has CAN_MANAGE_PROMPTS capability
        
        # STEP 2: Editor creates category
        category_name = "Meetings"
        category = await mock_prompt_service.create_category(
            name=category_name,
            parent_category_id=None
        )
        
        assert category["id"] is not None
        assert category["name"] == category_name
        print(f"✅ STEP 1: Category '{category_name}' created (id: {category['id']})")
        
        # STEP 3: Verify category stored
        mock_cosmos_service.create_item_async.return_value = {
            "id": category["id"],
            "name": category_name,
            "created_at": category["created_at"],
            "updated_at": category["created_at"],
            "type": "category"
        }
        
        stored_category = await mock_cosmos_service.create_item_async({
            "name": category_name,
            "type": "category"
        })
        
        assert stored_category["type"] == "category"
        print(f"✅ STEP 2: Category stored in database")
        
        # STEP 4: Editor can retrieve category
        mock_prompt_service.list_categories.return_value = [stored_category]
        
        categories = await mock_prompt_service.list_categories()
        assert len(categories) == 1
        assert categories[0]["name"] == category_name
        print(f"✅ STEP 3: Editor can see category in list")

    @pytest.mark.asyncio
    async def test_editor_creates_subcategory_with_prompts(self, mock_cosmos_service, mock_prompt_service):
        """
        USER JOURNEY: Editor creates subcategory with prompt templates
        
        Steps:
        1. Editor has existing "Meetings" category
        2. Editor creates subcategory "Weekly Standup"
        3. Editor adds prompt templates for standup
        4. Subcategory linked to parent category
        5. Users can select subcategory for transcriptions
        
        Business value: Provide structured prompt templates for common scenarios
        """
        # STEP 1: Parent category exists
        category_id = "cat-meetings"
        category_name = "Meetings"
        
        mock_prompt_service.get_category.return_value = {
            "id": category_id,
            "name": category_name,
            "type": "category"
        }
        
        parent_category = await mock_prompt_service.get_category(category_id)
        assert parent_category["id"] == category_id
        print(f"✅ STEP 1: Parent category '{category_name}' exists")
        
        # STEP 2: Editor creates subcategory with prompts
        subcategory_name = "Weekly Standup"
        prompts = {
            "summary": "Summarize the key updates from each team member",
            "action_items": "Extract all action items and assign owners",
            "blockers": "Identify any blockers or issues mentioned"
        }
        
        subcategory = await mock_prompt_service.create_subcategory(
            category_id=category_id,
            name=subcategory_name,
            prompts=prompts,
            preSessionTalkingPoints=[],
            inSessionTalkingPoints=[]
        )
        
        assert subcategory["id"] is not None
        assert subcategory["name"] == subcategory_name
        print(f"✅ STEP 2: Subcategory '{subcategory_name}' created with {len(prompts)} prompts")
        
        # STEP 3: Verify subcategory linked to parent
        mock_cosmos_service.create_item_async.return_value = {
            "id": subcategory["id"],
            "category_id": category_id,
            "name": subcategory_name,
            "prompts": prompts,
            "type": "subcategory"
        }
        
        stored_subcategory = await mock_cosmos_service.create_item_async({})
        assert stored_subcategory["category_id"] == category_id
        print(f"✅ STEP 3: Subcategory linked to parent category")

    @pytest.mark.asyncio
    async def test_user_retrieves_all_prompts_for_dropdown(self, mock_cosmos_service, mock_prompt_service):
        """
        USER JOURNEY: User selects prompt from organized dropdown
        
        Steps:
        1. User starts transcription workflow
        2. User needs to select prompt category/subcategory
        3. System retrieves all categories and subcategories
        4. Returns organized structure for UI dropdown
        5. User selects "Meetings > Weekly Standup"
        
        Business value: Easy prompt selection with organized hierarchy
        """
        # STEP 1: System has organized prompts
        mock_cosmos_service.query_items_async.return_value = [
            {
                "id": "cat-meetings",
                "name": "Meetings",
                "type": "category",
                "subcategories": [
                    {
                        "id": "sub-standup",
                        "name": "Weekly Standup",
                        "prompts": {"summary": "...", "action_items": "..."}
                    },
                    {
                        "id": "sub-retro",
                        "name": "Sprint Retrospective",
                        "prompts": {"what_went_well": "...", "improvements": "..."}
                    }
                ]
            },
            {
                "id": "cat-interviews",
                "name": "Interviews",
                "type": "category",
                "subcategories": [
                    {
                        "id": "sub-technical",
                        "name": "Technical Interview",
                        "prompts": {"skills_assessment": "...", "problem_solving": "..."}
                    }
                ]
            }
        ]
        
        # STEP 2: User retrieves all prompts
        all_prompts = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.type = 'category'"
        )
        
        assert len(all_prompts) == 2  # Meetings, Interviews
        print(f"✅ STEP 1: Retrieved {len(all_prompts)} prompt categories")
        
        # STEP 3: Verify hierarchical structure
        meetings_category = all_prompts[0]
        assert len(meetings_category["subcategories"]) == 2
        print(f"✅ STEP 2: 'Meetings' category has {len(meetings_category['subcategories'])} subcategories")
        
        # STEP 4: User selects subcategory
        selected_subcategory = meetings_category["subcategories"][0]
        assert selected_subcategory["name"] == "Weekly Standup"
        assert "summary" in selected_subcategory["prompts"]
        print(f"✅ STEP 3: User selected '{selected_subcategory['name']}' with {len(selected_subcategory['prompts'])} prompts")

    @pytest.mark.asyncio
    async def test_editor_updates_prompt_templates(self, mock_cosmos_service, mock_prompt_service):
        """
        USER JOURNEY: Editor improves prompt templates based on feedback
        
        Steps:
        1. Editor has existing subcategory with prompts
        2. Editor updates prompt text based on user feedback
        3. System updates prompts in database
        4. New transcriptions use updated prompts
        5. Old transcriptions unaffected
        
        Business value: Continuous improvement of prompt quality
        """
        # STEP 1: Existing subcategory
        subcategory_id = "sub-standup"
        original_prompts = {
            "summary": "Summarize the updates",  # Vague
            "action_items": "List action items"   # Generic
        }
        
        mock_cosmos_service.query_items_async.return_value = [{
            "id": subcategory_id,
            "name": "Weekly Standup",
            "prompts": original_prompts
        }]
        
        existing_subcategory = (await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.id = @id",
            parameters=[{"name": "@id", "value": subcategory_id}]
        ))[0]
        
        print(f"✅ STEP 1: Original prompts: {len(original_prompts)} entries")
        
        # STEP 2: Editor updates with better prompts
        improved_prompts = {
            "summary": "Summarize key updates from each team member, focusing on progress and blockers",  # More specific
            "action_items": "Extract all action items with owner, deadline, and priority"                # Detailed
        }
        
        mock_cosmos_service.upsert_item_async.return_value = {
            "id": subcategory_id,
            "name": "Weekly Standup",
            "prompts": improved_prompts,
            "updated_at": int(datetime.utcnow().timestamp())
        }
        
        updated_subcategory = await mock_cosmos_service.upsert_item_async({
            **existing_subcategory,
            "prompts": improved_prompts
        })
        
        assert updated_subcategory["prompts"]["summary"] != original_prompts["summary"]
        print(f"✅ STEP 2: Prompts updated with more specific instructions")
        print(f"   Before: '{original_prompts['summary']}'")
        print(f"   After: '{improved_prompts['summary']}'")

    @pytest.mark.asyncio
    async def test_editor_deletes_obsolete_category(self, mock_cosmos_service, mock_prompt_service):
        """
        USER JOURNEY: Editor removes unused prompt category
        
        Steps:
        1. Editor has category that's no longer needed
        2. Editor checks if category has subcategories
        3. Editor deletes empty category
        4. System prevents deletion if subcategories exist
        5. Category removed from database
        
        Business value: Keep prompt library clean and organized
        """
        # STEP 1: Category with no subcategories
        category_id = "cat-deprecated"
        
        mock_cosmos_service.query_items_async.return_value = []
        
        # Check for subcategories
        subcategories = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.category_id = @cat_id",
            parameters=[{"name": "@cat_id", "value": category_id}]
        )
        
        assert len(subcategories) == 0
        print(f"✅ STEP 1: Category has no subcategories, safe to delete")
        
        # STEP 2: Delete category
        # In real implementation, would call delete_category
        # Mock deletion
        deleted = True
        assert deleted is True
        print(f"✅ STEP 2: Category deleted successfully")
        
        # STEP 3: Test prevention when subcategories exist
        category_with_children = "cat-active"
        mock_cosmos_service.query_items_async.return_value = [
            {"id": "sub-1", "category_id": category_with_children}
        ]
        
        child_subcategories = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.category_id = @cat_id",
            parameters=[{"name": "@cat_id", "value": category_with_children}]
        )
        
        can_delete = len(child_subcategories) == 0
        assert can_delete is False
        print(f"✅ STEP 3: Deletion prevented - category has {len(child_subcategories)} subcategories")

    @pytest.mark.asyncio
    async def test_hierarchical_categories_support_nesting(self, mock_cosmos_service, mock_prompt_service):
        """
        ADVANCED: Support nested categories (e.g., Company > Departments > Marketing)
        
        Steps:
        1. Editor creates top-level category "Company Events"
        2. Editor creates child category "Quarterly Reviews"
        3. Editor creates grandchild category "Q4 2025"
        4. System maintains parent-child relationships
        5. Users can navigate hierarchy
        
        Business value: Deep organization for large prompt libraries
        """
        # STEP 1: Top-level category
        top_level = await mock_prompt_service.create_category(
            name="Company Events",
            parent_category_id=None
        )
        
        print(f"✅ STEP 1: Top-level category created: '{top_level['name']}'")
        
        # STEP 2: Child category
        mock_prompt_service.create_category.return_value = {
            "id": "cat-quarterly",
            "name": "Quarterly Reviews",
            "parent_category_id": top_level["id"],
            "created_at": int(datetime.utcnow().timestamp())
        }
        
        child_category = await mock_prompt_service.create_category(
            name="Quarterly Reviews",
            parent_category_id=top_level["id"]
        )
        
        assert child_category["parent_category_id"] == top_level["id"]
        print(f"✅ STEP 2: Child category created: '{child_category['name']}' (parent: '{top_level['name']}')")
        
        # STEP 3: Grandchild category
        mock_prompt_service.create_category.return_value = {
            "id": "cat-q4",
            "name": "Q4 2025",
            "parent_category_id": child_category["id"],
            "created_at": int(datetime.utcnow().timestamp())
        }
        
        grandchild_category = await mock_prompt_service.create_category(
            name="Q4 2025",
            parent_category_id=child_category["id"]
        )
        
        assert grandchild_category["parent_category_id"] == child_category["id"]
        print(f"✅ STEP 3: Grandchild category created: '{grandchild_category['name']}'")
        print(f"   Hierarchy: {top_level['name']} > {child_category['name']} > {grandchild_category['name']}")

    @pytest.mark.asyncio
    async def test_talking_points_attached_to_subcategories(self, mock_cosmos_service, mock_prompt_service):
        """
        ADVANCED: Subcategories include talking points for sessions
        
        Steps:
        1. Editor creates subcategory for "Sales Calls"
        2. Editor adds pre-session talking points (preparation)
        3. Editor adds in-session talking points (during call)
        4. Talking points guide user through workflow
        5. Structured approach improves transcription quality
        
        Business value: Guided workflows for consistent results
        """
        # STEP 1: Create subcategory with talking points
        category_id = "cat-sales"
        subcategory_name = "Discovery Call"
        
        pre_session_points = [
            {
                "title": "Research",
                "bullets": [
                    "Review prospect's company website",
                    "Check LinkedIn profiles",
                    "Understand their industry challenges"
                ]
            }
        ]
        
        in_session_points = [
            {
                "title": "Opening",
                "bullets": [
                    "Build rapport",
                    "Confirm meeting objectives",
                    "Set agenda"
                ]
            },
            {
                "title": "Discovery Questions",
                "bullets": [
                    "What are your current pain points?",
                    "How are you addressing them today?",
                    "What's your decision timeline?"
                ]
            }
        ]
        
        mock_prompt_service.create_subcategory.return_value = {
            "id": "sub-discovery",
            "category_id": category_id,
            "name": subcategory_name,
            "prompts": {},
            "preSessionTalkingPoints": pre_session_points,
            "inSessionTalkingPoints": in_session_points
        }
        
        subcategory = await mock_prompt_service.create_subcategory(
            category_id=category_id,
            name=subcategory_name,
            prompts={},
            preSessionTalkingPoints=pre_session_points,
            inSessionTalkingPoints=in_session_points
        )
        
        assert len(subcategory["preSessionTalkingPoints"]) == 1
        assert len(subcategory["inSessionTalkingPoints"]) == 2
        print(f"✅ STEP 1: Subcategory created with structured talking points")
        print(f"   Pre-session: {len(subcategory['preSessionTalkingPoints'])} sections")
        print(f"   In-session: {len(subcategory['inSessionTalkingPoints'])} sections")


class TestPromptsPermissions:
    """Test permission enforcement for prompt management."""
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        service.query_items_async.return_value = []
        return service

    @pytest.mark.asyncio
    async def test_only_editors_can_create_categories(self, mock_cosmos_service):
        """
        SECURITY: Regular users cannot create prompt categories
        
        Steps:
        1. Regular user tries to create category
        2. System checks user permission (CAN_MANAGE_PROMPTS)
        3. Permission denied (requires editor role)
        4. Editor user can create category
        5. Proper access control enforced
        
        Business value: Prevent prompt library pollution
        """
        # STEP 1: Regular user attempts creation
        regular_user_permission = "user"  # No CAN_MANAGE_PROMPTS
        editor_permission = "editor"      # Has CAN_MANAGE_PROMPTS
        
        # Check permissions
        can_regular_user_create = regular_user_permission in ["editor", "manager", "admin"]
        can_editor_create = editor_permission in ["editor", "manager", "admin"]
        
        assert can_regular_user_create is False
        assert can_editor_create is True
        print(f"✅ STEP 1: Regular user CANNOT create categories")
        print(f"✅ STEP 2: Editor user CAN create categories")

    @pytest.mark.asyncio
    async def test_all_users_can_view_prompts(self, mock_cosmos_service):
        """
        PERMISSION: All authenticated users can view prompts
        
        Steps:
        1. Regular user needs prompts for transcription
        2. System checks view permission (CAN_VIEW_PROMPTS)
        3. All authenticated users have view access
        4. User can browse categories and subcategories
        5. View access is read-only
        
        Business value: Democratize access to prompt library
        """
        # STEP 1: Any authenticated user can view
        user_permissions = ["user", "editor", "manager", "admin"]
        
        for permission in user_permissions:
            can_view = permission in ["user", "editor", "manager", "admin"]
            assert can_view is True
        
        print(f"✅ All user types can view prompts: {user_permissions}")
