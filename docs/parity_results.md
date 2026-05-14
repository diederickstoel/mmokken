# Three-way parity results — `mmokken` v0.1.0

Headline statistics produced on the MSP 5 bundled test set
(`msp_reference/installed/TEST.DAT`, 828 × 17 odour-annoyance items,
TYPE=TEST analysis of all 17 items as a single scale).

* MSP 5 numbers: harvested manually from `TEST full report.txt`
  (ProGAMMA 2003, frozen reference; MSP 5 is interactive-only and
  therefore not invoked at script runtime).
* R values: produced by `r_reference/mokken_3.1.2/mokken/R/*.R`
  via `Rscript`.
* Python values: produced by `mmokken` (this package).

## Scale-level statistics

| Statistic | MSP 5 (2003) | R `mokken` 3.1.2 | Python `mmokken` v0.1.0 | Python−R | Python−MSP |
|---|---|---|---|---|---|
| Scale H (Loevinger) | 0.15 | 0.1476 | 0.1476 | -0.0000 | -0.0024 |
| Scale Z | 39.85 | 39.8535 | 39.8535 | -0.0000 | +0.0035 |
| Reliability (MS / Rho) | 0.72 | 0.7206 | 0.7206 | +0.0000 | +0.0006 |
| Cronbach α | — | 0.6952 | 0.6952 | +0.0000 | — |
| Guttman λ₂ | — | 0.7338 | 0.7338 | +0.0000 | — |

## Per-item Hi values

| Item | Label | MSP 5 | R | Python | Py−R | Py−MSP |
|---|---|---|---|---|---|---|
| Item1 | keep windows closed | 0.22 | 0.2224 | 0.2224 | -0.0000 | +0.0024 |
| Item2 | no laundry outside | 0.18 | 0.1839 | 0.1839 | -0.0000 | +0.0039 |
| Item3 | search source of malodour | 0.21 | 0.2115 | 0.2115 | +0.0000 | +0.0015 |
| Item4 | no blankets outside | 0.19 | 0.1860 | 0.1860 | -0.0000 | -0.0040 |
| Item5 | try to find out solutions | 0.20 | 0.2010 | 0.2010 | -0.0000 | +0.0010 |
| Item6 | go elsewhere to fresh air | 0.20 | 0.2033 | 0.2033 | +0.0000 | +0.0033 |
| Item7 | call environment agency | 0.18 | 0.1797 | 0.1797 | +0.0000 | -0.0003 |
| Item8 | think of something else | 0.17 | 0.1722 | 0.1722 | +0.0000 | +0.0022 |
| Item9 | file complaint at producer | 0.14 | 0.1409 | 0.1409 | +0.0000 | +0.0009 |
| Item10 | acquiesce in odour annoyance | -0.06 | -0.0569 | -0.0569 | +0.0000 | +0.0031 |
| Item11 | do something to get rid of it | 0.19 | 0.1868 | 0.1868 | +0.0000 | -0.0032 |
| Item12 | say: it might have been worse | -0.07 | -0.0733 | -0.0733 | +0.0000 | -0.0033 |
| Item13 | experience unrest | 0.20 | 0.1986 | 0.1986 | +0.0000 | -0.0014 |
| Item14 | talk to friends and family | 0.18 | 0.1830 | 0.1830 | +0.0000 | +0.0030 |
| Item15 | seek diversion | 0.22 | 0.2167 | 0.2167 | +0.0000 | -0.0033 |
| Item16 | avoid nose breathing | 0.15 | 0.1460 | 0.1460 | -0.0000 | -0.0040 |
| Item17 | try to adapt to situation | 0.05 | 0.0508 | 0.0508 | +0.0000 | +0.0008 |

## GA AISP partition comparison

Both implementations run the AISP genetic-algorithm search with
`lowerbound=0.3, alpha=0.05, popsize=20, maxgens=500` for 5 seeds.
GA is stochastic and R / numpy use different RNGs, so element-wise
equivalence is impossible. We report **item-pair agreement**: the
fraction of item pairs where both implementations agree on
*same-scale* vs *different-scale* (chance ≈ 0.5 for two scales,
1.0 = identical partition up to relabeling).

| Seed | Py scales | R scales | Largest scale Py | Largest scale R | Pair-agreement |
|---|---|---|---|---|---|
| 1 | 4 | 3 | 8 | 8 | 0.963 |
| 2 | 2 | 3 | 8 | 8 | 0.801 |
| 7 | 3 | 3 | 8 | 8 | 0.941 |
| 13 | 2 | 3 | 8 | 8 | 0.801 |
| 42 | 2 | 2 | 8 | 8 | 0.868 |

Mean pair-agreement across 5 seeds: **0.875** (min 0.801, max 0.963).
Pair agreement of 1.000 means R and Python found identical scale
structures (up to label permutation); chance level for two-scale
partitions is ≈0.500.

## Interpretation

* Python ↔ R agree to within numerical noise (typical |Δ| < 1e-9) on
  Loevinger H, Cronbach α, Guttman λ₂, and per-item Hi.
* Python ↔ MSP 5 agree to within the precision MSP reported
  (2 decimals for Hi/H, 2 decimals for Z). Differences are bounded
  by MSP's display rounding rather than true numerical drift.
* The MS reliability and MSP's `Rho` should match closely — both are
  the Sijtsma-Molenaar reliability with the same 4-direction
  interpolation; minor drift can occur when P1 ties are broken
  differently across implementations.
* Item12 and Item10 have negative Hi across all three implementations,
  consistent with MSP 5's report ('worst item is marked by an
  asterisk where relevant').

## Known issues uncovered by this exercise

Running the parity script for the first time surfaced a regression
in `mmokken.coefH` that the existing 3-item × 3-category unit tests
did not catch:

* `coefH(X, se=True)` on the 17 × 828 TEST.DAT returns H ≈ −0.04 and
  per-item Hi ≈ −0.05, whereas `coefH(X, se=False)` and `coefHTiny`
  agree with R and MSP 5 at H ≈ 0.15. The SE-branch of `coefH`
  fails for matrices with many items (small J=3 cases in the test
  suite return correct values, so the bug went undetected).
* Workaround used by this script: call `coefH(X, se=False)` for the
  Loevinger coefficients. Z is computed via the classic-Z path in
  `coefZ` which does not invoke `coefH`'s SE-branch, so Z values
  match exactly across implementations.
* Follow-up: must be fixed before tagging v0.1.0 and before JOSS
  submission.

Reproducibility: this file was generated by `scripts/run_three_way_parity.py`.
Re-run it after any algorithmic change to `mmokken.coefH`, `coefZ`,
`check_reliability`, or the validation layer.
