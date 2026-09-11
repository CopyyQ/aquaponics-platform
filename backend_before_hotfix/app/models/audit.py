"""Compatibility import for the renamed AuditLog model module."""

from app.models.audit_log import AuditLog

__all__ = ["AuditLog"]
