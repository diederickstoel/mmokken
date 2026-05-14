"""Data utilities for the mmokken package.

These mirror R `mokken`'s small utility functions (``recode``, ``twoway``)
that transform an input data matrix without performing a Mokken-specific
analysis.
"""

from __future__ import annotations

from .recode import recode
from .twoway import twoway

__all__ = ["recode", "twoway"]
