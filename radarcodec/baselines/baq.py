"""Block Adaptive Quantization — the classical raw-radar codec family.

Per block of N real samples (I and Q treated as independent streams, as in
spaceborne BAQ), estimate sigma, normalize, quantize with the Lloyd-Max
quantizer optimal for a unit Gaussian, denormalize on decode. Rate is exactly
`bits` per real sample plus sigma overhead (8 bits per block), i.e.
2*(bits + 8/block) bits per complex sample.

Sentinel-1's operational FDBAQ is this with entropy-coded, SNR-adaptive bit
allocation; fixed-rate BAQ at 2-4 bits brackets it. See fdbaq.py for how the
already-FDBAQ'd nature of ground L0 data is accounted for.
"""

import numpy as np
from scipy import stats


def _lloyd_max_levels(bits, iters=100):
    """Lloyd-Max quantizer levels/thresholds for a unit Gaussian, via fixed point."""
    n = 2**bits
    # init: equiprobable-mass centroids
    qs = (np.arange(n) + 0.5) / n
    levels = stats.norm.ppf(qs)
    for _ in range(iters):
        thresholds = (levels[:-1] + levels[1:]) / 2
        edges = np.concatenate([[-np.inf], thresholds, [np.inf]])
        # centroid of each cell under the Gaussian: E[x | a<x<b]
        a, b = edges[:-1], edges[1:]
        mass = stats.norm.cdf(b) - stats.norm.cdf(a)
        levels = (stats.norm.pdf(a) - stats.norm.pdf(b)) / np.maximum(mass, 1e-300)
    return levels, thresholds


_LEVEL_CACHE = {}


def _levels(bits):
    if bits not in _LEVEL_CACHE:
        _LEVEL_CACHE[bits] = _lloyd_max_levels(bits)
    return _LEVEL_CACHE[bits]


def _baq_real(x, bits, block):
    """Quantize a real 1-D stream block-adaptively; returns reconstruction."""
    levels, thresholds = _levels(bits)
    n = len(x)
    pad = (-n) % block
    xp = np.pad(x, (0, pad)).reshape(-1, block)
    sigma = xp.std(axis=1, keepdims=True) + 1e-12
    idx = np.searchsorted(thresholds, xp / sigma)
    rec = levels[idx] * sigma
    return rec.ravel()[:n]


def baq_codec(iq, bits=3, block=128, **_):
    """Returns (iq_hat, rate_bits_per_complex_sample)."""
    shape = iq.shape
    i_rec = _baq_real(iq.real.ravel().astype(np.float64), bits, block)
    q_rec = _baq_real(iq.imag.ravel().astype(np.float64), bits, block)
    iq_hat = (i_rec + 1j * q_rec).reshape(shape).astype(np.complex64)
    rate = 2 * (bits + 8.0 / block)
    return iq_hat, rate
