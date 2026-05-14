"""Shared helpers for diagnostic checks (monotonicity, restscore, pmatrix).

Private — not part of the public API.
"""

from __future__ import annotations

import numpy as np


def default_minsize(n: int) -> int:
    """Mirror R defaults: N>=500 -> N/10, N<=250 -> N/3, N<150 -> 50.

    Source: R/check.monotonicity.R lines 8-10 (same heuristic used across the
    `check.*` family).
    """
    if n < 150:
        return 50
    if n <= 250:
        return n // 3
    if n >= 500:
        return n // 10
    return n // 5


def build_groups(sorted_rest: np.ndarray, minsize: int, n: int) -> list[int]:
    """Build cumulative right-edge positions for rest-score groups.

    Mirrors the R `repeat` loop used by check.monotonicity and check.restscore.
    Returns a list of 1-based right-edge positions; the final group covers
    everything from the last edge+1 to N (caller adds that bound).

    Source: R/check.monotonicity.R lines 34-40; R/check.restscore.R lines 39-44.
    """
    target = sorted_rest[minsize - 1]
    g0 = int(np.max(np.where(sorted_rest == target)[0])) + 1  # 1-based
    group = [g0]
    while n - max(group) >= minsize:
        target = sorted_rest[minsize + max(group) - 1]
        g_next = int(np.max(np.where(sorted_rest == target)[0])) + 1
        group.append(g_next)
    group.pop()
    return group
