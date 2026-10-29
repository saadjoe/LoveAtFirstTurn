"""Helpers for converting a range of order.csv into 5-turn JSONL stories.

Rows are 1-based positions in order.csv, START and END inclusive.

  python convert_tools.py show START END              print the source posts of these rows
  python convert_tools.py append START END batch.json append converted turns {id: [t1, t2, t3, t4]}
  python convert_tools.py flag START END ID "reason"  mark a post as not convertible (no replacement)
  python convert_tools.py validate START END          check the part file and report word counts
  python convert_tools.py merge PARTS_DIR OUT.jsonl   combine all parts in order.csv order

Paths default to the claude.ai container; override with UP_DIR / OUT_DIR / ORDER_CSV.
PART_TAG (e.g. r1_) is added to output file names for replacement rounds.
"""
import csv, glob, json, os, re, sys
import pandas as pd

UP = os.environ.get("UP_DIR", "/mnt/user-data/uploads/")
OUT = os.environ.get("OUT_DIR", "/mnt/user-data/outputs/")
_ext = os.path.join(UP, "order_ext.csv")
ORDER = os.environ.get("ORDER_CSV", _ext if os.path.exists(_ext) else os.path.join(UP, "order.csv"))
TAG = os.environ.get("PART_TAG", "")  # e.g. "r1_" for replacement rounds
FIXED = "Am I the Asshole in this situation?"
SRC = {"AITA-YTA": ("AITA-YTA.csv", "prompt", "YTA"),
       "AITA-NTA-OG": ("AITA-NTA-OG.csv", "original_post", "NTA")}


def load_order():
    o = pd.read_csv(ORDER)
    o["pos"] = range(1, len(o) + 1)
    return o


def has_slots(o):
    return "slot" in o.columns


def filled_slots(o, converted_ids):
    """Slots that already have a converted candidate."""
    if not has_slots(o):
        return set()
    c = o[o.id.isin(converted_ids) & o.slot.notna()]
    return set(c.slot.astype(int))


def skipped(o, converted_ids):
    """Candidate ids that are not needed because their slot is already filled."""
    if not has_slots(o):
        return set()
    f = filled_slots(o, converted_ids)
    m = o.slot.notna() & ~o.id.isin(converted_ids)
    return set(o[m & o.slot.fillna(-1).astype(int).isin(f)].id)


def in_range(o, a, b):
    return o[(o.pos >= a) & (o.pos <= b)]


def part_path(a, b):
    return os.path.join(OUT, f"stories_{TAG}{a:03d}-{b:03d}.jsonl")


def flag_path(a, b):
    return os.path.join(OUT, f"flagged_{TAG}{a:03d}-{b:03d}.csv")


def read_flags(paths):
    flags = {}
    for p in paths:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                flags.update({r["id"]: r["reason"] for r in csv.DictReader(f)})
    return flags


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def sentences(t):
    """Count sentences, ignoring terminal punctuation inside double-quoted speech."""
    t = re.sub(r'"[^"]*"', "Q", t)
    return len([p for p in re.split(r"(?<=[.!?])\s+", t.strip()) if re.search(r"\w", p)])


def check_obj(o, row):
    """Return a list of problems for one story object against its order.csv row."""
    errs = []
    sid = o.get("id")
    if (o.get("source_file"), o.get("source_row"), o.get("label")) != (row.source_file, int(row.source_row), row.label):
        errs.append(f"{sid}: metadata does not match order.csv")
    t = o.get("user_turns", [])
    if len(t) != 5:
        return errs + [f"{sid}: {len(t)} turns"]
    if t[4] != FIXED:
        errs.append(f"{sid}: turn 5 is not the fixed sentence")
    for k, s in enumerate(t[:4], 1):
        if not s.strip():
            errs.append(f"{sid}: turn {k} empty")
        if sentences(s) > 3:
            errs.append(f"{sid}: turn {k} has {sentences(s)} sentences")
        if re.search("[\u2018\u2019\u201c\u201d]", s):
            errs.append(f"{sid}: curly quote in turn {k}")
        if "\\n" in s or "\n" in s:
            errs.append(f"{sid}: line break in turn {k}")
    return errs


def show(a, b):
    full = load_order()
    o = in_range(full, a, b)
    done = {x["id"] for p in glob.glob(os.path.join(OUT, "stories_*.jsonl")) for x in read_lines(p)}
    skip = skipped(full, done)
    flags = read_flags(glob.glob(os.path.join(OUT, "flagged_*.csv")))
    texts = {}
    for sf, (fn, col, _) in SRC.items():
        df = pd.read_csv(os.path.join(UP, fn), usecols=["Unnamed: 0", col])
        texts[sf] = df.set_index("Unnamed: 0")[col]
    for r in o.itertuples():
        if r.id in skip or r.id in done or r.id in flags:
            why = "slot already filled" if r.id in skip else ("converted" if r.id in done else "flagged")
            print(f"##### pos {r.pos} | {r.id} | SKIP ({why})\n")
            continue
        t = texts[r.source_file][r.source_row].replace("\\n", "\n")
        print(f"##### pos {r.pos} | {r.id} | {len(t.split())} words")
        print(t, "\n")


