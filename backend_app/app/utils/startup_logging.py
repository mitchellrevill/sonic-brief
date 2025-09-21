"""
Enhanced startup logging for DI container initialization and service creation tracking
"""
import logging
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ServiceMetadata:
    """Metadata for tracking service initialization"""
    name: str
    service_type: str  # 'singleton', 'transient', 'scoped'
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    initialization_time_ms: Optional[float] = None
    instance_id: Optional[str] = None
    available: bool = True
    error: Optional[str] = None


class DIContainer:
    """Dependency injection container with comprehensive logging"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._services: Dict[str, ServiceMetadata] = {}
        self._creation_order: List[str] = []
        self._lock = Lock()
        self._startup_phase = "initialization"
        
    def set_startup_phase(self, phase: str):
        """Set the current startup phase for context"""
        self._startup_phase = phase
        self.logger.info(f"🏁 Entering startup phase: {phase}")
        
    def register_service_creation(self, 
                                service_name: str,
                                service_type: str = "singleton",
                                dependencies: List[str] = None,
                                instance_id: str = None) -> ServiceMetadata:
        """Register the start of service creation"""
        with self._lock:
            metadata = ServiceMetadata(
                name=service_name,
                service_type=service_type,
                dependencies=dependencies or [],
                created_at=datetime.now(),
                instance_id=instance_id
            )
            self._services[service_name] = metadata
            self._creation_order.append(service_name)
            
            deps_str = f" (deps: {', '.join(dependencies)})" if dependencies else ""
            self.logger.info(f"🔧 Creating {service_type} service: {service_name}{deps_str}")
            return metadata
    
    def mark_service_created(self, 
                           service_name: str, 
                           instance_id: str = None,
                           available: bool = True,
                           error: str = None):
        """Mark a service as successfully created"""
        with self._lock:
            if service_name in self._services:
                metadata = self._services[service_name]
                if metadata.created_at:
                    elapsed = (datetime.now() - metadata.created_at).total_seconds() * 1000
                    metadata.initialization_time_ms = elapsed
                
                metadata.instance_id = instance_id or metadata.instance_id
                metadata.available = available
                metadata.error = error
                
                status_icon = "✅" if available and not error else "⚠️" if available else "❌"
                timing = f" ({elapsed:.1f}ms)" if metadata.initialization_time_ms else ""
                error_msg = f" - {error}" if error else ""
                instance_msg = f" [id:{instance_id}]" if instance_id else ""
                
                self.logger.info(f"{status_icon} {metadata.service_type.title()} service ready: {service_name}{timing}{instance_msg}{error_msg}")
    
    def log_dependency_graph(self):
        """Log the service dependency graph"""
        if not self._services:
            return
            
        self.logger.info("📊 Service Dependency Graph:")
        
        # Group by service type
        by_type = {}
        for service_name, metadata in self._services.items():
            service_type = metadata.service_type
            if service_type not in by_type:
                by_type[service_type] = []
            by_type[service_type].append(metadata)
        
        for service_type, services in by_type.items():
            self.logger.info(f"  {service_type.upper()} Services:")
            for service in services:
                status = "✅" if service.available and not service.error else "❌"
                timing = f" ({service.initialization_time_ms:.1f}ms)" if service.initialization_time_ms else ""
                deps = f" → depends on: {', '.join(service.dependencies)}" if service.dependencies else ""
                self.logger.info(f"    {status} {service.name}{timing}{deps}")
    
    def log_startup_summary(self):
        """Log startup summary with timing and health information"""
        total_services = len(self._services)
        available_services = sum(1 for s in self._services.values() if s.available)
        total_time = sum(s.initialization_time_ms or 0 for s in self._services.values())
        
        self.logger.info("📈 Startup Summary:")
        self.logger.info(f"  Services initialized: {available_services}/{total_services}")
        self.logger.info(f"  Total initialization time: {total_time:.1f}ms")
        self.logger.info(f"  Initialization order: {' → '.join(self._creation_order)}")
        
        # Log any services with issues
        problematic = [s for s in self._services.values() if not s.available or s.error]
        if problematic:
            self.logger.warning("⚠️ Services with issues:")
            for service in problematic:
                issue = service.error if service.error else "unavailable"
                self.logger.warning(f"  - {service.name}: {issue}")
    
    def get_service_info(self, service_name: str) -> Optional[ServiceMetadata]:
        """Get information about a specific service"""
        return self._services.get(service_name)
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available"""
        service = self._services.get(service_name)
        return service is not None and service.available and not service.error


class StartupLogger:
    """Enhanced startup logger with phase tracking and service monitoring"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.di_container = DIContainer(logger)
        self._startup_start = None
        self._phases: Dict[str, float] = {}
        
    def start_startup(self):
        """Mark the beginning of application startup"""
        self._startup_start = time.time()
        self.logger.info("🚀 Starting Sonic Brief API application startup...")
        
    def start_phase(self, phase_name: str, description: str = None):
        """Start a new startup phase"""
        self._phases[phase_name] = time.time()
        self.di_container.set_startup_phase(phase_name)
        if description:
            self.logger.info(f"📋 {description}")
    
    def end_phase(self, phase_name: str):
        """End a startup phase"""
        if phase_name in self._phases:
            elapsed = (time.time() - self._phases[phase_name]) * 1000
            self.logger.info(f"✅ Phase '{phase_name}' completed in {elapsed:.1f}ms")
    
    def log_config_info(self, config):
        """Log configuration information"""
        self.logger.info("⚙️ Configuration Summary:")
        if hasattr(config, 'cosmos') and config.cosmos:
            cosmos_status = "enabled" if config.cosmos.get('enabled') else "disabled"
            self.logger.info(f"  Cosmos DB: {cosmos_status}")
            if config.cosmos.get('enabled'):
                self.logger.info(f"  Database: {config.cosmos.get('database', 'unknown')}")
                
        if hasattr(config, 'storage'):
            self.logger.info(f"  Storage Account: {config.storage.account_url}")
            self.logger.info(f"  Recordings Container: {config.storage.recordings_container}")
    
    def finish_startup(self):
        """Complete startup logging with summary"""
        if self._startup_start:
            total_time = (time.time() - self._startup_start) * 1000
            self.logger.info(f"🎉 Application startup completed in {total_time:.1f}ms")
        
        self.di_container.log_dependency_graph()
        self.di_container.log_startup_summary()


# Global startup logger instance
_startup_logger: Optional[StartupLogger] = None
_startup_lock = Lock()


def get_startup_logger() -> StartupLogger:
    """Get the global startup logger instance"""
    global _startup_logger
    if _startup_logger is None:
        with _startup_lock:
            if _startup_logger is None:
                logger = logging.getLogger("startup")
                _startup_logger = StartupLogger(logger)
    return _startup_logger


def log_service_creation(service_name: str, 
                        service_type: str = "singleton",
                        dependencies: List[str] = None,
                        instance_id: str = None) -> ServiceMetadata:
    """Convenience function to log service creation"""
    startup_logger = get_startup_logger()
    return startup_logger.di_container.register_service_creation(
        service_name, service_type, dependencies, instance_id
    )


def log_service_ready(service_name: str, 
                     instance_id: str = None,
                     available: bool = True,
                     error: str = None):
    """Convenience function to log service completion"""
    startup_logger = get_startup_logger()
    startup_logger.di_container.mark_service_created(
        service_name, instance_id, available, error
    )
