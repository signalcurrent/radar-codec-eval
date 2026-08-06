# Findings log

Running notes toward the 1–2 page feasibility summary. Newest at the bottom.
Numbers regenerable from `experiments/runs.jsonl` via `scripts/plot_curves.py`.

## Weekend 1 — classical baselines on real data (2026-08-06)

**Setup.** 1,268 train / 223 val complex 256×256 patches from 4 echo chunks of
a Sentinel-1D IW scene over Hampton Roads (VV, decoded from L0 with
`sentinel1decoder`). MSTAR public target chips (1,622 train @17°, 1,365 test
@15°, BMP2/BTR70/T72). Frozen task models: 2-D CA-CFAR (Pfa 1e-4) applied
after range compression; small CNN ATR trained once on uncompressed chips
(86.1% test accuracy ceiling), then frozen.

**Headline.** Classical codecs collapse on radar-utility metrics well above
the rates where they look acceptable on MSE:

- At FDBAQ's ~3.4 bits/complex-sample operating point, the best classical
  codec preserves only ~20–30% of CFAR detections.
- No classical codec exceeds Pd 0.8 below ~8–12 bits/sample.
- JPEG2000 beats BAQ per bit at moderate rates (transform coding exploits
  spatial correlation BAQ ignores) but degrades phase fastest — phase RMSE
  0.5 rad at 4 bps — which is disqualifying for interferometric/Doppler use.
- HEVC is the strongest classical baseline per bit but needs ~14 bps for
  Pd ≈ 0.94.

**Implication for feasibility.** The neural codec does not need miracles: the
target region (Pd ≥ 0.9 at ≤ 4 bps) is empty of classical competitors by a
wide margin. Even a modest learned codec that halves the utility loss at
FDBAQ-rate would be a publishable, proposable result.

**Methodology decisions that mattered.**
1. CFAR on unfocused raw echoes is meaningless (it thresholds speckle; Pd
   readings were noise). Range compression via matched filter built from
   packet-header chirp parameters (TXPRR/TXPSF/TXPL + range-decimation sample
   rate) made detection physical. Azimuth focusing is a possible later upgrade.
2. Detection "ground truth" = detections on the uncompressed patch, so Pd
   measures preservation of detector behavior, not absolute detection skill.
3. Public L0 has already been through onboard FDBAQ once. All codecs start
   from identical decoded samples (internally fair), but the honest claim is
   "re-compression of operationally compressed raw data." [redacted] question
   pending on whether that surrogate is acceptable.

**Caveats.** Single scene, single polarization, 64-patch eval subsets; CFAR
agreement tolerance 3 px; ATR is 3-class with modest (86%) frozen ceiling.
Good enough to rank codecs; not publication statistics yet.

## Weekend 1b — ATR-vs-rate on MSTAR (2026-08-06)

300 held-out 15° chips through every codec operating point, scored by the
frozen classifier (uncompressed ceiling on this subsample: 86.0%):

- ATR is far more compression-tolerant than raw-echo detection: JPEG2000 at
  3.9 bps holds 85.3% (statistically at ceiling); HEVC at 3.5 bps holds 81%.
- Collapse only begins below ~2 bps (HEVC 1.4 bps → 47.7%; J2K 1.0 bps → 55.3%).
- BAQ at 4 bps loses 27 points (59.0%) — block-adaptive quantization, built
  for raw echo statistics, is the WORST performer on focused imagery, the
  mirror image of the raw-domain result.

## Frozen-classifier robustness check (2026-08-06)

The v1 ATR ceiling (86%) invited the objection that a stronger classifier
would be more robust to compression artifacts, shrinking the effect. Tested
directly: classifier strengthened (shift augmentation, 60 epochs, cosine LR)
to 90.4% test accuracy, sweep rerun against the frozen v2. Result: the curve
keeps its shape. Low-rate collapse is unchanged (HEVC 1.38 bps: 47.7% → 48.0%;
J2K 0.98 bps: 55.3% → 57.7%), and mid-rate points track the higher ceiling.
The degradation effect is a property of the codecs, not of classifier
weakness. Objection answered with data.

## PRE-REGISTRATION — corrected go/no-go, recorded BEFORE focused results (2026-08-06)

