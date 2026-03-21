"""Platform adapter package."""
from .base import BaseAdapter
from .x_twitter import XTwitterAdapter
from .facebook import FacebookAdapter
from .instagram import InstagramAdapter
from .linkedin import LinkedInAdapter
from .gbp import GBPAdapter

__all__ = [
    "BaseAdapter",
    "XTwitterAdapter",
    "FacebookAdapter",
    "InstagramAdapter",
    "LinkedInAdapter",
    "GBPAdapter",
]

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "x": XTwitterAdapter,
    "facebook": FacebookAdapter,
    "instagram": InstagramAdapter,
    "linkedin": LinkedInAdapter,
    "gbp": GBPAdapter,
}
