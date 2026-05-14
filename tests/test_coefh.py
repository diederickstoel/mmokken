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
