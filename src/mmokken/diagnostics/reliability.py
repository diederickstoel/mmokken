"""Reliability estimators (MS, alpha, lambda-2, item-rest correlations).

Original R source:
- r_reference/mokken_3.1.2/mokken/R/check.reliability.R::check.reliability

This implements MS (Sijtsma-Molenaar reliability with the 2D interpolation of
missing within-item joint-probability cells), Cronbach's alpha, Guttman's
lambda-2, and the item-rest correlation (irc). The LCRC branch (latent-class
reliability correction) requires the R packages ``poLCA`` and ``MASS`` and
is not ported in this increment — passing ``lcrc=True`` raises
``NotImplementedError``.
"""

from __future__ import annotations

import numpy as np

from ..validation import check_data


def _compute_pp_ordered(x: np.ndarray, p1_order: np.ndarray, n: int, j: int, m: int) -> np.ndarray:
    """Build joint P(X_i >= a, X_j >= b) matrix ordered by ``p1_order``.

    Mirrors R/check.reliability.R::compute.PP (lines 4-17). Within-item
    diagonal blocks are masked to NaN.
    """
    maxx = m - 1
    pp = np.zeros((j * maxx, j * maxx), dtype=float)
    a_grid = np.arange(maxx)
    ind = (x[:, :, None] > a_grid[None, None, :]).astype(float)  # (N, J, maxx)
    for ii in range(j - 1):
        for jj in range(ii + 1, j):
            block = ind[:, ii, :].T @ ind[:, jj, :] / n
            pp[ii * maxx : (ii + 1) * maxx, jj * maxx : (jj + 1) * maxx] = block
    pp = pp + pp.T
    block_neg = -1.0 * np.ones((maxx, maxx))
    for k in range(j):
        pp[k * maxx : (k + 1) * maxx, k * maxx : (k + 1) * maxx] += block_neg
    pp = np.where(pp < -0.5, np.nan, pp)
    return pp[np.ix_(p1_order, p1_order)]


