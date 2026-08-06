"""Focused-domain CFAR eval: compress RAW -> decompress -> FOCUS -> detect.

This is the operationally meaningful pipeline: detection loss measured here is
loss that survives SAR processing, answering the "you don't detect on raw
echoes" objection. Uses one stripmap chunk (RDA-focusable); the codec sees the
same raw crop every time, and detections on the focused uncompressed crop are
ground truth.

    python scripts/eval_focused.py [--config configs/baseline_sweep.yaml]
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import yaml

from radarcodec.baselines import CODECS
from radarcodec.experiments import log_run
from radarcodec.metrics.focus_rda import focus_stripmap
from radarcodec.tasks.cfar import detection_agreement

CACHE = Path("data/s1_sm/chunk_crop.npz")
SAFE_GLOB = "data/s1_sm/*.SAFE"
AZ, RG = 4096, 8192  # raw crop size (echoes x samples)
TRIM = 512  # interior margin for detection scoring (edge/aperture effects)


def load_crop():
    if CACHE.exists():
        d = np.load(CACHE, allow_pickle=True)
        return d["iq"], d["meta"].item()
    from radarcodec.data.sentinel1 import read_l0_bursts

    safe = sorted(Path().glob(SAFE_GLOB))[0]
    _, iq, meta = next(read_l0_bursts(safe, max_chunks=1))
    r0, c0 = (iq.shape[0] - AZ) // 2, (iq.shape[1] - RG) // 2
    crop = np.ascontiguousarray(iq[r0 : r0 + AZ, c0 : c0 + RG])
    del iq
    np.savez_compressed(CACHE, iq=crop, meta=meta)
    return crop, meta


def interior(img):
    return img[TRIM:-TRIM, TRIM:-TRIM]


def operating_points(codec_cfg):
    import itertools

    name = codec_cfg["name"]
    fixed = {k: v for k, v in codec_cfg.items() if k != "name" and not isinstance(v, list)}
    swept = {k: v for k, v in codec_cfg.items() if isinstance(v, list)}
    if not swept:
        yield name, fixed
        return
    keys, vals = zip(*swept.items())
    for combo in itertools.product(*vals):
        yield name, {**fixed, **dict(zip(keys, combo))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/baseline_sweep.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})

    raw, meta = load_crop()
    print(f"raw crop {raw.shape}, focusing reference...")
    ref = focus_stripmap(raw, meta)

    for codec_cfg in cfg["codecs"]:
        for name, params in operating_points(codec_cfg):
            # wall time for encode+decode combined — crude (Python vs native
            # varies by orders of magnitude) but answers "why not just HEVC?"
            # with the onboard-compute argument Phase II will demand properly
            extra = {"meta": meta} if name == "tfocus" else {}  # chirp/timing side info, not a swept param
            t0 = time.perf_counter()
            raw_hat, rate = CODECS[name](raw, **params, **extra)
            codec_s = time.perf_counter() - t0
            img_hat = focus_stripmap(raw_hat, meta)
            del raw_hat
            det = detection_agreement(interior(ref), interior(img_hat), **cfar_cfg)
            del img_hat
            row = log_run(cfg["out"], cfg, {
                "codec": name, "params": params, "domain": "s1_focused",
                "rate_bps": float(rate), "cfar_pd": det["pd"],
                "cfar_false": det["n_false"], "n_ref_detections": det["n_ref"],
                "codec_seconds": round(codec_s, 2),
                "msamples_per_s": round(raw.size / codec_s / 1e6, 2),
            })
            print(f"{name} {params}: rate={rate:.2f} bps  pd={det['pd']:.3f}  "
                  f"false={det['n_false']}  codec_s={codec_s:.1f}")


if __name__ == "__main__":
    main()
