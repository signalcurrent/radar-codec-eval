"""E7c: crop-exact FDBAQ bitstream rate. Re-parses the user data of the 4,096 crop echoes bit by bit (FDBAQ Huffman
trees per the S-1 space-packet spec; same trees as sentinel1decoder v1.0.0 _fdbaq_decoder.py) and attributes
sample-code bits to 128-quad blocks (the two blocks straddling the crop edge by block fraction), so the rate of the study crop (central 8,192 of 20,072 samples) is measured
rather than the line average (E7b). Self-check: parsed bytes == decoder user-data bounds == header user bytes for every packet.

    python scripts/measure_fdbaq_rate_crop.py [--stride N]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[1]
AZ, RG = 4096, 8192

TREES = {
    0: (0, (1, (2, 3))),
    1: (0, (1, (2, (3, 4)))),
    2: (0, (1, (2, (3, (4, (5, 6)))))),
    3: ((0, 1), (2, (3, (4, (5, (6, (7, (8, 9)))))))),
    4: ((0, (1, 2)), ((3, 4), ((5, 6), (7, (8, (9, ((10, 11), ((12, 13), (14, 15))))))))),
}
W = 12  # window bits: 1 sign + max depth 9 (BRC4) <= 12


def build_table(tree):
    """window value (W bits, MSB first, first bit = sign) -> total bits consumed (sign + code)."""
    tab = [0] * (1 << W)
    for v in range(1 << W):
        bits = [(v >> (W - 1 - k)) & 1 for k in range(W)]
        node = tree
        k = 1  # skip sign
        while not isinstance(node, int):
            node = node[bits[k]]
            k += 1
        tab[v] = k
    return tab


TABS = {b: build_table(t) for b, t in TREES.items()}


def parse_packet(data, nq):
    """Return (brc[], thidx[], bits_per_channel_block[4][nblk] (sample-code bits only), bytes_consumed, bytes_available)."""
    nblk = -(-nq // 128)
    arr = np.frombuffer(data, dtype=np.uint8)
    bits = np.unpackbits(arr)
    bits = np.concatenate([bits, np.zeros(W, dtype=np.uint8)])
    pow2 = (1 << np.arange(W - 1, -1, -1)).astype(np.int64)
    win = (np.lib.stride_tricks.sliding_window_view(bits, W).astype(np.int64) @ pow2).tolist()
    bl = bits.tolist()
    nbits = len(arr) * 8
    pos = 0
    brc, thidx = [], []
    chan_bits = [[0] * nblk for _ in range(4)]
    for ch in range(4):
        done = 0
        for b in range(nblk):
            if ch == 0:
                brc.append((bl[pos] << 2) | (bl[pos + 1] << 1) | bl[pos + 2])
                pos += 3
            if ch == 2:
                v = 0
                for k in range(8):
                    v = (v << 1) | bl[pos + k]
                thidx.append(v)
                pos += 8
            tab = TABS[brc[b]]
            n = min(128, nq - done)
            start = pos
            for _ in range(n):
                pos += tab[win[pos]]
            chan_bits[ch][b] = pos - start
            done += n
        # align to the next 16-bit word boundary
        if pos % 8:
            pos += 8 - pos % 8
        if (pos // 8) % 2:
            pos += 8
    # the packet's user data field is padded to a 32-bit word after the last channel
    if (pos // 8) % 4:
        pos += 8 * (4 - (pos // 8) % 4)
    return brc, thidx, chan_bits, pos // 8, nbits // 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=1)
    a = ap.parse_args()
    import sentinel1decoder as s1d
    from sentinel1decoder._sentinel1decoder import decode_packet_headers
    safe = sorted((ROOT / "data" / "s1_sm").glob("*.SAFE"))[0]
    dats = sorted(p for p in safe.glob("*.dat") if "-vv-" in p.name and not p.name.endswith(("annot.dat", "index.dat")))
    raw = dats[0].read_bytes()
    _, bounds = decode_packet_headers(raw)
    f = s1d.Level0File(str(dats[0]))
    pm = f.packet_metadata
    sig = pm.groupby(level=0)["Signal Type"].agg(["first", "count"])
    chunk = sig[(sig["first"] == s1d.SignalType.ECHO) & (sig["count"] >= 256)].index[0]
    rows = pm.loc[chunk]
    n = len(rows)
    r0 = (n - AZ) // 2
    sel = rows.iloc[r0:r0 + AZ]
    pdl = next(c for c in sel.columns if "Packet Data Length" in c)
    nqc = next(c for c in sel.columns if "Number of Quads" in c)
    # global packet numbers = positional index into the full metadata frame (same order as the file)
    first = pm.index.get_loc(chunk)
    if isinstance(first, slice):
        first = first.start
    else:
        first = int(np.flatnonzero(first)[0])
    gps = [first + r0 + i for i in range(AZ)]
    nq = int(sel[nqc].iloc[0])
    ns = 2 * nq
    c0 = (ns - RG) // 2
    nblk = -(-nq // 128)
    # sample s (0..ns-1) belongs to quad s//2 and block (s//2)//128; a block covers samples [256b, 256b+256)
    frac = np.zeros(nblk)
    for b in range(nblk):
        lo, hi = 256 * b, min(256 * b + 256, ns)
        frac[b] = max(0, min(hi, c0 + RG) - max(lo, c0)) / (hi - lo)
    t0 = time.time()
    crop_rates, line_rates, line_parsed = [], [], []
    brc_line = np.zeros((nblk, 5))
    brc_crop = np.zeros(5)
    block_bits_sum = np.zeros(nblk)
    used = 0
    mism = []
    for i in range(AZ):
        if i % a.stride:
            continue
        gp = gps[i]
        off, ln = bounds[gp]
        data = raw[off:off + ln]
        # sentinel1decoder's 'Packet Data Length' column is already the raw CCSDS field + 1 (verified against the raw
        # primary header, 2026-10-29), so user bytes = column - 62 (= raw PDL + 1 - 62).
        exp_bytes = int(sel[pdl].iloc[i]) - 62
        brc, thidx, cb, nbytes, have = parse_packet(data, nq)
        # the parse must land exactly on the decoder's user-data bounds AND on the header figure, else the Huffman walk desynchronised.
        if nbytes != have or nbytes != exp_bytes:
            sys.exit(f"SELF-CHECK FAILED packet {gp}: parsed {nbytes} bytes, header says {exp_bytes}, user data len {have}")
        mism.append(exp_bytes - nbytes)
        cb = np.asarray(cb, dtype=np.float64)  # 4 x nblk sample-code bits
        blk = cb.sum(0) + 11.0  # + BRC(3) + THIDX(8)
        block_bits_sum += blk
        crop_rates.append(float((blk * frac).sum()) / RG)
        line_rates.append(8.0 * exp_bytes / ns)
        line_parsed.append(float(blk.sum()) / ns)
        for b, v in enumerate(brc):
            brc_line[b, v] += 1
            if frac[b] > 0:
                brc_crop[v] += frac[b]
        used += 1
        if used % 256 == 0:
            print(f"{used} echoes, {time.time()-t0:.0f}s, crop {np.mean(crop_rates):.4f} line {np.mean(line_rates):.4f}", flush=True)
    crop_rates = np.asarray(crop_rates)
    line_rates = np.asarray(line_rates)
    per_block_rate = block_bits_sum / used / 256.0
    out = {
        "chunk": int(chunk), "rows_used": [int(r0), int(r0 + AZ)], "stride": a.stride, "echoes_parsed": used,
        "quads_per_echo": nq, "samples_per_echo": ns, "crop_cols": [c0, c0 + RG], "blocks_per_echo": nblk,
        "blocks_touching_crop": [int(np.flatnonzero(frac)[0]), int(np.flatnonzero(frac)[-1])],
        "self_check": "parsed bytes (32-bit padded) == decoder user-data bounds == header user bytes for every parsed packet (PASS)",
        "header_minus_parsed_bytes": {"min": int(min(mism)), "max": int(max(mism))},
        "crop_bits_per_complex_sample": {"mean": round(float(crop_rates.mean()), 4), "min": round(float(crop_rates.min()), 4),
                                         "max": round(float(crop_rates.max()), 4)},
        "line_bits_per_complex_sample_from_headers": {"mean": round(float(line_rates.mean()), 4)},
        "line_bits_per_complex_sample_parsed_excl_padding": {"mean": round(float(np.mean(line_parsed)), 4)},
        "per_block_rate_mean_over_echoes": [round(float(x), 3) for x in per_block_rate],
        "brc_histogram_line_blocks": {str(k): int(brc_line[:, k].sum()) for k in range(5)},
        "brc_histogram_crop_blocks_weighted": {str(k): round(float(brc_crop[k]), 1) for k in range(5)},
        "side_info_convention": "3 BRC + 8 THIDX bits per 128-quad block, apportioned by the fraction of the block inside the crop; channel word-alignment padding excluded (<= 60 bits per echo)",
        "huffman_trees": "S-1 space packet spec FDBAQ trees (sentinel1decoder v1.0.0 _fdbaq_decoder.py); bits per sample = 1 sign + tree depth",
    }
    (ROOT / "reports" / "fdbaq_rate_crop.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
