"""
Smoke tests to verify test infrastructure is working correctly.

These tests ensure that:
- Pytest is configured correctly
- Fixtures are loading properly
- Mock objects work as expected
- Async tests can run
"""

import pytest
from unittest.mock import Mock


class TestTestInfrastructure:
    """Verify test infrastructure is working"""
    
    def test_pytest_working(self):
        """Verify pytest is working"""
        assert True
    
    def test_mock_working(self):
        """Verify mocking is working"""
        mock_obj = Mock()
        mock_obj.test_method.return_value = "test"
        
        assert mock_obj.test_method() == "test"
    
    @pytest.mark.asyncio
    async def test_async_working(self):
        """Verify async tests are working"""
        async def sample_async_func():
            return "async_result"
        
        result = await sample_async_func()
        assert result == "async_result"


class TestFixturesLoading:
    """Verify fixtures are loading correctly"""
    
    def test_mock_config_fixture(self, mock_config):
        """Verify mock_config fixture loads"""
        assert mock_config is not None
        assert hasattr(mock_config, 'cosmos_endpoint')
    
    def test_cosmos_service_fixture(self, cosmos_service):
        """Verify cosmos_service fixture loads"""
        assert cosmos_service is not None
        assert cosmos_service.is_available() is True
    
    def test_authentication_service_fixture(self, authentication_service):
        """Verify authentication_service fixture loads"""
        assert authentication_service is not None
        assert hasattr(authentication_service, 'decode_jwt_token')
    
    def test_job_service_fixture(self, job_service):
        """Verify job_service fixture loads"""
        assert job_service is not None
        assert hasattr(job_service, 'get_job')


class TestSampleData:
    """Verify sample data fixtures work"""
    
    def test_sample_user_fixture(self, sample_user):
        """Verify sample_user fixture"""
        assert sample_user is not None
        assert "id" in sample_user
        assert "email" in sample_user
        assert sample_user["type"] == "user"
    
    def test_sample_job_fixture(self, sample_job):
        """Verify sample_job fixture"""
        assert sample_job is not None
        assert "id" in sample_job
        assert sample_job["type"] == "job"
        assert sample_job["status"] == "uploaded"
    
    def test_valid_jwt_token_fixture(self, valid_jwt_token):
        """Verify valid_jwt_token fixture"""
        assert valid_jwt_token is not None
        assert isinstance(valid_jwt_token, str)
        assert len(valid_jwt_token) > 0


class TestImports:
    """Verify all required modules can be imported"""
    
    def test_import_cosmos_service(self):
        """Verify CosmosService can be imported"""
        from app.core.dependencies import CosmosService
        assert CosmosService is not None
    
    def test_import_authentication_service(self):
        """Verify AuthenticationService can be imported"""
        from app.services.auth.authentication_service import AuthenticationService
        assert AuthenticationService is not None
    
    def test_import_job_service(self):
        """Verify JobService can be imported"""
        from app.services.jobs.job_service import JobService
        assert JobService is not None
    
    def test_import_azure_exceptions(self):
        """Verify Azure exceptions can be imported"""
        from azure.cosmos.exceptions import (
            CosmosHttpResponseError,
            CosmosResourceNotFoundError
        )
        assert CosmosHttpResponseError is not None
        assert CosmosResourceNotFoundError is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
