"""Asiyabi adaptation procedure for FDBAQ-decoded Sentinel-1 raw data.

Reference: R. M. Asiyabi et al., "Adaptation of decoded Sentinel-1 SAR raw
data for the assessment of novel data compression methods," IGARSS 2024,
pp. 2541-2545; applied in Asiyabi et al., IEEE JSTSP 19(3), 2025.

Problem: decoded S1 L0 samples sit on the FDBAQ reconstruction lattice. In
our Chicago stripmap crop that is only 48 distinct I values across 1.05M
samples (32 distinct in a 64x64 block). Any codec applied on top interacts
with that lattice; Asiyabi et al. report BAQ at one bit depth scoring
anomalously WELL purely because its quantization step coincidentally aligned
with the FDBAQ step.

Fix (theirs): add random uniform noise of amplitude equal to the local
lattice step to fill the gaps between reconstruction levels, producing
"quasi-uniformly quantized" data whose statistics resemble uncompressed
onboard raw data. Explicitly NOT an inversion back to true ADC output — it
restores the right conditions for *evaluating* compression, nothing more.

Honest note: the superior option, now available, is to evaluate on genuinely
unencoded public data (AFRL Gotcha GMTI phase history, no BAQ signature).
Use this adaptation for Sentinel-1 continuity; use Gotcha to escape the
issue entirely.
"""

import numpy as np


def estimate_lattice_step(x, block=64):
    """Median spacing between adjacent distinct values in local blocks."""
    steps = []
    h, w = x.shape
    for r in range(0, min(h, block * 8), block):
        for c in range(0, min(w, block * 8), block):
            u = np.unique(x[r : r + block, c : c + block])
            if u.size > 2:
                d = np.diff(u)
                d = d[d > 0]
                if d.size:
                    steps.append(np.median(d))
    return float(np.median(steps)) if steps else 0.0


def adapt(iq, rng=None, step=None):
    """Return FDBAQ-decoded iq with lattice gaps filled by uniform noise.

    Noise is uniform on [-step/2, +step/2] applied independently to I and Q,
    where `step` defaults to the estimated local lattice spacing.
    """
    rng = np.random.default_rng(1337) if rng is None else rng
    if step is None:
        step = max(estimate_lattice_step(iq.real), estimate_lattice_step(iq.imag))
    if step <= 0:
        return iq.astype(np.complex64)  # already continuous-valued
    n = iq.shape
    di = rng.uniform(-step / 2, step / 2, n)
    dq = rng.uniform(-step / 2, step / 2, n)
    return (iq.real + di + 1j * (iq.imag + dq)).astype(np.complex64)
