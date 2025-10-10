import logging
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables early
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Use relative imports so the module is importable when run as a package
from .routers.auth import auth_router
from .routers.prompts import prompts_router
from .routers.jobs import all_job_routers
from .routers.analytics import analytics_router
# from .routers.content import content_router  # Module missing - commented out
from .routers.system import system_router

from .core.config import get_config
from .core.errors import (
    ApplicationError,
    AuthenticationError,
    ErrorCode,
    PermissionError,
    application_error_response,
)
# NOTE: temporarily import only essential services for minimal server
# from .core.dependencies import get_storage_service, get_background_service
# from .core.dependencies import (
#     get_user_service,
#     get_permission_service,
#     get_job_service,
#     get_analytics_service,
#     reset_all_services,
# )
from .core.http_client import startup as http_client_startup, shutdown as http_client_shutdown

from .utils.logging_config import setup_application_logging
from .utils.startup_logging import get_startup_logger
from .core.health import StartupValidator, StartupValidationError

logger = setup_application_logging(level="INFO", force_flush=True)
startup_logger = get_startup_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_logger.start_startup()
    
    # Phase 1: Configuration
    startup_logger.start_phase("configuration", "Initializing application configuration")
    config = get_config()
    startup_logger.log_config_info(config)
    startup_logger.end_phase("configuration")

    # Phase 2: Storage Services  
    startup_logger.start_phase("storage", "Initializing storage services")
    # NOTE: Storage service temporarily disabled for minimal server
    # # Use centralized DI provider to ensure singleton
    # storage_service = get_storage_service(config)
    # # Attach to app.state so routers/middleware can access if needed
    # app.state.storage_service = storage_service
    startup_logger.end_phase("storage")

    # Phase 3: Background Processing
    startup_logger.start_phase("background", "Initializing background processing")
    # NOTE: Background service temporarily disabled for minimal server
    # # Initialize background processing service via DI provider
    # bg = get_background_service(config)
    # app.state.background_service = bg
    startup_logger.end_phase("background")

    # Phase 4: Core Services Warming
    startup_logger.start_phase("services", "Warming core services")
    # Initialize other core singleton services to ensure readiness and
    # warm caches/connections. These will be cached by the DI providers.
    try:
        # Some services depend on CosmosDB; if Cosmos is not available skip warming
        from .core.dependencies import (
            get_cosmos_service, 
            get_session_tracking_service,
            get_audit_logging_service,
            get_authentication_service,
        )
        cosmos_service = get_cosmos_service()
        if hasattr(cosmos_service, "is_available") and not cosmos_service.is_available():
            logger.warning("CosmosDB unavailable during startup; skipping session-tracking middleware configuration")
        else:
            # Services are warmed but middleware is already configured at app startup
            session_tracking_service = get_session_tracking_service()
            audit_logging_service = get_audit_logging_service()
            authentication_service = get_authentication_service()

            logger.info("🔧 Session tracking services warmed successfully")

            # NOTE: Other service initializations temporarily disabled for minimal server
            # analytics_service = get_analytics_service()
            # job_service = get_job_service()
            # permission_service = get_permission_service()
            # user_service = get_user_service()
        startup_logger.end_phase("services")
    except Exception as e:
        logger.error(f"❌ Failed to warm core services: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        startup_logger.end_phase("services")

    # Phase 5: Startup Validation (Fail-Fast Check)
    startup_logger.start_phase("validation", "Validating critical dependencies")
    try:
        from .core.dependencies import get_cosmos_service
        cosmos_service = get_cosmos_service()
        
        # Create validator and run comprehensive checks
        validator = StartupValidator(cosmos_service, config)
        
        # Run validation with fail_fast=True to exit on critical failures
        validation_result = await validator.validate_all(fail_fast=True)
        
        # If we get here, validation passed
        logger.info(f"✅ Startup validation passed: {validation_result.summary()}")
        
        # Log warnings if any
        if validation_result.warnings:
            logger.warning(f"⚠️  {len(validation_result.warnings)} non-critical warnings during startup")
            for warning in validation_result.warnings:
                logger.warning(str(warning))
        
        startup_logger.end_phase("validation")
        
    except StartupValidationError as e:
        # Critical validation failure - log and exit
        logger.critical("💥 STARTUP VALIDATION FAILED - APPLICATION CANNOT START")
        logger.critical(f"Failed {len(e.result.errors)} critical checks:")
        for error in e.result.errors:
            logger.critical(f"  - {error}")
        
        startup_logger.end_phase("validation")
        startup_logger.finish_startup(success=False)
        
        # Exit with error code to signal container orchestrator
        import sys
        sys.exit(1)
        
    except Exception as e:
        # Unexpected error during validation itself
        logger.critical(f"💥 UNEXPECTED ERROR DURING STARTUP VALIDATION: {str(e)}", exc_info=True)
        startup_logger.end_phase("validation")
        startup_logger.finish_startup(success=False)
        
        # Exit with error code
        import sys
        sys.exit(1)

    # Complete startup
    startup_logger.finish_startup()

    # Start shared HTTP client
    try:
        await http_client_startup()
    except Exception:
        logger.exception("Failed to start shared HTTP client")

    yield

    # Shutdown: reset/cleanup services
    try:
        # NOTE: reset_all_services temporarily disabled for minimal server
        # reset_all_services()
        pass
    except Exception:
        logger.exception("Error during service reset on shutdown")

    # Close shared http client
    try:
        await http_client_shutdown()
    except Exception:
        logger.exception("Error closing shared HTTP client")


# Instantiate the FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

from .middleware.session_tracking_middleware import SessionTrackingMiddleware
from .core.dependencies import (
    get_cosmos_service,
    get_session_tracking_service,
    get_audit_logging_service,
    get_authentication_service,
)

# Add session tracking middleware if CosmosDB is available
# Check Cosmos availability before adding middleware since it depends on Cosmos services
cosmos_service = get_cosmos_service()
if hasattr(cosmos_service, "is_available") and cosmos_service.is_available():
    session_tracking_service = get_session_tracking_service()
    audit_logging_service = get_audit_logging_service()
    authentication_service = get_authentication_service()
    
    app.add_middleware(
        SessionTrackingMiddleware,
        session_service=session_tracking_service,
        audit_service=audit_logging_service,
        auth_service=authentication_service,
    )
else:
    logger.warning("CosmosDB unavailable during app initialization; skipping session-tracking middleware configuration")

# Configure CORS with security best practices
config = get_config()

# Configure CORS carefully: when credentials are allowed the Access-Control-Allow-Origin
# header must not be the wildcard '*' — browsers will reject wildcard with credentials.
cors_origins = config.cors_origins_list if config.cors_origins_list else []
allow_origin_regex = None

# SECURITY WARNING: Check for wildcard in production
if cors_origins == ["*"] or "*" in cors_origins:
    import os
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment in ["production", "prod"]:
        logger.critical(
            "🚨 SECURITY RISK: CORS configured with wildcard '*' in production! "
            "This allows ANY website to make authenticated requests to your API. "
            "Set CORS_ORIGINS to your frontend domain(s) immediately."
        )
        # In production, fail fast - don't start with insecure CORS
        import sys
        sys.exit(1)
    else:
        logger.warning(
            "⚠️  CORS configured with wildcard '*' - acceptable for local development only. "
            "Ensure CORS_ORIGINS is set to specific domain(s) before deploying to production."
        )
        # Allow all origins but use a regex so the middleware will echo the request Origin
        # header instead of sending a literal '*'. This is required when allow_credentials=True.
        cors_origins = []
        allow_origin_regex = r".*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Include routers
app.include_router(auth_router)
app.include_router(prompts_router)

# Register all routers exposed by the jobs package
# These routers already declare their own prefixes (e.g. '/api', '/api/jobs', '/api/admin/jobs').
# Do not re-apply the '/api/jobs' prefix here or routes will become '/api/jobs/api/jobs' etc.
for r in all_job_routers:
    app.include_router(r)

app.include_router(analytics_router)
# app.include_router(content_router)  # Module missing - commented out
app.include_router(system_router)


@app.exception_handler(ApplicationError)
async def handle_application_error(request: Request, exc: ApplicationError):
    return application_error_response(exc)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException):
    logger.warning(
        "Handled HTTPException",
        extra={
            "path": str(request.url),
            "status_code": exc.status_code,
        },
    )

    if isinstance(exc.detail, dict) and {"message", "error_code"}.issubset(exc.detail):
        payload = {
            "message": exc.detail["message"],
            "error_code": exc.detail["error_code"],
            "details": exc.detail.get("details", {}),
        }
        return JSONResponse(status_code=exc.status_code, content=payload)

    if exc.status_code == 401:
        error = AuthenticationError()
    elif exc.status_code == 403:
        error = PermissionError()
    elif exc.status_code == 404:
        error = ApplicationError(
            "Resource not found",
            ErrorCode.RESOURCE_NOT_FOUND,
            status_code=exc.status_code,
            details={"path": request.url.path},
        )
    elif 400 <= exc.status_code < 500:
        error = ApplicationError(
            "Request validation failed",
            ErrorCode.INVALID_INPUT,
            status_code=exc.status_code,
        )
    else:
        error = ApplicationError(
            "Internal server error",
            ErrorCode.INTERNAL_ERROR,
            status_code=exc.status_code,
        )

    return application_error_response(error)


