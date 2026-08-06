"""Sentinel-1 Level-0 reading: thin wrapper over the `sentinel1decoder` package.

L0 products ship as .SAFE directories with one measurement .dat per
polarization, packetized as acquisition chunks. Echo-type chunks hold the raw
radar returns (post-onboard-FDBAQ); cal/noise chunks are skipped. Each echo
chunk decodes to a rectangular complex array (n_echoes, n_samples).
"""

from pathlib import Path

import numpy as np


def read_l0_bursts(safe_dir, pol="vv", min_echoes=256, max_chunks=None):
    """Yield (chunk_id, iq complex64 [n_echoes, n_samples]) from a .SAFE dir."""
    import sentinel1decoder as s1d

    safe_dir = Path(safe_dir)
    dats = sorted(p for p in safe_dir.glob("*.dat")
                  if f"-{pol}-" in p.name and not p.name.endswith(("annot.dat", "index.dat")))
    if not dats:
        raise FileNotFoundError(f"no {pol} measurement .dat under {safe_dir}")

    for dat in dats:
        f = s1d.Level0File(str(dat))
        pm = f.packet_metadata
        sig = pm.groupby(level=0)["Signal Type"].agg(["first", "count"])
        is_echo = sig["first"] == s1d.SignalType.ECHO  # values are enum members, not strings
        echo_chunks = sig[is_echo & (sig["count"] >= min_echoes)].index
        if max_chunks is not None:
            echo_chunks = echo_chunks[:max_chunks]
        for chunk in echo_chunks:
            iq = np.asarray(f.get_acquisition_chunk_data(chunk), dtype=np.complex64)
            row = pm.loc[chunk].iloc[0]
            chirp = {
                "fs": s1d.utilities.range_dec_to_sample_rate(row["Range Decimation"]),
                "txprr": float(row["Tx Ramp Rate"]),
                "txpsf": float(row["Tx Pulse Start Frequency"]),
                "txpl": float(row["Tx Pulse Length"]),
            }
            yield int(chunk), iq, chirp
