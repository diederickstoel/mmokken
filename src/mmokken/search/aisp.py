"""Automated Item Selection Procedure (AISP).

Original R source:
- r_reference/mokken_3.1.2/mokken/R/aisp.R::aisp
"""

from __future__ import annotations

import warnings

import numpy as np

from mmokken.validation import check_data
from mmokken.core.scalability import coefHTiny

from .ga import search_ga
from .normal import search_normal


def aisp(
    X,
    lowerbound=0.3,
    search="normal",
    alpha=0.05,
    StartSet=False,
    popsize=20,
    maxgens=None,
    pxover=0.5,
    pmutation=0.1,
    verbose=False,
    type_z="Z",
    test_Hi=False,
    level_two_var=None,
    random_state=None,
):
    """Port of R/aisp.R::aisp (normal search path)."""
    x = check_data(X)
    output = None

    params = [alpha, pxover, pmutation]
    cparams = ["alpha", "pxover", "pmutation"]
    for i in range(3):
        p = params[i]
        if not np.isscalar(p) or isinstance(p, (bool, np.bool_)) or np.isnan(float(p)):
            raise ValueError(f"{cparams[i]} is not numeric")
        # Preserve R behavior: warnings are emitted but value is not changed.
        if p < 0:
            warnings.warn(f"Negative {cparams[i]}. {cparams[i]} is set to 0", UserWarning, stacklevel=2)
        if p > 1:
            warnings.warn(f"{cparams[i]} greater than 1. {cparams[i]} is set to 1", UserWarning, stacklevel=2)

    lb_vec = np.asarray(lowerbound if np.ndim(lowerbound) > 0 else [lowerbound], dtype=float).reshape(-1)
    for lb in lb_vec:
        if np.isnan(lb):
            raise ValueError(" lowerbound contains non-numeric values")

    tmp = coefHTiny(x)["Hij"].copy()
    np.fill_diagonal(tmp, 0)
    c_max = np.max(tmp)
    if np.any(lb_vec > c_max):
        warnings.warn(
            "Some lower bounds are greater than max(Hij) rendering all items unscalable. "
            "Lower bounds greater than max(Hij) are removed",
            UserWarning,
            stacklevel=2,
        )
        lb_vec = lb_vec[lb_vec <= c_max]
        if lb_vec.size == 0:
            raise ValueError("no lowerbound provided")

    default_maxgens = (10 ** (np.log2(x.shape[1] / 5.0))) * 1000.0
    if not np.isscalar(popsize) or isinstance(popsize, (bool, np.bool_)) or np.isnan(float(popsize)):
        raise ValueError("popsize is not numeric")
    popsize = int(popsize)
    if popsize < 1:
        raise ValueError("popsize is nonpositive")

    if maxgens is None:
        maxgens = default_maxgens
    if not np.isscalar(maxgens) or isinstance(maxgens, (bool, np.bool_)) or np.isnan(float(maxgens)):
        raise ValueError("maxgens is not numeric")
    maxgens = int(maxgens)
    if maxgens < 1:
        raise ValueError("maxgens is nonpositive")

    if search == "ga":
        if level_two_var is not None:
            raise NotImplementedError(
                "aisp(search='ga', level_two_var=...) is not yet ported."
            )
        output_cols = []
        for lb in lb_vec:
            assignment = search_ga(
                x,
                lowerbound=float(lb),
                alpha=float(alpha),
                popsize=int(popsize),
                maxgens=int(maxgens),
                pxover=float(pxover),
                pmutation=float(pmutation),
                random_state=random_state,
                verbose=verbose,
            )
            output_cols.append(assignment.reshape(-1, 1).astype(float))
        return np.column_stack(output_cols) if output_cols else np.zeros((x.shape[1], 0))
    if search == "extended":
        raise NotImplementedError("aisp(search='extended') is not yet ported.")

    # Normal search path
    if test_Hi and type_z == "Z":
        type_z = "WB"
        warnings.warn("type.z has been changed to 'WB' to enable testing Hi > c.", UserWarning, stacklevel=2)

    if level_two_var is not None:
        lv = np.asarray(level_two_var)
        if lv.shape[0] != x.shape[0]:
            level_two_var = None
            warnings.warn("level.two.var not the same length/nrow as X: level.two.var is ignored.", UserWarning, stacklevel=2)
        elif np.any(np.isnan(lv)):
            level_two_var = None
            warnings.warn("level.two.var contains missing value(s): level.two.var is ignored.", UserWarning, stacklevel=2)
        else:
            if type_z == "Z":
                type_z = "WB"
                warnings.warn("type.z has been changed to 'WB' to enable testing in multilevel data.", UserWarning, stacklevel=2)
            # Full multilevel path depends on coefZ/search.normal level_two_var support.
            raise NotImplementedError("aisp level.two.var path is not yet ported.")

    output_cols = []
    for lb in lb_vec:
        no = search_normal(
            x,
            lowerbound=[float(lb)],
            alpha=float(alpha),
            StartSet=StartSet,
            verbose=verbose,
            type_z=type_z,
            test_Hi=test_Hi,
            level_two_var=level_two_var,
        )
        output_cols.append(no.reshape(-1, 1))

    output = np.column_stack(output_cols) if output_cols else np.zeros((x.shape[1], 0))
    return output

