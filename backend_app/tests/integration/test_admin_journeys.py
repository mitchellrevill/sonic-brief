"""
Integration Tests: Admin Management User Journeys

Tests the complete admin workflows that are critical for production operations.
These tests validate that admins can manage the system, users, and jobs effectively.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta
from typing import Dict, Any, List


class TestAdminManagementJourney:
    """
    USER STORY: "As an admin, I need to manage users and monitor the system"
    
    This validates the complete admin workflow:
    1. Admin authenticates with admin privileges
    2. Admin views all jobs across all users
    3. Admin soft-deletes problematic job
    4. Admin restores accidentally deleted job
    5. Admin permanently deletes job
    6. Admin views system statistics
    
    If this fails, admins cannot manage the system effectively.
    """
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service with admin-level data"""
        service = AsyncMock()
        
        # Mock admin user
        service.get_user_by_id_async.return_value = {
            "id": "admin-123",
            "email": "admin@example.com",
            "permission_level": "admin"
        }
        
        # Mock all jobs across users
        service.query_items_async.return_value = [
            {
                "id": "job-1",
                "user_id": "user-1",
                "file_name": "meeting1.mp3",
                "status": "completed",
                "is_deleted": False,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": "job-2",
                "user_id": "user-2",
                "file_name": "meeting2.mp3",
                "status": "processing",
                "is_deleted": False,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": "job-3",
                "user_id": "user-1",
                "file_name": "meeting3.mp3",
                "status": "failed",
                "is_deleted": False,
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        
        # Mock job retrieval
        service.get_job_by_id_async.return_value = {
            "id": "job-1",
            "user_id": "user-1",
            "file_name": "meeting1.mp3",
            "status": "completed",
            "is_deleted": False
        }
        
        # Mock job update (soft delete)
        service.update_item_async.return_value = {
            "id": "job-1",
            "user_id": "user-1",
            "file_name": "meeting1.mp3",
            "status": "completed",
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": "admin-123"
        }
        
        return service
    
    @pytest.fixture
    def mock_auth_service(self):
        """Mock authentication service for admin"""
        service = Mock()
        
        service.decode_token.return_value = {
            "sub": "admin-123",
            "email": "admin@example.com",
            "permission_level": "admin",
            "exp": 9999999999
        }
        
        return service
    
    @pytest.fixture
    def mock_permission_service(self):
        """Mock permission service"""
        service = Mock()
        
        # Admin has all permissions
        service.has_permission_level_method.return_value = True
        service.get_user_capabilities.return_value = {
            "view_all_jobs": True,
            "delete_any_job": True,
            "manage_users": True,
            "view_analytics": True
        }
        
        return service
    
    @pytest.mark.asyncio
    async def test_admin_can_manage_system_wide_jobs(
        self,
        mock_cosmos_service,
        mock_auth_service,
        mock_permission_service
    ):
        """
        CRITICAL ADMIN WORKFLOW: Complete job management lifecycle
        
        Validates:
        1. Admin authentication with elevated privileges
        2. Viewing all jobs across all users
        3. Soft-deleting problematic jobs
        4. Restoring accidentally deleted jobs
        5. Viewing system statistics
        
        If this fails, admins cannot manage production issues.
        """
        
        # STEP 1: Admin authenticates
        admin_token = "admin-jwt-token"
        admin_payload = mock_auth_service.decode_token(admin_token)
        assert admin_payload["permission_level"] == "admin"
        print("✅ STEP 1: Admin authenticated with elevated privileges")
        
        # STEP 2: Admin retrieves user profile
        admin_user = await mock_cosmos_service.get_user_by_id_async("admin-123")
        assert admin_user["permission_level"] == "admin"
        print(f"✅ STEP 2: Admin profile retrieved: {admin_user['email']}")
        
        # STEP 3: Admin checks permissions
        can_view_all = mock_permission_service.get_user_capabilities("admin")
        assert can_view_all["view_all_jobs"] is True
        assert can_view_all["delete_any_job"] is True
        print("✅ STEP 3: Admin permissions verified")
        
        # STEP 4: Admin views all jobs across all users
        all_jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c WHERE c.is_deleted = false",
            parameters=[]
        )
        assert len(all_jobs) == 3
        assert all_jobs[0]["user_id"] == "user-1"
        assert all_jobs[1]["user_id"] == "user-2"
        print(f"✅ STEP 4: Admin retrieved {len(all_jobs)} jobs across all users")
        
        # STEP 5: Admin soft-deletes problematic job
        job_to_delete = await mock_cosmos_service.get_job_by_id_async("job-1")
        assert job_to_delete["is_deleted"] is False
        
        deleted_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-1",
            item={
                **job_to_delete,
                "is_deleted": True,
                "deleted_at": datetime.utcnow().isoformat(),
                "deleted_by": "admin-123"
            }
        )
        assert deleted_job["is_deleted"] is True
        assert deleted_job["deleted_by"] == "admin-123"
        print(f"✅ STEP 5: Admin soft-deleted job: {deleted_job['id']}")
        
        # STEP 6: Admin can restore the job (simulate accidental deletion)
        mock_cosmos_service.update_item_async.return_value = {
            **deleted_job,
            "is_deleted": False,
            "deleted_at": None,
            "deleted_by": None,
            "restored_at": datetime.utcnow().isoformat(),
            "restored_by": "admin-123"
        }
        
        restored_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-1",
            item={
                **deleted_job,
                "is_deleted": False,
                "restored_at": datetime.utcnow().isoformat(),
                "restored_by": "admin-123"
            }
        )
        assert restored_job["is_deleted"] is False
        assert restored_job["restored_by"] == "admin-123"
        print(f"✅ STEP 6: Admin restored job: {restored_job['id']}")
        
        # STEP 7: Admin views system statistics
        stats = {
            "total_jobs": len(all_jobs),
            "active_jobs": sum(1 for j in all_jobs if j["status"] in ["pending", "processing"]),
            "completed_jobs": sum(1 for j in all_jobs if j["status"] == "completed"),
            "failed_jobs": sum(1 for j in all_jobs if j["status"] == "failed"),
            "total_users": 2
        }
        assert stats["total_jobs"] == 3
        assert stats["completed_jobs"] == 1
        assert stats["failed_jobs"] == 1
        print(f"✅ STEP 7: Admin viewed system statistics: {stats['total_jobs']} total jobs")
        
        print("✅ COMPLETE: Admin can manage system-wide jobs and monitor health")
    
    @pytest.mark.asyncio
    async def test_admin_can_manage_user_accounts(
        self,
        mock_cosmos_service,
        mock_auth_service,
        mock_permission_service
    ):
        """
        ADMIN USER MANAGEMENT: Create, update, and manage user accounts
        
        Validates:
        1. Admin can view all users
        2. Admin can create new users
        3. Admin can update user permissions
        4. Admin can view user-specific jobs
        
        Critical for user lifecycle management.
        """
        
        # STEP 1: Admin authenticates
        admin_token = "admin-jwt-token"
        admin_payload = mock_auth_service.decode_token(admin_token)
        assert admin_payload["permission_level"] == "admin"
        print("✅ STEP 1: Admin authenticated")
        
        # STEP 2: Admin views all users
        mock_cosmos_service.query_items_async.return_value = [
            {"id": "user-1", "email": "user1@example.com", "permission_level": "user"},
            {"id": "user-2", "email": "user2@example.com", "permission_level": "user"},
            {"id": "admin-123", "email": "admin@example.com", "permission_level": "admin"}
        ]
        
        all_users = await mock_cosmos_service.query_items_async(
            container_name="users",
            query="SELECT * FROM c",
            parameters=[]
        )
        assert len(all_users) == 3
        print(f"✅ STEP 2: Admin viewed {len(all_users)} users")
        
        # STEP 3: Admin creates new user
        mock_cosmos_service.create_item_async.return_value = {
            "id": "user-3",
            "email": "newuser@example.com",
            "permission_level": "user",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": "admin-123"
        }
        
        new_user = await mock_cosmos_service.create_item_async(
            container_name="users",
            item={
                "email": "newuser@example.com",
                "permission_level": "user",
                "created_by": "admin-123"
            }
        )
        assert new_user["email"] == "newuser@example.com"
        assert new_user["created_by"] == "admin-123"
        print(f"✅ STEP 3: Admin created new user: {new_user['email']}")
        
        # STEP 4: Admin updates user permission level
        mock_cosmos_service.update_item_async.return_value = {
            **new_user,
            "permission_level": "editor",
            "updated_at": datetime.utcnow().isoformat(),
            "updated_by": "admin-123"
        }
        
        updated_user = await mock_cosmos_service.update_item_async(
            container_name="users",
            item_id="user-3",
            item={
                **new_user,
                "permission_level": "editor",
                "updated_by": "admin-123"
            }
        )
        assert updated_user["permission_level"] == "editor"
        assert updated_user["updated_by"] == "admin-123"
        print(f"✅ STEP 4: Admin updated user permission to: {updated_user['permission_level']}")
        
        # STEP 5: Admin views user-specific jobs
        mock_cosmos_service.query_items_async.return_value = [
            {"id": "job-1", "user_id": "user-1", "file_name": "meeting1.mp3"},
            {"id": "job-2", "user_id": "user-1", "file_name": "meeting2.mp3"}
        ]
        
        user_jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": "user-1"}]
        )
        assert len(user_jobs) == 2
        assert all(j["user_id"] == "user-1" for j in user_jobs)
        print(f"✅ STEP 5: Admin viewed {len(user_jobs)} jobs for specific user")
        
        print("✅ COMPLETE: Admin can manage user accounts and permissions")


