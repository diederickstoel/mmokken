import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from mmokken.core.scalability import coefH, coefHTiny


def test_coefh_fast_path_matches_coefhtiny():
    # Source mapping: R/coefH.R::coefH fast branch (lines 75-85).
    x = np.array(
        [
            [0, 0, 0],
            [0, 1, 0],
            [1, 0, 1],
            [1, 1, 1],
            [2, 1, 1],
            [2, 2, 2],
        ],
        dtype=float,
    )
    out = coefH(x, se=False, ci=False, results=False)
    tiny = coefHTiny(x)
    assert np.allclose(out["Hij"], tiny["Hij"])
    assert np.allclose(out["Hi"], tiny["Hi"])
    assert np.isclose(out["H"], tiny["H"])


def test_coefh_fixed_itemstep_order_branch_runs_and_returns_shapes():
    x = np.array(
        [
            [0, 0, 1],
            [0, 1, 1],
            [1, 0, 0],
            [1, 1, 1],
            [2, 1, 2],
            [2, 2, 2],
        ],
        dtype=float,
    )
    fixed = np.array([[1, 3, 5], [2, 4, 6]], dtype=float)
    out = coefH(x, se=False, ci=False, fixed_itemstep_order=fixed, results=False)
    assert out["Hij"].shape == (3, 3)
    assert out["Hi"].shape == (3,)
    assert np.isscalar(out["H"])
    assert np.all(np.isfinite(out["Hij"]))
    assert np.all(np.isfinite(out["Hi"]))
    assert np.isfinite(out["H"])


def test_coefh_unsupported_branches_raise():
    x = np.array([[0, 1], [1, 0], [1, 1]], dtype=float)
    with pytest.raises(NotImplementedError):
        coefH(x, se=False, ci=0.95)
    with pytest.raises(NotImplementedError):
        coefH(x, se=False, ci=False, group_var=np.array([1, 1, 2]))
    with pytest.raises(NotImplementedError):
        coefH(x, se=False, ci=False, level_two_var=np.array([1, 1, 2]))


def test_coefh_se_branch_returns_standard_errors():
    x = np.array(
        [
            [0, 0, 0],
            [0, 1, 0],
            [1, 0, 1],
            [1, 1, 1],
            [2, 1, 1],
            [2, 2, 2],
        ],
        dtype=float,
    )
    out = coefH(x, se=True, ci=False, results=False)
    assert "se.Hij" in out and "se.Hi" in out and "se.H" in out
    assert out["se.Hij"].shape == out["Hij"].shape
    assert out["se.Hi"].shape == out["Hi"].shape
    assert np.isscalar(out["se.H"])


def test_coefh_se_branch_h_matches_fast_path_across_dimensions():
    """SE-branch must reproduce the same H/Hi/Hij as coefHTiny for any J.

    Regression test: an earlier version of the port silently produced
    nonsense H values from the SE branch for J >= 3 because the underlying
    ``weights()`` helper used numpy's row-major reshape where R uses
    column-major (the bug was uncovered by the three-way parity exercise on
    the MSP 5 odour-annoyance dataset; the existing SE-branch test above
    only asserted shapes, not values).
    """
    rng = np.random.default_rng(0)
    t = rng.standard_normal(400)
    for j_count in (3, 4, 5, 8, 10, 12):
        cols = []
        for k in range(j_count):
            thr = [-0.5 + 0.05 * k, 0.5 - 0.05 * k]
            cols.append(np.digitize(t + 0.1 * rng.standard_normal(400), thr))
        X = np.column_stack(cols).astype(float)
        tiny = coefHTiny(X)
        full = coefH(X, se=True, results=False)
        assert np.isclose(tiny["H"], full["H"], atol=1e-9), (
            f"H mismatch at J={j_count}: tiny={tiny['H']} vs se=True={full['H']}"
        )
        assert np.allclose(tiny["Hi"], full["Hi"], atol=1e-9), (
            f"Hi mismatch at J={j_count}"
        )
        # Compare off-diagonals only: coefHTiny leaves 1.0 on the diagonal
        # while the SE-branch leaves it at 0. Same convention as R.
        mask = ~np.eye(j_count, dtype=bool)
        assert np.allclose(tiny["Hij"][mask], full["Hij"][mask], atol=1e-9), (
            f"Hij off-diagonal mismatch at J={j_count}"
        )


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available for golden comparison")
def test_coefh_golden_against_r_fast_path():
    repo = Path(__file__).resolve().parents[1]
    coefh_r = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "coefH.R"
    internal = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "internalFunctions.R"
    mlweight = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "MLweight.R"

    coefh_rp = str(coefh_r).replace("\\", "/")
    internal_rp = str(internal).replace("\\", "/")
    mlweight_rp = str(mlweight).replace("\\", "/")

    x = np.array(
        [
            [0, 0, 0],
            [0, 1, 0],
            [1, 0, 1],
            [1, 1, 1],
            [2, 1, 1],
            [2, 2, 2],
        ],
        dtype=float,
    )
    py = coefH(x, se=False, ci=False, results=False)

    r_code = f"""
source('{internal_rp}')
source('{mlweight_rp}')
source('{coefh_rp}')
X <- matrix(c(0,0,0, 0,1,0, 1,0,1, 1,1,1, 2,1,1, 2,2,2), ncol=3, byrow=TRUE)
res <- coefH(X, se=FALSE, ci=FALSE, nice.output=FALSE, results=FALSE)
cat(paste(c(as.numeric(res$Hij), as.numeric(res$Hi), as.numeric(res$H)), collapse=','))
"""
    proc = subprocess.run(["Rscript", "-e", r_code], check=True, capture_output=True, text=True)
    rvals = np.array([float(v) for v in proc.stdout.strip().split(",")], dtype=float)

    hij_n = py["Hij"].size
    hi_n = py["Hi"].size
    r_hij = rvals[:hij_n].reshape(py["Hij"].shape, order="F")
    r_hi = rvals[hij_n : hij_n + hi_n]
    r_h = rvals[-1]
    assert np.allclose(py["Hij"], r_hij)
    assert np.allclose(py["Hi"], r_hi)
    assert np.isclose(py["H"], r_h)
