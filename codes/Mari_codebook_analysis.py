# %% [markdown]
# # Codebook: analysis of the LLM-coded newspaper articles
#
# Term paper "Creating a Database of Bike Lane Infrastructure" (NHH).
# Compiled by Mari, 9 November 2026.
#
# The code was written with assistance from Claude (Anthropic) based on
# the authors' instructions. All steps, hand coding and results were
# checked by the authors.
#
# The file collects all code used for the following parts of the analysis:
#
#   Part 1  Pilot sample (round 1): AI vs. human coding, overlap between rounds
#   Part 2  Section 5 Results: descriptive analysis of rounds 2-4
#           (Combined_runs_2-4.xlsx), temporal and spatial distribution
#   Part 3  Section 6 Further Uses of the Articles: grouping into projects,
#           coverage and attention, field-group inventory (Table tab:inventory)
#   Part 4  Export of the project coding (appendix file)
#   Part 5  Figures (not used in the current draft of Section 5)
#
# Run from the project folder:  py Mari_codebook_analysis.py
# Requires: pandas, openpyxl, matplotlib (Part 5 only).
# All outputs are written to the folder codebook_output/ so that existing
# files in the project folder are not overwritten.
#
# The file uses "# %%" cells, so it can be run cell by cell in VS Code.

# %% Part 0: setup and helper functions
import os
import re
import collections
import openpyxl
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'codebook_output')
os.makedirs(OUT, exist_ok=True)

ROUND_FILES = {1: 'Articles_coding_round_1.xlsx', 2: 'Articles_coding_round_2.xlsx',
               3: 'Articles_coding_round_3.xlsx', 4: 'Articles_coding_round_4.xlsx'}
RUN_FILES = {1: '20261104_121554_v2_gemini-3.8-flash.xlsx',          # pilot, 3 repeats
             2: '20261104_135045_v2_gemini-3.8-flash_run_2.xlsx',
             3: '20261106_092043_v2_gemini-3.8-flash_run_3.xlsx',
             4: '20261106_120135_v2_gemini-3.8-flash_run_4.xlsx'}
COMBINED = 'Combined_runs_2-4.xlsx'


def fix(x):
    """Repair mojibake: some text (mainly round 3) is UTF-8 read as cp1252."""
    if isinstance(x, str):
        try:
            return x.encode('cp1252').decode('utf-8')
        except Exception:
            return x
    return x


def load(f):
    """First sheet of an Excel file as a DataFrame (text repaired, empty rows dropped)."""
    rows = list(openpyxl.load_workbook(os.path.join(BASE, f), read_only=True)
                .worksheets[0].iter_rows(values_only=True))
    return pd.DataFrame([[fix(x) for x in r] for r in rows[1:] if r[0]], columns=rows[0])


def norm_src(s):
    """Merge print/online editions of the same outlet ("Pluss"/"Login")."""
    return re.sub(r'\s+(Pluss|Login)$', '', str(s).strip())


# Article metadata for all four rounds: article_id -> source, date, title, text
meta = pd.concat([load(f).assign(round=r) for r, f in ROUND_FILES.items()])
meta = meta.drop_duplicates('article_id').set_index('article_id')
meta['src'] = meta.source.map(norm_src)
meta['pub'] = pd.to_datetime(meta.published.astype(str).str[:10], errors='coerce')
print('Articles with metadata, rounds 1-4:', len(meta))


# %% [markdown]
# ## Part 1: Pilot sample (round 1)
# In AI run 1, each pilot article is coded three times (column `repeat`).
# The file also contains the human coding used in the validation (Section 4).

# %% Part 1a: AI vs. human coding in the pilot sample
pilot = load(RUN_FILES[1])
print('Pilot rows:', len(pilot), '| unique articles:', pilot.article_id.nunique(),
      '| repeats:', pilot.repeat.value_counts().to_dict())
for col in ['ai_relevant', 'human_relevant', 'ai_date precision', 'human_coder']:
    print(col, pilot[col].value_counts(dropna=False).to_dict())
