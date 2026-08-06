"""HEVC (x265) baseline: I and Q planes as two frames of a 16-bit gray video.

Requires ffmpeg with libx265 on PATH. Rate measured from encoded byte count.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

def _find_ffmpeg():
    """PATH first, then the winget package dir (PATH isn't refreshed in this shell)."""
    hit = shutil.which("ffmpeg")
    if hit:
        return hit
    pkg = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for exe in pkg.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
        return str(exe)
    return "ffmpeg"


FFMPEG = _find_ffmpeg()


def hevc_codec(iq, qp=20, **_):
    """Returns (iq_hat, rate_bits_per_complex_sample)."""
    h, w = iq.shape
    planes = np.stack([iq.real, iq.imag]).astype(np.float64)
    lo, hi = planes.min(), planes.max()
    scale = (hi - lo) + 1e-12
    u16 = np.round((planes - lo) / scale * 65535).astype("<u2")

    with tempfile.TemporaryDirectory() as td:
        raw, enc, dec = Path(td) / "in.raw", Path(td) / "out.hevc", Path(td) / "dec.raw"
        raw.write_bytes(u16.tobytes())
        fmt = ["-f", "rawvideo", "-pix_fmt", "gray16le", "-s", f"{w}x{h}"]
        subprocess.run(
            [FFMPEG, "-y", "-v", "error", *fmt, "-i", str(raw),
             "-c:v", "libx265", "-x265-params", f"qp={qp}:lossless=0", str(enc)],
            check=True)
        nbytes = enc.stat().st_size
        subprocess.run(
            [FFMPEG, "-y", "-v", "error", "-i", str(enc),
             *fmt[:2], "-pix_fmt", "gray16le", str(dec)],
            check=True)
        out = np.frombuffer(dec.read_bytes(), dtype="<u2").reshape(2, h, w)

    rec = out.astype(np.float64) / 65535 * scale + lo
    iq_hat = (rec[0] + 1j * rec[1]).astype(np.complex64)
    rate = 8.0 * nbytes / iq.size
    return iq_hat, rate
