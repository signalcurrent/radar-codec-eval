"""Range compression: matched-filter raw echoes with the transmitted chirp.

CFAR on unfocused raw echoes just thresholds speckle — hypersensitive to any
perturbation and not what "radar utility" means. Range compression concentrates
target energy in range, giving the detector something physical to detect. Both
reference and reconstruction get the identical deterministic transform, so the
comparison stays fair. (Full azimuth focusing is a later upgrade.)

Chirp convention follows the Sentinel-1 L0 decoding literature: replica built
over t in [-TXPL/2, TXPL/2] with phase 2*pi*(phi1*t + phi2*t^2),
phi1 = TXPSF + TXPRR*TXPL/2, phi2 = TXPRR/2.
"""

import numpy as np


def chirp_replica(fs, txprr, txpsf, txpl):
    n = int(round(txpl * fs))
    t = np.arange(n) / fs - txpl / 2
    phi1 = txpsf + txprr * txpl / 2
    phi2 = txprr / 2
    return np.exp(2j * np.pi * (phi1 * t + phi2 * t**2)).astype(np.complex64)


def range_compress(iq, fs, txprr, txpsf, txpl):
    """Matched-filter along the range axis (axis 1). Returns complex array, same shape."""
    replica = chirp_replica(fs, txprr, txpsf, txpl)
    n = iq.shape[1]
    nfft = int(2 ** np.ceil(np.log2(n + len(replica) - 1)))
    spec = np.fft.fft(iq, n=nfft, axis=1) * np.conj(np.fft.fft(replica, n=nfft))[None, :]
    out = np.fft.ifft(spec, axis=1)[:, : n]
    return out.astype(np.complex64)
