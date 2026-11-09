"""
Convert Retriever text exports (news_txts/*.txt) into a CSV with the same
columns and conventions as artikler_nytt.csv.

Usage (from the project folder or the pipeline folder):
    python pipeline/txt_to_csv.py
    python pipeline/txt_to_csv.py --txt-dir news_txts --template artikler_nytt.csv \
        --out artikler_nytt3.csv --id-prefix D

How each column is filled:
  artikkel_id     prefix + running number (D0001, D0002, ...). The prefix is
                  different from artikler_nytt.csv ("B") so ids never clash.
  avis            articles whose newspaper name begins with "Stortinget"
                  (case-insensitive) are excluded
                  otherwise, source name from the "<Avis>, DD.MM.YYYY HH:MM" line
  publisert       that date as YYYY-MM-DD
  side            page number from a "Side N" line (print articles), else NA
  tittel          the (possibly wrapped) title lines above the source line
  forfatter       best guess: a "Name Name name@domain" byline at the very
                  start or end of the text. NA when there is no e-mail byline
                  (the txt export has no separate author field).
  antall_ord      number of whitespace-separated words in tekst
  mangler_tekst   TRUE when antall_ord < 30 (same cut-off as artikler_nytt.csv)
  tekst_avkortet  TRUE when the text ends with "…" (Retriever cut it off)
  tekst           body text on one line; image captions ("Bildetekst:"),
                  the copyright footer and the ret.nu link are removed
  duplikat_av     id of the first earlier row with the same avis + title
                  (or identical text), else NA
  mulig_duplikat  TRUE when duplikat_av is set
  finnes_fra_for  artikkel_id in artikler_nytt.csv with the same avis + title,
                  else NA
"""

import argparse
import csv
import re
import sys
from pathlib import Path

SEPARATOR = re.compile(r"^={20,}\s*$")
SOURCE_LINE = re.compile(r"^(?P<avis>.+?), (?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4})(?: \d{2}:\d{2})?\s*$")
PAGE_LINE = re.compile(r"^Side\s+(?P<side>\S+)\s*$")
PUBLISHED_LINE = re.compile(r"^Publisert på (nett|trykk)\.?\s*$")
EMAIL = r"[\w.\-]+@[\w\-]+(?:\.[\w\-]+)+"
NAME_WORD = r"[A-ZÆØÅÉÜÖÄ][\w.\-'’]*"
BYLINE_END = re.compile(rf"((?:{NAME_WORD}\s+){{1,5}}{EMAIL})\s*$")
BYLINE_START = re.compile(rf"^((?:{NAME_WORD}\s+){{1,5}}{EMAIL})\s")
MIN_WORDS = 30


def norm(s):
    """Normalise a string for duplicate matching."""
    s = str(s).lower().replace("–", "-").replace("—", "-")
    return re.sub(r"[^\w]+", " ", s).strip()


def split_articles(raw):
    """Yield the list of lines for each article block in one export file."""
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    # Drop the export header (search query, period, "News Articles:")
    for i, line in enumerate(lines):
        if line.strip().endswith("Articles:"):
            lines = lines[i + 1:]
            break
    block = []
    for line in lines:
        if SEPARATOR.match(line):
            if any(l.strip() for l in block):
                yield block
            block = []
        else:
            block.append(line)
    if any(l.strip() for l in block):
        yield block


