# MSP 5 vs R `mokken` 3.1.2 — feature gap analysis

**Date**: 2026-05-14
**Sources**:
* MSP 5 user manual (Molenaar & Sijtsma, April 2002, located at
  `msp_reference/installed/manual.pdf`)
* R `mokken` 3.1.2 NAMESPACE + man pages
  (`r_reference/mokken_3.1.2/mokken/`, CRAN-published 2024-06-18)
* Personal account by Diederick Stoel, taught Mokken Scale Analysis
  directly by Robert J. Mokken

**Purpose**: identify functionality present in MSP 5 (the historical
reference implementation, ProGAMMA 2003) that the R `mokken` package does
not currently expose, and map each gap to a phase of the `mmokken`
roadmap. This document underpins the validation chapter of the JOSS
paper and the roadmap section of the migration journal.

---

## 1. Methodology of comparison

For each feature listed in the MSP 5 manual table of contents
(chapters 2–4 + appendices), I asked three questions:

1. **Is there a direct R `mokken` 3.1.2 counterpart?**
   Checked against the NAMESPACE export list and the man pages under
   `r_reference/mokken_3.1.2/mokken/man/`.
2. **If partial, what is the conceptual or operational difference?**
3. **Where does this feature sit on `mmokken`'s phase roadmap (B1
   unidim core / B2 multidim / B3 unified estimator / Track A
   comparison)?**

The MSP 5 manual is the authoritative reference because Mokken-Sijtsma
methodology was first programmed there. R `mokken` is itself a port
(Van der Ark, 2007); its design choices are downstream of MSP.

---

## 2. Features in MSP 5 not exposed in R `mokken` 3.1.2

### 2.1 `Check = Restsplit` — non-intersection via split restscore groups

**MSP 5 behaviour (manual §4.6).** For the *k*-1 remaining items in a
restscore comparison, MSP joins all groups below a cutpoint into a "low"
aggregate and all groups above into a "high" aggregate, then iterates
over cutpoints (1, 2, 3, …, up to a Minsize-bounded maximum). At each
cutpoint, popularity reversals between the low and high aggregates are
counted as non-intersection violations. The results are combined
across cutpoints and across item-steps for polytomous items.

The manual is explicit about *why* it's a separate procedure:

> Suppose that two IRFs intersect at exactly one value of the latent
> trait. In this situation, Restsplit is expected to have **higher
> power than Restscore** for detecting this violation because Restsplit
> uses larger groups.

> Pending more conclusive evidence, it is recommended to **use all
> three methods** (with default or possibly varying Minsize choices).

So the design intent in MSP 5 is to triangulate Restscore × Restsplit ×
Pmatrix — three different statistical lenses on non-intersection.

**R `mokken` 3.1.2.** Restscore (`check.restscore`) and Pmatrix
(`check.pmatrix`) are exported; Restsplit is **not** in NAMESPACE or
any man page. Users who need this diagnostic must compute it by hand.

**Roadmap mapping for `mmokken`.** Belongs in **Tier 2 priority A
extension** (alongside the existing `check_monotonicity`,
`check_restscore`, `check_pmatrix`). Algorithmically a straightforward
extension of `_build_groups`. ~150 lines of new code expected. Worth
porting before v0.2.0 because the manual's "use all three" framing is
methodologically standard.

### 2.2 Group / subgroup analyses (`Groupvar` mechanism)

**MSP 5 behaviour (manual §4.8).** Users can declare one variable as
`Groupvar` (gender, age band, organisation, …) and MSP then **reproduces
every analysis per subgroup** and produces three dedicated comparison
outputs:

* §4.8.2 **Scalability per group** — H, Hi, Hij computed within each
  subgroup, side-by-side, so the analyst can see whether the
  measurement model holds equally well in each.
* §4.8.3 **Means and frequencies per group** — per-item endorsement
  rates and scale-score distributions, for inspection of distributional
  differences.
* §4.8.4 **Invariant item-step ordering per group** — does the
  difficulty ordering of item-steps match across subgroups? Items
  whose ranks differ between groups are flagged as candidates for
  **differential item functioning** (DIF) / item bias.

The manual is explicit that this maps onto **measurement invariance**:

> a) Does the measurement model fit equally well across subgroups?
> b) Are scale score and item scores similarly distributed?
> c) Are there specific items for which the overall difficulty order is
>    violated in one or more subgroups?

