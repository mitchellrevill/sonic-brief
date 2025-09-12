"""Authentication services exports.

This package now exposes only the audit service. Permission logic has been
refactored into `app.models.permissions` and `app.core.permissions`.
"""

from .audit_service import AuditService

__all__ = [
    'AuditService',
]
