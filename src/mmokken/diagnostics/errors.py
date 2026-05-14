"""Person-fit error indices (Guttman errors / Oplus).

Original R source:
- r_reference/mokken_3.1.2/mokken/R/check.errors.R::check.errors

The G+ index counts Guttman errors per respondent against the implied
item-step popularity ordering (ISRF rank). The O+ index sums per-item
unobserved-rank counts. Both indices come with robust upper fences U1 and
U2 (the latter applies a med-couple-adjusted exponential bias correction
for skewness).

This is a behaviour-first port; we deliberately follow R's tie-handling for
the rank inversion case (1000 jitter replications averaged) using an
explicit ``numpy.random.Generator`` seeded with ``seed=1`` to match R's
``set.seed(1)`` semantics for reproducibility within Python.
"""

from __future__ import annotations

import numpy as np

from ..validation import check_data


def _median_couple(x: np.ndarray) -> float:
    """Med-couple robust skewness statistic (Brys, Hubert, Struyf 2004).

    Source: R/check.errors.R::medCouple (inner function).
    """
    x = np.sort(np.asarray(x, dtype=float))
    median_x = float(np.median(x))
    xp = x[x >= median_x]
    xn = x[x <= median_x]
    p = xp.size
    n = xn.size
    if p == 0 or n == 0:
        return 0.0
    rn = np.arange(1, n + 1)
    rp = np.arange(1, p + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        # h[ii, jj] = ((xp_jj - med) - (med - xn_ii)) / (xp_jj - xn_ii)
        h = ((xp[None, :] - median_x) - (median_x - xn[:, None])) / (xp[None, :] - xn[:, None])
    # Replace entries where xp == xn (the tie-broken cells per Brys et al.)
    same = xn[:, None] == xp[None, :]
    if same.any():
        sign_block = np.sign(p - 1 - rp[None, :] - rn[:, None])
        h = np.where(same, sign_block.astype(float), h)
    return float(np.median(h))


def _isrf_matrix(x: np.ndarray, n: int, j: int, maxx: int) -> np.ndarray:
    """Build the (N, maxx*J) ISRF binary matrix in row-major (item, step) order.

    Mirrors R's ``Z`` construction in lines 26-31 of check.errors.R.
    """
    a_grid = np.arange(1, maxx + 1)
    z = (x[:, :, None] >= a_grid[None, None, :]).astype(int)  # (N, J, maxx)
    # Row-major over (item, step): for item j, step a is at column j*maxx + (a-1)
    return z.reshape(n, j * maxx)


def _gplus_one_order(z_ordered: np.ndarray) -> np.ndarray:
    """Compute G+ scores given a column-ordered ISRF matrix.

    Source: R/check.errors.R line 43 / line 49 — ``sum(x * cumsum(abs(x-1)))``.
    """
    flipped = np.abs(z_ordered - 1)
    cum = np.cumsum(flipped, axis=1)
    return (z_ordered * cum).sum(axis=1)


def check_errors(
    X,
    return_gplus: bool = True,
    return_oplus: bool = False,
) -> dict:
    """Compute Guttman G+ and/or Mokken O+ person-fit indices.

    Parameters
    ----------
    X : array_like
        Respondents × items, integer-valued (validated by
        :func:`mmokken.check_data`).
    return_gplus : bool, default True
        Return the G+ index (Guttman errors against ISRF popularity ordering).
    return_oplus : bool, default False
        Return the O+ index (per-item rank-sum form).

    Returns
    -------
    dict
        Subset of ``{Gplus, UGplus, Oplus, UOplus}`` depending on flags. The
        upper-fence dicts contain ``U1`` (1.5 IQR rule) and ``U2`` (med-couple
        adjusted), matching the R output names ``U1Gplus``/``U2Gplus`` etc.
    """
    x = check_data(X)
    n, j_count = x.shape
    maxx = int(np.max(x))

    out: dict = {}

    if return_gplus:
        z = _isrf_matrix(x, n, j_count, maxx)

        # tmp.1: per-item tabulate at scores 1..maxx (excluding 0)
        # R: apply(X, 2, tabulate, maxx) -> shape (maxx, J), row k = count of score k per item
        # Then tmp.2 = apply(tmp.1, 2, function(x) rev(cumsum(rev(x)))) -> reverse-cum down rows
        # so tmp.2[k, j] = #respondents with X[r,j] >= k (k in 1..maxx)
        tmp2 = np.zeros((maxx, j_count), dtype=int)
        for jj in range(j_count):
            counts = np.bincount(x[:, jj].astype(int), minlength=maxx + 1)[1 : maxx + 1]
            # reverse cumulative sum from the high end
            tmp2[:, jj] = np.cumsum(counts[::-1])[::-1]

        # tmp.3 = as.numeric(matrix(rank(-tmp.2), 1, maxx*J))
        # R rank uses average tie ranks by default; column-major (R fills by column)
        flat = (-tmp2.flatten(order="F")).astype(float)
        # Average ranks: equivalent to scipy.stats.rankdata default
        order = np.argsort(flat, kind="stable")
        ranks = np.empty_like(order, dtype=float)
        # average-rank assignment for ties
        i = 0
        while i < order.size:
            j2 = i
            while j2 + 1 < order.size and flat[order[j2 + 1]] == flat[order[i]]:
                j2 += 1
            avg = 0.5 * (i + 1 + j2 + 1)
            ranks[order[i : j2 + 1]] = avg
            i = j2 + 1
        tmp3 = ranks

        if len(np.unique(tmp3)) < tmp3.size:
            # Tie-broken via 1000 jitter replications averaged (R set.seed(1))
            rng = np.random.default_rng(1)
            gplus_x = np.zeros((n, 1000), dtype=float)
            tmp2_flat = tmp2.flatten(order="F").astype(float)
            for it in range(1000):
                tmp2x = tmp2_flat + rng.uniform(-0.001, 0.001, size=tmp2_flat.size)
                jittered = -tmp2x
                jorder = np.argsort(jittered, kind="stable")
                # explicit per-replication rank
                jranks = np.empty_like(jorder, dtype=float)
                jranks[jorder] = np.arange(1, jorder.size + 1)
                # column-major order from jranks
                col_order = np.argsort(jranks, kind="stable")
                z_ord = z[:, col_order]
                gplus_x[:, it] = _gplus_one_order(z_ord)
            gplus = np.round(gplus_x.mean(axis=1))
        else:
            col_order = np.argsort(tmp3, kind="stable")
            z_ord = z[:, col_order]
            gplus = _gplus_one_order(z_ord)

        q1 = float(np.quantile(gplus, 0.25))
        q3 = float(np.quantile(gplus, 0.75))
        iqr = q3 - q1
        u1 = q3 + 1.5 * iqr
        u2 = u1 * float(np.exp(3.87 * _median_couple(gplus)))
        out["Gplus"] = gplus
        out["UGplus"] = {"U1": float(u1), "U2": float(u2)}

    if return_oplus:
        num_item_points = max(int(np.unique(x[:, jj]).size) for jj in range(j_count))
        counting_mat = np.zeros((num_item_points, j_count), dtype=int)
        for jj in range(j_count):
            counts = np.bincount((x[:, jj] + 1).astype(int), minlength=num_item_points + 1)[1 : num_item_points + 1]
            counting_mat[:, jj] = counts
        # Replicate R: apply(apply(counting_mat, 2, rank), 2, rev) - 1
        # rank with ties -> average; rev flips top/bottom
        ranked = np.empty_like(counting_mat, dtype=float)
        for jj in range(j_count):
            col = counting_mat[:, jj].astype(float)
            order = np.argsort(col, kind="stable")
            r = np.empty_like(order, dtype=float)
            i = 0
            while i < order.size:
                k2 = i
                while k2 + 1 < order.size and col[order[k2 + 1]] == col[order[i]]:
                    k2 += 1
                avg = 0.5 * (i + 1 + k2 + 1)
                r[order[i : k2 + 1]] = avg
                i = k2 + 1
            ranked[:, jj] = r
        rev_ranked = ranked[::-1, :] - 1.0  # apply rev then -1

        # OScores[r, j] = rev_ranked[X[r,j], j]
        score_idx = x.astype(int)
        oscores = np.take_along_axis(rev_ranked, score_idx, axis=0)
        oplus = oscores.sum(axis=1)
        q1 = float(np.quantile(oplus, 0.25))
        q3 = float(np.quantile(oplus, 0.75))
        iqr = q3 - q1
        u1 = q3 + 1.5 * iqr
        u2 = u1 * float(np.exp(3.87 * _median_couple(oplus)))
        out["Oplus"] = oplus
        out["UOplus"] = {"U1": float(u1), "U2": float(u2)}

    return out
