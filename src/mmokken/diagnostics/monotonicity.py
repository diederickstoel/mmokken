"""Manifest monotonicity check for Mokken scales.

Original R source:
- r_reference/mokken_3.1.2/mokken/R/check.monotonicity.R::check.monotonicity

This implements the single-level (no ``level.two.var``) path. The R multilevel
branch uses ``MLcoefH`` and aggregated rest-scores and is deferred to a later
increment (raises ``NotImplementedError`` here).
"""

from __future__ import annotations

import numpy as np

from ..core.scalability import coefHTiny
from ..validation import check_data


def _default_minsize(n: int) -> int:
    """Mirror R defaults: N>=500 -> N/10, N<=250 -> N/3, N<150 -> 50.

    Source: R/check.monotonicity.R lines 8-10.
    """
    if n < 150:
        return 50
    if n <= 250:
        return n // 3
    if n >= 500:
        return n // 10
    return n // 5


def _build_groups(sorted_rest: np.ndarray, minsize: int, n: int) -> list[int]:
    """Build cumulative right-edge positions for rest-score groups.

    Mirrors the R `repeat` loop in check.monotonicity. Returns a list of
    1-based right-edge positions (counts of respondents in groups 1..L-1).

    Source: R/check.monotonicity.R lines 34-40.
    """
    # 1-based logic transposed: group = [last 1-based idx where sorted == sorted[minsize-1]]
    target = sorted_rest[minsize - 1]
    g0 = int(np.max(np.where(sorted_rest == target)[0])) + 1  # 1-based
    group = [g0]
    while n - max(group) >= minsize:
        target = sorted_rest[minsize + max(group) - 1]
        g_next = int(np.max(np.where(sorted_rest == target)[0])) + 1
        group.append(g_next)
    # R: group <- group[-length(group)]  -> drop the last element after break
    group.pop()
    return group