> If the finding can be replicated, one speaks of **item bias or
> differential item functioning**.

**R `mokken` 3.1.2.** No dedicated group-comparison function. A user
can subset data and call `coefH` per group manually, but there is no
canonical comparison statistic for "is the item ordering the same in
group A and B?". The multilevel functions (`MLcoefH`, `MLcoefZ`,
`MLweight`) are for nested data (respondents within clusters), which is
a different design from MSP 5's cross-sectional subgroup comparison.

**Roadmap mapping for `mmokken`.** **Strategic candidate for B2 or
B2-adjacent.** This is exactly what the user's PhD demonstration case
requires: scale comparison across organisations in the
career-progression dataset (~1,700 employees from multiple
organisations, per `docs/research_proposal.docx` §5). Track A's
residual-as-signal analysis (ε = R_B − R_D varying by institutional
context) is functionally a Groupvar analysis.

Proposed Python API:

```python
from mmokken import compare_groups

result = compare_groups(
    X,                    # respondents × items
    group=group_var,      # vector of group labels per respondent
    statistics=("H", "Hi", "ordering"),  # what to compare
    test="permutation",   # significance test for between-group differences
)
result.h_per_group          # DataFrame: group × scale H
result.item_ordering_diff   # which items shift rank between groups
result.dif_flags            # items flagged as candidate DIF
```

Effort: ~300–400 lines, plus tests and golden parity against MSP
output where possible.

### 2.3 Weighted vs unweighted H coefficient — toggle

**MSP 5 behaviour (manual §2).** MSP exposes both the unweighted
H-coefficient (Mokken's original 1971 / Sijtsma 1982 formulation, equal
weight to all errors on an item pair) and the **weighted** H
(Molenaar 1991), which weights errors by the number of involved
item-step pairs.

Quote from the manual:

> The other coefficient (Molenaar, 1991) weights errors on an item pair
> by the number of item step pairs involved in those items on which an
> error was observed corresponding to the responses to both items. This
> weighted coefficient is used in MSP5 for Windows (it was the default
> option in MSP3.0).

Molenaar's argument for the weighted version is that it equals the
ratio of covariance to maximum covariance and that it doesn't suffer
the calculation issues the unweighted form has when item-step
difficulties are equal. The manual recommends the weighted version,
but MSP keeps the unweighted toggle for backward-comparison purposes.

**R `mokken` 3.1.2.** `coefH` and `coefHTiny` compute the **weighted**
H by default. There is no documented switch for the unweighted form.
For backward comparison with the early Mokken-Sijtsma literature
(1982–1991) and with old MSP 3.0 outputs, the unweighted variant is
unavailable.

**Roadmap mapping for `mmokken`.** **Tier 2 priority A** — small,
optional add-on. Add an `h_type='weighted'|'unweighted'` parameter to
`coefH` and `coefHTiny`. The unweighted version is a simpler
computation (cf. Sijtsma & Molenaar 2002 §4); ~50 lines of code,
delegated to a private helper.

### 2.4 The expert / semantic start-set protocol

**MSP 5 / Mokken methodology (manual §4.2 + personal account).** Robert
Mokken's preferred analytic workflow, as taught to the user:

> "Mooi al die data, maar wat is je theorie?"
> ("Nice data, but what is your theory?")

The recommended protocol — Mokken's own seven-step expert-clustering
procedure — is:

1. Run AISP at `c = 0.30` and identify a centroid.
2. Select a subset of items most sensitive to the theoretical
   principle, with H_i ≥ 0.40 (significantly positive).
3. Examine the **inter-item semantic cohesion** of the selected items.
4. Select the items with the best semantic cohesion.
5. Use those items as the **start set** for a subsequent AISP run.
6. Set lowerbound `c` to the lowest H_i of the selected start-set
   items.
7. Run AISP again, this time letting the algorithm fill in the rest.

The intuition: AISP without a start set lets the data drive scale
formation purely correlationally. With a semantically-curated start
set, the analyst forces the algorithm to grow scales around a
theory-anchored core. This combines a priori construct validity with
post hoc data-driven scale completion. It is the conceptual ancestor
of the R_D ↔ R_B framework in the user's PhD proposal: semantics
(R_D) seeds the scale, behaviour (R_B) completes it.

