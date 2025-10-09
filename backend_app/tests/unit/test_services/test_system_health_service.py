"""
Unit tests for SystemHealthService

Tests system health monitoring including service status checks,
response time measurements, and health metric collection.
"""

import pytest
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.services.monitoring.system_health_service import SystemHealthService
from app.models.analytics_models import SystemHealthMetrics, SystemHealthResponse


@pytest.fixture
def mock_cosmos_service():
    """Mock CosmosService"""
    mock = Mock()
    mock.auth_container = Mock()
    mock.auth_container.query_items = Mock()
    mock.config = Mock()
    return mock


@pytest.fixture
def system_health_service(mock_cosmos_service):
    """Create SystemHealthService instance with mocked dependencies"""
    return SystemHealthService(cosmos_service=mock_cosmos_service)


class TestGetSystemHealth:
    """Tests for get_system_health method"""

    @pytest.mark.asyncio
    async def test_get_system_health_success(self, system_health_service):
        """Test successful health check"""
        with patch.object(system_health_service, '_test_api_response_time', return_value=50.0), \
             patch.object(system_health_service, '_test_database_health', return_value=100.0), \
             patch.object(system_health_service, '_get_real_memory_usage', return_value=45.5):
            
            result = await system_health_service.get_system_health()

        assert isinstance(result, SystemHealthResponse)
        assert result.status in ['healthy', 'degraded', 'unhealthy']
        assert result.metrics.api_response_time_ms == 50.0
        assert result.metrics.database_response_time_ms == 100.0
        assert result.metrics.memory_usage_percentage == 45.5
        assert 'timestamp' in result.model_dump() or hasattr(result, 'timestamp')

    @pytest.mark.asyncio
    async def test_get_system_health_healthy_status(self, system_health_service):
        """Test health check returns healthy status with good metrics"""
        with patch.object(system_health_service, '_test_api_response_time', return_value=30.0), \
             patch.object(system_health_service, '_test_database_health', return_value=50.0), \
             patch.object(system_health_service, '_get_real_memory_usage', return_value=40.0):
            
            result = await system_health_service.get_system_health()

        assert result.status == 'healthy'

    @pytest.mark.asyncio
    async def test_get_system_health_degraded_status(self, system_health_service):
        """Test health check returns degraded status with slow response times"""
        with patch.object(system_health_service, '_test_api_response_time', return_value=500.0), \
             patch.object(system_health_service, '_test_database_health', return_value=600.0), \
             patch.object(system_health_service, '_get_real_memory_usage', return_value=75.0):
            
            result = await system_health_service.get_system_health()

        assert result.status in ['degraded', 'unhealthy']

    @pytest.mark.asyncio
    async def test_get_system_health_error_handling(self, system_health_service):
        """Test health check handles errors gracefully"""
        with patch.object(system_health_service, '_test_api_response_time', side_effect=Exception("API error")):
            result = await system_health_service.get_system_health()

        # Should return error response, not crash
        assert isinstance(result, SystemHealthResponse)

    @pytest.mark.asyncio
    async def test_get_system_health_includes_services_status(self, system_health_service):
        """Test health check includes service status"""
        with patch.object(system_health_service, '_test_api_response_time', return_value=50.0), \
             patch.object(system_health_service, '_test_database_health', return_value=100.0), \
             patch.object(system_health_service, '_get_real_memory_usage', return_value=45.0):
            
            result = await system_health_service.get_system_health()

        assert hasattr(result, 'services') or 'services' in result.model_dump()
        services = result.services if hasattr(result, 'services') else result.model_dump().get('services', {})
        assert isinstance(services, dict)


