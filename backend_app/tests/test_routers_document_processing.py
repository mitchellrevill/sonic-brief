import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from app.models.permissions import PermissionLevel, PermissionCapability


class TestDocumentProcessingRoutes:
    """Test document processing routes with dependency-based authorization."""
    
    def test_refine_analysis_requires_edit_permission(self, app_client, fake_user, fake_job, 
                                                     mock_cosmos_service, mock_analysis_service):
        """Test that refine_analysis endpoint requires job edit permission."""
        from conftest import override_get_current_user, clear_dependency_overrides
        
        # Setup: user owns the job (should have edit permission)
        mock_cosmos_service.get_job_by_id.return_value = fake_job
        mock_analysis_service.process_refine.return_value = {"status": "completed", "refined_analysis": "test content"}
        
        override_get_current_user(app_client, fake_user)
        
        # Test data
        refine_request = {
            "refined_content": "This is refined analysis content",
            "analysis_type": "refined",
            "preserve_original": True
        }
        
        response = app_client.put(f"/api/content/jobs/{fake_job['id']}/analysis/refine", json=refine_request)
        
        assert response.status_code == 200
        mock_analysis_service.process_refine.assert_called_once()
    
    def test_refine_analysis_denies_non_owner_without_permission(self, app_client, fake_user, other_user_job,
                                                               mock_cosmos_service, mock_analysis_service):
        """Test that non-owners without edit permission are denied."""
        mock_cosmos_service.get_job_by_id.return_value = other_user_job
        
        override_get_current_user(app_client, fake_user)
        
        refine_request = {
            "refined_content": "This is refined analysis content",
            "analysis_type": "refined", 
            "preserve_original": True
        }
        
        response = app_client.put(f"/api/content/jobs/{other_user_job['id']}/analysis/refine", json=refine_request)
        
        assert response.status_code == 403
        mock_analysis_service.process_refine.assert_not_called()
    
    def test_refine_analysis_allows_admin_for_any_job(self, app_client, fake_admin_user, other_user_job,
                                                     mock_cosmos_service, mock_analysis_service):
        """Test that admin users can refine any job's analysis."""
        mock_cosmos_service.get_job_by_id.return_value = other_user_job
        mock_analysis_service.process_refine.return_value = {"status": "completed"}
        
        override_get_current_user(app_client, fake_admin_user)
        
        refine_request = {
            "refined_content": "Admin refined content",
            "analysis_type": "refined",
            "preserve_original": True
        }
        
        response = app_client.put(f"/api/content/jobs/{other_user_job['id']}/analysis/refine", json=refine_request)
        
        assert response.status_code == 200
        mock_analysis_service.process_refine.assert_called_once()
    
    def test_generate_talking_points_requires_edit_permission(self, app_client, fake_user, fake_job,
                                                            mock_cosmos_service, mock_analysis_service):
        """Test that generate_talking_points requires job edit permission."""
        mock_cosmos_service.get_job_by_id.return_value = fake_job
        mock_analysis_service.generate_talking_points.return_value = {
            "talking_points": ["Point 1", "Point 2"],
            "generated_at": "2025-09-11T12:00:00Z"
        }
        
        override_get_current_user(app_client, fake_user)
        
        talking_points_request = {
            "key_themes": ["innovation", "growth"],
            "audience_type": "executives",
            "format_style": "bullet"
        }
        
        response = app_client.post(f"/api/content/jobs/{fake_job['id']}/talking-points", json=talking_points_request)
        
        assert response.status_code == 200
        result = response.json()
        assert "talking_points" in result
        mock_analysis_service.generate_talking_points.assert_called_once()
    
    def test_generate_talking_points_denies_unauthorized_user(self, app_client, fake_user, other_user_job,
                                                            mock_cosmos_service, mock_analysis_service):
        """Test that unauthorized users cannot generate talking points."""
        mock_cosmos_service.get_job_by_id.return_value = other_user_job
        
        override_get_current_user(app_client, fake_user)
        
        talking_points_request = {
            "key_themes": ["innovation"],
            "audience_type": "general",
            "format_style": "bullet"
        }
        
        response = app_client.post(f"/api/content/jobs/{other_user_job['id']}/talking-points", json=talking_points_request)
        
        assert response.status_code == 403
        mock_analysis_service.generate_talking_points.assert_not_called()
    
    def test_get_talking_points_requires_view_permission(self, app_client, fake_user, fake_job,
                                                       mock_cosmos_service):
        """Test that get_talking_points requires job view permission."""
        mock_cosmos_service.get_job_by_id.return_value = fake_job
        
        # Mock job with talking points
        job_with_talking_points = {**fake_job, "talking_points": ["Point 1", "Point 2"]}
        mock_cosmos_service.get_job_by_id.return_value = job_with_talking_points
        
        override_get_current_user(app_client, fake_user)
        
        response = app_client.get(f"/api/content/jobs/{fake_job['id']}/talking-points")
        
        assert response.status_code == 200
        result = response.json()
        assert "talking_points" in result
    
    def test_get_talking_points_denies_unauthorized_user(self, app_client, fake_user, other_user_job,
                                                        mock_cosmos_service):
        """Test that unauthorized users cannot view talking points."""
        mock_cosmos_service.get_job_by_id.return_value = other_user_job
        
        override_get_current_user(app_client, fake_user)
        
        response = app_client.get(f"/api/content/jobs/{other_user_job['id']}/talking-points")
        
        assert response.status_code == 403
    
    def test_export_job_content_requires_export_permission(self, app_client, fake_editor_user, fake_job,
                                                          mock_cosmos_service, mock_export_service):
        """Test that export_job_content requires export permission."""
        mock_cosmos_service.get_job_by_id.return_value = fake_job
        mock_export_service.export_job.return_value = b"exported content"
        
        override_get_current_user(app_client, fake_editor_user)  # Editor has export capability
        
        response = app_client.get(f"/api/content/jobs/{fake_job['id']}/export?format=pdf")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "attachment" in response.headers.get("content-disposition", "")
        mock_export_service.export_job.assert_called_once()
    
    def test_export_job_content_denies_user_without_export_permission(self, app_client, fake_user, fake_job,
                                                                     mock_cosmos_service, mock_export_service):
        """Test that users without export permission are denied."""
        mock_cosmos_service.get_job_by_id.return_value = fake_job
        
        # Mock user to not have export capability
        user_without_export = {**fake_user, "permission_level": PermissionLevel.USER}
        
        with patch("app.core.dependencies.user_has_capability_for_job") as mock_capability_check:
            mock_capability_check.return_value = False
            
            override_get_current_user(app_client, user_without_export)
            
            response = app_client.get(f"/api/content/jobs/{fake_job['id']}/export?format=pdf")
            
            assert response.status_code == 403
            mock_export_service.export_job.assert_not_called()
    
    def test_download_original_file_requires_download_permission(self, app_client, fake_user, fake_job,
                                                               mock_cosmos_service, mock_storage_service):
        """Test that download_original_file requires download permission."""
        mock_cosmos_service.get_job_by_id.return_value = fake_job
        mock_storage_service.get_blob_stream.return_value = b"original file content"
        
        override_get_current_user(app_client, fake_user)
        
        response = app_client.get(f"/api/content/jobs/{fake_job['id']}/download")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers.get("content-disposition", "")
        mock_storage_service.get_blob_stream.assert_called_once()
    
    def test_download_original_file_denies_unauthorized_user(self, app_client, fake_user, other_user_job,
                                                           mock_cosmos_service, mock_storage_service):
        """Test that unauthorized users cannot download files."""
        mock_cosmos_service.get_job_by_id.return_value = other_user_job
        
        override_get_current_user(app_client, fake_user)
        
        response = app_client.get(f"/api/content/jobs/{other_user_job['id']}/download")
        
        assert response.status_code == 403
        mock_storage_service.get_blob_stream.assert_not_called()
    
    def test_job_not_found_returns_404(self, app_client, fake_user, mock_cosmos_service):
        """Test that missing jobs return 404 for all endpoints."""
        mock_cosmos_service.get_job_by_id.return_value = None
        
        override_get_current_user(app_client, fake_user)
        
        # Test various endpoints
        endpoints = [
            ("PUT", f"/api/content/jobs/nonexistent/analysis/refine", {"refined_content": "test"}),
            ("POST", f"/api/content/jobs/nonexistent/talking-points", {"key_themes": []}),
            ("GET", f"/api/content/jobs/nonexistent/talking-points", None),
            ("GET", f"/api/content/jobs/nonexistent/export", None),
            ("GET", f"/api/content/jobs/nonexistent/download", None),
        ]
        
        for method, url, json_data in endpoints:
            if method == "GET":
                response = app_client.get(url)
            elif method == "POST":
                response = app_client.post(url, json=json_data)
            elif method == "PUT":
                response = app_client.put(url, json=json_data)
            
            assert response.status_code == 404, f"Endpoint {method} {url} should return 404"


# Import the override helper at module level for the tests to access it
from conftest import override_get_current_user
