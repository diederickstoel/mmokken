# Methodology notes

Notes on how to *use* `mmokken` in practice, with attention to design
choices that travelled from MSP 5 (1990s/2003) and R `mokken` (2007–)
into the Python implementation. This page is documentation in the
narrow sense plus an account of Mokken-Sijtsma analytic tradition; it
exists so that the seven-step procedures and rules-of-thumb that
practitioners normally pick up through apprenticeship are not lost.

---

## How Mokken did it

The first author of this package was taught Mokken Scale Analysis
directly by Robert J. Mokken. Mokken's recurring opening question to
consulting analysts was:

> "Mooi al die data, maar wat is je theorie?"
> ("Nice data, but what is your theory?")

His point: in non-parametric IRT, scale formation is not a substitute
for theoretical reasoning about *what* the items are supposed to
measure. The data tell you whether your hypothesised scale survives
the H-coefficient bar; they do not, on their own, tell you which items
should sit at the centre of the scale in the first place. That choice
is yours, and you bring linguistic and substantive knowledge to it.

Mokken's preferred protocol therefore combined an a-priori, theory-
and-semantics-driven step with the algorithmic step:

1. **Run AISP** at `lowerbound = 0.30` and identify the centroid scale.
2. From the centroid, **select a subset of items most sensitive to the
   theoretical principle**, with H_i ≥ 0.40 (significantly positive).
3. **Examine the inter-item semantic cohesion** of the selected items —
   do they really mean the same thing? Read them out loud.
4. **Pick the items with the best semantic cohesion** as the conceptual
   anchor.
5. **Use those items as the start set** for a subsequent AISP run.
6. **Set `lowerbound` to the lowest H_i** of the chosen start-set items.
7. **Run AISP again**, this time letting the algorithm grow the scale
   around your theoretical core.

The intuition: AISP without a start set lets the correlation structure
drive scale formation. With a curated start set, you force the
algorithm to grow scales around items that are *also* theoretically
coherent. The result is a scale that is both statistically and
substantively defensible.

This protocol is the conceptual ancestor of the R_D ↔ R_B framework
in the first author's PhD programme (see
`docs/research_proposal.docx` §2). Semantic structure (the
discursive ordering R_D, derivable from LLM embeddings) seeds the
scale; behavioural data (the empirical ordering R_B, derivable from
respondent endorsements via AISP) completes it; the residual
ε = R_B − R_D is treated as substantive signal about institutional and
individual factors not captured by general semantic structure.

## How to apply the protocol in `mmokken`

The Python primitives directly support steps 1, 5, 6, 7. Step 3 (the
semantic-cohesion check) is at present a manual step — read the items
out loud, ask whether they belong together — but it will be supported
in code by the forthcoming `mmokken-compare` sibling package, which
operationalises semantic cohesion using sentence-transformer
embeddings.

```python
import numpy as np
from mmokken import aisp, coefH

# Step 1: data-driven centroid
centroid_assignment = aisp(X, lowerbound=0.30, search="normal")
centroid_items = np.where(centroid_assignment[:, 0] == 1)[0]  # the largest scale

# Compute item-level H to filter on H_i >= 0.40
h_centroid = coefH(X[:, centroid_items], se=False)
hi_values = h_centroid["Hi"]

# Step 2: filter on H_i >= 0.40
high_hi_mask = hi_values >= 0.40
high_hi_items = centroid_items[high_hi_mask]

# Step 3 (manual): inspect semantic cohesion of `high_hi_items`,
# e.g. by reading their text in your VAR file or, in mmokken-compare,
# computing cosine similarity in the embedding space.

# Step 4 (manual): select the start set of best semantically-cohesive items.
start_set = [1, 5, 7, 13]  # example — your call, not the algorithm's

# Step 6: lowerbound = lowest H_i of the chosen start-set items
hi_start = coefH(X[:, start_set], se=False)["Hi"]
new_lb = float(np.min(hi_start))

# Step 7: theory-anchored AISP
final_assignment = aisp(
    X,
    lowerbound=new_lb,
    search="normal",
    StartSet=[i + 1 for i in start_set],  # R-style 1-based indexing
)
```

## Lineage of the start-set parameter

The `StartSet=` mechanism was native to MSP 5 from the start (Molenaar
& Sijtsma, 2000). It was *not* present in early versions of the R
`mokken` package and was added later, at the first author's request.
The R `aisp(..., StartSet = c(1, 2))` interface that is now widely used
exists because of this Mokken-tradition workflow. `mmokken` keeps the
parameter (translated to a Python sequence) so that the seven-step
procedure remains expressible.

## A note on toggling between weighted and unweighted H

R `mokken` 3.1.2 uses Molenaar's (1991) weighted H-coefficient by
default and does not expose the unweighted variant. MSP 5 keeps both
and recommends the weighted form (manual §2.2). For comparison with
the early Mokken-Sijtsma literature (1982–1991) the unweighted
coefficient is occasionally needed. `mmokken` plans to expose this
toggle in v0.2 (`coefH(..., h_type='weighted'|'unweighted')`). For
dichotomous items the two coincide.

## See also

* `docs/research_proposal.docx` — the PhD programme this package serves.
* `docs/decisions/0001-scikit-learn-estimator-api.md` — architecture
  decision on the public API.
* `docs/msp_vs_r_gap_analysis.md` — full feature comparison MSP 5 vs
  R `mokken`, with `mmokken` roadmap.
* `docs/parity_results.md` — three-way numerical parity benchmark.
