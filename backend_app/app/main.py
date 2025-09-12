import logging
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables early
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Use relative imports so the module is importable when run as a package
from .routers.analytics import analytics_router
from .routers.system import system_router
from .routers.content import content_router
from .routers.auth import auth_router

from .core.config import get_app_config
from .services.storage import StorageService
from .services.processing.background_service import initialize_background_service

from .utils.logging_config import setup_application_logging, log_startup_step, log_completion, log_error_with_context
from .core.settings import get_settings
from .middleware.session_tracking_middleware import SessionTrackingMiddleware

logger = setup_application_logging(level="INFO", force_flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Sonic Brief API application...")
    log_startup_step("Initializing application configuration", 1, 3, logger)
    config = get_app_config()
    log_completion("Configuration initialized", logger)

    log_startup_step("Initializing storage service", 2, 3, logger)
    storage_service = StorageService(config)
    log_completion("Storage service initialized", logger)

    log_startup_step("Initializing background processing", 3, 3, logger)
    initialize_background_service(storage_service, config)
    log_completion("Background processing initialized", logger)

    yield


# Instantiate the FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Configure CORS with security best practices
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Add session tracking middleware
app.add_middleware(
    SessionTrackingMiddleware,
    heartbeat_interval_minutes=5,
)

# Include routers
app.include_router(auth_router)
app.include_router(content_router)
app.include_router(analytics_router)
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
