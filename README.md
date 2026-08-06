# radar-codec

Feasibility prototype: neural compression of raw radar (SAR) data that preserves
**radar utility** — detection and recognition performance — rather than pixel
fidelity. Target: [redacted] [redacted] topic [redacted] (Phase I deliverable =
feasibility study + performance evaluation + algorithm implementation + synthetic
data). Public data only.

## The claim being tested

At a given compression ratio, a learned codec reconstructs raw I/Q such that
frozen downstream task models (CFAR detection, ATR classification) perform
**statistically indistinguishably from uncompressed**, while classical codecs
(FDBAQ/BAQ, JPEG2000, HEVC) at the same rate degrade them measurably.

PSNR/SSIM are deliberately not the headline metrics. Radar-specific quality
(impulse response width, PSLR, phase error) and task performance are.

## Two design principles

1. **Harness before model.** Baselines (BAQ, JPEG2000, HEVC) flow through the
   full pipeline first. If the model is a dead end, the evaluation harness is
   still the reusable half.
2. **Frozen task models.** The CFAR detector and ATR classifier are trained/tuned
   once on uncompressed data, frozen, then evaluated on decompressed data across
   rates. That makes "preserves radar utility" falsifiable.

## Timebox

Two weekends to a go/no-go signal.

- **Weekend 1:** data pipeline + baselines + frozen task models. End state: a
  rate-vs-detection curve for classical codecs alone.
- **Weekend 2:** I/Q autoencoder with learned entropy model (CompressAI
  scaffold), plotted on the same axes. If it doesn't land above the baselines,
  stop — the harness survives.

## Environment

Two environments, deliberately:

- **Harness (this machine, Python 3.14 OK):** numpy/scipy/matplotlib only.
  `pip install -r requirements.txt`
- **Model training (Python <= 3.13 required — torch/CompressAI do not support
  3.14 yet):** a 3.12 venv or free Colab. `pip install -r requirements-train.txt`

HEVC baseline requires `ffmpeg` (with libx265) on PATH.

## Data (git-ignored; see data/README.md for exact download steps)

- Sentinel-1 **Level-0 RAW** (complex I/Q echoes) via ASF — primary target;
  ESA's onboard FDBAQ is the operational baseline to beat.
- Sentinel-1 SLC for image-domain comparisons.
- MSTAR public SAR chips for the ATR evaluation.

## Reproduce

```bash
pip install -r requirements.txt
# 1. download data (see data/README.md), then extract patches:
python -m radarcodec.data.patches --l0-dir data/s1_l0 --out data/patches
# 2. baseline sweep (weekend 1):
python -m radarcodec.eval --config configs/baseline_sweep.yaml
# 3. neural codec (weekend 2, in the 3.12/Colab env):
python -m radarcodec.train --config configs/ae_small.yaml
python -m radarcodec.eval --config configs/ae_small.yaml
```

Every run appends one JSON line to `experiments/runs.jsonl` keyed by config hash
and seed. Curves in `reports/` are regenerated from that file; nothing is
overwritten by hand.

## Constraints

- Public data only. No classified or export-controlled sources.
- Standalone repo — no shared code or history with any other project.
- Small cropped patches first; no paid GPU until results show signal.
