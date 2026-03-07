# mokken R -> Python 1:1 Migration Inventory (v3.1.2 reference)

## Scope and confidence
- Source audited: `r_reference/mokken_3.1.2/mokken/R/*.R`, `NAMESPACE`, and `src/geneticAlgorithm.cpp`/`RcppExports.R`.
- Goal: behavior-preserving first Python port, not redesign.
- Confidence: high for API surface and data structures; medium for exact matrix-calculus internals in `coefH`/`MLcoefH` (complex Jacobian blocks are partially summarized).
- Note: commented-out legacy functions (`*.old`, deprecated helpers) are listed as legacy, not primary port targets.

## 1) Public API inventory
Exported in `NAMESPACE`:
- `aisp`
- `coefH`
- `coefZ`
- `check.bounds`
- `check.ca`
- `check.errors`
- `check.monotonicity`
- `check.norms`
- `check.iio`
- `check.pmatrix`
- `check.reliability`
- `check.restscore`
- `ICC`
- `MLcoefH`
- `MLcoefZ`
- `MLweight`
- `recode`
- `twoway`

Registered S3 methods (public behavior but not exported as regular symbols):
- `summary.monotonicity.class`, `summary.pmatrix.class`, `summary.restscore.class`, `summary.iio.class`
- `plot.monotonicity.class`, `plot.pmatrix.class`, `plot.restscore.class`, `plot.iio.class`

## 2) Internal helpers / local functions / compiled bridge
### Global internal helpers (`R/internalFunctions.R`)
- `check.data`, `check.ml.data`, `coefHTiny`, `phi`, `dphi`, `string2integer`, `oldweights` (legacy), `weights`, `complete.observed.frequencies`, `direct.sum`
- local helper `perm` inside `weights`

### File-scoped helpers (defined in same file)
- `R/check.ca.R`: `coefHi`, `compute.defaultminsize`, `joinRSG`, `covweight`, `nweight`, `compute.restscores`, `compute.W1`, `compute.W2`, `compute.W3`, `flag`
- `R/check.errors.R`: local `medCouple`
- `R/check.pmatrix.R`: `compute.Ppp`, `compute.Pmm`, `Scores2Steps`
- `R/check.reliability.R`: `compute.PP`, `IRC`, `compute.PP.LCRC`, `check.probs`
- `R/check.iio.R`: `coefHT`, `coefHTB`
- `R/search.normal.R` and `R/search.extended.R`: `any.neg`, `adjusted.alpha`, `fitstring`, `newH`
- plot helpers: `up.lo.bound.mean`, `cn2n`, `up.lo.bound.ISRF`
- `R/MLweight.R`: `perm`, `allPatterns` (note: `allPatterns` is globally used by other files)

### Compiled bridge
- `runGeneticAlgorithm` (`R/RcppExports.R`) -> `.Call("_mokken_runGeneticAlgorithm", ...)`
- Used by `search.ga`.

## 3) Objects/classes/data structures
### S3 classes
- `monotonicity.class`: list with `results`, `I.labels`, `Hi`, `m`, `X`; in multilevel mode becomes list of two such objects.
- `pmatrix.class`: list with `results` (nested `Ppp/Pmm`, violations, z-stats), `I.item`, `I.step`, `I.labels`, `Hi`, `minvi`, `ncat`, `N`.
- `restscore.class`: list with `results`, `I.labels`, `Hi`, `m`.
- `iio.class`: list with `results`, `violations`, `items.removed`, `Hi`, `HT`, `method`, `item.mean`, `m`; optional second-level/cluster variants in nested lists.

### Key matrices/lists reused across package
- `Hij`, `Hi`, `H`: scalability coefficients at pair/item/scale level.
- `se.Hij`, `se.Hi`, `se.H`: SE matrices/vectors.
- violation matrices with standardized columns: `#ac`, `#vi`, `#vi/#ac`, `maxvi`, `sum`, `sum/#ac`, max test stat, count significant.
- backward-selection matrices (`VI`, `VIA`, `VIC`) in IIO.
- Guttman weight vectors from `weights`/`MLweight`.

