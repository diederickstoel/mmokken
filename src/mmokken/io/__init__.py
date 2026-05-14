"""Input/output for the mmokken package.

Currently supports the legacy MSP 5 ``.dat`` + ``.var`` format produced by
the original Mokken Scale Program for Windows (ProGAMMA, 2003). The format
predates the R `mokken` package and is therefore useful for three-way
parity validation (MSP 5 → R `mokken` → Python `mmokken`).
"""

from __future__ import annotations

from .msp_loader import load_msp_dataset

__all__ = ["load_msp_dataset"]
