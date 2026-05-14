"""Diagnostic checks for Mokken scales.

Ports of R `mokken`'s ``check.*`` family. Each function returns a dict that
mirrors the corresponding R S3 class structure (``monotonicity.class``,
``restscore.class``, ``pmatrix.class``, etc.) using plain Python types.
"""

from __future__ import annotations

from .monotonicity import check_monotonicity
from .restscore import check_restscore

__all__ = ["check_monotonicity", "check_restscore"]
