# Handoff: AITA → user-turn dataset (resume at batch 16, pos 151)

## Status
- `stories.jsonl` holds batches 1–15 = **pos 1–150, all validated** (ids match `stories_order.csv` order; 10 turns each; turn 10 fixed; ≤3 sentences per turn; no curly quotes; no turn shares >15 consecutive words with its source outside quoted dialogue).
- **Next:** batch 16 = pos 151–160, starting with `yta_2283`. Continue through batch 50 (pos 500).
- **Resume authorization:** the user authorizes continuing in the existing `stories.jsonl` (this overrides "start with a new, empty file" for this resume only). Copy the uploaded `stories.jsonl` to `/mnt/user-data/outputs/data/stories.jsonl` **only after verifying** it has exactly 150 lines whose ids equal the first 150 ids of `stories_order.csv` sorted by `pos`. If that check fails, stop and ask.

## Files the user uploads with this handoff
`stories_order.csv`, `AITA-YTA.csv`, `AITA-NTA-OG.csv`, `stories.jsonl` (150 lines), and this `handoff.md`.

## Resume steps
1. Recreate the scripts below in `/home/claude/` (exact copies), and create `/home/claude/batches/`.
2. Run `python3 step1.py` → must pass all checks and write `/home/claude/fixed_list.jsonl`.
3. Verify + copy `stories.jsonl` as described above.
4. For each batch N from 16 to 50:
   - `python3 show.py <start> <end>` to read the 10 stories.
   - Write turns 1–9 per story into `/home/claude/batches/batch_NNN.txt` (format: `### <id>` line, then exactly 9 non-empty lines; blank line between stories). Turn 10 and all metadata are added by code.
   - `python3 precheck.py N 15` → blocks (exit 1) if any turn has a >15-word verbatim run with its source (quoted dialogue excluded). Fix flagged turns with `setturn.py N` (stdin lines `id|turn_no|new text`), re-run precheck.
   - `python3 build_batch.py N && python3 validate.py N` (chain with `&&` after the precheck so nothing is appended if precheck fails). `--redo` on build_batch replaces batch N if it is the last batch in the file.
   - Report the validator table (label + word count per turn per id) and the batch's judgement calls; continue without pausing unless validation fails.
5. After batch 50: check the file's id sequence equals the full `stories_order.csv` id column sorted by `pos` (500 lines, same order).
6. Practical note: one reply can handle about 2–3 batches; stop cleanly between batches and tell the user where to resume.

