import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from mmokken.search.normal import search_normal


def _synthetic_monotone_data(n=300, seed=0):
    rng = np.random.default_rng(seed)
    t = rng.standard_normal(n)
    x = np.column_stack(
        [
            np.digitize(t + 0.1 * rng.standard_normal(n), [-0.5, 0.5]),
            np.digitize(t + 0.1 * rng.standard_normal(n), [-0.3, 0.7]),
            np.digitize(t + 0.1 * rng.standard_normal(n), [-0.4, 0.6]),
        ]
    ).astype(float)
    return x


def test_search_normal_returns_matrix_with_expected_shape():
    # Source mapping: R/search.normal.R::search.normal
    x = _synthetic_monotone_data()
    out = search_normal(x, lowerbound=[0.1, 0.3], alpha=0.05, StartSet=False, type_z="Z", test_Hi=False)
    assert out.shape == (x.shape[1], 2)
    assert np.all(np.isfinite(out))


def test_search_normal_finds_single_scale_on_synthetic_data():
    x = _synthetic_monotone_data()
    out = search_normal(x, lowerbound=[0.1], alpha=0.05, StartSet=False, type_z="Z", test_Hi=False)
    assert np.array_equal(out.reshape(-1), np.array([1.0, 1.0, 1.0]))


def test_search_normal_invalid_startset_warns_and_ignores():
    x = _synthetic_monotone_data()
    with pytest.warns(UserWarning, match="Start set of items is not properly defined"):
        out = search_normal(x, lowerbound=[0.1], alpha=0.05, StartSet=True, type_z="Z", test_Hi=False)
    assert out.shape == (x.shape[1], 1)


def test_search_normal_raises_when_item_has_no_variance():
    x = np.array(
        [
            [0, 1, 0],
            [0, 2, 1],
            [0, 0, 1],
            [0, 1, 2],
        ],
        dtype=float,
    )
    with pytest.raises(ValueError, match="At least one item has no variance"):
        search_normal(x, lowerbound=[0.1], alpha=0.05, StartSet=False, type_z="Z", test_Hi=False)


def test_search_normal_level_two_ignored_for_type_z():
    x = _synthetic_monotone_data()
    lvl = np.repeat(np.arange(1, 151), 2)
    with pytest.warns(UserWarning, match="level.two.var is ignored for type.z = 'Z'"):
        out = search_normal(x[: lvl.shape[0], :], lowerbound=[0.1], alpha=0.05, StartSet=False, type_z="Z", test_Hi=False, level_two_var=lvl)
    assert out.shape == (3, 1)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available for golden comparison")
def test_search_normal_golden_against_r_reference():
    repo = Path(__file__).resolve().parents[1]
    internal = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "internalFunctions.R"
    mlweight = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "MLweight.R"
    coefh_r = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "coefH.R"
    coefz_r = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "coefZ.R"
    search_r = repo / "r_reference" / "mokken_3.1.2" / "mokken" / "R" / "search.normal.R"

    internal_rp = str(internal).replace("\\", "/")
    mlweight_rp = str(mlweight).replace("\\", "/")
    coefh_rp = str(coefh_r).replace("\\", "/")
    coefz_rp = str(coefz_r).replace("\\", "/")
    search_rp = str(search_r).replace("\\", "/")

    x = _synthetic_monotone_data()
    py = search_normal(x, lowerbound=[0.1], alpha=0.05, StartSet=False, type_z="Z", test_Hi=False)

    x_vec = ",".join(str(int(v)) for v in x.reshape(-1))
    r_code = f"""
source('{internal_rp}')
source('{mlweight_rp}')
source('{coefh_rp}')
source('{coefz_rp}')
source('{search_rp}')
X <- matrix(c({x_vec}), ncol=3, byrow=TRUE)
res <- search.normal(X, lowerbound=0.1, alpha=0.05, StartSet=FALSE, verbose=FALSE, type.z='Z', test.Hi=FALSE, level.two.var=NULL)
cat(paste(as.numeric(res), collapse=','))
"""
    proc = subprocess.run(["Rscript", "-e", r_code], check=True, capture_output=True, text=True)
    r_vals = np.array([float(v) for v in proc.stdout.strip().split(",")], dtype=float).reshape(py.shape, order="F")
    assert np.array_equal(py, r_vals)

