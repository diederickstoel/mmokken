import itertools
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from mokken_py.core.weights import allPatterns, weights


def _build_z(maxx):
    pats = allPatterns(2, maxx + 1)
    y = np.tile(pats.reshape(1, -1), (maxx, 1))
    row = np.repeat(np.arange(1, maxx + 1), y.shape[1]).reshape(maxx, -1)
    z = np.where(y < row, 0.0, 1.0)
    return z.reshape(-1, maxx * 2, order="C")


def _score_weights_for_order(order_1based, maxx):
    z = _build_z(maxx)
    z = z[:, np.asarray(order_1based, dtype=int) - 1]
    return np.apply_along_axis(lambda x: np.sum(x * np.cumsum(np.abs(x - 1))), 1, z)


def _admissible_orders_within_item(cumrel, maxx):
    names = np.arange(1, len(cumrel) + 1)
    order_desc = np.argsort(-cumrel, kind="mergesort")
    y = cumrel[order_desc]
    y_names = names[order_desc]

    unique_vals = []
    for v in y:
        if v not in unique_vals:
            unique_vals.append(v)

    groups = []
    for v in unique_vals:
        idx = y_names[y == v].astype(int).tolist()
        if len(idx) <= 1:
            groups.append([[idx[0]]])
            continue

        valid = []
        for perm in itertools.permutations(idx):
            p = np.asarray(perm)
            p1 = p[(p >= 1) & (p <= maxx)]
            p2 = p[(p >= maxx + 1) & (p <= maxx * 2)]
            ok1 = len(p1) == 0 or np.all(p1 == np.sort(p1))
            ok2 = len(p2) == 0 or np.all(p2 == np.sort(p2))
            if ok1 and ok2:
                valid.append(list(perm))
        groups.append(valid)

    orders = []
    for combo in itertools.product(*groups):
        flat = []
        for part in combo:
            flat.extend(part)
        orders.append(flat)
    return orders


def test_allpatterns_layout_matches_r_behavior():
    # Source mapping:
    # - R/MLweight.R::allPatterns
    out = allPatterns(2, 3)
    expected = np.array(
        [
            [0, 0, 0, 1, 1, 1, 2, 2, 2],
            [0, 1, 2, 0, 1, 2, 0, 1, 2],
        ],
        dtype=float,
    )
    assert np.array_equal(out, expected)


def test_weights_tie_averaging_matches_manual_admissible_permutation_average():
    # Source mapping:
    # - R/internalFunctions.R::weights
    x = np.array(
        [
            [0, 0],
            [1, 1],
            [2, 2],
        ],
        dtype=float,
    )
    maxx = 2
    out = weights(x, maxx=maxx)

    rel1 = np.array([(x[:, 0] == lv).sum() for lv in range(maxx + 1)], dtype=float)
    rel2 = np.array([(x[:, 1] == lv).sum() for lv in range(maxx + 1)], dtype=float)
    cumrel = np.concatenate([np.cumsum(rel1[::-1])[::-1][1:], np.cumsum(rel2[::-1])[::-1][1:]])

    orders = _admissible_orders_within_item(cumrel, maxx=maxx)
    expected = np.mean([_score_weights_for_order(o, maxx=maxx) for o in orders], axis=0, keepdims=True)

    assert out.shape == expected.shape
    assert np.allclose(out, expected)


def test_weights_constrained_itemstep_order_is_applied():
    x = np.array(
        [
            [0, 0],
            [1, 0],
            [1, 1],
            [2, 1],
            [2, 2],
        ],
        dtype=float,
    )
    maxx = 2
    # Constrained ordering (no ties): rank of flattened matrix [4,2,3,1].
    itemstep_order = np.array([[4, 2], [3, 1]], dtype=float)
    out = weights(x, maxx=maxx, **{"itemstep.order": itemstep_order})
    expected = _score_weights_for_order([4, 2, 3, 1], maxx=maxx)
    assert np.allclose(out, expected)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available for golden comparison")
def test_weights_golden_against_r_reference():
    repo = Path(__file__).resolve().parents[1]
    internal = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "internalFunctions.R"
    mlweight = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "MLweight.R"
    internal_r = str(internal).replace("\\", "/")
    mlweight_r = str(mlweight).replace("\\", "/")

    # Tie-heavy case triggers permutation averaging path.
    x = np.array([[0, 0], [1, 1], [2, 2]], dtype=int)
    out = weights(x, maxx=2)

    r_code = f"""
source('{internal_r}')
source('{mlweight_r}')
X <- matrix(c(0,0,1,1,2,2), ncol=2, byrow=TRUE)
w <- weights(X, maxx=2, minx=0)
cat(paste(as.numeric(w), collapse=','))
"""
    proc = subprocess.run(["Rscript", "-e", r_code], check=True, capture_output=True, text=True)
    r_vals = np.array([float(v) for v in proc.stdout.strip().split(",")], dtype=float)
    assert np.allclose(out.reshape(-1), r_vals)
