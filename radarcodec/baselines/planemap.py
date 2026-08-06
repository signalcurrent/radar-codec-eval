"""Mapping v2: the single real-plane <-> uint16 mapping every plane-based
codec uses, in every domain (FINDINGS.md Amendment 5).

Symmetric clip at the 99.99th percentile of |value|, bounds carried as side
info (2 floats per plane, negligible rate). Robust to the heavy-tailed
amplitude distribution of focused SAR that made min/max mapping degenerate.
Decided once, applied to JPEG2000 and HEVC in raw and transformed domains;
the learned codec is granted this identical mapping and no more.
"""

import numpy as np

MAPPING_VERSION = "v2-pctclip99.99"
_Q = 99.99


def plane_to_u16(plane):
    c = float(np.percentile(np.abs(plane), _Q))
    c = max(c, 1e-12)
    x = np.clip(plane, -c, c)
    u16 = np.round((x + c) / (2 * c) * 65535).astype(np.uint16)
    return u16, c


def u16_to_plane(u16, c):
    return u16.astype(np.float64) / 65535 * 2 * c - c
