import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyreadr
import pytest

from mmokken.diagnostics.reliability import check_reliability


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


def test_check_reliability_returns_requested_keys():
    rng = np.random.default_rng(0)
    x = rng.integers(0, 3, size=(150, 6)).astype(float)
    out = check_reliability(x, ms=True, alpha=True, lambda_2=True, irc=True)
    assert {"MS", "alpha", "lambda_2", "irc"} <= set(out)
    assert isinstance(out["alpha"], float)
    assert 0.0 <= out["alpha"] <= 1.0 or out["alpha"] < 0  # alpha can be negative on noise data
    assert out["irc"].shape == (x.shape[1],)


def test_check_reliability_lambda2_ge_alpha():
    rng = np.random.default_rng(2)
    x = rng.integers(0, 3, size=(200, 5)).astype(float)
    out = check_reliability(x, ms=False, alpha=True, lambda_2=True)
    # Guttman's lambda_2 is always >= Cronbach alpha by construction
    assert out["lambda_2"] >= out["alpha"] - 1e-12


def test_check_reliability_lcrc_not_implemented():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 3, size=(50, 4)).astype(float)
    with pytest.raises(NotImplementedError):
        check_reliability(x, lcrc=True)


def test_check_reliability_can_request_only_specific_estimators():
    rng = np.random.default_rng(3)
    x = rng.integers(0, 3, size=(100, 5)).astype(float)
    out = check_reliability(x, ms=False, alpha=True, lambda_2=False, irc=False)
    assert set(out) == {"alpha"}


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_check_reliability_alpha_lambda2_golden_against_r_reference():
    repo = Path(__file__).resolve().parents[1]
    rscript = _rscript_path()
    x = _load_acl_communality()
    py = check_reliability(x, ms=True, alpha=True, lambda_2=True, irc=True)

    n, j = x.shape
    x_vec = ",".join(str(int(v)) for v in x.reshape(-1))
    script = f"""
source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
source('r_reference/mokken_3.1.2/mokken/R/check.reliability.R')
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
res <- check.reliability(X, MS=TRUE, alpha=TRUE, lambda.2=TRUE, LCRC=FALSE, irc=TRUE)
cat('ALPHA|', res$alpha, sep='')
cat('\\n')
cat('LAMBDA2|', res$lambda.2, sep='')
cat('\\n')
cat('MS|', res$MS, sep='')
cat('\\n')
cat('IRC|', paste(as.numeric(res$irc), collapse=','), sep='')
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

    r_alpha = float(sections["ALPHA"])
    r_lambda2 = float(sections["LAMBDA2"])
    r_ms = float(sections["MS"])
    r_irc = np.array([float(v) for v in sections["IRC"].split(",")], dtype=float)

    assert np.isclose(py["alpha"], r_alpha, atol=1e-9), f"alpha mismatch: py={py['alpha']} r={r_alpha}"
    assert np.isclose(py["lambda_2"], r_lambda2, atol=1e-9), f"lambda_2 mismatch: py={py['lambda_2']} r={r_lambda2}"
    assert np.allclose(py["irc"], r_irc, atol=1e-9), f"irc mismatch"
    # MS uses an interpolation that depends on ordering of equally-popular item-steps; tolerate small drift
    assert np.isclose(py["MS"], r_ms, atol=1e-6), f"MS mismatch: py={py['MS']} r={r_ms}"
