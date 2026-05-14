"""P-matrix non-intersection diagnostic for Mokken scales.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/check.pmatrix.R::check.pmatrix

Builds the joint P(X_i >= a, X_j >= b) and P(X_i < a, X_j < b) matrices
indexed by item-step, ordered by item-step popularity (P1). For each
item-step row checks for non-intersection violations on both matrices.
Z-scores use the McNemar-like sqrt-difference form, computed on the
appropriate conditional subsample of respondents.
"""

from __future__ import annotations

import numpy as np

from ..core.scalability import coefHTiny
from ..validation import check_data

_Z95 = 1.6448536269514722


def _scores_to_steps(x: np.ndarray, p1_order: np.ndarray, maxx: int) -> np.ndarray:
    """Convert raw score matrix to ISRF binary matrix ordered by P1.

    Source: R/check.pmatrix.R::Scores2Steps (lines 32-44).
    Returns an (N, J * maxx) matrix where column corresponds to "X_j >= a"
    for a in 1..maxx, then reordered by ``p1_order`` (ascending sort indices).
    """
    n, j_count = x.shape
    # For each respondent r and item j, columns 1..maxx contain 1 iff X[r,j] >= a
    # R: nested via row/col operations. Direct numpy build:
    a_grid = np.arange(1, maxx + 1)
    y = (x[:, :, None] >= a_grid[None, None, :]).astype(int)  # (N, J, maxx)
    y = y.reshape(n, j_count * maxx)  # row-major: item 0 steps 1..maxx, item 1 steps 1..maxx, ...
    return y[:, p1_order]


def _compute_pmatrix(x: np.ndarray, p1_order: np.ndarray, n: int, j_count: int, m: int, *, plus: bool) -> np.ndarray:
    """Compute Ppp (``plus=True``) or Pmm (``plus=False``) and reorder by P1.

    Source: R/check.pmatrix.R::compute.Ppp / ::compute.Pmm (lines 4-30).
    Within-item diagonal blocks are masked to NaN via the kronecker(-1) trick.
    """
    maxx = m - 1
    p = np.zeros((j_count * maxx, j_count * maxx), dtype=float)
    a_grid = np.arange(maxx)  # 0..maxx-1, since R uses 0:(m-2)
    if plus:
        ind = x[:, :, None] > a_grid[None, None, :]  # X[,i] > a equivalently X >= a+1
    else:
        ind = x[:, :, None] <= a_grid[None, None, :]  # X[,i] <= a equivalently X < a+1
    # ind: (N, J, maxx)
    for i in range(j_count - 1):
        for j in range(i + 1, j_count):
            block = ind[:, i, :].T.astype(float) @ ind[:, j, :].astype(float) / n
            # block shape: (maxx, maxx)
            p[i * maxx : (i + 1) * maxx, j * maxx : (j + 1) * maxx] = block
    p = p + p.T
    # kronecker(diag(J), -1 block of size maxx) — only within-item blocks
    block_neg = -1.0 * np.ones((maxx, maxx))
    for k in range(j_count):
        p[k * maxx : (k + 1) * maxx, k * maxx : (k + 1) * maxx] += block_neg
    # Mark masked entries as NaN
    p = np.where(p < -0.5, np.nan, p)
    # Reorder rows and columns by P1
    return p[np.ix_(p1_order, p1_order)]