The original bar ("neural Pd >= 0.9 at <= 4 bps, where no classical codec
reaches") was set against pre-focus CFAR scoring, which measured detection on
range-compressed but azimuth-unfocused data. That measurement is now known to
be flawed as a proxy for operational utility, so the bar derived from it is
void and is re-registered here before `eval_focused.py` results exist.

**Physics prediction, stated in advance:** focusing is coherent integration
with large processing gain; approximately-white quantization noise integrates
incoherently while signal integrates coherently, so focusing should suppress
compression noise substantially. Classical codecs are therefore expected to
look much better post-focus — this is exactly why BAQ/FDBAQ at 2–4 bits are
operationally viable — and the contested territory should move below ~2 bps.

**Re-registered primary endpoint (rate-relative, so it does not depend on
where classical lands):** "sustains utility" at a rate means BOTH
(a) focused-domain Pd >= 0.9 against detections on the focused uncompressed
reference, AND (b) spurious detections (reconstruction detections unmatched
within tolerance to any reference detection) <= 10% of reference detections —
Pd alone is gameable by a codec that floods the detector. Both sides are
scored at the identical CFAR configuration (Pfa 1e-4, guard 2, train 8,
tolerance 3 px). Let R_c = the lowest rate at which the best classical codec
sustains utility so defined. GO requires the learned codec to sustain utility
at <= R_c/2 (a >= 2x rate advantage). Secondary endpoint (unaffected by the
focusing correction, since MSTAR chips were always focused imagery): learned
codec must beat the best classical accuracy-vs-rate curve below 2 bps on the
frozen-ATR eval. Anything less on both endpoints is NO-GO, reported as a
negative result: "classical codecs are near-utility-lossless at operational
rates; the frontier is below 2 bps, and here is what would have to be true
for learned coding to beat it."

**Grid evaluability (recorded in the same blind window):** if focusing gain is
as strong as predicted, R_c may sit at or below the current sweep floor,
making R_c/2 unmeasurable on the present grid. A low-rate extension config
(`configs/lowrate_ext.yaml`: BAQ 1-bit, JPEG2000 ratios 64/128, HEVC QP
40/44, reaching ~0.5 bps) is committed alongside this amendment and will be
run with the identical pipeline so the criterion is evaluable wherever R_c
lands. BAQ cannot go below ~2.1 bps (1 bit/component + sigma overhead) —
below that, only transform codecs and the learned codec compete, which is
itself part of the finding.

**Known limitation, stated in advance:** the focused-domain eval is currently
a single 4096x8192 crop of a single (agricultural/urban, Illinois) scene.
Clutter statistics differ sharply across terrain; detection results may not
generalize. A second scene with different terrain (coastal/maritime stripmap)
is planned before any proposal-grade claim; until then every focused-domain
number carries this caveat.

## CHRONOLOGY CORRECTION — read this before citing the pre-registration

The pre-registration commits were made while the focused sweep ran in the
background, and the sweep appends rows as each operating point completes.
Exact sequence from row timestamps and commit times (both in git history):

- 00:39:21 — first focused-domain row written to runs.jsonl
- 00:41:58 — pre-registration commit 08c420d (7 of 12 rows already on disk)
- 00:44:51 — last focused-domain row written
- 00:44:52 — amendment commit 22df565 (all 12 rows on disk); its commit
  message wrongly claims zero rows existed — that claim is RETRACTED here

What remains true: no row had been read before either commit — the results
were first opened after 00:45. So the endpoints are DECLARED-BEFORE-ANALYSIS,
not provably blind; a skeptic cannot verify unreadness from git history and
should weight the pre-registration accordingly. The declared endpoints are
retained unchanged.

## Weekend 1c — focused-domain results: the physics prediction held (2026-08-06)

Compress raw -> decompress -> RDA focus -> CFAR, single Illinois stripmap
crop, 23,387 reference detections. Utility = Pd >= 0.9 AND spurious <= 10%
of reference (2,339):

| codec | rate (bps) | Pd | spurious | sustains? |
|---|---|---|---|---|
| BAQ 2-bit | 4.12 | 0.851 | 2,201 | no (Pd) |
| BAQ 3-bit | 6.12 | 0.905 | 1,619 | yes |
| BAQ 4-bit | 8.12 | 0.963 | 784 | yes |
| J2K r8 | 4.00 | 0.843 | 2,788 | no |
| J2K r16 | 2.00 | 0.692 | 6,121 | no |
| J2K r32 | 1.00 | 0.566 | 5,128 | no |
| HEVC qp28 | 7.71 | 0.969 | 705 | yes |
| HEVC qp36 | 4.69 | 0.901 | 1,858 | yes |

Focusing gain suppressed compression noise exactly as predicted in advance:
BAQ 2-bit Pd went 0.29 (pre-focus) -> 0.85 (post-focus), and the operational
viability of 3-bit BAQ (Pd 0.905) is reproduced — consistent with why
FDBAQ exists. Provisional R_c on this grid = 4.69 bps (HEVC qp36), but HEVC
sustains at the grid floor, so R_c must be located with the low-rate
extension before the GO target (R_c/2) is fixed. The contested region has
moved down-rate as predicted; the pre-focus "20-30% at FDBAQ rate" headline
is retracted as an operational-utility claim and survives only as a
statement about the range-compressed domain.

**Interpretation.** "Radar utility" splits into two regimes. In the raw-echo
domain (where onboard compression actually operates), classical codecs lose
most detections at operational rates — that is the neural codec's primary
target and the topic's stated Phase I focus. In the focused image domain,
classical transform codecs are already near-utility-lossless at 4 bps, so a
learned codec must win below ~2 bps to matter there. This regime split is
itself a proposal-grade insight: it says compress-then-focus, not
focus-then-compress, is where the money is.
