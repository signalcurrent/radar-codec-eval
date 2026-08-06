"""Evaluation pipeline: patches -> codec -> radar metrics + frozen-task metrics.

Runs every codec operating point in the config over the validation patches and
appends one JSON line per (codec, operating point) to experiments/runs.jsonl.
Works for classical baselines today; a learned codec plugs in as one more
codec name in a later phase.

    python -m radarcodec.eval --config configs/baseline_sweep.yaml
"""

import argparse
import itertools

import numpy as np
import yaml

from radarcodec.baselines import CODECS
from radarcodec.experiments import log_run
from radarcodec.metrics import irw_pslr, mse, phase_rmse
from radarcodec.tasks.cfar import detection_agreement


def _operating_points(codec_cfg):
    """Expand list-valued params into one dict per operating point."""
    name = codec_cfg["name"]
    fixed = {k: v for k, v in codec_cfg.items() if k != "name" and not isinstance(v, list)}
    swept = {k: v for k, v in codec_cfg.items() if isinstance(v, list)}
    if not swept:
        yield name, fixed
        return
    keys, vals = zip(*swept.items())
    for combo in itertools.product(*vals):
        yield name, {**fixed, **dict(zip(keys, combo))}


def evaluate_codec(patches, codec_fn, params, cfar_cfg):
    rates, mses, phases, pds, falses = [], [], [], [], []
    for iq in patches:
        iq_hat, rate = codec_fn(iq, **params)
        rates.append(rate)
        mses.append(mse(iq, iq_hat))
        phases.append(phase_rmse(iq, iq_hat))
        det = detection_agreement(iq, iq_hat, **cfar_cfg)
        if det["n_ref"] > 0:
            pds.append(det["pd"])
            falses.append(det["n_false"])
    return {
        "rate_bps": float(np.mean(rates)),
        "mse": float(np.mean(mses)),
        "phase_rmse": float(np.nanmean(phases)),
        "cfar_pd": float(np.mean(pds)) if pds else float("nan"),
        "cfar_false_per_patch": float(np.mean(falses)) if falses else float("nan"),
        "n_patches": len(patches),
        "n_patches_with_detections": len(pds),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--max-patches", type=int, default=64)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))

    rng = np.random.default_rng(cfg["seed"])
    data = np.load(cfg["patches"].replace("train.npz", "val.npz"))["iq"]
    idx = rng.permutation(len(data))[: args.max_patches]
    patches = data[idx]
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})

    for codec_cfg in cfg["codecs"]:
        for name, params in _operating_points(codec_cfg):
            print(f"== {name} {params}")
            result = evaluate_codec(patches, CODECS[name], params, cfar_cfg)
            row = log_run(cfg["out"], cfg, {"codec": name, "params": params, **result})
            print(f"   rate={row['rate_bps']:.2f} bps  mse={row['mse']:.3e}  "
                  f"phase_rmse={row['phase_rmse']:.3f}  pd={row['cfar_pd']:.3f}")


if __name__ == "__main__":
    main()