**MSP 5.** The `StartSet=` mechanism was native to MSP 5.

**R `mokken` 3.1.2.** Per personal account: the `StartSet=` parameter
was **not** in early versions of R `mokken` and was added to the
package later, at the user's request. Current `aisp(X, ...,
StartSet=)` does work, but the protocol itself — the seven steps,
including the semantic-cohesion examination — lives in researcher
practice, not as an automated function.

**Roadmap mapping for `mmokken`.** Two complementary deliverables:

* A docs/methodology note `docs/methodology_notes.md` (see proposed
  draft in §4 below) capturing the protocol so future users of
  `mmokken` know how to combine its tools.
* In Track A, a function `mmokken.compare.semantic_startset(items,
  embeddings, top_k=8, min_hi=0.40)` that automates the
  semantic-cohesion step by ranking items on within-cluster cosine
  similarity in the LLM embedding space, then proposing a start set
  for `aisp`. This is one of the points where R_D explicitly feeds
  R_B (the bridge that the PhD programme rests on).

### 2.5 Item-step ordering options (`STEPORDER=`)

**MSP 5 behaviour.** MSP exposes `STEPORDER=COMMON` (use the same
ordering of item-steps across all items) and `STEPORDER=...` per-item
variants in `Check=Monotonicity` and related diagnostics. This matters
when polytomous items have different category usage profiles: a
"common" ordering may over-estimate violations.

**R `mokken` 3.1.2.** `coefH` exposes a `fixed.itemstep.order=` matrix
parameter, which is the more flexible form (user supplies the exact
order). The `check.monotonicity` family does not surface this control.

**Roadmap mapping for `mmokken`.** Tier 3 — low-priority refinement.
Add `fixed_itemstep_order` to the diagnostic `check_*` functions for
parity. Most use cases don't require it.

### 2.6 Save-results pipeline (extended output files)

**MSP 5 behaviour (manual §3.6 + §4.9).** With `Save additional results`
the analyst can write per-case scale scores, item-step values, Guttman
errors, and the HT_a person-fit coefficient to an extended data file.
Useful for downstream regression analyses linking scale scores to
covariates.

**R `mokken` 3.1.2.** No equivalent "save extended results" helper.
Users compute scale scores by hand with `rowSums(X[, scale_items])` and
attach to their data frame.

**Roadmap mapping for `mmokken`.** Trivial. A `mmokken.export.augment(X,
scales)` returning a pandas DataFrame with `scale_score_1`,
`scale_score_2`, …, `gplus`, `oplus`, etc. is ~30 lines. Useful for the
PhD demonstration case (linking ε per organisation to organisation
covariates).

---

## 3. Features in R `mokken` 3.1.2 that were *added after* MSP 5

For completeness (and to give the gap analysis the other direction):

* **Multilevel functions** (`MLcoefH`, `MLcoefZ`, `MLweight`) — nested
  data (respondents within clusters). MSP 5 has no multilevel mode.
* **`check.ca` (conditional association)** — Sijtsma-style diagnostic
  not in MSP 5.
* **`check.bounds` (Ellis correlation bounds)** — added by Van der Ark
  in the R port.
* **`check.iio` with multiple methods (`MIIO`, `IT`, `MSCPM`)** —
  generalises MSP 5's HTrans (which is essentially the dichotomous-IT
  case).
* **`twoway` (two-way imputation)** — added in R; MSP 5 only filters
  cases with missing values.
* **LCRC reliability** — needs `poLCA`, added in R, not in MSP 5.
* **Genetic-algorithm AISP** — actually present in both MSP 5 (`Type =
  Search GA`) and R. Implementation differs (MSP-Pascal vs Rcpp/C++).

So the lineage is non-trivial. R `mokken` extended MSP 5 in some
directions (multilevel, modern diagnostics) while leaving other
directions (group comparison, weighted toggle, restsplit) behind. The
goal of `mmokken` is to recover both lineages and combine them.

---

## 4. Proposed `docs/methodology_notes.md` excerpt

Draft prose for a new docs page that captures Mokken's expert-clustering
protocol with attribution:

> ## How Mokken did it
>
> Robert J. Mokken's own analytical workflow — taught directly to this
> package's author — combined theory-driven item selection with
> data-driven scale completion. He often opened a consultation with
> "*Mooi al die data, maar wat is je theorie?*" (nice data, but what
> is your theory?). The recommended seven-step procedure was:
>
> 1. Run AISP at lowerbound *c* = 0.30 to find a centroid.
> 2. Select a subset of items most sensitive to the theoretical
>    principle, with H_i ≥ 0.40 (significantly positive).
> 3. Examine the inter-item *semantic* cohesion of the selected items.
> 4. Pick the items with the best semantic cohesion.
> 5. Use those items as the start set for a subsequent AISP run.
> 6. Set lowerbound *c* to the lowest H_i of the start-set items.
> 7. Run AISP again, letting the algorithm fill in the rest.
>
> In modern `mmokken` terms:
>
> ```python
> # Step 1: data-driven centroid
> raw_scales = aisp(X, lowerbound=0.30, search="normal")
>
> # Steps 2-4: pick high-Hi items + check semantic cohesion (manual,
> # or — in mmokken-compare — automated via LLM embeddings)
> seed_items = [i for i in centroid_scale if Hi[i] >= 0.40 and
>               semantically_cohesive(i, theory)]
>
> # Steps 5-7: theory-anchored AISP
> assignments = aisp(X, lowerbound=min_Hi(seed_items),
>                    search="normal", StartSet=seed_items)
> ```
>
> The protocol is the conceptual ancestor of this PhD programme's
> R_D ↔ R_B framework (`docs/research_proposal.docx` §2): semantic
> structure (R_D) seeds the scale, behavioural data (R_B) completes
> it, and the residual is interpreted as institutional / individual
> variation beyond general semantic structure.

---

## 5. Summary table

| Feature | MSP 5 | R `mokken` 3.1.2 | `mmokken` plan |
|---|---|---|---|
| Restscore non-intersection | ✓ | ✓ | ✓ (v0.1) |
| **Restsplit non-intersection** | ✓ | **✗** | **B1 extension (v0.2)** |
| Pmatrix non-intersection | ✓ | ✓ | ✓ (v0.1) |
| Manifest monotonicity | ✓ | ✓ | ✓ (v0.1) |
| HTrans / IIO | ✓ (dichotomous) | ✓ (`check.iio` — multi-method) | Tier 3 |
| Reliability (MS, α, λ₂) | ✓ | ✓ | ✓ (v0.1) |
| LCRC reliability | ✗ | ✓ (needs poLCA) | Deferred |
| Norms | partial | ✓ | Tier 3 |
| Guttman errors / Oplus | ✓ | ✓ | ✓ (v0.1) |
| Bounds (Ellis) | ✗ | ✓ | Tier 3 |
| Conditional association (CA) | ✗ | ✓ | Tier 3 |
| AISP normal search | ✓ | ✓ | ✓ (v0.1) |
| AISP genetic algorithm | ✓ | ✓ | ✓ (v0.1) |
| AISP `StartSet` | ✓ | ✓ (added later) | ✓ (v0.1) |
| **Group comparison (`Groupvar`)** | ✓ | **✗** | **B2 priority — Track A demonstration** |
| **Weighted/unweighted H toggle** | ✓ | **✗ (weighted only)** | **B1 extension (v0.2)** |
| `STEPORDER` per-item | ✓ | partial | Tier 3 |
| Save extended results | ✓ | ✗ | Trivial; v0.1.x |
| Multilevel (`MLcoefH`/Z/`MLweight`) | ✗ | ✓ | Tier 3 |
| `recode` / `twoway` | partial | ✓ | ✓ (v0.1) |
| **Multidim / Stoel H** | ✗ | ✗ | **B2 — package USP** |

---

## 6. Implications for the JOSS paper

This gap analysis strengthens the Statement of Need beyond "Python
implementation of Mokken Scale Analysis":

> `mmokken` recovers two lineages in one package. From R `mokken`
> 3.1.2 it inherits the modern diagnostics suite, the multilevel
> extensions, and a GA AISP implementation; from MSP 5 it recovers
> features that the R port dropped — the Restsplit diagnostic, the
> weighted/unweighted H toggle, and the `Groupvar` mechanism for
> measurement-invariance and DIF testing. The new combined surface is
> validated three-way against both predecessors on the canonical MSP
> 5 odour-annoyance dataset.

This is the strongest version of the "three-way validation" framing —
not just "we agree numerically" but "we know which line of the lineage
each feature comes from, and we expose features that one or both
predecessors hid."
