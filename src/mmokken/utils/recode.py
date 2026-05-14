"""Reverse-coding utility for item scores.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/recode.R::recode
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def recode(
    X,
    items: Sequence[int] | None = None,
    values: Sequence[int] | None = None,
) -> np.ndarray:
    """Reverse-code one or more items.

    Mirrors R's ``mokken::recode``. For each item index in ``items`` the new
    score is ``max(values) - x + min(values)``. NaN entries are left
    untouched. Items not in ``items`` are returned unchanged.

    Parameters
    ----------
    X : array_like
        Respondents × items, integer-valued (NaN allowed and preserved).
    items : sequence of int, optional
        0-based item indices to recode. Default: empty (no-op).
    values : sequence of int, optional
        Score range used to compute the new value. Defaults to
        ``range(np.nanmin(X), np.nanmax(X) + 1)``.

    Returns
    -------
    ndarray
        A new array with the same shape as the input.
    """
    arr = np.array(X, dtype=float, copy=True)
    if values is None:
        v_min = float(np.nanmin(arr))
        v_max = float(np.nanmax(arr))
    else:
        vals = np.asarray(values, dtype=float)
        v_min = float(vals.min())
        v_max = float(vals.max())
    if items is None:
        return arr
    items_arr = np.asarray(items, dtype=int)
    if items_arr.size == 0:
        return arr
    block = arr[:, items_arr]
    mask = ~np.isnan(block)
    block[mask] = v_max - block[mask] + v_min
    arr[:, items_arr] = block
    return arr
