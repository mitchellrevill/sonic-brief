"""
Unit tests for MemoryDiagnosticsService (Phase 3 - Monitoring Services)

Tests cover:
- Memory info collection
- Process memory tracking  
- Diagnostics enable/disable
- Graceful handling of missing dependencies (psutil, tracemalloc)

Coverage target: 90%+ on app/services/monitoring/memory_diagnostics_service.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from app.services.monitoring.memory_diagnostics_service import MemoryDiagnosticsService


# ============================================================================
# Test Class: Service Initialization
# ============================================================================

@pytest.mark.unit
class TestMemoryDiagnosticsInitialization:
    """Test service initialization and configuration"""
    
    def test_init_diagnostics_enabled_explicitly(self):
        """Test initialization with diagnostics explicitly enabled"""
        # Act
        service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Assert
        assert service.enable_diagnostics is True
    
    def test_init_diagnostics_disabled_explicitly(self):
        """Test initialization with diagnostics explicitly disabled"""
        # Act
        service = MemoryDiagnosticsService(enable_diagnostics=False)
        
        # Assert
        assert service.enable_diagnostics is False
    
    def test_init_diagnostics_from_environment_variable(self):
        """Test initialization from environment variable"""
        # Arrange
        with patch.dict(os.environ, {"ENABLE_SESSION_MEMORY_DIAG": "true"}):
            # Act
            service = MemoryDiagnosticsService()
            
            # Assert
            assert service.enable_diagnostics is True
    
    def test_init_diagnostics_default_disabled(self):
        """Test initialization defaults to disabled"""
        # Arrange
        with patch.dict(os.environ, {}, clear=True):
            # Act
            service = MemoryDiagnosticsService()
            
            # Assert
            assert service.enable_diagnostics is False
    
    def test_init_custom_pending_threshold(self):
        """Test initialization with custom pending threshold"""
        # Act
        service = MemoryDiagnosticsService(enable_diagnostics=True, pending_threshold=500)
        
        # Assert
        assert service.pending_threshold == 500


# ============================================================================
# Test Class: Memory Info Collection
# ============================================================================

@pytest.mark.unit
class TestMemoryInfoCollection:
    """Test memory information collection"""
    
    def test_get_memory_info_diagnostics_disabled(self):
        """Test memory info returns minimal info when diagnostics disabled"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=False)
        
        # Act
        result = service.get_memory_info()
        
        # Assert
        assert result["diagnostics_enabled"] is False
        assert len(result) == 1  # Only contains diagnostics_enabled
    
    def test_get_memory_info_with_psutil(self):
        """Test memory info collection with psutil available"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Mock psutil
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 1024 * 1024 * 100  # 100 MB
        mock_memory_info.vms = 1024 * 1024 * 200  # 200 MB
        mock_process.memory_info.return_value = mock_memory_info
        
        with patch('app.services.monitoring.memory_diagnostics_service.psutil') as mock_psutil:
            mock_psutil.Process.return_value = mock_process
            
            # Act
            result = service.get_memory_info()
        
        # Assert
        assert result["diagnostics_enabled"] is True
        assert "platform" in result
        assert "pid" in result
    
    def test_get_memory_info_without_psutil(self):
        """Test memory info collection without psutil"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Mock psutil as None (not available)
        with patch('app.services.monitoring.memory_diagnostics_service.psutil', None):
            # Act
            result = service.get_memory_info()
        
        # Assert
        assert result["diagnostics_enabled"] is True
        assert "platform" in result
    
    def test_get_memory_info_handles_exceptions(self):
        """Test memory info gracefully handles exceptions"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Mock psutil to raise exception
        with patch('app.services.monitoring.memory_diagnostics_service.psutil') as mock_psutil:
            mock_psutil.Process.side_effect = Exception("Process error")
            
            # Act
            result = service.get_memory_info()
        
        # Assert - should still return dict with diagnostics_enabled
        assert result["diagnostics_enabled"] is True


# ============================================================================
# Test Class: Process Memory Tracking
# ============================================================================

@pytest.mark.unit
class TestProcessMemoryTracking:
    """Test process-level memory tracking via get_memory_info"""
    
    def test_memory_info_includes_process_info(self):
        """Test memory info includes process details"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 1024 * 1024 * 150  # 150 MB
        mock_memory_info.vms = 1024 * 1024 * 200  # 200 MB
        mock_process.memory_info.return_value = mock_memory_info
        
        with patch('app.services.monitoring.memory_diagnostics_service.psutil') as mock_psutil:
            mock_psutil.Process.return_value = mock_process
            
            # Act
            result = service.get_memory_info()
        
        # Assert
        assert result["diagnostics_enabled"] is True
        assert "pid" in result


# ============================================================================
# Test Class: Tracemalloc Integration
# ============================================================================

@pytest.mark.unit
class TestTracemalloc:
    """Test tracemalloc integration"""
    
    def test_tracemalloc_initialization(self):
        """Test tracemalloc starts when diagnostics enabled"""
        # Arrange & Act
        with patch('app.services.monitoring.memory_diagnostics_service.tracemalloc') as mock_tracemalloc:
            mock_tracemalloc.is_tracing.return_value = False
            service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Assert
        mock_tracemalloc.start.assert_called_once()
    
    def test_tracemalloc_not_started_when_disabled(self):
        """Test tracemalloc not started when diagnostics disabled"""
        # Arrange & Act
        with patch('app.services.monitoring.memory_diagnostics_service.tracemalloc') as mock_tracemalloc:
            service = MemoryDiagnosticsService(enable_diagnostics=False)
        
        # Assert
        mock_tracemalloc.start.assert_not_called()
    
    def test_tracemalloc_already_tracing(self):
        """Test tracemalloc not restarted if already tracing"""
        # Arrange & Act
        with patch('app.services.monitoring.memory_diagnostics_service.tracemalloc') as mock_tracemalloc:
            mock_tracemalloc.is_tracing.return_value = True
            service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Assert
        mock_tracemalloc.start.assert_not_called()


# ============================================================================
# Test Class: Service Properties
# ============================================================================

@pytest.mark.unit
class TestServiceProperties:
    """Test service properties and state"""
    
    def test_is_diagnostics_enabled(self):
        """Test diagnostics enabled check"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=True)
        
        # Act & Assert
        assert service.enable_diagnostics is True
    
    def test_pending_threshold_property(self):
        """Test pending threshold is set correctly"""
        # Arrange
        service = MemoryDiagnosticsService(enable_diagnostics=True, pending_threshold=300)
        
        # Act & Assert
        assert service.pending_threshold == 300
