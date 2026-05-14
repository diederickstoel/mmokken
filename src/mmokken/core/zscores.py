"""Z-score helpers for the mmokken package.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/coefZ.R::coefZ
"""

from __future__ import annotations

import warnings

import numpy as np

from mmokken.validation import check_data

from .scalability import coefH


def coefZ(X, lowerbound=0, type_z="Z", level_two_var=None):
    """Port of R/coefZ.R::coefZ for one-level data."""
    x = check_data(X, check_scores=False)

    if type_z not in {"Z", "WB", "RP"}:
        type_z_t = "WB" if lowerbound > 0 else "Z"
        warnings.warn(
            f"type.z = '{type_z}' is unknown. "
            "Type of z-score was changed to type.z = 'Z' if lowerbound = 0 and to type.z = 'WB' if lowerbound > 0. "
            f"In this case, type.z was changed to '{type_z_t}'",
            UserWarning,
            stacklevel=2,
        )
        type_z = type_z_t

    if lowerbound > 0 and type_z == "Z":
        type_z = "WB"
        warnings.warn(
            "type.z has been changed to 'WB' to enable testing for lowerbound > 0.",
            UserWarning,
            stacklevel=2,
        )

    if level_two_var is not None:
        raise NotImplementedError("coefZ level.two.var branch is not yet ported.")

    if type_z == "WB":
        hs = coefH(x, se=True, ci=False, nice_output=False, results=False)
        Zij = (hs["Hij"] - lowerbound) / hs["se.Hij"]
        np.fill_diagonal(Zij, 0)
        Zi = ((hs["Hi"] - lowerbound) / hs["se.Hi"]).reshape(1, -1)
        Z = float((hs["H"] - lowerbound) / hs["se.H"])
    elif type_z == "RP":
        hs = coefH(x, se=True, ci=False, nice_output=False, results=False)
        Zij = -(np.log(1 - hs["Hij"]) - np.log(1 - lowerbound)) / (hs["se.Hij"] / (1 - hs["Hij"]))
        np.fill_diagonal(Zij, 0)
        Zi = (
            -(
                np.log(1 - hs["Hi"]) - np.log(1 - lowerbound)
            )
            / (hs["se.Hi"] / (1 - hs["Hi"]))
        ).reshape(1, -1)
        Z = float(-(np.log(1 - hs["H"]) - np.log(1 - lowerbound)) / (hs["se.H"] / (1 - hs["H"])))
    else:
        N = x.shape[0]
        S = np.cov(x, rowvar=False, ddof=1)
        vars_ = np.var(x, axis=0, ddof=1)
        Sij = np.outer(vars_, vars_)
        Zij = (S * np.sqrt(N - 1)) / np.sqrt(Sij)
        np.fill_diagonal(S, 0)
        np.fill_diagonal(Sij, 0)
        np.fill_diagonal(Zij, 0)
        Zi = ((np.sum(S, axis=1) * np.sqrt(N - 1)) / np.sqrt(np.sum(Sij, axis=1))).reshape(1, -1)
        Z = float((np.sum(S) / 2.0 * np.sqrt(N - 1)) / np.sqrt(np.sum(Sij) / 2.0))

    return {"Zij": Zij, "Zi": Zi, "Z": Z}