## 4) File-level dependency map
- `aisp.R` -> `internalFunctions.R` (`check.data`, `coefHTiny`), `search.normal.R`, `search.extended.R`, `search.ga.R`
- `check.bounds.R` -> `internalFunctions.R` (`check.data`)
- `check.ca.R` -> `internalFunctions.R` (`check.data`)
- `check.errors.R` -> `internalFunctions.R` (`check.data`)
- `check.monotonicity.R` -> `internalFunctions.R` (`check.data`, `coefHTiny`), `MLcoefH.R`
- `check.iio.R` -> `internalFunctions.R` (`check.data`, `coefHTiny`), `MLcoefH.R`
- `check.pmatrix.R` -> `internalFunctions.R` (`check.data`, `coefHTiny`)
- `check.reliability.R` -> `internalFunctions.R` (`check.data`)
- `check.norms.R` -> `internalFunctions.R` (`direct.sum`)
- `check.restscore.R` -> `internalFunctions.R` (`check.data`, `coefHTiny`)
- `coefZ.R` -> `internalFunctions.R` (`check.data`), `coefH.R`
- `coefH.R` -> `internalFunctions.R` (`check.data`, `phi`, `dphi`, `weights`, `complete.observed.frequencies`, `allPatterns`)
- `MLcoefZ.R` -> `MLcoefH.R`
- `MLcoefH.R` -> `internalFunctions.R` (`check.ml.data`, `phi`, `dphi`, `weights`), `MLweight.R`
- `search.normal.R` / `search.extended.R` -> `coefZ.R`, `internalFunctions.R` (`coefHTiny`)
- `search.ga.R` -> `RcppExports.R` (`runGeneticAlgorithm`) -> `src/geneticAlgorithm.cpp`
- `summary.*`/`plot.*` files depend on class-object structures from corresponding `check.*` functions.

## 5) Function-level summaries (inputs/outputs/side effects/purpose/deps/edge cases)

## 5.1 Scalability coefficients
- `coefH(X, se=TRUE, ci=FALSE, nice.output=TRUE, level.two.var=NULL, group.var=NULL, fixed.itemstep.order=NULL, type.ci="WB", results=TRUE)`
  - Output: matrices/vectors for `Hij/Hi/H` with optional SE, CI, covariance matrices; format depends on `nice.output`/`results`/grouping.
  - Side effects: warnings on invalid `ci/type.ci`, `level.two.var`, `group.var`, fixed order, singleton groups; may print formatted output in some branches.
  - Purpose: core Mokken H coefficients + asymptotic covariance/SE via matrix calculus (`phi`,`dphi`) and Guttman weights.
  - Depends on: `check.data`, `weights`, `allPatterns`, `complete.observed.frequencies`, `phi`, `dphi`.
  - Edge cases: zero variance items stop; multilevel drops groups with single respondent; CI type `RP` log-transform behavior near H=1; strong branch complexity for `group.var`.

- `coefZ(X, lowerbound=0, type.z="Z", level.two.var=NULL)`
  - Output: `list(Zij, Zi, Z)`.
  - Side effects: coercive warnings (`type.z` auto-switch to `WB` for `lowerbound>0` or multilevel).
  - Purpose: significance statistics for H at pair/item/scale levels; either classic Z or Wald/range-preserving based on `coefH` output.
  - Depends on: `check.data`, `coefH`.
  - Edge cases: invalid `type.z`; multilevel singleton groups removed.

- `MLcoefH(X, se=TRUE, ci=FALSE, nice.output=TRUE, subject=1, fixed.itemstep.order=NULL, weigh.props=TRUE, type.ci="WB", cov.mat=FALSE)`
  - Output: two-level coefficients (within/between/combined: Hij/Hi/H), optional SE/CI and cov matrices.
  - Side effects: many warnings for naming, variance, CI args, singleton subjects, fixed order shape.
  - Purpose: multilevel Mokken scalability decomposition.
  - Depends on: `check.ml.data`, `weights`/`MLweight`, `phi`, `dphi`, `allPatterns`.
  - Edge cases: unequal raters handled with harmonic mean style weighting; near-boundary CI behavior; output shape highly branch-dependent.

- `MLcoefZ(X, lowerbound=0, type.z="WB")`
  - Output: `list(Zij, Zi, Z)` for within/between/combined columns.
  - Side effects: warning if invalid `type.z`.
  - Purpose: Z-statistics on MLcoefH estimates.
  - Depends on: `MLcoefH`.
  - Edge cases: `RP` path uses transformed H and can be unstable near 1.

- `coefHTiny(X)` (internal)
  - Output: fast `list(Hij, Hi, H)` without SE.
  - Purpose: lightweight H computations used widely in search/check functions.
  - Edge cases: division by small `Smax` can magnify noise.

