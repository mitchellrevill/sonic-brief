# Backend Test Suite - Phase 1 Critical Services

This directory contains comprehensive unit tests for the Sonic Brief backend application, focusing on Phase 1 Critical Services as defined in `TESTING_STRATEGY.md`.

## 📋 Overview

The test suite covers the following Phase 1 Critical Services with 90%+ coverage target:

1. **CosmosService** (`test_cosmos_service.py`) - Database operations and connectivity
2. **AuthenticationService** (`test_authentication_service.py`) - JWT validation and user authentication  
3. **JobService** (`test_job_service.py`) - Job lifecycle and file management

## 🚀 Quick Start

### Install Dependencies

```powershell
# Install test dependencies
pip install -r requirements-test.txt
```

### Run Tests

```powershell
# Navigate to backend_app directory
cd backend_app

# Run smoke tests (verify setup)
pytest tests/test_smoke.py -v

# Run all Phase 1 tests with coverage
pytest tests/test_cosmos_service.py tests/test_authentication_service.py tests/test_job_service.py --cov=app --cov-report=html -v

# Or use the convenient PowerShell runner
.\tests\run_tests.ps1 -Phase1Only

# Run all tests
pytest --cov=app --cov-report=html

# Open coverage report
start htmlcov/index.html
```

## 📁 Test Structure

```
tests/
├── conftest.py                        # Shared fixtures and configuration
├── test_smoke.py                      # Infrastructure verification tests
├── test_cosmos_service.py             # CosmosService unit tests (90%+ coverage)
├── test_authentication_service.py     # AuthenticationService unit tests (90%+ coverage)
├── test_job_service.py                # JobService unit tests (90%+ coverage)
└── run_tests.ps1                      # PowerShell test runner script
```

## 🧪 Test Coverage

### CosmosService Tests (`test_cosmos_service.py`)

**Coverage Areas:**
- ✅ Connection and availability checks
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Error handling (timeouts, permissions, connection errors)
- ✅ User operations (get, create, update, delete)
- ✅ Job operations (get, create, update, query)
- ✅ Container access and caching
- ✅ Client initialization scenarios

**Test Classes:**
- `TestCosmosServiceAvailability` - 5 tests
- `TestCosmosServiceJobOperations` - 6 tests
- `TestCosmosServiceUserOperations` - 8 tests
- `TestCosmosServiceErrorHandling` - 6 tests
- `TestCosmosServiceContainerAccess` - 5 tests
- `TestCosmosServiceClientInitialization` - 4 tests

**Total: 34+ tests**

### AuthenticationService Tests (`test_authentication_service.py`)

**Coverage Areas:**
- ✅ JWT token validation and decoding
- ✅ Token expiration handling
- ✅ User extraction from requests
- ✅ IP address extraction (X-Forwarded-For, X-Real-IP)
- ✅ User agent parsing (Windows, macOS, Linux, iOS, Android)
- ✅ Session management
- ✅ Error handling for malformed/expired tokens

**Test Classes:**
- `TestTokenValidation` - 6 tests
- `TestUserExtraction` - 7 tests
- `TestSessionManagement` - 2 tests
- `TestTokenExpiration` - 4 tests
- `TestIPAddressExtraction` - 5 tests
- `TestUserAgentExtraction` - 7 tests
- `TestAuthenticationServiceInitialization` - 3 tests
- `TestAuthenticationEdgeCases` - 3 tests

**Total: 37+ tests**

### JobService Tests (`test_job_service.py`)

**Coverage Areas:**
- ✅ Job lifecycle (create, retrieve, update)
- ✅ File upload and storage integration
- ✅ File URL enrichment with SAS tokens
- ✅ Job querying and filtering
- ✅ Status management
- ✅ Error handling (storage failures, Cosmos errors)
- ✅ Data validation

**Test Classes:**
- `TestJobRetrieval` - 4 tests
- `TestJobCreation` - 4 tests
- `TestJobStatusManagement` - 3 tests
- `TestJobFileEnrichment` - 6 tests
- `TestJobDataValidation` - 3 tests
- `TestJobServiceLifecycle` - 2 tests
- `TestJobServiceErrorHandling` - 4 tests
- `TestJobQueryOperations` - 3 tests
- `TestJobFilePathParsing` - 3 tests

**Total: 32+ tests**

## 🔧 Fixtures and Test Utilities

### Common Fixtures (`conftest.py`)

**Configuration:**
- `mock_config` - Mock application configuration
- `mock_jwt_secret` - JWT secret for token testing

