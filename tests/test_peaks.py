"""Regression test for the E0 scorer bug (2026-10-29): adjacent CFAR exceedance pixels of one peak must reduce to
ONE detection. The legacy reduction returned every exceedance pixel."""
import numpy as np

from radarcodec.tasks.cfar import _to_centroids, detection_agreement


def test_plateau_reduces_to_one_peak():
    det = np.zeros((9, 9), bool)
    det[2:4, 2:4] = True  # four adjacent exceedance pixels of one peak
    power = np.random.default_rng(0).random((9, 9))
    power[2:4, 2:4] += 5.0
    assert len(_to_centroids(det, power)) == 1


def test_two_separate_peaks_stay_two():
    det = np.zeros((12, 12), bool)
    det[2, 2] = True
    det[9, 9] = True
    power = np.zeros((12, 12))
    power[2, 2] = 10.0
    power[9, 9] = 10.0
    assert len(_to_centroids(det, power)) == 2


def test_agreement_identity_is_perfect():
    rng = np.random.default_rng(1)
    iq = (rng.standard_normal((128, 128)) + 1j * rng.standard_normal((128, 128))).astype(np.complex64)
    iq[64, 64] += 40.0
    d = detection_agreement(iq, iq.copy(), pfa=1e-4, guard=2, train=8)
    assert d["pd"] == 1.0 and d["n_false"] == 0 and d["n_ref"] >= 1