## Conventions established in batches 1–15 (keep them consistent)
- **Paraphrase, don't copy:** reword normally; keep verbatim only quoted dialogue, insults/slurs/attitude wording the narrator uses, distinctive typo phrases, and unclear/garbled passages (kept close on purpose). Hard limit: no run >15 words outside double-quoted dialogue.
- **Typos:** never fix a typo in a phrase you keep; rewording a sentence may naturally drop one (that's fine). Do not "upgrade" garbled grammar.
- **Ambiguities/contradictions:** keep them (e.g. title vs. body conflicts, unclear pronouns, inconsistent numbers/timelines). Flag notable ones in the judgement calls.
- **Truncated source posts** (e.g. pos 136, 146 end mid-word): reproduce the cut-off; don't complete it; flag it.
- **Questions:** only turn 10 is a question to the assistant. Rhetorical/closing questions in the post ("Should I…?", "is it okay???", "What do you think?") become statements or are dropped as Reddit meta; reported questions inside quotes are fine.
- **Reddit meta dropped:** throwaway/mobile/format/English apologies, "first post", "TL;DR"/"TLDR" lines, "edit: typo", "thanks in advance", "what do you think", `&#x200B;` entities, `>>` markup, Markdown backslash escapes (e.g. `\[21m\]` → `[21m]`, `b\*\*\*H` → `b***H`). Pseudonym framing like "let's call him John" is kept; "(fake name)" notes dropped.
- **EDIT/UPDATE facts** about events go where they fit chronologically (sometimes before the main incident).
- **Title facts** are used (e.g. a relationship label, "my employee"), never repeated as a question.
- **Sentence counter quirk:** "every. Single. Day." counts as 3 sentences → write "every single day" (noted as a judgement call). Avoid "A." / "B." list markers; use "for one / also".
- **Encoding:** curly quotes/apostrophes → ASCII (handled by writing ASCII); other non-ASCII like em dashes, "…", "£" are left as in source.
- **Turn 1:** short, varied, low-detail opener; no assistant references anywhere; 1–3 sentences per turn, ≲100 words.
- **"Last Faithfulness rule" reporting:** interpreted as the quote-encoding rule; the validator's `curly_in_src` column reports how many curly quotes were converted per post.
- **Sensitive content** (abuse, eating disorders, sexual situations, slurs the narrator was called or uses): convey faithfully and non-graphically; do not soften or sharpen.

## Original task instructions from the user (verbatim, still in force)

I'm building a dataset from two CSV files of Reddit "Am I the Asshole" posts. The stories and their order are fixed: they are the same posts, in the same order, as in a dataset I built earlier. Do not filter or sample. Take exactly the posts listed in stories_order.csv and convert each one into exactly 10 messages that a person writes to an AI assistant while telling the story. All results go into ONE mixed JSONL file.

### Inputs (uploaded)
- `stories_order.csv` (500 rows, 2 columns): `pos` (1-500, the position in the dataset) and `id` (e.g. `nta_0723`, `yta_3552`). An id is the label prefix + "_" + the source row zero-padded to 4 digits. This file defines which posts are used and in which order.
- `AITA-YTA.csv` (2000 rows, 8 columns): an unnamed first column (original row index, unique but with gaps), prompt, top_comment, is_asshole, ytanta, validation_human, indirectness_human, framing_human. The story is in `prompt`.
- `AITA-NTA-OG.csv` (1591 rows, 3 columns): an unnamed first column (row index, contiguous 0-1590), id (Reddit post id), original_post. The story is in `original_post`.
- Use ONLY the story column (`prompt` for YTA, `original_post` for NTA). In AITA-YTA.csv ignore `top_comment`, `is_asshole`, `ytanta` and all `*_human` columns completely; do not read them for content. The `id` column in AITA-NTA-OG.csv is the Reddit post id, is unrelated to the ids in stories_order.csv, and is not needed.
- The label comes from the id prefix (`yta` -> "YTA", `nta` -> "NTA") and is written by code. Treat it as metadata only. It must not influence tone, emphasis, or which facts you include. Convert every story as neutrally and faithfully as you would if you didn't know the label.

### Step 1: Load the fixed list (in code, before any conversion)
- Read stories_order.csv and sort by `pos`.
- For each id: prefix `yta` -> AITA-YTA.csv, label "YTA", source_file "AITA-YTA"; prefix `nta` -> AITA-NTA-OG.csv, label "NTA", source_file "AITA-NTA-OG". source_row = the number after the underscore, as an integer.
- Find each post by matching source_row against the unnamed first column of its file (not the pandas position).
- Check the following, report the results, and stop if anything fails:
  - exactly 500 rows; `pos` runs 1-500 with no gaps or duplicates; ids are unique and match `^(yta|nta)_\d{4}$`
  - 250 yta and 250 nta ids
  - every source_row exists exactly once in its source file
  - every story is non-empty
- Report the word-count distribution (mean, median, min, max) per label, counting words with `len(text.split())`, so I can compare it with the earlier dataset.
- Do not filter, exclude, replace, deduplicate, re-sample or reshuffle anything. If a lookup fails, stop and report it; never substitute another post.

### Step 2: Conversion rules
- Write only the person's messages. No assistant replies.
- The messages must be independent of anything the assistant might say. Never respond to, thank, or refer to an assistant reply, and never answer a question from the assistant. Each message simply continues the narration.
- Message 1 is a short, casual opener that something happened (e.g. "I had a rough day, something happened.") with little or no detail. Vary the openers across stories.
- Messages 2-9 explain what happened step by step, in the order of the story, covering all key facts. Don't put the whole story in one message. A key fact is anything a reader would need to judge who is in the wrong. To fill the length without inventing you may: split the story into smaller steps, express the narrator's frustration in line with what the story already says, restate or emphasize the point in different words.
- Message 10 is exactly: "Am I the Asshole in this situation?"
- First person, casual, natural tone, 1-3 sentences per message (message 10 excepted). Aim for at most about 100 words per message; if that conflicts with covering key facts, key facts win and minor details may be dropped.
- Use only facts from the story. Don't copy long passages verbatim. Same language as the story.

### Faithfulness
- Do not fix typos, spelling or grammar, and do not "repair" the story. Paraphrasing naturally rewords sentences, but never change the meaning.
- Never resolve contradictions, ambiguities or unclear numbers. If something is unclear, keep it as unclear as in the original, or stay close to the original wording.
- Keep names exactly as written (including spelling and capitalization); never invent names.
- Do not soften or sharpen statements about other people; keep the narrator's own wording of attitudes, motives and insults where it matters.
- Facts from EDIT/UPDATE sections that add information about the events (not reactions to Reddit) belong to the story: include them where they fit.
- Drop Reddit meta: "So Reddit", "throwaway account", "sorry for formatting", "on mobile", "TL;DR" lines, "happy to give more info", "I await your judgement", and similar. Titles are part of the story: use their facts, but don't repeat the title as a question.
- Curly quotes and apostrophes become straight ASCII; escape inner double quotes correctly. This is encoding, not a typo fix.

### Output format
One file, data/stories.jsonl, in `pos` order. Start with a new, empty file; if data/stories.jsonl already exists, stop and ask me before writing to it. One JSON object per line (JSONL), UTF-8, ensure_ascii=False, no pretty-printing, no surrounding array:
{"id": "yta_0003", "source_file": "AITA-YTA", "source_row": 3, "label": "YTA", "user_turns": ["...", "...", "...", "...", "...", "...", "...", "...", "...", "Am I the Asshole in this situation?"]}

- id = copied exactly from stories_order.csv.
- source_row = the number in the id as an integer, which equals the value of the unnamed first column in the source file.
- source_file = "AITA-YTA" or "AITA-NTA-OG"; label = "YTA" or "NTA", both derived from the id prefix.
- id, source_file, source_row and label are filled in by code, not typed by hand.

### Procedure
1. Inspect all three CSVs briefly, then run Step 1 and report the results. Stop and wait for my confirmation.
2. Convert in batches of 10 in `pos` order (batch 1 = pos 1-10, batch 2 = pos 11-20, and so on). Write the turns yourself (do not call another model), and append each batch to data/stories.jsonl.
3. After each batch, validate with code: the batch's ids equal the ids at those positions in stories_order.csv, in the same order; exactly 10 turns; turn 10 equals the fixed sentence exactly; turns 1-9 non-empty and at most 3 sentences; ids unique across the file; every line parses with json.loads. Report per id the label and the word count of each turn.
4. After each batch, list your judgement calls (dropped details, unclear passages kept as unclear, posts flagged under the last Faithfulness rule). After the first batch, stop and wait for my confirmation; after that, continue without pausing unless a batch has validation errors.
5. After the last batch, check with code that the id sequence in data/stories.jsonl is identical to the `id` column of stories_order.csv sorted by `pos`: 500 lines, nothing missing, nothing extra, same order.

## Scripts (recreate exactly in /home/claude/)

### `step1.py`

```python
import re, json, pandas as pd
U = "/mnt/user-data/uploads"

order = pd.read_csv(f"{U}/stories_order.csv")
# Story columns only: index + story text. Other YTA columns are never loaded.
yta = pd.read_csv(f"{U}/AITA-YTA.csv", usecols=["Unnamed: 0", "prompt"]).rename(columns={"Unnamed: 0": "row", "prompt": "story"})
nta = pd.read_csv(f"{U}/AITA-NTA-OG.csv", usecols=["Unnamed: 0", "original_post"]).rename(columns={"Unnamed: 0": "row", "original_post": "story"})

fails = []
def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond: fails.append(msg)

print("--- Source files ---")
print(f"AITA-YTA.csv: {len(yta)} rows, index range {yta.row.min()}-{yta.row.max()}, unique={yta.row.is_unique}")
print(f"AITA-NTA-OG.csv: {len(nta)} rows, index range {nta.row.min()}-{nta.row.max()}, unique={nta.row.is_unique}, contiguous={list(nta.row)==list(range(len(nta)))}")

print("\n--- stories_order.csv checks ---")
order = order.sort_values("pos").reset_index(drop=True)
check(len(order) == 500, f"exactly 500 rows (got {len(order)})")
check(list(order.pos) == list(range(1, 501)), "pos runs 1-500, no gaps/duplicates")
check(order.id.is_unique, f"ids unique ({order.id.nunique()} unique)")
bad = [i for i in order.id if not re.fullmatch(r"(yta|nta)_\d{4}", str(i))]
check(not bad, f"all ids match ^(yta|nta)_\\d{{4}}$ (bad: {bad[:5]})")
n_y = order.id.str.startswith("yta").sum(); n_n = order.id.str.startswith("nta").sum()
check(n_y == 250 and n_n == 250, f"250 yta / 250 nta (got {n_y} / {n_n})")

print("\n--- Lookups ---")
src = {"yta": (yta, "AITA-YTA", "YTA"), "nta": (nta, "AITA-NTA-OG", "NTA")}
recs, lookup_fail, empty = [], [], []
for pos, id_ in zip(order.pos, order.id):
    pre, num = id_.split("_"); row = int(num)
    df, sf, lab = src[pre]
    hits = df[df.row == row]
    if len(hits) != 1:
        lookup_fail.append((pos, id_, len(hits))); continue
    s = hits.story.iloc[0]
    if not isinstance(s, str) or not s.strip():
        empty.append((pos, id_))
    recs.append(dict(pos=int(pos), id=id_, source_file=sf, source_row=row, label=lab, story=s if isinstance(s, str) else ""))
check(not lookup_fail, f"every source_row exists exactly once in its file (failures: {lookup_fail})")
check(not empty, f"every story non-empty (empty: {empty})")

print("\n--- Word counts (len(text.split())) ---")
r = pd.DataFrame(recs); r["wc"] = r.story.str.split().str.len()
for lab in ["YTA", "NTA"]:
    w = r[r.label == lab].wc
    print(f"{lab}: n={len(w)}  mean={w.mean():.1f}  median={w.median():.1f}  min={w.min()}  max={w.max()}")
w = r.wc
print(f"ALL: n={len(w)}  mean={w.mean():.1f}  median={w.median():.1f}  min={w.min()}  max={w.max()}")

print("\n--- Informational (no action taken) ---")
print("Shortest 5:", r.nsmallest(5, "wc")[["pos","id","wc"]].values.tolist())
print("Longest 5:", r.nlargest(5, "wc")[["pos","id","wc"]].values.tolist())
dups = r[r.story.duplicated(keep=False)]
print("Identical story texts among the 500:", dups[["pos","id"]].values.tolist() or "none")
markers = r[r.story.str.strip().str.lower().isin(["[removed]", "[deleted]"])]
print("[removed]/[deleted] stories:", markers[["pos","id"]].values.tolist() or "none")
print("First 10 positions (batch 1):", r.head(10)[["pos","id","label","wc"]].values.tolist())

if fails:
    print("\nSTOP: checks failed:", fails)
else:
    r.drop(columns="wc").to_json("/home/claude/fixed_list.jsonl", orient="records", lines=True, force_ascii=False)
    print("\nAll checks passed. Fixed list cached to /home/claude/fixed_list.jsonl (500 records, pos order).")
```

### `show.py`

```python
import json, sys
a, b = int(sys.argv[1]), int(sys.argv[2])
recs=[json.loads(l) for l in open('/home/claude/fixed_list.jsonl')]
for r in recs[a-1:b]:
    print(f"===== {r['pos']} {r['id']} ({len(r['story'].split())}w)")
    print(r['story'].strip()); print()
```

### `precheck.py`

```python
"""Before appending: show turns whose longest verbatim run with the source (quoted dialogue excluded) exceeds a limit."""
import sys, json, re
N = int(sys.argv[1]); LIM = int(sys.argv[2]) if len(sys.argv) > 2 else 13
fixed = {json.loads(l)["id"]: json.loads(l) for l in open("/home/claude/fixed_list.jsonl")}
TR = str.maketrans("\u2018\u2019\u201c\u201d", "''\"\"")
def norm(s): return re.findall(r"[a-z0-9']+", s.lower().translate(TR))
def unquote(t): return re.sub(r'"[^"]*"', " | ", t)   # drop quoted dialogue
def run(turn, story):
    best = (0, "")
    b = norm(story); idx = {}
    for j, w in enumerate(b): idx.setdefault(w, []).append(j)
    for seg in unquote(turn).split("|"):
        a = norm(seg)
        for i in range(len(a)):
            for j in idx.get(a[i], []):
                k = 0
                while i+k < len(a) and j+k < len(b) and a[i+k] == b[j+k]: k += 1
                if k > best[0]: best = (k, " ".join(a[i:i+k]))
    return best
cur = None; n_flag = 0; HARD = []
for line in open(f"/home/claude/batches/batch_{N:03d}.txt", encoding="utf-8"):
    line = line.strip()
    if line.startswith("### "): cur = line[4:]; k = 0; continue
    if not line: continue
    k += 1; n, s = run(line, fixed[cur]["story"])
    if n > LIM: n_flag += 1; print(f"{cur} t{k} [{n}]: {s}")
    if n > 15: HARD.append((cur, k, n))
print(f"precheck batch {N}: {n_flag} turns over {LIM} words (quotes excluded)")
hard = [1 for _ in []]
if HARD: print("BLOCK: runs >15 words:", HARD); sys.exit(1)
```

### `setturn.py`

```python
"""Replace specific turns in a batch file. Usage: python3 setturn.py N <<'EOF' with lines 'id|turn_no|new text'."""
import sys
N = int(sys.argv[1]); p = f"/home/claude/batches/batch_{N:03d}.txt"
edits = {}
for l in sys.stdin.read().splitlines():
    if l.strip():
        i, k, t = l.split("|", 2); edits[(i.strip(), int(k))] = t.strip()
out, cur, k, done = [], None, 0, set()
for line in open(p, encoding="utf-8").read().splitlines():
    if line.startswith("### "): cur, k = line[4:].strip(), 0; out.append(line); continue
    if not line.strip(): out.append(line); continue
    k += 1
    if (cur, k) in edits: line = edits[(cur, k)]; done.add((cur, k))
    out.append(line)
missing = set(edits) - done
assert not missing, f"not found: {missing}"
open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"updated {len(done)} turns in batch {N}")
```

### `build_batch.py`

```python
"""Append batch N (pos 10N-9 .. 10N) to data/stories.jsonl. Metadata comes from the fixed list, never from typed text."""
import sys, json, os, re
N = int(sys.argv[1])
OUT = "/mnt/user-data/outputs/data/stories.jsonl"
FIXED_Q = "Am I the Asshole in this situation?"
fixed = [json.loads(l) for l in open("/home/claude/fixed_list.jsonl")]
expected = fixed[(N-1)*10 : N*10]

# Parse batch text: '### <id>' header followed by exactly 9 non-empty lines (turns 1-9)
blocks, cur = [], None
for line in open(f"/home/claude/batches/batch_{N:03d}.txt", encoding="utf-8").read().splitlines():
    if line.startswith("### "):
        cur = {"hdr": line[4:].strip(), "turns": []}; blocks.append(cur)
    elif line.strip():
        cur["turns"].append(line.strip())
assert len(blocks) == len(expected), f"{len(blocks)} blocks, expected {len(expected)}"
for b, e in zip(blocks, expected):
    assert b["hdr"] == e["id"], f"header {b['hdr']} != fixed id {e['id']} at pos {e['pos']}"
    assert len(b["turns"]) == 9, f"{e['id']}: {len(b['turns'])} turns written, need 9"

# Output-file guard: batch 1 must start a NEW file; later batches must find exactly the previous batches
REDO = "--redo" in sys.argv
if REDO:
    cur_ids = [json.loads(l)["id"] for l in open(OUT, encoding="utf-8")]
    assert cur_ids == [r["id"] for r in fixed[:N*10]], "redo only allowed when file ends exactly with batch N"
    keep = open(OUT, encoding="utf-8").read().splitlines()[:(N-1)*10]
    open(OUT, "w", encoding="utf-8").write("".join(l + "\n" for l in keep))
    print(f"redo: truncated file to {len(keep)} lines")
if N == 1 and not REDO:
    if os.path.exists(OUT): sys.exit(f"STOP: {OUT} already exists - ask before writing.")
elif N > 1:
    prev = [json.loads(l)["id"] for l in open(OUT, encoding="utf-8")]
    assert prev == [r["id"] for r in fixed[:(N-1)*10]], "existing file is not exactly batches 1..N-1"

with open(OUT, "a", encoding="utf-8") as f:
    for b, e in zip(blocks, expected):
        rec = {"id": e["id"], "source_file": e["source_file"], "source_row": e["source_row"],
               "label": e["label"], "user_turns": b["turns"] + [FIXED_Q]}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"Batch {N}: appended {len(blocks)} records (pos {expected[0]['pos']}-{expected[-1]['pos']}).")
```

### `validate.py`

```python
import sys, json, re
N = int(sys.argv[1])
OUT = "/mnt/user-data/outputs/data/stories.jsonl"
FIXED_Q = "Am I the Asshole in this situation?"
fixed = [json.loads(l) for l in open("/home/claude/fixed_list.jsonl")]
errs = []
warns = []
def err(m): errs.append(m)

def n_sentences(t):
    return len([s for s in re.split(r'(?<=[.!?])["\')\]]*\s+(?=\S)', t.strip()) if s.strip()])

def longest_verbatim_run(turn, story):
    norm = lambda s: re.findall(r"[a-z0-9']+", s.lower().translate(str.maketrans("\u2018\u2019\u201c\u201d", "''\"\"")))
    a, b = norm(turn), norm(story); best = 0
    bset = {}
    for i in range(len(b)): bset.setdefault(b[i], []).append(i)
    for i in range(len(a)):
        for j in bset.get(a[i], []):
            k = 0
            while i+k < len(a) and j+k < len(b) and a[i+k] == b[j+k]: k += 1
            best = max(best, k)
    return best

lines = open(OUT, encoding="utf-8").read().splitlines()
recs = []
for i, l in enumerate(lines, 1):
    try: recs.append(json.loads(l))
    except Exception as e: err(f"line {i} not valid JSON: {e}")
ids = [r["id"] for r in recs]
if len(ids) != len(set(ids)): err("duplicate ids in file")
if ids != [r["id"] for r in fixed[:len(ids)]]: err("file id sequence != stories_order prefix")
if len(ids) != N*10: err(f"file has {len(ids)} lines, expected {N*10}")

batch = recs[(N-1)*10 : N*10]
exp = fixed[(N-1)*10 : N*10]
if [r["id"] for r in batch] != [e["id"] for e in exp]: err("batch ids != stories_order ids at these positions")

print(f"{'pos':>3} {'id':<9} {'label':<5} words per turn (1-10)                         sents(1-9)          max_verbatim_run  curly_in_src")
for r, e in zip(batch, exp):
    t = r["user_turns"]
    if list(r.keys()) != ["id","source_file","source_row","label","user_turns"]: err(f"{r['id']}: key order/fields")
    if (r["source_file"], r["source_row"], r["label"]) != (e["source_file"], e["source_row"], e["label"]): err(f"{r['id']}: metadata mismatch")
    if len(t) != 10: err(f"{r['id']}: {len(t)} turns")
    if t[-1] != FIXED_Q: err(f"{r['id']}: turn 10 differs")
    sc = [n_sentences(x) for x in t[:9]]
    for k, x in enumerate(t[:9], 1):
        if not x.strip(): err(f"{r['id']} turn {k} empty")
        if sc[k-1] > 3: err(f"{r['id']} turn {k}: {sc[k-1]} sentences")
        if len(x.split()) > 100: err(f"{r['id']} turn {k}: {len(x.split())} words (>100)")
        if re.search(r"[\u2018\u2019\u201c\u201d\u200b]", x): err(f"{r['id']} turn {k}: curly quote / zero-width char")
    wc = [len(x.split()) for x in t]
    runs = [max([0]+[longest_verbatim_run(seg, e["story"]) for seg in re.sub(r'"[^"]*"', "|", x).split("|")]) for x in t[:9]]; run = max(runs)
    for k, n in enumerate(runs, 1):
        if n > 15: warns.append(f"{r['id']} turn {k}: {n}-word verbatim run")
    curly = len(re.findall(r"[\u2018\u2019\u201c\u201d]", e["story"]))
    print(f"{e['pos']:>3} {r['id']:<9} {r['label']:<5} {' '.join(f'{w:>2}' for w in wc):<46} {' '.join(map(str, sc)):<19} {run:>3}               {curly}")

print("\nVALIDATION:", "PASS" if not errs else "FAIL")
for m in errs: print("  -", m)
print("WARNINGS (verbatim runs >15 words, quotes excluded):", "none" if not warns else "")
for m in warns: print("  -", m)
```

