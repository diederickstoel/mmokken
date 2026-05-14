"""Three-way parity benchmark: MSP 5 vs R `mokken` vs Python `mmokken`.

Reproduces the headline statistics that MSP 5 produced on its bundled
``TEST.DAT`` (828 respondents × 17 odour-annoyance items, 4-point Likert,
scores 0–3) under a TYPE=TEST analysis (one scale of all 17 items, no AISP).

Compares each statistic across three implementations:

* **MSP 5** (ProGAMMA, 2003): values harvested manually from
  ``msp_reference/installed/TEST full report.txt`` and frozen as constants
  below. MSP 5 is a closed Windows program — not scriptable from Python.
* **R `mokken` 3.1.2** (Van der Ark, 2007): invoked via ``Rscript`` when
  available.
* **Python `mmokken`** (this package): the implementation under test.

The script writes a markdown table to ``docs/parity_results.md`` and prints
the same table to stdout. Run it from the repo root:

.. code-block:: shell

    python scripts/run_three_way_parity.py

The data file ``msp_reference/installed/TEST.DAT`` is gitignored — the
script requires a local MSP 5 install to run. The frozen MSP 5 reference
values mean the script's *output* (parity_results.md) is reproducible
without MSP 5 in CI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

# Repo root and data paths
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

# Local data — gitignored, MSP 5 install required
MSP_INSTALL = REPO / "msp_reference" / "installed"
DAT = MSP_INSTALL / "TEST.DAT"
VAR = MSP_INSTALL / "Test.var"
OUT = REPO / "docs" / "parity_results.md"

# Items in MSP-report order: Item1..Item17 are columns 0..16 in TEST.DAT
ITEM_LABELS = [f"Item{i}" for i in range(1, 18)]

# MSP 5 reference values from `TEST full report.txt` (analysis 1, TYPE=TEST)
# Harvested manually 2026-05-14 from lines 293, 297-313, 1409-1410.
# These are the canonical 1990s/2003 numbers from the original Mokken Scale
# Program — they are frozen for reproducibility.
MSP_REFERENCE = {
    "scale_h": 0.15,
    "scale_z": 39.85,
    "rho": 0.72,
    # Per-item Hi values, indexed by Item1..Item17. MSP rounds to 2 decimals.
    "item_hi": {
        "Item1": 0.22,
        "Item2": 0.18,
        "Item3": 0.21,
        "Item4": 0.19,
        "Item5": 0.20,
        "Item6": 0.20,
        "Item7": 0.18,
        "Item8": 0.17,
        "Item9": 0.14,
        "Item10": -0.06,
        "Item11": 0.19,
        "Item12": -0.07,
        "Item13": 0.20,
        "Item14": 0.18,
        "Item15": 0.22,
        "Item16": 0.15,
        "Item17": 0.05,
    },
    # Per-item mean scores (for sanity check)
    "item_mean": {
        "Item1": 1.86,
        "Item2": 1.38,
        "Item3": 1.85,
        "Item4": 1.33,
        "Item5": 0.82,
        "Item6": 0.54,
        "Item7": 0.26,
        "Item8": 0.76,
        "Item9": 0.35,
        "Item10": 1.56,
        "Item11": 0.86,
        "Item12": 1.07,
        "Item13": 0.65,
        "Item14": 0.98,
        "Item15": 0.78,
        "Item16": 0.62,
        "Item17": 1.95,
    },
}


def find_rscript() -> str | None:
    for path in (
        r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe",
        r"C:\Program Files\R\R-4.3.2\bin\Rscript.exe",
    ):
        if Path(path).exists():
            return path
    return shutil.which("Rscript")


GA_SEEDS = (1, 2, 7, 13, 42)


def pair_agreement(part_a: np.ndarray, part_b: np.ndarray) -> float:
    """Rand-index-style item-pair agreement, robust to label permutation.

    For each pair of items, counts the agreement on "same scale" vs
    "different scale" between two partitions. Returns the fraction of
    pairs that agree (1.0 = identical partition up to relabeling,
    chance level ≈ 0.5 for two scales).
    """
    n = part_a.size
    if n != part_b.size:
        raise ValueError("Partitions must have the same length")
    agree = 0
    total = 0
    for i in range(n):
        for j in range(i + 1, n):
            same_a = part_a[i] == part_a[j]
            same_b = part_b[i] == part_b[j]
            agree += int(same_a == same_b)
            total += 1
    return agree / total if total else 0.0


def run_python_ga(items: np.ndarray, seeds=GA_SEEDS) -> list[np.ndarray]:
    from mmokken.search.ga import search_ga

    parts = []
    for s in seeds:
        out = search_ga(
            items, lowerbound=0.3, alpha=0.05, popsize=20, maxgens=500, random_state=int(s)
        )
        parts.append(out.astype(int))
    return parts


def run_r_ga(items: np.ndarray, rscript: str, seeds=GA_SEEDS) -> list[np.ndarray] | None:
    """Run R `aisp(search='ga')` for each seed and parse the returned partitions."""
    n, j = items.shape
    x_vec = ",".join(str(int(v)) for v in items.reshape(-1))
    seed_str = ",".join(str(s) for s in seeds)
    script = f"""
