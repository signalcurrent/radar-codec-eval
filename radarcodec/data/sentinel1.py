"""Sentinel-1 Level-0 reading: thin wrapper over the `sentinel1decoder` package.

L0 products ship as .SAFE directories containing measurement .dat files of
packetized raw echoes. `sentinel1decoder` handles packet parsing and FDBAQ
decode; we return complex64 arrays of shape (n_echoes, n_samples) per burst.
"""

from pathlib import Path

import numpy as np


def read_l0_bursts(safe_dir, max_echoes=None):
    """Yield (burst_id, iq) complex64 arrays from a Sentinel-1 L0 .SAFE dir.

    Echo lines within a burst share a sampling configuration, so they stack
    into a rectangular array; different bursts may differ in width.
    """
    import sentinel1decoder

    safe_dir = Path(safe_dir)
    dat_files = sorted(safe_dir.glob("*.dat"))
    if not dat_files:
        raise FileNotFoundError(f"no measurement .dat files under {safe_dir}")
    for dat in dat_files:
        decoder = sentinel1decoder.Level0File(str(dat))
        for burst_id in decoder.get_burst_metadata().index.unique(level="Burst"):
            iq = decoder.get_burst_data(burst_id)
            iq = np.asarray(iq, dtype=np.complex64)
            if max_echoes is not None:
                iq = iq[:max_echoes]
            yield burst_id, iq
