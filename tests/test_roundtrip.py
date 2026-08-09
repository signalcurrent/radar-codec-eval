"""Round-trip invertibility tests for both focus transforms.

The paper's Reproducibility section states the invertible transforms ship
with their round-trip verification tests; these are those tests, runnable
with no data downloads (synthetic complex input only).

    python -m pytest tests/ -v
        (or)  python tests/test_roundtrip.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

# Tolerances: float32/complex64 machine-precision round trips. The paper
# reports ~1e-7 relative error for the Sentinel-1 unitary transform and
# 4.4e-7 mean relative error for the Gotcha DFT pair on real data;
# synthetic inputs here are held to the same order.
MEAN_RTOL = 5e-6
MAX_RTOL = 5e-3  # isolated near-zero samples can have large relative error


def _rel_err(x, x_hat):
    denom = np.maximum(np.abs(x), 1e-9)
    return np.abs(x_hat - x) / denom


def _synth_iq(shape, seed=1337):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(shape) + 1j * rng.standard_normal(shape)).astype(
        np.complex64
    )


def _synth_meta(n_rg):
    """Chirp/timing metadata with representative Sentinel-1 stripmap values."""
    return {
        "fs": 46918402.8,
        "txprr": 825635554407.18,
        "txpsf": -21094036.489,
        "txpl": 5.109935e-05,
        "pri": 6.0115e-04,
        "swst": 7.513e-05,
        "rank": 10,
        "vr": 7207.57,
    }


def test_sentinel1_unitary_transform_roundtrip():
    """Phase-only dechirp/RCMC/azimuth transform: forward then inverse."""
    from radarcodec.baselines.transform_codec import forward, inverse

    iq = _synth_iq((256, 512))
    meta = _synth_meta(iq.shape[1])
    for mode in ("dechirp", "full"):
        y = forward(iq, meta, mode)
        iq_hat = inverse(y, meta, mode)
        err = _rel_err(iq, iq_hat)
        assert err.mean() < MEAN_RTOL, f"{mode}: mean rel err {err.mean():.2e}"
        assert err.max() < MAX_RTOL, f"{mode}: max rel err {err.max():.2e}"


def test_gotcha_dft_pair_roundtrip():
    """form_image / inverse_image are exact adjoints up to float rounding."""
    from radarcodec.data.gotcha import form_image, inverse_image

    ph = _synth_iq((384, 512))
    img = form_image(ph)
    ph_hat = inverse_image(img)
    err = _rel_err(ph, ph_hat)
    assert err.mean() < MEAN_RTOL, f"mean rel err {err.mean():.2e}"
    assert err.max() < MAX_RTOL, f"max rel err {err.max():.2e}"


def test_transform_preserves_energy():
    """Unitarity check: the transforms must preserve total signal energy."""
    from radarcodec.baselines.transform_codec import forward
    from radarcodec.data.gotcha import form_image

    iq = _synth_iq((256, 512))
    meta = _synth_meta(iq.shape[1])
    e0 = float(np.sum(np.abs(iq) ** 2))
    for mode in ("dechirp", "full"):
        e1 = float(np.sum(np.abs(forward(iq, meta, mode)) ** 2))
        assert abs(e1 - e0) / e0 < 1e-5, f"{mode}: energy ratio {e1/e0:.6f}"

    ph = _synth_iq((384, 512))
    # orthonormal-scaled DFT pair preserves energy up to fft normalization
    img = form_image(ph)
    e_img = float(np.sum(np.abs(img) ** 2)) * img.size
    e_ph = float(np.sum(np.abs(ph) ** 2))
    assert abs(e_img - e_ph) / e_ph < 1e-4, f"gotcha: energy ratio {e_img/e_ph:.6f}"


if __name__ == "__main__":
    test_sentinel1_unitary_transform_roundtrip()
    print("sentinel-1 unitary transform round trip: OK")
    test_gotcha_dft_pair_roundtrip()
    print("gotcha DFT pair round trip: OK")
    test_transform_preserves_energy()
    print("energy preservation: OK")
