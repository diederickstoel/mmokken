# mmokken

**Multidimensional non-parametric measurement models in Python.**

`mmokken` is the implementation track of an ongoing PhD research programme on
the comparison of language-derived and behaviour-derived item orderings, with a
multidimensional extension of Mokken scale analysis. The package is the
infrastructure for that work and is intended as a community resource. See
[`docs/research_proposal.docx`](docs/research_proposal.docx) for the full frame.

> **Status: alpha.** v0.1 targets numerical parity with the R `mokken` package
> on the unidimensional core. Multidimensional Stoel-H and parametric IRT
> families (Rasch, 2PL, GRM, md-2PL) follow in subsequent releases under a
> unified scikit-learn-style estimator API (see ADR
> [`docs/decisions/0001-scikit-learn-estimator-api.md`](docs/decisions/0001-scikit-learn-estimator-api.md)).

## Installation

```bash
pip install mmokken
```

Editable install from a clone:

```bash
git clone https://github.com/dstoel/mmokken
cd mmokken
pip install -e ".[dev,test,docs]"
```

Python ≥ 3.10. Core dependencies: `numpy`, `scipy`, `pandas`.
Plotting requires `mmokken[plot]`.

## Quickstart

```python
import numpy as np
from mmokken import aisp, coefH

X = np.array(...)  # respondents × items, integer 0..k

assignment = aisp(X, lowerbound=0.3)
h_stats = coefH(X, se=False)
print(h_stats["H"], h_stats["Hi"])
```

## Current scope (v0.1.0.dev0)

R parity (functional surface):

- `aisp` (normal search path; GA in progress)
- `coefH`, `coefHTiny`
- `coefZ`
- `search_normal`
- `check_data`, `check_ml_data`

Deferred / in progress (tracked in
[`migration_journal.md`](migration_journal.md)):

- `check.monotonicity`, `check.restscore`, `check.pmatrix`, `check.reliability`,
  `check.iio`, `check.bounds`, `check.ca`, `check.errors`, `check.norms`
- Plot / summary helpers
- Multilevel (`MLcoefH`, `MLcoefZ`, `MLweight`, `level_two_var` branches)
- GA AISP body (skeleton in
  [`src/mmokken/search/ga.py`](src/mmokken/search/ga.py); pure-Python target)
- Stoel-H multi-scale metric (separate publication track)

## Repository layout

```
src/mmokken/         Package source
  __init__.py        Public API
  core/              coefH, coefHTiny, coefZ, weights, transforms
  search/            aisp, search_normal, search_ga (skeleton)
  validation.py      check_data, check_ml_data
tests/               pytest suite; golden tests against R reference when
                     Rscript is available
docs/                Sphinx documentation + research_proposal + decisions
r_reference/         Read-only R `mokken` source used by golden tests
reference/           Legacy MSPWIN5 binary + manual
data/                MSP-format example datasets
migration_journal.md Chronological port log
migration_report.md  Inventory of R package functions and porting plan
```

## Running the tests

```bash
pytest -q
```

Golden tests against the R reference are skipped automatically when `Rscript` is
not on the PATH. To run them, install R ≥ 4.3 and ensure `Rscript` resolves.

## Citing

A citation file (`CITATION.cff`) will be added with the v0.1.0 release.

## License

GPL-3.0-or-later (inherits from the R `mokken` package this work ports).
