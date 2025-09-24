"""
Analytics Router Module - Central import and routing registration for analytics domain
Provides unified access to all analytics-related router endpoints
"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Defensive imports: don't fail app startup if a specific analytics submodule
# is missing during migration. Import what is available and include it.
user_analytics_router = None
system_analytics_router = None
export_router = None

try:
    from .user_analytics import router as user_analytics_router
except Exception as e:
    logger.warning("user_analytics router unavailable: %s", e)


try:
    from .export import router as export_router
except Exception as e:
    logger.warning("export router unavailable: %s", e)

# Create main analytics router. Do not set a parent tag here so included
# subrouters keep their own tags. Setting tags on the parent caused included
# routes to inherit both the parent and child tags, producing duplicate
# groups in the OpenAPI/Swagger UI.
analytics_router = APIRouter(prefix="/api/analytics")

# Include only routers that imported successfully
if user_analytics_router is not None:
    analytics_router.include_router(user_analytics_router, prefix="")

if export_router is not None:
    analytics_router.include_router(export_router, prefix="")

__all__ = ["analytics_router"]
