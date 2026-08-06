"""Synthetic SAR-like scenes: speckled clutter + point targets.

Serves two purposes: (1) the harness runs end-to-end before any real data is
downloaded, (2) "synthetic data" is itself a named Phase I deliverable of the
topic. Complex circular-Gaussian clutter gives Rayleigh magnitude / exponential
power — the standard homogeneous-clutter model CA-CFAR assumes — and point
targets are sinc-shaped impulse responses so IRW/PSLR are measurable.
"""

import numpy as np


def _sinc_psf(size, width):
    """Separable sinc^2-windowed impulse response, unit peak."""
    x = (np.arange(size) - size // 2) / width
    s = np.sinc(x)
    return np.outer(s, s)


def make_scene(size=256, n_targets=6, tcr_db=25.0, psf_width=3.0, seed=0):
    """Return (iq complex64, target_positions [(r,c)]).

    tcr_db: target-to-clutter ratio. Targets are placed away from edges and
    each other so CFAR training rings stay clean.
    """
    rng = np.random.default_rng(seed)
    clutter = (rng.standard_normal((size, size)) + 1j * rng.standard_normal((size, size))) / np.sqrt(2)

    margin = 24
    positions = []
    while len(positions) < n_targets:
        r, c = rng.integers(margin, size - margin, 2)
        if all(max(abs(r - r0), abs(c - c0)) > 2 * margin // 2 for r0, c0 in positions):
            positions.append((int(r), int(c)))

    amp = 10 ** (tcr_db / 20)
    psf_size = 33
    psf = _sinc_psf(psf_size, psf_width) * amp
    iq = clutter.astype(np.complex128)
    h = psf_size // 2
    for r, c in positions:
        phase = np.exp(1j * rng.uniform(0, 2 * np.pi))
        iq[r - h : r + h + 1, c - h : c + h + 1] += psf * phase
    return iq.astype(np.complex64), positions


def make_dataset(n_scenes=32, size=256, seed=1337, **kw):
    """Stack of synthetic scenes for harness testing: (N, size, size) complex64."""
    scenes = [make_scene(size=size, seed=seed + i, **kw)[0] for i in range(n_scenes)]
    return np.stack(scenes)
