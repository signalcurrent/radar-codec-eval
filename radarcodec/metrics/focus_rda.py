"""Stripmap range-Doppler focusing (compact Cumming & Wong implementation).

Chain: range compression -> azimuth FFT -> RCMC (linear-phase range shift in
the 2-D frequency domain) -> azimuth matched filter (hyperbolic) -> azimuth
IFFT. Sentinel-1 is zero-Doppler steered, so the Doppler centroid is taken as
zero — adequate for comparative codec evaluation, not for geolocation.

Only valid for STRIPMAP (S1–S6) chunks. IW/TOPSAR needs burst-aware processing
this deliberately does not attempt.

The eval question this serves: compress raw -> decompress -> FOCUS -> CFAR,
so measured detection loss is loss that survives SAR processing.
"""

import numpy as np

from radarcodec.metrics.focus import chirp_replica

C = 299792458.0
WAVELENGTH = C / 5.405e9  # Sentinel-1 C-band


def focus_stripmap(iq, meta):
    """Focus a raw stripmap chunk. iq: (n_echoes, n_samples) complex.

    meta keys: fs, txprr, txpsf, txpl (chirp); pri, swst, rank (timing);
    vr (effective radar velocity, m/s).
    Returns focused complex image, same shape (azimuth x slant range).
    """
    n_az, n_rg = iq.shape
    fs, pri = meta["fs"], meta["pri"]
    prf = 1.0 / pri

    # --- range compression (frequency domain, whole chunk at once)
    replica = chirp_replica(fs, meta["txprr"], meta["txpsf"], meta["txpl"])
    nfft_rg = int(2 ** np.ceil(np.log2(n_rg + len(replica) - 1)))
    H_rg = np.conj(np.fft.fft(replica, nfft_rg))
    data = np.fft.ifft(np.fft.fft(iq, nfft_rg, axis=1) * H_rg[None, :], axis=1)[:, :n_rg]

    # --- slant range per sample (rank = number of PRIs between tx and rx window)
    fast_time = meta["rank"] * pri + meta["swst"] + np.arange(n_rg) / fs
    r0 = C * fast_time / 2.0

    # --- azimuth FFT
    data = np.fft.fft(data, axis=0)
    f_eta = np.fft.fftfreq(n_az, d=pri)  # azimuth (Doppler) frequency

    # --- migration factor D(f_eta, vr)
    vr = meta["vr"]
    arg = 1.0 - (WAVELENGTH * f_eta / (2.0 * vr)) ** 2
    D = np.sqrt(np.maximum(arg, 1e-9))[:, None]  # (n_az, 1)

    # --- RCMC: shift each range line by dR(f_eta) via linear phase in range freq
    dR = r0[None, :] * (1.0 / D - 1.0)  # (n_az, n_rg); varies slowly with r0
    f_tau = np.fft.fftfreq(n_rg, d=1.0 / fs)
    spec = np.fft.fft(data, axis=1)
    # use mid-swath dR per azimuth frequency (range dependence is weak across a chunk)
    rcmc = np.exp(4j * np.pi * f_tau[None, :] * dR[:, n_rg // 2 : n_rg // 2 + 1] / C)
    data = np.fft.ifft(spec * rcmc, axis=1)

    # --- azimuth matched filter and inverse FFT
    H_az = np.exp(4j * np.pi * r0[None, :] * D / WAVELENGTH)
    data = np.fft.ifft(data * H_az, axis=0)
    return data.astype(np.complex64)


def effective_velocity(ephemeris):
    """Effective radar velocity sqrt(Vs*Vg) from a sentinel1decoder ephemeris frame."""
    vcols = [c for c in ephemeris.columns if "velocity ECEF" in c]
    pcols = [c for c in ephemeris.columns if "position ECEF" in c]
    v = np.linalg.norm(ephemeris[vcols].iloc[len(ephemeris) // 2].to_numpy())
    p = np.linalg.norm(ephemeris[pcols].iloc[len(ephemeris) // 2].to_numpy())
    re = 6371e3
    vg = v * re / p  # ground velocity approximation
    vr = float(np.sqrt(v * vg))
    if not np.isfinite(vr) or not 6500 < vr < 7800:
        raise ValueError(f"implausible effective velocity {vr}")
    return vr
