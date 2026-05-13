"""Matrix transform helpers ported from R internal functions.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/internalFunctions.R
  - phi
  - dphi
  - complete.observed.frequencies
"""

from __future__ import annotations

import numpy as np

from .weights import allPatterns


def _row_scale(coeff, df):
    coeff = np.asarray(coeff, dtype=float)
    df = np.asarray(df, dtype=float)
    if coeff.ndim == 1 and df.ndim == 2 and coeff.shape[0] == df.shape[0]:
        return coeff[:, None] * df
    return coeff * df


def phi(A, f, action):
    """Port of R/internalFunctions.R::phi."""
    eps = 1e-80
    A = np.asarray(A, dtype=float)
    f = np.asarray(f, dtype=float)

    if action == "identity":
        term = f
    elif action == "exp":
        term = np.exp(f)
    elif action == "log":
        term = np.log(np.abs(f) + eps)
    elif action == "sqrt":
        term = np.sqrt(f)
    elif action == "xlogx":
        term = -f * np.log(f + eps)
    elif action == "xbarx":
        term = f * (1 - f)
    else:
        raise ValueError(f"Unknown action: {action}")

    return A @ term


def dphi(A, f, df, action):
    """Port of R/internalFunctions.R::dphi."""
    eps = 1e-80
    A = np.asarray(A, dtype=float)
    f = np.asarray(f, dtype=float)
    df = np.asarray(df, dtype=float)

    if action == "identity":
        term = df
    elif action == "exp":
        term = _row_scale(np.asarray(np.exp(f), dtype=float), df)
    elif action == "log":
        term = _row_scale(np.asarray(1.0 / (f + eps), dtype=float), df)
    elif action == "sqrt":
        term = _row_scale(np.asarray(1.0 / (2.0 * np.sqrt(f)), dtype=float), df)
    elif action == "xlogx":
        term = _row_scale(np.asarray(-1.0 - np.log(f + eps), dtype=float), df)
    elif action == "xbarx":
        term = _row_scale(np.asarray(1.0 - 2.0 * f, dtype=float), df)
    else:
        raise ValueError(f"Unknown action: {action}")

    return A @ term


def complete_observed_frequencies(data, J, m, order_items=False):
    """Port of R/internalFunctions.R::complete.observed.frequencies.

    Returns a (m**J, 1) matrix of observed response-pattern frequencies.
    """
    J = int(J)
    m = int(m)
    x = np.asarray(data, dtype=float)

    if order_items:
        col_means = np.mean(x, axis=0)
        order_idx = np.argsort(col_means, kind="mergesort")[::-1]
    else:
        order_idx = np.arange(J)
    x = np.asarray(x[:, order_idx], dtype=float)

    t_r = np.column_stack((allPatterns(J, m).T, np.zeros((m**J, 1), dtype=float)))
    p = m**J

    for i in range(p):
        diffs = np.abs(x - t_r[i, :J])
        size = np.sum(diffs, axis=1) == 0
        t_r[i, J] = np.sum(size)

    return t_r[:, J].reshape(-1, 1)

