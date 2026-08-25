"""HTTP API."""

from .deals import router as deals_router
from .devices import router as devices_router
from .scans import router as scans_router
from .settings import router as settings_router

__all__ = ["deals_router", "devices_router", "scans_router", "settings_router"]
