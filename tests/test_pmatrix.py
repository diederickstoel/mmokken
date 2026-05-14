import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyreadr
import pytest

from mmokken.diagnostics.pmatrix import check_pmatrix


def _rscript_path():
    candidates = [
        Path(r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe"),
        Path(r"C:\Program Files\R\R-4.3.2\bin\Rscript.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return shutil.which("Rscript")


def _synthetic_monotone_data(n=200, seed=0, j=4):
    rng = np.random.default_rng(seed)
    t = rng.standard_normal(n)
    thresholds = [[-0.5, 0.5], [-0.3, 0.7], [-0.4, 0.6], [-0.2, 0.8]]
    cols = []
    for k in range(j):
        cols.append(np.digitize(t + 0.1 * rng.standard_normal(n), thresholds[k % 4]))
    return np.column_stack(cols).astype(float)


def _load_acl_communality():
    root = Path(__file__).resolve().parents[1]
    acl = pyreadr.read_r(
        str(root / "r_reference" / "mokken_3.1.2" / "mokken" / "data" / "acl.rda")
    )["acl"]
    arr = acl.to_numpy() if hasattr(acl, "to_numpy") else np.asarray(acl)
    return np.asarray(arr[:, 0:10], dtype=float)


def test_check_pmatrix_returns_expected_keys_and_shapes():
    x = _synthetic_monotone_data(n=200, seed=1, j=4)
    out = check_pmatrix(x, minvi=0.03)
    res = out["results"]
    j = x.shape[1]
    maxx = int(x.max())
    K = j * maxx
    assert res["Ppp"].shape == (K, K)
    assert res["Pmm"].shape == (K, K)
    assert len(res["vi"]["Ppp"]) == K
    assert len(res["vi"]["Pmm"]) == K
    assert res["n_vi"]["total"].shape == (K,)
    # ac = (J-1)(J-2) * maxx^3
    assert res["ac"] == (j - 1) * (j - 2) * maxx ** 3


def test_check_pmatrix_within_item_blocks_are_nan_in_ppp():
    x = _synthetic_monotone_data(n=100, seed=2, j=3)
    out = check_pmatrix(x, minvi=0.03)
    Ppp = out["results"]["Ppp"]
    # After P1 reordering the within-item NaN blocks no longer align with
    # contiguous index ranges, but the *count* of NaN cells is preserved.
    j = x.shape[1]
    maxx = int(x.max())
    expected_nan = j * maxx * maxx
    assert int(np.isnan(Ppp).sum()) == expected_nan


def test_check_pmatrix_no_violations_on_perfect_guttman():
    x = np.array(
        [
            [0, 0, 0, 0],
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [1, 1, 1, 0],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
            [1, 1, 1, 1],
        ]
        * 10,
        dtype=float,
    )
    out = check_pmatrix(x, minvi=0.03)
    total_vi = out["results"]["n_vi"]["total"]
    assert int(total_vi.sum()) == 0


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_check_pmatrix_golden_against_r_reference():
    repo = Path(__file__).resolve().parents[1]
    rscript = _rscript_path()
    x = _load_acl_communality()

    py = check_pmatrix(x, minvi=0.03)

    n, j = x.shape
    x_vec = ",".join(str(int(v)) for v in x.reshape(-1))
    script = f"""
source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
source('r_reference/mokken_3.1.2/mokken/R/check.pmatrix.R')
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
res <- check.pmatrix(X, minvi=0.03)
ppp <- res$results$Ppp
pmm <- res$results$Pmm
ppp[is.na(ppp)] <- -999
pmm[is.na(pmm)] <- -999
cat('PPP|', paste(as.numeric(ppp), collapse=','), sep='')
cat('\\n')
cat('PMM|', paste(as.numeric(pmm), collapse=','), sep='')
cat('\\n')
nvi_t <- res$results$n.vi$total
cat('NVI_TOTAL|', paste(as.numeric(nvi_t), collapse=','), sep='')
cat('\\n')
"""
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False, dir=str(repo)) as tf:
        tf.write(script)
        script_path = tf.name
    try:
        proc = subprocess.run(
            [rscript, script_path],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)

    sections = {}
    for line in proc.stdout.splitlines():
        if "|" not in line:
            continue
        key, vals = line.split("|", 1)
        sections[key] = np.array([float(v) for v in vals.split(",")], dtype=float)

    py_ppp = py["results"]["Ppp"]
    r_ppp = sections["PPP"].reshape(py_ppp.shape, order="F")
    r_ppp = np.where(r_ppp == -999, np.nan, r_ppp)
    # Compare entries where both are non-NaN
    mask = ~(np.isnan(py_ppp) | np.isnan(r_ppp))
    assert np.allclose(py_ppp[mask], r_ppp[mask], atol=1e-9), "Ppp mismatch"

    py_pmm = py["results"]["Pmm"]
    r_pmm = sections["PMM"].reshape(py_pmm.shape, order="F")
    r_pmm = np.where(r_pmm == -999, np.nan, r_pmm)
    mask_m = ~(np.isnan(py_pmm) | np.isnan(r_pmm))
    assert np.allclose(py_pmm[mask_m], r_pmm[mask_m], atol=1e-9), "Pmm mismatch"

    py_nvi = py["results"]["n_vi"]["total"]
    r_nvi = sections["NVI_TOTAL"]
    assert np.array_equal(py_nvi, r_nvi), "n_vi.total mismatch"
