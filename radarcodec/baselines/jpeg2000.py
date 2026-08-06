"""JPEG2000 baseline applied per I/Q plane (16-bit scaled), via Pillow/OpenJPEG.

Rate is measured from actual encoded bytes of both planes.
"""

import io

import numpy as np
from PIL import Image


def _encode_plane(plane, ratio):
    lo, hi = plane.min(), plane.max()
    scale = (hi - lo) + 1e-12
    u16 = np.round((plane - lo) / scale * 65535).astype(np.uint16)
    buf = io.BytesIO()
    Image.fromarray(u16, mode="I;16").save(
        buf, format="JPEG2000", quality_mode="rates", quality_layers=[ratio], irreversible=True
    )
    nbytes = buf.tell()
    buf.seek(0)
    dec = np.asarray(Image.open(buf), dtype=np.float64)
    rec = dec / 65535 * scale + lo
    return rec, nbytes


def jpeg2000_codec(iq, ratio=8, **_):
    """Returns (iq_hat, rate_bits_per_complex_sample)."""
    i_rec, i_bytes = _encode_plane(iq.real.astype(np.float64), ratio)
    q_rec, q_bytes = _encode_plane(iq.imag.astype(np.float64), ratio)
    iq_hat = (i_rec + 1j * q_rec).astype(np.complex64)
    rate = 8.0 * (i_bytes + q_bytes) / iq.size
    return iq_hat, rate
