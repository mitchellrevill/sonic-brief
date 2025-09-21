"""
Top-level services package

This file re-exports commonly used services to provide a single import
surface for application code. Keep this file minimal — prefer importing
subpackages directly in new modules to avoid large import graphs.

Structure:
- app.services.auth (auth related services and routers)
- app.services.content (content-related services: analysis, prompts, talking points)
- app.services.storage (storage helper services)
- app.services.processing (processing pipelines)
"""

from . import prompts as prompts
from . import auth as auth

from .user_service import *
from .password_service import *

# New job-related helpers
from .jobs import JobService
from .jobs import check_job_access, check_job_access_permission, get_user_job_permission

__all__ = [
    'prompts',
    'auth',
    'JobService',
    'check_job_access',
    'check_job_access_permission',
    'get_user_job_permission',
]
