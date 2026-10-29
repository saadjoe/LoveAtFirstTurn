import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "results"
MODELS = ["qwen3.8-27b", "gemma-4-31b-it", "olmo-3.1-32b-think"]
DATASETS = ["1_prompt", "5_prompt", "10_prompt", "third_person"]
DATASET_NAMES = ["1 turn", "5 turns", "10 turns", "3rd person"]
PAIRS = [("1_prompt", "5_prompt"), ("1_prompt", "10_prompt"), ("1_prompt", "third_person")]
COLORS = ["#2a78d6", "#eb6834"]
SEED = 0


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def load():
    rows, reliability = [], []
    for model in MODELS:
        for dataset in DATASETS:
            conversations = read_jsonl(DATA_DIR / "conversations" / model / f"conversations_{dataset}.jsonl")
            thinking = {c["id"]: [m for m in c["messages"] if m["role"] == "assistant"][-1]["thinking"] for c in conversations}
            judged = read_jsonl(DATA_DIR / "judgements" / model / f"judgements_{dataset}.jsonl")
            failures = 0
            for r in judged:
                cot = r["cot"]
                # The judge sometimes misreads the reasoning as its own task and quotes its first line.
                quote = cot["quote"].strip().strip("\"'")[:30] if cot else ""
                failed = cot is not None and cot["verdict"] == "UNCLEAR" and thinking[r["id"]].lstrip().startswith(quote)
                failures += failed
                valid = cot is not None and not failed
                rows.append(
                    {
                        "model": model,
                        "dataset": dataset,
                        "id": r["id"],
                        "label": r["label"],
                        "answer": r["answer"]["verdict"] if r["answer"] else None,
                        "cot": cot["verdict"] if valid else None,
                        "softening": cot["softening"] if valid else None,
                    }
                )
            reliability.append(
                {
                    "model": model,
                    "dataset": dataset,
                    "missing": len(conversations) - len(judged),
                    "answer_null": sum(r["answer"] is None for r in judged),
                    "cot_judge_failures": failures,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(reliability)


def wilson(k, n, z=1.96):
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def binom_p(k, n):
    if n == 0:
        return 1.0
    k = min(k, n - k)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n)


def paired(x, y, rng):
    """Difference y - x of two boolean arrays over the same stories, with bootstrap CI and exact McNemar p."""
    idx = rng.integers(0, len(x), (2000, len(x)))
    diffs = y[idx].mean(1) - x[idx].mean(1)
    return {
        "diff": y.mean() - x.mean(),
        "ci_low": np.percentile(diffs, 2.5),
        "ci_high": np.percentile(diffs, 97.5),
        "p": binom_p(int((x & ~y).sum()), int((x != y).sum())),
    }


def sycophancy_table(df):
    rows = []
    for (model, dataset), d in df.groupby(["model", "dataset"], sort=False):
        for part in ["answer", "cot"]:
            yta = d.loc[d.label == "YTA", part].dropna()
            nta = d.loc[d.label == "NTA", part].dropna()
            k = int((yta == "NTA").sum())
            low, high = wilson(k, len(yta))
            rows.append(
                {
                    "model": model,
                    "dataset": dataset,
                    "part": part,
                    "n": len(yta),
                    "sycophancy": k / len(yta),
                    "ci_low": low,
                    "ci_high": high,
                    "nta_agreement": (nta == "NTA").mean(),
                }
            )
    return pd.DataFrame(rows)


def comparison_table(df, rng):
    rows = []
    yta = df[df.label == "YTA"]
    for model in MODELS:
        for part in ["answer", "cot"]:
            for first, second in PAIRS:
                a = yta[(yta.model == model) & (yta.dataset == first)].set_index("id")[part]
                b = yta[(yta.model == model) & (yta.dataset == second)].set_index("id")[part]
                both = pd.concat([a, b], axis=1, keys=["a", "b"], join="inner").dropna()
                x, y = (both.a == "NTA").to_numpy(), (both.b == "NTA").to_numpy()
                rows.append({"model": model, "part": part, "first": first, "second": second, "n": len(both), **paired(x, y, rng)})
    return pd.DataFrame(rows)


def cot_vs_answer_table(df, rng):
    rows = []
    for (model, dataset), d in df.groupby(["model", "dataset"], sort=False):
        d = d.dropna(subset=["answer", "cot"])
        yta = d[d.label == "YTA"]
        softened = int(((d.cot == "YTA") & (d.answer == "NTA")).sum())
        hardened = int(((d.cot == "NTA") & (d.answer == "YTA")).sum())
        rows.append(
            {
                "model": model,
                "dataset": dataset,
                "n": len(d),
                "agreement": (d.cot == d.answer).mean(),
                **paired((yta.cot == "NTA").to_numpy(), (yta.answer == "NTA").to_numpy(), rng),
                "cot_yta_answer_nta": softened,
                "cot_nta_answer_yta": hardened,
                "p_switch": binom_p(softened, softened + hardened),
                "softening_rate": d.softening.astype(bool).mean(),
            }
        )
    return pd.DataFrame(rows)


def bar_figure(series, title, ylabel, path, percent=False):
    """series: {model: [(label, values, (lows, highs) or None), (label, values, ci)]}, one value per dataset."""
    fig, axes = plt.subplots(1, len(MODELS), figsize=(13, 4.2), sharey=True)
    x = np.arange(len(DATASETS))
    for ax, model in zip(axes, MODELS):
        for i, (label, values, ci) in enumerate(series[model]):
            pos = x + (i - 0.5) * 0.38
            values = np.asarray(values)
            ax.bar(pos, values, 0.38, color=COLORS[i], edgecolor="white", linewidth=2, label=label)
            if ci is not None:
                ax.errorbar(pos, values, yerr=[values - ci[0], ci[1] - values], fmt="none", ecolor="black", elinewidth=1, capsize=3)
        ax.set_xticks(x, DATASET_NAMES)
        ax.set_title(model, fontsize=11)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e4e3df")
        ax.set_axisbelow(True)
    if percent:
        axes[0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        axes[0].set_ylim(0, 1)
    axes[0].set_ylabel(ylabel)
    axes[0].legend(frameon=False, loc="upper left")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main():
    (OUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "figures").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    df, reliability = load()
    syc = sycophancy_table(df)
    comparisons = comparison_table(df, rng)
    cva = cot_vs_answer_table(df, rng)
    for name, table in [("sycophancy", syc), ("comparisons", comparisons), ("cot_vs_answer", cva), ("reliability", reliability)]:
        table.to_csv(OUT_DIR / "tables" / f"{name}.csv", index=False, float_format="%.4f")

    series = {}
    for model in MODELS:
        series[model] = []
        for part, label in [("answer", "Final answer"), ("cot", "Thinking")]:
            s = syc[(syc.model == model) & (syc.part == part)].set_index("dataset").loc[DATASETS]
            series[model].append((label, s.sycophancy, (s.ci_low.to_numpy(), s.ci_high.to_numpy())))
    bar_figure(series, "Sycophancy: share of YTA stories judged NTA (95% CI)", "YTA stories judged NTA", OUT_DIR / "figures" / "sycophancy.png", percent=True)

    series = {}
    for model in MODELS:
        s = cva[cva.model == model].set_index("dataset").loc[DATASETS]
        series[model] = [("Thinking YTA, answer NTA", s.cot_yta_answer_nta, None), ("Thinking NTA, answer YTA", s.cot_nta_answer_yta, None)]
    bar_figure(series, "Verdict switches between thinking and final answer", "Stories", OUT_DIR / "figures" / "switches.png")

    pd.set_option("display.width", 200, "display.max_columns", 20, "display.precision", 3)
    print(syc.pivot_table(index=["model", "part"], columns="dataset", values="sycophancy", sort=False)[DATASETS])
    print(f"\nWrote tables and figures to {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
