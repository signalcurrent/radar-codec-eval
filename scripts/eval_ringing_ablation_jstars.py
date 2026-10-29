"""JSTARS revision E3 + E6 on the Sentinel-1 scene.

E3 (ringing ablation): focused-domain ("tfocus", mode=full) compression with four base codecs at
matched rate: JPEG2000 9/7 irreversible (the study's wavelet), JPEG2000 5/3 reversible at the same
byte budget, HEVC (block transform; QP grid, nearest-rate points chosen post hoc by the declared
rule), and BAQ (non-transform scalar quantizer). For each reconstruction the spurious detections
("phantoms": reconstruction detections farther than TOL cells from any reference detection) are
located relative to STRONG reference scatterers (reference detections whose power is in the top
decile of reference-detection powers). Metrics: fraction of phantoms within R cells of a strong
scatterer, the areal baseline (fraction of interior pixels within R cells of a strong scatterer),
their ratio (enrichment), and the radial histogram 0..30 cells.

E6 (transform / focuser impulse response): a unit point target synthesised at the crop centre with
the invertible transform's inverse, focused with the study's RDA focuser; IRW (-3 dB, cells) and
PSLR (dB) along range and azimuth via radar_metrics.irw_pslr. Also records the Fig. 5 crop
coordinates (make_ringing_figure.py's selection rule) to reports/ringing_crop.json.

Pre-declared in FINDINGS.md (2026-10-29, "E3 / E6") BEFORE the first run. Rows tagged
study = "jstars_E3"; E6 numbers are written to reports/e6_impulse_response.json.

    python scripts/eval_ringing_ablation_jstars.py [--dry-run] [--skip-e6]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import yaml
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

from radarcodec.baselines import CODECS
from radarcodec.experiments import log_run
from radarcodec.metrics.focus_rda import focus_stripmap
from radarcodec.metrics.radar_metrics import irw_pslr
from radarcodec.tasks.cfar import _to_centroids, ca_cfar

ROOT = Path(__file__).resolve().parents[1]
PFA, GUARD, TRAIN, TOL = 1e-4, 2, 8, 3
R_NEAR = 8          # "near a strong scatterer" radius, cells (declared)
STRONG_Q = 0.90     # top decile of reference-detection powers (declared)
HIST_MAX = 30

ARMS = [
    ("jpeg2000_97", "jpeg2000", {"ratio": 8}), ("jpeg2000_97", "jpeg2000", {"ratio": 16}),
    ("jpeg2000_53", "jpeg2000", {"ratio": 8, "reversible": True}), ("jpeg2000_53", "jpeg2000", {"ratio": 16, "reversible": True}),
    ("hevc", "hevc", {"qp": 16}), ("hevc", "hevc", {"qp": 20}), ("hevc", "hevc", {"qp": 24}),
    ("hevc", "hevc", {"qp": 28}), ("hevc", "hevc", {"qp": 32}),
    ("baq", "baq", {"bits": 1, "block": 128}), ("baq", "baq", {"bits": 2, "block": 128}),
]


def phantom_geometry(ref_i, hat_i):
    pref = np.abs(ref_i) ** 2
    phat_ = np.abs(hat_i) ** 2
    ref_pts = _to_centroids(ca_cfar(pref, PFA, GUARD, TRAIN), pref)
    hat_pts = _to_centroids(ca_cfar(phat_, PFA, GUARD, TRAIN), phat_)
    d, _ = cKDTree(ref_pts).query(hat_pts, k=1)
    phantoms = hat_pts[d > TOL]
    pw = pref[ref_pts[:, 0], ref_pts[:, 1]]
    strong = ref_pts[pw >= np.quantile(pw, STRONG_Q)]
    dist_ph, _ = cKDTree(strong).query(phantoms, k=1) if len(phantoms) else (np.array([]), None)
    mask = np.ones(ref_i.shape, dtype=bool)
    mask[strong[:, 0], strong[:, 1]] = False
    areal = float(np.mean(distance_transform_edt(mask) <= R_NEAR))
    frac = float(np.mean(dist_ph <= R_NEAR)) if len(phantoms) else float("nan")
    # E3b (declared 2026-10-29 evening): absolute counts near three equal-size anchor sets
    weak = ref_pts[pw <= np.quantile(pw, 1.0 - STRONG_Q)]
    rng = np.random.default_rng(1337)
    rand = np.column_stack([rng.integers(0, ref_i.shape[0], len(strong)), rng.integers(0, ref_i.shape[1], len(strong))])
    def near_count(anchors):
        if not len(phantoms):
            return 0
        d, _ = cKDTree(anchors).query(phantoms, k=1)
        return int(np.sum(d <= R_NEAR))
    e3b = {"n_anchors": {"strong": int(len(strong)), "weak": int(len(weak)), "random": int(len(rand))},
           "near_strong": near_count(strong), "near_weak": near_count(weak), "near_random": near_count(rand)}
    hist = np.histogram(np.minimum(dist_ph, HIST_MAX), bins=np.arange(0, HIST_MAX + 2))[0].tolist() if len(phantoms) else []
    pd = float(np.mean(cKDTree(hat_pts).query(ref_pts, k=1)[0] <= TOL)) if len(hat_pts) else 0.0
    return {"n_ref": int(len(ref_pts)), "n_strong": int(len(strong)), "n_hat": int(len(hat_pts)),
            "n_phantom": int(len(phantoms)), "pd": round(pd, 5),
            "frac_phantom_within_R": None if np.isnan(frac) else round(frac, 4),
            "areal_baseline_within_R": round(areal, 4),
            "enrichment": None if np.isnan(frac) else round(frac / areal, 3),
            "median_phantom_dist": None if not len(phantoms) else float(np.median(dist_ph)),
            "radial_hist_0_30": hist, "R": R_NEAR, "strong_quantile": STRONG_Q, "e3b": e3b}


def e6_impulse_response(raw_shape, meta):
    from radarcodec.baselines.transform_codec import inverse
    img = np.zeros(raw_shape, dtype=np.complex64)
    img[raw_shape[0] // 2, raw_shape[1] // 2] = 1.0
    raw_pt = inverse(img, meta, mode="full")
    psf = focus_stripmap(raw_pt, meta)
    pk = np.unravel_index(np.argmax(np.abs(psf)), psf.shape)
    chip = psf[pk[0] - 64: pk[0] + 64, pk[1] - 64: pk[1] + 64]
    irw_rg, pslr_rg = irw_pslr(chip, axis=1)
    irw_az, pslr_az = irw_pslr(chip, axis=0)
    return {"peak_rc": [int(pk[0]), int(pk[1])], "irw_range_cells": round(float(irw_rg), 3),
            "pslr_range_db": round(float(pslr_rg), 2), "irw_azimuth_cells": round(float(irw_az), 3),
            "pslr_azimuth_db": round(float(pslr_az), 2), "method": "unit target via transform_codec.inverse(mode=full) at crop centre, focus_stripmap, irw_pslr oversample 16"}


def fig5_crop_coords(ref_i, hat_i):
    """Replicates make_ringing_figure.py's crop selection on the logged r32 operating point."""
    pref = np.abs(ref_i) ** 2
    phat_ = np.abs(hat_i) ** 2
    ref_pts = _to_centroids(ca_cfar(pref, PFA, GUARD, TRAIN), pref)
    hat_pts = _to_centroids(ca_cfar(phat_, PFA, GUARD, TRAIN), phat_)
    matched = cKDTree(ref_pts).query(hat_pts, k=1)[0] <= TOL
    order = np.argsort(-pref[ref_pts[:, 0], ref_pts[:, 1]])
    win = 160
    for idx in order[:200]:
        r0, c0 = ref_pts[idx]
        if not (win < r0 < ref_i.shape[0] - win and win < c0 < ref_i.shape[1] - win):
            continue
        n = int(np.sum((~matched) & (np.abs(hat_pts[:, 0] - r0) < win) & (np.abs(hat_pts[:, 1] - c0) < win)))
        if n >= 8:
            return {"center_interior_rc": [int(r0), int(c0)], "center_full_rc": [int(r0) + 512, int(c0) + 512],
                    "half_window": win, "nearby_phantoms": n, "interior_trim": 512}
    r0, c0 = ref_pts[order[0]]
    return {"center_interior_rc": [int(r0), int(c0)], "center_full_rc": [int(r0) + 512, int(c0) + 512],
            "half_window": win, "nearby_phantoms": 0, "interior_trim": 512}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-e6", action="store_true")
    ap.add_argument("--study", default="jstars_E3", help="row tag; jstars_E3b for the null-anchor rerun")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_focused import interior, load_crop
    raw, meta = load_crop()
    ref = focus_stripmap(raw, meta)
    ref_i = interior(ref)

    if not a.skip_e6:
        e6 = e6_impulse_response(raw.shape, meta)
        print("E6 impulse response:", json.dumps(e6), flush=True)
        raw_hat, _ = CODECS["tfocus"](raw, meta=meta, base="jpeg2000", mode="full", ratio=32)
        crop = fig5_crop_coords(ref_i, interior(focus_stripmap(raw_hat, meta)))
        print("Fig. 5 crop:", json.dumps(crop), flush=True)
        if not a.dry_run:
            (ROOT / "reports" / "e6_impulse_response.json").write_text(json.dumps(e6, indent=1))
            (ROOT / "reports" / "ringing_crop.json").write_text(json.dumps(crop, indent=1))
        del raw_hat

    for arm, base, bp in ARMS:
        t0 = time.perf_counter()
        raw_hat, rate = CODECS["tfocus"](raw, meta=meta, base=base, mode="full", **bp)
        cs = time.perf_counter() - t0
        hat_i = interior(focus_stripmap(raw_hat, meta))
        del raw_hat
        g = phantom_geometry(ref_i, hat_i)
        del hat_i
        row = {"study": a.study, "codec": "tfocus", "arm": arm,
               "params": {"base": base, "mode": "full", **bp}, "domain": "s1_focused",
               "rate_bps": float(rate), "cfar_pd": g["pd"], "cfar_false": g["n_phantom"],
               "n_ref_detections": g["n_ref"], "mapping": "v2-pctclip99.99", "codec_seconds": round(cs, 2),
               "ringing": g}
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        print(f"{arm:12s} {json.dumps(bp, sort_keys=True):40s} rate={rate:.3f} pd={g['pd']:.3f} phantoms={g['n_phantom']:6d} "
              f"within{R_NEAR}={g['frac_phantom_within_R']} areal={g['areal_baseline_within_R']} enrich={g['enrichment']} | {cs:.0f}s", flush=True)


if __name__ == "__main__":
    main()
