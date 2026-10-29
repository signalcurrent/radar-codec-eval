"""JSTARS revision E8: plane-mapping clip control (pre-declared in FINDINGS.md, 2026-10-29 evening).
No-codec round trips through the registered v2 plane mapping (99.99th-percentile clip, 16-bit) in the raw and
the focused/transform domains of each scene, scored with the corrected scorer; then focused-domain JPEG2000
ratio 8 on S1 under three clip settings. Rows tagged study = "ctrl_E8".

    python scripts/eval_clip_control_jstars.py [--dry-run]
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
from radarcodec.baselines.planemap import plane_to_u16, u16_to_plane
from radarcodec.experiments import log_run
from radarcodec.tasks.cfar import _to_centroids, ca_cfar, detection_agreement

ROOT = Path(__file__).resolve().parents[1]
PFA, GUARD, TRAIN = 1e-4, 2, 8


def map_round_trip(iq, q=99.99):
    """Identity 'codec': plane mapping forward and back, no coding. Returns (iq_hat, clip bounds)."""
    ui, ci = plane_to_u16(iq.real.astype(np.float64), q)
    uq, cq = plane_to_u16(iq.imag.astype(np.float64), q)
    return (u16_to_plane(ui, ci) + 1j * u16_to_plane(uq, cq)).astype(np.complex64), (ci, cq)


def clip_stats(x, bounds, ref_img_for_peaks=None):
    """Fraction of samples clipped per plane and clipped energy fraction; if a scored image is given, the
    fraction of its reference peaks whose own I or Q exceeds the bound (only meaningful when x is that image)."""
    ci, cq = bounds
    re, im = x.real, x.imag
    clipped = (np.abs(re) > ci) | (np.abs(im) > cq)
    e_tot = float(np.sum(re.astype(np.float64) ** 2 + im.astype(np.float64) ** 2))
    e_over = float(np.sum((np.maximum(np.abs(re) - ci, 0)) ** 2 + (np.maximum(np.abs(im) - cq, 0)) ** 2))
    out = {"frac_samples_clipped": float(np.mean(clipped)), "clipped_energy_fraction": e_over / max(e_tot, 1e-30)}
    if ref_img_for_peaks is not None:
        p = np.abs(ref_img_for_peaks) ** 2
        pts = _to_centroids(ca_cfar(p, PFA, GUARD, TRAIN), p)
        hit = clipped[pts[:, 0], pts[:, 1]]
        out["frac_reference_peaks_clipped"] = float(np.mean(hit))
        out["n_reference_peaks"] = int(len(pts))
    return out


def sqnr(x, xh):
    return float(10 * np.log10(np.sum(np.abs(x) ** 2) / max(np.sum(np.abs(x - xh) ** 2), 1e-30)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_sweep.yaml"))
    cfar_cfg = cfg.get("tasks", {}).get("cfar", {})
    sys.path.insert(0, str(ROOT / "scripts"))
    rows = []

    def emit(row, msg):
        if not a.dry_run:
            log_run(cfg["out"], cfg, row)
        print(msg, flush=True)
        rows.append(row)

    # ---------------- S1
    from eval_focused import interior, load_crop
    from radarcodec.baselines.transform_codec import forward, inverse
    from radarcodec.metrics.focus_rda import focus_stripmap
    raw, meta = load_crop()
    ref = focus_stripmap(raw, meta)
    ref_i = interior(ref)
    # (a) raw-domain round trip
    raw_hat, b = map_round_trip(raw)
    hat_i = interior(focus_stripmap(raw_hat, meta))
    det = detection_agreement(ref_i, hat_i, **cfar_cfg)
    emit({"study": "ctrl_E8", "codec": "mapping_only", "params": {"domain_applied": "raw", "clip_q": 99.99},
          "domain": "s1_focused", "rate_bps": 32.0, "cfar_pd": det["pd"], "cfar_false": det["n_false"],
          "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "sqnr_img_db": round(sqnr(ref_i, hat_i), 3),
          "clip": clip_stats(raw, b)},
         f"S1 raw-domain mapping round trip: pd={det['pd']:.4f} false={det['n_false']} n_ref={det['n_ref']} sqnr={sqnr(ref_i, hat_i):.2f} dB")
    # (b) focused/transform-domain round trip
    y = forward(raw, meta, mode="full")
    y_hat, b = map_round_trip(y)
    hat_i = interior(focus_stripmap(inverse(y_hat, meta, mode="full"), meta))
    det = detection_agreement(ref_i, hat_i, **cfar_cfg)
    cs = clip_stats(y, b)
    emit({"study": "ctrl_E8", "codec": "mapping_only", "params": {"domain_applied": "transform_full", "clip_q": 99.99},
          "domain": "s1_focused", "rate_bps": 32.0, "cfar_pd": det["pd"], "cfar_false": det["n_false"],
          "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "sqnr_img_db": round(sqnr(ref_i, hat_i), 3), "clip": cs},
         f"S1 transform-domain mapping round trip: pd={det['pd']:.4f} false={det['n_false']} sqnr={sqnr(ref_i, hat_i):.2f} dB clipped_energy={cs['clipped_energy_fraction']:.2e}")
    # (c) focused JPEG2000 r8 under three clip settings
    for q, tag in ((99.99, "v2-pctclip99.99"), (99.999, "pctclip99.999"), (100.0, "minmax")):
        t0 = time.perf_counter()
        raw_hat, rate = CODECS["tfocus"](raw, meta=meta, base="jpeg2000", mode="full", ratio=8, clip_q=q)
        hat_i = interior(focus_stripmap(raw_hat, meta))
        det = detection_agreement(ref_i, hat_i, **cfar_cfg)
        emit({"study": "ctrl_E8", "codec": "tfocus", "params": {"base": "jpeg2000", "mode": "full", "ratio": 8, "clip_q": q},
              "domain": "s1_focused", "rate_bps": float(rate), "cfar_pd": det["pd"], "cfar_false": det["n_false"],
              "n_ref_detections": det["n_ref"], "mapping": tag, "sqnr_img_db": round(sqnr(ref_i, hat_i), 3),
              "codec_seconds": round(time.perf_counter() - t0, 1)},
             f"S1 focused JPEG2000 r8 clip {q}: rate={rate:.3f} pd={det['pd']:.4f} false={det['n_false']} sqnr={sqnr(ref_i, hat_i):.2f} dB")
    del raw, ref, y

    # ---------------- Gotcha
    from eval_gotcha import N_PULSES, PH_PATH, START_PULSE
    from radarcodec.data.gotcha import form_image, inverse_image, read_phase_history
    ph = read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)
    ref = form_image(ph)
    ph_hat, b = map_round_trip(ph)
    hat = form_image(ph_hat)
    det = detection_agreement(ref, hat, **cfar_cfg)
    emit({"study": "ctrl_E8", "codec": "mapping_only", "params": {"domain_applied": "raw", "clip_q": 99.99}, "domain": "gotcha_gmti",
          "scene": "durango_chan1_mis2", "rate_bps": 32.0, "cfar_pd": det["pd"], "cfar_false": det["n_false"],
          "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "sqnr_img_db": round(sqnr(ref, hat), 3), "clip": clip_stats(ph, b)},
         f"Gotcha raw-domain mapping round trip: pd={det['pd']:.4f} false={det['n_false']} n_ref={det['n_ref']} sqnr={sqnr(ref, hat):.2f} dB")
    img_hat, b = map_round_trip(ref)
    hat = form_image(inverse_image(img_hat))
    det = detection_agreement(ref, hat, **cfar_cfg)
    cs = clip_stats(ref, b, ref_img_for_peaks=ref)
    emit({"study": "ctrl_E8", "codec": "mapping_only", "params": {"domain_applied": "focused", "clip_q": 99.99}, "domain": "gotcha_gmti",
          "scene": "durango_chan1_mis2", "rate_bps": 32.0, "cfar_pd": det["pd"], "cfar_false": det["n_false"],
          "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "sqnr_img_db": round(sqnr(ref, hat), 3), "clip": cs},
         f"Gotcha focused-domain mapping round trip: pd={det['pd']:.4f} false={det['n_false']} sqnr={sqnr(ref, hat):.2f} dB peaks_clipped={cs['frac_reference_peaks_clipped']:.4f}")
    del ph, ref

    # ---------------- Umbra
    from eval_umbra import TRIM, load_sicd_crop
    iq = load_sicd_crop(ROOT / "data" / "umbra" / "vancouver_SICD.nitf", 4096)
    ref_i = iq[TRIM:-TRIM, TRIM:-TRIM]
    iq_hat, b = map_round_trip(iq)
    hat_i = iq_hat[TRIM:-TRIM, TRIM:-TRIM]
    det = detection_agreement(ref_i, hat_i, **cfar_cfg)
    cs = clip_stats(iq, b, ref_img_for_peaks=None)
    p = np.abs(ref_i) ** 2
    pts = _to_centroids(ca_cfar(p, PFA, GUARD, TRAIN), p)
    clipped = (np.abs(ref_i.real) > b[0]) | (np.abs(ref_i.imag) > b[1])
    cs["frac_reference_peaks_clipped"] = float(np.mean(clipped[pts[:, 0], pts[:, 1]]))
    cs["n_reference_peaks"] = int(len(pts))
    emit({"study": "ctrl_E8", "codec": "mapping_only", "params": {"domain_applied": "image", "clip_q": 99.99}, "domain": "umbra",
          "scene": "umbra_vancouver_prt", "rate_bps": 32.0, "cfar_pd": det["pd"], "cfar_false": det["n_false"],
          "n_ref_detections": det["n_ref"], "mapping": "v2-pctclip99.99", "sqnr_img_db": round(sqnr(ref_i, hat_i), 3), "clip": cs},
         f"Umbra image-domain mapping round trip: pd={det['pd']:.4f} false={det['n_false']} sqnr={sqnr(ref_i, hat_i):.2f} dB peaks_clipped={cs['frac_reference_peaks_clipped']:.4f}")
    if not a.dry_run:
        (ROOT / "reports" / "e8_clip_control.json").write_text(json.dumps(rows, indent=1, default=float))


if __name__ == "__main__":
    main()
