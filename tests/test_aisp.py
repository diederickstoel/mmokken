import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pyreadr
import pytest

from mmokken.search.aisp import aisp


def _rscript_path():
    candidates = [
        Path(r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe"),
        Path(r"C:\Program Files\R\R-4.3.2\bin\Rscript.exe"),
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _load_acl_communality():
    root = Path(__file__).resolve().parents[1]
    acl = pyreadr.read_r(str(root / "r_reference" / "mokken_3.1.2" / "mokken" / "data" / "acl.rda"))["acl"]
    arr = acl.to_numpy() if hasattr(acl, "to_numpy") else np.asarray(acl)
    return np.asarray(arr[:, 0:10], dtype=float)


def _run_r_aisp(mode):
    root = Path(__file__).resolve().parents[1]
    rscript = _rscript_path()
    script = f"""
args <- commandArgs(trailingOnly=TRUE)
mode <- args[1]
source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
source('r_reference/mokken_3.1.2/mokken/R/MLweight.R')
source('r_reference/mokken_3.1.2/mokken/R/coefH.R')
source('r_reference/mokken_3.1.2/mokken/R/coefZ.R')
source('r_reference/mokken_3.1.2/mokken/R/search.normal.R')
source('r_reference/mokken_3.1.2/mokken/R/aisp.R')
load('r_reference/mokken_3.1.2/mokken/data/acl.rda')
Communality <- as.matrix(acl[,1:10])
if(mode == 'default') {{
  res <- aisp(Communality, lowerbound=.3, search='normal', alpha=.05, StartSet=FALSE, verbose=FALSE, type.z='Z', test.Hi=FALSE, level.two.var=NULL)
}} else if(mode == 'startset') {{
  res <- aisp(Communality, lowerbound=.3, search='normal', alpha=.05, StartSet=c(1,2), verbose=FALSE, type.z='Z', test.Hi=FALSE, level.two.var=NULL)
}} else if(mode == 'lbseq') {{
  res <- aisp(Communality, lowerbound=seq(0,.55,.05), search='normal', alpha=.05, StartSet=FALSE, verbose=FALSE, type.z='Z', test.Hi=FALSE, level.two.var=NULL)
}} else {{
  stop('unknown mode')
}}
cat('DIM=', nrow(res), 'x', ncol(res), '\\n', sep='')
cat('RES=', paste(as.numeric(res), collapse=','), '\\n', sep='')
"""
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False, dir=str(root)) as tf:
        tf.write(script)
        script_path = tf.name
    proc = subprocess.run([rscript, script_path, mode], cwd=str(root), capture_output=True, text=True, check=True)
    lines = proc.stdout.splitlines()
    dim = [ln for ln in lines if ln.startswith("DIM=")][0].split("=")[1]
    r_dim = tuple(map(int, dim.split("x")))
    vals = [ln for ln in lines if ln.startswith("RES=")][0].split("=")[1]
    r_res = np.array([float(v) for v in vals.split(",")], dtype=float).reshape(r_dim, order="F")
    Path(script_path).unlink(missing_ok=True)
    return r_res


def test_aisp_scalar_and_vector_lowerbound_shapes():
    x = _load_acl_communality()
    out1 = aisp(x, lowerbound=0.3, search="normal", alpha=0.05, StartSet=False, verbose=False, type_z="Z", test_Hi=False)
    out2 = aisp(x, lowerbound=[0.3, 0.4], search="normal", alpha=0.05, StartSet=False, verbose=False, type_z="Z", test_Hi=False)
    assert out1.shape == (10, 1)
    assert out2.shape == (10, 2)


def test_aisp_startset_parameter_runs():
    x = _load_acl_communality()
    out = aisp(x, lowerbound=0.3, search="normal", StartSet=[1, 2], verbose=False, type_z="Z", test_Hi=False)
    assert out.shape == (10, 1)
    assert np.all(np.isfinite(out))


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_aisp_golden_acl_default_example():
    # Example mapping: man/aisp.Rd -> scale <- aisp(Communality)
    x = _load_acl_communality()
    py = aisp(x, lowerbound=0.3, search="normal", alpha=0.05, StartSet=False, verbose=False, type_z="Z", test_Hi=False)
    r_res = _run_r_aisp("default")
    assert np.array_equal(py, r_res)


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_aisp_golden_acl_startset_example():
    # Example mapping: man/aisp.Rd -> aisp(Communality, StartSet=c(1,2))
    x = _load_acl_communality()
    py = aisp(x, lowerbound=0.3, search="normal", alpha=0.05, StartSet=[1, 2], verbose=False, type_z="Z", test_Hi=False)
    r_res = _run_r_aisp("startset")
    assert np.array_equal(py, r_res)


@pytest.mark.skipif(_rscript_path() is None, reason="Rscript not available for golden comparison")
def test_aisp_golden_acl_lowerbound_sequence_example():
    # Example mapping: man/aisp.Rd -> aisp(Communality, lowerbound = seq(0, .55, .05))
    x = _load_acl_communality()
    lbs = np.arange(0.0, 0.55 + 1e-12, 0.05)
    py = aisp(x, lowerbound=lbs, search="normal", alpha=0.05, StartSet=False, verbose=False, type_z="Z", test_Hi=False)
    r_res = _run_r_aisp("lbseq")
    assert np.array_equal(py, r_res)
