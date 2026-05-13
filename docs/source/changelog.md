# Changelog

## Unreleased

- Restructured to `src/mmokken/` layout; package import name `mmokken`.
- Consolidated legacy `mokken/` helpers (`coefHTiny`, `check_data`, `check_ml_data`) into the `mmokken` namespace.
- Added `pyproject.toml` (hatchling backend) and editable install support.
- Added ADR 0001 fixing the scikit-learn estimator convention as the v0.1 public API contract.
- Added Sphinx docs skeleton.
- Added GitHub Actions matrix for pytest on Python 3.10–3.12 across Linux/macOS/Windows, plus an R-golden parity job.
- Added `mmokken.search.ga` skeleton — placeholder for pure-Python GA AISP.
