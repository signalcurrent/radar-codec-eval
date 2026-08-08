"""Extract focused-domain training patches from Gotcha mis2, held-out clean
of the evaluation window (pulses 5585:7449, AFRL's worked example).

Tiles the 154,180-pulse file into non-overlapping 1864-pulse windows (same
size as the eval crop), forms each into a range-Doppler image, and cuts
32x32 complex patches from each (Gotcha's image is 384x1864 -- far smaller
than Sentinel-1's, so a much smaller patch size than the 256px Illinois
patches). Any window overlapping the eval range is dropped entirely, not
just cropped -- full held-out separation, not adjacency.

    python scripts/extract_gotcha_patches.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from radarcodec.data.gotcha import form_image, n_pulses_in_file, read_phase_history

PH_PATH = "data/gotcha_gmti/durangoChallenge_chan1_mis2_PH"
EVAL_START, EVAL_N = 5585, 1864
EVAL_END = EVAL_START + EVAL_N
WINDOW = 1864  # matches eval crop CPI length
# PATCH=64: the encoder's four stride-2 layers give 16x downsampling; 32px
# patches leave only a 1x1 latent (too degenerate). 64px gives a 4x4 latent
# (Illinois's 128px patches gave 8x8) -- smaller but not degenerate, sized
# to this scene's actual dimensions (range axis is only 384px total).
PATCH, STRIDE = 64, 64
MIN_POWER_DB = -50.0
SEED = 1337


def extract_patches(img, size=PATCH, stride=STRIDE, min_power_db=MIN_POWER_DB):
    rows, cols = img.shape
    ref = np.mean(np.abs(img) ** 2) + 1e-12
    out = []
    for r in range(0, rows - size + 1, stride):
        for c in range(0, cols - size + 1, stride):
            p = img[r : r + size, c : c + size]
            power_db = 10 * np.log10(np.mean(np.abs(p) ** 2) / ref + 1e-12)
            if power_db > min_power_db:
                out.append(p.astype(np.complex64))
    return out


def main():
    total = n_pulses_in_file(PH_PATH)
    print(f"total pulses: {total}; eval window [{EVAL_START},{EVAL_END}) held out")

    all_patches = []
    n_windows = 0
    for start in range(1, total - WINDOW + 1, WINDOW):
        end = start + WINDOW
        if not (end <= EVAL_START or start >= EVAL_END):
            continue  # overlaps eval window -- skip entirely, not just crop
        ph = read_phase_history(PH_PATH, start_pulse=start, n_pulses=WINDOW)
        img = form_image(ph)
        patches = extract_patches(img)
        all_patches.extend(patches)
        n_windows += 1
        if n_windows % 20 == 0:
            print(f"  {n_windows} windows, {len(all_patches)} patches so far...")

    patches = np.stack(all_patches)
    print(f"{n_windows} training windows -> {len(patches)} patches {patches.shape[1:]}")

    rng = np.random.default_rng(SEED)
    idx = rng.permutation(len(patches))
    n_val = max(1, int(len(patches) * 0.15))
    out = Path("data/gotcha_patches")
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "train.npz", iq=patches[idx[n_val:]])
    np.savez_compressed(out / "val.npz", iq=patches[idx[:n_val]])
    print(f"wrote {len(patches) - n_val} train / {n_val} val patches to {out}")


if __name__ == "__main__":
    main()
