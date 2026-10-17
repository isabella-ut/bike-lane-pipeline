# Building a Database of Bicycle Infrastructure Changes in Norway

Summary based on the presentation "Building a Database of Bicycle Infrastructure Changes in Norway: AI-assisted extraction from historical news articles" (NHH Norwegian School of Economics, 15 October 2026).

## Objective

The project aims to build a georeferenced database of bicycle infrastructure changes in Norway from newspaper archives. The research question is: how accurately can an agentic AI pipeline identify changes in cycling infrastructure from a news archive in Norway?

The motivation is a data gap. Existing maps show where cycling infrastructure is, but almost never when it was implemented. Without exact dates, causal effects are hard to identify, because the strongest designs compare outcomes before and after a route opens. A dataset with exact change dates would allow the following questions to be studied:

- Does cycling infrastructure increase cycling and reduce driving?
- Are cycle lanes capitalised into house prices?
- Does council composition affect bike lane construction?

## Data

- **Main source:** Norwegian newspaper articles from the Retriever archive, retrieved with the search term "Åpning sykkelvei". The articles are free-form Norwegian text describing what, where and when. Examples shown come from Trøndelag, Oslo, Åmli (NRK) and Stavanger–Sandnes.
- **Benchmark:** official records from NVDB, the road database of Statens vegvesen (CSV or API download). It is segment-level, but its dates are unclear. OSM historical records are also named as a benchmark.
- **Scale:** roughly 530–6,400 candidate articles over the last three years.

## Methods

An agentic AI pipeline based on large language models (LLMs) processes the articles in four steps:

1. **Detect:** decide whether an article is relevant. Keyword search returns many articles that do not report an opening.
2. **Extract:** identify the infrastructure type, place and date. Dates may be explicit, relative (e.g. "Mandag", resolved using the publication date) or partial (e.g. "16. juni", with no year).
3. **Deduplicate:** merge several articles on the same project, such as an announcement, an opening and a follow-up, into one record per project.
4. **Geolocate:** match each project to OSM or NVDB.

**Validation:** human raters label a sample at each step, and Norwegian speakers check the article extractions. The approach is scaled up when LLM labelling approximates human labelling. NVDB and OSM historical records serve as benchmarks.

## Expected outputs

- A georeferenced database of bicycle infrastructure changes in Norway, with dates more precise than those in OSM.
- Partial coverage that varies by region.
- A resource that enables natural experiments.
- An accuracy assessment of the LLM-based approach, as framed by the research question.
- If the project succeeds, the pipeline could be applied to other countries.

## Open questions

- Is coverage sufficient? The presentation lists this as an open issue.
- Is a completion date stated in the articles? This is an open issue in the presentation.
- Is the location given precisely enough to georeference? This is an open issue in the presentation.
- The period covered is unspecified. Only "the last 3 years" is mentioned in connection with the article count, and the range of 530–6,400 is not explained.
- Which LLM or model is used, and what "agentic" means in practice, is not stated.
- The presentation gives no sample sizes, accuracy metrics or thresholds for deciding that LLM labelling is close enough to human labelling.
- How OSM is accessed and used is not described, and the NVDB dates are described only as "unclear".
- Whether Retriever is the only article source, or whether other archives will be used, is not stated.
- The planned analyses, such as the difference-in-differences method cited in the references (Callaway and Sant'Anna, 2021), are not described, and the presentation does not say whether they are in scope.
- No timeline, responsibilities or final format of the database (file type, fields, access) are given.
