# Review findings: bicycle infrastructure paper

Summary of the reviewer run on `bicycle_infrastructure_paper.pdf` (Claude Sonnet 5.5, 10 Nov 2026).

**What this is:** 143 findings from 18 AI reviewers. Many reviewers flagged the same problems, so they are merged into themes below, ordered by how much they matter. The repo's final editor report was not produced because the numerical reviewer kept failing the strict citation checks. Its 5 findings are included here; all of them were also flagged by other reviewers that passed.

**How to read it:** "(×N)" means N reviewers flagged it independently. Items marked ✔ were checked directly against the paper's text. The rest are AI reviewer judgments, so check them against your PDF before changing anything.

---

## 1. Fix before submitting: concrete errors

These are quick fixes and are clearly wrong as written.

1. ✔ **Unfilled placeholder on the title page.** The author contribution for Valentin Bayas still reads `[add contribution]`.

2. ✔ **Footnote 3 contradicts Table 3 and Section 4.1** (×7, the most-flagged single issue).
   - **Footnote:** says the Stord article was "coded as not relevant by both human coders".
   - **Section 4.1 and Table 3:** Stord is the one article the coders *disagreed* on. The pilot coder said not relevant; the second coder (and the LLM majority) said relevant.
   - **Fix:** correct the footnote, and explain why Stord is counted among the 44 projects (or drop it from Table 7 and the Section 6.3 counts).

3. ✔ **"Only 2 of the 34 unique articles (about 6 percent)" mixes units** (×6). The 2 counts distinct *openings*, not articles. By your own coding, 5 of the 34 articles concern those openings (3 after the pre-opening recoding). The Figure 1 caption ("Only 2 of 70 search hits") has the same problem.
   - **Fix:** use one unit per statement, for example "5 of 34 articles (about 15 percent), concerning 2 distinct openings".

4. ✔ **Grettefoss Bridge status is inconsistent** (×5).
   - **The inconsistency:** Table 2 says "Planned", but its footnote c says it was "Confirmed to have opened 3 November". The abstract and Figure 1 say the pilot had "only two actual openings", which becomes three by the paper's own date.
   - **Fix:** state the reference date for the status and the count, and align Table 2 with footnote c.

5. ✔ **The keyword-precedence rule in Appendix A.3.2 contradicts its own example** (×5).
   - **The contradiction:** the rule is that a word fitting several types gets "the first type in the table". But `bysykkelstativ` contains `stativ` (Parking & storage), which is listed *before* Infrastructure in Table 9, yet the word is classified as Infrastructure.
   - **Related:** `syklende` contains `sykle` (Proximity) but is listed under Infrastructure. `sykkelmulighet` is coloured as Leisure in Figure 2, but none of the Leisure word parts in Table 9 match it.
   - **Fix:** state the precedence the code actually uses, and confirm that Table 8 and Figure 2 follow it.

6. ✔ **Figure 3 text says "the first quarter of 2024 is missing"**, but A.1 and the caption say the gap is January–April 2024 (×5).
   - **Fix:** align the text and flag Q2 2024 as partial. The last quarter (Q4 2026) also only contains October, which affects the "about 9 percentage points" rise.

7. **43 projects / 92 articles vs 44 projects / 96 articles** (×2). Section 5, the abstract and the conclusion use 43/92, while Section 6 and Table 7 use 44/96. Say clearly that the extra one is the pilot-only Stord project. Also say whether the pilot articles overlap rounds 2–4, since their date windows overlap, which could mean double counting.

8. **Figure 2 tick labels.** The ticks read "2%" and "8%", but they sit on equally spaced gridlines between 0% and 10%, so the positions don't match the labels.

9. **Copy-editing.**
   - ✔ Footnote 3: "The 96 articles **consists**" should be "consist".
   - Coding rule 3 (Section 3.1.4): the subject of "counted as metadata" is unclear.
   - Missing commas in "…city centre, for example." (6.1) and "…in this pilot, but the analysis…" (3.1.1).

10. **Unreferenced elements.** Table 6 is never cited in the text (cite it in Section 5). Appendix B is never cited (cite it in Section 3.2).

---

## 2. Biggest substantive issue: the abstract, introduction and conclusion claim more than the body supports

This was the most common theme across reviewers. The body already contains most of the caveats; they just aren't carried into the abstract and conclusion.

- **"97% LLM–human agreement, the same as human–human"** (×8).
  - **The problem:** this rests on 34 articles with only **3 relevant**. A rule that labels everything "not relevant" would already score about 91%.
  - **Fix:**
    - Report positive-class agreement (precision and recall against the pilot coder) and Cohen's kappa.
    - Carry the "indicative only" caveat into the abstract and conclusion.
    - Replace "matched" or "the same rate" with "similar in this small pilot".
- **The full-run counts are unvalidated** (×7). The 92 articles, 43 projects and 29 dated openings are presented as results, but no part of the 3,187-article run was checked against human coding.
  - **Fix:** label them as unvalidated LLM output, or hand-check a random sample and report precision.
- **The FINN.no linkage was not done** (×2). The abstract says the paper "shows how the data can be linked to 700 579 listings", but Section 6.1 says no linkage was made.
  - **Fix:** say the paper describes the listings and proposes a linkage.
- **The NVDB claim rests on one example** (×2). "Articles add an exact opening date that NVDB lacks" is based on the single Homborsund record. Say "in one example".
- **"Keyword search alone is too noisy; an LLM filter is needed"** (×2). This comes from one search term over five weeks, and no non-LLM filter was tested. Limit the claim to the pilot.
- **"A scalable pipeline for creating treatment data"** (×3). Project grouping and NVDB matching were done by hand, and date precision varies. Describe it as a proof of concept for the extraction step.
- **"29 dated to the day or month"** (×1). Only about 19 of 43 projects are dated to the day, and month-level dates can't place listings before or after an opening within that month. Report the day-level count too.
- **Conclusions about "LLMs" rest on one model and one prompt** (Gemini 3.8 Flash, low reasoning). Limit the claim to what was tested.

