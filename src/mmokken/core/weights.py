"""Port of Mokken weight helpers.

Original R sources:
- r_reference/mokken_3.1.2/mokken/R/internalFunctions.R::weights
- r_reference/mokken_3.1.2/mokken/R/MLweight.R::allPatterns

Complexity risk:
- In tie-heavy cases, `weights` enumerates admissible permutations of tied
  item-step orders and averages resulting weights.
- Let tie groups have sizes g1..gk; worst-case candidate count is
  product(factorial(gi)). This can grow very quickly (permutation explosion).
"""

from __future__ import annotations

import itertools
import math
import warnings

import numpy as np


def allPatterns(J, m):
    """R-compatible allPatterns (matrix J x m^J)."""
    J = int(J)
    m = int(m)
    grid = [list(range(m)) for _ in range(J)]
    # R's expand.grid with transpose and row reversal.
    cols = list(itertools.product(*grid[::-1]))
    mat = np.array(cols, dtype=float).T
    return mat


def _perm(v):
    """R-style full permutation matrix for a value vector."""
    return list(itertools.permutations(v, len(v)))


def _build_z(maxx):
    pats = allPatterns(2, maxx + 1)
    y = np.tile(pats.reshape(1, -1), (maxx, 1))
    row = np.repeat(np.arange(1, maxx + 1), y.shape[1]).reshape(maxx, -1)
    z = np.where(y < row, 0.0, 1.0)
    z = z.reshape(-1, maxx * 2, order="C")
    return z


def _weights_from_order(ords_1based, maxx):
    z = _build_z(maxx)
    z = z[:, np.asarray(ords_1based, dtype=int) - 1]
    return np.apply_along_axis(lambda x: np.sum(x * np.cumsum(np.abs(x - 1))), 1, z)


def weights(X, maxx=None, minx=0, itemstep_order=None, **kwargs):
    """R/internalFunctions.R::weights.

    Parameters mirror R naming intentionally for first parity phase.
    """
    x = np.asarray(X)
    if x.ndim != 2:
        raise ValueError("X must be 2-dimensional")

    if maxx is None:
        maxx = int(np.max(x))
    else:
        maxx = int(maxx)
    minx = int(minx)

    if "itemstep.order" in kwargs:
        if itemstep_order is not None:
            raise TypeError("Specify only one of itemstep_order or itemstep.order")
        itemstep_order = kwargs.pop("itemstep.order")
    if kwargs:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(kwargs.keys())}")

    if x.shape[1] != 2:
        warnings.warn(
            "X contains more than two columns. Only first two columns will be used",
            UserWarning,
            stacklevel=2,
        )
        x = x[:, :2]

    levels = np.arange(minx, maxx + 1)
    rel1 = np.array([(x[:, 0] == lv).sum() for lv in levels], dtype=float)
    rel2 = np.array([(x[:, 1] == lv).sum() for lv in levels], dtype=float)

    cumrel = np.concatenate(
        [
            np.cumsum(rel1[::-1])[::-1][1:],
            np.cumsum(rel2[::-1])[::-1][1:],
        ]
    )

    # 1-based names after sorting, matching R approach.
    names = np.arange(1, len(cumrel) + 1)
    order_desc = np.argsort(-cumrel, kind="mergesort")
    y = cumrel[order_desc]
    y_names = names[order_desc]

    if np.any(np.diff(y) == 0) and itemstep_order is None:
        # Split ties by unique values in descending encounter order.
        seen = []
        for val in y:
            if val not in seen:
                seen.append(val)

        o = []
        for val in seen:
            m = y_names[y == val].astype(int).tolist()
            if len(m) <= 1:
                o.append(m)
            else:
                o.append([list(p) for p in _perm(m)])

        # Ensure fixed ordering within each item for tied-step permutations.
        for idx, group in enumerate(o):
            if len(group) == 0:
                continue
            if isinstance(group[0], int):
                continue

            selected = []
            for h in group:
                h_arr = np.asarray(h, dtype=int)
                first_mask = (h_arr >= 1) & (h_arr <= maxx)
                second_mask = (h_arr >= maxx + 1) & (h_arr <= maxx * 2)
                if np.any(first_mask) and np.any(second_mask):
                    ok = np.all(h_arr[first_mask] == np.sort(h_arr[first_mask])) and np.all(
                        h_arr[second_mask] == np.sort(h_arr[second_mask])
                    )
                else:
                    i1 = np.all(h_arr[first_mask] == np.sort(h_arr[first_mask])) if np.any(first_mask) else False
                    i2 = np.all(h_arr[second_mask] == np.sort(h_arr[second_mask])) if np.any(second_mask) else False
                    ok = (int(i1) + int(i2)) > 0
                if ok:
                    selected.append(h)
            o[idx] = selected

        # Expand grid over tie-groups and average resulting weights.
        combos = itertools.product(*o)
        w = []
        for combo in combos:
            ords = []
            for part in combo:
                if isinstance(part, int):
                    ords.append(part)
                else:
                    ords.extend(list(part))
            w.append(_weights_from_order(ords, maxx))

        w = np.vstack(w)
        wr = np.mean(w, axis=0, keepdims=True)
    else:
        if itemstep_order is None:
            ords = y_names
        else:
            flat = np.asarray(itemstep_order).reshape(-1)
            # R's rank default: ties.method = "average".
            ords = _rank_average_1based(flat)
        wr = _weights_from_order(ords, maxx)

    return wr


def _rank_average_1based(values):
    """Approximate R rank(..., ties.method='average') with 1-based ranks."""
    values = np.asarray(values, dtype=float)
    sorter = np.argsort(values, kind="mergesort")
    ranks = np.empty_like(values, dtype=float)
    i = 0
    n = len(values)
    while i < n:
        j = i
        while j + 1 < n and values[sorter[j + 1]] == values[sorter[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        ranks[sorter[i : j + 1]] = avg_rank
        i = j + 1
    return ranks
