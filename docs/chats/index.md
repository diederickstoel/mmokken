# Research chats — chronological index

Conversations that fed into the PhD research programme proposal in `../research_proposal.docx`. Copied from the ChatGPT export of 2026-04-15.

For a thematic, quote-by-quote view aligned with the proposal sections, see `snippets.md`.

## Tag legend

- **#theory** — conceptual / methodological foundations
- **#mokken-basics** — classical Mokken scale analysis
- **#mIRT-mMokken** — multidimensional Mokken / mIRT bridge
- **#R_D-R_B** — discursive vs behavioural ordering comparison
- **#network-of-paths** — multidim structure as item network with crossings
- **#Stoel-H** — Stoel H multidimensional scalability metric
- **#implementation** — Python package, migration, tooling
- **#related-work** — adjacent literature (AI-GENIE, etc.)
- **#data** — career-progression dataset, 1,700 employees
- **#meta** — project organisation, not substantive content

## Chronological table

| Date | Title | Tags | One-line takeaway |
|---|---|---|---|
| 2024-08-16 | [Mokken Package Overview](./2024-08-16_Mokken%20Package%20Overview/chat.md) | #mokken-basics | First exploration of the R `mokken` package — foundations for later migration. |
| 2024-12-04 | [Mokken-analyse optimaliseren](./2024-12-04_Mokken-analyse%20optimaliseren/chat.md) | #mokken-basics #implementation | Practical R script with `mokken` + `gridExtra` for visualising scalability. |
| 2025-06-19 | [Dominantie Modellen Rasch Mokken](./2025-06-19_Dominantie%20Modellen%20Rasch%20Mokken/chat.md) | #theory #mIRT-mMokken #network-of-paths | **Core conceptual chat.** Dominance models, mIRT as a network of dimensions, "items als kruispunten" / strategic hubs in the multidim learning path. 28k lines — most theoretically substantive single source. |
| 2025-07-01 | [AI-GENIE Overview](./2025-07-01_AI-GENIE%20Overview/chat.md) | #related-work | Golino et al.'s LLM-based item generation pipeline with EGA validation. Reference point for positioning the proposal: AI-GENIE = LLM as item generator; this proposal = LLM as ordering source. |
| 2025-07-02 | [differentiatie](./2025-07-02_differentiatie/chat.md) | #theory | Audio-transcript; LLM-as-transformer analogy explored at the level of biology/gender. Tangential to mokken but conceptually informs the "LLM as structure-revealer" framing. |
| 2025-07-07 | [Kun je lezen](./2025-07-07_Kun%20je%20lezen/chat.md) | #mIRT-mMokken #data | Compact summary of mIRT/mMokken bridge with explicit "leerpaden door netwerk" framing. First mention attached the TRA-ind.csv (career data). |
| 2025-08-07 | [Samenvatting Stoel H metric](./2025-08-07_Samenvatting%20Stoel%20H%20metric/chat.md) | #Stoel-H | Summary of the Stoel H Multidimensional Scalability Metric docx. The information-theoretic global structure index (k vs 2ⁿ−1). |
| 2026-02-14 | [LLM en Token Voorspellingen](./2026-02-14_LLM%20en%20Token%20Voorspellingen/chat.md) | #R_D-R_B #genesis | **Origin chat for the R_D vs R_B idea.** Pivot from "can an LLM predict progression?" to "is the LLM-derived progression structurally congruent with the Mokken-derived one?" |
| 2026-02-19 | [Lexical Field and Order](./2026-02-19_Lexical%20Field%20and%20Order/chat.md) | #R_D-R_B #formalisation | **Paper-prose version of the framework.** Lexical fields, two orderings, item as mediator between language and behaviour, residual-as-signal extended cross-method. Mineable directly for the methodological paper. |
| 2026-03-04 | [AISP functie uitleg](./2026-03-04_AISP%20functie%20uitleg/chat.md) | #mIRT-mMokken #implementation | **mMokken package architecture.** Reframes mMokken as a modern meetmodel-platform with estimation engine (not a 1-on-1 R port). |
| 2026-03-04 | [Codex environment setup](./2026-03-04_Codex%20environment%20setup/chat.md) | #implementation #meta | Practical: setting up an OpenAI Codex environment for the mokken migration work. |
| 2026-03-06 | [R naar Python migratie](./2026-03-06_R%20naar%20Python%20migratie/chat.md) | #implementation | Strategy and concrete plan for migrating the R `mokken` package to Python via Codex. |
| 2026-03-07 | [MPS5 software in project](./2026-03-07_MPS5%20software%20in%20project/chat.md) | #implementation #related-work | Original MPS5 Mokken software (legacy, pre-R) located and reviewed for inclusion. |
| 2026-04-15 | [Project samenvatting opties](./2026-04-15_Project%20samenvatting%20opties/chat.md) | #meta | Project-export and summarisation options. Most recent chat; useful as project-state snapshot, not theoretically substantive. |

## Narrative arc

1. **2024-08 → 2024-12**: classical Mokken footing. Tooling familiarisation in R.
2. **2025-06 → 2025-07**: the conceptual leap. Dominance models reread as networks; "leerpaden" reframed as paths through a multidim space with items as nodes and crossings as hubs. mMokken introduced as the non-parametric counterpart to mIRT.
3. **2025-08**: Stoel H metric formalised — gives the multidim regime a global scalability index.
4. **2026-02**: the second conceptual leap. With Mokken scales on 1,700 employees in hand, the comparison shifts from *"can an LLM predict progression?"* to *"is the LLM-derived discursive ordering structurally congruent with the Mokken-derived behavioural ordering?"*. By 2026-02-19 the idea is paper-shaped.
5. **2026-03**: implementation phase begins — mMokken package architecture, R→Python migration plan, Codex environment, MPS5 legacy artefacts retrieved.
6. **2026-04**: meta — taking stock of the project state.
