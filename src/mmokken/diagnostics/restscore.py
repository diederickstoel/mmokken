"""Restscore (non-intersection) diagnostic check for Mokken scales.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/check.restscore.R::check.restscore
"""

from __future__ import annotations

import numpy as np

from ..core.scalability import coefHTiny
from ..validation import check_data
from ._utils import build_groups, default_minsize

# z-threshold qnorm(.95)
_Z95 = 1.6448536269514722


def _restscore_z(group_x: np.ndarray, i: int, j: int, g: int, h: int, J: int) -> float:
    """Compute the pairwise restscore Z statistic for one (group, g, h) cell.

    Source: R/check.restscore.R lines 92-100 (the inner `if(d[gg] > 0)` block).
    The `length(Xgg[mask, ])/J` idiom in R counts rows; we use the same.
    """
    # Counts of off-diagonal pair patterns in this group
    f01 = int(np.sum((group_x[:, i] >= g) & (group_x[:, j] < h)))
    f10 = int(np.sum((group_x[:, i] < g) & (group_x[:, j] >= h)))
    f_k = min(f01, f10)
    f_n = f01 + f10
    if f_n == 0:
        return 0.0
    f_b = ((2 * f_k + 1 - f_n) ** 2 - 10 * f_n) / (12 * f_n)
    z = abs(np.sqrt(2 * f_k + 2 + f_b) - np.sqrt(2 * f_n - 2 * f_k + f_b))
    return float(z)


