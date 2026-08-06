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
    # an operating point IS (codec, rate); last row wins so re-runs supersede
    runs[(r["codec"], round(r["rate_bps"], 2))] = r

by_codec = {}
for r in runs.values():
    by_codec.setdefault(r["codec"], []).append(r)

Path("reports").mkdir(exist_ok=True)
for metric, label, fname in [
    ("cfar_pd", "CFAR detection agreement (Pd)", "rate_vs_pd.png"),
    ("mse", "MSE (raw I/Q)", "rate_vs_mse.png"),
    ("phase_rmse", "Phase RMSE (rad)", "rate_vs_phase.png"),
]:
    fig, ax = plt.subplots(figsize=(7, 5))
    for codec, rows in sorted(by_codec.items()):
        rows = sorted(rows, key=lambda r: r["rate_bps"])
        ax.plot([r["rate_bps"] for r in rows], [r[metric] for r in rows], "o-", label=codec)
    ax.set_xlabel("rate (bits per complex sample)")
    ax.set_ylabel(label)
    if metric == "mse":
        ax.set_yscale("log")
    ax.axvline(3.4, ls="--", lw=1, color="gray")
    ax.text(3.45, ax.get_ylim()[1], " FDBAQ IW avg", va="top", fontsize=8, color="gray")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"reports/{fname}", dpi=150)
    print(f"reports/{fname}")
