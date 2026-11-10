# Building a Database of Bicycle Infrastructure Changes in Norway

**Authors:** Mari Baklund Størseth, Dag Martin Sundelius, Simen Wilsher Lohre, Karl Vika, Valentin Bayas and Isabella Urbano-Trujillo

Code, prompts and LLM output for the term paper *Building a Database of Bicycle Infrastructure Changes in Norway: AI-assisted extraction from historical news articles* (ECS579, Transforming Economic and Financial Research with AI, NHH, Autumn 2026).

The paper tests how accurately a large language model can identify openings of cycling infrastructure in Norwegian newspaper articles, and when and where they took place. Articles from the Retriever/Atekst archive are coded by Gemini 3.8 Flash and compared with two independent human coders.

## Repository contents

| Folder | Contents |
|---|---|
| [`articles_to_csv/`](articles_to_csv) | Scripts that split Retriever/Atekst exports into one row per article, flag duplicates and truncated texts, and create the sheets used for manual coding. `lag_kodeark_uttrekk4.R` handles RTF/Word exports and `txt_to_csv.py` handles text exports. |
| [`prompts/`](prompts) | The coding schema (`Coding_Schema_EN.xlsx`, with the original Norwegian version), both prompt versions (`prompt_v1.md`, `prompt_v2.md`), the JSON output format, an example output, and `prompt_changelog.txt`, which records what changed between versions and why. |
| [`AI_pipeline/`](AI_pipeline) | `run_coding.py` sends each article to Gemini in a separate API call and writes the AI coding next to the human coding. The folder README describes setup, Google Cloud login and how to run it. |
| [`AI_coded_articles/`](AI_coded_articles) | Output of the LLM runs: the validation run on the 34 pilot articles (each coded three times), runs 2–4 on the later extracts, and `Combined_runs_2-4.xlsx` with all 3,187 articles. |
| [`codes/`](codes) | `Codebook_analysis.py`: the analysis behind the paper's results, including the AI vs. human comparison for the pilot, the descriptive results for rounds 2–4, the grouping of relevant articles into 44 projects, and the table of further information in the articles. `coding_further_uses_of_articles.xlsx` is its output, with the project-level coding, the flagged articles and a codebook describing each variable. |

## Model settings

| Setting | Value |
|---|---|
| Model | `gemini-3.8-flash` via Vertex AI (Google Cloud) |
| Thinking level | `low` |
| Temperature | Model default |
| Calls | One independent API call per article, no memory between calls |
| Prompt | `prompts/prompt_v2.md` for all reported runs |
| Repeats | 3 per article in the validation run, used to measure internal consistency |
| Cost | About NOK 70 for the full run of 3,187 articles |

## Data not included

The full newspaper article texts and the manual coding sheets are **not** included in this repository. They contain articles from the Retriever/Atekst archive, many of them behind paywalls, which the licence does not allow us to redistribute. The AI output files include only short evidence quotes.

To reproduce the coding, export articles from Retriever/Atekst with the search terms described in the paper, convert them with the scripts in `articles_to_csv/`, and run `AI_pipeline/run_coding.py`. The pipeline needs Python 3.10 or newer with `google-genai` and `openpyxl`, and a Google Cloud project with the Vertex AI API enabled. The scripts expect the article spreadsheets in the folder layout described in [`AI_pipeline/README.md`](AI_pipeline/README.md).

## Statement on the use of AI

Generative AI is both the subject of this paper and a key tool we used to prepare it. As part of the method, Gemini 3.8 Flash was used to classify and extract information from the newspaper articles (Section 3.2 of the paper). In addition, we used AI assistants to write and debug analysis code, to support the coding of the articles, and to draft, edit, and proofread parts of the text. All AI-generated output was reviewed and revised by the authors, who take full responsibility for the content of the paper.
