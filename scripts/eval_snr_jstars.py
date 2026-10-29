"""JSTARS revision E2: SNR sensitivity of the classical frontier. Adds seeded complex white Gaussian
noise to the RAW input at a declared added-noise-to-signal ratio, re-forms the uncompressed reference
from the SAME noisy input (criterion at matched threshold on the same scene), and re-runs every
classical configuration of the paper's tables. Pre-declared in FINDINGS.md (2026-10-29, "E2")
BEFORE the first run. Rows tagged study = "jstars_E2".

    python scripts/eval_snr_jstars.py --scene s1|gotcha [--levels -9,-6,-3,0] [--limit N] [--dry-run]
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
from radarcodec.experiments import log_run
from radarcodec.tasks.cfar import detection_agreement

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments" / "runs.jsonl"
SEED = 1337


def configs_for(domain):
    rows = [json.loads(line) for line in open(RUNS, encoding="utf-8")]
    seen = {}
    for r in rows:
        if (r.get("domain") == domain and r.get("mapping") == "v2-pctclip99.99" and r.get("study") is None
                and r["codec"] in ("baq", "jpeg2000", "hevc", "tfocus")):
            seen[(r["codec"], json.dumps(r["params"], sort_keys=True))] = r
    return list(seen.values())


def add_noise(x, nsr_db, level_index):
    """Complex white Gaussian noise with power = mean|x|^2 * 10^(nsr_db/10); seeded per level."""
    rng = np.random.default_rng(SEED + 1000 * level_index)
    sigma = np.sqrt(np.mean(np.abs(x) ** 2) * 10 ** (nsr_db / 10) / 2.0)
    n = rng.standard_normal(x.shape, dtype=np.float32) + 1j * rng.standard_normal(x.shape, dtype=np.float32)
    return (x + sigma * n).astype(np.complex64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["s1", "gotcha"])
    ap.add_argument("--levels", default="-9,-6,-3,0")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--study", default="jstars_E2", help="row tag; rescore_E2 for the corrected-scorer re-run")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})
    levels = [float(v) for v in a.levels.split(",")]
    sys.path.insert(0, str(ROOT / "scripts"))

    if a.scene == "s1":
        from eval_focused import interior, load_crop
        from radarcodec.metrics.focus_rda import focus_stripmap
        raw, meta = load_crop()
        domain, scene = "s1_focused", None
        focus = lambda x: focus_stripmap(x, meta)
        trim = interior
        extra = lambda name: {"meta": meta} if name == "tfocus" else {}
        codec = lambda name, params, x: CODECS[name](x, **params, **extra(name))
    else:
        from eval_gotcha import N_PULSES, PH_PATH, START_PULSE
        from radarcodec.data.gotcha import form_image, read_phase_history, tfocus_gotcha_codec
        raw = read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)
        domain, scene = "gotcha_gmti", "durango_chan1_mis2"
        focus = form_image
        trim = lambda x: x

        def codec(name, params, x):
            if name == "tfocus":
                p = {k: v for k, v in params.items() if k not in ("base", "mode")}
                return tfocus_gotcha_codec(x, base=params["base"], **p)
            return CODECS[name](x, **params)

    todo = configs_for(domain)
    if a.limit:
        todo = todo[: a.limit]
    print(f"[{domain}] {len(todo)} configurations x {len(levels)} noise levels", flush=True)
    for li, nsr in enumerate(levels):
        noisy = add_noise(raw, nsr, li)
        ref = trim(focus(noisy))
        # reference row: how many detections survive on the uncompressed noisy scene
        det0 = detection_agreement(ref, ref, **cfar_cfg)
        print(f"--- added noise {nsr:+.0f} dB rel. signal: n_ref = {det0['n_ref']}", flush=True)
        if not a.dry_run:
            log_run(cfg["out"], cfg, {"study": a.study, "codec": "uncompressed", "params": {}, "domain": domain,
                                      **({"scene": scene} if scene else {}), "added_nsr_db": nsr, "rate_bps": 16.0,
                                      "cfar_pd": 1.0, "cfar_false": 0, "n_ref_detections": det0["n_ref"],
                                      "mapping": "v2-pctclip99.99", "noise_seed": SEED + 1000 * li})
        for prev in todo:
            name, params = prev["codec"], prev["params"]
            t0 = time.perf_counter()
            hat_raw, rate = codec(name, params, noisy)
            cs = time.perf_counter() - t0
            hat = trim(focus(hat_raw))
            del hat_raw
            det = detection_agreement(ref, hat, **cfar_cfg)
            del hat
            row = {"study": a.study, "codec": name, "params": params, "domain": domain,
                   "added_nsr_db": nsr, "noise_seed": SEED + 1000 * li,
                   "rate_bps": float(rate), "cfar_pd": det["pd"], "cfar_false": det["n_false"],
                   "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "codec_seconds": round(cs, 2)}
            if scene:
                row["scene"] = scene
            if not a.dry_run:
                log_run(cfg["out"], cfg, row)
            ok = det["pd"] >= 0.9 and det["n_false"] <= 0.1 * det["n_ref"]
            print(f"{name} {json.dumps(params, sort_keys=True)}: rate={rate:.3f} pd={det['pd']:.3f} "
                  f"false={det['n_false']} {'SUSTAINS' if ok else '-'} | {cs:.0f}s", flush=True)


if __name__ == "__main__":
    main()
