"""Reader for the AFRL Gotcha GMTI Challenge Problem phase-history data.

Public release (SDMS). Format per AFRL's readChallengePH.m: big-endian
float32, I/Q interleaved, 384 range bins per pulse, column-major. Image
formation for this motion-compensated phase history is a plain 2-D IFFT
(AFRL's formSimpleRangeDopplerImage.m), so no focuser is needed.

Ingest verified 2026-08-08 against AFRL's own example parameters
(chan1/mis2, startPulse 5585, 1864 pulses): the Durango sits at ~-13.8 dB
with 29.3 dB contrast over scene median, and the image renders correctly at
AFRL's stated display range of [-60, -10] dB.

Why this dataset matters here: it is public PHASE-HISTORY data (our claimed
domain) with MOVING TARGETS and GPS GROUND TRUTH — addressing the topic's
MTI language and our standing "detections are detector self-consistency"
limitation. See reports/afrl_data_opportunities.md.

Courtesy obligation: AFRL asks that results be shared with the ATR Division,
AFRL Sensors Directorate, and AFRL/RYA acknowledged as the data source.
"""

import numpy as np

N_RANGE_BINS = 384


def read_phase_history(path, start_pulse=1, n_pulses=1864, n_range_bins=N_RANGE_BINS):
    """Return complex64 phase history, shape (n_range_bins, n_pulses).

    start_pulse is 1-based, matching AFRL's convention.
    """
    bytes_per_pulse = n_range_bins * 2 * 4
    with open(path, "rb") as f:
        f.seek((start_pulse - 1) * bytes_per_pulse)
        raw = np.fromfile(f, dtype=">f4", count=2 * n_range_bins * n_pulses)
    raw = raw.reshape(n_pulses, 2 * n_range_bins).T  # column-major equivalent
    return (raw[0::2, :] + 1j * raw[1::2, :]).astype(np.complex64)


def form_image(ph):
    """Range-Doppler image from motion-compensated phase history (AFRL method)."""
    return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(ph))).astype(np.complex64)


def inverse_image(img):
    """Exact inverse of form_image -- recovers phase history from the image.

    Unlike Sentinel-1 raw echo (which needs a physical dechirp/RCMC/azimuth
    chain to reach a concentrated domain), Gotcha's phase history is already
    motion-compensated, so its focus step IS a plain 2-D DFT pair -- forward
    and inverse are exact adjoints of each other, verified round-trip
    2026-08-08 at 4.4e-7 mean relative error (float32 precision).
    """
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(img))).astype(np.complex64)


def tfocus_gotcha_codec(ph, base="jpeg2000", **base_params):
    """Compress Gotcha phase history in the focused (range-Doppler) domain.

    Direct analog of transform_codec.tfocus_codec for this dataset: forward
    to the image domain, compress there with a classical codec, invert.
    Only one domain exists here (no dechirp-only/full-focus split -- the
    data has no separate dechirp step to begin with).
    """
    from radarcodec.baselines import CODECS  # lazy: avoids circular import

    img = form_image(ph)
    img_hat, rate = CODECS[base](img, **base_params)
    return inverse_image(img_hat), rate


def n_pulses_in_file(path, n_range_bins=N_RANGE_BINS):
    import os

    return os.path.getsize(path) // (n_range_bins * 2 * 4)
