import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyreadr
import pytest

from mmokken.diagnostics.errors import check_errors


def _rscript_path():
    candidates = [
        Path(r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe"),
        Path(r"C:\Program Files\R\R-4.3.2\bin\Rscript.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return shutil.which("Rscript")


def _load_acl_communality():
    root = Path(__file__).resolve().parents[1]
    acl = pyreadr.read_r(
        str(root / "r_reference" / "mokken_3.1.2" / "mokken" / "data" / "acl.rda")
    )["acl"]
    arr = acl.to_numpy() if hasattr(acl, "to_numpy") else np.asarray(acl)
    return np.asarray(arr[:, 0:10], dtype=float)


def test_check_errors_gplus_shape_and_fences():
    rng = np.random.default_rng(0)
    n = 200
    j = 6
    x = rng.integers(0, 3, size=(n, j)).astype(float)
    out = check_errors(x, return_gplus=True, return_oplus=False)
    assert "Gplus" in out
    assert out["Gplus"].shape == (n,)
    assert "UGplus" in out
    assert {"U1", "U2"} <= set(out["UGplus"])
    assert out["UGplus"]["U2"] >= 0


def test_check_errors_oplus_shape_and_fences():
    rng = np.random.default_rng(0)
    x = rng.integers(0, 3, size=(150, 5)).astype(float)
    out = check_errors(x, return_gplus=False, return_oplus=True)
    assert "Oplus" in out
    assert out["Oplus"].shape == (150,)
    assert {"U1", "U2"} <= set(out["UOplus"])


def test_check_errors_perfect_guttman_yields_zero_gplus():
    # A perfectly Guttman dataset should have all-zero Guttman error count.
    x = np.array(
        [
            [0, 0, 0, 0],
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [1, 1, 1, 0],
            [1, 1, 1, 1],
        ]
        * 10,
        dtype=float,
    )
    out = check_errors(x, return_gplus=True, return_oplus=False)
    # In a perfect Guttman pattern, no respondent produces any inversion
    assert int(out["Gplus"].sum()) == 0


def test_check_errors_returns_both_when_flagged():
    rng = np.random.default_rng(7)
    x = rng.integers(0, 3, size=(80, 4)).astype(float)
    out = check_errors(x, return_gplus=True, return_oplus=True)
    assert {"Gplus", "UGplus", "Oplus", "UOplus"} <= set(out)


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_check_errors_golden_against_r_reference():
    repo = Path(__file__).resolve().parents[1]
    rscript = _rscript_path()
    x = _load_acl_communality()
    py = check_errors(x, return_gplus=True, return_oplus=True)

    n, j = x.shape
    x_vec = ",".join(str(int(v)) for v in x.reshape(-1))
    script = f"""
source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
source('r_reference/mokken_3.1.2/mokken/R/check.errors.R')
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
res <- check.errors(X, returnGplus=TRUE, returnOplus=TRUE)
cat('GPLUS|', paste(as.numeric(res$Gplus), collapse=','), sep='')
cat('\\n')
cat('OPLUS|', paste(as.numeric(res$Oplus), collapse=','), sep='')
cat('\\n')
cat('U1GPLUS|', res$UGplus$U1Gplus, sep='')
cat('\\n')
cat('U2GPLUS|', res$UGplus$U2Gplus, sep='')
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
        sections[key] = vals

    r_gplus = np.array([float(v) for v in sections["GPLUS"].split(",")], dtype=float)
    r_oplus = np.array([float(v) for v in sections["OPLUS"].split(",")], dtype=float)

    # G+ has a stochastic component when there are tied ISRF ranks (1000-rep
    # jitter average in R, mirrored here with seed=1 numpy.Generator). The two
    # RNGs differ between R and numpy, so we compare distributions instead of
    # element-wise.
    assert py["Gplus"].shape == r_gplus.shape
    py_q = np.quantile(py["Gplus"], [0.25, 0.5, 0.75])
    r_q = np.quantile(r_gplus, [0.25, 0.5, 0.75])
    assert np.allclose(py_q, r_q, atol=1.0), f"Gplus quartiles mismatch: py={py_q} r={r_q}"

    # O+ is deterministic; compare element-wise
    assert np.array_equal(py["Oplus"], r_oplus)