def parse_article(block):
    lines = [l.rstrip() for l in block]
    while lines and not lines[0].strip():
        lines.pop(0)

    # Header: title lines, then the "<Avis>, DD.MM.YYYY HH:MM" line
    src_idx = next((i for i, l in enumerate(lines[:8]) if SOURCE_LINE.match(l.strip())), None)
    if src_idx is None:
        return None
    m = SOURCE_LINE.match(lines[src_idx].strip())
    avis = m.group("avis").strip()
    publisert = f"{m.group('y')}-{m.group('m')}-{m.group('d')}"
    tittel = " ".join(l.strip() for l in lines[:src_idx] if l.strip())

    i = src_idx + 1
    side = None
    while i < len(lines) and i <= src_idx + 3:
        s = lines[i].strip()
        pm = PAGE_LINE.match(s)
        if pm:
            side = pm.group("side")
        elif PUBLISHED_LINE.match(s):
            i += 1
            break
        elif s:
            break
        i += 1

    # Body: everything up to the caption or the copyright footer
    body = []
    for line in lines[i:]:
        s = line.strip()
        if s.startswith("Bildetekst:") or s.startswith("©") or re.match(r"^(Se webartikkelen|Les hele nyheten) på", s):
            break
        if "©" in s and "<br>" in s:  # footer glued onto the last text line
            s = s.split("©")[0].rstrip(" |")
            body.append(s)
            break
        body.append(s)
    tekst = re.sub(r"\s+", " ", " ".join(body)).strip()

    forfatter = None
    mm = BYLINE_END.search(tekst) or BYLINE_START.search(tekst)
    if mm:
        forfatter = mm.group(1).strip()

    antall_ord = len(tekst.split())
    return {
        "avis": avis,
        "publisert": publisert,
        "side": side,
        "tittel": tittel,
        "forfatter": forfatter,
        "antall_ord": antall_ord,
        "mangler_tekst": antall_ord < MIN_WORDS,
        "tekst_avkortet": tekst.endswith("…"),
        "tekst": tekst or None,
    }


def main():
    here = Path(__file__).resolve().parent
    root = here.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--txt-dir", default=root / "news_txts", type=Path)
    ap.add_argument("--template", default=root / "artikler_nytt.csv", type=Path)
    ap.add_argument("--out", default=root / "artikler_nytt3.csv", type=Path)
    ap.add_argument("--id-prefix", default="D")
    ap.add_argument("--overwrite", action="store_true", help="allow replacing an existing output file")
    args = ap.parse_args()

    if args.out.exists() and not args.overwrite:
        sys.exit(f"{args.out} already exists. Use --overwrite to replace it.")

    with open(args.template, encoding="utf-8-sig", newline="") as f:
        template = csv.DictReader(f)
        columns = template.fieldnames
        if columns is None:
            sys.exit(f"{args.template} has no header row.")
        known = {}
        for r in template:
            known.setdefault((norm(r["avis"]), norm(r["tittel"])), r["artikkel_id"])

    rows = []
    for path in sorted(args.txt_dir.glob("*.txt")):
        raw = path.read_text(encoding="utf-8-sig")
        n_before = len(rows)
        n_stortinget = 0
        for block in split_articles(raw):
            art = parse_article(block)
            if art is None:
                print(f"  skipped a block in {path.name} (no source/date line found)")
                continue
            if art["avis"].casefold().startswith("stortinget"):
                n_stortinget += 1
                continue
            rows.append(art)
        print(
            f"{path.name}: {len(rows) - n_before} articles "
            f"({n_stortinget} Stortinget articles excluded)"
        )

    seen_title, seen_text = {}, {}
    for n, r in enumerate(rows, start=1):
        r["artikkel_id"] = f"{args.id_prefix}{n:04d}"
        key = (norm(r["avis"]), norm(r["tittel"]))
        tkey = norm(r["tekst"]) if r["tekst"] and r["antall_ord"] >= MIN_WORDS else None
        first = seen_title.get(key) or (seen_text.get(tkey) if tkey else None)
        r["duplikat_av"] = first
        r["mulig_duplikat"] = first is not None
        seen_title.setdefault(key, r["artikkel_id"])
        if tkey:
            seen_text.setdefault(tkey, r["artikkel_id"])
        r["finnes_fra_for"] = known.get(key)

    boolean_columns = {"mangler_tekst", "tekst_avkortet", "mulig_duplikat"}
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        for rec in rows:
            cells = []
            for c in columns:
                v = rec[c]
                if c in boolean_columns:
                    cells.append("TRUE" if v else "FALSE")
                elif v is None:
                    cells.append("NA")
                else:
                    cells.append(v)
            writer.writerow(cells)

    print(f"\nWrote {len(rows)} rows to {args.out}")
    print(f"  mangler_tekst TRUE: {sum(r['mangler_tekst'] for r in rows)}")
    print(f"  mulig_duplikat TRUE: {sum(r['mulig_duplikat'] for r in rows)}")
    print(f"  finnes_fra_for set: {sum(r['finnes_fra_for'] is not None for r in rows)}")
    print(f"  forfatter found: {sum(r['forfatter'] is not None for r in rows)}")


if __name__ == "__main__":
    main()
