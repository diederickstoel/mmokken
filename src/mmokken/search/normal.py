"""Normal item selection search procedure.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/search.normal.R::search.normal
"""

from __future__ import annotations

import warnings
from statistics import NormalDist

import numpy as np

from mmokken.core.scalability import coefHTiny
from mmokken.core.zscores import coefZ


def _any_neg(x):
    return bool(np.any(np.asarray(x) < 0))


def _adjusted_alpha(alpha, K):
    k = np.asarray(K, dtype=float).reshape(-1)
    if k.size == 1:
        return float(alpha / (k[0] * (k[0] - 1) * 0.5))
    return float(alpha / (k[0] * (k[0] - 1) * 0.5 + np.sum(k[1:])))


def _norm_ppf(p):
    return NormalDist().inv_cdf(float(p))


def _newH(j, in_this_set, x, lb, z_c, type_z, test_Hi):
    cols = np.where(in_this_set == 1)[0].tolist() + [j]
    new_x = x[:, cols]
    h_list = coefHTiny(new_x)
    if h_list["Hi"][-1] < lb:
        return -98.0
    zi = coefZ(new_x, lowerbound=(float(bool(test_Hi)) * lb), type_z=type_z)["Zi"]
    if zi.reshape(-1)[-1] < z_c:
        return -97.0
    return float(h_list["H"])


def _prepare_startset(start_set, n_items):
    # Mirrors R validation style for logical/numeric/integer StartSet.
    if isinstance(start_set, (bool, np.bool_)):
        if bool(start_set):
            warnings.warn("Start set of items is not properly defined. User-defined StartSet ignored.", UserWarning, stacklevel=2)
            return False
        return False

    arr = np.asarray(start_set)
    if arr.size == 0:
        warnings.warn("Start set of items is not properly defined. User-defined StartSet ignored.", UserWarning, stacklevel=2)
        return False
    if np.any(np.isnan(arr)):
        warnings.warn("Start set of items is not properly defined. User-defined StartSet ignored.", UserWarning, stacklevel=2)
        return False
    if arr.dtype.kind not in {"i", "u", "f"}:
        warnings.warn("data.class(StartSet) should be logical or numeric. User-defined StartSet ignored.", UserWarning, stacklevel=2)
        return False

    arr = np.unique(arr.astype(int))
    if not np.all((arr >= 1) & (arr <= n_items)):
        warnings.warn("Start set of items is not properly defined. User-defined StartSet ignored", UserWarning, stacklevel=2)
        return False
    return arr