print('problems (top 5):', pilot.problems.value_counts().head(5).to_dict())

# Articles where the AI or the human coder found an opening, saved for reading by hand
flag = (pilot.ai_relevant != 'no') | ~pilot.human_relevant.isin([None, 'NA', 'no', '0', 0])
cols = ['article_id', 'repeat', 'human_relevant', 'ai_relevant', 'ai_place', 'ai_kommune',
        'ai_date in text', 'ai_opening date', 'ai_date precision', 'human_opening date']
pilot[flag][cols].to_csv(os.path.join(OUT, 'pilot_relevant.csv'), index=False, encoding='utf-8-sig')

# %% Part 1b: overlap between search rounds 1-3 (same outlet and title, or same text)
key = meta.src + '|' + meta.title.astype(str).str.strip().str.lower()
k = {r: set(key[meta['round'] == r]) for r in (1, 2, 3)}
print('Round 1 in round 2:', len(k[1] & k[2]), 'of', len(k[1]),
      '| round 2 and 3:', len(k[2] & k[3]),
      '| union by outlet+title:', len(k[1] | k[2] | k[3]))
txt300 = meta.text.astype(str).str.split().str.join(' ').str[:300]
print('Union by text (rounds 1-3):', txt300[meta['round'] <= 3].nunique())


# %% [markdown]
# ## Part 2: Section 5 Results (rounds 2-4, not in the validation set)
# AI coding from Combined_runs_2-4.xlsx, merged with publication date and
# outlet from Articles_coding_round_2-4.xlsx.

# %% Part 2a: check that the combined file equals the three run files
comb = load(COMBINED)
sep = pd.concat([load(RUN_FILES[r]) for r in (2, 3, 4)])
assert set(comb.article_id) == set(sep.article_id) and len(comb) == len(sep)
m = comb.merge(sep, on='article_id', suffixes=('_c', '_s'))
for col in ['ai_relevant', 'ai_date precision']:
    print(col, 'differences combined vs runs:', (m[col + '_c'].astype(str) != m[col + '_s'].astype(str)).sum())

# %% Part 2b: coverage, relevance and outlets
df = comb.merge(meta[['src', 'pub', 'title', 'text', 'round']], left_on='article_id',
                right_index=True, how='left')
assert df.pub.notna().all()
print('Articles:', len(df), '| by round:', df['round'].value_counts().sort_index().to_dict())
print('Published:', df.pub.min().date(), 'to', df.pub.max().date(), '| outlets:', df.src.nunique())
print('Relevance:', df.ai_relevant.value_counts().to_dict(),
      (100 * df.ai_relevant.value_counts(normalize=True)).round(1).to_dict())
yes = df[df.ai_relevant == 'yes']
print('Outlets with relevant articles:', yes.src.nunique())
print('Date precision, relevant articles:', yes['ai_date precision'].value_counts().to_dict())

# Duplicates: articles with the same outlet and title, and the number of unique texts
dkey = df.src + '|' + df.title.astype(str).str.strip().str.lower()
print('Duplicates (outlet+title):', dkey.duplicated().sum(),
      '| unique texts:', df.text.astype(str).str.split().str.join(' ').str[:300].nunique())

# %% Part 2c: temporal distribution
months = pd.period_range('2025-10', '2026-10', freq='M')
df['month'] = df.pub.dt.to_period('M')
monthly = (df.groupby('month')
             .agg(articles=('article_id', 'size'),
                  relevant=('ai_relevant', lambda s: (s == 'yes').sum()))
             .reindex(months, fill_value=0))
monthly['pct_relevant'] = (100 * monthly.relevant / monthly.articles.where(monthly.articles > 0)).round(1)
monthly.to_csv(os.path.join(OUT, 'monthly.csv'))
print(monthly.to_string())

