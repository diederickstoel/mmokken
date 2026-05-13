# ADR 0001: scikit-learn estimator API as the public interface

- **Status:** Accepted
- **Date:** 2026-05-13
- **Deciders:** Diederick Stoel
- **Context source:** PhD research programme proposal §6.2 (Track B); chats `docs/chats/snippets.md` §6.2

## Context

The PhD research programme treats `mmokken` not as a one-to-one R port but as a
**modern measurement-model platform** in which Mokken scale analysis is one
family within a broader (m)IRT ecosystem. Phase B1 delivers a unidimensional
non-parametric core (R-parity with the R `mokken` package). Phase B2 adds the
multidimensional Stoel-H regime. Phase B3 integrates parametric IRT families
(Rasch, 2PL, GRM, md-2PL) under a unified API and is the target of the Journal
of Statistical Software package paper.

Once `mmokken` v0.1 ships on PyPI, the public API becomes load-bearing. API
changes after release force semver-major bumps and break downstream code,
including the demonstration analyses (Track A) that depend on the package. The
shape of the public surface must therefore be fixed **before** v0.1, even
though only the unidimensional core is implemented in B1.

## Decision

The public interface of `mmokken` follows the **scikit-learn estimator
convention** ([scikit-learn developer guide](https://scikit-learn.org/stable/developers/develop.html)):

1. Estimators are classes with a constructor that takes only hyperparameters,
   no data.
2. Constructor parameters are stored as attributes with the same name and are
   not mutated by `fit`.
3. `fit(X, y=None)` performs the work and returns `self`.
4. Fitted attributes end in a trailing underscore (e.g., `self.scales_`,
   `self.H_`, `self.Hi_`, `self.Hij_`).
5. `transform`, `predict`, `score` are added where the operation is well-defined
   for the family of models. For Mokken: `transform(X)` returns scale scores;
   `score(X)` returns the global H coefficient.
6. Estimators implement `get_params` / `set_params` (inherited from
   `sklearn.base.BaseEstimator`) so they compose with `Pipeline`, `GridSearchCV`,
   and `cross_validate`.
7. Input validation and conversion happens in `fit` via the existing
   `mmokken.validation.check_data` (R-parity validation) layered on top of
   sklearn's `check_array` semantics.

A minimal sketch:

```python
from sklearn.base import BaseEstimator, TransformerMixin

class MokkenScale(BaseEstimator, TransformerMixin):
    def __init__(self, lowerbound=0.3, search="normal", alpha=0.05,
                 type_z="Z", test_Hi=False, random_state=None):
        self.lowerbound = lowerbound
        self.search = search
        self.alpha = alpha
        self.type_z = type_z
        self.test_Hi = test_Hi
        self.random_state = random_state

    def fit(self, X, y=None):
        # validate, run aisp, store fitted attributes
        ...
        self.scales_ = ...      # item -> scale assignment
        self.H_ = ...           # global Loevinger H per scale
        self.Hi_ = ...          # item-level H per scale
        self.Hij_ = ...         # pairwise H per scale
        return self

    def transform(self, X):
        # return per-scale sum scores using self.scales_
        ...

    def score(self, X):
        # global H
        ...
```

The same pattern extends to multidimensional regimes (B2) — the fitted
attributes simply become higher-rank (e.g. `self.scales_` becomes a multi-scale
membership matrix that admits crossings) — and to parametric estimators (B3)
where `RaschModel`, `TwoPLModel`, `GRMModel`, `MD2PLModel` live under the same
contract.

The existing functional API (`aisp`, `coefH`, `coefZ`, `search_normal`) stays
exposed at the package root as the R-parity surface. The estimator classes
wrap them. Both layers are stable in v0.1; the estimator layer is the
**recommended** surface for new code.

## Consequences

### Positive

- Mokken scales, mIRT, and parametric IRT all share one interface; users move
  between them without rewriting orchestration code.
- Pipeline composition (preprocess → fit → score) works out of the box.
- The Track A comparison framework (`mmokken-compare` sibling package) can
  treat `mmokken` estimators as drop-in components for ordering-extraction
  pipelines.
- API contract is reviewable by JSS reviewers against a widely-understood
  reference.

### Negative

- A non-trivial amount of dispatch and validation glue is added before any
  estimator is meaningful. The functional API must still ship alongside.
- `sklearn` becomes a soft dependency. We use `BaseEstimator` /
  `TransformerMixin` only, which are dependency-light and pure-Python, but
  this still ties our installation to scikit-learn ≥ 1.4. Acceptable for a
  scientific Python package.
- R-parity tests bypass the estimator layer (they call the functional API
  directly). We need a separate test layer for estimator behaviour
  (parameter cloning, repeated `fit` calls, `Pipeline` composition).

### Neutral

- No estimator classes are written in v0.1.0. The ADR locks the **shape** of
  the API; the implementations land incrementally. The first estimator
  (`MokkenScale`) ships in v0.1.x once the unidimensional functional surface
  is stable.

## Alternatives considered

- **Pure functional API.** Simpler, but every new model family (B3) adds yet
  another top-level function with subtly different argument conventions, and
  Pipeline composition has to be hand-wired downstream.
- **PyMC / probabilistic-programming-style interface.** Powerful but overkill
  for non-parametric Mokken, and orthogonal to the JSS audience's expectations.
- **Custom Estimator-like protocol.** Possible to avoid sklearn dependency
  entirely, but the loss of `Pipeline`/`GridSearchCV` integration is not worth
  the dependency saving for a scientific package.

## References

- Pedregosa et al. (2011). Scikit-learn: Machine Learning in Python. JMLR.
- scikit-learn developer guide: API conventions for new estimators.
- Research programme proposal §6.2 (this repo: `docs/research_proposal.docx`).
- Chat history excerpt `docs/chats/snippets.md` §6.2.
