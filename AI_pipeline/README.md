# Gemini coding pipeline – setup in VS Code

The script:
- `run_coding.py` sends each article to Gemini in a separate call, using `prompts/prompt_v1.md` and `prompts/json_schema_v1.json`. It saves a log (`.jsonl`) and a spreadsheet with the AI coding next to the human coding in `outputs/`.

The script expects this layout, with the "GroupWork AI Sem" folder open in VS Code:

```
GroupWork AI Sem/
  Articles_coding_round_1.xlsx
  prompts/prompt_v1.md, json_schema_v1.json
  pipeline/run_coding.py, requirements.txt
  outputs/            (created on the first run)
```

## 1. One-time setup

1. Install Python 3.10 or newer (python.org) and, in VS Code, the **Python** extension from Microsoft.
2. In VS Code: File → Open Folder → `GroupWork AI Sem`.
3. Open a terminal (Terminal → New Terminal) and create a virtual environment:
   ```
   py -m venv .venv
   .venv\Scripts\python.exe -m pip install -r pipeline\requirements.txt
   ```
   If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again. Then pick the `.venv` interpreter when VS Code asks (or Ctrl+Shift+P → "Python: Select Interpreter").

## 2. Google Cloud login and billing (Vertex AI, paid from the free trial credit)

The script runs on Vertex AI, so the free trial credit pays for it. No API key is needed, and the `GEMINI_API_KEY` variable isn't used.

1. Go to https://console.cloud.google.com, select the project that has the free trial credit, and note its **project ID** (on the dashboard; it's not the same as the project name).
2. In that project, open **APIs & Services → Enable APIs** and enable the **Vertex AI API** (Google now also calls it the **Gemini Enterprise Agent Platform API**).
3. Install the Google Cloud CLI: https://cloud.google.com/sdk/docs/install. Then, in a new terminal:
   ```
   gcloud auth application-default login
   gcloud auth application-default set-quota-project <your-project-id>
   ```
   The first command opens your browser to log in with the Google account that owns the credit. The login is stored on your PC, outside the project folder.
4. Put your project ID in `PROJECT_ID` at the top of `run_coding.py`.
5. Don't upgrade the trial to a paid account, so it simply stops when the credit runs out. Also set a budget with email alerts under Billing → Budgets & alerts (e.g. 1,500 NOK).

## 3. Before a run: model and prices

At the top of `run_coding.py`:
- `DEFAULT_MODEL` is `gemini-3.8-flash` (the current stable Flash model on 4 Nov 2026). Check that it is listed in Vertex AI Studio for your project.
- Fill in `PRICE_INPUT_USD_PER_M` and `PRICE_OUTPUT_USD_PER_M` from https://cloud.google.com/vertex-ai/generative-ai/pricing (Vertex prices can differ slightly from AI Studio prices). Only then does `--max-cost-nok` work as a cap; without prices the script reports token counts only.

## 4. Running

```
python3 pipeline/run_coding.py --dry-run                     # shows the first prompt and its token count; costs nothing
python3 pipeline/run_coding.py --limit 5                     # first 5 articles, to test
python3 pipeline/run_coding.py --repeats 3 --max-cost-nok 50 # all articles, 3 times each, stops at ~50 NOK
python3 pipeline/run_coding.py --ids A0065,A0069             # specific articles
python3 pipeline/run_coding.py --max-cost-nok 200 --resume outputs/20261106_120135_v2_gemini-3.8-flash.jsonl
```

Each run gets a new name (`<date>_<time>_<prompt version>_<model>`) and never overwrites earlier runs. The `problems` column flags answers that break the format (for example a date precision that doesn't match the date).


## 5. Workflow in Google Cloud Shell
1. Upload any new or changed files (e.g. prompts/prompt_v3.md) with ⋮ → Upload, and move them into ~/aisem
2. cd ~/aisem
3. python3 pipeline/run_coding.py --prompt prompts/prompt_vX.md --max-cost-nok 50
or: python3 pipeline/run_coding.py --max-cost-nok 200
4. cloudshell download $(ls -t outputs/*.xlsx | head -1)
5. Note the run name and the results in prompts/prompt_changelog.txt


## 6. Tuning the prompt

1. Edit the prompt in a copy: `prompts/prompt_v2.md`, and change the `Version:` line to `v2`. The script reads the system prompt and the user message from the two sections in that file, so keep the headings `## SYSTEM PROMPT` and `## USER MESSAGE` and the `---` line between them.
2. Run with `--prompt prompts/prompt_v2.md` on the same development articles and compare the results with the earlier run.
3. Keep a short note per version on what changed and why (AGENTS.md section 5).