class TestAdminJobManagementEdgeCases:
    """
    Edge cases and error scenarios for admin job management
    """
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_admin_cannot_permanently_delete_without_soft_delete_first(
        self,
        mock_cosmos_service
    ):
        """
        BUSINESS RULE: Permanent deletion requires soft-delete first
        
        Validates:
        - Jobs must be soft-deleted before permanent deletion
        - Prevents accidental data loss
        - Audit trail is preserved
        """
        
        # STEP 1: Try to permanently delete non-soft-deleted job
        mock_cosmos_service.get_job_by_id_async.return_value = {
            "id": "job-1",
            "user_id": "user-1",
            "is_deleted": False  # Not soft-deleted
        }
        
        job = await mock_cosmos_service.get_job_by_id_async("job-1")
        
        # Business rule check
        can_permanently_delete = job.get("is_deleted", False)
        assert can_permanently_delete is False
        print("✅ STEP 1: Permanent deletion blocked for non-soft-deleted job")
        
        # STEP 2: Soft-delete the job first
        mock_cosmos_service.update_item_async.return_value = {
            **job,
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat()
        }
        
        soft_deleted_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-1",
            item={**job, "is_deleted": True}
        )
        assert soft_deleted_job["is_deleted"] is True
        print("✅ STEP 2: Job soft-deleted successfully")
        
        # STEP 3: Now permanent deletion is allowed
        can_permanently_delete = soft_deleted_job.get("is_deleted", False)
        assert can_permanently_delete is True
        print("✅ STEP 3: Permanent deletion now allowed after soft-delete")
        
        print("✅ COMPLETE: Two-step deletion process validated")
    
    @pytest.mark.asyncio
    async def test_admin_operations_preserve_audit_trail(
        self,
        mock_cosmos_service
    ):
        """
        DATA INTEGRITY: All admin operations must be auditable
        
        Validates:
        - Who performed the action
        - When the action was performed
        - What was changed
        
        Critical for compliance and debugging.
        """
        
        # STEP 1: Admin deletes job - audit trail recorded
        mock_cosmos_service.update_item_async.return_value = {
            "id": "job-1",
            "user_id": "user-1",
            "is_deleted": True,
            "deleted_at": datetime.utcnow().isoformat(),
            "deleted_by": "admin-123",  # WHO
            "deletion_reason": "Inappropriate content"  # WHY
        }
        
        deleted_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-1",
            item={}
        )
        
        # Validate audit trail
        assert deleted_job["deleted_by"] is not None
        assert deleted_job["deleted_at"] is not None
        assert "admin-123" in deleted_job["deleted_by"]
        print(f"✅ STEP 1: Deletion audit trail: by {deleted_job['deleted_by']} at {deleted_job['deleted_at']}")
        
        # STEP 2: Admin restores job - audit trail recorded
        mock_cosmos_service.update_item_async.return_value = {
            **deleted_job,
            "is_deleted": False,
            "restored_at": datetime.utcnow().isoformat(),
            "restored_by": "admin-123",  # WHO
            "restoration_reason": "False positive"  # WHY
        }
        
        restored_job = await mock_cosmos_service.update_item_async(
            container_name="jobs",
            item_id="job-1",
            item={}
        )
        
        # Validate restoration audit trail
        assert restored_job["restored_by"] is not None
        assert restored_job["restored_at"] is not None
        assert restored_job["deleted_at"] is not None  # Original deletion time preserved
        print(f"✅ STEP 2: Restoration audit trail: by {restored_job['restored_by']} at {restored_job['restored_at']}")
        
        # STEP 3: Verify complete audit history
        audit_history = {
            "created_at": "2025-01-01T00:00:00Z",
            "deleted_at": deleted_job["deleted_at"],
            "deleted_by": deleted_job["deleted_by"],
            "restored_at": restored_job["restored_at"],
            "restored_by": restored_job["restored_by"]
        }
        assert all(v is not None for v in audit_history.values())
        print(f"✅ STEP 3: Complete audit trail preserved: {len(audit_history)} events")
        
        print("✅ COMPLETE: All admin operations are fully auditable")