def _ms_interpolation(pp: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Fill NaN cells in ``pp`` using R's directional Type 1-4 interpolation.

    Implements the Sijtsma & Molenaar interpolation laid out in
    R/check.reliability.R lines 82-138.
    """
    km = pp.shape[0]
    pp_hat = pp.copy()

    set_matrix = (p[:, None] == p[None, :]).astype(int)
    rowsum = set_matrix.sum(axis=1)
    unique_idx = np.where(rowsum == 1)[0]

    # Type matrix construction (R lines 86-89)
    type_mat = set_matrix.copy()
    type_mat[np.ix_(unique_idx, unique_idx)] = 0
    set_vector = np.sign(type_mat.sum(axis=1))  # 1 if at least one tied non-unique partner
    # Final type matrix encoding: sv pair -> Type
    # sv=(0,0)->4, sv=(0,1)->3, sv=(1,0)->2, sv=(1,1)->1
    type_final = np.full((km, km), 4, dtype=int)
    type_final[np.ix_(set_vector == 1, set_vector == 1)] = 1
    type_final[np.ix_(set_vector == 1, set_vector == 0)] = 2
    type_final[np.ix_(set_vector == 0, set_vector == 1)] = 3
    # Type-4 is the default fill value

    nan_mask = np.isnan(pp)

    def _set_mean(rows_mask: np.ndarray, cols_mask: np.ndarray) -> float:
        block = pp[np.ix_(rows_mask, cols_mask)]
        with np.errstate(invalid="ignore"):
            mean_val = float(np.nanmean(block))
        return mean_val

    rows_iter, cols_iter = np.where(nan_mask)
    for i, jj in zip(rows_iter, cols_iter, strict=False):
        t = int(type_final[i, jj])
        row_mask = set_matrix[i] == 1
        col_mask = set_matrix[:, jj] == 1

        if t == 1:
            val = _set_mean(row_mask, col_mask)
            pp_hat[i, jj] = 0.0 if np.isnan(val) else val
            continue

        # Search for nearest non-NaN cells in 4 directions
        right_n = left_n = lower_n = upper_n = None
        right_pp = left_pp = lower_pp = upper_pp = float("nan")

        # For Types 2 and 4 we search in the row direction (varying j)
        if t in (2, 4):
            # Right: smallest col >= jj where PP[i, col] is non-NaN
            right_candidates = np.where(~np.isnan(pp[i, jj:]))[0]
            if right_candidates.size:
                right_n = jj + int(right_candidates.min())
                right_pp = _set_mean(row_mask, set_matrix[:, right_n] == 1)
            left_candidates = np.where(~np.isnan(pp[i, : jj + 1]))[0]
            if left_candidates.size:
                left_n = int(left_candidates.max())
                left_pp = _set_mean(row_mask, set_matrix[:, left_n] == 1)
        else:  # t == 3: row-direction collapses to row i itself
            right_n = left_n = jj
            right_pp = left_pp = _set_mean(row_mask, set_matrix[:, jj] == 1)

        if t in (3, 4):
            lower_candidates = np.where(~np.isnan(pp[i:, jj]))[0]
            if lower_candidates.size:
                lower_n = i + int(lower_candidates.min())
                lower_pp = _set_mean(set_matrix[lower_n] == 1, col_mask)
            upper_candidates = np.where(~np.isnan(pp[: i + 1, jj]))[0]
            if upper_candidates.size:
                upper_n = int(upper_candidates.max())
                upper_pp = _set_mean(set_matrix[upper_n] == 1, col_mask)
        else:  # t == 2: column-direction collapses to col jj
            lower_n = upper_n = i
            lower_pp = upper_pp = _set_mean(row_mask, col_mask)

        p_i = float(p[i])
        p_j = float(p[jj])

        candidates = []
        with np.errstate(invalid="ignore", divide="ignore"):
            if lower_n is not None and not np.isnan(lower_pp):
                pln = float(p[lower_n])
                if pln != 0:
                    candidates.append(lower_pp * p_i / pln)  # E17a
                if pln != 1:
                    candidates.append(lower_pp * (1 - p_i) / (1 - pln) - p_j * (pln - p_i) / (1 - pln))  # E21a
            if right_n is not None and not np.isnan(right_pp):
                prn = float(p[right_n])
                if prn != 0:
                    candidates.append(right_pp * p_j / prn)  # E17b
                if prn != 1:
                    candidates.append(right_pp * (1 - p_j) / (1 - prn) - p_i * (prn - p_j) / (1 - prn))  # E21b
            if upper_n is not None and not np.isnan(upper_pp):
                pun = float(p[upper_n])
                if pun != 0:
                    candidates.append(upper_pp * p_i / pun)  # E17c
                if pun != 1:
                    candidates.append(upper_pp * (1 - p_i) / (1 - pun) + p_j * (p_i - pun) / (1 - pun))  # E21c
            if left_n is not None and not np.isnan(left_pp):
                pln_ = float(p[left_n])
                if pln_ != 0:
                    candidates.append(left_pp * p_j / pln_)  # E17d
                if pln_ != 1:
                    candidates.append(left_pp * (1 - p_j) / (1 - pln_) + p_i * (p_j - pln_) / (1 - pln_))  # E21d

        if candidates:
            arr = np.asarray(candidates, dtype=float)
            arr = arr[~np.isnan(arr)]
            pp_hat[i, jj] = float(arr.mean()) if arr.size else 0.0
        else:
            pp_hat[i, jj] = 0.0

    pp_hat = np.nan_to_num(pp_hat, nan=0.0)
    return pp_hat


def check_reliability(
    X,
    ms: bool = True,
    alpha: bool = True,
    lambda_2: bool = True,
    irc: bool = False,
    lcrc: bool = False,
    nclass: int | None = None,
) -> dict:
    """Mokken reliability estimators.

    Parameters mirror R's ``check.reliability`` flags (``MS``, ``alpha``,
    ``lambda.2``, ``LCRC``, ``irc``). LCRC is currently deferred and raises
    ``NotImplementedError`` when ``lcrc=True``.

    Returns
    -------
    dict
        Subset of ``{MS, alpha, lambda_2, irc}`` depending on flags.
    """
    if lcrc:
        raise NotImplementedError(
            "check_reliability LCRC branch requires R packages poLCA and MASS; not yet ported."
        )

    x = check_data(X)
    n, j = x.shape
    m = int(np.max(x)) + 1
    res: dict = {}

    if ms:
        a_grid = np.arange(1, m)
        isrf = (x[:, :, None] >= a_grid[None, None, :]).astype(float)
        p1 = isrf.mean(axis=0).reshape(j * (m - 1))
        p1_order = np.argsort(p1, kind="mergesort")
        pp = _compute_pp_ordered(x, p1_order, n, j, m)

        p_sorted = np.sort(p1)
        off_boundary = (p_sorted > 0) & (p_sorted < 1)
        p_ob = p_sorted[off_boundary]
        pp_ob = pp[np.ix_(off_boundary, off_boundary)]

        lower_bound = np.outer(p_ob, p_ob)
        upper_bound = np.minimum.outer(p_ob, p_ob)
        was_nan = np.isnan(pp_ob)

        pp_hat = _ms_interpolation(pp_ob, p_ob)
        # Clip imputed cells to feasible bounds
        too_high = (pp_hat > upper_bound) & was_nan
        pp_hat[too_high] = upper_bound[too_high]
        too_low = (pp_hat < lower_bound) & was_nan
        pp_hat[too_low] = lower_bound[too_low]

        total = x.sum(axis=1)
        var_total = float(np.var(total, ddof=1)) * ((n - 1) / n)
        if var_total > 0:
            res["MS"] = float((pp_hat - lower_bound).sum() / var_total)
        else:
            res["MS"] = float("nan")

    if alpha:
        var_x = np.cov(x, rowvar=False, ddof=1)
        sum_all = var_x.sum()
        sum_diag = np.diag(var_x).sum()
        res["alpha"] = float(j / (j - 1) * (sum_all - sum_diag) / sum_all)

    if lambda_2:
        var_x = np.cov(x, rowvar=False, ddof=1)
        sum_all = var_x.sum()
        sum_diag = np.diag(var_x).sum()
        sum_sq_all = (var_x ** 2).sum()
        sum_sq_diag = (np.diag(var_x) ** 2).sum()
        numerator = (sum_all - sum_diag) + np.sqrt(j / (j - 1) * (sum_sq_all - sum_sq_diag))
        res["lambda_2"] = float(numerator / sum_all)

    if irc:
        ones = np.ones((j, j))
        np.fill_diagonal(ones, 0)
        r = x @ ones  # rest score per item
        # diagonal of correlation matrix between X and R
        out = np.empty(j, dtype=float)
        for k in range(j):
            cov = np.cov(x[:, k], r[:, k], ddof=1)[0, 1]
            sd_x = np.std(x[:, k], ddof=1)
            sd_r = np.std(r[:, k], ddof=1)
            out[k] = cov / (sd_x * sd_r) if sd_x > 0 and sd_r > 0 else 0.0
        res["irc"] = out

    return res