# Time from opening to publication, for relevant articles dated to the day
day = yes[yes['ai_date precision'] == 'day'].copy()
day['opening'] = pd.to_datetime(day['ai_opening date'].astype(str).str[:10], errors='coerce')
lag = (day.pub - day.opening).dt.days
print('Lag (days): n =', lag.notna().sum(), '| median =', lag.median(),
      '| share within a week =', round(100 * (lag <= 7).mean(), 1), '%')
opening = pd.to_datetime(yes['ai_opening date'].astype(str).str[:10], errors='coerce')
print('Opening year of relevant articles:', opening.dt.year.value_counts().sort_index().to_dict())


# %% [markdown]
# ## Part 3: Grouping relevant articles into projects (Sections 5 and 6)
# The 96 articles coded ai_relevant = yes in runs 1-4 were read and grouped
# by hand into 44 projects. For each project the table gives a short name,
# municipality, county, the finest date precision in any of its articles,
# whether an official opening event (ceremony) is reported (coded by hand),
# and the article ids (A = round 1, B = 2, C = 3, D = 4).

# %% Part 3a: project list (hand coding)
PROJECTS = [
 # key, project, municipality, county, precision, ceremony, article ids
 ('Homborsund', 'Homborsund, by Eide school', 'Grimstad', 'Agder', 'day', 1, 'A0004 A0006 B0048 B0066 C0115'),
 ('Stod', 'Stod, Gusthaugen–Leinskorsen', 'Steinkjer', 'Trøndelag', 'day', 1, 'A0015 B0389'),
 ('Leland', 'Leland, Fv 17 Sankarveien–Slettveien', 'Leirfjord', 'Nordland', 'day', 1, 'C0192 C0195 C0199 C0236 C0255'),
 ('Sykkelstamvegen', 'Sykkelstamvegen, final stage', 'Stavanger/Sandnes', 'Rogaland', 'day', 1, 'C0286 C0290 C0311 C0314 C0316'),
 ('Hogas', 'Høgåsveien, Nøtterøy (temporary path)', 'Færder', 'Vestfold', 'month', 0, 'B0202 B0371'),
 ('Mortensrud', 'Lofsrudveien/Luhnvileveien, Mortensrud', 'Oslo', 'Oslo', 'year', 0, 'B0194'),
 ('Litlabo', 'Litlabøvegen towards E39', 'Stord', 'Vestland', 'year', 0, 'A0058'),
 ('Kvamskogen', 'Kvamskogen gravel path', 'Kvam', 'Vestland', 'none', 0, 'C0309'),
 ('Stjordal', 'Stjørdal valley path', 'Stjørdal', 'Trøndelag', 'none', 0, 'C0374'),
 ('OvreStorgate', 'Øvre Storgate–Landfalløya', 'Drammen', 'Buskerud', 'day', 1, 'D2160 D2044 D2144'),
 ('Tonsberg', 'Tønsberg station, Burmastien', 'Tønsberg', 'Vestfold', 'day', 0, 'D2055 D2155'),
 ('Hunsfosvegen', 'Hunsfosvegen', 'Vennesla', 'Agder', 'none', 0, 'D2039 D2139'),
 ('Findal', 'Gassveien, Findal–Surtebogen', 'Bamble', 'Telemark', 'day', 1, 'D1935 D1875 D1885 D1889'),
 ('AsHolstad', 'Ås centre–Holstad', 'Ås', 'Akershus', 'day', 1, 'D1958 D1719 D1616'),
 ('Sagdalen', 'Ruth Maiers gate, Sagdalen', 'Lillestrøm', 'Akershus', 'month', 0, 'D1925 D1916'),
 ('Larvik', 'Elveveien crossing, Yttersø', 'Larvik', 'Vestfold', 'month', 0, 'D1915'),
 ('Sunndal', 'Sunndalsøra, last 200 m', 'Sunndal', 'Møre og Romsdal', 'none', 0, 'D1881'),
 ('Stamnes', 'Stamnes arena, Prestmarkveien', 'Alstahaug', 'Nordland', 'year', 0, 'D1755 D1658'),
 ('Sandviken', 'Sandviken, Bradbenken–Sandvikstorget', 'Bergen', 'Vestland', 'day', 1, 'D1764 D1747'),
 ('HusebySmestad', 'Sørkedalsveien, Huseby–Smestad', 'Oslo', 'Oslo', 'none', 0, 'D1644 D1629'),
 ('Aksdal', 'Aksdal bridge over E134', 'Tysvær', 'Rogaland', 'day', 1, 'D1542 D1538 D1524'),
 ('Lovenskiold', 'Løvenskioldsgate', 'Oslo', 'Oslo', 'year', 0, 'D1551'),
 ('Industriveien', 'Industriveien', 'Sandefjord', 'Vestfold', 'year', 0, 'D1560'),
 ('Bodo', 'Rv 80, Thallekrysset–Snippen', 'Bodø', 'Nordland', 'day', 1, 'D3087 D3088 D3063'),
 ('Narvik', 'Fredskapellet underpass', 'Narvik', 'Nordland', 'month', 0, 'D3066 D3050'),
 ('Tjeldsund', 'E10 Tjeldsund bru–Steinsland', 'Tjeldsund', 'Troms', 'day', 1, 'D3037 D3042 D3015'),
 ('Rv94', 'Rv 94 Mollstrand–Grøtnes', 'Hammerfest', 'Finnmark', 'day', 1, 'D1437 D1407 D1193'),
 ('Vagendalen', 'Vågendalen, Alstenveien–Vågen', 'Alstahaug', 'Nordland', 'month', 0, 'D1423'),
 ('Stromme', 'Strømme roundabout, Høvågveien/Dvergsnesveien', 'Kristiansand', 'Agder', 'day', 1, 'D1430'),
 ('Gjelten', 'Gjelten bru', 'Alvdal', 'Innlandet', 'year', 0, 'D1166'),
 ('Stamsund', 'Fv 817 through Stamsund', 'Vestvågøy', 'Nordland', 'month', 0, 'D1141 D1092'),
 ('Strindvegen', 'Strindvegen, Lerkendal–Klæbuvegen', 'Trondheim', 'Trøndelag', 'day', 0, 'D1117'),
 ('Kittelsbukt', 'Kittelsbuktveien–Varmekrogen', 'Arendal', 'Agder', 'month', 0, 'D1040 D1047'),
 ('Tromso', 'Vestregata bike boxes', 'Tromsø', 'Troms', 'year', 0, 'D0983 D0960'),
 ('Kanebogen', 'Rv 83 Kanebogen–Margrethe Jørgensens vei', 'Harstad', 'Troms', 'month', 0, 'D0858 D0861 D0836'),
 ('Smithestrom', 'Smithestrøm park', 'Drammen', 'Buskerud', 'day', 1, 'D0677 D0650'),
 ('Bekkeli', 'Bekkeli–Saragammen', 'Hammerfest', 'Finnmark', 'year', 0, 'D2948'),
 ('Askoy', 'Lavik–Haugland', 'Askøy', 'Vestland', 'month', 1, 'D0279'),
 ('KrsRailway', 'Railway site, Havnegata', 'Kristiansand', 'Agder', 'month', 0, 'D2545'),
 ('Nonnestien', 'Nonnestien, Store Lungegårdsvann', 'Bergen', 'Vestland', 'day', 1, 'D2444'),
 ('Griniveien', 'Griniveien, Røakrysset–Bærum border', 'Oslo', 'Oslo', 'year', 0, 'D2293'),
 ('Froyland', 'Frøyland bru, Kvernelandsvegen', 'Time/Klepp', 'Rogaland', 'day', 1, 'D2273 D2274 D2267 D2218'),
 ('Oynosletto', 'Øynosletto trail', 'Sokndal', 'Rogaland', 'day', 1, 'D2276 D2262'),
 ('Torodveien', 'Torødveien', 'Færder', 'Vestfold', 'year', 0, 'D2233 D2236 D2205 D0064 D1261 D0043 D1240'),
]
proj = pd.DataFrame(PROJECTS, columns=['key', 'project', 'municipality', 'county',
                                       'date_precision', 'ceremony_reported', 'article_ids'])