def _z_block(
    sample_mask: np.ndarray,
    x: np.ndarray,
    x_isrf: np.ndarray,
    p1_order: np.ndarray,
    n: int,
    j_count: int,
    m: int,
    *,
    plus: bool,
    sign_matrix: np.ndarray,
) -> np.ndarray:
    """Compute the K x K Z-score matrix for one item-step row.

    Source: R/check.pmatrix.R lines 110-145 (the two parallel branches for
    Ppp/Pmm). Implements the McNemar-like B-corrected sqrt-difference form.
    Returns a K x K matrix with entries below qnorm(.95) replaced by NaN.
    """
    K = j_count * (m - 1)
    if int(sample_mask.sum()) < 2:
        return np.full((K, K), np.nan)
    x_sub = x[sample_mask]
    n_sub_rows = x_sub.shape[0]
    if plus:
        np11 = _compute_pmatrix(x_sub, p1_order, n, j_count, m, plus=True) * n
        np1 = np.tile(x_isrf[sample_mask].sum(axis=0), (K, 1))
        np01 = np.round(np1 - np11)
        np10 = np01.T
    else:
        nm00 = _compute_pmatrix(x_sub, p1_order, n, j_count, m, plus=False) * n
        nm1 = np.tile(x_isrf[sample_mask].sum(axis=0), (K, 1))
        nm0 = n_sub_rows - nm1
        np01 = np.round(nm0.T - nm00)
        np10 = np01.T
    k = np.fmin(np01, np10)
    nn = np01 + np10
    nn = np.where(nn < 1, 0.5, nn)
    with np.errstate(invalid="ignore", divide="ignore"):
        B = ((2 * k + 1 - nn) ** 2 - 10 * nn) / (12 * nn)
        z = np.abs(np.sqrt(2 * k + 2 + B) - np.sqrt(2 * nn - 2 * k + B))
    z = z * np.sign(sign_matrix)
    z = np.where(z < _Z95, np.nan, z)
    return z