def check_monotonicity(
    X,
    minvi: float = 0.03,
    minsize: int | None = None,
    level_two_var=None,
) -> dict:
    """Manifest monotonicity check.

    Parameters
    ----------
    X : array_like
        Respondents × items, integer-coded item scores (validated by
        :func:`mmokken.check_data`).
    minvi : float, default 0.03
        Minimum violation size to flag (per item-step).
    minsize : int, optional
        Minimum group size for rest-score groupings. Defaults to the R
        heuristic based on N (see :func:`_default_minsize`).
    level_two_var : array_like, optional
        Cluster identifiers for the multilevel path. Currently deferred —
        passing a non-None value raises ``NotImplementedError``.

    Returns
    -------
    dict
        Keys: ``results`` (list of per-item dicts with ``label``,
        ``summary_matrix``, ``violation_matrix``, ``settings``),
        ``I_labels`` (item labels), ``Hi`` (item-level H from
        :func:`coefHTiny`), ``m`` (number of response categories), ``X``
        (validated score matrix).
    """
    if level_two_var is not None:
        raise NotImplementedError(
            "check_monotonicity level.two.var branch is not yet ported."
        )

    x = check_data(X)
    n, j_count = x.shape
    m = int(np.max(x)) + 1

    if minsize is None:
        minsize = _default_minsize(n)
    if n < minsize:
        raise ValueError("Sample size less than Minsize")
    if minsize > n / 2:
        raise ValueError("Minsize value is too high")

    # R: R <- as.matrix(X) %*% (matrix(1,J,J) - diag(J))
    # Rest-score matrix: R[:, j] = sum of all OTHER items for each respondent.
    rest = x @ (np.ones((j_count, j_count)) - np.eye(j_count))

    results: list[dict] = []
    i_labels = [f"C{j + 1}" for j in range(j_count)]

    cum_col_count = m - 1  # cumulative columns 1..m-1
    score_levels = np.arange(m, dtype=float)  # 0, 1, ..., m-1

    for j in range(j_count):
        sorted_r = np.sort(rest[:, j])
        group_edges_1b = _build_groups(sorted_r, minsize, n)

        # Sizes per group: diffs of [0, *edges, N]
        edges_with_bounds = [0, *group_edges_1b, n]
        sizes = np.array(
            [edges_with_bounds[i + 1] - edges_with_bounds[i] for i in range(len(edges_with_bounds) - 1)],
            dtype=int,
        )
        # Convert position-edges to score-edges (R: group <- c(sorted.R[group], max(sorted.R)))
        score_edges = np.array(
            [sorted_r[e - 1] for e in group_edges_1b] + [float(np.max(sorted_r))],
            dtype=float,
        )
        L = len(score_edges)

        # Lo Score, Hi Score
        hi_score = score_edges.copy()
        lo_score = np.empty(L, dtype=float)
        lo_score[0] = float(np.min(sorted_r))
        lo_score[1:] = score_edges[:-1] + 1.0

        # Group membership per respondent: 1-based
        # R: apply(1 - outer(R[,j], group, "<="),1,sum) + 1
        member = (1 - (rest[:, j][:, None] <= score_edges[None, :]).astype(int)).sum(axis=1) + 1

        summary_matrix = np.zeros((L, 4 + 2 * m), dtype=float)
        summary_matrix[:, 0] = np.arange(1, L + 1)
        summary_matrix[:, 1] = lo_score
        summary_matrix[:, 2] = hi_score
        summary_matrix[:, 3] = sizes

        for i in range(L):
            mask = member == (i + 1)
            ni = int(sizes[i])
            scores_i = x[mask, j].astype(int)
            freq = np.bincount(scores_i, minlength=m).astype(float)
            summary_matrix[i, 4 : 4 + m] = freq
            summary_matrix[i, 4 + m] = float((freq * score_levels).sum()) / ni if ni > 0 else 0.0
            # Cumulative P(X >= k) for k = 1..m-1
            # R: rev(cumsum(rev(freq))/Ni)[2:m]
            rev_cum = np.cumsum(freq[::-1])[::-1] / ni if ni > 0 else np.zeros(m)
            summary_matrix[i, 4 + m + 1 : 4 + 2 * m + 1] = rev_cum[1:m]

        # violation matrix: (m, 10) — last row is "Total"
        violation_matrix = np.zeros((m, 10), dtype=float)
        freq_cols = summary_matrix[:, 4 : 4 + m]  # (L, m)
        cum_cols = summary_matrix[:, 4 + m + 1 : 4 + 2 * m + 1]  # (L, m-1)

        # #ac per item-step: number of admissible comparisons
        # R: outer condition with > 1e-10 AND < 0.999... AND upper.tri
        nac = np.zeros(cum_col_count, dtype=int)
        upper_tri = np.triu(np.ones((L, L), dtype=bool), k=1)  # strict upper triangle
        for step in range(cum_col_count):
            col = cum_cols[:, step]
            left = (col > 1e-10)[:, None]  # column-wise (across rows of LxL)
            right = (col < 0.999999999999)[None, :]  # row-wise
            nac[step] = int((left & right & upper_tri).sum())
        violation_matrix[: m - 1, 0] = nac
        violation_matrix[m - 1, 0] = nac.sum()

        # For each item-step, find violations via outer difference of cumulative probs
        for step in range(cum_col_count):
            cum_col = cum_cols[:, step]
            V = cum_col[:, None] - cum_col[None, :]  # (L,L) outer subtraction
            # R: V[row(V) <= col(V)] <- 0 -> keep only strict lower triangle (row > col)
            lower_mask = np.tril(np.ones((L, L), dtype=bool), k=-1)
            V = np.where(lower_mask, V, 0.0)
            # R: V[V >= -minvi] <- 0  -> keep only V < -minvi (true downward violations)
            V = np.where(V >= -minvi, 0.0, V)

            violation_matrix[step, 1] = float(np.ceil(np.abs(V)).sum())  # #vi
            violation_matrix[step, 3] = float(np.abs(V).max())  # maxvi

            if violation_matrix[step, 3] > minvi:
                violation_matrix[step, 4] = float(np.abs(V).sum())  # sum
                # freqd: (L, 2) — cumulative bin sums at this item-step
                # R: cbind(apply(freq[,1:i],1,sum), apply(freq[,(i+1):m],1,sum))
                left_sum = freq_cols[:, : step + 1].sum(axis=1)
                right_sum = freq_cols[:, step + 1 :].sum(axis=1)
                # Z = abs(sign(-V) * 2 * (sqrt(outer(b+1, a+1)) - sqrt(outer(a, b))) /
                #          sqrt(outer(b, a, "+") + outer(a, b, "+") - 1))
                a = left_sum
                b = right_sum
                num = 2 * (
                    np.sqrt(np.outer(b + 1, a + 1)) - np.sqrt(np.outer(a, b))
                )
                den = np.sqrt(np.outer(b, a) * 0 + np.add.outer(b, a) + np.add.outer(a, b) - 1)
                # Handle den == 0 cleanly (no observations)
                with np.errstate(invalid="ignore", divide="ignore"):
                    Z = np.abs(np.sign(-V) * num / den)
                Z = np.nan_to_num(Z, nan=0.0, posinf=0.0, neginf=0.0)
                zmax = float(Z.max())
                violation_matrix[step, 6] = zmax  # zmax
                # group indices: R uses min(col(Z)[Z==zmax]) and min(row(Z)[Z==zmax])
                # col/row in R are 1-based for matrix positions
                argmax_idx = np.argwhere(Z == zmax)
                if argmax_idx.size:
                    # R col(Z)[Z==zmax] gives column indices; min(...) is smallest column.
                    violation_matrix[step, 7] = int(argmax_idx[:, 1].min() + 1)
                    violation_matrix[step, 8] = int(argmax_idx[:, 0].min() + 1)
                violation_matrix[step, 9] = int(np.sign(Z[Z > 1.6449]).sum())

        # Total row aggregates
        violation_matrix[m - 1, 1] = violation_matrix[: m - 1, 1].sum()
        with np.errstate(invalid="ignore", divide="ignore"):
            violation_matrix[:, 2] = np.where(
                violation_matrix[:, 0] > 0,
                violation_matrix[:, 1] / violation_matrix[:, 0],
                0.0,
            )
        violation_matrix[m - 1, 3] = violation_matrix[: m - 1, 3].max()
        violation_matrix[m - 1, 4] = violation_matrix[: m - 1, 4].sum()
        with np.errstate(invalid="ignore", divide="ignore"):
            violation_matrix[:, 5] = np.where(
                violation_matrix[:, 0] > 0,
                violation_matrix[:, 4] / violation_matrix[:, 0],
                0.0,
            )
        violation_matrix[m - 1, 6] = violation_matrix[: m - 1, 6].max()
        violation_matrix[m - 1, 9] = violation_matrix[: m - 1, 9].sum()

        results.append(
            {
                "label": i_labels[j],
                "summary_matrix": summary_matrix,
                "violation_matrix": violation_matrix,
                "settings": f"Minsize = {minsize} Minvi = {minvi}",
            }
        )

    hi = coefHTiny(x)["Hi"]

    return {
        "results": results,
        "I_labels": i_labels,
        "Hi": hi,
        "m": m,
        "X": x,
    }
