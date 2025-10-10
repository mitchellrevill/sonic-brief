# Sonic Brief Backend API

**An AI-powered audio transcription and analysis platform built with FastAPI**

Sonic Brief is a production-ready audio processing platform that transcribes meetings, calls, and recordings, then generates intelligent summaries and insights using Azure OpenAI. The backend handles authentication, file processing, job management, and integrates with Azure Functions for serverless audio processing.

---

## 🏗️ System Architecture

### Technology Stack

- **Web Framework**: FastAPI (Python 3.11+)
- **Database**: Azure Cosmos DB (NoSQL)
- **Storage**: Azure Blob Storage  
- **Authentication**: JWT + Microsoft SSO (MSAL) with cryptographic token validation
- **AI/ML**: Azure OpenAI (GPT-4) + Azure Speech Services
- **Processing**: Azure Functions (serverless audio pipeline)
- **Monitoring**: Application Insights, structured logging

### 🔒 Security Features

- **Token Validation**: Cryptographic verification of Microsoft Azure AD tokens using JWKS
- **Tenant Isolation**: Multi-tenant protection - only accepts tokens from authorized Azure AD tenant
- **Audience Validation**: Ensures tokens are issued specifically for this application
- **CORS Protection**: Restricts API access to authorized frontend domains only
- **Rate Limiting**: Built-in protection against abuse and DDoS
- **Input Validation**: SQL/NoSQL injection, XSS, and path traversal prevention
- **Audit Logging**: Complete audit trail of authentication and sensitive operations

See [SECURITY_CONFIGURATION.md](../SECURITY_CONFIGURATION.md) for detailed security documentation.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│              Static Web App + MSAL Auth                      │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS + JWT
┌──────────────────────▼──────────────────────────────────────┐
│                   FastAPI Backend API                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Router  │  │ Jobs Router  │  │Analytics Rtr │      │
│  │ - Login/SSO  │  │ - Upload     │  │ - Usage Stats│      │
│  │ - Users      │  │ - Transcribe │  │ - Exports    │      │
│  │ - Permissions│  │ - Analyze    │  │              │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────▼──────────────────▼──────────────────▼───────┐    │
│  │         Dependency Injection Container              │    │
│  │  CosmosService │ StorageService │ JobService       │    │
│  └──────┬──────────────────┬──────────────────┬───────┘    │
└─────────┼──────────────────┼──────────────────┼────────────┘
          │                  │                  │
┌─────────▼─────┐  ┌─────────▼─────┐  ┌────────▼────────────┐
│  Cosmos DB    │  │ Blob Storage  │  │ Azure Functions     │
│  - Users      │  │ - Audio files │  │ - Audio Processing  │
│  - Jobs       │  │ - Transcripts │  │ - Speech-to-Text   │
│  - Analytics  │  │               │  │ - AI Analysis      │
│  - Audit Logs │  │               │  │ - OpenAI Integration│
└───────────────┘  └───────────────┘  └─────────────────────┘
```

---

## 🚀 Core Features

### 1. **Authentication & Authorization**
- **JWT-based authentication** with secure token management
- **Microsoft SSO integration** (Azure AD/Entra ID)
- **Hierarchical permission system**: User → Editor → Admin
- **Session tracking** for security auditing

### 2. **Audio Processing Pipeline**
- **File upload** with validation (MP3, WAV, M4A, WebM)
- **Azure Functions integration** for serverless transcription
- **Async job processing** with status tracking
- **Blob storage** for audio files and results

### 3. **AI-Powered Analysis**
- **Azure OpenAI integration** (GPT-4) for content analysis
- **Customizable prompts** for different analysis types
- **Refinement capabilities** - iterative analysis improvements
- **Talking points extraction** from transcriptions

### 4. **User Management**
- **Role-based access control** (RBAC)
- **Permission hierarchy** with inheritance
- **Resource sharing** (jobs can be shared between users)
- **Capability management** (feature flags per user)

### 5. **Analytics & Monitoring**
- **Usage tracking** (processing time, storage, API calls)
- **System health monitoring** with startup validation
- **Audit logging** for compliance
- **Export capabilities** (CSV, JSON)

---

## 🔄 Request Processing Flow

### Typical API Request Path

```
1. Client Request → CORS Middleware
   ├─ Validates origin
   └─ Sets security headers

2. Session Tracking Middleware  
   ├─ Extracts user session from JWT
   ├─ Tracks activity for analytics
   └─ Logs for audit trail