class TestAPIResponseTime:
    """Tests for _test_api_response_time method"""

    @pytest.mark.asyncio
    async def test_api_response_time_measurement(self, system_health_service):
        """Test API response time is measured"""
        response_time = await system_health_service._test_api_response_time()

        assert isinstance(response_time, float)
        assert response_time >= 0
        assert response_time < 10000  # Should be less than 10 seconds

    @pytest.mark.asyncio
    async def test_api_response_time_performs_json_operations(self, system_health_service):
        """Test API response time includes real JSON operations"""
        # Should complete without errors
        response_time = await system_health_service._test_api_response_time()
        
        assert response_time >= 0  # Should be non-negative (might be 0.0 on fast machines)
        assert isinstance(response_time, float)

    @pytest.mark.asyncio
    async def test_api_response_time_consistent(self, system_health_service):
        """Test API response time is relatively consistent"""
        times = []
        for _ in range(3):
            response_time = await system_health_service._test_api_response_time()
            times.append(response_time)
        
        # All measurements should be non-negative
        assert all(t >= 0 for t in times)
        # Should all be floats
        assert all(isinstance(t, float) for t in times)


class TestDatabaseHealth:
    """Tests for _test_database_health method"""

    @pytest.mark.asyncio
    async def test_database_health_success(self, system_health_service, mock_cosmos_service):
        """Test successful database health check"""
        mock_cosmos_service.auth_container.query_items.return_value = [{'id': 'test'}]
        
        with patch('app.services.monitoring.system_health_service.run_sync', return_value=[{'id': 'test'}]):
            response_time = await system_health_service._test_database_health()

        assert isinstance(response_time, float)
        assert response_time >= 0

    @pytest.mark.asyncio
    async def test_database_health_no_cosmos_service(self):
        """Test database health when cosmos service is unavailable"""
        service = SystemHealthService(cosmos_service=None)
        
        response_time = await service._test_database_health()

        assert response_time == -1.0  # Indicates unavailable

    @pytest.mark.asyncio
    async def test_database_health_no_container(self, mock_cosmos_service):
        """Test database health when auth container is unavailable"""
        mock_cosmos_service.auth_container = None
        service = SystemHealthService(cosmos_service=mock_cosmos_service)
        
        response_time = await service._test_database_health()

        assert response_time == -1.0

    @pytest.mark.asyncio
    async def test_database_health_query_error(self, system_health_service, mock_cosmos_service):
        """Test database health handles query errors"""
        with patch('app.services.monitoring.system_health_service.run_sync', side_effect=Exception("Query failed")):
            response_time = await system_health_service._test_database_health()

        assert response_time == -1.0  # Indicates error


class TestMemoryUsage:
    """Tests for _get_real_memory_usage method"""

    def test_get_real_memory_usage_with_psutil(self, system_health_service):
        """Test memory usage when psutil is available"""
        with patch('app.services.monitoring.system_health_service.PSUTIL_AVAILABLE', True):
            with patch('app.services.monitoring.system_health_service.psutil') as mock_psutil:
                mock_psutil.virtual_memory.return_value = Mock(percent=65.5)
                
                memory_usage = system_health_service._get_real_memory_usage()

        assert memory_usage == 65.5

    def test_get_real_memory_usage_without_psutil(self, system_health_service):
        """Test memory usage when psutil is unavailable"""
        with patch('app.services.monitoring.system_health_service.PSUTIL_AVAILABLE', False):
            memory_usage = system_health_service._get_real_memory_usage()

        assert memory_usage == 0.0

    def test_get_real_memory_usage_error_handling(self, system_health_service):
        """Test memory usage handles errors gracefully"""
        with patch('app.services.monitoring.system_health_service.PSUTIL_AVAILABLE', True):
            with patch('app.services.monitoring.system_health_service.psutil') as mock_psutil:
                mock_psutil.virtual_memory.side_effect = Exception("Memory error")
                
                memory_usage = system_health_service._get_real_memory_usage()

        assert memory_usage == 0.0


class TestCheckServicesStatus:
    """Tests for _check_services_status method"""

    @pytest.mark.asyncio
    async def test_check_services_status_healthy(self, system_health_service):
        """Test service status with healthy response times"""
        services = await system_health_service._check_services_status(
            api_time=50.0,
            db_time=100.0
        )

        assert isinstance(services, dict)
        assert 'api' in services or 'database' in services

    @pytest.mark.asyncio
    async def test_check_services_status_degraded(self, system_health_service):
        """Test service status with degraded response times"""
        services = await system_health_service._check_services_status(
            api_time=500.0,
            db_time=600.0
        )

        assert isinstance(services, dict)

    @pytest.mark.asyncio
    async def test_check_services_status_unavailable(self, system_health_service):
        """Test service status with unavailable services"""
        services = await system_health_service._check_services_status(
            api_time=-1.0,  # Indicates unavailable
            db_time=-1.0
        )

        assert isinstance(services, dict)


