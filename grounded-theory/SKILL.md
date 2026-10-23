---
name: grounded-theory
description: >-
  Applies Grounded Theory (Glaser & Strauss) and investigative sensemaking to qualitative,
  OSINT, journalistic, and mixed-methods analysis. Use when analyzing news, community forums,
  reviews, documents, or socio-economic data to move beyond dry fact reporting toward deeper
  understanding: detecting anomalies and surprises, analyzing language and framing (in-vivo codes),
  exposing contradictions between declarations and actions, coding processes (open, axial, selective),
  and iteratively building and falsifying hypotheses via the Constant Comparative Method.
---

# Grounded Theory & Investigative Sensemaking Skill (Glaser & Strauss)

Use this skill whenever your task is to **understand a social, organizational, political, or economic reality** rather than merely summarizing dry facts. Inspired by Barney Glaser and Anselm Strauss (*The Discovery of Grounded Theory*, 1967), Kathy Charmaz's constructivist coding, and Charles Sanders Peirce's abductive reasoning, this workflow turns an AI agent from a passive stenographer into an investigative researcher.

---

## Core Epistemological Stance: Beyond Stenography

Dry reporting answers only *"What happened?"*. Grounded sensemaking asks:
1. **What is surprising or anomalous here?** (*Zdziwienie poznawcze*)
2. **What language are actors using to frame or obscure reality?** (*Wrażliwość na język i kody in vivo*)
3. **Where do words contradict actions, numbers, or incentives?** (*Sprzeczności strukturalne*)
4. **What underlying social/economic process explains these scattered facts?** (*Teoria ugruntowana w danych*)

> [!IMPORTANT]
> **Epistemic Hygiene (Fact vs. Hypothesis Separation):**
> Never blur raw facts with interpretations, and never write sensationalist tabloid prose. Keep factual reporting rigorous and exact (dates, numbers, names, votes), and place interpretations, anomalies, and hypotheses into explicitly marked analytical sections or theoretical memos (`hipotezy/`).

---

## The 5 Pillars of Grounded Inquiry

### 1. Abductive Surprise & Anomaly Detection (*Zdziwienie*)
Begin every analysis by scanning for friction between expectations and observations:
- **Unexpected alliances or votes:** Why did actor $A$ vote with rival $B$ right after a public conflict?
- **Disproportionate reactions:** Why is a minor procedural issue generating 50 angry comments or an emergency session, while a multi-million debt passes quietly?
- **Conspicuous silences (*Znaczące milczenie*):** Who failed to speak up? Which numbers were omitted from an official report? Why does a job offer hide the employer's name or salary range?
- **Cross-domain anomalies:** Why are luxury real estate prices hitting record highs in a town where local job postings offer mostly minimum-wage physical labor?

### 2. Language Sensitivity & *In-Vivo* Coding (*Analiza języka*)
Treat language as data, not a transparent window onto facts:
- **Capture *In-Vivo* Codes:** Preserve exact, telling phrases used by actors and citizens (e.g. `"odpolitycznienie placówki"`, `"minister kazał"`, `"dług na pokolenia"`). They reveal local mental models and collective emotions.
- **Deconstruct Bureaucratic Euphemisms:** Translate institutional jargon into concrete actions:
  - *"Optymalizacja zatrudnienia / racjonalizacja sieci"* $\rightarrow$ layoffs or ward closures.
  - *"Przesunięcie horyzontu obsługi zadłużenia do 2050 r."* $\rightarrow$ rolling current deficits onto future taxpayers.
  - Passive voice (*"powstało zadłużenie"*, *"dokumenty nie dotarły"*) $\rightarrow$ ask **who** made the decision or blocked access.
- **Framing Asymmetry:** Compare how two portals or factions describe the exact same event (what goes into the headline vs. the last paragraph).

### 3. Contradiction Mapping (*Sprzeczności*)
Actively triangulate across four planes to expose tensions:

| Plane A | vs. | Plane B | Analytical Question |
| :--- | :---: | :--- | :--- |
| **Official Declarations** (PR, speeches) | $\leftrightarrow$ | **Resource Flows & Votes** (*Follow the money*) | Do budget allocations and roll-call votes match public rhetoric? |
| **Elite Narrative** (officials, press releases) | $\leftrightarrow$ | **Grassroots Experience** (comments, forum, reviews) | How do citizens or patients experience the policy on the ground? |
| **Micro-Market Signals** (job ads, property prices) | $\leftrightarrow$ | **Macro/Institutional Claims** | What do classified ads (labor shortages, wage offers, asset sales) say about actual household and firm health? |
| **Past Promises** (archives) | $\leftrightarrow$ | **Present State** | What was promised 6–24 months ago vs. delivered today? |

