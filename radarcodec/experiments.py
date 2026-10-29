"""Append-only experiment logging.

One JSON line per run, keyed by config hash + seed. Curves in reports/ are
regenerated from this file; results are never edited or overwritten by hand.
"""

import hashlib
import json
import time
from pathlib import Path


def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]


def log_run(out_path, cfg, record):
    # 2026-10-29 (E0): every row now records which detection reduction and HEVC pipeline produced it.
    import os
    legacy = os.environ.get("RADARCODEC_LEGACY") == "1"
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config_hash": config_hash(cfg),
        "seed": cfg.get("seed"),
        "scorer": "legacy-pixels" if legacy else "peak-v2",
        "hevc": "legacy-16to12-interframe" if legacy else "intra12",
        **record,
    }
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")
    return row
