"""
Memory Diagnostics Service - Optional memory monitoring for debugging

This service handles ONLY memory diagnostics and monitoring:
- Memory usage tracking
- Process memory information
- Optional memory snapshots

This was extracted from the middleware to maintain separation of concerns.
"""

import logging
import os
import platform
import gc
from typing import Dict, Any, Optional

from ...utils.logging_config import get_logger

# Optional memory tooling: prefer psutil when available; fallback to tracemalloc for Python-level
try:
    import psutil
except ImportError:
    psutil = None

try:
    import tracemalloc
except ImportError:
    tracemalloc = None


class MemoryDiagnosticsService:
    """
    Optional service for memory diagnostics and monitoring.
    
    This service provides memory usage tracking and debugging capabilities.
    It's completely optional and doesn't affect core application functionality.
    
    Responsibilities:
    - Track process memory usage
    - Provide memory snapshots for debugging
    - Monitor memory allocation patterns
    
    NOT responsible for:
    - Session tracking
    - Audit logging
    - Business logic
    """
    
    def __init__(self, enable_diagnostics: bool = None, pending_threshold: int = 200):
        self.logger = get_logger(__name__)
        
        # Enable diagnostics based on environment variable if not explicitly set
        if enable_diagnostics is None:
            enable_diagnostics = os.getenv("ENABLE_SESSION_MEMORY_DIAG", "false").lower() in ("1", "true", "yes")
        
        self.enable_diagnostics = enable_diagnostics
        self.pending_threshold = pending_threshold
        
        if self.enable_diagnostics:
            self.logger.info("🧭 Memory diagnostics service enabled")
            self._initialize_tracemalloc()
        else:
            self.logger.debug("Memory diagnostics service disabled")
    
    def _initialize_tracemalloc(self) -> None:
        """Initialize tracemalloc if available for Python allocation tracking"""
        if tracemalloc and not tracemalloc.is_tracing():
            try:
                tracemalloc.start()
                self.logger.debug("tracemalloc started for Python allocation tracking")
            except Exception as e:
                self.logger.debug(f"Could not start tracemalloc: {e}")
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Collect memory information from the running process.
        
        Prefers psutil (RSS/VMS). Falls back to tracemalloc snapshot for Python-level allocations.
        
        Returns:
            Dictionary containing memory information
        """
        if not self.enable_diagnostics:
            return {"diagnostics_enabled": False}
        
        info: Dict[str, Any] = {
            "platform": platform.system(),
            "diagnostics_enabled": True
        }
        
        try:
            pid = os.getpid()
            info["pid"] = pid
        except Exception:
            info["pid"] = None
        
        # psutil: system-level process memory
        if self._get_psutil_memory_info(info):
            return info
        
        # tracemalloc: Python allocations fallback
        self._get_tracemalloc_memory_info(info)
        return info
    
    def _get_psutil_memory_info(self, info: Dict[str, Any]) -> bool:
        """
        Get memory information using psutil.
        
        Args:
            info: Dictionary to update with memory information
            
        Returns:
            True if successful, False if psutil unavailable or failed
        """
        try:
            if not psutil:
                return False
            
            p = psutil.Process(os.getpid())
            mem = p.memory_info()
            info.update({
                "rss": getattr(mem, "rss", None),
                "vms": getattr(mem, "vms", None),
                "uss": getattr(mem, "uss", None) if hasattr(mem, "uss") else None,
                "python_objs": None,
                "source": "psutil"
            })
            return True
        except Exception as e:
            self.logger.debug(f"psutil memory read failed: {e}")
            return False
    
    def _get_tracemalloc_memory_info(self, info: Dict[str, Any]) -> None:
        """
        Get memory information using tracemalloc.
        
        Args:
            info: Dictionary to update with memory information
        """
        try:
            if not tracemalloc or not tracemalloc.is_tracing():
                info.update({
                    "rss": None,
                    "vms": None,
                    "uss": None,
                    "python_objs": None,
                    "source": "tracemalloc_unavailable"
                })
                return
            
            snapshot = tracemalloc.take_snapshot()
            stats = snapshot.statistics('filename')
            top = stats[0] if stats else None
            info.update({
                "rss": None,
                "vms": None,
                "uss": None,
                "python_objs": len(stats),
                "top_alloc_file": getattr(top, "traceback", None),
                "source": "tracemalloc"
            })
        except Exception as e:
            self.logger.debug(f"tracemalloc memory read failed: {e}")
            info.update({
                "rss": None,
                "vms": None,
                "uss": None,
                "python_objs": None,
                "source": "tracemalloc_error"
            })
    
    def log_memory_snapshot(self, label: str) -> None:
        """
        Log a memory snapshot with the given label.
        
        Args:
            label: Description of when/why this snapshot was taken
        """
        if not self.enable_diagnostics:
            return
        
        try:
            memory_info = self.get_memory_info()
            self.logger.debug(f"Memory snapshot [{label}]: {memory_info}")
        except Exception as e:
            self.logger.debug(f"Failed to capture memory snapshot for [{label}]: {e}")
    
    def check_pending_threshold(self, pending_count: int) -> None:
        """
        Check if pending operations exceed threshold and log warning.
        
        Args:
            pending_count: Number of pending operations
        """
        if not self.enable_diagnostics:
            return
        
        if pending_count > self.pending_threshold:
            memory_info = self.get_memory_info()
            self.logger.warning(
                f"High pending operations count: {pending_count} "
                f"(threshold: {self.pending_threshold}). Memory: {memory_info}"
            )
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """
        Force garbage collection and return collection statistics.
        
        Returns:
            Dictionary with garbage collection results
        """
        if not self.enable_diagnostics:
            return {"diagnostics_enabled": False}
        
        try:
            before_memory = self.get_memory_info()
            collected = gc.collect()
            after_memory = self.get_memory_info()
            
            return {
                "collected_objects": collected,
                "memory_before": before_memory,
                "memory_after": after_memory,
                "diagnostics_enabled": True
            }
        except Exception as e:
            self.logger.error(f"Failed to perform garbage collection: {e}")
            return {"error": str(e), "diagnostics_enabled": True}
    
    def get_gc_stats(self) -> Dict[str, Any]:
        """
        Get garbage collection statistics.
        
        Returns:
            Dictionary with GC statistics
        """
        if not self.enable_diagnostics:
            return {"diagnostics_enabled": False}
        
        try:
            return {
                "gc_counts": gc.get_count(),
                "gc_thresholds": gc.get_threshold(),
                "diagnostics_enabled": True
            }
        except Exception as e:
            self.logger.error(f"Failed to get GC stats: {e}")
            return {"error": str(e), "diagnostics_enabled": True}