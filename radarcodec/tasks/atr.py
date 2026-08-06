"""Frozen task model #2: ATR classifier on MSTAR chips.

Train once on uncompressed magnitude chips (train_frozen, in the torch env),
save the checkpoint, freeze it, then report accuracy on codec-reconstructed
chips at each rate (evaluate_frozen). The checkpoint is never fine-tuned on
compressed data.

Torch imports are local so the numpy-only harness env can import this module.
"""

import numpy as np

N_CLASSES = 3  # e.g. T72 / BMP2 / BTR70 public chips
CHIP = 128


def _model():
    import torch.nn as nn

    return nn.Sequential(
        nn.Conv2d(1, 32, 5, stride=2, padding=2), nn.ReLU(),
        nn.Conv2d(32, 64, 5, stride=2, padding=2), nn.ReLU(),
        nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(),
        nn.AdaptiveAvgPool2d(1), nn.Flatten(),
        nn.Linear(128, N_CLASSES),
    )


def _norm(mag):
    """Per-chip log-magnitude normalization — must be identical at train and eval."""
    x = np.log1p(np.abs(mag)).astype(np.float32)
    return (x - x.mean()) / (x.std() + 1e-6)


def _augment(batch, rng, max_shift=8):
    """Random per-chip translation (zero-padded) — the standard MSTAR augmentation."""
    out = np.empty_like(batch)
    for i, chip in enumerate(batch):
        dr, dc = rng.integers(-max_shift, max_shift + 1, 2)
        shifted = np.zeros_like(chip)
        src = chip[max(0, -dr) : chip.shape[0] - max(0, dr), max(0, -dc) : chip.shape[1] - max(0, dc)]
        shifted[max(0, dr) : max(0, dr) + src.shape[0], max(0, dc) : max(0, dc) + src.shape[1]] = src
        out[i] = shifted
    return out


def train_frozen(chips, labels, checkpoint, epochs=30, seed=1337, augment=True):
    """chips: (N, CHIP, CHIP) magnitude (or complex; magnitude is taken)."""
    import torch

    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    xn = np.stack([_norm(c) for c in chips])
    y = torch.from_numpy(np.asarray(labels, dtype=np.int64))
    model = _model()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    loss_fn = torch.nn.CrossEntropyLoss()
    for epoch in range(epochs):
        perm = torch.randperm(len(xn))
        for i in range(0, len(xn), 64):
            b = perm[i : i + 64]
            xb = xn[b.numpy()]
            if augment:
                xb = _augment(xb, rng)
            opt.zero_grad()
            loss = loss_fn(model(torch.from_numpy(xb[:, None])), y[b])
            loss.backward()
            opt.step()
        sched.step()
        print(f"epoch {epoch}: loss {loss.item():.4f}")
    torch.save(model.state_dict(), checkpoint)
    return checkpoint


def evaluate_frozen(chips, labels, checkpoint):
    """Accuracy of the frozen checkpoint on (possibly codec-degraded) chips."""
    import torch

    model = _model()
    model.load_state_dict(torch.load(checkpoint, map_location="cpu"))
    model.eval()
    x = torch.from_numpy(np.stack([_norm(c) for c in chips])[:, None])
    with torch.no_grad():
        pred = model(x).argmax(1).numpy()
    return float(np.mean(pred == np.asarray(labels)))
