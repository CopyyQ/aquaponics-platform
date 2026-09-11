"""Deprecated database import shim.

New code must import from :mod:`app.db.base` or :mod:`app.db.session`.
"""

from app.db.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.session import AsyncSessionLocal, async_session_factory, engine, get_db, get_session

__all__ = [
    "AsyncSessionLocal",
    "Base",
    "SoftDeleteMixin",
    "TimestampMixin",
    "async_session_factory",
    "engine",
    "get_db",
    "get_session",
]
