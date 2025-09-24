import logging
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables early
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Use relative imports so the module is importable when run as a package
from .routers.auth import auth_router
from .routers.prompts import prompts_router
from .routers.jobs import all_job_routers
from .routers.analytics import analytics_router
# from .routers.content import content_router  # Module missing - commented out
from .routers.system import system_router

from .core.config import get_config
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

from .utils.logging_config import setup_application_logging, log_startup_step, log_completion, log_error_with_context
from .utils.startup_logging import get_startup_logger

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
        cfg = get_config()
        from .core.dependencies import (
            get_cosmos_service, 
            get_session_tracking_service,
            get_audit_logging_service,
            get_authentication_service,
        )
        cosmos_service = get_cosmos_service(cfg)
        if hasattr(cosmos_service, "is_available") and not cosmos_service.is_available():
            logger.warning("CosmosDB unavailable during startup; skipping warm for cosmos-dependent services")
            app.state.session_tracking_service = None
            app.state.audit_logging_service = None
            app.state.authentication_service = None
        else:
            # Initialize new modular services for middleware use
            app.state.session_tracking_service = get_session_tracking_service(cosmos_service)
            app.state.audit_logging_service = get_audit_logging_service(cosmos_service)
            app.state.authentication_service = get_authentication_service()
            logger.info("🔧 Modular session services initialized with proper DI")
            logger.info("✅ Session tracking middleware will discover services from app.state automatically")
            
            # NOTE: Other service initializations temporarily disabled for minimal server
            # app.state.analytics_service = get_analytics_service()
            # app.state.job_service = get_job_service()
            # app.state.permission_service = get_permission_service()
            # app.state.user_service = get_user_service()
            pass
        startup_logger.end_phase("services")
    except Exception as e:
        logger.error(f"❌ Failed to warm core services: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        # Ensure session services are None if startup fails
        app.state.session_tracking_service = None
        app.state.audit_logging_service = None
        app.state.authentication_service = None
        startup_logger.end_phase("services")

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

# Add session tracking middleware (configured during startup)
from .middleware.session_tracking_middleware import LazySessionTrackingMiddleware
app.add_middleware(LazySessionTrackingMiddleware)

# Configure CORS with security best practices
config = get_config()

# Configure CORS carefully: when credentials are allowed the Access-Control-Allow-Origin
# header must not be the wildcard '*' — browsers will reject wildcard with credentials.
cors_origins = config.cors_origins_list if config.cors_origins_list else []
allow_origin_regex = None
if cors_origins == ["*"] or "*" in cors_origins:
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

@app.get("/")
async def root():
    logger.info("✓ Root endpoint called - API is responsive")
    return {
        "message": "Audio Summarization API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/echo")
async def echo_request():
    logger.info("✓ Echo endpoint called")
    return {"message": "Echo successful", "timestamp": datetime.now().isoformat()}
