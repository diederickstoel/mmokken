# Snippets — quotes organised by proposal section

Quotable passages from the research chats, organised against the structure of the PhD research programme proposal (`../research_proposal.docx`). Each block notes the source chat and date so claims remain traceable. For full context, follow the link to the chat.

For a chronological view of all chats, see `index.md`.

---

## §1 — Background and Rationale

### The genesis of the R_D vs R_B framing

The pivotal shift — from "*can an LLM predict progression?*" to "*are the two structures congruent?*" — happens once the 1,700-employee Mokken scales are on the table.

> Nu heb je een empirisch progressiemodel uit gedragsdata. Dus je kunt nu twee structuren vergelijken:
>
> 1. De latente progressiestructuur uit Mokken
> 2. De progressielogica die uit het corpus wordt afgeleid
>
> De echte vraag is niet meer: *Kan een LLM progressie voorspellen?* Maar: **Is de progressiestructuur die uit organisatie-taal wordt afgeleid congruent met de empirische progressiestructuur van medewerkers?**

— *[2026-02-14 LLM en Token Voorspellingen](./2026-02-14_LLM%20en%20Token%20Voorspellingen/chat.md)*

### Related work — AI-GENIE as adjacent but different

> AI‑GENIE represents a major step forward in automating the traditionally labor- and time-intensive process of developing psychometric scales … uses several open- and closed‑source large language models (Gemma 2, Mixtral 8x7b, Llama 3, GPT‑3.5, GPT‑4o) … applies advanced network psychometric methods—including Exploratory Graph Analysis (EGA), Unique Variable Analysis (UVA), and bootstrapped stability metrics.

— *[2025-07-01 AI-GENIE Overview](./2025-07-01_AI-GENIE%20Overview/chat.md)*

*Positioning note.* AI-GENIE uses the LLM as **item generator** and EGA as **validator**. The proposal treats both as **independent ordering sources** and compares them. This is the gap.

---

## §2 — Theoretical Framework

### Items as dual-nature objects; two parallel orderings

The paper-prose formulation of the duality is already drafted in the Lexical Field chat:

> From an LLM we can extract a discursive ordering R_D of the items — whether through direct prompting … or by examining the geometry of item embeddings and identifying directions that correspond to progression. … From item response data we obtain an empirical ordering R_B — a ranking derived from how actual respondents endorse the same items in specific institutional and material contexts. … Both orderings are ordinal relations defined over the same finite set of linguistically formulated items.

— *[2026-02-19 Lexical Field and Order](./2026-02-19_Lexical%20Field%20and%20Order/chat.md)*

### §2.4 — Residual as signal (cross-method extension)

The Lexical Field chat already extends Mokken's classical residual-as-signal principle across methods:

> In classical measurement theory, such a residual would be treated as error — unexplained variance to be minimized or discarded. We draw here on an insight from nonparametric item response theory. Mokken (1971) emphasized that deviations from a cumulative scale are not merely noise but can be informative about the structure of the domain (Meijer, Sijtsma, & Smid, 1990; Van der Ark, 2007). … We extend this principle to the cross-regime context. … The residual represents that part of how people respond to items which cannot be explained by general semantic structure alone — institutional constraints, individual differences, and situational influences.

— *[2026-02-19 Lexical Field and Order](./2026-02-19_Lexical%20Field%20and%20Order/chat.md)*

---

## §6 — Multidimensional Extension (mMokken)

### §6.1 — From IRT/Mokken to mIRT/mMokken: the conceptual leap

> De stap van IRT naar mIRT is de stap van **lineaire niveaus** naar **netwerken van potentie**. … mIRT vertelt je waar je bent op een **kruising van routes** — en welke kant je het best op kunt groeien.

— *[2025-06-19 Dominantie Modellen Rasch Mokken](./2025-06-19_Dominantie%20Modellen%20Rasch%20Mokken/chat.md)*

### Items as crossings — strategic hubs in the path network

> Items die op beide dimensies bijdragen, vormen **strategische hubs** in het leerpad. … i2 en i4 zijn interessante **kruispunten**: zij dragen bij aan beide schalen met verschillende ordinalen.

— *[2025-06-19 Dominantie Modellen Rasch Mokken](./2025-06-19_Dominantie%20Modellen%20Rasch%20Mokken/chat.md)*

### §6.1 — mMokken vs mIRT: parametric vs non-parametric, both as networks

> mMokken is een non-parametrische schaalmethode, geschikt voor situaties waarin je minder aannames wilt doen over de onderliggende verdelingen of itemeigenschappen. … We hebben besproken dat **leerpad-analyse** in een mMokken-netwerk een mooie brug kan slaan tussen ordinale, empirisch gefundeerde paden en de meer theoretische paden in mIRT.

