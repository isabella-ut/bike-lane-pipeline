"""
Code newspaper articles with Gemini, one independent API call per article.

Reads:   the article spreadsheet (e.g. Articles_coding_round_1.xlsx)
         the prompt file (prompts/prompt_v1.md) and the JSON format (prompts/json_schema_v1.json)
Writes:  outputs/<run_name>.jsonl  - one line per API call (raw answer, parsed coding, tokens, model, prompt version)
         outputs/<run_name>.xlsx   - AI coding next to the human coding, one row per article and repeat
Never overwrites earlier runs: every run gets a new name with a timestamp.

Examples (run from the "GroupWork AI Sem" folder):
  py pipeline/run_coding.py --dry-run                 # show the first prompt and token count, no cost
  py pipeline/run_coding.py --limit 5                 # code the first 5 articles
  py pipeline/run_coding.py --repeats 3 --max-cost-nok 50
  py pipeline/run_coding.py --resume outputs/<run name>.jsonl   # finish an interrupted run (same --prompt and --repeats)
"""

import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import openpyxl
from google import genai
from google.genai import types

# ----------------------------------------------------------------------------
# Settings you may want to change
# ----------------------------------------------------------------------------
DEFAULT_MODEL = "gemini-3.8-flash"     # check the model list in Vertex AI Studio / Model Garden
THINKING_LEVEL = "low"                 # "low" is cheaper; try "medium" if accuracy is weak

# Prices in USD per 1 million tokens. Fill these in from
# https://cloud.google.com/vertex-ai/generative-ai/pricing before a large run.
# Thinking tokens are billed as output tokens. Left as None, the cost guard is off
# and the script only reports token counts.
PRICE_INPUT_USD_PER_M = 0.75
PRICE_OUTPUT_USD_PER_M = 3.75
NOK_PER_USD = 11.0                     # rough exchange rate, update if needed

# Vertex AI (paid from the Google Cloud free trial credit). No API key needed:
# log in once with "gcloud auth application-default login" (see README).
PROJECT_ID = "project-833e3daa-b807-4b3c-b20"        # Google Cloud project ID, shown on console.cloud.google.com
LOCATION = "global"

# Spreadsheet column -> placeholder in the prompt's user message
ARTICLE_COLUMNS = {
    "article_id": "article_id",
    "newspaper": "source",
    "publication_date": "published",
    "title": "title",
    "article_text": "text",
}
# JSON key in the AI output -> human coding column in the spreadsheet
CODING_COLUMNS = {
    "relevant": "relevant",
    "place": "place",
    "kommune": "kommune",
    "date_in_text": "date in text",
    "opening_date": "opening date",
    "date_precision": "date precision",
    "evidence": "evidence",
    "comment": "comment",
}
# ----------------------------------------------------------------------------


def load_prompt(path):
    """Split prompt_v1.md into version, system prompt and user-message template."""
    text = Path(path).read_text(encoding="utf-8")
    version = re.search(r"^Version:\s*(\S+)", text, re.M)
    system = re.search(r"^## SYSTEM PROMPT.*?\n(.*?)^---\s*$", text, re.M | re.S)
    user = re.search(r"^## USER MESSAGE.*?\n(.*)\Z", text, re.M | re.S)
    if not (system and user):
        sys.exit(f"Could not find the SYSTEM PROMPT and USER MESSAGE sections in {path}")
    return (version.group(1) if version else Path(path).stem,
            system.group(1).strip(), user.group(1).strip())


def load_articles(path, sheet=None):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    missing = [c for c in ARTICLE_COLUMNS.values() if c not in header]
    if missing:
        sys.exit(f"Columns missing in {path}: {missing}. Found: {header}")
    articles = []
    for r in rows:
        row = dict(zip(header, r))
        if row.get("article_id") and row.get("text"):
            articles.append(row)
    return articles


def to_text(value):
    if value is None:
        return ""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value).strip()


def render_user_message(template, article):
    msg = template
    for placeholder, column in ARTICLE_COLUMNS.items():
        msg = msg.replace("{{" + placeholder + "}}", to_text(article.get(column)))
    return msg


