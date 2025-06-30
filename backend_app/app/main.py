import logging
import sys
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables first
load_dotenv()

# Import FastAPI and routers after environment is configured
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, upload, prompts, analytics
from app.routers import logout  # Add this import
from fastapi import Request
from azure.identity import DefaultAzureCredential

# Import services for initialization
from app.core.config import AppConfig
from app.services.storage_service import StorageService
from app.services.background_processing_service import initialize_background_service, cleanup_background_service

# Import improved logging utilities
from app.utils.logging_config import setup_application_logging, log_startup_step, log_completion, log_error_with_context

default_credential = DefaultAzureCredential()

# Setup improved logging configuration
logger = setup_application_logging(level="INFO", force_flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services on startup
    logger.info("🚀 Starting Sonic Brief API application...")
    
    try:
        # Initialize configuration
        log_startup_step("Initializing application configuration", 1, 3, logger)
        config = AppConfig()
        log_completion("Configuration initialized", logger)
        
        # Initialize storage service
        log_startup_step("Initializing storage service", 2, 3, logger)
        storage_service = StorageService(config)
        log_completion("Storage service initialized", logger)
        
        # Initialize background processing service
        log_startup_step("Initializing background processing", 3, 3, logger)
        initialize_background_service(storage_service, config)
        log_completion("Background processing initialized", logger)
        
        logger.info("🎉 Sonic Brief API is ready and listening for requests!")
        
    except Exception as e:
        log_error_with_context(e, "Application startup failed", logger)
        raise
    
    yield
    
    # Cleanup on shutdown
    logger.info("🔄 Shutting down Sonic Brief API...")
    try:
        await cleanup_background_service()
        log_completion("Services cleaned up successfully", logger)
    except Exception as e:
        log_error_with_context(e, "Error during cleanup", logger)
    
    logger.info("👋 Sonic Brief API shutdown complete")
    sys.stdout.flush()


app = FastAPI(lifespan=lifespan)

# Configure CORS first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with their own prefixes
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(prompts.router)
app.include_router(analytics.router)
app.include_router(logout.router)  # Add this line


@app.get("/")
async def root():
    logger.info("✓ Root endpoint called - API is responsive")
    return {
        "message": "Audio Summarization API", 
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/echo")
async def echo_request():
    """Simple echo endpoint that returns the request data"""
    logger.info("✓ Echo endpoint called")
    return {
        "message": "Echo successful", 
        "timestamp": datetime.now().isoformat()
    }
