"""JSTARS revision E1 + E5: fidelity metrics and matching/CFAR sensitivity on every classical
configuration in the paper's tables, recomputed deterministically. Pre-declared in FINDINGS.md
(2026-10-29, "JSTARS REVISION") BEFORE this script first ran. Appends one row per configuration to
experiments/runs.jsonl with study = "jstars_E1E5".

    python scripts/eval_fidelity_jstars.py --scene s1|gotcha|umbra [--limit N] [--dry-run]
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
from radarcodec.metrics.radar_metrics import phase_rmse
from radarcodec.tasks.cfar import _to_centroids, ca_cfar

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments" / "runs.jsonl"
TOLS = (1, 2, 3, 5)
PFAS = (1e-3, 1e-4, 1e-5)
GUARD, TRAIN = 2, 8


def sqnr_db(x, xh):
    return float(10 * np.log10(np.sum(np.abs(x) ** 2) / max(np.sum(np.abs(x - xh) ** 2), 1e-30)))


def psnr_mag_db(x, xh):
    a, b = np.abs(x), np.abs(xh)
    return float(20 * np.log10(a.max()) - 10 * np.log10(max(np.mean((a - b) ** 2), 1e-30)))


def fidelity(x, xh):
    return {
        "sqnr_db": round(sqnr_db(x, xh), 3),
        "psnr_mag_db": round(psnr_mag_db(x, xh), 3),
        "mse": float(np.mean(np.abs(x - xh) ** 2)),
        "phase_rmse": round(phase_rmse(x, xh), 5),
    }


def match(ref_pts, hat_pts, tol):
    from scipy.spatial import cKDTree

    if len(ref_pts) == 0:
        return {"pd": float("nan"), "n_false": int(len(hat_pts)), "n_ref": 0}
    hits = int(np.sum(cKDTree(hat_pts).query(ref_pts, k=1)[0] <= tol)) if len(hat_pts) else 0
    matched = int(np.sum(cKDTree(ref_pts).query(hat_pts, k=1)[0] <= tol)) if len(hat_pts) else 0
    return {"pd": hits / len(ref_pts), "n_false": int(len(hat_pts) - matched), "n_ref": int(len(ref_pts))}


def sensitivity(ref_img, hat_img):
    """E5: detections at each Pfa (reference recomputed per Pfa), matched at each tol."""
    pref, phat = np.abs(ref_img) ** 2, np.abs(hat_img) ** 2
    out = {}
    for pfa in PFAS:
        r = _to_centroids(ca_cfar(pref, pfa, GUARD, TRAIN), pref)
        h = _to_centroids(ca_cfar(phat, pfa, GUARD, TRAIN), phat)
        tols = TOLS if pfa == 1e-4 else (3,)
        for tol in tols:
            m = match(r, h, tol)
            out[f"pfa{pfa:g}_tol{tol}"] = {"pd": round(m["pd"], 5), "n_false": m["n_false"], "n_ref": m["n_ref"]}
    return out


def logged_rows():
    rows = [json.loads(line) for line in open(RUNS, encoding="utf-8")]
    return [
        r for r in rows
        if r.get("mapping") == "v2-pctclip99.99" and r["codec"] in ("baq", "jpeg2000", "hevc", "tfocus")
        and r.get("study") is None
    ]


def configs_for(domain):
    seen = {}
    for r in logged_rows():
        if r.get("domain") == domain:
            seen[(r["codec"], json.dumps(r["params"], sort_keys=True))] = r
    return list(seen.values())


def scene_s1():
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_focused import interior, load_crop
    from radarcodec.metrics.focus_rda import focus_stripmap

    raw, meta = load_crop()
    ref = focus_stripmap(raw, meta)

    def run(name, params):
        extra = {"meta": meta} if name == "tfocus" else {}
        t0 = time.perf_counter()
        raw_hat, rate = CODECS[name](raw, **params, **extra)
        cs = time.perf_counter() - t0
        img_hat = focus_stripmap(raw_hat, meta)
        return rate, cs, interior(ref), interior(img_hat), raw, raw_hat

    return "s1_focused", None, run


def scene_gotcha():
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_gotcha import N_PULSES, PH_PATH, START_PULSE
    from radarcodec.data.gotcha import form_image, read_phase_history, tfocus_gotcha_codec

    ph = read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)
    ref = form_image(ph)

    def run(name, params):
        t0 = time.perf_counter()
        if name == "tfocus":
            p = {k: v for k, v in params.items() if k not in ("base", "mode")}
            ph_hat, rate = tfocus_gotcha_codec(ph, base=params["base"], **p)
        else:
            ph_hat, rate = CODECS[name](ph, **params)
        cs = time.perf_counter() - t0
        return rate, cs, ref, form_image(ph_hat), ph, ph_hat

    return "gotcha_gmti", "durango_chan1_mis2", run


def scene_umbra():
    sys.path.insert(0, str(ROOT / "scripts"))
    from eval_umbra import TRIM, load_sicd_crop

    iq = load_sicd_crop(ROOT / "data" / "umbra" / "vancouver_SICD.nitf", 4096)

    def run(name, params):
        t0 = time.perf_counter()
        iq_hat, rate = CODECS[name](iq, **params)
        cs = time.perf_counter() - t0
        return rate, cs, iq[TRIM:-TRIM, TRIM:-TRIM], iq_hat[TRIM:-TRIM, TRIM:-TRIM], None, None

    return "umbra", "umbra_vancouver_prt", run


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True, choices=["s1", "gotcha", "umbra"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="compute but do not append to runs.jsonl")
    ap.add_argument("--study", default="jstars_E1E5", help="row tag; rescore_E0 for the corrected-scorer re-run")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    domain, scene, run = {"s1": scene_s1, "gotcha": scene_gotcha, "umbra": scene_umbra}[a.scene]()
    todo = configs_for(domain)
    if a.limit:
        todo = todo[: a.limit]
    print(f"[{domain}] {len(todo)} configurations", flush=True)
    for prev in todo:
        name, params = prev["codec"], prev["params"]
        rate, cs, ref_img, hat_img, raw, raw_hat = run(name, params)
        sens = sensitivity(ref_img, hat_img)
        base = sens["pfa0.0001_tol3"]
        dpd, dfalse = base["pd"] - prev["cfar_pd"], base["n_false"] - prev["cfar_false"]
        det_ok = abs(dpd) <= 0.002 and abs(dfalse) <= 0.01 * prev["n_ref_detections"]
        row = {
            "study": a.study, "codec": name, "params": params, "domain": domain,
            "rate_bps": float(rate), "cfar_pd": base["pd"], "cfar_false": base["n_false"],
            "n_ref_detections": base["n_ref"], "mapping": "v2-pctclip99.99", "codec_seconds": round(cs, 2),
            "fidelity_img": fidelity(ref_img, hat_img),
            "fidelity_raw": fidelity(raw, raw_hat) if raw is not None else None,
            "sensitivity": sens,
            "determinism": {"prev_ts": prev["ts"], "d_pd": round(dpd, 5), "d_false": int(dfalse), "ok": bool(det_ok)},
        }
        if scene:
            row["scene"] = scene
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        f = row["fidelity_img"]
        verdict = "OK" if det_ok else f"MISMATCH dPd={dpd:.4f} dF={int(dfalse)}"
        print(
            f"{name} {json.dumps(params, sort_keys=True)}: rate={rate:.3f} pd={base['pd']:.3f} false={base['n_false']} "
            f"| img SQNR {f['sqnr_db']:.2f} dB PSNR {f['psnr_mag_db']:.2f} | det {verdict} | {cs:.0f}s",
            flush=True,
        )
        del hat_img, raw_hat


if __name__ == "__main__":
    main()
