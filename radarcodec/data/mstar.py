"""MSTAR Phoenix-format reader + dataset builder.

Each chip file = ASCII Phoenix header (self-describing length) followed by
big-endian float32 magnitude block then float32 phase block (rows*cols each).
Complex chip = mag * exp(1j * phase) — so codecs can compress complex data and
the ATR classifier consumes magnitude.

Build the npz datasets (standard protocol: train on 17 deg, test on 15 deg):

    python -m radarcodec.data.mstar --root data/mstar --out data/mstar_npz
"""

import argparse
from pathlib import Path

import numpy as np

CLASSES = ["BMP2", "BTR70", "T72"]  # class index = position in this list


def read_phoenix(path):
    """Return (complex64 chip [rows, cols], header dict)."""
    raw = Path(path).read_bytes()
    if b"[PhoenixHeaderVer" not in raw[:64]:  # files start with a stray newline
        raise ValueError(f"{path}: not a Phoenix file")
    header = {}
    text = raw[: raw.index(b"[EndofPhoenixHeader]") + 20].decode("ascii", "replace")
    for line in text.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            header[k.strip()] = v.strip()
    hlen = int(header["PhoenixHeaderLength"])
    rows = int(header["NumberOfRows"])
    cols = int(header["NumberOfColumns"])
    n = rows * cols
    data = np.frombuffer(raw, dtype=">f4", count=2 * n, offset=hlen)
    mag = data[:n].reshape(rows, cols).astype(np.float32)
    phase = data[n:].reshape(rows, cols).astype(np.float32)
    return (mag * np.exp(1j * phase)).astype(np.complex64), header


def center_crop(chip, size=128):
    r, c = chip.shape
    if r < size or c < size:
        out = np.zeros((size, size), chip.dtype)
        out[: min(r, size), : min(c, size)] = chip[:size, :size]
        return out
    r0, c0 = (r - size) // 2, (c - size) // 2
    return chip[r0 : r0 + size, c0 : c0 + size]


def load_split(targets_dir, size=128):
    """Walk TARGETS/{TRAIN,TEST}/... and return dict of split -> (chips, labels)."""
    out = {}
    for split in ["TRAIN", "TEST"]:
        chips, labels = [], []
        for cls_idx, cls in enumerate(CLASSES):
            for f in sorted(Path(targets_dir, split).rglob(f"{cls}/**/*")):
                if not f.is_file():
                    continue
                try:
                    chip, _ = read_phoenix(f)
                except (ValueError, KeyError):
                    continue  # JPGs, HTM files mixed into the tree
                chips.append(center_crop(chip, size))
                labels.append(cls_idx)
        out[split] = (np.stack(chips), np.array(labels, np.int64))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="data/mstar")
    ap.add_argument("--out", default="data/mstar_npz")
    ap.add_argument("--size", type=int, default=128)
    args = ap.parse_args()

    targets = next(Path(args.root).rglob("TARGETS"))
    splits = load_split(targets, args.size)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for split, (chips, labels) in splits.items():
        np.savez_compressed(out / f"{split.lower()}.npz", iq=chips, labels=labels)
        counts = {CLASSES[i]: int((labels == i).sum()) for i in range(len(CLASSES))}
        print(f"{split}: {len(chips)} chips {chips.shape[1:]}  {counts}")


if __name__ == "__main__":
    main()
