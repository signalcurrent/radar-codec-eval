"""Evaluation-pipeline schematic (Figure 1 of the paper).

A block diagram of the task-based evaluation: the same raw echo block is
carried down two lanes -- a reference lane (focus, then detect) and a
reconstruction lane (compress, decompress, focus, then detect) -- whose
detection sets feed the two-sided criterion of eq. (5). No data; pure
diagram. Regenerate: python scripts/make_pipeline_figure.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


def box(ax, x, y, w, h, text, fc="white"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.04",
            linewidth=1.3, edgecolor="black", facecolor=fc,
        )
    )
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10)


def arrow(ax, x0, y0, x1, y1, label=None):
    ax.add_patch(
        FancyArrowPatch(
            (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=13,
            linewidth=1.2, color="black", shrinkA=0, shrinkB=0,
        )
    )
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.05, label,
                ha="center", va="bottom", fontsize=9, style="italic")


fig, ax = plt.subplots(figsize=(11, 4.4))
ax.set_xlim(0, 11)
ax.set_ylim(0, 4.4)
ax.axis("off")

BW, BH = 1.35, 0.62
yr, yc = 3.35, 1.15  # reference lane y, reconstruction lane y

# input
box(ax, 0.15, (yr + yc) / 2 - BH / 2 + 0.31, 1.0, BH, r"raw  $\mathbf{x}$", fc="#eeeeee")
xin_r, xin_c = 1.15, 1.15

# reference lane (top): Focus -> I -> CFAR -> D_ref
box(ax, 2.1, yr, BW, BH, r"Focus $\mathcal{F}$")
box(ax, 4.0, yr, BW, BH, r"CA-CFAR" "\n" r"(2)")
box(ax, 6.0, yr, 1.5, BH, r"$\mathcal{D}_{\mathrm{ref}}$", fc="#eeeeee")
# reconstruction lane (bottom): Codec -> xhat -> Focus -> Ihat -> CFAR -> D_rec
box(ax, 2.1, yc, BW, BH, r"Codec $\mathcal{C}_R$")
box(ax, 4.0, yc, BW, BH, r"Focus $\mathcal{F}$")
box(ax, 5.9, yc, BW, BH, r"CA-CFAR" "\n" r"(2)")
box(ax, 7.75, yc, 1.4, BH, r"$\mathcal{D}_{\mathrm{rec}}$", fc="#eeeeee")

# input splits to both lanes
ax.add_patch(FancyArrowPatch((xin_r, (yr + yc) / 2 + 0.31), (1.6, (yr + yc) / 2 + 0.31),
                             arrowstyle="-", linewidth=1.2, color="black"))
arrow(ax, 1.6, yr + BH / 2, 2.1, yr + BH / 2)
arrow(ax, 1.6, yc + BH / 2, 2.1, yc + BH / 2)
ax.add_patch(FancyArrowPatch((1.6, yc + BH / 2), (1.6, yr + BH / 2),
                             arrowstyle="-", linewidth=1.2, color="black"))

# reference lane arrows
arrow(ax, 3.45, yr + BH / 2, 4.0, yr + BH / 2, r"$\mathbf{I}$")
arrow(ax, 5.35, yr + BH / 2, 6.0, yr + BH / 2)
# reconstruction lane arrows
arrow(ax, 3.45, yc + BH / 2, 4.0, yc + BH / 2, r"$\hat{\mathbf{x}}$")
arrow(ax, 5.35, yc + BH / 2, 5.9, yc + BH / 2, r"$\hat{\mathbf{I}}$")
arrow(ax, 7.25, yc + BH / 2, 7.75, yc + BH / 2)

# criterion box (right), fed by both detection sets
cx, cy, cw, ch = 9.4, 1.9, 1.5, 0.95
box(ax, cx, cy, cw, ch, "Two-sided\ncriterion (5)", fc="#dddddd")
ax.add_patch(FancyArrowPatch((7.5, yr + BH / 2), (cx + cw / 2, yr + BH / 2),
                             arrowstyle="-", linewidth=1.2, color="black"))
ax.add_patch(FancyArrowPatch((cx + cw / 2, yr + BH / 2), (cx + cw / 2, cy + ch),
                             arrowstyle="-|>", mutation_scale=13, linewidth=1.2, color="black"))
ax.add_patch(FancyArrowPatch((9.15, yc + BH / 2), (cx + cw / 2, yc + BH / 2),
                             arrowstyle="-", linewidth=1.2, color="black"))
arrow(ax, cx + cw / 2, yc + BH / 2, cx + cw / 2, cy)

# verdict
ax.text(cx + cw / 2, cy - 0.28,
        r"sustains utility at $R$?" "\n" r"($P_d \geq 0.9$,  $N_\mathrm{spur} \leq 0.1\,|\mathcal{D}_\mathrm{ref}|$)",
        ha="center", va="top", fontsize=8.5)

# lane labels
ax.text(0.15, yr + BH + 0.18, "reference lane", fontsize=9, style="italic", color="#444444")
ax.text(0.15, yc - 0.22, "reconstruction lane", fontsize=9, style="italic", color="#444444")

out = "reports/pipeline_schematic.png"
fig.savefig(out, dpi=160, bbox_inches="tight")
print(f"wrote {out}")
