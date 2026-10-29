"""Length-matched sampling: 25-word bins over [100, 450]; each bin gets the same number of
YTA and NTA posts, allocated in proportion to min(YTA, NTA) available in the bin
(largest-remainder rounding). Within a bin, each pool is permuted with seed 42; the first k
are sampled and the rest form that bin's replacement queue, so a replacement keeps the match.
All 2N posts are then shuffled together with seed 42."""
import sys, numpy as np, pandas as pd
N = int(sys.argv[1]); SEED = 42; LO, HI, W = 100, 450, 25
D = "/home/claude/aita/"
edges = np.arange(LO, HI + W, W); edges[0] -= 1
pools = {l: pd.read_csv(D + f"pool_{l}.csv") for l in ["YTA", "NTA"]}
for p in pools.values(): p["bin"] = pd.cut(p.words, edges, labels=False)
cnt = pd.DataFrame({l: p.bin.value_counts() for l, p in pools.items()}).fillna(0).sort_index()
cap = cnt.min(axis=1)
raw = cap / cap.sum() * N
k = np.floor(raw).astype(int)
for b in (raw - k).sort_values(ascending=False).index[: N - k.sum()]: k[b] += 1
picked, queues = [], []
for l, p in pools.items():
    for b, kb in k.items():
        perm = p[p.bin == b].sample(frac=1, random_state=SEED)
        picked.append(perm.head(kb)); queues.append(perm.iloc[kb:])
sample = pd.concat(picked, ignore_index=True)
order = sample.sample(frac=1, random_state=SEED).reset_index(drop=True)
order["id"] = order.label.str.lower() + "_" + order.source_row.astype(int).map("{:04d}".format)
order.to_csv(D + "order.csv", index=False)
pd.concat(queues, ignore_index=True).to_csv(D + "replacements.csv", index=False)
print(pd.DataFrame({"YTA avail": cnt.YTA.astype(int), "NTA avail": cnt.NTA.astype(int), "drawn per label": k},
      index=cnt.index).rename(index=lambda b: f"{int(edges[b])+ (1 if b==0 else 1)}-{int(edges[b+1])}"))
print(order.groupby("label").words.agg(["count", "mean", "median", "min", "max"]).round(1))
