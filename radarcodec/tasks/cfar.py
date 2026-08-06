"""Frozen task model #1: 2-D cell-averaging CFAR detector.

Parameters (pfa, guard, train) are fixed in the config, tuned once on
uncompressed data, and never adjusted per-codec — that is what makes
"detection preserved under compression" a falsifiable claim.

Utility metric: probability of detection at fixed Pfa, using detections on the
uncompressed image as ground truth (so the question is literally "does the
detector still see what it saw before compression").
"""

import numpy as np
from scipy.ndimage import maximum_filter, uniform_filter


def ca_cfar(power, pfa=1e-4, guard=2, train=8):
    """Boolean detection map from a power image via 2-D CA-CFAR."""
    power = np.asarray(power, dtype=np.float64)
    outer = 2 * (guard + train) + 1
    inner = 2 * guard + 1
    n_outer, n_inner = outer**2, inner**2
    n_train = n_outer - n_inner
    # training-ring mean = (outer-box sum - inner-box sum) / ring count
    ring_mean = (
        uniform_filter(power, outer, mode="reflect") * n_outer
        - uniform_filter(power, inner, mode="reflect") * n_inner
    ) / n_train
    # CA-CFAR threshold factor for exponentially-distributed clutter power
    alpha = n_train * (pfa ** (-1.0 / n_train) - 1.0)
    return power > alpha * np.maximum(ring_mean, 1e-30)


def _to_centroids(det):
    """Reduce a detection map to local-maximum points to compare across images."""
    peaks = det & (maximum_filter(det.astype(np.uint8), 3) == det)
    return np.argwhere(peaks)


def detection_agreement(iq_ref, iq_hat, pfa=1e-4, guard=2, train=8, tol=3):
    """Pd/Pfa of detections on the reconstruction vs. detections on the reference.

    Returns dict with pd (fraction of reference detections recovered within
    `tol` pixels), n_false (new detections absent from reference), n_ref.
    """
    ref_pts = _to_centroids(ca_cfar(np.abs(iq_ref) ** 2, pfa, guard, train))
    hat_pts = _to_centroids(ca_cfar(np.abs(iq_hat) ** 2, pfa, guard, train))
    if len(ref_pts) == 0:
        return {"pd": float("nan"), "n_false": int(len(hat_pts)), "n_ref": 0}
    from scipy.spatial import cKDTree

    tree = cKDTree(hat_pts) if len(hat_pts) else None
    hits = 0
    if tree is not None:
        d, _ = tree.query(ref_pts, k=1)
        hits = int(np.sum(d <= tol))
    matched_hat = 0
    if len(hat_pts) and len(ref_pts):
        d2, _ = cKDTree(ref_pts).query(hat_pts, k=1)
        matched_hat = int(np.sum(d2 <= tol))
    return {
        "pd": hits / len(ref_pts),
        "n_false": int(len(hat_pts) - matched_hat),
        "n_ref": int(len(ref_pts)),
    }