### 4. Three-Stage Grounded Coding (*Kodowanie Glasera i Straussa*)
When tagging notes or structuring findings, move from topics to **processes**:
1. **Open Coding (*Kodowanie otwarte*):**
   - Avoid static noun tags (`#szpital`, `#drogi`). Use **process/action concepts** (*gerunds* / rzeczowniki odczasownikowe): e.g., `#przerzucanie-kosztow`, `#kupowanie-wiekszosci`, `#polaryzacja-mieszkaniowa`, `#drenaz-fachowcow`, `#fasadowa-konsultacja`.
2. **Axial Coding (*Kodowanie osiowe*):**
   - Connect open codes around an axis using Strauss's paradigm model:
     - **Causal Conditions** (what triggered it?) $\rightarrow$ **Central Phenomenon** (what is the core tension?) $\rightarrow$ **Context / Intervening Conditions** (legal, financial, demographic constraints) $\rightarrow$ **Action/Interaction Strategies** (how actors maneuver) $\rightarrow$ **Consequences** (intended & unintended).
3. **Selective Coding (*Kodowanie selektywne*):**
   - Identify the overarching **Core Category** that links seemingly unrelated threads (e.g. how hospital debt, long-term road loans, labor market outflows, and real estate polarization reflect a single structural dynamic).

### 5. Constant Comparative Method & Theoretical Memos (*Hipotezy i Noty Teoretyczne*)
Every hypothesis is a living analytical object tested against incoming data:
- **Formulate Explicit Hypotheses:** State a clear causal or structural claim (*"We hypothesize that X occurs because Y"*).
- **Maintain Dual Evidence Ledgers:**
  - **Dowody ZA (*Confirming Evidence*):** Facts, quotes, votes, or numbers supporting the hypothesis.
  - **Dowody PRZECIW (*Negative Cases / Falsification*):** Mandatory search for counter-evidence. If new data contradicts a hypothesis, **revise or falsify it**—never ignore disconfirming facts.
- **Theoretical Sampling (*Próbkowanie teoretyczne*):** Every memo must end with **next verification steps**—what specific archival document, Google query, dataset, or statistical test is needed next to confirm or refute the hypothesis.

---

## Standard Template for a Theoretical Memo (`hipotezy/<slug>.md`)

When maintaining a knowledge base or Obsidian Vault, structure each hypothesis note as follows:

```markdown
---
title: "Hipoteza: [Krótki, procesowy tytuł zjawiska]"
date: YYYY-MM-DD
updated: YYYY-MM-DD
status: weryfikowana # zalążek | weryfikowana | potwierdzona | zmodyfikowana | obalona
confidence: średnia # niska | średnia | wysoka
tags:
  - hipoteza
  - [kody-procesowe]
---

# 💡 Hipoteza: [Tytuł]

## 1. Zdziwienie wyjściowe i sprzeczność (Punkt wyjścia)
Co wzbudziło zdziwienie? Jakie sprzeczne sygnały (język, liczby, zachowania) doprowadziły do postawienia tej hipotezy?

## 2. Treść hipotezy (Model osiowy)
- **Zjawisko centralne:** ...
- **Mechanizm przyczynowy:** Dlaczego tak się dzieje? Kto odnosi korzyść, a kto ponosi koszt?
- **Powiązane byty i tematy:** [[osoba/instytucja/temat]]

## 3. Metoda ciągłego porównywania (Dowody)
### ✅ Przesłanki i dowody ZA:
- `[YYYY-MM-DD]` Fakt / cytat *in vivo* / dane liczbowe...

### ❌ Przesłanki PRZECIW i przypadki negatywne (Falsyfikacja):
- `[YYYY-MM-DD]` Co przeczy tej tezie? Jakie alternatywne wyjaśnienie jest możliwe?

## 4. Próbkowanie teoretyczne (Co trzeba sprawdzić dalej?)
- **Dla Dziennikarza (obserwacja bieżąca):** Na co zwracać uwagę w kolejnych dniach (np. ogłoszenia, sesje, komentarze)?
- **Dla Kontekstualizatora (archiwum / OSINT):** Jakie archiwalne artykuły, BIP, KRS lub powiązania personalne należy prześwietlić?
- **Dla Statystyka (weryfikacja ilościowa R):** Jaki wskaźnik, rozkład lub korelację należy policzyć na twardych danych?
```

---

## Multi-Agent Synergy Pattern

When operating in a multi-agent research team:
1. **Field Journalist / Primary Observer:** Detects daily surprises, codes *in-vivo* language, monitors grassroots signals (classifieds, job offers, comments), updates evidence ledgers, and posts investigative requests.
2. **Archival Contextualizer / OSINT Researcher:** Takes theoretical sampling questions from hypotheses and the team forum, digs into historical archives, registries, and web sources, and supplies deep background and longitudinal comparisons.
3. **Quantitative Statistician (R):** Treats qualitative hypotheses as testable statistical claims—aggregating time series (labor market, real estate, civic engagement) to confirm or falsify narrative intuitions with hard numbers.
