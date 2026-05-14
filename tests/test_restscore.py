import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyreadr
import pytest

from mmokken.diagnostics.restscore import check_restscore


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
    thresholds = [[-0.5, 0.5], [-0.3, 0.7], [-0.4, 0.6], [-0.2, 0.8], [-0.1, 0.9]]
    cols = []
    for k in range(j):
        cols.append(np.digitize(t + 0.1 * rng.standard_normal(n), thresholds[k % len(thresholds)]))
    return np.column_stack(cols).astype(float)


def _load_acl_communality():
    root = Path(__file__).resolve().parents[1]
    acl = pyreadr.read_r(
        str(root / "r_reference" / "mokken_3.1.2" / "mokken" / "data" / "acl.rda")
    )["acl"]
    arr = acl.to_numpy() if hasattr(acl, "to_numpy") else np.asarray(acl)
    return np.asarray(arr[:, 0:10], dtype=float)


def test_check_restscore_returns_expected_shapes():
    x = _synthetic_monotone_data(n=200, seed=1, j=4)
    out = check_restscore(x, minvi=0.03, minsize=40)
    j = x.shape[1]
    expected_pairs = j * (j - 1) // 2
    assert len(out["results"]) == expected_pairs
    m = out["m"]
    rvm = (m - 1) ** 2 + 1
    for r in out["results"]:
        assert r["violation_matrix"].shape == (rvm, 8)
        # summary matrix cols = 6 + 2*(m-1)
        assert r["summary_matrix"].shape[1] == 6 + 2 * (m - 1)


def test_check_restscore_raises_on_undersized_sample():
    x = _synthetic_monotone_data(n=10, seed=2, j=4)
    with pytest.raises(ValueError, match="Sample size less than Minsize"):
        check_restscore(x, minsize=50)


def test_check_restscore_raises_on_too_few_items():
    x = _synthetic_monotone_data(n=200, seed=3, j=4)[:, :2]
    with pytest.raises(ValueError, match="Less than 3 items"):
        check_restscore(x, minsize=40)


def test_check_restscore_zero_violations_on_perfect_guttman():
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
    out = check_restscore(x, minvi=0.03, minsize=10)
    for r in out["results"]:
        total = r["violation_matrix"][-1]
        # #vi and sum should be 0 for a perfectly Guttman pattern
        assert total[1] == 0
        assert total[4] == 0


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_check_restscore_golden_against_r_reference():
    repo = Path(__file__).resolve().parents[1]
    rscript = _rscript_path()
    x = _load_acl_communality()

    py = check_restscore(x, minvi=0.03, minsize=30)

    n, j = x.shape
    x_vec = ",".join(str(int(v)) for v in x.reshape(-1))
    script = f"""
source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
source('r_reference/mokken_3.1.2/mokken/R/check.restscore.R')
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
res <- check.restscore(X, minvi=0.03, minsize=30)
for(k in seq_along(res$results)) {{
  vm <- res$results[[k]]$VIOLATION.MATRIX
  cat('VM', k, paste(as.numeric(vm), collapse=','), sep='|')
  cat('\\n')
}}
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

    r_vm_per_pair = {}
    for line in proc.stdout.splitlines():
        if not line.startswith("VM"):
            continue
        _, idx, vals = line.split("|", 2)
        r_vm_per_pair[int(idx) - 1] = np.array([float(v) for v in vals.split(",")], dtype=float)

    for k, r_flat in r_vm_per_pair.items():
        py_vm = py["results"][k]["violation_matrix"]
        r_vm = r_flat.reshape(py_vm.shape, order="F")
        py_clean = np.nan_to_num(py_vm, nan=0.0)
        r_clean = np.nan_to_num(r_vm, nan=0.0)
        assert np.allclose(py_clean, r_clean, atol=1e-9), (
            f"violation matrix mismatch on pair {k}"
        )
