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


def hevc_codec(iq, qp=20, clip_q=99.99, **_):
    """Returns (iq_hat, rate_bits_per_complex_sample). clip_q: plane-mapping clip percentile (E10 control; 100 = min/max)."""
    from radarcodec.baselines.planemap import plane_to_u16, u16_to_plane

    h, w = iq.shape
    u16_i, c_i = plane_to_u16(iq.real.astype(np.float64), clip_q)
    u16_q, c_q = plane_to_u16(iq.imag.astype(np.float64), clip_q)
    u16 = np.ascontiguousarray(np.stack([u16_i, u16_q]).astype("<u2"))

    # 2026-10-29 (E0): libx265 accepts gray up to 12 bits, so the original call let ffmpeg convert the
    # gray16le planes to gray12le silently and coded I and Q as a two-frame video (Q inter-predicted from I).
    # Corrected pipeline (HEVC_TAG "intra12"): explicit gray12le, each plane its own all-intra stream, psy
    # tuning off. RADARCODEC_LEGACY=1 reproduces the archived behaviour.
    import os
    legacy = os.environ.get("RADARCODEC_LEGACY") == "1"
    with tempfile.TemporaryDirectory() as td:
        if legacy:
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
        else:
            planes, nbytes = [], 0
            for k in range(2):
                raw, enc, dec = Path(td) / f"in{k}.raw", Path(td) / f"out{k}.hevc", Path(td) / f"dec{k}.raw"
                raw.write_bytes(np.ascontiguousarray(u16[k]).tobytes())
                subprocess.run(
                    [FFMPEG, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray16le", "-s", f"{w}x{h}",
                     "-i", str(raw), "-pix_fmt", "gray12le", "-c:v", "libx265",
                     "-x265-params", f"qp={qp}:lossless=0:keyint=1:bframes=0:psy-rd=0:psy-rdoq=0", str(enc)],
                    check=True)
                nbytes += enc.stat().st_size
                subprocess.run(
                    [FFMPEG, "-y", "-v", "error", "-i", str(enc), "-f", "rawvideo", "-pix_fmt", "gray16le", str(dec)],
                    check=True)
                planes.append(np.frombuffer(dec.read_bytes(), dtype="<u2").reshape(h, w))
            out = np.stack(planes)

    iq_hat = (u16_to_plane(out[0], c_i) + 1j * u16_to_plane(out[1], c_q)).astype(np.complex64)
    rate = 8.0 * nbytes / iq.size
    return iq_hat, rate