proj.insert(0, 'project_id', [f'P{i:02d}' for i in range(1, len(proj) + 1)])
proj['ids'] = proj.article_ids.str.split()
all_ids = [i for ids in proj.ids for i in ids]
assert len(all_ids) == len(set(all_ids)) == 96
assert set(all_ids) <= set(meta.index)
proj['rounds'] = proj.ids.map(lambda ids: ','.join(sorted({str(meta.loc[i, 'round']) for i in ids})))
print('Projects:', len(proj), '| flagged articles:', len(all_ids))

# %% Part 3b: coverage per project (records, distinct stories, outlets)
def distinct_stories(ids):
    """Articles with the same text start or the same title count as one story."""
    groups = []
    for i in ids:
        a = meta.loc[i]
        k1 = re.sub(r'\W+', '', str(a.text).lower())[:150]
        k2 = re.sub(r'\W+', '', str(a.title).lower())[:40]
        for g in groups:
            if k1 in g or k2 in g:
                g.update([k1, k2])
                break
        else:
            groups.append({k1, k2})
    return len(groups)


proj['llm_flagged_articles'] = proj.ids.map(len)
proj['distinct_stories'] = proj.ids.map(distinct_stories)
proj['outlets'] = proj.ids.map(lambda ids: meta.loc[ids, 'src'].nunique())