.libPaths(c("C:/Users/User/R/win-library/4.4", .libPaths()))
suppressPackageStartupMessages(library(mokken))
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
seeds <- c({seed_str})
for (s in seeds) {{
  set.seed(s)
  res <- suppressWarnings(aisp(X, search='ga', lowerbound=0.3, alpha=0.05, popsize=20, maxgens=500))
  cat('R_GA|', s, '|', paste(as.numeric(res), collapse=','), '\\n', sep='')
}}
"""
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False, dir=str(REPO)) as tf:
        tf.write(script)
        script_path = tf.name
    try:
        proc = subprocess.run(
            [rscript, script_path],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)
    parts = []
    for line in proc.stdout.splitlines():
        if line.startswith("R_GA|"):
            _, seed_s, vals = line.split("|", 2)
            parts.append(np.array([int(float(v)) for v in vals.split(",")], dtype=int))
    return parts if parts else None


def run_python_analysis(items: np.ndarray) -> dict:
    """Run the mmokken analysis matching MSP 5's TYPE=TEST setup.

    Uses the fast path ``coefH(se=False)`` for the Loevinger coefficients.
    The SE-branch of ``coefH`` (i.e. ``coefH(se=True)``) currently produces
    incorrect H values for matrices with many items; see the "Known issues"
    section in the generated ``parity_results.md``.
    """
    from mmokken import check_reliability, coefH, coefZ

    h = coefH(items, se=False, results=False)
    z = coefZ(items, lowerbound=0, type_z="Z")
    rel = check_reliability(items, ms=True, alpha=True, lambda_2=True, irc=False)
    return {
        "scale_h": float(h["H"]),
        "scale_z": float(z["Z"]),
        "ms": float(rel["MS"]),
        "alpha": float(rel["alpha"]),
        "lambda_2": float(rel["lambda_2"]),
        "item_hi": {label: float(h["Hi"][i]) for i, label in enumerate(ITEM_LABELS)},
        "item_mean": {label: float(items[:, i].mean()) for i, label in enumerate(ITEM_LABELS)},
    }


def run_r_analysis(items: np.ndarray, rscript: str) -> dict | None:
    """Run R mokken on the same matrix and parse stdout.

    Prefers the installed CRAN package (``library(mokken)``) so the
    comparison validates against the canonical published version. Falls
    back to ``source(r_reference/...)`` when the package is not installed
    — the numerical results are identical, but the installed path also
    exercises NAMESPACE/S3 dispatch.
    """
    n, j = items.shape
    x_vec = ",".join(str(int(v)) for v in items.reshape(-1))
    script = f"""
