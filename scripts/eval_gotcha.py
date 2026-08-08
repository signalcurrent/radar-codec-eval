"""Classical-codec rate-vs-detection sweep on AFRL's Gotcha GMTI phase history.

Tier 1 of the AFRL game plan: same methodology as eval_focused.py (compress
raw -> decompress -> form image -> CA-CFAR detection agreement), same codec
grid as configs/baseline_sweep.yaml, applied to genuinely UNENCODED,
government-provided, airborne phase history for the first time in this
study -- removing the Sentinel-1 re-compression caveat entirely for this
result. Public Release # 88 ABW-09-0967 (data); # 88 ABW-09-1031 (paper).

    python scripts/eval_gotcha.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import yaml

from radarcodec.baselines import CODECS
from radarcodec.data.gotcha import form_image, read_phase_history, tfocus_gotcha_codec
from radarcodec.experiments import log_run
from radarcodec.tasks.cfar import detection_agreement

PH_PATH = "data/gotcha_gmti/durangoChallenge_chan1_mis2_PH"
START_PULSE, N_PULSES = 5585, 1864  # AFRL's own worked example, ingest-verified 2026-08-08

# Transform-domain arm: same base codecs/grids as the Illinois tfocus study
# (raw-domain BAQ is the classical raw-echo baseline; JPEG2000/HEVC are run
# both raw and in the focused domain, matching configs/baseline_sweep.yaml's
# ratio/QP grid for direct comparability)
TFOCUS_CODECS = [
    {"name": "jpeg2000", "ratio": [4, 8, 16, 32]},
    {"name": "hevc", "qp": [12, 20, 28, 36]},
]


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
    cfg = yaml.safe_load(open("configs/baseline_sweep.yaml"))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})

    print(f"reading {PH_PATH} (pulses {START_PULSE}:{START_PULSE+N_PULSES})...")
    ph = read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)
    print(f"phase history {ph.shape}, forming reference image...")
    ref = form_image(ph)

    print("\n--- raw phase-history domain (Tier 1, already run) ---")
    for codec_cfg in cfg["codecs"]:
        for name, params in operating_points(codec_cfg):
            t0 = time.perf_counter()
            ph_hat, rate = CODECS[name](ph, **params)
            codec_s = time.perf_counter() - t0
            img_hat = form_image(ph_hat)
            det = detection_agreement(ref, img_hat, **cfar_cfg)
            row = log_run(cfg["out"], cfg, {
                "codec": name, "params": params, "domain": "gotcha_gmti",
                "scene": "durango_chan1_mis2",
                "rate_bps": float(rate), "cfar_pd": det["pd"],
                "cfar_false": det["n_false"], "n_ref_detections": det["n_ref"],
                "codec_seconds": round(codec_s, 2),
                "msamples_per_s": round(ph.size / codec_s / 1e6, 2),
                "mapping": "v2-pctclip99.99",
                "data_public_release": "88 ABW-09-0967",
            })
            print(f"{name} {params}: rate={rate:.2f} bps  pd={det['pd']:.3f}  "
                  f"false={det['n_false']}  n_ref={det['n_ref']}  codec_s={codec_s:.1f}")

    print("\n--- focused (range-Doppler) domain, transform arm ---")
    for codec_cfg in TFOCUS_CODECS:
        for base_name, base_params in operating_points(codec_cfg):
            t0 = time.perf_counter()
            ph_hat, rate = tfocus_gotcha_codec(ph, base=base_name, **base_params)
            codec_s = time.perf_counter() - t0
            img_hat = form_image(ph_hat)
            det = detection_agreement(ref, img_hat, **cfar_cfg)
            params = {"base": base_name, "mode": "focused", **base_params}
            row = log_run(cfg["out"], cfg, {
                "codec": "tfocus", "params": params, "domain": "gotcha_gmti",
                "scene": "durango_chan1_mis2",
                "rate_bps": float(rate), "cfar_pd": det["pd"],
                "cfar_false": det["n_false"], "n_ref_detections": det["n_ref"],
                "codec_seconds": round(codec_s, 2),
                "msamples_per_s": round(ph.size / codec_s / 1e6, 2),
                "mapping": "v2-pctclip99.99",
                "data_public_release": "88 ABW-09-0967",
            })
            print(f"tfocus-{base_name} {base_params}: rate={rate:.2f} bps  pd={det['pd']:.3f}  "
                  f"false={det['n_false']}  n_ref={det['n_ref']}  codec_s={codec_s:.1f}")


if __name__ == "__main__":
    main()
