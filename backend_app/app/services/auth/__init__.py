"""Authentication services exports.

This package now exposes only the audit service. Permission logic has been
refactored into `app.models.permissions` and `app.core.permissions`.

NOTE: Audit services are being refactored. The new AuditLoggingService
is available at app.services.audit_logging_service.
"""

# TODO: Implement proper auth-specific audit service if needed
# For now, use the new modular AuditLoggingService instead

__all__ = [
    # 'AuditService',  # Commented out until proper implementation
]