# %% Part 3c: projects in rounds 2-4 only (Section 5)
ids24 = set(df.article_id)
p24 = proj[proj.ids.map(lambda ids: any(i in ids24 for i in ids))].copy()
p24['n24'] = p24.ids.map(lambda ids: sum(i in ids24 for i in ids))
print('Projects in rounds 2-4:', len(p24))                     # 43 (Litlabø is pilot only)
print('Articles per project:', p24.n24.value_counts().sort_index().to_dict())
print('Date precision:', p24.date_precision.value_counts().to_dict())
county = p24.county.value_counts()
print('Projects by county:', county.to_dict())
print('Counties with a project:', county.size, 'of 15 (none in Østfold)')

# %% Part 3d: coverage and attention (Section 6)
print('Ceremony reported:', proj.ceremony_reported.sum(), 'of', len(proj))
print(pd.crosstab(proj.ceremony_reported, proj.date_precision)[['day', 'month', 'year', 'none']])
print('Mean distinct stories by ceremony:',
      proj.groupby('ceremony_reported').distinct_stories.mean().round(1).to_dict())
print('Projects with more than one story:', (proj.distinct_stories > 1).sum())

# %% Part 3e: field-group keyword search (Table tab:inventory)
# Step 1: search the flagged articles for keywords for each field group.
# Step 2: read every match by hand. The final coding is given in FIELDS below.
KEYWORDS = {
 'physical_characteristics': r'\d[\d,.]*\s*(km|kilometer|meter)\b|\d[\d,]*\s*m\b(?!\s*kr)|meter (lang|bred)|bredde',
 'project_stage_dates': r'byggestart|første spadetak|startet (i|opp)|anleggsstart|påbegynt|skulle (vært|være|stå) (ferdig|klar)|planen var|ferdig til|åpnes? (i|til) |siden \d{4}|i \d{4}\b',
 'use_and_attention': r'møtte opp|frammøtte|fremmøtte|hundrevis|i hopetall|personene|snor|markering|markert|i bruk|brukes|tellinger|syklister i døgnet|tatt veien i bruk',
 'trigger_for_project': r'spleiselag|finansier|bompeng|byvekstavtale|bymiljøpakke|bypakke|harstadpakken|tildelt|rekkefølgekrav|dugnad|vann- og avløp|va-anlegg|vann og avløp|avløpsprosjekt|regulert inn sammen|jernbaneprosjekt|ops',
 'reasons_for_delay': r'forsink|utsatt|utsett|fristforleng|ikke ferdigstilt som planlagt|tok lengre tid|krevende vinter|budsjettsprekk|foran skjema|før planlagt',
 'concurrent_interventions': r'rundkjøring|bussholdeplass|busstopp|kollektivfelt|nytt fortau|bredere .{0,10}fortau|fortau|belysning|undergang|ny bro|ny bru|nye bru|parkering|kryss',
 'initiator_and_conflict': r'initiativ|velforening|vel\b|kjempet for|gjennomslag|ønske fra|ønsket av|foreldre|beboere|lokale krefter|engasjement|klage|klaget|krangel|strid|konflikt|søksmål|rettssak|anmeld|reagerer|kritik|sløseri|uenig|frustr|forvirring|ulovlig',
 'project_status': r'etappe|delstrekning|byggetrinn|del to|første del|neste del|resten av|gjenstår|midlertidig|bruksovertakelse|forleng|videreføring|delprosjekt|ikke helt ferdig|ikke helt i mål|til våren',
 'location_description': r'\b(fra|mellom) [A-ZÆØÅ][\w-]+.{0,40}\b(til|og) [A-ZÆØÅ]|langs [A-ZÆØÅ]|ved [A-ZÆØÅ]|gjennom [A-ZÆØÅ]',
 'cost': r'\d[\d,. ]*\s*(millioner|mill\.|milliard\w*)|kroner (per|meteren)|prislapp|kostnadsramme|budsjettramme|regning',
}
with open(os.path.join(OUT, 'keyword_matches.txt'), 'w', encoding='utf-8') as fh:
    for _, p in proj.iterrows():
        txt = ' '.join(f'{meta.loc[i, "title"]}. {meta.loc[i, "text"]}' for i in p.ids)
        fh.write(f'\n### {p.project_id} {p.project} ({p.municipality})\n')
        for fg, rx in KEYWORDS.items():
            mm = re.search(rx, txt if fg == 'location_description' else txt.lower())
            if mm:
                a = max(0, mm.start() - 60)
                fh.write(f'  {fg}: ...{txt[a:mm.end() + 60]}...\n'.replace('\n', ' ') + '\n')

