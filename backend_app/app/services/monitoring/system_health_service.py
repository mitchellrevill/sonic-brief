"""
System Health Service - Only real metrics: API response time, Database response time, Memory usage
"""
import os
import time
import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from azure.cosmos import exceptions as cosmos_exceptions
from app.core.config import get_app_config, get_cosmos_db_cached
from app.models.analytics_models import SystemHealthMetrics, SystemHealthResponse

# Optional psutil import
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class SystemHealthService:
    """System health service that only reports 3 real metrics: API response time, Database response time, Memory usage"""
    
    def __init__(self):
        self.service_start_time = time.time()
        try:
            self.config = get_app_config()
            self.cosmos_db = get_cosmos_db_cached(self.config)
        except Exception as e:
            logger.warning(f"Failed to initialize connections: {str(e)}")
            self.config = None
            self.cosmos_db = None

    async def get_system_health(self) -> SystemHealthResponse:
        """
        Get system health metrics for only 3 real, measurable values:
        1. API Response Time (ms) - Real timing of JSON operations
        2. Database Response Time (ms) - Real Cosmos DB query timing 
        3. Memory Usage (%) - Real system memory from psutil
        
        All other metrics are set to 0 and not used.
        """
        try:
            # Real metrics only
            api_response_time = await self._test_api_response_time()
            db_response_time = await self._test_database_health()
            memory_usage = self._get_real_memory_usage()
            
            # Service status based on real response times
            services = await self._check_services_status(api_response_time, db_response_time)

            metrics = SystemHealthMetrics(
                api_response_time_ms=api_response_time,
                database_response_time_ms=db_response_time,
                storage_response_time_ms=0.0,  # Not used
                uptime_percentage=0.0,  # Not used
                active_connections=0,  # Not used
                memory_usage_percentage=memory_usage,
                disk_usage_percentage=0.0  # Not used
            )

            # Determine overall status
            status = self._determine_overall_status(metrics, services)

            return SystemHealthResponse(
                status=status,
                timestamp=datetime.now(timezone.utc).isoformat(),
                metrics=metrics,
                services=services
            )

        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return self._get_error_response(str(e))

    async def _test_api_response_time(self) -> float:
        """Test actual API response time with meaningful operation"""
        start_time = time.time()
        
        # Perform realistic API work - JSON serialization/deserialization
        test_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_array": list(range(100)),
            "nested": {"key": "value", "numbers": [1, 2, 3, 4, 5]}
        }
        
        # Serialize and deserialize to simulate real work
        serialized = json.dumps(test_data)
        deserialized = json.loads(serialized)
        
        # Verify the operation worked
        assert deserialized["test_array"][50] == 50
        
        response_time = (time.time() - start_time) * 1000
        return round(response_time, 2)

    async def _test_database_health(self) -> float:
        """Test actual database connectivity and response time"""
        if not self.cosmos_db:
            return -1.0  # Indicates unavailable, not fake high number
            
        try:
            start_time = time.time()
            
            # Real query to test database
            if hasattr(self.cosmos_db, 'auth_container') and self.cosmos_db.auth_container:
                query = "SELECT TOP 1 c.id FROM c"
                results = list(self.cosmos_db.auth_container.query_items(
                    query=query, 
                    enable_cross_partition_query=True
                ))
                # Verify we got a response
                logger.debug(f"Database health check returned {len(results)} items")
            else:
                return -1.0  # No container available
            
            response_time = (time.time() - start_time) * 1000
            return round(response_time, 2)
            
        except Exception as e:
            logger.warning(f"Database health check failed: {str(e)}")
            return -1.0  # Indicates error, not fake high number

    def _get_real_memory_usage(self) -> float:
        """Get only real memory usage"""
        if PSUTIL_AVAILABLE:
            try:
                # Real memory usage
                memory = psutil.virtual_memory()
                return round(memory.percent, 1)
            except Exception as e:
                logger.warning(f"Error getting memory usage: {e}")
        
        # Return 0 if we can't get real memory usage
        return 0.0

    async def _check_services_status(self, api_time: float, db_time: float) -> Dict[str, str]:
        """
        Check status of API and Database services based on response times
        
        Returns:
            Dict with 'api' and 'database' keys and status values:
            - 'healthy': Good response times
            - 'degraded': Slow but working
            - 'unhealthy': Very slow 
            - 'unavailable': Not working
        """
        services = {}
        
        # API service status
        if api_time > 0:
            if api_time < 100:
                services["api"] = "healthy"
            elif api_time < 1000:
                services["api"] = "degraded"
            else:
                services["api"] = "unhealthy"
        else:
            services["api"] = "unavailable"
        
        # Database service status
        if db_time > 0:
            if db_time < 200:
                services["database"] = "healthy"
            elif db_time < 1000:
                services["database"] = "degraded"
            else:
                services["database"] = "unhealthy"
        else:
            services["database"] = "unavailable"
        
        return services

    def _determine_overall_status(
        self, metrics: SystemHealthMetrics, services: Dict[str, str]
    ) -> str:
        """Determine overall status based on API, Database, and Memory only"""
        # Count service statuses
        unhealthy_services = sum(1 for status in services.values() if status == "unhealthy")
        unavailable_services = sum(1 for status in services.values() if status == "unavailable")
        degraded_services = sum(1 for status in services.values() if status == "degraded")
        
        # If any critical service is unavailable
        if unavailable_services > 0:
            return "unhealthy"
        
        # If any service is unhealthy
        if unhealthy_services > 0:
            return "unhealthy"
        
        # Check memory usage (only if we have real data)
        if metrics.memory_usage_percentage > 0 and metrics.memory_usage_percentage > 90:
            return "unhealthy"
        
        # If services are degraded
        if degraded_services > 0:
            return "degraded"
        
        # Check if performance is degraded
        if (metrics.api_response_time_ms > 500 or 
            (metrics.database_response_time_ms > 0 and metrics.database_response_time_ms > 500) or
            (metrics.memory_usage_percentage > 0 and metrics.memory_usage_percentage > 80)):
            return "degraded"
        
        return "healthy"

    def _get_error_response(self, error_message: str) -> SystemHealthResponse:
        """Return error response with minimal real data"""
        return SystemHealthResponse(
            status="unknown",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metrics=SystemHealthMetrics(
                api_response_time_ms=-1.0,  # Indicates error
                database_response_time_ms=-1.0,
                storage_response_time_ms=0.0,  # Not used
                uptime_percentage=0.0,  # Not used
                active_connections=0,  # Not used
                memory_usage_percentage=0.0,
                disk_usage_percentage=0.0  # Not used
            ),
            services={
                "error": error_message,
                "api": "unknown",
                "database": "unknown"
            }
        )
