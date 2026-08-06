"""Build TRANSFORMED-domain training patches from the stripmap scene.

Train/eval split by acquisition chunk: the eval crop (chunk_crop.npz cache)
came from the FIRST qualifying echo chunk; training patches come from the
SUBSEQUENT chunks — zero overlap with the evaluation data.

    python scripts/build_tfocus_patches.py --out data/tfocus_patches
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from radarcodec.baselines.transform_codec import forward
from radarcodec.data.sentinel1 import read_l0_bursts

SAFE_GLOB = "data/s1_sm/*.SAFE"


def tile(img, size=128, stride=128):
    rows, cols = img.shape
    out = []
    for r in range(0, rows - size + 1, stride):
        for c in range(0, cols - size + 1, stride):
            out.append(img[r : r + size, c : c + size])
    return np.stack(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/tfocus_patches")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--chunks", type=int, default=3, help="training chunks AFTER the held-out first")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    safe = sorted(Path().glob(SAFE_GLOB))[0]
    patches = []
    for i, (cid, iq, meta) in enumerate(read_l0_bursts(safe, max_chunks=args.chunks + 1)):
        if i == 0:
            print(f"chunk {cid}: HELD OUT (eval crop source)")
            continue
        y = forward(iq, meta, "full")
        del iq
        p = tile(y, args.size)
        del y
        print(f"chunk {cid}: {len(p)} transformed patches")
        patches.append(p)
    allp = np.concatenate(patches)
    rng = np.random.default_rng(args.seed)
    idx = rng.permutation(len(allp))
    n_val = int(0.1 * len(allp))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "train.npz", iq=allp[idx[n_val:]])
    np.savez_compressed(out / "val.npz", iq=allp[idx[:n_val]])
    print(f"wrote {len(allp) - n_val} train / {n_val} val to {out}")


if __name__ == "__main__":
    main()