# Final coding after reading every match (Mari, 9 November 2026)
S = lambda s: set(s.split())
FIELDS = {
 'physical_characteristics': S('Homborsund Stod Leland Sykkelstamvegen Hogas Hunsfosvegen Findal Sagdalen Sandviken Bodo Tjeldsund Rv94 Vagendalen Askoy Nonnestien Griniveien Froyland Oynosletto Torodveien'),
 'project_stage_dates': S('Homborsund Stod Leland Sykkelstamvegen Hogas Litlabo Tonsberg AsHolstad Larvik Sandviken Industriveien Rv94 Vagendalen Smithestrom Askoy Griniveien Oynosletto Stamsund Froyland'),
 'use_and_attention': S('Homborsund Stod Leland Sykkelstamvegen Kvamskogen OvreStorgate Findal AsHolstad Sagdalen Stamnes Sandviken Aksdal Bodo Tjeldsund Rv94 Vagendalen Stromme Smithestrom Nonnestien Froyland Oynosletto'),
 'trigger_for_project': S('Homborsund Kvamskogen Hogas Findal Sagdalen Tonsberg Industriveien Narvik Tjeldsund Vagendalen Stromme Kittelsbukt Griniveien Froyland Askoy'),
 'reasons_for_delay': S('Vagendalen Oynosletto Industriveien Strindvegen'),
 'concurrent_interventions': S('Homborsund Mortensrud OvreStorgate Tonsberg Hunsfosvegen Findal Stamnes Aksdal Narvik Tjeldsund Rv94 Vagendalen Stromme Gjelten Stamsund Strindvegen Tromso Kanebogen Smithestrom Askoy KrsRailway Griniveien Froyland'),
 'initiator_and_conflict': S('Hogas Litlabo Kvamskogen Sykkelstamvegen Stod Homborsund OvreStorgate Hunsfosvegen AsHolstad Sagdalen HusebySmestad Lovenskiold Narvik Vagendalen Gjelten Stamsund Smithestrom Askoy Torodveien'),
 'project_status': S('Sykkelstamvegen Homborsund Leland Stjordal Hunsfosvegen Findal AsHolstad Larvik Sandviken Aksdal Lovenskiold Industriveien Bodo Tjeldsund Rv94 Vagendalen Stromme Stamsund Strindvegen Kanebogen KrsRailway Nonnestien Froyland Torodveien'),
 'location_description': set(proj.key) - S('Kvamskogen Stjordal'),
 'cost': S('Homborsund Stod Sykkelstamvegen Kvamskogen Sagdalen Stamnes Sandviken Narvik Rv94 Vagendalen Stromme Kittelsbukt Kanebogen Askoy Froyland Oynosletto'),
}
assert all(v <= set(proj.key) for v in FIELDS.values())
for fg, keys in FIELDS.items():
    proj[fg] = proj.key.isin(keys).astype(int)
