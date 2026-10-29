"""Score the post hoc focused-domain HEVC arms (QP 16/20/24, Illinois) with the full E1/E5 metric set (fidelity,
tolerance and Pfa sensitivity) so the tested minimum of the frontier carries the same robustness evidence as the
registered rows. Same reconstructions as rescore_E3; rows tagged study = "rescore_E0x".

    python scripts/eval_focused_hevc_sens.py [--dry-run]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import yaml

from eval_fidelity_jstars import fidelity, sensitivity
from radarcodec.baselines import CODECS
from radarcodec.experiments import log_run
from radarcodec.metrics.focus_rda import focus_stripmap

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    from eval_focused import interior, load_crop
    raw, meta = load_crop()
    ref_i = interior(focus_stripmap(raw, meta))
    for qp in (16, 20, 24):
        t0 = time.perf_counter()
        raw_hat, rate = CODECS["tfocus"](raw, meta=meta, base="hevc", mode="full", qp=qp)
        cs = time.perf_counter() - t0
        hat_i = interior(focus_stripmap(raw_hat, meta))
        sens = sensitivity(ref_i, hat_i)
        base = sens["pfa0.0001_tol3"]
        row = {"study": "rescore_E0x", "codec": "tfocus", "params": {"base": "hevc", "mode": "full", "qp": qp},
               "domain": "s1_focused", "rate_bps": float(rate), "cfar_pd": base["pd"], "cfar_false": base["n_false"],
               "n_ref_detections": base["n_ref"], "mapping": "v2-pctclip99.99", "codec_seconds": round(cs, 2),
               "fidelity_img": fidelity(ref_i, hat_i), "fidelity_raw": fidelity(raw, raw_hat), "sensitivity": sens}
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        ok = {k: (v["pd"] >= 0.9 and v["n_false"] <= 0.1 * v["n_ref"]) for k, v in sens.items()}
        print(f"focused HEVC QP{qp}: rate={rate:.3f} pd={base['pd']:.3f} false={base['n_false']} | sustains at: "
              f"{[k for k, v in ok.items() if v]} | SQNR {row['fidelity_img']['sqnr_db']:.2f} dB | {cs:.0f}s", flush=True)


if __name__ == "__main__":
    main()
