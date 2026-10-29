"""E0: re-score the 30 legacy learned-codec rows under the corrected peak-v2 scorer, from their archived
checkpoints (all present in experiments/checkpoints). One new row per legacy row, study = "rescore_learned",
carrying the legacy row's timestamp for pairing. Run under the torch venv:

    .venv312/Scripts/python.exe scripts/rescore_learned_jstars.py [--dry-run]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import yaml

from radarcodec.experiments import log_run
from radarcodec.tasks.cfar import _to_centroids, ca_cfar, detection_agreement

ROOT = Path(__file__).resolve().parents[1]


def match_pts(ref_pts, hat_pts, tol=3):
    from scipy.spatial import cKDTree
    if len(ref_pts) == 0:
        return {"pd": float("nan"), "n_false": int(len(hat_pts)), "n_ref": 0}
    hits = int(np.sum(cKDTree(hat_pts).query(ref_pts, k=1)[0] <= tol)) if len(hat_pts) else 0
    matched = int(np.sum(cKDTree(ref_pts).query(hat_pts, k=1)[0] <= tol)) if len(hat_pts) else 0
    return {"pd": hits / len(ref_pts), "n_false": int(len(hat_pts) - matched), "n_ref": int(len(ref_pts))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})
    rows = [json.loads(l) for l in open(ROOT / "experiments" / "runs.jsonl", encoding="utf-8")]
    legacy = [r for r in rows if str(r["codec"]).startswith("neural") and r.get("study") is None]
    print(len(legacy), "legacy learned rows", flush=True)
    sys.path.insert(0, str(ROOT / "scripts"))

    # Gotcha context
    from eval_gotcha import N_PULSES, PH_PATH, START_PULSE
    from radarcodec.data.gotcha import form_image, read_phase_history
    ph = read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)
    ref_g = form_image(ph)
    p_ref_g = np.abs(ref_g) ** 2
    ref_pts_g = _to_centroids(ca_cfar(p_ref_g, 1e-4, 2, 8), p_ref_g)
    s1_ctx = None

    for prev in legacy:
        params, dom = prev["params"], prev.get("domain")
        ck = str(params.get("checkpoint", "")).replace("\\", "/")
        t0 = time.perf_counter()
        try:
            if prev["codec"] == "neural" and dom == "gotcha_gmti":
                from radarcodec.baselines.neural_gotcha import neural_gotcha_codec
                ph_hat, rate = neural_gotcha_codec(ph, checkpoint=ck, patch=64)
                det = detection_agreement(ref_g, form_image(ph_hat), **cfar_cfg)
            elif prev["codec"] == "neural_stat":
                from radarcodec.baselines.neural_gotcha_stat import neural_gotcha_stat_codec
                from radarcodec.tasks import diff_cfar
                that, rate = neural_gotcha_stat_codec(ph, checkpoint=ck, patch=64)
                alpha = diff_cfar.cfar_alpha(1e-4)
                that = np.asarray(that, dtype=np.float64)
                hat_pts = _to_centroids(that > alpha, that)  # peaks of the decoded statistic
                det = match_pts(ref_pts_g, hat_pts)
            elif prev["codec"] == "neural" and dom == "s1_focused":
                if s1_ctx is None:
                    from eval_focused import interior, load_crop
                    from radarcodec.metrics.focus_rda import focus_stripmap
                    raw, meta = load_crop()
                    s1_ctx = (raw, meta, interior(focus_stripmap(raw, meta)), interior, focus_stripmap)
                raw, meta, ref_i, interior, focus_stripmap = s1_ctx
                from radarcodec.baselines import CODECS
                p = {k: v for k, v in params.items() if k != "checkpoint"}
                raw_hat, rate = CODECS["neural"](raw, meta=meta, checkpoint=ck, **p)
                det = detection_agreement(ref_i, interior(focus_stripmap(raw_hat, meta)), **cfar_cfg)
            else:
                print("skip", prev["codec"], dom, flush=True)
                continue
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {prev['codec']} {ck}: {type(e).__name__}: {e}", flush=True)
            continue
        row = {"study": "rescore_learned", "codec": prev["codec"], "params": params, "domain": dom,
               "rate_bps": float(rate), "cfar_pd": det["pd"], "cfar_false": det["n_false"],
               "n_ref_detections": det["n_ref"], "mapping": prev.get("mapping"), "legacy_ts": prev["ts"],
               "legacy_pd": prev["cfar_pd"], "legacy_false": prev.get("cfar_false"),
               "codec_seconds": round(time.perf_counter() - t0, 1)}
        if prev.get("scene"):
            row["scene"] = prev["scene"]
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        print(f"{prev['codec']} {Path(ck).name}: rate={rate:.3f} pd {prev['cfar_pd']:.3f}->{det['pd']:.3f} "
              f"false {prev.get('cfar_false')}->{det['n_false']} n_ref {det['n_ref']}", flush=True)


if __name__ == "__main__":
    main()
