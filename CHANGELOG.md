# Changelog

All notable changes to `mmokken` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-14

First public release. Unidimensional Mokken Scale Analysis with three-way
numerical validation against R `mokken` 3.1.2 and MSPWIN 5 (2003).

### Added

- **Scalability coefficients**: `coefH`, `coefHTiny`, `coefZ` for Loevinger
  H coefficients and Z-statistics at pair, item, and scale level. SE/CI
  branches of `coefH` ported for one-level data; multilevel deferred to a
  later release.
- **Automated Item Selection Procedure (AISP)**: `aisp` with both the
  sequential normal search (`search='normal'`) and the genetic-algorithm
  search (`search='ga'`). The GA is a pure-Python port of the C++ kernel
  in R `mokken`, validated distributionally against the R reference.
- **Diagnostic checks** (`mmokken.diagnostics`):
  - `check_monotonicity` — manifest-monotonicity violations per item-step.
  - `check_restscore` — pairwise non-intersection violations.
  - `check_pmatrix` — P(++)/P(--) matrices with non-intersection
    diagnostics.
  - `check_reliability` — MS (Sijtsma-Molenaar), Cronbach's α, Guttman's
    λ₂, item-rest correlations. LCRC branch (requires `poLCA`) deferred.
  - `check_errors` — Guttman G+ and Mokken O+ person-fit indices with
    med-couple-adjusted upper fences.
- **Utilities** (`mmokken.utils`): `recode` (reverse coding), `twoway`
  (two-way imputation of missing values).
- **I/O** (`mmokken.io`): `load_msp_dataset` reads the legacy MSP 5
  `.dat` + `.var` format. Encoding fallback chain (utf-8 → cp1252 → latin1).
- **Three-way parity benchmark**: `scripts/run_three_way_parity.py`
  reproduces the MSP 5 ↔ R `mokken` ↔ Python `mmokken` comparison on the
  bundled MSP 5 odour-annoyance dataset (828 × 17). Results are committed
  to `docs/parity_results.md`.
- **Documentation**: Sphinx skeleton in `docs/source/`, ADR fixing the
  scikit-learn estimator API as the public-API contract in
  `docs/decisions/0001-scikit-learn-estimator-api.md`.
- **CI**: GitHub Actions matrix runs the test suite on Python 3.10/3.11/3.12
  across Ubuntu/macOS/Windows, plus a dedicated R-golden parity job and an
  advisory lint+mypy job.

### Fixed

- During the three-way parity validation, three latent bugs were
  discovered and fixed in `mmokken.coefH`'s SE-branch and the
  `mmokken.core.weights` helper. The bugs were silently producing
  incorrect H/Hi/Hij values from `coefH(se=True)` for matrices with
  more than one item-pair; the original unit tests asserted only output
  shapes, not values, so the bugs went undetected until the cross-tool
  validation. After the fix, Python ↔ R parity holds to better than
  1e-9 on all deterministic functions, including `se.H`, `se.Hi`,
  `se.Hij`. See `docs/parity_results.md` for details.

### Known limitations

- Multilevel branches (`level_two_var` paths in `coefH`, `coefZ`,
  `search_normal`, `aisp`, `check_monotonicity`, etc.; the `MLcoefH`,
  `MLcoefZ`, `MLweight` functions) raise `NotImplementedError`. They
  will be ported in a later release once the multidimensional core
  (mMokken) lands.
- The LCRC branch of `check_reliability` raises `NotImplementedError`
  (requires the R-side `poLCA` package; a pure-Python equivalent is out
  of scope for v0.1).
- The scikit-learn-style estimator classes (`MokkenScale.fit/transform`)
  are specified in ADR 0001 but not yet implemented; the functional API
  is the only working surface in v0.1.0.
- Plot and summary helpers for diagnostic results are not yet provided.

[Unreleased]: https://github.com/diederickstoel/mmokken/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/diederickstoel/mmokken/releases/tag/v0.1.0