— *[2025-07-07 Kun je lezen](./2025-07-07_Kun%20je%20lezen/chat.md)*

### §6.2 — mMokken as a modern measurement platform (not a 1-on-1 R port)

> Dan moet mMokken niet voelen als "een R-port", maar als een **modern meetmodel-platform** waar Mokken één familie is binnen een breder mIRT-ecosysteem. … mMokken is een Python package voor **(multi)dimensionale meetmodellen** met twee pilaren:
>
> 1. Nonparametrisch (Mokken) — schaalvorming, monotoniciteit, invariantie-diagnostiek, H-coëfficiënten, AISP/GA.
> 2. [Parametric: Rasch, 2PL, GRM, md-2PL]

— *[2026-03-04 AISP functie uitleg](./2026-03-04_AISP%20functie%20uitleg/chat.md)*

---

## §4.1 & §6.2 — Stoel H Multidimensional Scalability Metric

> De **Stoel H**-maat is een nieuwe informatie-theoretische metric die meet hoe gestructureerd een set carrièrepaden of itemresponsen is. Het vergelijkt het **aantal gevonden valide schalen (k)** met het **theoretisch maximale aantal mogelijke schalen** (2ⁿ – 1, bij n items).
>
> - Stoel H ≈ 1: weinig schalen nodig → sterke unidimensionaliteit.
> - Stoel H ≈ 0: veel schalen nodig → hoge multidimensionaliteit of chaos.
>
> Voorbeeld: bij 46 items en 10 valide schalen met H ≥ 0.3 is Stoel H = 0.92 → zeer gestructureerde data.

— *[2025-08-07 Samenvatting Stoel H metric](./2025-08-07_Samenvatting%20Stoel%20H%20metric/chat.md)*

---

## §6.4 — Implementation: R → Python migration

The migration is a concrete prerequisite for Track B's first phase.

> We hebben het R pakket van Mokken. Wat kan Codex doen als we het hele pakket 1 op 1 naar Python willen omzetten?

— *user prompt in [2026-03-06 R naar Python migratie](./2026-03-06_R%20naar%20Python%20migratie/chat.md)*

The chat continues with concrete strategy: use Codex as the migration agent, scope the package functions, set up the Python environment, validate numerical equivalence against the R reference on benchmark datasets. This maps directly to **Phase B1** in the proposal's project plan.

---

## §5 — Demonstration data (career-progression items)

> Kijk een nu heb ik data van 1700 medewerkers. Daar heb ik Mokkenschalen van.

— *user, [2026-02-14 LLM en Token Voorspellingen](./2026-02-14_LLM%20en%20Token%20Voorspellingen/chat.md)*

The career-progression instrument covers:

> Promotie, lateraal, switch domein, switch bedrijf, uitstroom.

— *[2026-02-14 LLM en Token Voorspellingen](./2026-02-14_LLM%20en%20Token%20Voorspellingen/chat.md)*

These five categories are exactly the multidimensional structure that motivates Track B: forcing them into a single Mokken scale loses the substantively interesting distinctions between vertical advancement, lateral mobility, and exit-and-re-entry trajectories.

---

## Cross-reference table — which chat informs which proposal section

| Proposal section | Primary chat | Secondary |
|---|---|---|
| §1 (background) | 2026-02-19 Lexical Field | 2026-02-14 LLM en Token |
| §1 (related work / AI-GENIE) | 2025-07-01 AI-GENIE Overview | — |
| §2 (theoretical framework) | 2026-02-19 Lexical Field | 2026-02-14 LLM en Token |
| §2.4 (residual as signal) | 2026-02-19 Lexical Field | — |
| §3 (RQ4 — crossings) | 2025-06-19 Dominantie Modellen | 2025-07-07 Kun je lezen |
| §4.1 (Mokken estimation) | 2024-12-04 Mokken optimaliseren | 2024-08-16 Mokken Package |
| §4.1 / §6.2 (Stoel H) | 2025-08-07 Stoel H | — |
| §5 (demonstration data) | 2026-02-14 LLM en Token | 2025-07-07 Kun je lezen |
| §6.1-6.2 (mMokken concept) | 2025-06-19 Dominantie Modellen | 2025-07-07 Kun je lezen |
| §6.2 (mMokken architecture) | 2026-03-04 AISP | — |
| §6.4 (R→Python migration) | 2026-03-06 R naar Python | 2026-03-04 Codex env |
