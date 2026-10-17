"""Append replacement candidates for flagged posts to order.csv.

  python make_extension.py ORDER_CSV REPLACEMENTS_CSV PARTS_DIR [K]

Every flagged post leaves a slot (its position, label and length bin). For each slot, the next K
unused posts with the same label and bin are taken from replacements.csv (default K=2). Rows
501.. hold all first candidates in slot order, then all second candidates, and so on. Column
`slot` is the position a candidate can fill, `cand` its rank. convert_tools.py skips a candidate
once its slot is filled, so a later candidate is only converted if the earlier ones were flagged.

Writes order_ext.csv next to ORDER_CSV: the 500 original rows plus the candidate rows.
"""
import glob, os, sys
import pandas as pd

order_csv, repl_csv, parts_dir = sys.argv[1:4]
K = int(sys.argv[4]) if len(sys.argv) > 4 else 2
order = pd.read_csv(order_csv)
order["pos"] = range(1, len(order) + 1)
repl = pd.read_csv(repl_csv)
flags = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(parts_dir, "flagged_*.csv")))]).drop_duplicates("id")
missing = set(flags.id) - set(order.id)
if missing:
    sys.exit(f"flagged ids not in order.csv: {sorted(missing)}")

key = lambda df: set(zip(df.source_file, df.source_row.astype(int)))
used = key(order)
slots = order[order.id.isin(flags.id)]
cands = {k: [] for k in range(1, K + 1)}
for r in slots.itertuples():
    pool = repl[(repl.label == r.label) & (repl.bin == r.bin)]
    pool = pool[[(a, int(b)) not in used for a, b in zip(pool.source_file, pool.source_row)]]
    if len(pool) < K:
        sys.exit(f"only {len(pool)} candidates left for slot {r.pos} ({r.label}, bin {r.bin})")
    for k in range(1, K + 1):
        c = pool.iloc[k - 1]
        used.add((c.source_file, int(c.source_row)))
        cands[k].append({"source_file": c.source_file, "source_row": int(c.source_row), "label": c.label,
                         "words": int(c.words), "bin": int(c.bin),
                         "id": f"{c.label.lower()}_{int(c.source_row):04d}", "slot": r.pos, "cand": k})

cols = ["source_file", "source_row", "label", "words", "bin", "id"]
ext = pd.concat([order[cols].assign(slot=pd.NA, cand=pd.NA)] + [pd.DataFrame(cands[k]) for k in cands], ignore_index=True)
assert ext.id.is_unique and len(key(ext)) == len(ext)
out = os.path.join(os.path.dirname(os.path.abspath(order_csv)), "order_ext.csv")
ext.to_csv(out, index=False)
n = len(slots)
print(f"{n} slots ({slots.label.value_counts().to_dict()}), {K} candidates each")
print(f"candidate rows: 501-{500 + n * K}; first candidates 501-{500 + n}")
print(f"wrote {out}")