3. Route Handler (FastAPI)
   ├─ Dependency Injection
   │  ├─ Authentication (get_current_user)
   │  ├─ Service injection (JobService, CosmosService, etc.)
   │  └─ Error handling (ErrorHandler)
   │
   ├─ Permission Checks
   │  ├─ Hierarchical permission validation
   │  ├─ Resource ownership verification
   │  └─ Shared access evaluation
   │
   ├─ Business Logic Execution
   │  ├─ Database queries (Cosmos DB)
   │  ├─ Blob storage operations
   │  ├─ Azure Functions calls (async processing)
   │  └─ OpenAI API calls (analysis)
   │
   └─ Response Formation
      ├─ Success: 200/201/204 with data
      └─ Error: ApplicationError → HTTP error response

4. Response → Client
```

---

## 🔐 Permission System

### Hierarchical Levels

```python
USER (Level 1)
├─ View own resources
├─ Upload files
└─ Basic operations

EDITOR (Level 2 - inherits USER)
├─ Edit shared resources
├─ Modify analyses
└─ Advanced features

ADMIN (Level 3 - inherits EDITOR)
├─ Manage all users
├─ Access all resources
├─ System configuration
└─ Delete any resource
```

### Permission Evaluation Logic

```python
# Hierarchical check
if user.permission_level >= required_level:
    return True

# Ownership check  
if resource.owner_id == user.id:
    return True

# Sharing check
if user.id in resource.shared_with:
    return True

return False  # Access denied
```

---

## 📦 Service Layer

### Core Services

| Service | Purpose | Dependencies |
|---------|---------|--------------|
| **CosmosService** | Database operations | Azure Cosmos DB SDK |
| **StorageService** | Blob storage operations | Azure Storage SDK |
| **JobService** | Job lifecycle management | CosmosService, StorageService |
| **AnalyticsService** | Usage tracking & reporting | CosmosService |
| **SessionTrackingService** | User session management | CosmosService |
| **AuditLoggingService** | Security audit trail | CosmosService |
| **AuthenticationService** | JWT + SSO handling | CosmosService |
| **BackgroundService** | Azure Functions integration | HTTP Client, Circuit Breaker |
| **PromptService** | AI prompt management | CosmosService, OpenAI |
| **ExportService** | Data export (CSV/JSON) | CosmosService |
| **SystemHealthService** | Health checks & monitoring | All services |

---

## 🛣️ API Routes

### Authentication (`/api/auth`)
- `POST /login` - Email/password authentication
- `POST /microsoft-sso` - Microsoft SSO authentication  
- `POST /register` - New user registration
- `GET /me` - Current user info
- `POST /logout` - Session termination

### Jobs (`/api/jobs`)
- `POST /jobs` - Upload audio file and create job
- `GET /jobs` - List user's jobs (with filtering)
- `GET /jobs/{id}` - Get job details
- `GET /jobs/{id}/transcription` - Get transcription results
- `PATCH /jobs/{id}` - Update job metadata
- `DELETE /jobs/{id}` - Soft delete job
- `POST /jobs/{id}/restore` - Restore deleted job
- `POST /jobs/{id}/refine` - AI refinement request
- `GET /jobs/{id}/refinements` - List refinements

### User Management (`/api/auth/users`)
- `GET /users` - List users (Admin only)
- `GET /users/{id}` - Get user by ID
- `PATCH /users/{id}` - Update user
- `PATCH /users/{id}/permission` - Change permission level (Admin only)
- `DELETE /users/{id}` - Delete user (Admin only)

### Analytics (`/api/analytics`)
- `GET /analytics/user` - User-specific usage stats
- `GET /analytics/system` - System-wide stats (Admin only)
- `POST /analytics/export` - Export analytics data

### Prompts (`/api/prompts`)
- `GET /prompts` - List prompt templates
- `GET /prompts/{id}` - Get prompt template
- `POST /prompts` - Create custom prompt (Editor+)
- `PATCH /prompts/{id}` - Update prompt (Editor+)
- `DELETE /prompts/{id}` - Delete prompt (Admin only)

### System (`/api/system`)
- `GET /health` - System health check (Admin only)
- Root `/` - API information and endpoints

---

## 🔧 Dependency Injection

### FastAPI DI Pattern

Services use FastAPI's built-in dependency injection:

```python
# Service provider function
def get_cosmos_service() -> CosmosService:
    """Singleton CosmosDB service"""
    return _cosmos_service_instance

# Usage in route handler
@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    current_user: Dict = Depends(get_current_user),  # Auth DI
    job_service: JobService = Depends(get_job_service),  # Service DI
    error_handler: ErrorHandler = Depends(get_error_handler)  # Error DI
):
    """Get job with automatic dependency injection"""
    # All dependencies are automatically resolved by FastAPI
    ...
