"""E9: entropy-coded BAQ rate at identical reconstruction (pre-declared in FINDINGS.md, 2026-10-29). Recomputes the
Lloyd-Max BAQ quantizer indices with the same block-adaptive procedure as radarcodec.baselines.baq (so the
reconstruction, and therefore Pd and spurious count, are identical to the logged BAQ rows) and reports the order-0
entropy of the indices per plane plus the block side information at the paper's convention (8 bits per block per
plane). Writes reports/e9_entropy_baq.json; no log rows (the detection numbers are the logged BAQ rows').

    python scripts/eval_entropy_baq.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np

from radarcodec.baselines.baq import _levels

ROOT = Path(__file__).resolve().parents[1]
BLOCK = 128


def indices(x, bits, block=BLOCK):
    levels, thresholds = _levels(bits)
    n = len(x)
    pad = (-n) % block
    xp = np.pad(x, (0, pad)).reshape(-1, block)
    sigma = xp.std(axis=1, keepdims=True) + 1e-12
    return np.searchsorted(thresholds, xp / sigma).ravel()[:n]


def entropy_bits(idx):
    _, c = np.unique(idx, return_counts=True)
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def main():
    out = {}
    from eval_focused import load_crop
    from eval_gotcha import N_PULSES, PH_PATH, START_PULSE
    from radarcodec.data.gotcha import read_phase_history
    scenes = {"s1_raw": load_crop()[0], "gotcha_ph": read_phase_history(PH_PATH, start_pulse=START_PULSE, n_pulses=N_PULSES)}
    for name, iq in scenes.items():
        out[name] = {}
        for bits in (2, 3, 4, 6):
            hi = entropy_bits(indices(iq.real.ravel().astype(np.float64), bits))
            hq = entropy_bits(indices(iq.imag.ravel().astype(np.float64), bits))
            side = 2 * 8.0 / BLOCK
            out[name][f"baq{bits}"] = {"fixed_rate_bps": 2 * (bits + 8.0 / BLOCK), "entropy_I": round(hi, 4), "entropy_Q": round(hq, 4),
                                       "entropy_coded_rate_bps": round(hi + hq + side, 4), "side_info_bps": side}
            print(f"{name} BAQ {bits}-bit: fixed {2*(bits+8/BLOCK):.3f} -> entropy-coded {hi+hq+side:.3f} bps (H_I {hi:.3f}, H_Q {hq:.3f})", flush=True)
    (ROOT / "reports" / "e9_entropy_baq.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