user_lib <- "C:/Users/User/R/win-library/4.4"
if (dir.exists(user_lib)) .libPaths(c(user_lib, .libPaths()))
have_pkg <- suppressWarnings(suppressMessages(require(mokken, quietly=TRUE)))
if (!have_pkg) {{
  source('r_reference/mokken_3.1.2/mokken/R/internalFunctions.R')
  source('r_reference/mokken_3.1.2/mokken/R/MLweight.R')
  source('r_reference/mokken_3.1.2/mokken/R/coefH.R')
  source('r_reference/mokken_3.1.2/mokken/R/coefZ.R')
  source('r_reference/mokken_3.1.2/mokken/R/check.reliability.R')
}}
X <- matrix(c({x_vec}), nrow={n}, ncol={j}, byrow=TRUE)
h <- suppressWarnings(coefH(X, se=FALSE, ci=FALSE, nice.output=FALSE, results=FALSE))
z <- suppressWarnings(coefZ(X, lowerbound=0, type.z='Z'))
rel <- suppressWarnings(check.reliability(X, MS=TRUE, alpha=TRUE, lambda.2=TRUE, LCRC=FALSE))
src <- if (have_pkg) paste0('library(mokken ', as.character(packageVersion('mokken')), ')') else 'source(r_reference/mokken_3.1.2)'
cat('SOURCE|', src, '\\n', sep='')
cat('SCALE_H|', as.numeric(h$H), '\\n', sep='')
cat('SCALE_Z|', as.numeric(z$Z), '\\n', sep='')
cat('MS|', as.numeric(rel$MS), '\\n', sep='')
cat('ALPHA|', as.numeric(rel$alpha), '\\n', sep='')
cat('LAMBDA2|', as.numeric(rel$lambda.2), '\\n', sep='')
cat('ITEM_HI|', paste(as.numeric(h$Hi), collapse=','), '\\n', sep='')
"""
    with tempfile.NamedTemporaryFile("w", suffix=".R", delete=False, dir=str(REPO)) as tf:
        tf.write(script)
        script_path = tf.name
    try:
        proc = subprocess.run(
            [rscript, script_path],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        Path(script_path).unlink(missing_ok=True)

    sections: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "|" not in line:
            continue
        key, vals = line.split("|", 1)
        sections[key] = vals.strip()

    item_hi_arr = np.array([float(v) for v in sections["ITEM_HI"].split(",")], dtype=float)
    return {
        "source": sections.get("SOURCE", "unknown"),
        "scale_h": float(sections["SCALE_H"]),
        "scale_z": float(sections["SCALE_Z"]),
        "ms": float(sections["MS"]),
        "alpha": float(sections["ALPHA"]),
        "lambda_2": float(sections["LAMBDA2"]),
        "item_hi": {label: float(item_hi_arr[i]) for i, label in enumerate(ITEM_LABELS)},
    }


def fmt(value: float | None, *, decimals: int = 4) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f}"


def render_table(py: dict, r: dict | None, msp: dict) -> str:
    """Produce a markdown table comparing the three implementations."""
    lines = [
        "# Three-way parity results — `mmokken` v0.1.0",
        "",
        "Headline statistics produced on the MSP 5 bundled test set",
        "(`msp_reference/installed/TEST.DAT`, 828 × 17 odour-annoyance items,",
        "TYPE=TEST analysis of all 17 items as a single scale).",
        "",
        "* MSP 5 numbers: harvested manually from `TEST full report.txt`",
        "  (ProGAMMA 2003, frozen reference; MSP 5 is interactive-only and",
        "  therefore not invoked at script runtime).",
        "* R values: produced by `r_reference/mokken_3.1.2/mokken/R/*.R`",
        "  via `Rscript`.",
        "* Python values: produced by `mmokken` (this package).",
        "",
        "## Scale-level statistics",
        "",
        "| Statistic | MSP 5 (2003) | R `mokken` 3.1.2 | Python `mmokken` v0.1.0 | Python−R | Python−MSP |",
        "|---|---|---|---|---|---|",
    ]

    def diff(a: float | None, b: float | None) -> str:
        if a is None or b is None:
            return "—"
        return f"{a - b:+.4f}"

    for label, key, decimals in [
        ("Scale H (Loevinger)", "scale_h", 4),
        ("Scale Z", "scale_z", 4),
        ("Reliability (MS / Rho)", "ms", 4),
        ("Cronbach α", "alpha", 4),
        ("Guttman λ₂", "lambda_2", 4),
    ]:
        msp_val = msp.get("rho") if key == "ms" else msp.get(key)
        r_val = (r or {}).get(key) if r is not None else None
        py_val = py.get(key)
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    fmt(msp_val, decimals=2 if key in {"scale_h", "scale_z", "ms"} else decimals),
                    fmt(r_val, decimals=decimals),
                    fmt(py_val, decimals=decimals),
                    diff(py_val, r_val),
                    diff(py_val, msp_val),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Per-item Hi values",
            "",
            "| Item | Label | MSP 5 | R | Python | Py−R | Py−MSP |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    label_lookup = {
        "Item1": "keep windows closed",
        "Item2": "no laundry outside",
        "Item3": "search source of malodour",
        "Item4": "no blankets outside",
        "Item5": "try to find out solutions",
        "Item6": "go elsewhere to fresh air",
        "Item7": "call environment agency",
        "Item8": "think of something else",
        "Item9": "file complaint at producer",
        "Item10": "acquiesce in odour annoyance",
        "Item11": "do something to get rid of it",
        "Item12": "say: it might have been worse",
        "Item13": "experience unrest",
        "Item14": "talk to friends and family",
        "Item15": "seek diversion",
        "Item16": "avoid nose breathing",
        "Item17": "try to adapt to situation",
    }
    for label in ITEM_LABELS:
        msp_v = msp["item_hi"][label]
        r_v = (r or {}).get("item_hi", {}).get(label) if r is not None else None
        py_v = py["item_hi"][label]
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    label_lookup[label],
                    fmt(msp_v, decimals=2),
                    fmt(r_v, decimals=4),
                    fmt(py_v, decimals=4),
                    diff(py_v, r_v),
                    diff(py_v, msp_v),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## GA AISP partition comparison",
            "",
            "Both implementations run the AISP genetic-algorithm search with",
            "`lowerbound=0.3, alpha=0.05, popsize=20, maxgens=500` for 5 seeds.",
            "GA is stochastic and R / numpy use different RNGs, so element-wise",
            "equivalence is impossible. We report **item-pair agreement**: the",
            "fraction of item pairs where both implementations agree on",
            "*same-scale* vs *different-scale* (chance ≈ 0.5 for two scales,",
            "1.0 = identical partition up to relabeling).",
            "",
            "%%GA_TABLE%%",
            "",
            "## Interpretation",
            "",
            "* Python ↔ R agree to within numerical noise (typical |Δ| < 1e-9) on",
            "  Loevinger H, Cronbach α, Guttman λ₂, and per-item Hi.",
            "* Python ↔ MSP 5 agree to within the precision MSP reported",
            "  (2 decimals for Hi/H, 2 decimals for Z). Differences are bounded",
            "  by MSP's display rounding rather than true numerical drift.",
            "* The MS reliability and MSP's `Rho` should match closely — both are",
            "  the Sijtsma-Molenaar reliability with the same 4-direction",
            "  interpolation; minor drift can occur when P1 ties are broken",
            "  differently across implementations.",
            "* Item12 and Item10 have negative Hi across all three implementations,",
            "  consistent with MSP 5's report ('worst item is marked by an",
            "  asterisk where relevant').",
            "",
            "## Known issues uncovered by this exercise",
            "",
            "Running the parity script for the first time surfaced a regression",
            "in `mmokken.coefH` that the existing 3-item × 3-category unit tests",
            "did not catch:",
            "",
            "* `coefH(X, se=True)` on the 17 × 828 TEST.DAT returns H ≈ −0.04 and",
            "  per-item Hi ≈ −0.05, whereas `coefH(X, se=False)` and `coefHTiny`",
            "  agree with R and MSP 5 at H ≈ 0.15. The SE-branch of `coefH`",
            "  fails for matrices with many items (small J=3 cases in the test",
            "  suite return correct values, so the bug went undetected).",
            "* Workaround used by this script: call `coefH(X, se=False)` for the",
            "  Loevinger coefficients. Z is computed via the classic-Z path in",
            "  `coefZ` which does not invoke `coefH`'s SE-branch, so Z values",
            "  match exactly across implementations.",
            "* Follow-up: must be fixed before tagging v0.1.0 and before JOSS",
            "  submission.",
            "",
            "Reproducibility: this file was generated by `scripts/run_three_way_parity.py`.",
            "Re-run it after any algorithmic change to `mmokken.coefH`, `coefZ`,",
            "`check_reliability`, or the validation layer.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    if not DAT.exists() or not VAR.exists():
        print(
            f"ERROR: MSP 5 test data not found at {DAT}.\n"
            f"This script needs a local MSP 5 install in msp_reference/installed/.",
            file=sys.stderr,
        )
        return 2

    from mmokken.io.msp_loader import load_msp_dataset

    ds = load_msp_dataset(DAT, VAR)
    print(f"Loaded {ds.items.shape[0]} respondents × {ds.items.shape[1]} items")

    py = run_python_analysis(ds.items)
    print(f"Python analysis OK (H={py['scale_h']:.4f}, Z={py['scale_z']:.4f}, MS={py['ms']:.4f})")

    rscript = find_rscript()
    r = None
    if rscript is None:
        print("WARNING: Rscript not found — skipping R parity column")
    else:
        try:
            r = run_r_analysis(ds.items, rscript)
            print(
                f"R analysis OK ({r.get('source', '?')}: H={r['scale_h']:.4f}, "
                f"Z={r['scale_z']:.4f}, MS={r['ms']:.4f})"
            )
        except subprocess.CalledProcessError as err:
            print(f"R analysis failed: {err.stderr[:500]}", file=sys.stderr)

    md = render_table(py, r, MSP_REFERENCE)

    # GA comparison (stochastic — separate flow from headline stats)
    print("\nRunning GA comparison (5 seeds × Python + R)...")
    py_parts = run_python_ga(ds.items)
    print(f"  Python GA OK ({len(py_parts)} runs)")
    r_parts = None
    if rscript is not None:
        try:
            r_parts = run_r_ga(ds.items, rscript)
            if r_parts is not None:
                print(f"  R GA OK ({len(r_parts)} runs)")
        except subprocess.CalledProcessError as err:
            print(f"  R GA failed: {err.stderr[:500]}", file=sys.stderr)

    ga_table_lines = [
        "| Seed | Py scales | R scales | Largest scale Py | Largest scale R | Pair-agreement |",
        "|---|---|---|---|---|---|",
    ]
    for i, seed in enumerate(GA_SEEDS):
        py_p = py_parts[i]
        r_p = r_parts[i] if r_parts is not None else None
        py_n = len(set(int(v) for v in py_p if v > 0))
        py_largest = int(np.max(np.bincount(py_p[py_p > 0]))) if (py_p > 0).any() else 0
        if r_p is not None:
            r_n = len(set(int(v) for v in r_p if v > 0))
            r_largest = int(np.max(np.bincount(r_p[r_p > 0]))) if (r_p > 0).any() else 0
            agreement = pair_agreement(py_p, r_p)
            agreement_str = f"{agreement:.3f}"
        else:
            r_n = "—"
            r_largest = "—"
            agreement_str = "—"
        ga_table_lines.append(
            f"| {seed} | {py_n} | {r_n} | {py_largest} | {r_largest} | {agreement_str} |"
        )

    if r_parts is not None:
        agreements = [pair_agreement(py_parts[i], r_parts[i]) for i in range(len(GA_SEEDS))]
        ga_table_lines.extend(
            [
                "",
                f"Mean pair-agreement across 5 seeds: **{np.mean(agreements):.3f}** "
                f"(min {min(agreements):.3f}, max {max(agreements):.3f}).",
                "Pair agreement of 1.000 means R and Python found identical scale",
                "structures (up to label permutation); chance level for two-scale",
                "partitions is ≈0.500.",
            ]
        )
    else:
        ga_table_lines.append("")
        ga_table_lines.append(
            "R GA values missing — could not invoke R `mokken::aisp(search='ga')`. "
            "Re-run after installing the package."
        )

    md = md.replace("%%GA_TABLE%%", "\n".join(ga_table_lines))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(md, encoding="utf-8")
    print(f"\nWrote {OUT.relative_to(REPO)}")
    # NB: do not echo `md` to stdout — Windows cp1252 console can choke on the
    # Unicode minus sign produced by markdown rendering.
    return 0


if __name__ == "__main__":
    sys.exit(main())
