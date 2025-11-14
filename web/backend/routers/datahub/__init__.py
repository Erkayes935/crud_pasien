"""
Data Hub Routers Module
Handles all data standardization & ingestion routes
"""

from .ui_router import router as ui_router
from .ingestion_router import router as ingestion_router
from .monitor_router import router as monitor_router
from .export_router import router as export_router
from .api_router import router as api_router
from .hybrid_sync_router import router as hybrid_sync_router
from .manual_input_router import router as manual_input_router
from .test_celery_router import router as test_celery_router

__all__ = [
    "ui_router",
    "ingestion_router",
    "monitor_router",
    "export_router",
    "api_router",
    "hybrid_sync_router",
    "manual_input_router",
    "test_celery_router",
]
