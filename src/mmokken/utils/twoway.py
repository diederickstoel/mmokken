"""Two-way imputation of missing item scores.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/twoway.R::twoway

Combines person-mean + item-mean - grand-mean with normal random noise whose
variance matches the residual of the observed cells. The result is rounded
and clipped to ``[minX, maxX]``.
"""

from __future__ import annotations

import warnings

import numpy as np


def twoway(
    X,
    n_completed_data_sets: int = 1,
    min_x: float | None = None,
    max_x: float | None = None,
    seed: int | None = None,
) -> np.ndarray | list[np.ndarray]:
    """Two-way imputation for an item score matrix with missing values.

    Parameters
    ----------
    X : array_like
        Respondents × items, integer-valued; ``np.nan`` denotes missing.
    n_completed_data_sets : int, default 1
        Number of imputed datasets to return.
    min_x, max_x : float, optional
        Clipping bounds. Default to ``np.nanmin(X)`` and ``np.nanmax(X)``.
    seed : int, optional
        Seed for ``numpy.random.default_rng``. R's `set.seed` uses a global
        state; here we follow scikit-learn conventions and accept an explicit
        seed.

    Returns
    -------
    ndarray or list of ndarrays
        A single completed dataset when ``n_completed_data_sets == 1``,
        otherwise a list of them.
    """
    arr = np.asarray(X, dtype=float)
    if not np.issubdtype(arr.dtype, np.number):
        raise TypeError("X must be numeric")
    # Validate non-negative integers on observed cells (mirror R checks)
    observed = ~np.isnan(arr)
    if np.any(arr[observed] < 0):
        raise ValueError("All scores must be nonnegative")
    if np.any(np.mod(arr[observed], 1) != 0):
        raise ValueError("All scores must be integers")
    if min_x is None:
        min_x = float(np.nanmin(arr))
    if max_x is None:
        max_x = float(np.nanmax(arr))
    if np.any(arr[observed] < min_x):
        raise ValueError("All scores must be greater than or equal to minX")
    if np.any(arr[observed] > max_x):
        raise ValueError("All scores must be less than or equal to maxX")

    n, j = arr.shape
    missing = np.isnan(arr)

    if not missing.any():
        warnings.warn("X does not contain missing values", UserWarning, stacklevel=2)
        return arr.copy() if n_completed_data_sets == 1 else [arr.copy() for _ in range(n_completed_data_sets)]

    if np.any(missing.sum(axis=1) == j):
        raise ValueError("At least one row has no observed scores.")
    if np.any(missing.sum(axis=0) == n):
        raise ValueError("At least one column has no observed scores.")

    item_means = np.nanmean(arr, axis=0)
    person_means = np.nanmean(arr, axis=1)
    grand_mean = float(np.nanmean(arr))

    item_grid = np.tile(item_means, (n, 1))
    person_grid = np.tile(person_means[:, None], (1, j))
    two_way = person_grid + item_grid - grand_mean

    # Residual variance over observed cells; mirrors R's var((Xm - TW)[!M])
    resid = (arr - two_way)[observed]
    # R's `var(...)` is ddof=1
    resid_var = float(np.var(resid, ddof=1)) if resid.size > 1 else 0.0

    rng = np.random.default_rng(seed)
    completed_list: list[np.ndarray] = []
    for _ in range(n_completed_data_sets):
        noise = rng.normal(0.0, resid_var, size=(n, j)) if resid_var > 0 else np.zeros((n, j))
        x_tmp = np.round(two_way + noise)
        x_tmp = np.clip(x_tmp, min_x, max_x)
        # Preserve observed cells verbatim
        x_tmp[observed] = arr[observed]
        completed_list.append(x_tmp)

    return completed_list[0] if n_completed_data_sets == 1 else completed_list
