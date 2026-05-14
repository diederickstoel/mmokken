import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from mmokken.core.scalability import coefH
from mmokken.core.zscores import coefZ


def test_coefz_classic_z_matches_manual_formula():
    # Source mapping: R/coefZ.R::coefZ (type.z == "Z")
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
    out = coefZ(x, lowerbound=0, type_z="Z")

    N = x.shape[0]
    S = np.cov(x, rowvar=False, ddof=1)
    vars_ = np.var(x, axis=0, ddof=1)
    Sij = np.outer(vars_, vars_)
    Zij = (S * np.sqrt(N - 1)) / np.sqrt(Sij)
    np.fill_diagonal(S, 0)
    np.fill_diagonal(Sij, 0)
    np.fill_diagonal(Zij, 0)
    Zi = ((np.sum(S, axis=1) * np.sqrt(N - 1)) / np.sqrt(np.sum(Sij, axis=1))).reshape(1, -1)
    Z = float((np.sum(S) / 2.0 * np.sqrt(N - 1)) / np.sqrt(np.sum(Sij) / 2.0))

    assert np.allclose(out["Zij"], Zij)
    assert np.allclose(out["Zi"], Zi)
    assert np.isclose(out["Z"], Z)


def test_coefz_wb_uses_coefh_standard_errors():
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
    hs = coefH(x, se=True, ci=False, results=False)
    out = coefZ(x, lowerbound=0.0, type_z="WB")

    expected_zij = hs["Hij"] / hs["se.Hij"]
    np.fill_diagonal(expected_zij, 0)
    expected_zi = (hs["Hi"] / hs["se.Hi"]).reshape(1, -1)
    expected_z = hs["H"] / hs["se.H"]

    assert np.allclose(out["Zij"], expected_zij)
    assert np.allclose(out["Zi"], expected_zi)
    assert np.isclose(out["Z"], expected_z)


def test_coefz_unknown_type_warns_and_switches():
    x = np.array([[0, 0], [1, 1], [1, 0], [0, 1]], dtype=float)
    with pytest.warns(UserWarning, match="type.z = 'UNKNOWN' is unknown"):
        out = coefZ(x, lowerbound=0, type_z="UNKNOWN")
    assert out["Zij"].shape == (2, 2)


def test_coefz_lowerbound_switches_z_to_wb_with_warning():
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
    with pytest.warns(UserWarning, match="type.z has been changed to 'WB'"):
        out = coefZ(x, lowerbound=0.1, type_z="Z")
    assert "Z" in out


def test_coefz_level_two_var_not_implemented():
    x = np.array([[0, 0], [1, 1], [1, 0], [0, 1]], dtype=float)
    with pytest.raises(NotImplementedError):
        coefZ(x, lowerbound=0, type_z="Z", level_two_var=np.array([1, 1, 2, 2]))


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available for golden comparison")
def test_coefz_golden_against_r_classic_z():
    repo = Path(__file__).resolve().parents[1]
    coefz_r = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "coefZ.R"
    coefh_r = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "coefH.R"
    internal = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "internalFunctions.R"
    mlweight = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "MLweight.R"

    coefz_rp = str(coefz_r).replace("\\", "/")
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
    py = coefZ(x, lowerbound=0, type_z="Z")

    r_code = f"""
source('{internal_rp}')
source('{mlweight_rp}')
source('{coefh_rp}')
source('{coefz_rp}')
X <- matrix(c(0,0,0, 0,1,0, 1,0,1, 1,1,1, 2,1,1, 2,2,2), ncol=3, byrow=TRUE)
res <- coefZ(X, lowerbound=0, type.z='Z')
cat(paste(c(as.numeric(res$Zij), as.numeric(res$Zi), as.numeric(res$Z)), collapse=','))
"""
    proc = subprocess.run(["Rscript", "-e", r_code], check=True, capture_output=True, text=True)
    rvals = np.array([float(v) for v in proc.stdout.strip().split(",")], dtype=float)

    zij_n = py["Zij"].size
    zi_n = py["Zi"].size
    r_zij = rvals[:zij_n].reshape(py["Zij"].shape, order="F")
    r_zi = rvals[zij_n : zij_n + zi_n].reshape(py["Zi"].shape, order="F")
    r_z = rvals[-1]
    assert np.allclose(py["Zij"], r_zij)
    assert np.allclose(py["Zi"], r_zi)
    assert np.isclose(py["Z"], r_z)