## 5.2 AISP / search procedures
- `aisp(X, lowerbound=.3, search="normal", alpha=.05, StartSet=FALSE, popsize=20, maxgens=default.maxgens, pxover=.5, pmutation=.1, verbose=FALSE, type.z="Z", test.Hi=FALSE, level.two.var=NULL)`
  - Output: item-by-lowerbound matrix of scale memberships.
  - Side effects: warnings, parameter coercions, optional `cat` output via called search functions.
  - Purpose: automated item selection into Mokken scales.
  - Depends on: `check.data`, `coefHTiny`, `search.normal`, `search.extended`, `search.ga`.
  - Edge cases: lowerbounds > max(Hij) dropped; `type.z` forced to `WB` in some settings; singleton groups removed for multilevel.

- `search.normal(...)` (internal primary AISP engine)
  - Output: item->scale assignment matrix for each lowerbound.
  - Side effects: warnings for invalid StartSet and multilevel settings; optional verbose `cat` trace.
  - Purpose: sequential scale construction with Bonferroni-like adjusted alpha and candidate filtering by Hij sign/significance + Hi/H bounds.
  - Depends on: `coefHTiny`, `coefZ`.
  - Edge cases: ties broken by tiny epsilon perturbation (`row*1e-10`); sentinel codes `-99/-98/-97`; StartSet validation is strict.

- `search.extended(...)` (legacy/internal)
  - Similar to old `search.normal` logic; not used by default pathways except `aisp(search="extended")`.

- `search.ga(X, popsize, maxgens, alpha, critval, pxover, pmutation)`
  - Output: one assignment row from GA output.
  - Purpose: GA-based scale partitioning.
  - Depends on: `runGeneticAlgorithm` (C++).
  - Edge cases: iteration cap heuristic by item count; stochastic behavior from compiled routine.

- `runGeneticAlgorithm(...)`
  - Output: numeric vector returned from C++.
  - Purpose: compiled optimization kernel.

## 5.3 Monotonicity / IIO / pair-matrix / restscore checks
- `check.monotonicity(X, minvi=.03, minsize=default.minsize, level.two.var=NULL)`
  - Output: `monotonicity.class` (single- or two-level list).
  - Side effects: stops on sample constraints.
  - Purpose: restscore-group monotonicity violations per item step; computes summary matrices and z-based violation diagnostics.
  - Depends on: `check.data`, `coefHTiny`, `MLcoefH` (for level-two Hi).
  - Edge cases: hard thresholds `1e-10`, `0.999999999999`, z cutoff `1.6449`; minsize grouping heuristic.

- `check.iio(X, method="MIIO", minvi=default.minvi, minsize=default.minsize, alpha=.05, item.selection=TRUE, verbose=FALSE, fixed.item.order=NULL, level.two.var=NULL)`
  - Output: `iio.class` (possibly nested variants for cluster/aggregate levels).
  - Side effects: extensive warnings, optional print.
  - Purpose: invariant item ordering checks via methods `IT`, `MSCPM`, `MIIO`; optional backward item selection.
  - Depends on: `check.data`, `coefHTiny`, `MLcoefH`, local `coefHT`, `coefHTB`.
  - Edge cases: method auto-remapping, fixed-cluster constraints, tie-breaking with `+ rnorm(1,0,1e-10)` in item removal criterion, many branch-specific statistics.

- `check.pmatrix(X, minvi=.03)`
  - Output: `pmatrix.class` with P(++) and P(--) matrices, violation/z summaries.
  - Purpose: non-intersection diagnostics on cumulative probabilities.
  - Depends on: `check.data`, `coefHTiny`, local matrix builders.
  - Edge cases: NA mask for diagonal/block artifacts (`< -0.5`), z-threshold fixed at `qnorm(.95)`.

- `check.restscore(X, minvi=.03, minsize=default.minsize)`
  - Output: `restscore.class`.
  - Purpose: pairwise restscore grouping violations between item-step response functions.
  - Depends on: `check.data`, `coefHTiny`.
  - Edge cases: group construction by sorted restscores and minsize; z approximation via frequency cells can destabilize with sparse groups.

## 5.4 Reliability / bounds / conditional association / error detection / norms
- `check.reliability(X, MS=TRUE, alpha=TRUE, lambda.2=TRUE, LCRC=FALSE, nclass=nclass.default, irc=FALSE)`
  - Output: list subset of `MS`, `alpha`, `lambda.2`, `LCRC`, `irc`.
  - Side effects: warning if `poLCA` unavailable.
  - Purpose: multiple reliability estimators incl latent-class reliability correction.
  - Depends on: `check.data`, local helpers; optional `poLCA`, `MASS`.
  - Edge cases: missing `PP` cells imputed by rule-based interpolation; boundary clipping to feasible probability bounds.