**CosmosDB:**
- `cosmos_service` - Fully mocked CosmosService instance
- `mock_cosmos_client` - Mock Cosmos client
- `mock_cosmos_container` - Mock container with CRUD operations
- `mock_cosmos_database` - Mock database reference

**Authentication:**
- `authentication_service` - AuthenticationService instance
- `valid_jwt_token` - Valid JWT token for testing
- `expired_jwt_token` - Expired JWT token for testing
- `mock_request` - Mock FastAPI request object

**Job Management:**
- `job_service` - JobService instance with mocked dependencies
- `mock_storage_service` - Mock StorageService for file operations

**Sample Data:**
- `sample_user` - Sample user document
- `sample_admin_user` - Sample admin user document
- `sample_job` - Sample job document
- `sample_completed_job` - Sample completed job with all fields

**Utilities:**
- `cosmos_error_factory` - Helper to create Cosmos errors

## 📊 Running Specific Test Suites

```powershell
# Run only CosmosService tests
pytest tests/test_cosmos_service.py -v

# Run only AuthenticationService tests
pytest tests/test_authentication_service.py -v

# Run only JobService tests
pytest tests/test_job_service.py -v

# Run tests with specific marker
pytest -m asyncio -v

# Run tests matching pattern
pytest -k "test_get_job" -v

# Run with detailed output
pytest -vv -s

# Run and stop on first failure
pytest -x

# Run with coverage for specific module
pytest --cov=app.core.dependencies --cov-report=term-missing -v
```

## 🎯 PowerShell Test Runner Options

The `run_tests.ps1` script provides convenient options:

```powershell
# Run smoke tests only
.\tests\run_tests.ps1 -Smoke

# Run Phase 1 tests with coverage
.\tests\run_tests.ps1 -Phase1Only

# Run all tests with coverage
.\tests\run_tests.ps1 -Coverage

# Run with verbose output
.\tests\run_tests.ps1 -Verbose

# Run tests with specific marker
.\tests\run_tests.ps1 -Marker "asyncio"

# Run specific test path
.\tests\run_tests.ps1 -TestPath "tests/test_cosmos_service.py"
```

## 🐛 Debugging Tests

```powershell
# Run with Python debugger
pytest --pdb

# Run and show local variables on failure
pytest -l

# Run with full traceback
pytest --tb=long

# Run with warnings shown
pytest -W all
```

## 📈 Coverage Goals

| Service | Target Coverage | Current Status |
|---------|----------------|----------------|
| CosmosService | 90%+ | ✅ Comprehensive tests |
| AuthenticationService | 90%+ | ✅ Comprehensive tests |
| JobService | 90%+ | ✅ Comprehensive tests |

## 🔍 Test Categories

Tests are organized by functionality:

- **Happy Path Tests** - Verify correct behavior with valid inputs
- **Error Cases** - Test error handling and edge cases
- **Edge Cases** - Test boundary conditions and unusual inputs
- **Integration Points** - Test interactions between components

## 📝 Writing New Tests

When adding new tests, follow these patterns:

```python
import pytest
from unittest.mock import Mock

class TestYourFeature:
    """Test suite for your feature"""
    
    def test_happy_path(self, fixture_name):
        """Test the happy path scenario"""
        # Arrange
        # Act
        # Assert
        pass
    
    @pytest.mark.asyncio
    async def test_async_operation(self, fixture_name):
        """Test async operations"""
        result = await service.async_method()
        assert result is not None
    
    def test_error_handling(self, fixture_name):
        """Test error handling"""
        with pytest.raises(ExpectedException):
            service.method_that_fails()
```

## 🚨 Common Issues and Solutions

### Issue: Import Errors
**Solution:** Make sure you're in the `backend_app` directory and have installed dependencies:
```powershell
cd backend_app
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Issue: Async Tests Failing
**Solution:** Ensure pytest-asyncio is installed and tests are marked:
```python
@pytest.mark.asyncio
async def test_async_function():
    pass
```

### Issue: Mock Not Working
**Solution:** Check that you're using the correct mock path:
```python
from unittest.mock import Mock, patch

# Mock at the point of use, not definition
with patch('app.services.jobs.job_service.CosmosService') as mock:
    pass
```

## 📚 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## 🎓 Next Steps

After completing Phase 1 tests, proceed to:

1. **Phase 2: Business Logic** - AnalyticsService, JobManagementService, PermissionService
2. **Phase 3: Integration & AI Services** - API integration tests, AI service mocking
3. **Phase 4: Monitoring & Optimization** - Performance tests, load tests

See `TESTING_STRATEGY.md` in the root directory for the complete testing roadmap.
