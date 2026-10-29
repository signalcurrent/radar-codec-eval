"""Measure the ACTUAL FDBAQ bitstream rate of the Illinois crop from the Level-0 packet headers: user-data bits per
complex sample for the echoes that make up data/s1_sm/chunk_crop.npz (first echo chunk with >= 256 echoes, centre
4096 rows). This is the true lossless classical rate for the re-compression scenario (retention 1.0, spurious 0).
Writes reports/fdbaq_rate.json. No codec, no log rows.

    python scripts/measure_fdbaq_rate.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AZ = 4096


def main():
    import sentinel1decoder as s1d
    safe = sorted((ROOT / "data" / "s1_sm").glob("*.SAFE"))[0]
    dats = sorted(p for p in safe.glob("*.dat") if "-vv-" in p.name and not p.name.endswith(("annot.dat", "index.dat")))
    f = s1d.Level0File(str(dats[0]))
    pm = f.packet_metadata
    sig = pm.groupby(level=0)["Signal Type"].agg(["first", "count"])
    chunks = sig[(sig["first"] == s1d.SignalType.ECHO) & (sig["count"] >= 256)].index
    chunk = chunks[0]
    rows = pm.loc[chunk]
    n = len(rows)
    r0 = (n - AZ) // 2
    sel = rows.iloc[r0:r0 + AZ]
    cols = {c: c for c in sel.columns}
    pdl = next(c for c in sel.columns if "Packet Data Length" in c)
    nq = next(c for c in sel.columns if "Number of Quads" in c)
    baq = [c for c in sel.columns if "BAQ" in c]
    # Packet Data Length is (bytes - 1) per CCSDS; the secondary header is 62 bytes; user data = PDL + 1 - 62
    user_bytes = sel[pdl].astype(np.int64) + 1 - 62
    quads = sel[nq].astype(np.int64)
    bits_per_complex = 8.0 * user_bytes / (2.0 * quads)
    out = {"chunk": int(chunk), "n_echoes_in_chunk": int(n), "rows_used": [int(r0), int(r0 + AZ)],
           "quads_per_echo": {"min": int(quads.min()), "max": int(quads.max())},
           "user_bytes_per_echo": {"min": int(user_bytes.min()), "mean": float(user_bytes.mean()), "max": int(user_bytes.max())},
           "fdbaq_bits_per_complex_sample": {"mean": round(float(bits_per_complex.mean()), 4),
                                             "min": round(float(bits_per_complex.min()), 4),
                                             "max": round(float(bits_per_complex.max()), 4)},
           "baq_columns": {c: str(sel[c].iloc[0]) for c in baq},
           "note": "user data = Packet Data Length + 1 - 62 (secondary header); 2 real samples per quad pair -> rate per complex sample = 8*bytes/(2*quads); includes FDBAQ block side information."}
    (ROOT / "reports" / "fdbaq_rate.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