- `check.bounds(X, quant=.90, lower=TRUE, upper=FALSE)`
  - Output: lower/upper bounds matrices list.
  - Purpose: Ellis upper/lower correlation bounds.
  - Depends on: `check.data`.
  - Edge cases: tiny correlations replaced with `1e-10` to avoid divide-by-zero; requires `J>=3`.

- `check.ca(X, Windex=FALSE, MINSIZE=4, NWEIGHTOPTION="noweight", COVWEIGHTOPTION="pnorm", MINGROUP=4)`
  - Output: either full iterative index structures (`W1/W2/W3`, flags) or only in-scale vectors.
  - Side effects: random tie-break (`sample`) when multiple removal candidates.
  - Purpose: conditional association diagnostics with iterative item removal.
  - Depends on: `check.data` + local helper stack.
  - Edge cases: `N<50` effectively invalid (default minsize NA->stop), stochastic item elimination in ties.

- `check.errors(X, returnGplus=TRUE, returnOplus=FALSE)`
  - Output: list containing `Gplus`/`Oplus` and robust upper fences.
  - Side effects: sets seed to 1 when tie randomization is required.
  - Purpose: person-fit style error scores (Guttman errors and Oplus).
  - Depends on: `check.data`, local `medCouple`.
  - Edge cases: tie handling via 1000 jitter replications and averaging; robust fence uses `exp(3.87*medCouple)`.

- `check.norms(y, nice.output=TRUE)`
  - Output: list with mean/sd/z/stanine/percentile estimates and SE/CI.
  - Purpose: score norming via delta-method matrix transformations.
  - Depends on: `direct.sum`.
  - Edge cases: score shift if min<=0; heavy matrix algebra sensitive to zero counts.

- `ICC(X)`
  - Output: list with item ICCs and scale ICC + F test.
  - Side effects: warning for duplicate names and singleton groups removed.
  - Purpose: intraclass correlation estimation for clustered ratings.
  - Edge cases: requires subject id in first column; uses harmonic-mean related corrections for unequal cluster sizes.

## 5.5 Utilities
- `check.data(X, checkScores=TRUE)` / `check.ml.data(...)`
  - Output: validated numeric integer matrix with shifted minimum to 0 (all columns or all except subject column).
  - Side effects: warnings for varying observed category support.
  - Edge cases: hard limit `<=10` categories (message text indicates package limit), no missings allowed.

- `weights(X, maxx=max.x, minx=0, itemstep.order=NULL)`
  - Output: Guttman weights vector.
  - Purpose: item-step ordering weights with tie-averaging across admissible permutations.
  - Edge cases: tie handling enumerates permutations (potential combinatorial blowup); within-item ordering constraints enforced.

- `MLweight(X, maxx=NULL, minx=NULL, itemstep.order=NULL)`
  - Output: multilevel analog of Guttman weights.
  - Side effects: warnings when inferring min/max.

- `complete.observed.frequencies(data, J, m, order.items=FALSE)`
  - Output: frequency vector over all response patterns.

- `phi`, `dphi`
  - Purpose: core transform and Jacobian blocks for delta-method covariance derivations.

- `recode(X, items=NULL, values=defaultValues)`
  - Output: recoded dataset.
  - Edge cases: assumes selected columns and value range consistent; keeps NA untouched.

- `twoway(X, nCompletedDataSets=1, minX=defaultMinX, maxX=defaultMaxX, seed=FALSE)`
  - Output: one or list of completed datasets.
  - Side effects: optional RNG seeding; warning if no missing data.
  - Purpose: two-way imputation using person mean + item mean - grand mean + random noise.
  - Edge cases: variance of residuals used in noise term; clamped to minX/maxX.

## 5.6 Plotting/reporting
- Plot methods consume class objects and draw base-R graphics with optional CI polygons.
- Summary methods compute per-item criticality score (`crit`) from weighted combination of H and violation metrics.
- Common edge case: branch logic supports single-level and two-level object shapes (`length(object)==2`).

## 6) Implicit design choices to preserve
- Input coercion/validation:
  - Integer nonnegative scoring enforced almost everywhere.
  - Missing values usually forbidden (`twoway` is exception for imputation).
- Category normalization:
  - Scores shifted so minimum becomes 0 in validators.
