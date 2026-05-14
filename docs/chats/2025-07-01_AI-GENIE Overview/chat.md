# AI-GENIE Overview

- **Chat-ID:** `68641dbf-7124-8010-ae5b-2df962ea4ecf`
- **Aangemaakt:** 2025-07-01 17:41
- **Laatst bijgewerkt:** 2025-07-07 15:18
- **Aantal berichten:** 16

---

## 🧑 Gebruiker · 2025-07-01 17:41

Are you familiar with AI-GENIE (Automatic Item Generation and Validation via Network Integrated Evaluation).

## 🤖 Assistent · 2025-07-01 17:41

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:41

```unknown
search("Are you familiar with AI-GENIE (Automatic Item Generation and Validation via Network Integrated Evaluation).")
```

## 🤖 Assistent · 2025-07-01 17:41

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:41

```unknown
{"search_query":[{"q":"AI-GENIE Automatic Item Generation and Validation via Network Integrated Evaluation"}]}
```

## 🔧 Tool (web.run) · 2025-07-01 17:41

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:41

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:41

Yes, I’m familiar with AI‑GENIE — it stands for **Automatic Item Generation and Validation via Network‑Integrated Evaluation**. It's a recent, fully automated methodology in psychometrics that:

- Uses large language models (LLMs) like Gemma 2, Llama 3, Mixtral, GPT‑3.5, and GPT‑4o to generate items (e.g., psychological test questions).
- Applies advanced **network psychometric methods**—including Exploratory Graph Analysis (EGA), Unique Variable Analysis (UVA), and bootstrapped stability metrics—to automatically validate and refine item pools without human data collection citeturn0search0turn0search1.
- Was introduced by Hudson Golino, Lara Lee Russell‑Lasalandra, and Alex Christensen in the paper “Generative Psychometrics via AI‑GENIE,” published in September 2024 citeturn0search1turn0search8.
- Demonstrated through simulations (e.g. for Big Five personality scales) that it improves structural validity and item stability—Normalized Mutual Information (NMI) improved up to about 15% in some conditions citeturn0search1turn0search5.
- Even offers practical training: workshops (e.g., Statistical Horizons) teach how to implement AI‑GENIE in R to generate and validate items “in silico” without human samples citeturn0search6turn0search9.

In short, AI‑GENIE represents a major step forward in automating the traditionally labor- and time-intensive process of developing psychometric scales.

Would you like more detail on its methodology, performance, code availability (e.g., an R package), or how to apply it in practice?

## 🧑 Gebruiker · 2025-07-01 17:43

Can you what techniques they are using?

## 🤖 Assistent · 2025-07-01 17:43

```unknown
search("Can you what techniques they are using?")
```

## 🤖 Assistent · 2025-07-01 17:44

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:43

```unknown
{"search_query":[{"q":"Generative Psychometrics via AI-GENIE Hudson Golino techniques network integrated evaluation EGA UVA"},{"q":"AI-GENIE Automatic Item Generation Validation network psychometric methods"}]}
```

## 🔧 Tool (web.run) · 2025-07-01 17:43

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:44

*(leeg)*

## 🤖 Assistent · 2025-07-01 17:43

AI‑GENIE employs a multi-stage pipeline that blends **LLM-powered item generation** with **network‑based psychometric validation**, all fully automated:

---

### 1. **LLM‑based item generation with prompt engineering**  
- Uses several open- and closed‑source large language models (Gemma 2, Mixtral 8x7b, Llama 3, GPT‑3.5, GPT‑4o).  
- Relies on few‑shot prompts (e.g., using Big Five items as examples, assigning the model an “expert personality methodologist” persona) to generate targeted items—including reverse‑keyed versions. Items are generated in batches to build large initial pools (e.g., ~300 items/sample) citeturn0search2turn0search1.

---

### 2. **Embedding items in semantic space**  
- Items are embedded via OpenAI’s `text-embedding-3-small` to convert text into numeric vectors capturing their semantic content. This enables similarity assessments useful for later steps citeturn0search2turn0search1.

---

### 3. **Exploratory Graph Analysis (EGA)**  
- Constructs a network (e.g., using graphical lasso or TMFG), then applies community detection (e.g., Walktrap algorithm) to estimate the dimension structure.  
- Step-size in the Walktrap algorithm is optimized by maximizing **Normalized Mutual Information (NMI)** between detected communities and known traits (e.g., Big Five) citeturn0search2turn0search1.

---

### 4. **Unique Variable Analysis (UVA)**  
- Detects local redundancies using weighted topological overlap.  
- Implements a tighter cutoff (0.20 instead of the typical 0.25) to identify too‑similar items, and removes them iteratively citeturn0search1turn0search8.

---

### 5. **Bootstrapped EGA stability (bootEGA)**  
- Performs bootstrap sampling to evaluate the stability of both item assignments and dimensions.  
- Items with stability below a threshold (commonly 0.75) are removed. This loop continues (typically 2–3 rounds) until all remaining items are stable citeturn0search2turn0search1.

---

### 🔍 Why these techniques?  
- **LLM generation + prompt design** ensures diverse, high-quality item pools efficiently.  
- **Embedding + network modeling (EGA)** captures latent structure in semantic/item space without traditional factor analysis.  
- **UVA** prevents redundancy—crucial for item clarity, fairness, and interpretability.  
- **bootEGA** secures robustness and structural validity, ensuring items reliably reflect constructs across resampling.

---

### Empirical strengths demonstrated  
- Across 15 conditions (5 models × 3 temperatures), AI‑GENIE consistently increased **NMI**, sometimes up to **+15.4%**, confirming better alignment with theoretical constructs citeturn0search2turn0search1.  
- The methodology works **“in silico,”** reducing the need for repeated human data collection and expert validation rounds citeturn0search0turn0search9.

---

In short, AI‑GENIE uniquely integrates **automated item generation** (via LLMs and smart prompting) with **network psychometric techniques** (EGA, UVA, bootEGA) to deliver a fully automated pipeline for psychometric scale creation and validation. Let me know if you'd like to explore any of these steps, request code examples (e.g., in R), or see case studies in detail!
