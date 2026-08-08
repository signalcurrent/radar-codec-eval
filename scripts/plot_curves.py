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
    # an operating point IS (domain, codec, rate); last row wins so re-runs supersede.
    # BUG FIX (2026-08-08): every tfocus row shares the literal codec string
    # "tfocus" regardless of (mode, base) -- the full and dechirp JPEG2000 arms
    # land on identical nominal rates (same ratio param) and were silently
    # colliding on this key, dropping tfocus-full-jpeg2000 from every figure.
    codec_key = r["codec"]
    if codec_key == "tfocus":
        codec_key = f"tfocus-{r['params'].get('mode', '?')}-{r['params'].get('base', '?')}"
    runs[(r.get("domain", "s1"), codec_key, round(r["rate_bps"], 2))] = r

Path("reports").mkdir(exist_ok=True)
PLOTS = [
    # (metric, required domain, label, filename)
    ("cfar_pd", "s1_focused", "Post-focus CFAR detection agreement (Pd)", "rate_vs_pd.png"),
    ("cfar_false", "s1_focused", "Spurious detections (count, log scale)", "rate_vs_spurious.png"),
    ("mse", "s1", "MSE (raw I/Q)", "rate_vs_mse.png"),
    ("phase_rmse", "s1", "Phase RMSE (rad)", "rate_vs_phase.png"),
    ("atr_acc", "mstar", "Frozen-ATR accuracy (MSTAR 15 deg)", "rate_vs_atr.png"),
]
for metric, domain, label, fname in PLOTS:
    by_codec = {}
    n_ref = None
    for r in runs.values():
        if r.get("domain", "s1") != domain or metric not in r or r[metric] != r[metric]:
            continue
        # focused-domain rows: only the mapping-v2 vintage (Amendment 5 supersession)
        if domain == "s1_focused" and r.get("mapping") != "v2-pctclip99.99":
            continue
        n_ref = r.get("n_ref_detections", n_ref)
        key = r["codec"]
        if key == "tfocus":
            key = f"tfocus-{r['params'].get('mode', '?')}-{r['params'].get('base', '?')}"
        by_codec.setdefault(key, []).append(r)
    if not by_codec:
        continue
    fig, ax = plt.subplots(figsize=(7, 5))
    for codec, rows in sorted(by_codec.items()):
        rows = sorted(rows, key=lambda r: r["rate_bps"])
        style = "o-" if codec != "uncompressed" else "k*"
        ax.plot([r["rate_bps"] for r in rows], [r[metric] for r in rows], style, label=codec)
    ax.set_xlabel("rate (bits per COMPLEX sample, I+Q combined)")
    ax.set_ylabel(label)
    if metric == "mse" or metric == "cfar_false":
        ax.set_yscale("log")
    if metric == "cfar_pd":
        # pre-registered utility floor (Sec 3.1)
        ax.axhline(0.9, ls=":", lw=1, color="crimson")
        ax.text(ax.get_xlim()[1] if ax.get_xlim()[1] else 14, 0.9, " Pd floor (0.9)",
                va="bottom", ha="right", fontsize=8, color="crimson")
        # R_c = 4.86 bps, raw-domain HEVC qp36 (FINAL CLASSICAL VERDICT, mapping v2)
        ax.axvline(4.86, ls=":", lw=1, color="crimson")
        ax.text(4.9, 0.05, " R_c = 4.86 bps", fontsize=8, color="crimson")
    if metric == "cfar_false" and n_ref:
        budget = 0.10 * n_ref
        ax.axhline(budget, ls=":", lw=1, color="crimson")
        ax.text(ax.get_xlim()[1] if ax.get_xlim()[1] else 14, budget,
                f" spurious budget (10% of {n_ref:,} ref.)", va="bottom", ha="right",
                fontsize=8, color="crimson")
    # ESA quotes FDBAQ per real component (~3.4); on this axis that is ~6.8
    ax.axvline(6.8, ls="--", lw=1, color="gray")
    ax.text(6.85, ax.get_ylim()[1], " FDBAQ IW avg (~3.4 b/component)", va="top", fontsize=8, color="gray")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"reports/{fname}", dpi=150)
    print(f"reports/{fname}")