proj['metadata_and_coverage'] = (proj.distinct_stories > 1).astype(int)
inventory = proj[list(FIELDS) + ['metadata_and_coverage']].sum()
print('Table tab:inventory (projects per field group):\n', inventory.to_string())


# %% [markdown]
# ## Part 4: Export of the project coding (appendix)

# %% Part 4: write Excel file with projects, articles and variable definitions
cols = ['project_id', 'project', 'municipality', 'county', 'rounds', 'date_precision',
        'ceremony_reported', 'llm_flagged_articles', 'distinct_stories', 'outlets',
        'physical_characteristics', 'project_stage_dates', 'use_and_attention',
        'metadata_and_coverage', 'trigger_for_project', 'reasons_for_delay',
        'concurrent_interventions', 'initiator_and_conflict', 'project_status',
        'location_description', 'cost', 'article_ids']
articles = pd.DataFrame([{'project_id': p.project_id, 'project': p.project, 'article_id': i,
                          'round': meta.loc[i, 'round'], 'source': meta.loc[i, 'source'],
                          'published': str(meta.loc[i, 'published'])[:10],
                          'title': str(meta.loc[i, 'title']).strip()}
                         for _, p in proj.iterrows() for i in p.ids])
codebook = pd.DataFrame([
 ('project_id', 'Project identifier assigned in this analysis.'),
 ('project', 'Short description of the project (place and route).'),
 ('municipality', 'Municipality as given by the LLM or inferred from the articles.'),
 ('county', 'County (2024 county structure).'),
 ('rounds', 'Search rounds (1-4) in which the LLM-flagged articles appear.'),
 ('date_precision', 'Finest precision of the opening date in any flagged article: day, month, year or none.'),
 ('ceremony_reported', '1 if a flagged article reports an official opening event (ribbon-cutting, marking or official opening). Coded by hand.'),
 ('llm_flagged_articles', 'Number of articles the LLM coded as reporting the opening (ai_relevant = yes).'),
 ('distinct_stories', 'Flagged articles after merging duplicates (same text start or same title).'),
 ('outlets', 'Number of different newspapers among the flagged articles ("Pluss"/"Login" editions merged).'),
 ('physical_characteristics', '1 if length, width or other physical attributes of the path are reported.'),
 ('project_stage_dates', '1 if dates other than the opening are reported (need raised, construction start, planned vs actual opening).'),
 ('use_and_attention', '1 if attendance at the opening, officials present or use of the path is reported.'),
 ('metadata_and_coverage', '1 if the project is covered by more than one distinct story.'),
 ('trigger_for_project', '1 if the direct reason for building the path is reported. Financing schemes alone are not counted.'),
 ('reasons_for_delay', '1 if the article explains why the project was delayed or completed at a different time than planned.'),
 ('concurrent_interventions', '1 if other measures built at the same time are reported (roundabouts, bus stops, pavements, lighting, road works).'),
 ('initiator_and_conflict', '1 if the article names who initiated the project, or reports conflict, complaints or disputes about it.'),
 ('project_status', '1 if the article reports status beyond "opened": partial opening, remaining works, temporary solution or early handover.'),
 ('location_description', '1 if the route is described precisely enough (endpoints, road name, landmarks) to support matching to OSM/NVDB.'),
 ('cost', '1 if the cost or budget of the project is reported (not in Table 1 of the paper).'),
 ('article_ids', 'Article identifiers of the flagged articles (A = round 1, B = round 2, C = round 3, D = round 4).'),
], columns=['variable', 'description'])

