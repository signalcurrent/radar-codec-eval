"""Image-domain rate-vs-utility eval on an Umbra open-data SICD scene.

Commercial-traction artifact (see FINDINGS/Phase III notes): same two-sided
criterion and codecs as the SBIR study, applied to a commercial operator's
focused complex imagery. No focusing step — SICD is already an image; codecs
compress the complex pixels, CFAR scores detection agreement against the
uncompressed reference.

    python scripts/eval_umbra.py --sicd data/umbra/vancouver_SICD.nitf
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
from radarcodec.tasks.cfar import detection_agreement

TRIM = 128  # interior margin for scoring


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


def load_sicd_crop(path, size):
    from sarpy.io.complex.converter import open_complex

    reader = open_complex(str(path))
    rows, cols = reader.sicd_meta.ImageData.NumRows, reader.sicd_meta.ImageData.NumCols
    print(f"SICD {rows} x {cols}")
    r0 = max(0, (rows - size) // 2)
    c0 = max(0, (cols - size) // 2)
    data = reader[r0 : r0 + min(size, rows), c0 : c0 + min(size, cols)]
    return np.asarray(data, dtype=np.complex64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sicd", required=True)
    ap.add_argument("--scene", default="umbra_vancouver_prt")
    ap.add_argument("--size", type=int, default=4096)
    ap.add_argument("--config", default="configs/baseline_sweep.yaml")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})

    iq = load_sicd_crop(args.sicd, args.size)
    print(f"crop {iq.shape}, mean|z| {float(np.abs(iq).mean()):.1f}")
    ref = iq  # already focused

    sweep = cfg["codecs"] + [
        {"name": "jpeg2000", "ratio": [64, 128]},
        {"name": "hevc", "qp": [40, 44]},
        {"name": "baq", "bits": [1], "block": 128},
    ]
    for codec_cfg in sweep:
        for name, params in operating_points(codec_cfg):
            t0 = time.perf_counter()
            iq_hat, rate = CODECS[name](iq, **params)
            codec_s = time.perf_counter() - t0
            det = detection_agreement(
                ref[TRIM:-TRIM, TRIM:-TRIM], iq_hat[TRIM:-TRIM, TRIM:-TRIM], **cfar_cfg
            )
            row = log_run(cfg["out"], cfg, {
                "codec": name, "params": params, "domain": "umbra",
                "scene": args.scene, "rate_bps": float(rate),
                "cfar_pd": det["pd"], "cfar_false": det["n_false"],
                "n_ref_detections": det["n_ref"],
                "codec_seconds": round(codec_s, 2),
                "mapping": "v2-pctclip99.99",
            })
            lim = 0.1 * det["n_ref"]
            ok = det["pd"] >= 0.9 and det["n_false"] <= lim
            print(f"{name} {params}: rate={rate:.2f} bps pd={det['pd']:.3f} "
                  f"false={det['n_false']} {'SUSTAINS' if ok else '-'}")


if __name__ == "__main__":
    main()
