"""E0 sub-item: re-score the FDBAQ lattice-artifact test (Section V-A; Asiyabi adaptation) under the corrected
peak-v2 scorer. The original eight rows (BAQ 2/3/4/6 bits, with and without adaptation) were recorded in the
notebook only; these are logged, study = "rescore_lattice".

    python scripts/eval_lattice_rescore.py [--dry-run]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import yaml

from radarcodec.baselines import CODECS
from radarcodec.data.adaptation import adapt
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
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_focused import interior, load_crop
    raw, meta = load_crop()
    out = {}
    for adapted in (False, True):
        x = adapt(raw, rng=np.random.default_rng(1337)) if adapted else raw
        ref_i = interior(focus_stripmap(x, meta))  # the reference is the (adapted) uncompressed input, as in the original test
        for bits in (2, 3, 4, 6):
            t0 = time.perf_counter()
            x_hat, rate = CODECS["baq"](x, bits=bits, block=128)
            hat_i = interior(focus_stripmap(x_hat, meta))
            det = detection_agreement(ref_i, hat_i, **cfar_cfg)
            row = {"study": "rescore_lattice", "codec": "baq", "params": {"bits": bits, "block": 128, "adapted": adapted},
                   "domain": "s1_focused", "rate_bps": float(rate), "cfar_pd": det["pd"], "cfar_false": det["n_false"],
                   "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "codec_seconds": round(time.perf_counter() - t0, 1)}
            if not a.dry_run:
                log_run(cfg["out"], cfg, row)
            out[(adapted, bits)] = det
            print(f"adapted={adapted} BAQ {bits}-bit: rate={rate:.3f} pd={det['pd']:.4f} false={det['n_false']} n_ref={det['n_ref']}", flush=True)
    print("\ndelta (adapted - plain):")
    for bits in (2, 3, 4, 6):
        p, q = out[(False, bits)], out[(True, bits)]
        print(f"  {bits}-bit: dPd={q['pd'] - p['pd']:+.4f} dFalse={q['n_false'] - p['n_false']:+d} ({(q['n_false'] - p['n_false']) / max(p['n_false'], 1) * 100:+.1f}%)")


if __name__ == "__main__":
    main()