```

### Service Lifecycle

1. **Startup**: Services initialized in `lifespan()` context manager
2. **Request**: FastAPI injects dependencies as needed
3. **Caching**: Singleton services cached for performance
4. **Shutdown**: Graceful cleanup of connections

---

## 🔥 Error Handling

### Structured Error System

```python
# Base application error
class ApplicationError(Exception):
    def __init__(self, message: str, error_code: ErrorCode, 
                 status_code: int, details: Dict = None)

# Specific error types
AuthenticationError   # 401 - Invalid credentials
PermissionError       # 403 - Access denied
ResourceNotFoundError # 404 - Resource doesn't exist
ResourceNotReadyError # 409 - Processing not complete
ValidationError       # 400 - Invalid input
```

All errors are handled by `ErrorHandler` and converted to proper HTTP responses.

---

## 🧪 Testing & Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (see .env.example)
export AZURE_COSMOS_ENDPOINT="..."
export AZURE_COSMOS_KEY="..."
# ... other variables

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Strategy

- **Unit tests**: Service layer with mocked dependencies
- **Integration tests**: Full request/response cycles
- **Dependency overrides**: FastAPI's `app.dependency_overrides` for mocking

```python
# Example test setup
app.dependency_overrides[get_cosmos_service] = lambda: MockCosmosService()
```

---

## 📁 Project Structure

```
backend_app/
├── app/
│   ├── main.py                    # Application entry point
│   ├── routers/                   # API endpoints
│   │   ├── auth/                  # Authentication & users
│   │   ├── jobs/                  # Job management
│   │   ├── analytics/             # Analytics & reporting
│   │   ├── prompts/               # Prompt templates
│   │   └── system/                # Health & monitoring
│   ├── services/                  # Business logic layer
│   │   ├── jobs/                  # Job processing services
│   │   ├── storage/               # Blob storage services
│   │   ├── monitoring/            # Health & session tracking
│   │   └── prompts/               # AI prompt services
│   ├── core/                      # Core infrastructure
│   │   ├── dependencies.py        # DI container
│   │   ├── config.py              # Configuration
│   │   ├── errors/                # Error handling
│   │   └── health.py              # Startup validation
│   ├── models/                    # Pydantic models
│   ├── middleware/                # Request/response middleware
│   └── utils/                     # Utility functions
├── tests/                         # Test suite
└── requirements.txt               # Python dependencies
```

---

## 🚀 Deployment

The application is designed for Azure deployment:

- **Azure App Service**: Host the FastAPI backend
- **Azure Cosmos DB**: Primary database
- **Azure Blob Storage**: File storage
- **Azure Functions**: Audio processing pipeline
- **Azure OpenAI**: AI analysis
- **Application Insights**: Monitoring and logging

### Environment Variables Required

```bash
# Database
AZURE_COSMOS_ENDPOINT
AZURE_COSMOS_KEY
AZURE_COSMOS_DATABASE_NAME

# Storage
AZURE_STORAGE_ACCOUNT_NAME
AZURE_STORAGE_ACCOUNT_KEY
AZURE_STORAGE_CONTAINER_NAME

# Azure Functions
AZURE_FUNCTIONS_BASE_URL
AZURE_FUNCTION_APP_KEY

# OpenAI
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_KEY
AZURE_OPENAI_DEPLOYMENT_NAME

# Authentication
JWT_SECRET_KEY
JWT_ALGORITHM
```

---

## 📚 Key Concepts

### 1. **Lifespan Management**
Application uses FastAPI's `lifespan` context manager for startup/shutdown logic, including service initialization and dependency validation.

### 2. **Circuit Breaker Pattern**
Azure Functions calls use circuit breaker to prevent cascading failures when external services are unavailable.

### 3. **Lazy Loading**
Expensive resources (database connections, Azure clients) are initialized on first use, not at startup.

### 4. **Fail-Fast Validation**
Startup validation checks critical dependencies (Cosmos DB, Storage) before accepting requests.

### 5. **Structured Logging**
All services use structured logging with correlation IDs for request tracing and debugging.

---

## 🤝 Contributing

When adding new features:

1. **Define service interface** in `services/interfaces.py`
2. **Implement service** following existing patterns
3. **Add DI provider** in `core/dependencies.py`
4. **Create router** in appropriate domain folder
5. **Add tests** with mocked dependencies
6. **Update this README** with new endpoints/services

---

## 📞 Support

For issues or questions:
- Check logs in Application Insights
- Review startup validation errors
- Verify Azure service connectivity
- Confirm environment variables are set correctly
