"""ATR-utility-vs-rate: compress MSTAR test chips, evaluate the FROZEN classifier.

The classifier was trained once on uncompressed 17-deg chips and is never
fine-tuned on compressed data; accuracy on codec-reconstructed 15-deg chips at
each rate is the utility number. Note the domain difference from the Sentinel-1
eval: MSTAR chips are focused image-domain complex data, so this curve measures
image-domain utility while the CFAR curve measures raw-echo-domain utility —
report both, conflate neither.

Runs in the torch env:  .venv312/Scripts/python.exe scripts/eval_atr.py
"""

import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import yaml

from radarcodec.baselines import CODECS
from radarcodec.experiments import log_run
from radarcodec.tasks.atr import evaluate_frozen


def operating_points(codec_cfg):
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
    ap.add_argument("--chips", default="data/mstar_npz/test.npz")
    ap.add_argument("--max-chips", type=int, default=300)
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))

    data = np.load(args.chips)
    rng = np.random.default_rng(cfg["seed"])
    idx = rng.permutation(len(data["iq"]))[: args.max_chips]
    chips, labels = data["iq"][idx], data["labels"][idx]
    ckpt = cfg["tasks"]["atr"]["checkpoint"]

    acc0 = evaluate_frozen(chips, labels, ckpt)
    row = log_run(cfg["out"], cfg, {"codec": "uncompressed", "params": {}, "domain": "mstar",
                                    "rate_bps": 64.0, "atr_acc": acc0, "n_chips": len(chips)})
    print(f"uncompressed: acc={acc0:.3f} (frozen-model ceiling)")

    for codec_cfg in cfg["codecs"]:
        for name, params in operating_points(codec_cfg):
            recs, rates = [], []
            for iq in chips:
                iq_hat, rate = CODECS[name](iq, **params)
                recs.append(iq_hat)
                rates.append(rate)
            acc = evaluate_frozen(np.stack(recs), labels, ckpt)
            row = log_run(cfg["out"], cfg, {"codec": name, "params": params, "domain": "mstar",
                                            "rate_bps": float(np.mean(rates)), "atr_acc": acc,
                                            "n_chips": len(chips)})
            print(f"{name} {params}: rate={row['rate_bps']:.2f} bps  atr_acc={acc:.3f}")


if __name__ == "__main__":
    main()
