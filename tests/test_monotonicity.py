import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyreadr
import pytest

from mmokken.diagnostics.monotonicity import check_monotonicity


def _rscript_path():
    candidates = [
        Path(r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe"),
        Path(r"C:\Program Files\R\R-4.3.2\bin\Rscript.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return shutil.which("Rscript")


def _synthetic_monotone_data(n=200, seed=0):
    rng = np.random.default_rng(seed)
    t = rng.standard_normal(n)
    cols = []
    for thresholds in ([-0.5, 0.5], [-0.3, 0.7], [-0.4, 0.6], [-0.2, 0.8]):
        cols.append(np.digitize(t + 0.1 * rng.standard_normal(n), thresholds))
    return np.column_stack(cols).astype(float)


def _load_acl_communality():
    root = Path(__file__).resolve().parents[1]
    acl = pyreadr.read_r(
        str(root / "r_reference" / "mokken_3.1.2" / "mokken" / "data" / "acl.rda")
    )["acl"]
    arr = acl.to_numpy() if hasattr(acl, "to_numpy") else np.asarray(acl)
    return np.asarray(arr[:, 0:10], dtype=float)


def test_check_monotonicity_returns_expected_keys_and_shapes():
    x = _synthetic_monotone_data(n=200, seed=1)
    out = check_monotonicity(x, minvi=0.03, minsize=40)
    assert set(out) >= {"results", "I_labels", "Hi", "m", "X"}
    assert len(out["results"]) == x.shape[1]
    assert out["m"] == int(x.max()) + 1
    assert out["Hi"].shape == (x.shape[1],)
    for r in out["results"]:
        assert {"label", "summary_matrix", "violation_matrix", "settings"} <= set(r)
        # summary matrix: cols = 4 + 2*m, where m = max+1
        assert r["summary_matrix"].shape[1] == 4 + 2 * out["m"]
        # violation matrix: m rows, 10 cols
        assert r["violation_matrix"].shape == (out["m"], 10)
        # last row of violation matrix is the "Total" aggregate
        assert r["violation_matrix"][out["m"] - 1, 0] == r["violation_matrix"][: out["m"] - 1, 0].sum()


def test_check_monotonicity_raises_on_undersized_sample():
    x = _synthetic_monotone_data(n=10, seed=2)
    with pytest.raises(ValueError, match="Sample size less than Minsize"):
        check_monotonicity(x, minsize=50)


def test_check_monotonicity_raises_when_minsize_too_high():
    x = _synthetic_monotone_data(n=60, seed=3)
    with pytest.raises(ValueError, match="Minsize value is too high"):
        check_monotonicity(x, minsize=40)


def test_check_monotonicity_level_two_var_not_implemented():
    x = _synthetic_monotone_data(n=100, seed=4)
    lvl = np.repeat(np.arange(1, 51), 2)
    with pytest.raises(NotImplementedError):
        check_monotonicity(x, minsize=20, level_two_var=lvl)


def test_check_monotonicity_no_violations_on_perfect_guttman_pattern():
    # Construct a perfectly Guttman-monotone dataset: rest-score and item
    # endorsement increase together, so no #vi should be reported.
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
    out = check_monotonicity(x, minvi=0.03, minsize=10)
    # No violations should be flagged (Guttman is perfectly monotone)
    for r in out["results"]:
        total_vi = r["violation_matrix"][out["m"] - 1, 1]
        assert total_vi == 0


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_check_monotonicity_golden_against_r_reference():
    # Compares violation matrices on the acl Communality subset (small N keeps
    # the script fast). Golden equality is asserted with allclose tolerance.
    repo = Path(__file__).resolve().parents[1]
    rscript = _rscript_path()
    x = _load_acl_communality()

    py = check_monotonicity(x, minvi=0.03, minsize=30)

    n, j = x.shape
    x_vec = ",".join(str(int(v)) for v in x.reshape(-1))
    script = f"""
source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
source('r_reference/mokken_3.1.2/mokken/R/check.monotonicity.R')
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
res <- check.monotonicity(X, minvi=0.03, minsize=30)
for(j in seq_along(res$results)) {{
  vm <- res$results[[j]][[3]]
  cat('VM', j, paste(as.numeric(vm), collapse=','), sep='|')
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

    r_vm_per_item = {}
    for line in proc.stdout.splitlines():
        if not line.startswith("VM"):
            continue
        _, idx, vals = line.split("|", 2)
        r_vm_per_item[int(idx) - 1] = np.array([float(v) for v in vals.split(",")], dtype=float)

    for j, r_flat in r_vm_per_item.items():
        py_vm = py["results"][j]["violation_matrix"]
        r_vm = r_flat.reshape(py_vm.shape, order="F")
        # NaN-safe comparison: replace NaN with 0 (R writes NaN where #ac==0)
        py_vm_clean = np.nan_to_num(py_vm, nan=0.0)
        r_vm_clean = np.nan_to_num(r_vm, nan=0.0)
        assert np.allclose(py_vm_clean, r_vm_clean, atol=1e-9), (
            f"violation matrix mismatch on item {j + 1}"
        )