def check_pmatrix(X, minvi: float = 0.03) -> dict:
    """P-matrix non-intersection diagnostic.

    Returns
    -------
    dict
        Nested results dict mirroring R's ``pmatrix.class`` structure:
        ``results`` (with ``Ppp``, ``Pmm``, ``ac``, ``vi``, ``n_vi``,
        ``max_vi``, ``sum_vi``, ``z``, ``n_z``, ``max_z``), ``I_item``,
        ``I_step``, ``I_labels``, ``Hi``, ``minvi``, ``ncat``, ``N``.
    """
    x = check_data(X)
    n, j_count = x.shape
    ncat = int(np.max(x)) + 1
    maxx = ncat - 1

    if maxx < 1:
        raise ValueError("All items are constant; pmatrix is undefined")

    # P1: item-step popularity = mean of (X >= a) over respondents, for each item, step
    # Reshaped to row-major (item, step) for each (i in 1..J, a in 1..maxx)
    a_grid = np.arange(1, maxx + 1)
    isrf_unsorted = (x[:, :, None] >= a_grid[None, None, :]).astype(float)  # (N, J, maxx)
    p1 = isrf_unsorted.mean(axis=0).reshape(j_count * maxx)  # row-major: item-major, step-minor

    p1_order = np.argsort(p1, kind="mergesort")  # ascending; ties stable

    x_isrf = _scores_to_steps(x, p1_order, maxx)
    i_item = np.repeat(np.arange(1, j_count + 1), maxx)[p1_order]
    i_step_unsorted = [f"X{j + 1}>={a}" for j in range(j_count) for a in range(1, maxx + 1)]
    i_step = [i_step_unsorted[i] for i in p1_order]
    i_labels = [f"C{j + 1}" for j in range(j_count)]

    Ppp = _compute_pmatrix(x, p1_order, n, j_count, ncat, plus=True)
    Pmm = _compute_pmatrix(x, p1_order, n, j_count, ncat, plus=False)

    K = j_count * maxx
    ac = (j_count - 1) * (j_count - 2) * (maxx ** 3)

    vi_ppp_list: list[np.ndarray] = []
    vi_pmm_list: list[np.ndarray] = []
    z_ppp_list: list[np.ndarray] = []
    z_pmm_list: list[np.ndarray] = []
    nvi_ppp_stack = []
    nvi_pmm_stack = []
    nz_ppp_stack = []
    nz_pmm_stack = []

    upper_mask = np.triu(np.ones((K, K), dtype=bool), k=1)
    lower_mask = np.tril(np.ones((K, K), dtype=bool), k=-1)

    for i in range(K):
        # Dpp[k, l] = Ppp[i, k] - Ppp[l, i]  (R: outer(Ppp[i,], Ppp[,i], "-"))
        Dpp = np.subtract.outer(Ppp[i, :], Ppp[:, i])
        Dmm = np.subtract.outer(Pmm[i, :], Pmm[:, i])

        TFpp = np.zeros((K, K), dtype=bool)
        TFmm = np.zeros((K, K), dtype=bool)
        # Replace NaNs in difference matrices (for the violation check) with 0.
        Dpp_no_nan = np.where(np.isnan(Dpp), 0.0, Dpp)
        Dmm_no_nan = np.where(np.isnan(Dmm), 0.0, Dmm)
        TFpp[upper_mask & (Dpp_no_nan > minvi)] = True
        TFpp[lower_mask & (Dpp_no_nan < -minvi)] = True
        TFmm[upper_mask & (Dmm_no_nan < -minvi)] = True
        TFmm[lower_mask & (Dmm_no_nan > minvi)] = True

        vi_ppp = np.abs(TFpp.astype(float) * Dpp_no_nan)
        vi_pmm = np.abs(TFmm.astype(float) * Dmm_no_nan)
        vi_ppp_list.append(vi_ppp)
        vi_pmm_list.append(vi_pmm)
        nvi_ppp_stack.append(vi_ppp)
        nvi_pmm_stack.append(vi_pmm)

        # Z-scores per row
        sample11 = x_isrf[:, i] == 1
        sample00 = x_isrf[:, i] == 0
        z_ppp = _z_block(sample11, x, x_isrf, p1_order, n, j_count, ncat, plus=True, sign_matrix=vi_ppp)
        z_pmm = _z_block(sample00, x, x_isrf, p1_order, n, j_count, ncat, plus=False, sign_matrix=vi_pmm)
        z_ppp_list.append(z_ppp)
        z_pmm_list.append(z_pmm)
        nz_ppp_stack.append(z_ppp)
        nz_pmm_stack.append(z_pmm)

    nvi_ppp = np.vstack(nvi_ppp_stack)
    nvi_pmm = np.vstack(nvi_pmm_stack)
    nz_ppp = np.nan_to_num(np.vstack(nz_ppp_stack), nan=0.0, posinf=0.0, neginf=0.0)
    nz_pmm = np.nan_to_num(np.vstack(nz_pmm_stack), nan=0.0, posinf=0.0, neginf=0.0)

    n_vi_ppp = np.sign(nvi_ppp).sum(axis=0)
    n_vi_pmm = np.sign(nvi_pmm).sum(axis=0)
    n_vi_total = np.sign(np.vstack([nvi_ppp, nvi_pmm])).sum(axis=0)

    max_vi_ppp = nvi_ppp.max(axis=0)
    max_vi_pmm = nvi_pmm.max(axis=0)
    max_vi_total = np.vstack([nvi_ppp, nvi_pmm]).max(axis=0)

    sum_vi_ppp = nvi_ppp.sum(axis=0)
    sum_vi_pmm = nvi_pmm.sum(axis=0)
    sum_vi_total = np.vstack([nvi_ppp, nvi_pmm]).sum(axis=0)

    n_z_ppp = np.sign(nz_ppp).sum(axis=0)
    n_z_pmm = np.sign(nz_pmm).sum(axis=0)
    n_z_total = n_z_ppp + n_z_pmm
    max_z_ppp = nz_ppp.max(axis=0)
    max_z_pmm = nz_pmm.max(axis=0)
    max_z_total = np.maximum(max_z_ppp, max_z_pmm)

    results = {
        "Ppp": Ppp,
        "Pmm": Pmm,
        "ac": ac,
        "vi": {"Ppp": vi_ppp_list, "Pmm": vi_pmm_list},
        "n_vi": {"Ppp": n_vi_ppp, "Pmm": n_vi_pmm, "total": n_vi_total},
        "max_vi": {"Ppp": max_vi_ppp, "Pmm": max_vi_pmm, "total": max_vi_total},
        "sum_vi": {"Ppp": sum_vi_ppp, "Pmm": sum_vi_pmm, "total": sum_vi_total},
        "z": {"Ppp": z_ppp_list, "Pmm": z_pmm_list},
        "n_z": {"Ppp": n_z_ppp, "Pmm": n_z_pmm, "total": n_z_total},
        "max_z": {"Ppp": max_z_ppp, "Pmm": max_z_pmm, "total": max_z_total},
    }

    hi = coefHTiny(x)["Hi"]

    return {
        "results": results,
        "I_item": i_item,
        "I_step": i_step,
        "I_labels": i_labels,
        "Hi": hi,
        "minvi": minvi,
        "ncat": ncat,
        "N": n,
    }
