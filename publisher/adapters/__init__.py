"""Platform adapter package."""
from .base import BaseAdapter
from .x_twitter import XTwitterAdapter
from .facebook import FacebookAdapter
from .instagram import InstagramAdapter
from .linkedin import LinkedInAdapter
from .gbp import GBPAdapter
from .ghl import GHLAdapter

__all__ = [
    "BaseAdapter",
    "XTwitterAdapter",
    "FacebookAdapter",
    "InstagramAdapter",
    "LinkedInAdapter",
    "GBPAdapter",
    "GHLAdapter",
]

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "x": XTwitterAdapter,
    "facebook": FacebookAdapter,
    "instagram": InstagramAdapter,
    "linkedin": LinkedInAdapter,
    "gbp": GBPAdapter,
}

# GHL mode uses a single adapter for all platforms
GHL_ADAPTER_CLASS = GHLAdapter
