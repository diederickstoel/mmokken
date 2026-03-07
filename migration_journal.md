# Mokken R → Python Migration Journal

This document tracks each Codex migration increment.

For every step include:
- Date
- Files modified
- Functions ported
- Tests added
- Edge cases preserved
- Remaining uncertainties

## Entry 1
- Date: 2026-03-07
- Step: Validation layer
- Files modified:
  - `validation.py`
  - `scalability.py`
  - `__init__.py`
  - `tests/test_scalability.py`
  - `tests/test_validation.py`
- Functions ported:
  - `check_data`
  - `check_ml_data`
  - `coefHTiny` mapping note
- Tests added:
  - `pytest` (9 tests passing)
- Edge cases preserved:
  - No missing values allowed
  - Numeric integer-only scoring
  - Nonnegative scores
  - Category normalization to start at 0
  - Maximum 10 categories
  - Warning for uneven category support
  - `check_ml_data` leaves first column unchanged
- Remaining uncertainties:
  - Exact parity of R warning vs Python warning/exception semantics.
