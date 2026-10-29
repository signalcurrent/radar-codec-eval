"""E10 (pre-declared in FINDINGS.md, 2026-10-29): mapping confound on the concentration result and on the Umbra
frontier. (a) Three-anchor phantom counts on the Illinois no-codec transform-domain mapping round trip;
(b) clip-free (min/max) reruns of focused-domain HEVC QP16/20/24 on Illinois with three-anchor counts and
two-sided scores; (c) clip-free reruns of Umbra HEVC QP12 and JPEG2000 r4/r8/r16. Rows tagged study = "ctrl_E10".

    python scripts/eval_mapping_confound_jstars.py [--dry-run]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np
import yaml

from eval_clip_control_jstars import map_round_trip
from eval_ringing_ablation_jstars import phantom_geometry
from radarcodec.baselines import CODECS
from radarcodec.baselines.transform_codec import forward, inverse
from radarcodec.experiments import log_run
from radarcodec.metrics.focus_rda import focus_stripmap
from radarcodec.tasks.cfar import detection_agreement

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})

    def emit(row, msg):
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        print(msg, flush=True)

    # ---------------- Illinois
    from eval_focused import interior, load_crop
    raw, meta = load_crop()
    ref_i = interior(focus_stripmap(raw, meta))
    # (a) no-codec transform-domain round trip, three-anchor counts
    y = forward(raw, meta, mode="full")
    y_hat, _ = map_round_trip(y)
    hat_i = interior(focus_stripmap(inverse(y_hat, meta, mode="full"), meta))
    g = phantom_geometry(ref_i, hat_i)
    emit({"study": "ctrl_E10", "codec": "mapping_only", "arm": "mapping_only", "params": {"domain_applied": "transform_full", "clip_q": 99.99},
          "domain": "s1_focused", "rate_bps": 32.0, "cfar_pd": g["pd"], "cfar_false": g["n_phantom"], "n_ref_detections": g["n_ref"],
          "mapping": "v2-pctclip99.99", "ringing": g},
         f"S1 mapping-only transform round trip: pd={g['pd']:.4f} phantoms={g['n_phantom']} near strong/weak/random = "
         f"{g['e3b']['near_strong']}/{g['e3b']['near_weak']}/{g['e3b']['near_random']}")
    del y, y_hat, hat_i
    # (b) clip-free focused HEVC
    for qp in (16, 20, 24):
        t0 = time.perf_counter()
        raw_hat, rate = CODECS["tfocus"](raw, meta=meta, base="hevc", mode="full", qp=qp, clip_q=100.0)
        hat_i = interior(focus_stripmap(raw_hat, meta))
        g = phantom_geometry(ref_i, hat_i)
        emit({"study": "ctrl_E10", "codec": "tfocus", "arm": "hevc", "params": {"base": "hevc", "mode": "full", "qp": qp, "clip_q": 100.0},
              "domain": "s1_focused", "rate_bps": float(rate), "cfar_pd": g["pd"], "cfar_false": g["n_phantom"],
              "n_ref_detections": g["n_ref"], "mapping": "minmax", "codec_seconds": round(time.perf_counter() - t0, 1), "ringing": g},
             f"S1 focused HEVC QP{qp} clip-free: rate={rate:.3f} pd={g['pd']:.3f} phantoms={g['n_phantom']} near s/w/r = "
             f"{g['e3b']['near_strong']}/{g['e3b']['near_weak']}/{g['e3b']['near_random']}")
        del raw_hat, hat_i
    del raw, ref_i

    # ---------------- Umbra clip-free
    from eval_umbra import TRIM, load_sicd_crop
    iq = load_sicd_crop(ROOT / "data" / "umbra" / "vancouver_SICD.nitf", 4096)
    ref = iq[TRIM:-TRIM, TRIM:-TRIM]
    for name, params in (("hevc", {"qp": 12}), ("jpeg2000", {"ratio": 4}), ("jpeg2000", {"ratio": 8}), ("jpeg2000", {"ratio": 16})):
        t0 = time.perf_counter()
        iq_hat, rate = CODECS[name](iq, **params, clip_q=100.0)
        det = detection_agreement(ref, iq_hat[TRIM:-TRIM, TRIM:-TRIM], **cfar_cfg)
        ok = det["pd"] >= 0.9 and det["n_false"] <= 0.1 * det["n_ref"]
        emit({"study": "ctrl_E10", "codec": name, "params": {**params, "clip_q": 100.0}, "domain": "umbra", "scene": "umbra_vancouver_prt",
              "rate_bps": float(rate), "cfar_pd": det["pd"], "cfar_false": det["n_false"], "n_ref_detections": det["n_ref"],
              "mapping": "minmax", "codec_seconds": round(time.perf_counter() - t0, 1)},
             f"Umbra {name} {params} clip-free: rate={rate:.3f} pd={det['pd']:.3f} false={det['n_false']} {'SUSTAINS' if ok else '-'}")


if __name__ == "__main__":
    main()