def check_output(coding, schema):
    """Return a list of problems with the model's answer (empty list = fine)."""
    problems = []
    for key in schema["required"]:
        if key not in coding:
            problems.append(f"missing {key}")
    for key, spec in schema["properties"].items():
        if "enum" in spec and key in coding and coding[key] not in spec["enum"]:
            problems.append(f"{key}={coding[key]!r} not allowed")
    d, p = coding.get("opening_date", ""), coding.get("date_precision", "")
    expected = {10: "day", 7: "month", 4: "year", 0: "not stated"}.get(len(d))
    if d and not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", d):
        problems.append(f"opening_date {d!r} has wrong format")
    elif expected and p != expected:
        problems.append(f"date_precision {p!r} does not match opening_date {d!r}")
    return problems


def cost_usd(in_tokens, out_tokens):
    if PRICE_INPUT_USD_PER_M is None or PRICE_OUTPUT_USD_PER_M is None:
        return None
    return in_tokens / 1e6 * PRICE_INPUT_USD_PER_M + out_tokens / 1e6 * PRICE_OUTPUT_USD_PER_M


def call_model(client, model, system_prompt, user_msg, schema, retries=4):
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_json_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
    )
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(model=model, contents=user_msg, config=config)
        except Exception as e:  # network errors, rate limits, server errors
            if attempt == retries:
                raise
            wait = 2 ** (attempt + 1)
            print(f"  API error ({e.__class__.__name__}: {e}); retrying in {wait}s")
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--articles", default="Articles_coding_round_1.xlsx")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--prompt", default="prompts/prompt_v1.md")
    ap.add_argument("--schema", default="prompts/json_schema_v1.json")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=None, help="only the first N articles")
    ap.add_argument("--ids", default=None, help="comma-separated article IDs to code")
    ap.add_argument("--repeats", type=int, default=1, help="code each article N times (consistency check)")
    ap.add_argument("--max-cost-nok", type=float, default=None, help="stop when the estimated cost reaches this")
    ap.add_argument("--out", default="outputs")
    ap.add_argument("--dry-run", action="store_true", help="show the first prompt and its token count, then stop")
    ap.add_argument("--resume", default=None, help="continue an interrupted run: path to its .jsonl file in outputs/")
    args = ap.parse_args()

    version, system_prompt, user_template = load_prompt(args.prompt)
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    articles = load_articles(args.articles, args.sheet)
    if args.ids:
        wanted = {i.strip() for i in args.ids.split(",")}
        articles = [a for a in articles if to_text(a["article_id"]) in wanted]
    if args.limit:
        articles = articles[: args.limit]
    print(f"{len(articles)} articles x {args.repeats} repeat(s), model {args.model}, prompt {version}")

    if PROJECT_ID == "your-project-id":
        sys.exit("Set PROJECT_ID at the top of run_coding.py to your Google Cloud project ID.")
    # timeout: a call that gets no answer within 2 minutes is retried instead of hanging forever
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION,
                          http_options=types.HttpOptions(timeout=120_000))

    if args.dry_run:
        msg = render_user_message(user_template, articles[0])
        print("\n--- SYSTEM PROMPT ---\n" + system_prompt + "\n\n--- USER MESSAGE ---\n" + msg[:1500])
        n = client.models.count_tokens(model=args.model, contents=system_prompt + "\n\n" + msg)
        print(f"\nInput tokens for this article (system prompt + article): {n.total_tokens}")
        return

    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)
    records = []      # all calls of this run, including those from an earlier, interrupted session
    if args.resume:
        jsonl_path = Path(args.resume)
        run_name = jsonl_path.stem
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        old = {(r.get("prompt_version"), r.get("model")) for r in records}
        if old and old != {(version, args.model)}:
            sys.exit(f"{jsonl_path} was made with prompt/model {old}, not {(version, args.model)}. "
                     "Use the same --prompt and --model as the original run.")
        # failed calls are dropped from the list so they are tried again
        records = [r for r in records if "error" not in r]
        print(f"Resuming {run_name}: {len(records)} calls already done")
    else:
        run_name = f"{dt.datetime.now():%Y%m%d_%H%M%S}_{version}_{args.model}"
        jsonl_path = out_dir / f"{run_name}.jsonl"
    done = {(r["article_id"], r["repeat"]) for r in records}
    total_in = sum(r.get("input_tokens", 0) for r in records)
    total_out = sum(r.get("output_tokens", 0) for r in records)

    try:
        with jsonl_path.open("a" if args.resume else "w", encoding="utf-8") as log:
            for i, art in enumerate(articles, 1):
                for rep in range(1, args.repeats + 1):
                    aid = to_text(art["article_id"])
                    if (aid, rep) in done:
                        continue
                    spent = cost_usd(total_in, total_out)
                    if args.max_cost_nok and spent is not None and spent * NOK_PER_USD >= args.max_cost_nok:
                        print(f"Cost cap reached ({spent * NOK_PER_USD:.2f} NOK). Stopping.")
                        break
                    msg = render_user_message(user_template, art)
                    record = {"run": run_name, "article_id": aid, "repeat": rep, "model": args.model,
                              "prompt_version": version, "thinking_level": THINKING_LEVEL,
                              "time": dt.datetime.now().isoformat(timespec="seconds")}
                    try:
                        resp = call_model(client, args.model, system_prompt, msg, schema)
                        u = resp.usage_metadata
                        in_t = u.prompt_token_count or 0
                        out_t = (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
                        total_in, total_out = total_in + in_t, total_out + out_t
                        record.update(raw=resp.text, input_tokens=in_t, output_tokens=out_t)
                        coding = json.loads(resp.text)
                        record["coding"] = coding
                        record["problems"] = check_output(coding, schema)
                    except Exception as e:
                        record["error"] = f"{e.__class__.__name__}: {e}"
                        coding = {}
                    log.write(json.dumps(record, ensure_ascii=False) + "\n")
                    log.flush()
                    records.append(record)
                    status = record.get("error") or coding.get("relevant", "?")
                    print(f"[{i}/{len(articles)}] {aid} run {rep}: {status}")
                else:
                    continue
                break
    except KeyboardInterrupt:
        print("\nStopped by you (Ctrl+C). Saving what is done so far.")
        print(f"To continue later: python3 pipeline/run_coding.py --resume {jsonl_path} "
              f"--prompt {args.prompt} --repeats {args.repeats}")

    # spreadsheet: AI coding next to the human coding, one row per article and repeat
    by_id = {to_text(a["article_id"]): a for a in load_articles(args.articles, args.sheet)}
    order = {aid: n for n, aid in enumerate(by_id)}
    rows = []
    for rec in sorted(records, key=lambda r: (order.get(r["article_id"], 1e9), r["repeat"])):
        art, coding = by_id.get(rec["article_id"], {}), rec.get("coding", {})
        row = {"article_id": rec["article_id"], "repeat": rec["repeat"]}
        for key, col in CODING_COLUMNS.items():
            row[f"human_{col}"] = art.get(col)
            row[f"ai_{col}"] = coding.get(key, "")
        row["human_coder"] = art.get("coder")
        row["problems"] = "; ".join(rec.get("problems", [])) or rec.get("error", "")
        rows.append(row)

    xlsx_path = out_dir / f"{run_name}.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    if rows:
        ws.append(list(rows[0].keys()))
        for r in rows:
            ws.append([to_text(v) for v in r.values()])
    wb.save(xlsx_path)

    failed = sum("error" in r for r in records)
    spent = cost_usd(total_in, total_out)
    print(f"\n{len(records)} calls in this run, {failed} failed")
    print(f"Tokens: {total_in} input, {total_out} output (incl. thinking)")
    if spent is not None:
        print(f"Estimated cost: {spent:.4f} USD = {spent * NOK_PER_USD:.2f} NOK")
    print(f"Saved {jsonl_path} and {xlsx_path}")
    if failed:
        print(f"Some calls failed. Run again with --resume {jsonl_path} to retry them.")

if __name__ == "__main__":
    main()
