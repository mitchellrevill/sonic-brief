from .jobs_router import router as jobs_router
from .sharing_router import router as sharing_router
from .analysis_router import router as analysis_router
from .admin_router import router as admin_router

# Register routers in an order that ensures static routes like '/shared' are
# registered before parameterized routes like '/{job_id}' which could
# accidentally capture static paths. Put sharing_router first.
all_job_routers = [sharing_router, jobs_router, analysis_router, admin_router]

__all__ = ["jobs_router", "sharing_router", "analysis_router", "admin_router", "all_job_routers"]
