"""Scalability coefficient helpers for the mmokken package.

Original R sources:
- r_reference/mokken_3.1.2/mokken/R/coefH.R::coefH
- r_reference/mokken_3.1.2/mokken/R/internalFunctions.R::coefHTiny
"""

from __future__ import annotations

import warnings

import numpy as np

from mmokken.validation import check_data

from .transforms import complete_observed_frequencies, dphi, phi
from .weights import allPatterns, weights


def coefHTiny(X):
    """Fast Loevinger H coefficients without standard errors.

    Original R source:
    - r_reference/mokken_3.1.2/mokken/R/internalFunctions.R::coefHTiny
    """
    X = np.asarray(X)
    S = np.cov(X, rowvar=False)
    X_sorted = np.sort(X, axis=0)
    Smax = np.cov(X_sorted, rowvar=False)
    Hij = S / Smax
    np.fill_diagonal(S, 0)
    np.fill_diagonal(Smax, 0)
    Hi = S.sum(axis=1) / Smax.sum(axis=1)
    H = S.sum() / Smax.sum()
    return {"Hij": Hij, "Hi": Hi, "H": H}


def coefH(
    X,
    se=True,
    ci=False,
    nice_output=True,
    level_two_var=None,
    group_var=None,
    fixed_itemstep_order=None,
    type_ci="WB",
    results=True,
):
    """Port of R/coefH.R::coefH (Loevinger's H coefficients).

    This increment implements faithful coefficient computation (`Hij`, `Hi`, `H`)
    for one-level data. R branches for SE/CI output formatting, grouped output,
    and level-two covariance estimation are intentionally deferred.
    """
    x = check_data(X)
    eps = 1e-40

    compute_ci = False if isinstance(ci, (bool, np.bool_)) and (ci is False) else True
    if compute_ci:
        raise NotImplementedError(
            "coefH CI/SE branches are not yet ported in this increment. "
            "Use se=False and ci=False for Loevinger H coefficients."
        )
    if group_var is not None:
        raise NotImplementedError("coefH group.var branch is not yet ported.")
    if level_two_var is not None:
        raise NotImplementedError("coefH level.two.var branch is not yet ported.")

    if fixed_itemstep_order is not None and not isinstance(fixed_itemstep_order, np.ndarray):
        fixed_itemstep_order = None
        warnings.warn(
            "fixed.itemstep.order is not a matrix: fixed.itemstep.order ignored",
            UserWarning,
            stacklevel=2,
        )

    if fixed_itemstep_order is not None:
        fiso = np.asarray(fixed_itemstep_order)
        cond_dim = fiso.shape[1] != x.shape[1] and fiso.shape[0] != int(np.max(x))
        cond_values = not np.array_equal(
            np.sort(fiso.reshape(-1)),
            np.arange(1, int(np.max(x)) * x.shape[1] + 1),
        )
        if cond_dim and cond_values:
            fixed_itemstep_order = None
            warnings.warn(
                "fixed.itemstep.order as incorrect dimensions and/or incorrect values: fixed.itemstep.order ignored",
                UserWarning,
                stacklevel=2,
            )

    # R fast path: coefH(..., se=FALSE, ci=FALSE, fixed.itemstep.order=NULL)
    if (not se) and fixed_itemstep_order is None:
        tiny = coefHTiny(x)
        return {"Hij": tiny["Hij"], "Hi": tiny["Hi"], "H": tiny["H"]}

    g = int(np.max(x) - np.min(x) + 1)
    J = x.shape[1]
    P = int(J * (J - 1) / 2)
    N = x.shape[0]

    if np.any(np.var(x, axis=0, ddof=1) < eps):
        raise ValueError("One or more variables have zero variance")

    row_patterns, counts = np.unique(["".join(str(int(v)) for v in row) for row in x], return_counts=True)
    lab_n = row_patterns.reshape(-1, 1)
    lab_u = np.array([str(i) for i in range(g)])
    r = len(lab_n)
    R = np.array([[int(ch) for ch in s] for s in row_patterns], dtype=float)

    lab_b = np.array(["".join(str(int(v)) for v in col) for col in allPatterns(2, g).T], dtype=object)
    Bi = np.array([s[0] for s in lab_b], dtype=object)
    Bj = np.array([s[1] for s in lab_b], dtype=object)

    U = [np.bincount(x[:, j].astype(int), minlength=g) for j in range(J)]

    WA = {}
    WY = {}
    WE = {}
    WF = {}
    pair_order = []

    for i in range(J):
        for j in range(i + 1, J):
            pair_order.append((i, j))
            if fixed_itemstep_order is None:
                w = weights(x[:, [i, j]], g - 1)
            else:
                w = weights(x[:, [i, j]], g - 1, **{"itemstep.order": fixed_itemstep_order[:, [i, j]]})

            rows = []
            for a in range(g):
                for b in range(g):
                    rows.append(((R[:, i] == a) & (R[:, j] == b)).astype(float))
            A1a = np.vstack(rows)
            WA[(i, j)] = w.reshape(1, -1) @ A1a

            Eij = (
                U[i][np.array(Bi, dtype=int)].reshape(-1, 1)
                * U[j][np.array(Bj, dtype=int)].reshape(-1, 1)
                / float(N)
            )

            Y22 = np.hstack(
                [
                    (np.equal.outer(Bi, lab_u)).astype(float),
                    (np.equal.outer(Bj, lab_u)).astype(float),
                ]
            ) * np.tile(Eij, (1, 2 * g))

            Ri = np.array([s[i] for s in row_patterns], dtype=object)
            Rj = np.array([s[j] for s in row_patterns], dtype=object)
            Z2 = np.vstack(
                [
                    (np.equal.outer(lab_u, Ri)).astype(float),
                    (np.equal.outer(lab_u, Rj)).astype(float),
                ]
            ) * np.concatenate([1.0 / U[i], 1.0 / U[j]])[:, None]
            Z2[np.isnan(Z2)] = 1.0 / eps

            YZ2 = Y22 @ Z2 - Eij @ np.full((1, r), 1.0 / float(N))
            WY[(i, j)] = w.reshape(1, -1) @ YZ2

            Fij = complete_observed_frequencies(x[:, [i, j]], 2, g)
            WF[(i, j)] = w.reshape(1, -1) @ Fij
            WE[(i, j)] = w.reshape(1, -1) @ Eij

    wf_vals = [WF[p].reshape(-1)[0] for p in pair_order]
    we_vals = [WE[p].reshape(-1)[0] for p in pair_order]
    wa_rows = np.vstack([WA[p] for p in pair_order])
    wy_rows = np.vstack([WY[p] for p in pair_order])

    g3 = np.array([wf_vals[0], *wf_vals, *we_vals], dtype=float).reshape(2 * P + 1, 1)
    G3 = np.vstack([wa_rows[0], wa_rows, wy_rows])

    A4 = np.vstack(
        [
            np.array([1.0, -1.0, *([0.0] * (J * (J - 1) - 1))], dtype=float).reshape(1, -1),
            np.hstack([np.zeros((P, 1)), np.eye(P), -np.eye(P)]),
        ]
    )
    A5 = np.hstack([np.ones((P, 1)), -np.eye(P)])
    g4 = phi(A4, g3, "log")
    g5 = phi(A5, g4, "exp").reshape(-1)
    G4 = dphi(A4, g3, G3, "log")
    G5ij = dphi(A5, g4, G4, "exp")

    Hij = np.zeros((J, J), dtype=float)
    tri = np.tril_indices(J, -1)
    Hij[tri] = g5
    Hij = Hij + Hij.T

    if P > 1:
        G3s = np.vstack(
            [
                np.sum(G3[1 : P + 1, :], axis=0),
                np.sum(G3[1 : P + 1, :], axis=0),
                np.sum(G3[P + 1 : 2 * P + 1, :], axis=0),
            ]
        )
    else:
        G3s = G3
    g3s = np.array(
        [
            np.sum(g3[1 : P + 1, :]),
            np.sum(g3[1 : P + 1, :]),
            np.sum(g3[P + 1 : 2 * P + 1, :]),
        ],
        dtype=float,
    ).reshape(-1, 1)
    A4s = np.hstack([np.ones((2, 1)), -np.eye(2)])
    A5s = np.array([[1.0, -1.0]])
    g4s = phi(A4s, g3s, "log")
    H = float(phi(A5s, g4s, "exp").reshape(-1)[0])
    G4s = dphi(A4s, g3s, G3s, "log")
    G5s = dphi(A5s, g4s, G4s, "exp")

    G3i = np.zeros((2 * J + 1, r), dtype=float)
    g3i = np.zeros((2 * J + 1, 1), dtype=float)
    for j in range(J):
        for k in range(J):
            if k > j:
                p = (j, k)
            elif k < j:
                p = (k, j)
            else:
                continue
            g3i[j + 1, 0] += WF[p].reshape(-1)[0]
            g3i[J + j + 1, 0] += WE[p].reshape(-1)[0]
            G3i[j + 1, :] += WA[p].reshape(-1)
            G3i[J + j + 1, :] += WY[p].reshape(-1)
    g3i[0, 0] = g3i[1, 0]
    G3i[0, :] = G3i[1, :]

    A4i = np.vstack(
        [
            np.array([1.0, -1.0, *([0.0] * (J * 2 - 1))], dtype=float).reshape(1, -1),
            np.hstack([np.zeros((J, 1)), np.eye(J), -np.eye(J)]),
        ]
    )
    A5i = np.hstack([np.ones((J, 1)), -np.eye(J)])
    g4i = phi(A4i, g3i, "log")
    Hi = phi(A5i, g4i, "exp").reshape(-1)
    G4i = dphi(A4i, g3i, G3i, "log")
    G5i = dphi(A5i, g4i, G4i, "exp")

    if se:
        nvec = counts.astype(float)
        acm_hij = G5ij @ (G5ij.T * nvec[:, None])
        se_hij = np.zeros((J, J), dtype=float)
        se_hij[np.tril_indices(J, -1)] = np.sqrt(np.diag(acm_hij))
        se_hij = se_hij + se_hij.T

        acm_hi = G5i @ (G5i.T * nvec[:, None])
        se_hi = np.sqrt(np.diag(acm_hi)).reshape(-1)

        acm_h = G5s @ (G5s.T * nvec[:, None])
        se_h = float(np.sqrt(np.diag(acm_h)).reshape(-1)[0])

        return {
            "Hij": Hij,
            "se.Hij": se_hij,
            "Hi": Hi,
            "se.Hi": se_hi,
            "H": H,
            "se.H": se_h,
            "covHij": acm_hij,
            "covHi": acm_hi,
            "covH": acm_h,
        }

    return {"Hij": Hij, "Hi": Hi, "H": H}
