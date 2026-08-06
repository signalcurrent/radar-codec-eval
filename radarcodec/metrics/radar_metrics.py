"""Radar-specific quality metrics — the ones that matter instead of PSNR/SSIM.

- mse / phase_rmse: signal-domain sanity numbers (phase matters: SAR focusing,
  interferometry, and Doppler processing all live in the phase).
- irw_pslr: impulse response width and peak sidelobe ratio measured on a
  point-target response. Feed it a focused chip containing an isolated strong
  scatterer (corner reflector, ship). Degraded IRW = lost resolution; degraded
  PSLR = sidelobe energy masking nearby targets.
"""

import numpy as np


def mse(iq, iq_hat):
    return float(np.mean(np.abs(iq - iq_hat) ** 2))


def phase_rmse(iq, iq_hat, mag_floor_db=-20.0):
    """RMS phase error in radians, masked to samples with meaningful magnitude."""
    mag = np.abs(iq)
    mask = mag > mag.max() * 10 ** (mag_floor_db / 20)
    if not mask.any():
        return float("nan")
    dphi = np.angle(iq[mask] * np.conj(iq_hat[mask]))
    return float(np.sqrt(np.mean(dphi**2)))


def _peak_cut(img, axis, oversample=16):
    """Oversampled 1-D cut through the image peak along `axis`, via FFT zero-pad."""
    peak = np.unravel_index(np.argmax(np.abs(img)), img.shape)
    cut = img[peak[0], :] if axis == 1 else img[:, peak[1]]
    n = len(cut)
    spec = np.fft.fftshift(np.fft.fft(cut))
    padded = np.zeros(n * oversample, dtype=complex)
    padded[(n * oversample - n) // 2 : (n * oversample + n) // 2] = spec
    return np.abs(np.fft.ifft(np.fft.ifftshift(padded))) * oversample, oversample


def irw_pslr(chip, axis=1, oversample=16):
    """(IRW in samples, PSLR in dB) from a point-target chip along one axis.

    IRW: -3 dB mainlobe width. PSLR: highest sidelobe relative to mainlobe peak,
    searched outside the first nulls.
    """
    cut, os_ = _peak_cut(chip, axis, oversample)
    p = int(np.argmax(cut))
    peak = cut[p]

    # -3 dB width
    half = peak / np.sqrt(2)
    left = p
    while left > 0 and cut[left] > half:
        left -= 1
    right = p
    while right < len(cut) - 1 and cut[right] > half:
        right += 1
    irw = (right - left) / os_

    # first nulls, then max sidelobe beyond them
    ln = p
    while ln > 0 and cut[ln - 1] < cut[ln]:
        ln -= 1
    rn = p
    while rn < len(cut) - 1 and cut[rn + 1] < cut[rn]:
        rn += 1
    outside = np.concatenate([cut[:ln], cut[rn + 1 :]])
    pslr_db = float(20 * np.log10(outside.max() / peak)) if len(outside) else float("nan")
    return float(irw), pslr_db
