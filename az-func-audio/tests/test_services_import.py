import importlib
import pytest

# List of service modules to check
SERVICE_MODULES = [
    "services.analysis_service",
    "services.cosmos_service",
    "services.file_processing_service",
    "services.storage_service",
    "services.transcription_service",
]

def test_services_importable():
    """Test that all service modules can be imported (compile check)."""
    for module_name in SERVICE_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            pytest.fail(f"Failed to import {module_name}: {e}")
