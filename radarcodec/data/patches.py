"""Extract fixed-size complex patches from decoded L0 bursts into one .npz.

Patches are the unit of everything downstream: codecs compress a patch, metrics
and task models consume a patch. Keeping them small (default 256x256 complex)
is what lets the whole study run on a laptop GPU / free Colab.

Usage:
    python -m radarcodec.data.patches --l0-dir data/s1_l0 --out data/patches
"""

import argparse
from pathlib import Path

import numpy as np

from radarcodec.data.sentinel1 import read_l0_bursts


def extract_patches(iq, size=256, stride=256, min_power_db=-40.0):
    """Tile a burst into (N, size, size) complex64 patches, dropping near-empty ones."""
    rows, cols = iq.shape
    out = []
    ref = np.mean(np.abs(iq) ** 2) + 1e-12
    for r in range(0, rows - size + 1, stride):
        for c in range(0, cols - size + 1, stride):
            p = iq[r : r + size, c : c + size]
            power_db = 10 * np.log10(np.mean(np.abs(p) ** 2) / ref + 1e-12)
            if power_db > min_power_db:
                out.append(p.astype(np.complex64))
    return np.stack(out) if out else np.empty((0, size, size), np.complex64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l0-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--stride", type=int, default=256)
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--max-chunks", type=int, default=4, help="echo chunks per product; keeps laptop runtime sane")
    args = ap.parse_args()

    all_patches = []
    for safe in sorted(Path(args.l0_dir).glob("*.SAFE")):
        for burst_id, iq in read_l0_bursts(safe, max_chunks=args.max_chunks):
            p = extract_patches(iq, args.size, args.stride)
            print(f"{safe.name} burst {burst_id}: {len(p)} patches")
            all_patches.append(p)
    patches = np.concatenate(all_patches)

    rng = np.random.default_rng(args.seed)
    idx = rng.permutation(len(patches))
    n_val = int(len(patches) * args.val_frac)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "train.npz", iq=patches[idx[n_val:]])
    np.savez_compressed(out / "val.npz", iq=patches[idx[:n_val]])
    print(f"wrote {len(patches) - n_val} train / {n_val} val patches to {out}")


if __name__ == "__main__":
    main()