def check_restscore(X, minvi: float = 0.03, minsize: int | None = None) -> dict:
    """Pairwise restscore non-intersection diagnostic.

    Parameters
    ----------
    X : array_like
        Respondents × items, integer-coded item scores (validated by
        :func:`mmokken.check_data`).
    minvi : float, default 0.03
        Minimum violation size to flag.
    minsize : int, optional
        Minimum rest-score group size. Defaults to the R heuristic.

    Returns
    -------
    dict
        Keys: ``results`` (list of per-pair dicts with ``first_item``,
        ``second_item``, ``summary_matrix``, ``violation_matrix``,
        ``z_scores``), ``I_labels``, ``Hi``, ``m``.
    """
    x = check_data(X)
    n, j_count = x.shape
    m = int(np.max(x)) + 1

    if minsize is None:
        minsize = default_minsize(n)
    if n < minsize:
        raise ValueError("Sample size less than Minsize")
    if j_count < 3:
        raise ValueError("Less than 3 items. Restscore cannot be computed")

    i_labels = [f"C{j + 1}" for j in range(j_count)]
    score_steps = m - 1
    rvm = score_steps * score_steps + 1  # rows per pair (cells + Total)

    results: list[dict] = []

    # Rest-score base: row-sum of all other items
    base_rest = x @ (np.ones((j_count, j_count)) - np.eye(j_count))

    for i in range(j_count - 1):
        # Subtract X[:, i] from every column, then zero column i (mirrors R).
        rest = base_rest - x[:, i : i + 1]
        rest[:, i] = 0

        for j in range(i + 1, j_count):
            sorted_r = np.sort(rest[:, j])
            group_edges_1b = build_groups(sorted_r, minsize, n)

            edges_with_bounds = [0, *group_edges_1b, n]
            sizes = np.array(
                [
                    edges_with_bounds[g + 1] - edges_with_bounds[g]
                    for g in range(len(edges_with_bounds) - 1)
                ],
                dtype=int,
            )
            score_edges = np.array(
                [sorted_r[e - 1] for e in group_edges_1b] + [float(np.max(sorted_r))],
                dtype=float,
            )
            L = len(score_edges)

            hi_score = score_edges.copy()
            lo_score = np.empty(L, dtype=float)
            lo_score[0] = float(np.min(sorted_r))
            lo_score[1:] = score_edges[:-1] + 1.0

            member = (1 - (rest[:, j][:, None] <= score_edges[None, :]).astype(int)).sum(axis=1) + 1

            # Summary matrix: cols = 6 + 2*(m-1) =
            #   Group, Lo, Hi, N, E(X_i), E(X_j), P(X_i>=1..m-1), P(X_j>=1..m-1)
            summary_matrix = np.zeros((L, 6 + 2 * score_steps), dtype=float)
            summary_matrix[:, 0] = np.arange(1, L + 1)
            summary_matrix[:, 1] = lo_score
            summary_matrix[:, 2] = hi_score
            summary_matrix[:, 3] = sizes

            for g in range(L):
                mask = member == (g + 1)
                ni = int(sizes[g])
                xi_g = x[mask, i].astype(int)
                xj_g = x[mask, j].astype(int)
                summary_matrix[g, 4] = float(xi_g.mean()) if ni > 0 else 0.0
                summary_matrix[g, 5] = float(xj_g.mean()) if ni > 0 else 0.0
                freqi = np.bincount(xi_g, minlength=m).astype(float)
                freqj = np.bincount(xj_g, minlength=m).astype(float)
                cumi = np.cumsum(freqi[::-1])[::-1] / ni if ni > 0 else np.zeros(m)
                cumj = np.cumsum(freqj[::-1])[::-1] / ni if ni > 0 else np.zeros(m)
                summary_matrix[g, 6 : 6 + score_steps] = cumi[1:m]
                summary_matrix[g, 6 + score_steps : 6 + 2 * score_steps] = cumj[1:m]

            # Violation matrix: rows = (m-1)^2 + 1 (Total), cols =
            #   #ac, #vi, #vi/#ac, maxvi, sum, sum/#ac, zmax, #zsig
            violation_matrix = np.zeros((rvm, 8), dtype=float)
            ac = L - 1
            violation_matrix[: rvm - 1, 0] = ac

            z_scores = np.zeros((score_steps * score_steps, L), dtype=float)

            row_idx = 0
            for g in range(1, score_steps + 1):
                for h in range(1, score_steps + 1):
                    p1 = summary_matrix[:, 6 + (g - 1)]  # P(X_i >= g)
                    p2 = summary_matrix[:, 6 + score_steps + (h - 1)]  # P(X_j >= h)
                    nn = summary_matrix[:, 3]

                    if (nn * p1).sum() > (nn * p2).sum():
                        d = p2 - p1
                    else:
                        d = p1 - p2

                    d = np.where(d <= minvi, 0.0, d)
                    vi = int(np.sum(d > minvi / 2))
                    sum_vi = float(d.sum())
                    maxd = float(d.max())

                    z = np.zeros(L, dtype=float)
                    if np.any(d > 0):
                        for gg in range(L):
                            if d[gg] > 0:
                                z[gg] = _restscore_z(x[member == (gg + 1)], i, j, g, h, j_count)
                    zmax = float(np.abs(z).max())
                    zsig = int(np.sum(np.abs(z) > _Z95))

                    violation_matrix[row_idx, 1] = vi
                    violation_matrix[row_idx, 2] = vi / ac if ac > 0 else 0.0
                    violation_matrix[row_idx, 3] = maxd
                    violation_matrix[row_idx, 4] = sum_vi
                    violation_matrix[row_idx, 5] = sum_vi / ac if ac > 0 else 0.0
                    violation_matrix[row_idx, 6] = zmax
                    violation_matrix[row_idx, 7] = zsig
                    z_scores[row_idx, :] = z
                    row_idx += 1

            # Total row
            if rvm > 2:
                violation_matrix[rvm - 1, 0] = violation_matrix[: rvm - 1, 0].sum()
                violation_matrix[rvm - 1, 1] = violation_matrix[: rvm - 1, 1].sum()
                violation_matrix[rvm - 1, 4] = violation_matrix[: rvm - 1, 4].sum()
                violation_matrix[rvm - 1, 7] = violation_matrix[: rvm - 1, 7].sum()
                violation_matrix[rvm - 1, 3] = violation_matrix[: rvm - 1, 3].max()
                violation_matrix[rvm - 1, 6] = violation_matrix[: rvm - 1, 6].max()
            else:
                violation_matrix[rvm - 1, [0, 1, 3, 4, 6, 7]] = violation_matrix[0, [0, 1, 3, 4, 6, 7]]
            if violation_matrix[rvm - 1, 0] > 0:
                violation_matrix[rvm - 1, 2] = violation_matrix[rvm - 1, 1] / violation_matrix[rvm - 1, 0]
                violation_matrix[rvm - 1, 5] = violation_matrix[rvm - 1, 4] / violation_matrix[rvm - 1, 0]

            results.append(
                {
                    "first_item": i_labels[i],
                    "second_item": i_labels[j],
                    "summary_matrix": summary_matrix,
                    "violation_matrix": violation_matrix,
                    "z_scores": z_scores,
                }
            )

    hi = coefHTiny(x)["Hi"]

    return {
        "results": results,
        "I_labels": i_labels,
        "Hi": hi,
        "m": m,
    }
