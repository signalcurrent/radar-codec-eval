"""Regenerate latex/s1-scene-quicklook.png from the focused reference with the Fig. 5 ringing crop
marked (JSTARS revision E6; crop centre/half-window from reports/ringing_crop.json). The previous
quicklook is kept as latex/s1-scene-quicklook_v2.png. Log-intensity, full 4096 x 8192 focused image
downsampled 2:1 in each axis by block mean of power before the dB scaling.

    python scripts/make_scene_figure_marked.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "latex" / "s1-scene-quicklook.png"
BACKUP = ROOT / "latex" / "s1-scene-quicklook_v2.png"
DOWN = 4  # 4096x8192 -> 1024x2048 (keeps the 1:2 aspect of the v2 figure)


def main():
    from eval_focused import load_crop
    from radarcodec.metrics.focus_rda import focus_stripmap

    crop = json.loads((ROOT / "reports" / "ringing_crop.json").read_text())
    r0, c0 = crop["center_full_rc"]
    w = crop["half_window"]
    raw, meta = load_crop()
    img = focus_stripmap(raw, meta)
    p = np.abs(img) ** 2
    h, wd = (p.shape[0] // DOWN) * DOWN, (p.shape[1] // DOWN) * DOWN
    pb = p[:h, :wd].reshape(h // DOWN, DOWN, wd // DOWN, DOWN).mean(axis=(1, 3))
    db = 10 * np.log10(np.maximum(pb, pb.max() * 1e-9))
    lo, hi = np.percentile(db, [2, 99.8])
    g = np.clip((db - lo) / (hi - lo), 0, 1)
    im = Image.fromarray((g * 255).astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = (c0 - w) / DOWN, (r0 - w) / DOWN, (c0 + w) / DOWN, (r0 + w) / DOWN
    for k in range(3):
        d.rectangle([x0 - k, y0 - k, x1 + k, y1 + k], outline=(255, 40, 40))
    d.text((x1 + 8, y0 - 2), "Fig. 5 crop", fill=(255, 40, 40))
    if OUT.exists() and not BACKUP.exists():
        OUT.replace(BACKUP)
    im.save(OUT, optimize=True)
    print(f"wrote {OUT} {im.size}; crop box rows {r0 - w}:{r0 + w}, cols {c0 - w}:{c0 + w} (full-image coords); "
          f"figure box x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f}")


if __name__ == "__main__":
    main()