- Default thresholds:
  - `minvi` defaults: often `.03` (or `(ncat-1)*.03` in `check.iio` MIIO).
  - `minsize` heuristic piecewise by N: `N>=500 => N/10`, `<=250 => N/3`, `<150 => 50`.
  - significance thresholds: often `qnorm(.95)` or `1.6449`; AISP uses adjusted alpha.
- Multiple-testing-like adjustment:
  - `adjusted.alpha = alpha / (K1*(K1-1)/2 + sum(K[-1]))` in search.
- Tie handling:
  - deterministic epsilon perturbations, random tie breaks via `sample` or `rnorm`, explicit tie simulation in `check.errors` (seed=1).
- Multilevel handling:
  - reorder by cluster id, reindex groups to 1..S, drop singleton groups with warnings.
- Confidence intervals:
  - two modes: Wald-based (`WB`) and range-preserving (`RP` log transform).
- Output polymorphism:
  - many functions change structure based on `nice.output`, `se`, `ci`, `results`, multilevel/group settings.
- Legacy behavior artifacts:
  - sentinel values (`-99`, `-98`, `-97`) in search functions.

## 7) Proposed Python package structure (faithful first port)

```text
mokken_py/
  __init__.py
  api.py                          # exported user API mirroring R names
  validation.py                   # check_data, check_ml_data
  core/
    scalability.py                # coef_h, coef_z, coef_h_tiny
    scalability_ml.py             # ml_coef_h, ml_coef_z
    weights.py                    # weights, mlweight, all_patterns
    delta.py                      # phi, dphi
  search/
    aisp.py                       # aisp orchestrator
    normal.py                     # search_normal
    extended.py                   # search_extended (legacy/compat)
    ga.py                         # search_ga + C++ bridge wrapper
  diagnostics/
    monotonicity.py               # check_monotonicity + result dataclasses
    iio.py                        # check_iio, coef_ht, coef_htb
    pmatrix.py                    # check_pmatrix
    restscore.py                  # check_restscore
    conditional_assoc.py          # check_ca
    bounds.py                     # check_bounds
    errors.py                     # check_errors
    reliability.py                # check_reliability, icc
    norms.py                      # check_norms
  reporting/
    summary.py                    # summary_* equivalents
    plotting.py                   # plot_* equivalents (matplotlib)
  imputation/
    twoway.py                     # twoway completion
  structures.py                   # dataclasses for monotonicity/iio/pmatrix/restscore results
  compat/
    r_like_output.py              # formatting/noquote-like tables for parity mode
  _ga_cpp/                        # optional pybind11/cython for GA parity
    ...
```

Port strategy notes:
- Keep R-like function names in `api.py` initially for 1:1 parity (`coefH` aliasing `coef_h`).
- Implement strict and permissive modes for output formatting; strict mode reproduces R field names and nested list layout.
- Preserve RNG behavior where relevant (`check.errors`, tie-breakers, `twoway`, GA).

## 8) Open uncertainties / verification targets before coding
- `coefH` and `MLcoefH` Jacobian block construction has many branch-specific matrix layouts; verify with golden tests for all argument combinations (`se/ci/nice_output/group/multilevel`).
- `check.iio` cluster-level outputs (`VIC`, `VIbetw`, `HTB`) require fixture-based parity checks due complex branching.
- `weights` and `MLweight` tie-permutation ordering constraints should be snapshot-tested for identical small synthetic datasets.
- C++ GA parity likely requires compiled port or embedding existing logic; Python-only reimplementation may drift.

## Appendix: legacy/commented functions observed
- `aisp.old`, `check.errors.old`, `search.normal.old`, commented `coefZ.wald`, `coefZ.old`, and older commented `coefHT` variants in `check.iio.R`.
- Recommended: keep out of first port unless explicit backward-compat requirement.

## Incremental Update (2026-03-07): `aisp`
- Implemented Python `aisp` normal-search path in `mokken_py/search/aisp.py`, mapped to `R/aisp.R::aisp`.
- `aisp` now calls `search_normal` internally and supports scalar/vector `lowerbound` plus `StartSet`.
- Added R-golden tests based on `man/aisp.Rd` examples (`acl` Communality subset):
  - default `aisp(Communality)`
  - `aisp(..., StartSet = c(1,2))`
  - `aisp(..., lowerbound = seq(0, .55, .05))`
- Current parity status: assignment matrices match R exactly for these tested examples.
- Deferred branches (explicit `NotImplementedError`): `search='ga'`, `search='extended'`, and `level.two.var` execution path in `aisp`.