with pd.ExcelWriter(os.path.join(OUT, 'coding_further_uses_of_articles.xlsx'), engine='openpyxl') as w:
    proj[cols].to_excel(w, sheet_name='projects', index=False)
    articles.to_excel(w, sheet_name='articles', index=False)
    codebook.to_excel(w, sheet_name='codebook', index=False)
proj[cols].to_csv(os.path.join(OUT, 'project_data.csv'), index=False, encoding='utf-8-sig')


# %% [markdown]
# ## Part 5: Figures (optional, since the current draft of Section 5 uses a table)

# %% Part 5: monthly coverage and relevance, projects by county
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
    print('matplotlib not installed: figures skipped')

if plt is not None:
    BLUE, INK, INK2, GRID = '#2a78d6', '#0b0b0b', '#52514e', '#e4e3df'
    plt.rcParams.update({'font.family': 'serif', 'font.size': 9, 'axes.edgecolor': INK2,
                         'axes.labelcolor': INK2, 'xtick.color': INK2, 'ytick.color': INK2,
                         'axes.spines.top': False, 'axes.spines.right': False})
    x = list(range(len(months)))
    labels = [p.strftime('%b\n%Y') if p.month in (10, 1) else p.strftime('%b') for p in months]

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.3, 4.2), sharex=True, gridspec_kw={'hspace': 0.35})
    a1.bar(x, monthly.articles, width=0.62, color=BLUE)
    a2.bar(x, monthly.pct_relevant.fillna(0), width=0.62, color=BLUE)
    a1.set_title('(a) Articles coded by the LLM', loc='left', color=INK)
    a2.set_title('(b) Share coded as reporting an opening (%)', loc='left', color=INK)
    a1.set_ylim(0, 480); a2.set_ylim(0, 7.5)
    for xi, (n, pct) in enumerate(zip(monthly.articles, monthly.pct_relevant)):
        if n:
            a1.text(xi, n + 8, str(n), ha='center', fontsize=7, color=INK2)
            a2.text(xi, pct + 0.15, f'{pct:.1f}', ha='center', fontsize=7, color=INK2)
        else:
            for ax, top in ((a1, 480), (a2, 7.5)):
                ax.text(xi, top * 0.06, 'no\ndata', ha='center', fontsize=7, color=INK2, style='italic')
    for ax in (a1, a2):
        ax.yaxis.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True); ax.tick_params(length=0)
    a2.set_xticks(x); a2.set_xticklabels(labels)
    fig.savefig(os.path.join(OUT, 'fig_results_monthly.pdf'), bbox_inches='tight')

    cs = county.reindex(county.index.tolist() + ['Østfold'], fill_value=0).sort_values()
    fig, ax = plt.subplots(figsize=(6.3, 3.2))
    ax.barh(range(len(cs)), cs.values, height=0.62, color=BLUE)
    ax.set_yticks(range(len(cs))); ax.set_yticklabels(cs.index)
    for yi, v in enumerate(cs.values):
        ax.text(v + 0.1, yi, str(v), va='center', fontsize=7, color=INK2)
    ax.set_xlabel('Projects'); ax.set_xlim(0, 8)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6); ax.set_axisbelow(True); ax.tick_params(length=0)
    fig.savefig(os.path.join(OUT, 'fig_results_county.pdf'), bbox_inches='tight')

print('\nDone. Outputs in', OUT)