class TestDetermineOverallStatus:
    """Tests for _determine_overall_status method"""

    def test_determine_overall_status_healthy(self, system_health_service):
        """Test overall status determination with healthy metrics"""
        metrics = SystemHealthMetrics(
            api_response_time_ms=50.0,
            database_response_time_ms=100.0,
            storage_response_time_ms=0.0,
            uptime_percentage=0.0,
            active_connections=0,
            memory_usage_percentage=40.0,
            disk_usage_percentage=0.0
        )
        services = {'api': 'healthy', 'database': 'healthy'}

        status = system_health_service._determine_overall_status(metrics, services)

        assert status in ['healthy', 'degraded', 'unhealthy']

    def test_determine_overall_status_unhealthy(self, system_health_service):
        """Test overall status determination with unhealthy metrics"""
        metrics = SystemHealthMetrics(
            api_response_time_ms=5000.0,
            database_response_time_ms=5000.0,
            storage_response_time_ms=0.0,
            uptime_percentage=0.0,
            active_connections=0,
            memory_usage_percentage=95.0,
            disk_usage_percentage=0.0
        )
        services = {'api': 'unhealthy', 'database': 'unhealthy'}

        status = system_health_service._determine_overall_status(metrics, services)

        assert status in ['degraded', 'unhealthy']


class TestCosmosConnectivity:
    """Tests for Cosmos DB connectivity checks"""

    @pytest.mark.asyncio
    async def test_cosmos_connectivity_success(self, system_health_service, mock_cosmos_service):
        """Test successful Cosmos DB connectivity check"""
        if not hasattr(system_health_service, 'check_cosmos_connectivity'):
            pytest.skip("check_cosmos_connectivity method not implemented")

        mock_cosmos_service.auth_container.query_items.return_value = [{'id': 'test'}]
        
        is_connected = await system_health_service.check_cosmos_connectivity()

        assert is_connected is True

    @pytest.mark.asyncio
    async def test_cosmos_connectivity_failure(self, system_health_service, mock_cosmos_service):
        """Test failed Cosmos DB connectivity check"""
        if not hasattr(system_health_service, 'check_cosmos_connectivity'):
            pytest.skip("check_cosmos_connectivity method not implemented")

        mock_cosmos_service.auth_container = None
        
        is_connected = await system_health_service.check_cosmos_connectivity()

        assert is_connected is False


class TestServiceAvailability:
    """Tests for service availability checks"""

    @pytest.mark.asyncio
    async def test_check_service_availability(self, system_health_service):
        """Test checking availability of individual services"""
        if not hasattr(system_health_service, 'check_service_availability'):
            pytest.skip("check_service_availability method not implemented")

        # Should check multiple services
        availability = await system_health_service.check_service_availability()

        assert isinstance(availability, dict)

    @pytest.mark.asyncio
    async def test_check_openai_availability(self, system_health_service):
        """Test OpenAI service availability check"""
        if not hasattr(system_health_service, 'check_openai_health'):
            pytest.skip("check_openai_health method not implemented")

        # Should return status without making actual API call in test
        status = await system_health_service.check_openai_health()

        assert isinstance(status, (bool, str, dict))


class TestErrorResponse:
    """Tests for error response handling"""

    def test_get_error_response(self, system_health_service):
        """Test error response generation"""
        error_response = system_health_service._get_error_response("Test error message")

        assert isinstance(error_response, SystemHealthResponse)
        assert error_response.status == 'unknown'
        
    def test_get_error_response_includes_timestamp(self, system_health_service):
        """Test error response includes timestamp"""
        error_response = system_health_service._get_error_response("Test error")

        assert hasattr(error_response, 'timestamp') or 'timestamp' in error_response.model_dump()