---

## 3. Validation design (Section 4)

- **The prompt was tuned on the validation set** (×5). The prompt was revised after reviewing output on the same 34 articles and then rerun, so the 97% is not a held-out estimate. Report agreement for the first prompt version, call it a development-set result, and plan a fresh held-out sample.
- **The recoding is undocumented** (×2).
  - About 10 "unclear" or very short articles were recoded as "not relevant". Show agreement with those excluded.
  - Say how the LLM's three categories ("unclear" included) map to relevant/not relevant, and how the majority across 3 runs is taken.
- **Date consistency isn't reported.** Run-to-run consistency is reported for relevance only, not for the extracted *dates*, which are the paper's main output. Also say which run's date is compared with the human coder.
- **"Opening date" is never defined** (×3). The physical opening, the official ceremony and a partial-section opening are all possible. Define the target, and say what the LLM is told to extract.

---

## 4. Missing documentation of the data and sample

- **"Rounds 1–4" are never defined** (×5). Give the search terms, date windows, number of hits, duplicates removed and missing-text exclusions for each round, ending at the 3,187 articles. Say whether the pilot articles are inside rounds 2–4.
- **The exclusion rule contradicts the pilot** (×1). Section 3.1.1 says missing or truncated articles are excluded, but the pilot keeps 4 with missing text and 2 very short ones.
- **The deduplication and grouping rules are undocumented.**
  - The automatic duplicate check missed an online/print pair, and full-run deduplication isn't documented.
  - The rule for grouping 92 articles into 43 projects isn't described.
  - The rule for project-level date and precision when articles disagree isn't given.
- **The keyword lists are missing.** Give the lists and hand-check criteria behind Table 7 and the "ceremony" indicator, and define the ceremony indicator.
- **The seasonality claim is unsupported** (×6). "Openings cluster before winter and summer holidays" relies on article *publication* shares that aren't shown. You also note that July–August has few articles. Show monthly counts, or drop the claim.
- **The county claims have no counts** (×2). "Most projects in Nordland, then Agder and Vestfold" isn't backed by any shown numbers. Add a county table.
- **The listing data needs more detail.**
  - How many listings have empty text?
  - Does "no mention" include missing text?
  - How are relistings and multi-unit listings handled?
  - How are listings assigned to counties across boundary changes?
  - How is text split into words (Table 9)?
- **There's no data availability statement** (×1). Say which data (articles, LLM output, pilot codings, listings) can or can't be shared under the Retriever/Atekst and FINN.no licences.

---

## 5. Proposed econometric analysis (Section 6.3)

- **The attenuation claim is wrong for δ** (×4). The text says date misclassification "could bias the results toward zero". That holds at most for θ. If misdating is larger for low-attention projects, which is your own premise, δ can be biased *away* from zero.
- **Equation (2) has three specification problems** (×2–3).
  - **The lower-order term is missing:** add Near×Attention, without which δ isn't the differential effect.
  - **Near_j should be Near_jp:** say how listings near several projects are handled.
  - **Y means two things:** it is used for both a mention indicator and a price. Define separate outcomes and hypotheses.
- **Restricting to precisely dated projects is a problem** (×3). Almost all day-dated projects are ceremony projects, so this selects on Attention, changes the estimand and leaves little variation in δ.
- **"Date precision depends on attention" (17 of 18 vs 2 of 26) is partly mechanical** (×7). A reported ceremony itself provides a dated event. Describe it as a descriptive association, and use attention measures that don't supply the date.
- **Attention is measured after the opening.** It is post-treatment, so δ is heterogeneity by coverage, not an effect of local awareness.
- **Identification assumptions aren't stated.**
  - Parallel trends and no anticipation: suggest an event study with leads and lags.
  - Spillovers into the "far" group: define the distance bands.
  - Concurrent works around the opening: Table 7 shows these are common.
  - The "quasi-random/exogenous" timing in Table 1 is not supported.
- **The interpretation of listing mentions goes too far** (×4). Cycling mentions in agent text are not evidence of capitalisation or a "stronger selling point". Treat that as a hypothesis, and declare a primary outcome.
- **Feasibility.** Report how many listings fall near each precisely dated project, and discuss power.

---

## 6. Literature and references

- **The literature claim about single projects is too broad.** The review says the cited cycling-effects studies each evaluate one or a few projects. But Kraus & Koch (2021) cover pop-up lanes in 106 cities, and Roaf et al. (2024) is a review of 78 studies.
- **Soften "the closest study"** (Bartik et al. 2026). Consider adding work on LLM/NLP event extraction from news, and on OpenStreetMap change tracking.
- **Check Fyhri et al. (2026):** is it really a difference-in-differences design, and which group does "up to five percentage points" refer to?
- **NVDB has no reference entry.** Add one, with the owner, URL and access date.
- **The GitHub repo "bike-lane-pipeline" has no URL.** Give the URL, the owner and a commit or release, and add it to the reference list.
- **Klein et al. dates don't line up.** The issue date is "Dec. 2026", but the access date is 09/24/2026. Check whether it is online-first.

---

*Source: the reviewer outputs in `reviewer\work\bicycle-infrastructure-paper\reviews\` (17 accepted, 1 rejected). Findings about the text-extraction tool itself were left out, since they're not about the paper.*
