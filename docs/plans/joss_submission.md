# Plan: `mmokken` v0.1.0 → JOSS submission

**Status**: In progress — planning phase
**Owner**: Diederick Stoel
**Last updated**: 2026-05-14
**Source**: extends `docs/research_proposal.docx` and `docs/decisions/0001-scikit-learn-estimator-api.md`

---

## 1. Strategic framing

This document plans the *first* publication artefact for the `mmokken` Python
package: a short software paper in the
[Journal of Open Source Software (JOSS)](https://joss.theoj.org/).

JOSS papers are 250–1000-word descriptions of research software, peer-reviewed
on an open GitHub-issue thread. They produce a citeable DOI. They are
**not** methodological contributions — those belong in JSS, Psychometrika or
Behavior Research Methods later.

### Why a JOSS paper now, instead of waiting for JSS?

- **Citeability**: a DOI from JOSS gives the PhD programme a deliverable that
  Track A papers and the demonstration paper can cite (`Stoel, 2026,
  Journal of Open Source Software`). Without it, every other paper has to
  cite "in preparation" software.
- **Validation insurance**: peer-reviewed published software gives a strong
  baseline when the larger JSS-paper enters review later.
- **Forces release discipline**: a JOSS submission requires a tagged release,
  a license file, a CITATION.cff, and CI — all things v0.1.0 needs anyway.
- **Non-competing with JSS**: JOSS describes *the tool*, JSS will describe
  *the methodology* (mMokken multidimensional + Stoel H). The two papers
  live in different genres and citation patterns.

### Scope discipline — what is IN

- All 13 currently-ported R `mokken` functions
- Three-way numerical parity: MSP 5 (2003), R `mokken` 3.1.2, Python
  `mmokken` v0.1.0
- Pure-Python GA AISP (unique vs R's C++ binding)
- MSP `.dat` + `.var` I/O (unique vs R)

### Scope discipline — what is OUT (intentionally)

These belong in later publications, not this one:

- mMokken multidimensional extension → JSS package paper
- Stoel H multi-scale metric → standalone methodology paper
- scikit-learn estimator API (`MokkenScale.fit/transform`) → v0.1.x, optional
- Multilevel branches (`MLcoefH`, `MLcoefZ`, `level_two_var` paths) → Tier 3
- Diagnostics not yet ported (`check_iio`, `check_bounds`, `check_ca`,
  `check_norms`, `ICC`) → Tier 3
- Plot/summary helpers → v0.1.x

This scope is **deliberately less ambitious** than "complete Mokken port".
The Statement of Need frames it as a validated foundation for further
multidimensional work.

---

## 2. JOSS requirements checklist

### Software requirements

- [x] Open-source with OSI-approved licence (GPL-3.0 in `pyproject.toml`)
- [ ] LICENSE file at repo root (currently only in pyproject metadata)
- [x] Public version-controlled repo (currently private; flip after audit)
- [ ] Tagged release `v0.1.0`
- [x] Installation instructions in README
- [x] Automated tests with CI (GitHub Actions matrix)
- [x] "Substantial scholarly effort": 13 functions + parity + GA + I/O
- [x] Documentation skeleton (Sphinx)
- [ ] Working basic-usage example in docs

### Paper requirements

- [ ] `paper/paper.md` with YAML frontmatter
- [ ] `paper/paper.bib` (BibTeX)
- [ ] Sections: Summary, Statement of Need, References (required); Functionality,
      Usage examples, Acknowledgements (recommended)
- [ ] Length 250–1000 words
- [ ] All authors have ORCIDs

### Submission process artefacts

- [ ] CITATION.cff at repo root (with DOI once Zenodo-archived)
- [ ] CHANGELOG.md with v0.1.0 entry
- [ ] GitHub-Zenodo integration enabled
- [ ] Zenodo DOI generated on release tag
- [ ] JOSS submission form filled at https://joss.theoj.org/papers/new
- [ ] `.github/workflows/joss_paper.yml` that compiles `paper.md` on push

---

## 3. Work breakdown — five slices in dependency order

### Slice A: three-way parity results (~2 days)

Most valuable to do first because:
1. The Statement of Need rests on the result
2. It tells us if any porting bugs exist before we publicise

Deliverables:
- `scripts/run_three_way_parity.py`: orchestrates the comparison on
  `msp_reference/installed/TEST.DAT` (828 × 17 odour annoyance dataset)
  - Loads via `mmokken.load_msp_dataset`
  - Runs full `mmokken` workflow (aisp, coefH, coefZ, check_*)
  - Invokes `Rscript` on the same data, parses output
  - For MSP 5: pulls reference values from `TEST full report.txt` (a one-time
    manual extraction, hard-coded in the script as a dict — the MSP 5
    program runs interactively, not scriptably)
  - Produces `docs/parity_results.md` with a table per statistic
- `tests/test_msp_parity.py`: pytest assertions on the Python ↔ R comparison
  with documented tolerances per statistic (atol=1e-9 for alpha,
  atol=1e-6 for MS, distributional for stochastic G+)

### Slice B: software pre-release polish (~1 day)

- `LICENSE` file at root (verbatim GPL-3.0 text)
- `CITATION.cff` with ORCID, year, repo URL, software DOI placeholder
- `CHANGELOG.md` with v0.1.0 entry summarising functions, parity, layout
- README badges: CI status, license, JOSS submission, PyPI version
- Sphinx docs polish: one fully-working quickstart example, one parity-result
  summary, published to readthedocs (or GitHub Pages)
- One-page CONTRIBUTING.md

### Slice C: write the paper (~2 days)

- `paper/paper.md`:
  - YAML frontmatter (title, authors, affiliations, date, bibliography)
  - **Summary** (1 paragraph): what the package does, who uses it
  - **Statement of Need** (1–2 paragraphs): why Python, why now, what
    others (PyIRT, mirt) don't do; the three-way validation
  - **Functionality** (3–4 bullet groups): scalability, search, diagnostics,
    I/O
  - **Validation** (table + 1 paragraph): summary of three-way parity
    results, link to `parity_results.md`
  - **Acknowledgements**: PhD context, supervisors when applicable
- `paper/paper.bib`: Mokken 1971, Sijtsma & Molenaar 2002, Van der Ark 2007,
  Molenaar & Sijtsma 2000 (MSP manual), Reckase 2009 (mIRT forward-pointer),
  Sijtsma & Van der Ark 2017 (tutorial)
- `.github/workflows/joss_paper.yml`: build `paper.md` to PDF on push for
  preview / catch-typo

### Slice D: release & DOI (~half day)

Pre-flight security audit before flipping repo public:
- `git log --all --pretty=format: --name-only | sort -u | grep -i "\\.env"`
  should return empty (verified post-filter-repo)
- `git log --all -p | grep -i "OPENAI\\|sk-\\|api_key\\|password" -A0`
  should return nothing meaningful
- Verify `.gitignore` covers `resources/`, `msp_reference/installed/`,
  career-progression data files
- Confirm no respondent-level personal data anywhere in tree

Then:
- Flip repo to public on GitHub
- Enable Zenodo-GitHub integration (https://zenodo.org/account/settings/github/)
- `git tag v0.1.0 -s -m "Initial public release"`
- `git push origin v0.1.0` → triggers Zenodo archive → DOI returned
- Update `CITATION.cff` with the Zenodo DOI; commit; tag `v0.1.0.post1` or
  amend (simpler: include placeholder, post-release update CITATION via
  v0.1.1 patch)

### Slice E: submission (~half day)

- Fill JOSS submission form: repo URL, archive DOI, paper PDF link,
  software description, authors, suggested editor
- Receive tracking issue on https://github.com/openjournals/joss-reviews/issues
- Two open-review reviewers assigned
- Iterate on feedback (usually 1–4 weeks)
- Acceptance → DOI assigned → published

Expected timeline: 4–12 weeks from submission to acceptance.

---

## 4. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Reviewer rejects as "just a port" | High — would block JOSS path | Three-way parity emphasised. Reference future multidim track in Statement of Need. Show GA pure-Python = different design choice from R's Rcpp. |
| Numerical parity worse than expected | Medium — would require tighter tolerances | Tolerances documented per statistic. Stochastic statistics (G+, GA) compared distributionally rather than element-wise. Be upfront in paper. |
| R installation fails in CI | Low | Existing `r-lib/actions/setup-r@v2` works. Fallback: parity script runs locally, paper cites results from `parity_results.md` in repo. |
| MSP 5 numbers harder to parse than expected | Low | Use manual extraction once into a Python dict literal. MSP 5 is dead software — not a re-run dependency. |
| Hidden secret in git history surfaces post-public | High — security incident | Pre-flight audit (see Slice D). Filter-repo already removed `.env`. Double-check before flipping public. |
| Respondent data leak (career-progression dataset) | High — privacy incident | `.gitignore` covers `resources/` already. Audit confirms no tracked rows. Career data never enters the public repo. |
| Stoel H reviewer asks "why not in v0.1?" | Low | Paper explicitly references the upcoming separate publication. |

---

## 5. What this teaches about PhD scope

Three principles this plan illustrates, useful when scoping later work:

1. **Two papers per artefact**: tools and methodologies are different genres.
   The same code can underpin a JOSS paper and a JSS paper that argue
   different things. Don't try to force one into the other's shape.

2. **Validation is publishable**: for a port/tool, "I behave the same as
   well-known X and Y" is a stronger contribution than "I exist". The
   three-way parity is mmokken's USP.

3. **Stepwise PhD publishing**: a small published artefact between bigger
   ones gives a citeable foundation. JOSS-paper makes Track A's
   demonstration paper and the JSS methodology paper easier to write,
   because both can cite the validated tool instead of describing the
   software in their own methods sections.

---

## 6. Open questions / decisions still to make

- **Co-authors**: solo, or include supervisors / contributors? PhD norms
  vary. Decide before paper.md is drafted.
- **Affiliation**: institution name + ORCID for everyone listed.
- **Submission timing**: before or after Track A pilot results? My
  recommendation: before. The JOSS paper is independent of Track A and
  buys you a citeable artefact for Track A's own write-up.
- **Acknowledgements**: who else has materially contributed? Codex
  migration (initial port) was AI-tooled — mention in acknowledgements
  per JOSS convention.
- **License confirmation**: GPL-3.0 matches R `mokken`'s licence and is
  natural for a port; confirm with supervisors no conflict with future
  commercial licensing of mMokken.

---

## 7. Done-when checklist

- [ ] Parity results published in `docs/parity_results.md`
- [ ] Parity test passing in CI
- [ ] LICENSE, CITATION.cff, CHANGELOG.md present
- [ ] `paper/paper.md` ≤ 1000 words, peer-readable
- [ ] All authors have ORCIDs and approved the draft
- [ ] Repo flipped to public after audit
- [ ] `v0.1.0` tag pushed, Zenodo DOI obtained
- [ ] JOSS submission form filled and tracked
- [ ] First reviewer feedback addressed
- [ ] Acceptance, DOI assigned
- [ ] CITATION.cff updated with final DOIs (JOSS + Zenodo)
- [ ] Programme-level migration_journal.md entry recording the JOSS DOI
