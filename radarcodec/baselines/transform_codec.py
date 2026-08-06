"""Invertible (unitary) dechirp/focus transform wrapped around a classical codec.

Every step is a phase-only multiply in an FFT domain plus FFT/IFFT pairs —
exactly unitary, hence exactly invertible up to float rounding (unlike the
matched filter in focus_rda.py, whose magnitude collapses out of band).
Circular convolution (no padding/truncation) keeps the round trip exact.

Modes (the registered compute ablation):
  'dechirp' — phase-only range dechirp only: one FFT + multiply per line;
              cheap enough for onboard hardware.
  'full'    — adds RCMC phase ramp + azimuth matched-filter phase; the
              expensive half (see FINDINGS.md Amendment 3).
"""

import numpy as np

from radarcodec.metrics.focus import chirp_replica
from radarcodec.metrics.focus_rda import C, WAVELENGTH


def _filters(shape, meta, mode):
    n_az, n_rg = shape
    replica_spec = np.fft.fft(chirp_replica(meta["fs"], meta["txprr"], meta["txpsf"], meta["txpl"]), n_rg)
    out = {"range": np.exp(-1j * np.angle(replica_spec))}  # phase-only matched filter
    if mode == "full":
        pri, vr = meta["pri"], meta["vr"]
        f_eta = np.fft.fftfreq(n_az, d=pri)
        D = np.sqrt(np.maximum(1.0 - (WAVELENGTH * f_eta / (2.0 * vr)) ** 2, 1e-9))[:, None]
        fast_time = meta["rank"] * pri + meta["swst"] + np.arange(n_rg) / meta["fs"]
        r0 = C * fast_time / 2.0
        f_tau = np.fft.fftfreq(n_rg, d=1.0 / meta["fs"])
        dR = r0[n_rg // 2] * (1.0 / D - 1.0)  # mid-swath, per azimuth frequency
        out["rcmc"] = np.exp(4j * np.pi * f_tau[None, :] * dR / C)
        out["az"] = np.exp(4j * np.pi * r0[None, :] * D / WAVELENGTH)
    return out


def forward(iq, meta, mode="full"):
    F = _filters(iq.shape, meta, mode)
    x = np.fft.ifft(np.fft.fft(iq, axis=1) * F["range"][None, :], axis=1)
    if mode == "full":
        x = np.fft.fft(x, axis=0)
        x = np.fft.ifft(np.fft.fft(x, axis=1) * F["rcmc"], axis=1)
        x = x * F["az"]
        x = np.fft.ifft(x, axis=0)
    return x.astype(np.complex64)


def inverse(x, meta, mode="full"):
    F = _filters(x.shape, meta, mode)
    y = x.astype(np.complex128)
    if mode == "full":
        y = np.fft.fft(y, axis=0)
        y = y * np.conj(F["az"])
        y = np.fft.ifft(np.fft.fft(y, axis=1) * np.conj(F["rcmc"]), axis=1)
        y = np.fft.ifft(y, axis=0)
    y = np.fft.ifft(np.fft.fft(y, axis=1) * np.conj(F["range"])[None, :], axis=1)
    return y.astype(np.complex64)


def tfocus_codec(iq, meta=None, base="jpeg2000", mode="full", **base_params):
    """Compress raw iq in the unitary transformed domain with a classical codec."""
    from radarcodec.baselines import CODECS  # lazy: avoids circular import

    if meta is None:
        raise ValueError("tfocus codec requires chirp/timing meta")
    y = forward(iq, meta, mode)
    y_hat, rate = CODECS[base](y, **base_params)
    return inverse(y_hat, meta, mode), rate
