"""Add one more candidate for every slot that is still open after the replacement chat.

  python add_candidates.py ORDER_EXT_CSV REPLACEMENTS_CSV PARTS_DIR

A slot is open when none of its candidates is converted and all of them are flagged.
For each open slot the next unused post with the same label and bin is appended to
order_ext.csv (a backup is written first). Prints the new row range to convert.
"""
import glob, json, os, shutil, sys
import pandas as pd

ext_csv, repl_csv, parts = sys.argv[1:4]
ext = pd.read_csv(ext_csv)
repl = pd.read_csv(repl_csv)
done = {json.loads(l)["id"] for p in glob.glob(os.path.join(parts, "stories_*.jsonl"))
        for l in open(p, encoding="utf-8") if l.strip()}
flags = set(pd.concat([pd.read_csv(f) for f in glob.glob(os.path.join(parts, "flagged_*.csv"))]).id)

c = ext[ext.slot.notna()]
open_slots = [s for s, g in c.groupby("slot") if not g.id.isin(done).any() and g.id.isin(flags).all()]
pending = [s for s, g in c.groupby("slot") if not g.id.isin(done).any() and not g.id.isin(flags).all()]
if pending:
    print(f"warning: slots {[int(s) for s in pending]} still have unconverted candidates; finish those first")
if not open_slots:
    sys.exit("no open slots")

used = set(zip(ext.source_file, ext.source_row.astype(int)))
rows = []
for s in open_slots:
    base = ext.iloc[int(s) - 1]
    pool = repl[(repl.label == base.label) & (repl.bin == base.bin)]
    pool = pool[[(a, int(b)) not in used for a, b in zip(pool.source_file, pool.source_row)]]
    if pool.empty:
        sys.exit(f"no candidate left for slot {int(s)}")
    p = pool.iloc[0]
    used.add((p.source_file, int(p.source_row)))
    rows.append({"source_file": p.source_file, "source_row": int(p.source_row), "label": p.label,
                 "words": int(p.words), "bin": int(p.bin), "id": f"{p.label.lower()}_{int(p.source_row):04d}",
                 "slot": int(s), "cand": int(c[c.slot == s].cand.max()) + 1})

shutil.copy(ext_csv, ext_csv.replace(".csv", "_backup.csv"))
start = len(ext) + 1
new = pd.concat([ext, pd.DataFrame(rows)], ignore_index=True)
assert new.id.is_unique
new.to_csv(ext_csv, index=False)
print(f"added {len(rows)} candidates for slots {[int(s) for s in open_slots]}: rows {start}-{len(new)}")
print(pd.DataFrame(rows)[["id", "slot", "cand", "label", "bin"]].to_string(index=False))
