"""
Analytics Router Module - Central import and routing registration for analytics domain
Provides unified access to all analytics-related router endpoints
"""
from fastapi import APIRouter
from .user_analytics import router as user_analytics_router
from .system_analytics import router as system_analytics_router
from .debug_analytics import router as debug_analytics_router
from .reports import router as reports_router

# Create main analytics router
analytics_router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Include all analytics domain routers
analytics_router.include_router(user_analytics_router, prefix="", tags=["user-analytics"])
analytics_router.include_router(system_analytics_router, prefix="", tags=["system-analytics"])
analytics_router.include_router(debug_analytics_router, prefix="", tags=["debug-analytics"])
analytics_router.include_router(reports_router, prefix="", tags=["reports"])

# Export individual routers for selective inclusion if needed
__all__ = [
    "analytics_router",
    "user_analytics_router",
    "system_analytics_router", 
    "debug_analytics_router",
    "reports_router"
]
