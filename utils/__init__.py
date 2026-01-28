# Re-export all public functions and constants for backward compatibility
# This allows: from utils import divider_color, remove_emojis, ...

from .constants import divider_color, DEFAULT_IMAGE
from .text import remove_emojis
from .display import display_item, display_order, display_split
from .parsers import order_processor

__all__ = [
    # Constants
    "divider_color",
    "DEFAULT_IMAGE",
    # Text utilities
    "remove_emojis",
    # Display functions
    "display_item",
    "display_order",
    "display_split",
    # Parsers
    "order_processor",
]
