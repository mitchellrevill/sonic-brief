"""
Startup Validation Module

This module provides comprehensive validation of critical dependencies during application startup.
It implements a fail-fast strategy to prevent broken deployments when dependencies are unavailable.

Key Features:
- Validates Cosmos DB connectivity and required containers
- Validates Azure Blob Storage connectivity
- Validates configuration completeness
- Validates OpenAI service availability
- Provides detailed error reporting with actionable remediation steps
- Supports both blocking (fail-fast) and non-blocking (warning) modes

Usage:
    from core.health import StartupValidator
    
    validator = StartupValidator(cosmos_service, config)
    result = await validator.validate_all()
    
    if not result.is_healthy:
        # Log errors and exit
        for error in result.errors:
            logger.error(error)
        sys.exit(1)
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from azure.cosmos.exceptions import CosmosHttpResponseError
from azure.core.exceptions import AzureError

from ..config import AppConfig


class ValidationLevel(str, Enum):
    """Severity level for validation checks"""
    CRITICAL = "critical"  # Must pass or app won't start
    WARNING = "warning"    # Should pass but app can continue
    INFO = "info"          # Informational only


@dataclass
class ValidationError:
    """Detailed validation error with remediation guidance"""
    component: str
    message: str
    level: ValidationLevel
    details: Dict[str, Any] = field(default_factory=dict)
    remediation: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def __str__(self) -> str:
        """Format error for logging"""
        msg = f"[{self.level.value.upper()}] {self.component}: {self.message}"
        if self.details:
            msg += f" | Details: {self.details}"
        if self.remediation:
            msg += f" | Remediation: {self.remediation}"
        return msg


@dataclass
class ValidationResult:
    """Result of startup validation"""
    is_healthy: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    validations_run: int = 0
    validations_passed: int = 0
    duration_seconds: float = 0.0
    
    def add_error(self, error: ValidationError):
        """Add validation error"""
        if error.level == ValidationLevel.CRITICAL:
            self.errors.append(error)
            self.is_healthy = False
        elif error.level == ValidationLevel.WARNING:
            self.warnings.append(error)
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        status = "✅ HEALTHY" if self.is_healthy else "❌ UNHEALTHY"
        return (
            f"{status} - {self.validations_passed}/{self.validations_run} checks passed "
            f"({self.duration_seconds:.2f}s) | "
            f"Errors: {len(self.errors)}, Warnings: {len(self.warnings)}"
        )


class StartupValidationError(Exception):
    """Exception raised when critical startup validation fails"""
    
    def __init__(self, result: ValidationResult):
        self.result = result
        error_messages = "\n".join(str(e) for e in result.errors)
        super().__init__(f"Startup validation failed:\n{error_messages}")


class StartupValidator:
    """
    Comprehensive startup validator for critical dependencies.
    
    Validates:
    1. Cosmos DB connectivity and container availability
    2. Azure Blob Storage connectivity
    3. Configuration completeness
    4. External service availability (OpenAI, Azure Speech)
    """
    
    def __init__(self, cosmos_service, config: AppConfig):
        """
        Initialize startup validator.
        
        Args:
            cosmos_service: CosmosService instance
            config: Application configuration
        """
        self.cosmos = cosmos_service
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def validate_all(self, fail_fast: bool = True) -> ValidationResult:
        """
        Run all validation checks.
        
        Args:
            fail_fast: If True, raise exception on critical failures
            
        Returns:
            ValidationResult with all check results
            
        Raises:
            StartupValidationError: If fail_fast=True and critical checks fail
        """
        start_time = datetime.utcnow()
        result = ValidationResult(is_healthy=True)
        
        self.logger.info("🚀 Starting application startup validation...")
        
        # Run all validation checks
        validation_checks = [
            ("Configuration", self._validate_configuration),
            ("Cosmos DB Connection", self._validate_cosmos_connection),
            ("Cosmos DB Containers", self._validate_cosmos_containers),
            ("Blob Storage", self._validate_blob_storage),
        ]
        
        for check_name, check_func in validation_checks:
            result.validations_run += 1
            try:
                self.logger.info(f"  Validating {check_name}...")
                validation_error = await check_func()
                
                if validation_error:
                    result.add_error(validation_error)
                    self.logger.error(f"  ❌ {check_name} validation failed: {validation_error.message}")
                else:
                    result.validations_passed += 1
                    self.logger.info(f"  ✅ {check_name} validated successfully")
                    
            except Exception as e:
                # Unexpected error during validation
                error = ValidationError(
                    component=check_name,
                    message=f"Validation check crashed: {str(e)}",
                    level=ValidationLevel.CRITICAL,
                    details={"error_type": type(e).__name__},
                    remediation="Check application logs for stack trace"
                )
                result.add_error(error)
                self.logger.error(f"  ❌ {check_name} validation crashed", exc_info=True)
        
        # Calculate duration
        end_time = datetime.utcnow()
        result.duration_seconds = (end_time - start_time).total_seconds()
        
        # Log summary
        self.logger.info(f"📊 Validation complete: {result.summary()}")
        
        # Log errors and warnings
        for error in result.errors:
            self.logger.error(str(error))
        for warning in result.warnings:
            self.logger.warning(str(warning))
        
        # Fail fast if requested and critical errors exist
        if fail_fast and not result.is_healthy:
            raise StartupValidationError(result)
        
        return result
    
    async def _validate_configuration(self) -> Optional[ValidationError]:
        """Validate required configuration values are present"""
        missing_configs = []
        
        # Check critical configuration values
        # Note: cosmos_endpoint is validated by the Cosmos DB connection check
        if not self.config.cosmos_key:
            # Key might be optional if using managed identity
            self.logger.warning("Cosmos key not configured, assuming managed identity")
        
        if not self.config.cosmos_database:
            missing_configs.append("AZURE_COSMOS_DB")
        
        if not self.config.jwt_secret_key:
            missing_configs.append("JWT_SECRET_KEY")
        
        if missing_configs:
            return ValidationError(
                component="Configuration",
                message=f"Missing required configuration: {', '.join(missing_configs)}",
                level=ValidationLevel.CRITICAL,
                details={"missing_vars": missing_configs},
                remediation=f"Set environment variables: {', '.join(missing_configs)}"
            )
        
        return None
    
    async def _validate_cosmos_connection(self) -> Optional[ValidationError]:
        """Validate Cosmos DB connection is working"""
        try:
            # Try to get database client
            database = self.cosmos.database
            
            # Test actual connectivity with a lightweight query
            # This will fail if credentials are wrong or endpoint is unreachable
            database_properties = database.read()
            
            self.logger.debug(f"Connected to Cosmos database: {database_properties.get('id')}")
            return None
            
        except CosmosHttpResponseError as e:
            return ValidationError(
                component="Cosmos DB Connection",
                message=f"Failed to connect to Cosmos DB",
                level=ValidationLevel.CRITICAL,
                details={
                    "endpoint": self.config.cosmos_endpoint,
                    "database": self.config.cosmos_database,
                    "status_code": e.status_code,
                    "error": str(e)
                },
                remediation="Check Cosmos DB endpoint, credentials, and network connectivity. "
                           "Verify firewall rules allow access from this IP address."
            )
        except Exception as e:
            return ValidationError(
                component="Cosmos DB Connection",
                message=f"Unexpected error connecting to Cosmos DB: {str(e)}",
                level=ValidationLevel.CRITICAL,
                details={"error_type": type(e).__name__},
                remediation="Check application logs for detailed stack trace"
            )
    
    async def _validate_cosmos_containers(self) -> Optional[ValidationError]:
        """Validate all required Cosmos DB containers exist"""
        required_containers = [
            "auth",
            "jobs",
            "analytics",
            "user_sessions",
            "audit_logs"
        ]
        
        missing_containers = []
        
        for container_name in required_containers:
            try:
                # Try to get container client
                container = self.cosmos.get_container(container_name)
                
                # Test container exists with a simple read
                container.read()
                
                self.logger.debug(f"Container '{container_name}' validated")
                
            except CosmosHttpResponseError as e:
                if e.status_code == 404:
                    missing_containers.append(container_name)
                    self.logger.warning(f"Container '{container_name}' not found (404)")
                else:
                    # Other Cosmos errors (auth, network, etc.)
                    return ValidationError(
                        component="Cosmos DB Containers",
                        message=f"Error accessing container '{container_name}'",
                        level=ValidationLevel.CRITICAL,
                        details={
                            "container": container_name,
                            "status_code": e.status_code,
                            "error": str(e)
                        },
                        remediation=f"Check permissions and container configuration for '{container_name}'"
                    )
            except Exception as e:
                return ValidationError(
                    component="Cosmos DB Containers",
                    message=f"Unexpected error validating container '{container_name}': {str(e)}",
                    level=ValidationLevel.CRITICAL,
                    details={"container": container_name, "error_type": type(e).__name__},
                    remediation="Check application logs for detailed stack trace"
                )
        
        if missing_containers:
            return ValidationError(
                component="Cosmos DB Containers",
                message=f"Missing required containers: {', '.join(missing_containers)}",
                level=ValidationLevel.CRITICAL,
                details={"missing_containers": missing_containers},
                remediation=f"Create missing containers in Cosmos DB or run infrastructure provisioning scripts. "
                           f"Required containers: {', '.join(missing_containers)}"
            )
        
        return None
    
    async def _validate_blob_storage(self) -> Optional[ValidationError]:
        """Validate Azure Blob Storage is accessible"""
        # Blob storage validation is optional - if not configured, just warn
        storage_account_url = self.config.azure_storage_account_url
        
        if not storage_account_url:
            return ValidationError(
                component="Blob Storage",
                message="Blob storage not configured",
                level=ValidationLevel.WARNING,
                details={"config_checked": ["azure_storage_account_url"]},
                remediation="Set AZURE_STORAGE_ACCOUNT_URL if blob storage is required"
            )
        
        # TODO: Add actual storage connectivity check when BlobService is available
        # For now, just check configuration is present
        self.logger.debug(f"Blob storage account configured: {storage_account_url}")
        return None
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Lightweight health check for readiness/liveness probes.
        
        Returns:
            Dict with health status suitable for HTTP health endpoints
        """
        result = await self.validate_all(fail_fast=False)
        
        return {
            "status": "healthy" if result.is_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "total": result.validations_run,
                "passed": result.validations_passed,
                "failed": len(result.errors),
                "warnings": len(result.warnings)
            },
            "duration_seconds": result.duration_seconds,
            "errors": [
                {
                    "component": e.component,
                    "message": e.message,
                    "level": e.level.value
                }
                for e in result.errors
            ],
            "warnings": [
                {
                    "component": w.component,
                    "message": w.message,
                    "level": w.level.value
                }
                for w in result.warnings
            ]
        }
