"""End-to-end smoke test on synthetic data — no downloads, no torch, no ffmpeg.

Run:  python tests/test_smoke.py   (or python -m pytest tests/)
Validates: synthetic scenes -> BAQ codec -> radar metrics -> CFAR utility eval,
and that BAQ behaves sanely (more bits -> less distortion, high Pd at 4 bits).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from radarcodec.baselines.baq import baq_codec
from radarcodec.data.synthetic import make_scene
from radarcodec.metrics import irw_pslr, mse, phase_rmse
from radarcodec.tasks.cfar import ca_cfar, detection_agreement


def main():
    iq, positions = make_scene(size=256, n_targets=6, seed=42)

    # CFAR on the clean scene should find the planted targets
    det = ca_cfar(np.abs(iq) ** 2, pfa=1e-4, guard=2, train=8)
    found = sum(det[max(r - 3, 0) : r + 4, max(c - 3, 0) : c + 4].any() for r, c in positions)
    print(f"CFAR on clean scene: {found}/{len(positions)} planted targets detected")
    assert found >= len(positions) - 1, "CFAR misses planted targets on clean data"

    # point-target metrics on a chip around one target
    r, c = positions[0]
    chip = iq[r - 16 : r + 16, c - 16 : c + 16]
    irw, pslr = irw_pslr(chip)
    print(f"clean point target: IRW={irw:.2f} samples, PSLR={pslr:.1f} dB")

    # BAQ sweep: distortion must fall as bits rise; utility must hold at 4 bits
    prev_mse = np.inf
    for bits in (2, 3, 4):
        iq_hat, rate = baq_codec(iq, bits=bits)
        m, ph = mse(iq, iq_hat), phase_rmse(iq, iq_hat)
        agree = detection_agreement(iq, iq_hat, pfa=1e-4, guard=2, train=8)
        print(f"BAQ {bits}-bit: rate={rate:.2f} bps  mse={m:.4f}  "
              f"phase_rmse={ph:.3f} rad  Pd={agree['pd']:.2f}  false={agree['n_false']}")
        assert m < prev_mse, "MSE should decrease with more bits"
        prev_mse = m
        if bits == 4:
            assert agree["pd"] >= 0.9, "4-bit BAQ should preserve detections"

    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
