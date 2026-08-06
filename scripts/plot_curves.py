"""Regenerate rate-vs-utility curves in reports/ from experiments/runs.jsonl.

Uses the most recent run per (codec, params) so re-runs supersede stale rows.

    python scripts/plot_curves.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

runs = {}
for line in open("experiments/runs.jsonl"):
    r = json.loads(line)
    # an operating point IS (domain, codec, rate); last row wins so re-runs supersede
    runs[(r.get("domain", "s1"), r["codec"], round(r["rate_bps"], 2))] = r

Path("reports").mkdir(exist_ok=True)
PLOTS = [
    # (metric, required domain, label, filename)
    ("cfar_pd", "s1_focused", "Post-focus CFAR detection agreement (Pd)", "rate_vs_pd.png"),
    ("mse", "s1", "MSE (raw I/Q)", "rate_vs_mse.png"),
    ("phase_rmse", "s1", "Phase RMSE (rad)", "rate_vs_phase.png"),
    ("atr_acc", "mstar", "Frozen-ATR accuracy (MSTAR 15 deg)", "rate_vs_atr.png"),
]
for metric, domain, label, fname in PLOTS:
    by_codec = {}
    for r in runs.values():
        if r.get("domain", "s1") == domain and metric in r and r[metric] == r[metric]:
            by_codec.setdefault(r["codec"], []).append(r)
    if not by_codec:
        continue
    fig, ax = plt.subplots(figsize=(7, 5))
    for codec, rows in sorted(by_codec.items()):
        rows = sorted(rows, key=lambda r: r["rate_bps"])
        style = "o-" if codec != "uncompressed" else "k*"
        ax.plot([r["rate_bps"] for r in rows], [r[metric] for r in rows], style, label=codec)
    ax.set_xlabel("rate (bits per COMPLEX sample, I+Q combined)")
    ax.set_ylabel(label)
    if metric == "mse":
        ax.set_yscale("log")
    # ESA quotes FDBAQ per real component (~3.4); on this axis that is ~6.8
    ax.axvline(6.8, ls="--", lw=1, color="gray")
    ax.text(6.85, ax.get_ylim()[1], " FDBAQ IW avg (~3.4 b/component)", va="top", fontsize=8, color="gray")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"reports/{fname}", dpi=150)
    print(f"reports/{fname}")