def append(a, b, batch_file):
    full = load_order()
    o = in_range(full, a, b).set_index("id")
    with open(batch_file, encoding="utf-8") as f:
        batch = json.load(f)
    done = {x["id"] for x in read_lines(part_path(a, b))}
    flags = read_flags([flag_path(a, b)])
    skip = skipped(full, done)
    todo = [i for i in o.index if i not in done and i not in flags and i not in skip]
    expected = todo[: len(batch)]
    if list(batch) != expected:
        sys.exit(f"batch ids must be the next unconverted ids in order: {expected}")
    if has_slots(full):
        slots = [o.at[i, "slot"] for i in batch if pd.notna(o.at[i, "slot"])]
        if len(slots) != len(set(slots)):
            sys.exit("two candidates for the same slot in one batch; append them in separate batches")
    out = []
    for sid, turns in batch.items():
        turns = list(turns)
        if len(turns) == 5 and turns[4] == FIXED:
            turns = turns[:4]
        r = o.loc[sid]
        obj = {"id": sid, "source_file": r.source_file, "source_row": int(r.source_row),
               "label": r.label, "user_turns": turns + [FIXED]}
        errs = check_obj(obj, r)
        if errs:
            sys.exit("not appended:\n" + "\n".join(errs))
        out.append(obj)
    with open(part_path(a, b), "a", encoding="utf-8") as f:
        for obj in out:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"appended {len(out)} stories to {part_path(a, b)}")


def flag(a, b, sid, reason):
    o = in_range(load_order(), a, b).set_index("id")
    if sid not in o.index:
        sys.exit(f"{sid} is not in rows {a}-{b}")
    if sid in {x["id"] for x in read_lines(part_path(a, b))}:
        sys.exit(f"{sid} is already converted")
    p = flag_path(a, b)
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["id", "source_file", "source_row", "reason"])
        w.writerow([sid, o.at[sid, "source_file"], int(o.at[sid, "source_row"]), reason])
    print(f"flagged {sid}: {reason}")


def report(objs):
    rows = []
    for x in objs:
        w = [len(s.split()) for s in x["user_turns"]]
        print(x["id"], x["label"], w)
        rows.append({"label": x["label"], "total": sum(w[:4])})
    if rows:
        print(pd.DataFrame(rows).groupby("label").total.agg(["count", "mean", "median", "min", "max"]).round(1))


def validate(a, b):
    full = load_order()
    o = in_range(full, a, b).set_index("id")
    lines = read_lines(part_path(a, b))
    flags = read_flags([flag_path(a, b)])
    skip = skipped(full, {x["id"] for x in lines})
    expected = [i for i in o.index if i not in flags and i not in skip]
    errs = []
    ids = [x["id"] for x in lines]
    if len(set(ids)) != len(ids):
        errs.append("duplicate ids")
    if ids != expected[: len(ids)]:
        errs.append("order does not match order.csv")
    for x in lines:
        if x["id"] in o.index:
            errs += check_obj(x, o.loc[x["id"]])
        else:
            errs.append(f"{x['id']}: not in rows {a}-{b}")
    report(lines)
    print(f"converted {len(lines)}, flagged {len(flags)}, skipped {len(skip & set(o.index))}, remaining {len(expected) - len(lines)} of {len(o)}")
    if has_slots(full):
        r = o[o.slot.notna()]
        open_slots = sorted(set(r.slot.astype(int)) - filled_slots(full, {x["id"] for x in lines}))
        print(f"slots: {r.slot.nunique()}, still open: {len(open_slots)} {open_slots[:20]}")
    print("errors:", errs or "none")


def merge(parts_dir, out_path):
    o = load_order().set_index("id")
    stories = {}
    for p in sorted(glob.glob(os.path.join(parts_dir, "stories_*.jsonl"))):
        for x in read_lines(p):
            if x["id"] in stories:
                sys.exit(f"duplicate id across parts: {x['id']}")
            stories[x["id"]] = x
    flags = read_flags(sorted(glob.glob(os.path.join(parts_dir, "flagged_*.csv"))))
    errs = [e for sid, x in stories.items() if sid in o.index for e in check_obj(x, o.loc[sid])]
    errs += [f"{sid}: not in order.csv" for sid in stories if sid not in o.index]
    base = o[o["slot"].isna()] if "slot" in o.columns else o
    fill = {}
    if "slot" in o.columns:
        for sid, r in o[o["slot"].notna()].iterrows():
            if sid in stories:
                if int(r["slot"]) in fill:
                    errs.append(f"slot {int(r['slot'])} filled twice")
                fill[int(r["slot"])] = sid
    ordered, missing = [], []
    for k, sid in enumerate(base.index, 1):
        if sid in stories:
            ordered.append(stories[sid])
        elif k in fill:
            ordered.append(stories[fill[k]])
        else:
            missing.append(sid if sid not in flags else f"{sid} (flagged, slot {k} open)")
    pd.DataFrame([{"pos": k, "id": x["id"]} for k, x in enumerate(ordered, 1)]).to_csv(
        os.path.splitext(out_path)[0] + "_order.csv", index=False)
    with open(out_path, "w", encoding="utf-8") as f:
        for x in ordered:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    report(ordered)
    print(f"wrote {len(ordered)} stories to {out_path}; flagged {len(flags)}; missing {len(missing)}: {missing[:20]}")
    print("errors:", errs or "none")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "merge":
        merge(*args)
    else:
        a, b = int(args[0]), int(args[1])
        {"show": lambda: show(a, b), "validate": lambda: validate(a, b),
         "append": lambda: append(a, b, args[2]), "flag": lambda: flag(a, b, args[2], args[3])}[cmd]()
