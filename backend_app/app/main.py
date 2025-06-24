import logging
import sys
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Import FastAPI and routers after environment is configured
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, upload, prompts
from app.routers import logout  # Add this import
from fastapi import Request
from azure.identity import DefaultAzureCredential

# Import services for initialization
from app.core.config import AppConfig
from app.services.storage_service import StorageService
from app.services.background_processing_service import initialize_background_service, cleanup_background_service

default_credential = DefaultAzureCredential()

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services on startup
    logger.info("Initializing application services...")
    
    try:
        # Initialize configuration
        config = AppConfig()
        
        # Initialize storage service
        storage_service = StorageService(config)
        
        # Initialize background processing service
        initialize_background_service(storage_service, config)
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise
    
    logger.debug("Available routes:")
    yield
    
    # Cleanup on shutdown
    logger.info("Cleaning up application services...")
    try:
        await cleanup_background_service()
        logger.info("Services cleaned up successfully")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


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
app.include_router(logout.router)  # Add this line


@app.get("/")
async def root():
    logger.debug("Root endpoint called")
    return {"message": "Audio Summarization API"}


@app.get("/echo")
async def echo_request():
    """Simple echo endpoint that returns the request data"""
    # data = request.json()
    # logger.debug(f"Received data: {data}")
    return {"message": "Echo successful"}