def search_normal(X, lowerbound, alpha, StartSet=False, verbose=False, type_z="Z", test_Hi=False, level_two_var=None):
    """Port of R/search.normal.R::search.normal."""
    x = np.asarray(X, dtype=float)

    if level_two_var is not None:
        lv = np.asarray(level_two_var)
        if lv.shape[0] != x.shape[0]:
            level_two_var = None
            warnings.warn("level.two.var not the same length/nrow as X: level.two.var is ignored.", UserWarning, stacklevel=2)
        elif type_z == "Z":
            level_two_var = None
            warnings.warn("level.two.var is ignored for type.z = 'Z'.", UserWarning, stacklevel=2)
        elif np.any(np.isnan(lv)):
            level_two_var = None
            warnings.warn("level.two.var contains missing value(s): level.two.var is ignored.", UserWarning, stacklevel=2)
        else:
            raise NotImplementedError("search.normal level.two.var branch requires multilevel coefZ support.")

    item_label = np.array([str(i + 1) for i in range(x.shape[1])], dtype=object)
    vars_ = np.var(x, axis=0, ddof=1)
    if np.any(vars_ == 0):
        raise ValueError("At least one item has no variance")

    Hij = coefHTiny(x)["Hij"]
    Zij = coefZ(x, lowerbound=0, type_z=type_z)["Zij"]

    J = Hij.shape[0]
    lb_vec = np.asarray(lowerbound if np.ndim(lowerbound) > 0 else [lowerbound], dtype=float).reshape(-1)
    output_cols = []

    start_set = _prepare_startset(StartSet, J)
    startset_provided = not isinstance(start_set, (bool, np.bool_))

    for lb in lb_vec:
        result = np.full(J, -99.0)
        inset = np.zeros(J, dtype=int)
        scale = 0

        while True:
            scale += 1
            step = 1
            K = np.zeros(J, dtype=float)

            if np.sum(inset == 0) < 2:
                break

            K[0] = np.sum(inset == 0)
            z_c = abs(_norm_ppf(_adjusted_alpha(alpha, K)))

            hselect = Hij.copy()
            hselect[np.abs(Zij) < z_c] = -99
            mask_prev = (inset > 0) & (inset < scale)
            hselect[mask_prev, :] = -99
            hselect[:, mask_prev] = -99
            tri_mask = np.triu(np.ones_like(hselect, dtype=bool), k=0)
            hselect[tri_mask] = -99
            eps = (np.arange(1, J + 1) * 1e-10).reshape(-1, 1)
            hselect = hselect - eps

            if np.max(np.round(hselect)) == -99:
                break

            if isinstance(start_set, (bool, np.bool_)) or scale > 1:
                maxv = np.max(hselect)
                r_idx, c_idx = np.where(hselect == maxv)
                start_set_current = np.sort(np.concatenate([r_idx + 1, c_idx + 1]))
            else:
                start_set_current = np.asarray(start_set, dtype=int)

            if start_set_current.size == 1 and scale == 1:
                first_item = int(start_set_current[0])
                max_tmp = max(np.max(hselect[first_item - 1, :]), np.max(hselect[:, first_item - 1]))
                second = np.where(np.abs(Hij[first_item - 1, :] - max_tmp) < 1e-6)[0] + 1
                start_set_current = np.sort(np.concatenate([[first_item], second]))

            if startset_provided and scale == 1:
                ss = start_set_current.astype(int) - 1
                start_hij = hselect[np.ix_(ss, ss)]
                lower = start_hij[np.tril_indices(start_hij.shape[0], -1)]
                if np.any(lower < 0):
                    warnings.warn(
                        "Items in start set do not form a Mokken scale: Some Hij are not significantly greater than zero",
                        UserWarning,
                        stacklevel=2,
                    )

            ss = start_set_current.astype(int) - 1
            if test_Hi:
                start_hi = coefZ(x[:, ss], lowerbound=lb, type_z=type_z)["Zi"].reshape(-1)
                check_hi = np.min(np.abs(start_hi)) < z_c
            else:
                start_hi = coefHTiny(x[:, ss])["Hi"]
                check_hi = np.min(start_hi) < lb

            if check_hi:
                if startset_provided and scale == 1:
                    warnings.warn(f"Items in start set do not form a Mokken scale: Some Hj < {lb}", UserWarning, stacklevel=2)
                if (not startset_provided) or scale > 1:
                    break

            inset[ss] = scale

            while True:
                step += 1
                in_this_set = inset.copy()
                in_this_set = np.where(inset == scale, 1, 0)
                in_this_set = np.where((inset < scale) & (inset > 0), -1, in_this_set)

                sel = np.where(in_this_set == 1)[0]
                neg1 = np.any(Hij[np.ix_(sel, np.arange(J))] < 0, axis=0)
                neg2 = np.any(Hij[np.ix_(np.arange(J), sel)] < 0, axis=1)
                in_this_set[(neg1 | neg2) & (in_this_set == 0)] = -1

                available = np.where(in_this_set == 0)[0]
                if available.size == 0:
                    break

                result[in_this_set != 0] = -99
                if step - 1 < J:
                    K[step - 1] = available.size
                z_c = abs(_norm_ppf(_adjusted_alpha(alpha, K)))
                for j in available:
                    result[j] = _newH(j, in_this_set, x, lb, z_c, type_z, test_Hi)

                if np.max(result) < lb:
                    break

                new_items = np.where(result == np.max(result))[0]
                inset[new_items] = scale

        output_cols.append(inset.astype(float))

    out = np.column_stack(output_cols)
    # R style dimnames are omitted; values are identical assignments.
    return out

