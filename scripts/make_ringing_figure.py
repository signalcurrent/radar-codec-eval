"""Qualitative ringing-artifact figure: reference vs. reconstruction crop,
with matched (real) and phantom (ringing-induced) CFAR detections marked.

Reproduces one already-logged operating point exactly (tfocus-full-jpeg2000,
ratio=32, rate=1.0 bps, Pd=0.861, false=37,711 -- see runs.jsonl / FINDINGS.md
"FINAL CLASSICAL VERDICT") and renders a crop around real scatterers so the
ringing mechanism described in Section 5.3 of the preprint is visible, not
just tabulated. This is a visualization of an already-quantified, already
pre-registered result -- no new experiment, no new claim, nothing that
reopens the stopping rule.

    python scripts/make_ringing_figure.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import maximum_filter
from scipy.spatial import cKDTree

from radarcodec.baselines import CODECS
from radarcodec.metrics.focus_rda import focus_stripmap
from radarcodec.tasks.cfar import ca_cfar

TRIM = 512  # matches eval_focused.py's interior() margin
PFA, GUARD, TRAIN, TOL = 1e-4, 2, 8, 3  # matches configs/baseline_sweep.yaml cfar block


def centroids(det_map):
    peaks = det_map & (maximum_filter(det_map.astype(np.uint8), 3) == det_map)
    return np.argwhere(peaks)


def main():
    d = np.load("data/s1_sm/chunk_crop.npz", allow_pickle=True)
    raw, meta = d["iq"], d["meta"].item()
    print(f"raw crop {raw.shape}; focusing reference...")
    ref = focus_stripmap(raw, meta)

    print("compressing: tfocus(base=jpeg2000, mode=full, ratio=32) -- "
          "the logged 1.0 bps / Pd 0.861 / false 37,711 operating point...")
    raw_hat, rate = CODECS["tfocus"](raw, meta=meta, base="jpeg2000", mode="full", ratio=32)
    hat = focus_stripmap(raw_hat, meta)
    print(f"measured rate: {rate:.3f} bps (logged: 1.00)")

    ref_i, hat_i = ref[TRIM:-TRIM, TRIM:-TRIM], hat[TRIM:-TRIM, TRIM:-TRIM]
    ref_det = ca_cfar(np.abs(ref_i) ** 2, PFA, GUARD, TRAIN)
    hat_det = ca_cfar(np.abs(hat_i) ** 2, PFA, GUARD, TRAIN)
    ref_pts = centroids(ref_det)
    hat_pts = centroids(hat_det)
    print(f"ref detections: {len(ref_pts)}  reconstruction detections: {len(hat_pts)}")

    # classify reconstruction points as matched (near a ref point) or phantom
    tree = cKDTree(ref_pts)
    dist, _ = tree.query(hat_pts, k=1)
    matched = dist <= TOL
    n_phantom = int((~matched).sum())
    print(f"matched: {int(matched.sum())}  phantom: {n_phantom}")

    # find a dense phantom cluster near a real, strong scatterer for the crop
    ref_power = np.abs(ref_i) ** 2
    # strongest real detection = best "real target survives" anchor
    ref_powers_at_pts = ref_power[ref_pts[:, 0], ref_pts[:, 1]]
    strong_order = np.argsort(-ref_powers_at_pts)
    win = 160  # crop half-window, pixels
    chosen = None
    for idx in strong_order[:200]:
        r0, c0 = ref_pts[idx]
        if not (win < r0 < ref_i.shape[0] - win and win < c0 < ref_i.shape[1] - win):
            continue
        nearby_phantom = np.sum(
            (~matched)
            & (np.abs(hat_pts[:, 0] - r0) < win)
            & (np.abs(hat_pts[:, 1] - c0) < win)
        )
        if nearby_phantom >= 8:  # want a visibly ringing neighborhood, not an isolated point
            chosen = (r0, c0, nearby_phantom)
            break
    if chosen is None:
        r0, c0 = ref_pts[strong_order[0]]
        chosen = (r0, c0, 0)
    r0, c0, n_nearby = chosen
    print(f"crop center (interior coords): ({r0},{c0}), nearby phantom count: {n_nearby}")

    rs, re = r0 - win, r0 + win
    cs, ce = c0 - win, c0 + win

    def crop_db(img):
        p = np.abs(img[rs:re, cs:ce]) ** 2
        p = np.maximum(p, p.max() * 1e-6)
        db = 10 * np.log10(p)
        return db

    ref_crop_db = crop_db(ref_i)
    hat_crop_db = crop_db(hat_i)
    vmin, vmax = np.percentile(ref_crop_db, [2, 99.9])

    def in_crop(pts):
        m = (pts[:, 0] >= rs) & (pts[:, 0] < re) & (pts[:, 1] >= cs) & (pts[:, 1] < ce)
        return pts[m] - [rs, cs]

    ref_pts_c = in_crop(ref_pts)
    hat_matched_c = in_crop(hat_pts[matched])
    hat_phantom_c = in_crop(hat_pts[~matched])

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    titles = [
        f"Reference (uncompressed)\n{len(ref_pts_c)} detections in crop",
        f"Reconstruction: tfocus+JPEG2000, ratio=32 (~1.0 bps)\n"
        f"{len(hat_matched_c)} matched, {len(hat_phantom_c)} phantom in crop",
    ]
    for ax, img_db, title in zip(axes, [ref_crop_db, hat_crop_db], titles):
        ax.imshow(img_db, cmap="gray", vmin=vmin, vmax=vmax, interpolation="nearest")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    axes[0].scatter(ref_pts_c[:, 1], ref_pts_c[:, 0], s=60, facecolors="none",
                     edgecolors="lime", linewidths=1.3, label="reference detection")
    axes[1].scatter(hat_matched_c[:, 1], hat_matched_c[:, 0], s=60, facecolors="none",
                     edgecolors="lime", linewidths=1.3, label="matched (real)")
    axes[1].scatter(hat_phantom_c[:, 1], hat_phantom_c[:, 0], s=50, marker="x",
                     color="red", linewidths=1.6, label="phantom (unmatched)")
    axes[0].legend(loc="upper right", fontsize=8, framealpha=0.7)
    axes[1].legend(loc="upper right", fontsize=8, framealpha=0.7)
    fig.suptitle(
        "Figure 3. Wavelet ringing around a real scatterer mints phantom CFAR "
        "detections (Section 5.3)", fontsize=11
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out = "reports/ringing_crop.png"
    fig.savefig(out, dpi=160)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
