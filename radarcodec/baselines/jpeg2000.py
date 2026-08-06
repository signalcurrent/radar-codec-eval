"""JPEG2000 baseline applied per I/Q plane (16-bit scaled), via glymur/OpenJPEG.

Rate is measured from actual encoded bytes of both planes.
"""

import tempfile
from pathlib import Path

import numpy as np


def _encode_plane(plane, ratio, tmpdir):
    import glymur

    lo, hi = plane.min(), plane.max()
    scale = (hi - lo) + 1e-12
    u16 = np.round((plane - lo) / scale * 65535).astype(np.uint16)
    path = Path(tmpdir) / "plane.jp2"
    glymur.Jp2k(str(path), data=u16, cratios=[ratio])
    nbytes = path.stat().st_size
    dec = glymur.Jp2k(str(path))[:]
    rec = dec.astype(np.float64) / 65535 * scale + lo
    return rec, nbytes


def jpeg2000_codec(iq, ratio=8, **_):
    """Returns (iq_hat, rate_bits_per_complex_sample)."""
    with tempfile.TemporaryDirectory() as td:
        i_rec, i_bytes = _encode_plane(iq.real.astype(np.float64), ratio, td)
        q_rec, q_bytes = _encode_plane(iq.imag.astype(np.float64), ratio, td)
    iq_hat = (i_rec + 1j * q_rec).astype(np.complex64)
    rate = 8.0 * (i_bytes + q_bytes) / iq.size
    return iq_hat, rate