@app.exception_handler(Exception)
async def handle_unexpected_exception(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception encountered",
        extra={"path": str(request.url)},
    )

    error = ApplicationError(
        "Internal server error",
        ErrorCode.INTERNAL_ERROR,
        status_code=500,
        details={"path": request.url.path},
    )
    return application_error_response(error)

@app.get("/")
async def root():
    """Get API information and available endpoints"""
    logger.info("✓ Root endpoint called - API is responsive")
    return {
        "name": "Sonic Brief API",
        "description": "Audio Summarization and Analytics API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": "development",  # Could be from config
        "endpoints": {
            "authentication": {
                "login": "POST /api/auth/login",
                "microsoft_sso": "POST /api/auth/microsoft-sso",
                "register": "POST /api/auth/register",
                "me": "GET /api/auth/me"
            },
            "jobs": {
                "upload": "POST /api/jobs/upload",
                "list": "GET /api/jobs",
                "get": "GET /api/jobs/{job_id}",
                "transcription": "GET /api/jobs/{job_id}/transcription"
            },
            "analytics": {
                "user_analytics": "GET /api/analytics/user",
                "system_analytics": "GET /api/analytics/system"
            },
            "system": {
                "health": "GET /api/system/health"
            }
        },
        "documentation": "/docs",
        "health_check": "/api/system/health"
    }


@app.get("/echo")
async def echo_request():
    logger.info("✓ Echo endpoint called")
    return {"message": "Echo successful", "timestamp": datetime.now().isoformat()}
