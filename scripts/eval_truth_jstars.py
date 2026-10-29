"""JSTARS revision E4: ground-truth anchors for the detection-agreement metric.

Gotcha: the GPS-truthed Durango (AFRL challenge data; durangoChallenge_GPStruth.mat) at AFRL's own
documented image position (formSimpleRangeDopplerImage.m: Doppler pixel 834, range pixel 180,
1-based; 0-based peak at (178, 833) in our identically formed image, 29.3 dB over scene median, a
reference CFAR detection at (179, 833)). The GPS record shows the vehicle stationary during our CPI.
For every classical configuration of Table IV: is the Durango still a detection within TOL cells,
where is its local peak, and how much of its contrast survives.

Sentinel-1: no surveyed truth exists for the Illinois crop. A PROXY subset is scored: reference
detections whose power exceeds the CA-CFAR training-ring mean by >= 20 dB (strong, persistent,
likely man-made scatterers). Retention on that subset is reported per configuration and labelled a
proxy in the manuscript.

Pre-declared in FINDINGS.md (2026-10-29, "E4") BEFORE the first run. Rows tagged study = "jstars_E4".

    python scripts/eval_truth_jstars.py --scene gotcha|s1 [--limit N] [--dry-run]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import yaml
from scipy.ndimage import uniform_filter
from scipy.spatial import cKDTree

from radarcodec.baselines import CODECS
from radarcodec.experiments import log_run
from radarcodec.tasks.cfar import _to_centroids, ca_cfar

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments" / "runs.jsonl"
PFA, GUARD, TRAIN, TOL = 1e-4, 2, 8, 3
DURANGO_PEAK = (178, 833)   # 0-based, from AFRL's example (180, 834) 1-based, verified 29.3 dB contrast
DURANGO_DET = (179, 833)    # reference CFAR detection centroid at the Durango
CONTRAST_DB = 20.0          # S1 proxy subset threshold over CA-CFAR training-ring mean


def configs_for(domain):
    rows = [json.loads(line) for line in open(RUNS, encoding="utf-8")]
    seen = {}
    for r in rows:
        if (r.get("domain") == domain and r.get("mapping") == "v2-pctclip99.99" and r.get("study") is None
                and r["codec"] in ("baq", "jpeg2000", "hevc", "tfocus")):
            seen[(r["codec"], json.dumps(r["params"], sort_keys=True))] = r
    return list(seen.values())


def ring_mean(power):
    outer, inner = 2 * (GUARD + TRAIN) + 1, 2 * GUARD + 1
    n_o, n_i = outer ** 2, inner ** 2
    return (uniform_filter(power, outer, mode="reflect") * n_o - uniform_filter(power, inner, mode="reflect") * n_i) / (n_o - n_i)


def durango_truth_record():
    import scipy.io as sio
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_gotcha import N_PULSES, START_PULSE
    aux = sio.loadmat(ROOT / "data/gotcha_gmti/durangoChallenge_chan1_mis2_PH_auxSaveData.mat", squeeze_me=True, struct_as_record=False)["aux_SPIE"]
    t = sio.loadmat(ROOT / "data/gotcha_gmti/durangoChallenge_GPStruth.mat", squeeze_me=True, struct_as_record=False)["truth_SPIE"]
    t0 = float(aux.GPSTODfirstPulse) + (START_PULSE - 1) / float(aux.PRF)
    t1 = t0 + N_PULSES / float(aux.PRF)
    tt = np.asarray(t.GPSTODtruthTime, dtype=float) + float(t.GPStime_offset)
    sel = np.where((tt >= t0 - 1.0) & (tt <= t1 + 1.0))[0]
    return {"cpi_gps_tod": [round(t0, 3), round(t1, 3)], "gps_samples_in_or_adjacent": [int(i) for i in sel],
            "gps_speed_mps": [round(float(np.asarray(t.trgSpeed_mps)[i]), 3) for i in sel],
            "gps_pos_pcs_m": [[round(float(v), 2) for v in np.asarray(t.trgPos_PCS)[:, i]] for i in sel],
            "afrl_example_pixel_1based": {"doppler": 834, "range": 180}, "peak_0based": list(DURANGO_PEAK),
            "ref_detection_0based": list(DURANGO_DET)}


def durango_metrics(ref_img, hat_img, hat_pts):
    pr, ph = np.abs(ref_img) ** 2, np.abs(hat_img) ** 2
    r, c = DURANGO_PEAK
    w_ref, w_hat = pr[r - 3:r + 4, c - 3:c + 4], ph[r - 3:r + 4, c - 3:c + 4]
    pk = np.unravel_index(np.argmax(w_hat), w_hat.shape)
    off = (int(pk[0]) - 3, int(pk[1]) - 3)
    d, _ = cKDTree(hat_pts).query(np.array(DURANGO_DET), k=1) if len(hat_pts) else (np.inf, None)
    return {"detected_within_tol": bool(d <= TOL), "nearest_hat_detection_cells": round(float(d), 2),
            "peak_offset_cells": off,
            "contrast_ref_db": round(float(10 * np.log10(w_ref.max() / np.median(pr))), 2),
            "contrast_hat_db": round(float(10 * np.log10(w_hat.max() / np.median(ph))), 2),
            "peak_power_retention_db": round(float(10 * np.log10(w_hat.max() / w_ref.max())), 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["gotcha", "s1"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--study", default="jstars_E4", help="row tag; rescore_E4 for the corrected-scorer re-run")
    ap.add_argument("--subset-mode", default="topdecile", choices=["contrast20", "topdecile"],
                    help="S1 proxy subset: declared contrast20 (empty on this scene) or the corrected top-decile-power subset")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    sys.path.insert(0, str(ROOT / "scripts"))
    subset_desc = None

    if a.scene == "gotcha":
        from eval_gotcha import N_PULSES, PH_PATH, START_PULSE
        from radarcodec.data.gotcha import form_image, read_phase_history, tfocus_gotcha_codec
        truth = durango_truth_record()
        print("Durango truth record:", json.dumps(truth), flush=True)
        if not a.dry_run:
            (ROOT / "reports" / "e4_durango_truth.json").write_text(json.dumps(truth, indent=1))
        raw = read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)
        ref = form_image(raw)
        pref_g = np.abs(ref) ** 2
        ref_pts = _to_centroids(ca_cfar(pref_g, PFA, GUARD, TRAIN), pref_g)
        d_anchor = cKDTree(ref_pts).query(np.array(DURANGO_DET))[0]
        print(f"nearest reference peak to the Durango anchor: {d_anchor:.1f} cells", flush=True)
        domain, scene = "gotcha_gmti", "durango_chan1_mis2"

        def run(name, params):
            if name == "tfocus":
                p = {k: v for k, v in params.items() if k not in ("base", "mode")}
                hat_raw, rate = tfocus_gotcha_codec(raw, base=params["base"], **p)
            else:
                hat_raw, rate = CODECS[name](raw, **params)
            return rate, form_image(hat_raw)
        subset_idx = None
    else:
        from eval_focused import interior, load_crop
        from radarcodec.metrics.focus_rda import focus_stripmap
        raw, meta = load_crop()
        ref = interior(focus_stripmap(raw, meta))
        pr = np.abs(ref) ** 2
        ref_pts = _to_centroids(ca_cfar(pr, PFA, GUARD, TRAIN), pr)
        contrast = 10 * np.log10(pr[ref_pts[:, 0], ref_pts[:, 1]] / np.maximum(ring_mean(pr)[ref_pts[:, 0], ref_pts[:, 1]], 1e-30))
        if a.subset_mode == "contrast20":
            subset_idx = np.where(contrast >= CONTRAST_DB)[0]
            subset_desc = f">= {CONTRAST_DB} dB over CA-CFAR ring mean"
        else:
            # 2026-10-29 correction: the declared 20 dB-over-ring-mean threshold selected ZERO detections
            # (max contrast 19.8 dB; the 2-cell guard ring is inflated by a scatterer's own sidelobes).
            # Replacement subset = top decile of reference-detection power, the same "strong scatterer"
            # definition E3 declared before it ran. Change made after seeing the empty result; labelled.
            pw = pr[ref_pts[:, 0], ref_pts[:, 1]]
            subset_idx = np.where(pw >= np.quantile(pw, 0.90))[0]
            subset_desc = "top decile of reference-detection power (E3 'strong' definition)"
        print(f"S1 proxy subset ({subset_desc}): {len(subset_idx)} of {len(ref_pts)} reference detections; "
              f"contrast-over-ring-mean percentiles 50/90/99/max = {np.percentile(contrast, [50, 90, 99]).round(1).tolist()} / {contrast.max():.1f} dB", flush=True)
        domain, scene = "s1_focused", None

        def run(name, params):
            extra = {"meta": meta} if name == "tfocus" else {}
            hat_raw, rate = CODECS[name](raw, **params, **extra)
            return rate, interior(focus_stripmap(hat_raw, meta))

    todo = configs_for(domain)
    if a.limit:
        todo = todo[: a.limit]
    print(f"[{domain}] {len(todo)} configurations", flush=True)
    for prev in todo:
        name, params = prev["codec"], prev["params"]
        t0 = time.perf_counter()
        rate, hat = run(name, params)
        cs = time.perf_counter() - t0
        phat_t = np.abs(hat) ** 2
        hat_pts = _to_centroids(ca_cfar(phat_t, PFA, GUARD, TRAIN), phat_t)
        d_ref = cKDTree(hat_pts).query(ref_pts, k=1)[0] if len(hat_pts) else np.full(len(ref_pts), np.inf)
        pd_all = float(np.mean(d_ref <= TOL))
        row = {"study": a.study, "codec": name, "params": params, "domain": domain, "rate_bps": float(rate),
               "cfar_pd": round(pd_all, 5), "n_ref_detections": int(len(ref_pts)), "mapping": "v2-pctclip99.99",
               "codec_seconds": round(cs, 2)}
        if scene:
            row["scene"] = scene
        if a.scene == "gotcha":
            row["durango"] = durango_metrics(ref, hat, hat_pts)
            msg = f"durango det={row['durango']['detected_within_tol']} off={row['durango']['peak_offset_cells']} contrast {row['durango']['contrast_hat_db']:.1f}/{row['durango']['contrast_ref_db']:.1f} dB ret {row['durango']['peak_power_retention_db']:+.2f} dB"
        else:
            pd_sub = float(np.mean(d_ref[subset_idx] <= TOL))
            row["strong_subset"] = {"mode": a.subset_mode, "definition": subset_desc, "n_subset": int(len(subset_idx)),
                                    "pd_subset": round(pd_sub, 5) if len(subset_idx) else None}
            msg = f"strong-subset Pd {pd_sub:.3f} (n={len(subset_idx)})"
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        print(f"{name} {json.dumps(params, sort_keys=True)}: rate={rate:.3f} pd={pd_all:.3f} | {msg} | {cs:.0f}s", flush=True)
        del hat


if __name__ == "__main__":
    main()
