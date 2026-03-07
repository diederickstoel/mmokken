"""Validation helpers for the Mokken Python port.

Original R sources:
- r_reference/mokken_3.1.2/mokken/R/internalFunctions.R::check.data
- r_reference/mokken_3.1.2/mokken/R/internalFunctions.R::check.ml.data
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd


def _as_numeric_array(x):
    if isinstance(x, pd.DataFrame):
        matrix_x = x.to_numpy()
    elif isinstance(x, np.ndarray):
        matrix_x = x
    else:
        raise TypeError("Data are not matrix or data.frame")
    return np.asarray(matrix_x)


def _check_common(matrix_x):
    if np.isnan(matrix_x).any():
        raise ValueError("Missing values are not allowed")
    if not np.issubdtype(matrix_x.dtype, np.number):
        raise ValueError("Data must be numeric")
    if (matrix_x < 0).any():
        raise ValueError("All scores should be nonnegative")
    if not np.all(np.mod(matrix_x, 1) == 0):
        raise ValueError("All scores must be integers")


def check_data(X, check_scores=True):
    """Port of R/internalFunctions.R::check.data."""
    matrix_x = _as_numeric_array(X)
    _check_common(matrix_x)

    matrix_x = matrix_x - np.min(matrix_x)

    if np.any(matrix_x > 9):
        raise ValueError(
            "Some items have more than 10 categories. mokken cannot only handle up to 10 categories"
        )

    if check_scores:
        max_score = int(np.max(matrix_x))
        score_check = []
        for col in range(matrix_x.shape[1]):
            observed = matrix_x[:, col]
            expected = np.arange(0, max_score + 1, 1)
            score_check.append(np.all(np.isin(expected, observed)))
        if not np.all(score_check):
            warnings.warn(
                "Varying numbers of item scores were observed across the items.\n"
                "  Either the items have the same number of response categories but some item categories were not endorsed;\n"
                "  or the items have different numbers of categories by design. \n"
                "  In the latter case, the sum score cannot be used for (ordinal) measurement.",
                UserWarning,
                stacklevel=2,
            )

    return matrix_x


def check_ml_data(X, check_scores=True):
    """Port of R/internalFunctions.R::check.ml.data."""
    matrix_x = _as_numeric_array(X)
    _check_common(matrix_x)

    matrix_x = matrix_x.copy()
    matrix_x[:, 1:] = matrix_x[:, 1:] - np.min(matrix_x[:, 1:])

    if check_scores:
        max_score = int(np.max(matrix_x[:, 1:]))
        score_check = []
        for col in range(1, matrix_x.shape[1]):
            observed = matrix_x[:, col]
            expected = np.arange(0, max_score + 1, 1)
            score_check.append(np.all(np.isin(expected, observed)))
        if not np.all(score_check):
            warnings.warn(
                "Varying numbers of item scores were observed across the items.\n"
                "  Either the items have the same number of response categories but some item categories were not endorsed;\n"
                "  or the items have different numbers of categories by design. \n"
                "  In the latter case, the sum score cannot be used for (ordinal) measurement.",
                UserWarning,
                stacklevel=2,
            )

    return matrix_x
