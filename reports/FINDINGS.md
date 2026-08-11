# Findings log

Running notes toward the 1–2 page feasibility summary. Newest at the bottom.
Numbers regenerable from `experiments/runs.jsonl` via `scripts/plot_curves.py`.

**RATE UNIT CONVENTION (applies to every number in this file and every plot):
bits per COMPLEX sample, I and Q combined.** ESA quotes FDBAQ per real
component (~2.6–3.6 bits/component in IW); on our axis that is ~5–7, nominal
**~6.8 bits/complex-sample**. Our BAQ n-bit points sit at 2n + 16/block bps.
Any comparison to published per-component figures must double them first.

## Weekend 1 — classical baselines on real data (2026-08-06)

**Setup.** 1,268 train / 223 val complex 256×256 patches from 4 echo chunks of
a Sentinel-1D IW scene over Hampton Roads (VV, decoded from L0 with
`sentinel1decoder`). MSTAR public target chips (1,622 train @17°, 1,365 test
@15°, BMP2/BTR70/T72). Frozen task models: 2-D CA-CFAR (Pfa 1e-4) applied
after range compression; small CNN ATR trained once on uncompressed chips
(86.1% test accuracy ceiling), then frozen.

**Headline.** Classical codecs collapse on radar-utility metrics well above
the rates where they look acceptable on MSE:

- At ~4 bits/complex-sample (below FDBAQ's ~6.8; unit correction applied
  2026-08-06, see convention above), the best classical codec preserves only
  ~20–30% of CFAR detections. [Section retracted as operational claim — see
  Weekend 1c; pre-focus scoring.]
- No classical codec exceeds Pd 0.8 below ~8–12 bits/sample.
- JPEG2000 beats BAQ per bit at moderate rates (transform coding exploits
  spatial correlation BAQ ignores) but degrades phase fastest — phase RMSE
  0.5 rad at 4 bps — which is disqualifying for interferometric/Doppler use.
- HEVC is the strongest classical baseline per bit but needs ~14 bps for
  Pd ≈ 0.94.

**Implication for feasibility.** The neural codec does not need miracles: the
target region (Pd ≥ 0.9 at ≤ 4 bps) is empty of classical competitors by a
wide margin. Even a modest learned codec that halves the utility loss at
FDBAQ-rate would be a publishable, significant result.

**Methodology decisions that mattered.**
1. CFAR on unfocused raw echoes is meaningless (it thresholds speckle; Pd
   readings were noise). Range compression via matched filter built from
   packet-header chirp parameters (TXPRR/TXPSF/TXPL + range-decimation sample
   rate) made detection physical. Azimuth focusing is a possible later upgrade.
2. Detection "ground truth" = detections on the uncompressed patch, so Pd
   measures preservation of detector behavior, not absolute detection skill.
3. Public L0 has already been through onboard FDBAQ once. All codecs start
   from identical decoded samples (internally fair), but the honest claim is
   "re-compression of operationally compressed raw data." [redacted: programmatic note]

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
is planned before any publication-grade claim; until then every focused-domain
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

**R_c determination (low-rate extension, same pipeline):** BAQ 1-bit
(2.12 bps) Pd 0.660; HEVC qp40 (3.18 bps) Pd 0.825 with 2,578 spurious
(fails both criteria); HEVC qp44 (1.82 bps) Pd 0.717; JPEG2000 r64/r128
(0.50/0.25 bps) Pd 0.438/0.323. No classical codec sustains utility below
4.69 bps. **R_c = 4.69 bits/complex-sample (~2.3 bits/component) ->
pre-registered GO target: sustain utility at <= 2.35 bits/complex-sample
(~1.2 bits/component), i.e. ~3x below the FDBAQ-class operating point.** That target sits below BAQ's physical
floor (~2.1 bps is already failing) and in the regime where transform codecs
have lost 20-30 points of Pd — a genuine, quantified gap for the learned
codec, narrower but far more defensible than the retracted pre-focus version.

Focusing gain suppressed compression noise exactly as predicted in advance:
BAQ 2-bit Pd went 0.29 (pre-focus) -> 0.85 (post-focus), and the operational
viability of 3-bit BAQ (Pd 0.905) is reproduced — consistent with why
FDBAQ exists.

**Harness validation:** after the unit correction, 3-bit BAQ sustaining
utility at 6.1 bits/complex-sample is our pipeline independently reproducing
the operating point of a fielded system (FDBAQ-class, ~6.8). The evaluation
measures something real; this is the strongest single piece of evidence for
the harness and should lead any methods discussion.

## AMENDMENT 2 (blind: no learned-codec results exist, nothing trained) —
## continuous primary outcome + architectural constraint (2026-08-06)

**Primary outcome is now continuous:** the lowest rate at which the learned
codec sustains utility (Pd >= 0.9, spurious <= 10% of reference, identical
CFAR config). The 2.35 bits/complex-sample threshold remains as a SECONDARY
binary GO/NO-GO. Rationale, recorded before any model exists: a learned codec
sustaining utility at e.g. 3.2 bps would be a NO-GO by the binary alone while
beating the fielded FDBAQ-class point by >2x and unconstrained HEVC by 1.5x —
an operationally excellent result that a binary-only report would headline as
failure. The threshold is not moved; a continuous readout is added.

**Architectural constraint, computed before training:** the transmitted chirp
spans ~2,400 range samples (stripmap: 51.1 us x 46.92 MHz; IW: ~2,900) and
target returns cohere across hundreds of azimuth pulses. Raw echo samples are
near-memoryless complex Gaussian PER SAMPLE — for such a source, entropy-coded
scalar quantization sits within ~0.25 bits of the rate-distortion bound,
which is exactly why BAQ/FDBAQ work. A learned codec beats classical ONLY by
exploiting the cross-sample structure BAQ discards: chirp correlation in
range, aperture coherence in azimuth. Our 256x256 patches with a conv
receptive field of ~70 px cannot see either scale — the vanilla
CompressAI-on-raw-patches plan is declared architecturally void HERE, before
producing a null. Design consequence: wrap the learned codec in the
INVERTIBLE all-pass dechirp/focus transform already implemented in
focus_rda.py (matched-filter phase, RCMC linear phase, azimuth filter phase
are each phase-only, hence exactly invertible), concentrating deterministic
structure inside the receptive field; compress in that domain; invert to
recover raw samples.

**New required baseline, registered before it runs:** invertible-focus +
classical transform codec (JPEG2000/HEVC in the transformed domain, inverse
transform on decode). This is a raw-data codec by construction and our own
regime-split data predicts it may be strong. If it alone approaches the GO
target, that is a major finding about WHERE the win comes from (the
transform, not the learning) and the learned codec must then beat it, not
just BAQ. The claim in one line: classical onboard codecs treat raw
radar as memoryless noise; any codec — learned or not — wins only by
exploiting the chirp and aperture coherence they discard.

## AMENDMENT 3 (blind: transform baseline has NOT run) — theory, invertibility
## test, compute ablation, and pre-registered readings (2026-08-06)

**Theory, stated properly (for the paper):** a phase-only focus is unitary and
preserves total entropy — it buys nothing on pure information-theoretic
accounting. What it changes is the distribution of variance across
coefficients, which is where transform coding gain lives: gain = ratio of
arithmetic to geometric mean of coefficient variances. Raw echoes spread
variance nearly uniformly (ratio ~1, gain ~0), so entropy-coded scalar
quantization — BAQ/FDBAQ — is near-optimal there. Focused data concentrates
energy into sparse scatterers over dark clutter (huge variance disparity,
large gain). This one argument explains the regime split, explains why FDBAQ
is the right raw-domain answer, and explains why any better codec — learned
or classical — needs the transform to have structure to exploit.

**Invertibility must be verified numerically before anything builds on it.**
Known threats: (1) amplitude windowing (we use none); (2) RCMC by sinc
interpolation (ours is a linear-phase ramp — safe); (3) the real one: our
matched filter is conj(FFT(replica)), whose magnitude collapses out of the
chirp band — NOT invertible as implemented. The transform codec must use the
PHASE-ONLY filter H/|H| and circular (unpadded) convolution so every step is
exactly unitary. Acceptance test, registered in advance: forward transform ->
inverse transform on uncompressed data must round-trip at machine precision
(relative error ~1e-6 for complex64). If it fails, stop and fix before any
baseline or model runs.

**Compute ablation, registered in advance:** full onboard focusing moves the
expensive operation to the platform — which is why raw downlink exists, and
revives "why not HEVC" as a compute question. Ablation arms: (none /
range-dechirp-only / full focus) x (classical codec). Range dechirp is one
complex multiply per sample plus an FFT and collapses the ~2,400-sample chirp
to a peak per scatterer; azimuth is the expensive half. If dechirp-only
captures most of the gain, that is the embeddable Phase II story. If only
full focus works, that constraint gets proposed against explicitly.

**Pre-registered readings of the transform baseline (both written before the
number exists):**
- Outcome A — tfocus+classical sustains utility at <= 2.35 bps: headline
  becomes "the domain transform matters more than the learning"; the cheap
  win for the government is a preprocessing change, not a neural network.
  The learned codec's competition is then tfocus+classical (continuous
  outcome vs. ITS curve), and the proposal thesis shifts accordingly. This
  outcome is a success of the study, not a failure of the idea.
- Outcome B — tfocus+classical improves on raw-domain classical but fails
  the GO rate: a genuine gap remains that only learned coding might close;
  the learned codec is judged against tfocus+classical as the strongest
  classical baseline, not against BAQ.
- Outcome C — tfocus+classical is no better than raw-domain classical:
  the concentration argument fails in the presence of quantization noise
  (e.g., compressed-domain errors unfocus destructively); the architectural
  premise for the learned codec is weakened and that gets reported honestly.

Execution order, fixed: round-trip test -> tfocus+JPEG2000/HEVC -> ablation
arms -> only then the learned model.

## AMENDMENT 4 — fourth outcome cell, entropy-model constraint, timing
## caveat, stopping rule (2026-08-06; tfocus row count at commit time is
## stated in the commit message — see git log)

**Fourth outcome cell (the ablation is a separate axis from A/B/C):** the
awkward cross-product is "full focus wins, dechirp-only does not" — a real
compression gain that requires a full azimuth focuser onboard, expensive
enough to reopen every compute objection. Reading rule, written before the
number: if only full-focus arms sustain utility at low rate, the result is
reported as CONDITIONAL — the gain exists but is contingent on onboard
focusing compute, and the Phase I conclusion must present the compute cost of
azimuth processing as the binding constraint, not bury it. Dechirp-only
sustaining within ~10% of the full-focus rate counts as "cheap transform
suffices" (the embeddable story); otherwise the conditional framing applies.

**Entropy model constraint for the learned codec, fixed before training:**
convolutional transforms map cleanly to FPGA/ASIC dataflow; the deployment
killer is the entropy coder. Fully autoregressive context models are
inherently sequential and cannot reach radar-rate throughput in realistic
silicon. The model will therefore use a FACTORIZED or checkerboard/parallel-
context entropy model only, accepting a known rate penalty to preserve
parallelism — because the operational constraint is throughput, not benchmark
BD-rate. Autoregressive results, if ever reported, are labeled non-deployable
reference points.

**Timing table caveat (named before a reviewer names it):** BAQ's wall-clock
advantage in our table is partly harness artifact — BAQ is vectorized NumPy
in-process; JPEG2000/HEVC go through external binaries with process-spawn and
file I/O overhead. Wall-clock is reported as measured, with this confound
stated. Implementation-independent order-of-magnitude operations per sample
(what actually transfers to Phase II hardware costing): BAQ ~10 (normalize +
~b comparisons + scale); JPEG2000 ~10^2–10^3 (wavelet cascade + EBCOT
bitplane coding); HEVC ~10^2–10^3+ (prediction search + transforms + CABAC,
sequential); unitary dechirp ~O(log n) butterflies/sample (FFT-dominated);
learned codec ~10^3–10^4 MACs/sample (conv stacks; parallel). The ranking
survives; the point is we name the confound first.

## AMENDMENT 5 — ringing mechanism, registered prediction for the learned
## codec, and the domain-mapping fairness rule (2026-08-06; 12/14 tfocus rows
## on disk; NO learned-codec code or results exist)

**Mechanism for the false-alarm minting (turns an observation into a claim):**
focused SAR is bright point scatterers over dark speckle — exactly the
high-contrast structure that makes wavelet coding ring. At low rates JPEG2000
produces Gibbs-type oscillations around every strong scatterer: a corona of
bright sidelobes that CFAR reads as detections. Real targets survive (Pd
holds 0.88–0.91) while each one spawns phantoms, with counts scaling
inversely with rate — our 4,482 -> 16,014 -> 138,131 progression at
4 -> 2 -> 0.5 bps. General form of the claim: concentrating energy makes
compression distortion STRUCTURED in exactly the way detection is sensitive
to. The two-sided criterion (Amendment 1) is what catches it; Pd alone would
have declared a spectacular false GO at 0.5 bps.

**REGISTERED PREDICTION P2, before any training (window verifiably clean —
no model code exists):** MSE-trained neural codecs characteristically BLUR
rather than ring; the squared-error optimum smooths detail instead of
oscillating around it. Predicted failure mode of the learned codec is
therefore the OPPOSITE of JPEG2000's: spurious counts stay controlled while
Pd degrades as weak scatterers smooth into clutter. Two mechanisms called in
advance from first principles; either confirmation or refutation is
informative about the architecture.

**Domain-mapping fairness rule (decided once, applied to every codec):** the
HEVC degenerate rows (rate ~0.00, near-black frames) come from min/max uint16
mapping on heavy-tailed focused data. The fix — robust percentile-clip
scaling — is NOT a neutral repair: it shifts the effective distortion toward
uniform RELATIVE error, which matches how CFAR thresholds work, and may
materially strengthen HEVC. Therefore: (1) one mapping — symmetric clip at
the 99.99th percentile of |value| per plane, clip bounds stored as side info,
then uint16 — applied to ALL plane-based codecs in ALL domains (JPEG2000,
HEVC, raw and transformed); (2) the learned codec is granted the identical
mapping and no more; (3) BAQ operates natively on floats (no mapping — it is
the fielded reference and takes no benefit); (4) all previously logged
plane-based rows are superseded by mapping-v2 reruns, old rows retained in
the log; (5) R_c is RECOMPUTED under v2 — because the GO criterion was
registered rate-RELATIVE (R_c/2), it self-updates mechanically; the threshold
rule does not move, its input does, and that distinction is the point of
having registered a relative rule. Complex-to-plane accounting, stated
explicitly: every codec here compresses I and Q (or transformed Re/Im)
symmetrically — no codec skips phase freight; rates are comparable on that
axis by construction.

## Transform baseline verdict (v1 mapping, provisional) + methodological note
## (2026-08-06)

**Outcome A EXCLUDED:** none of the 14 transform-baseline points sustains the
two-sided criterion at any rate. Full-focus JPEG2000 holds Pd 0.88–0.91 to
0.5 bps while minting phantoms at 2–60x the limit (the registered ringing
mechanism, confirmed in form). Dechirp-only fails mixed (Pd 0.86->0.50 plus
milder false-alarm excess — partial concentration, partial ringing). HEVC
transformed-domain rows were degenerate under mapping v1; B-vs-C is declared
undecidable until the v2 rerun.

**Methodological note — Amendment 4's equivalence test was inapplicable as
registered.** The rule compared dechirp vs full-focus RATE at matched
sustained utility; neither arm sustains utility at any rate, so the test
cannot be evaluated as written. Surrogate used (a judgment call, recorded as
such): compare Pd at matched rates. Full focus beats dechirp at every matched
rate (0.908 vs 0.859 @ 4 bps; 0.901 vs 0.731 @ 2 bps), far outside the ~10%
spirit of the registered band, so the conclusion "cheap transform is
insufficient" HELD under the surrogate. The registered rule's inapplicability
and the substitution are both part of the record.

**Feasibility argument as it now stands (drafted before the model runs, for
the proposal):** no classical approach sustains two-sided detection utility
below ~4.7 bits/complex-sample — not scalar quantization in the raw domain
(no transform coding gain: flat variance), not wavelet coding in the
concentrated domain (gain exists but the distortion is structured as ringing,
which detection is maximally sensitive to), not the cheap partial transform
(insufficient concentration). Each failure has a named, generalizing
mechanism. That negative space is the research opportunity, stated
falsifiably.

**The paragraph needed if P2 confirms (drafted in advance):** if the learned
codec blurs — Pd eroding while spurious stays controlled — then wavelet
coding and MSE-trained neural coding fail in COMPLEMENTARY directions, and
neither sustains two-sided utility below R_c, because both optimize a
distortion measure that is blind to detection. The open problem is then the
TRAINING OBJECTIVE, not the architecture: a detection-aware loss (e.g., CFAR
consistency or matched-filter-domain penalties) is precisely what Phase I
funds. The weekend produces the diagnosis; the proposal funds the treatment.

## AMENDMENT 6 — convergence interpretation rule, registered BEFORE training
## launches (2026-08-06; no training has started, no checkpoints exist)

**The confound this guards against:** an undertrained autoencoder produces
exactly the failure signature P2 predicts (over-smoothing, weak scatterers
lost, Pd eroding with spurious controlled). Without this rule, a
P2-confirming result could not be distinguished from a non-converged run.

**Rules, fixed in advance:**
1. The training loss trajectory is reported alongside any result (it is
   saved inside every checkpoint, not asserted afterward). If loss is still
   materially decreasing at the final step (final-decile slope worse than
   -1%), the outcome is reported as a LOWER BOUND on learned-codec
   performance — not as evidence for P2 and not as a NO-GO on the
   architecture.
2. Sanity gate: if the trained codec cannot beat BAQ at matched rate on the
   two-sided criterion inputs (Pd and spurious), that is reported as a
   convergence failure, not a finding — a converged learned codec should
   clear scalar quantization comfortably in the concentrated domain.
3. Model sized to converge, not to impress: ~0.5M params / 5,000 steps
   rather than 2.1M / 1,500. A small model trained to convergence is
   informative; a large one at step 1,500 mostly measures the optimizer.

**Generalization scope, stated precisely:** the train/eval split is by
acquisition chunk WITHIN the north-central-Illinois stripmap scene
(mislabeled "Chicago" until 2026-08-08 — corrected below and everywhere
else in this file; the scene's frame extends east to within a few km of
Chicago's western suburbs but the evaluated crop is agricultural terrain,
confirmed against the SAFE manifest footprint) — a clean held-out set
that measures WITHIN-SCENE generalization only. Cross-scene/cross-clutter
generalization (the topic's "regions not explicitly represented in
training") is untested here and is proposed Phase I work, alongside the
second-scene limitation already on record.

**Structural blindness note:** training begins while the mapping-v2 baseline
rescoring is still running; a model whose training started before the final
classical numbers existed cannot have been tuned against them. This is
blindness by construction, not assertion.

## FINAL CLASSICAL VERDICT — mapping v2, all 31 points (2026-08-06)

**R_c recomputed under v2: 4.86 bits/complex-sample** (raw-domain HEVC qp36:
Pd 0.908, spurious 1,742). Nothing sustains below it (HEVC 3.33 bps: 0.836
with excess spurious). **GO target: 2.43 bits/complex-sample** via the
registered R_c/2 rule.

**Outcome C on the frontier.** With the fairness mapping fixing the HEVC
degeneracy, the transform arms sustain the two-sided criterion NOWHERE, and
at every matched rate the utility frontier is set by RAW-domain HEVC. Per the
pre-registered Outcome C reading: the concentration argument fails in the
presence of quantization noise, and the architectural premise for the learned
codec is weakened accordingly — reported as registered. The mechanism nuance
(recorded because it defines the learned codec's remaining opening): the
transform DOES buy Pd at matched rate (full-focus J2K 0.912/0.888/0.861 at
4/2/1 bps vs raw J2K 0.845/0.691/0.574) — concentration works exactly as
theory says — but pays for it in ringing phantoms (5.8k/18k/38k spurious).
The opening for learning is therefore precisely: exploit concentration
WITHOUT ringing. Whether an MSE-trained codec can (P2 predicts its artifact
is blur, the opposite pole) is what the model run decides.

**Fourth cell under v2:** equivalence test again inapplicable as registered
(no transform arm sustains); under the documented surrogate (Pd at matched
rate), full focus > dechirp everywhere (e.g., 0.888 vs 0.729 at 2 bps) —
"cheap transform insufficient" HOLDS, consistent with v1.

**FRAMING CORRECTION (before this reaches prose):** "concentration premise
weakened" understates the data. The coding-gain theory predicted that
concentrating energy improves detection at matched rate, and it DID — 0.888
vs 0.691 Pd at 2 bps is the prediction CONFIRMED. What failed is the
instrument: wavelet coding rings, and ringing is the one artifact class CFAR
is maximally sensitive to. Precise statement: the concentrated domain is
exploitable in principle; JPEG2000 is the wrong tool for exploiting it.
Outcome C stands exactly as registered — it is the verdict on the
configurations tested — but the mechanism rides alongside it. Thesis sentence
of the study: a codec must capture the coding gain concentration provides
WITHOUT inheriting the artifact signature that destroys detection.

**Joint readout requirement for the model (and for all prose):** rate-utility
and ops-per-sample must be read together. The classical frontier holder (raw
HEVC, 4.86 bps) is also the least deployable codec in the study — serial
CABAC, no more silicon helps — while the fielded, deployable codec (BAQ/FDBAQ
class) sits at ~6.1. Therefore a learned codec sustaining utility anywhere
meaningfully below 4.86 with parallel-friendly compute beats the deployable
baseline on rate AND the undeployable one on implementability, even without
reaching 2.43. The model readout headline carries THREE numbers: (1) achieved
rate at sustained two-sided utility, (2) its position against 6.1 and 4.86,
(3) its ops-per-sample class (parallel MACs). Rate alone under-tells the
claim.

## MODEL READOUT (2026-08-06) — inconclusive under the registered rules;
## STOPPING RULE FIRED

Scored through the identical pipeline as every baseline:

| model | conv. slope | rate (bps) | Pd | spurious (limit 2,339) |
|---|---|---|---|---|
| lam=50 | -0.00% (flat) | 0.01 | 0.002 | 3,214 |
| lam=300 | -1.09% (descending) | 0.89 | 0.397 | 25,886 |

**Reading, mechanically applied:**
- lam=50 converged but to a DEGENERATE operating point: rate collapse
  (0.01 bps) means lambda was set 1-2 orders too low for this normalized
  data — a calibration error, not a finding.
- lam=300 fails the Amendment 6 sanity gate (worse than classical at
  matched rate: raw J2K at 1.0 bps scores 0.574/5,566 vs neural
  0.397/25,886) AND its loss was still descending (-1.09%). Per the
  registered rules this is reported as a CONVERGENCE/CALIBRATION FAILURE and
  a LOWER BOUND on learned-codec performance — not evidence for P2, not a
  NO-GO on the architecture.
- **P2 verdict: NEITHER confirmed nor refuted.** The observed signature (low
  Pd AND massive spurious) matches neither predicted pole (blur nor pure
  ringing). Candidate mechanism, unverified: independent per-tile compression
  with per-tile RMS normalization creates seam discontinuities on the 128-px
  grid that focusing amplifies into phantom detections. Verifying seam
  alignment of the false alarms is the first proposed diagnostic.
- **Three-number headline, as registered:** (1) achieved rate at sustained
  two-sided utility: NONE in this run; (2) position vs 6.1 / 4.86:
  not applicable; (3) ops class: parallel conv MACs, measured 0.6-1.3
  Msamples/s single-threaded CPU (vs BAQ 16-19 in-process) — the
  parallelism argument is unaffected by this run's quality failure.

**Continuous primary outcome:** no sustaining rate achieved. **Binary
secondary:** NO-GO on this run — reported with the mandatory qualifier that
Amendment 6's confound rule applies in full: this run bounds a compact
CPU-budget model below, and says nothing about the architecture class.

**STOPPING RULE FIRED.** Transform baseline and one trained autoencoder have
both been scored against the pre-registered criterion. The experimental phase
is closed. What the record establishes: (1) the classical feasibility spine
stands in full — on the evaluated scene, no classical approach sustains
two-sided utility below 4.86 bits/complex-sample, each failure
mechanistically named; (2) the concentrated
domain is exploitable in principle (coding-gain prediction confirmed) and the
open problem is capturing that gain without a detection-hostile artifact
signature; (3) the learned-codec question is OPEN, with the failure diagnosed
as budget/calibration/tiling engineering, not principle. Items for Phase I
proposal scope, converted from the ideas list per the stopping rule:
GPU-scale training with calibrated lambda schedules, seam-aware tiling
(overlap or global normalization), detection-aware training objectives,
cross-scene generalization, second-scene clutter, ANS productionization of
the entropy coder, embedded trade study.

## VALIDITY CHECK — FDBAQ lattice-alignment artifact (2026-08-08)

**Threat.** Asiyabi et al. (IEEE JSTSP 2025 — [redacted: programmatic context]) report that on FDBAQ-decoded Sentinel-1 raw data, BAQ at 3 bits
scored anomalously WELL — better than 4-bit BAQ — because the FDBAQ
reconstruction lattice coincidentally aligned with the 3-bit BAQ step. Our
strongest credibility claim ("3-bit BAQ sustains utility at 6.12
bits/complex-sample, independently reproducing the fielded FDBAQ operating
point") depends on exactly that configuration.

**Precondition confirmed present in our data.** The north-central-Illinois
stripmap crop
carries a visible FDBAQ lattice: **48 distinct I values across 1,048,576
samples; 32 distinct values in a 64x64 block** (estimated step 1.1471).
For contrast, AFRL Gotcha airborne phase history shows 153,443 distinct
values in 153,600 samples — effectively continuous.

**Test.** Re-ran the BAQ sweep on the same crop with and without the Asiyabi
adaptation procedure (uniform noise of one lattice step filling the gaps;
`radarcodec/data/adaptation.py`, after their IGARSS 2024 method). Adaptation
verified effective: 32 -> 4096 distinct values in a 64x64 block.

| BAQ bits | rate (bps) | Pd orig | false orig | Pd adapted | false adapted |
|---|---|---|---|---|---|
| 2 | 4.12 | 0.851 | 2,201 | 0.850 | 2,247 |
| 3 | 6.12 | 0.905 | 1,619 | 0.909 | 1,621 |
| 4 | 8.12 | 0.963 | 784 | 0.965 | 815 |
| 6 | 12.12 | 0.987 | 277 | 0.988 | 312 |

**Result: the artifact does NOT affect our results.** Max |dPd| = 0.004,
false-alarm counts shift by <5%, and — the decisive point — **monotonicity
is preserved in both conditions** (2 < 3 < 4 < 6 bits). We never observed
the inversion (3-bit beating 4-bit) that is the artifact's signature.

**Why we escaped it, most likely:** (a) our utility metric is post-focus
CFAR detection agreement, not SQNR; coherent integration suppresses
quantization-lattice effects that a direct signal-fidelity metric registers
immediately; (b) our BAQ is Lloyd-Max (Gaussian-optimal, non-uniform), so
its levels do not align with a uniform FDBAQ step the way a uniform
quantizer's would.

**Net: the harness-validation claim stands, and now stands tested.** State
it that way — "we tested for the lattice-alignment artifact reported by
Asiyabi et al. and confirmed our results are unaffected" is stronger than
the untested version. Adaptation is retained in the codebase as an option;
the preferred long-term answer remains evaluating on genuinely unencoded
data (AFRL Gotcha).

**Stopping rule (adopted 2026-08-06):** the experimental phase ends when the
transform baseline AND one trained autoencoder have both been scored against
the pre-registered continuous criterion. After that, the next artifact is
prose: FINDINGS.md -> preprint draft + Phase I proposal skeleton. Every
further experiment idea becomes PROPOSED Phase I work. Provisional R_c on this grid = 4.69 bps (HEVC qp36), but HEVC
sustains at the grid floor, so R_c must be located with the low-rate
extension before the GO target (R_c/2) is fixed. The contested region has
moved down-rate as predicted; the pre-focus "20-30% at FDBAQ rate" headline
is retracted as an operational-utility claim and survives only as a
statement about the range-compressed domain.

**Interpretation.** The behavior splits by task and domain, consistent with
the coding-gain argument. In the raw-echo domain, where onboard compression
actually operates, classical codecs lose most detections at operational
rates; that is the neural codec's primary target and the topic's stated
Phase I focus. In the focused domain the picture is task-dependent:
classification (ATR) stays near ceiling down to ~2 bps, but transform coding
still rings under detection (the tfocus result), so "focused domain is easy"
holds only for classification, not for detection. On the two scenes evaluated
this points to raw-domain compression as the more open opportunity for a
learned codec, since that is both where classical leaves the largest
detection-preserving gap and where onboard compression has to run.
Generalizing the split beyond these scenes is proposed Phase I work, not a
settled result.

## SCENE LOCATION CORRECTION — "Chicago" was wrong (2026-08-08)

Every document in this repo (this file, the preprint, `prior_art.md`'s
Asiyabi analysis) described the evaluation scene as "the Chicago stripmap
scene/crop." Caught by inspection of the rendered Figure 0
quicklook, which plainly did not resemble Chicago — no lakeshore, no
dense urban core, just farmland. Checked against the primary source (the
SAFE product's `manifest.safe`, `<gml:coordinates>` under `footPrint`):
`42.3705,-88.6264 40.7168,-88.9679 40.6390,-88.0440 42.2926,-87.6782`
(lat,lon corners) — the frame spans roughly 40.64°–42.37°N,
88.97°–87.68°W. Chicago itself (41.88°N, 87.63°W) sits at or just past the
frame's *eastern* edge, meaning the acquisition frame is centered well
**west** of the city, and the evaluated 4096×8192 crop (drawn from the
frame's interior per `load_crop()` in `eval_focused.py`) is agricultural/
exurban north-central Illinois, not Chicago proper. Corrected to
"north-central Illinois stripmap scene" everywhere this appears. No
numeric result is affected — this was a location label, not a data or
analysis error — but it's exactly the kind of easily-checkable factual
claim that should never have gone uncorrected into a document meant for a
government reviewer or an arXiv reader. Root cause: the label was carried
forward from an early, unverified assumption and never checked against
the SAFE manifest until asked.

## SECOND/THIRD-SCENE DATA ACQUIRED — Houston, São Paulo (2026-08-08)

Direct follow-on from the Chicago correction above: Asiyabi et al.'s own
training set is Chicago, Houston, and São Paulo (verbatim from their paper,
`reports/refs/asiyabi_text.txt` line 198: "three Sentinel-1 scenes acquired
over Chicago and Houston in the United States, and São Paulo in Brazil").
Checked ASF for genuine StripMap coverage (this pipeline needs StripMap,
not IW — see `TOPIC.md` Known Alignment Gaps) over all three via
`scripts/download_s1.py --beam-mode S1..S6`:

- **Chicago: no StripMap coverage found** (S1 through S6, zero results).
  StripMap is only tasked for specific sites; IW is Sentinel-1's default
  systematic land mode. This is *why* the original scene ended up over
  farmland west of the city rather than the city itself — Chicago-proper
  StripMap doesn't exist in the archive to acquire.
- **Houston: available (S1, S3, S6).** Pulled S6 (`S1C_S6_RAW__0SDH_
  20260807T002551_...`, 1.23 GB). Footprint verified against
  `manifest.safe` BEFORE use this time: 28.66°–30.40°N, -95.66° to
  -94.53°W — Houston (29.76°N, -95.37°W) sits well inside it. Confirmed
  by the focused quicklook: Galveston Bay, industrial shoreline
  structures, a large bright rectangular target and circular/triangular
  jetty or platform structures in the water — unambiguously real coastal
  Houston.
- **São Paulo: available (S3, S6).** Pulled S6 (`S1C_S6_RAW__0SDV_
  20260731T214258_...`, 1.20 GB; first download attempt was interrupted
  mid-transfer and the retry's "file already exists" check skipped a
  truncated 1.08 GB file — caught via unzip failure, deleted, re-pulled
  clean). Footprint verified: -24.74° to -22.97°N, -46.92° to -45.68°W —
  São Paulo (-23.55°N, -46.63°W) sits inside it. Confirmed by the focused
  quicklook: Serra do Mar coastal range terrain (radar layover/
  foreshortening striping typical of rugged relief) with a winding river
  valley and dense urban texture along it.

Both raw crops cached (`data/s1_houston/chunk_crop.npz`,
`data/s1_saopaulo/chunk_crop.npz`, same 4096×8192 convention as the
existing scene) with focused quicklooks in `reports/`. **No quantitative
evaluation run on either — that stays proposed Phase I scope (cross-scene
generalization), per the stopping rule.** This is data acquisition only:
two named, verified, real-city candidate second/third scenes now in hand,
directly matching Asiyabi et al.'s own precedent set, ready for that work
when it's funded.

## PLOTTING BUG FOUND AND FIXED — tfocus-full-jpeg2000 missing from every
## figure (2026-08-08)

While generating preprint figures, found that `scripts/plot_curves.py`'s
top-level dedup key was `(domain, codec, round(rate_bps, 2))`. Every
`tfocus` row shares the literal codec string `"tfocus"` regardless of
(mode, base) — and the JPEG2000 full-focus and dechirp-only arms land on
identical nominal rates (both parameterized by the same `ratio`), so they
collided on this key and one silently overwrote the other before the
downstream per-series grouping (which does distinguish mode/base) ever ran.
Net effect: `tfocus-full-jpeg2000` — the series carrying the paper's
central concentration-vs-ringing claim — was absent from every regenerated
plot, including the ones already committed to the repo before this pass.

**No numeric claim in FINDINGS.md, the preprint, or the proposal drafts was
affected.** Every number in the written record was pulled directly from
`runs.jsonl` rows (via `eval_focused.py` output or direct queries), never
read off a chart. This was a visualization completeness bug, not a data or
analysis bug — but it matters for the record because a reader comparing the
prose to the figures before this fix would have seen the strongest
evidence for the ringing mechanism in the text with no corresponding line
on the chart. Fixed by keying tfocus rows on `(domain, "tfocus-{mode}-{base}",
rate)` at the dedup stage, matching the grouping key already used
downstream. All five figures regenerated after the fix; `tfocus-full-jpeg2000`
now appears correctly as the highest-Pd / highest-spurious-count series at
low rates in both `rate_vs_pd.png` and the newly added `rate_vs_spurious.png`.

## GOTCHA GMTI EVALUATION — first genuinely unencoded result (2026-08-08)

Post-stopping-rule, with Houston/São Paulo set aside as lower priority.
Ran `scripts/eval_gotcha.py`: the identical, unmodified
protocol from Section 3 of the preprint (same CA-CFAR config, same BAQ/
JPEG2000/HEVC grid from `configs/baseline_sweep.yaml`) applied to AFRL's
Gotcha GMTI phase history (`chan1`/`mis2`, pulses 5585-7448, AFRL's own
worked example — the exact configuration already ingest-verified). No
threshold or codec setting was chosen or adjusted after seeing this data;
everything was already fixed by the Illinois pre-registration. This is
extension to new data under a frozen protocol, not reopening the
exploratory phase.

**Result:** 369 reference detections (vs. 23,387 on Illinois — a much
smaller, sparser scene, single dominant scatterer plus urban clutter).
Under the identical two-sided criterion (budget = 36.9 = 10% of 369):

| codec | params | rate (bps) | Pd | false | sustains? |
|---|---|---|---|---|---|
| baq | 2-bit | 4.12 | 0.659 | 62 | no |
| baq | 3-bit | 6.12 | 0.778 | 52 | no |
| baq | 4-bit | 8.12 | 0.862 | 38 | no |
| baq | 6-bit | 12.12 | 0.959 | 23 | yes |
| jpeg2000 | r4 | 8.00 | 0.905 | 30 | yes |
| jpeg2000 | r8 | 4.00 | 0.799 | 47 | no |
| jpeg2000 | r16 | 2.00 | 0.656 | 95 | no |
| jpeg2000 | r32 | 0.99 | 0.442 | 158 | no |
| hevc | qp12 | 10.49 | 0.973 | 18 | yes |
| hevc | qp20 | 7.35 | 0.900 | 23 | yes |
| hevc | qp28 | 4.54 | 0.780 | 48 | no |
| hevc | qp36 | 2.28 | 0.675 | 70 | no |

**R_c (Gotcha) = 7.35 bps** (HEVC qp20, Pd exactly at the 0.9 floor).
Higher than Illinois's 4.86 bps. Every codec's curve is monotonic and
sane — no wiring bugs, no artifacts. The gap between 7.35 and 4.86 is
**not** claimed as "unencoded data needs more bits" — the two scenes
differ in sensor (X-band airborne vs. C-band spaceborne), geometry
(circular-mode GMTI vs. stripmap), resolution, and detection-sample size
(369 vs. 23,387, meaning this R_c estimate carries far more sampling
noise). What's clean: this is the first result in the whole study with
zero re-compression caveat, and the qualitative pattern (a real,
nonzero, sub-fidelity-metric-implied frontier exists) replicates
independently under a frozen protocol.

**Data provenance, verified from primary source (not assumed):** paper
carries "Public Release # 88 ABW-09-1031"; the data package itself
carries its own "Public Release # 88 ABW-09-0967" (found in
`SAR-Based_GMTI_CP/Public Release Numbers.txt`, bundled with the
downloaded data). Both confirm public research use, including publication
of derived results, is the explicitly intended use — not a gray area.

**Also confirmed in hand and not yet used:** `durangoChallenge_GPStruth.mat`
contains real timestamped position, speed, and heading for the Durango
vehicle (~100+ samples, a genuine move-stop-move profile, speeds 0-22
m/s) — a real tracking-fidelity metric (position error after compression,
not just detect/no-detect) is buildable against this and remains the
highest-value next step on the AFRL data (Tier 2 of the game plan; not
attempted this pass).

**Preprint updated:** new Section 5.8, Figures 5-6 (`rate_vs_pd_gotcha.png`,
`rate_vs_spurious_gotcha.png`), abstract finding (4), Limitations,
Conclusion future-work reprioritized (AFRL extensions now lead; Houston/
São Paulo demoted to lower priority), reference [17] added (Scarborough
et al., Proc. SPIE 7337, 73370G, 2009).

## TIER 2 ATTEMPT — single-channel GMTI change detection, honest negative
## result, self-corrected false positive (2026-08-08)

Attempted the compression-impact-on-tracking metric
(the highest-value item flagged when Section 5.8 was written): use AFRL's
GPS ground truth to score moving-target-detection fidelity after
compression, per Phase II's own language ("impact to target... tracks
after decompression"). Followed AFRL's own published method (Scarborough
et al. [17], Section 4): coherent + non-coherent change detection between
the `mis2` (mission, target present) and `ref4` (reference) passes.

**Calibration, real and useful regardless of outcome below:** cross-
referenced each pass's `GPSTODfirstPulse` (from the bundled
`*_auxSaveData.mat` files — mis2: 63589.839, ref4: 60924.541 GPS
seconds-of-day) against the GPS truth file's timestamp range
(63575-63676). mis2's pulse count (154,180) / PRF (2171.55 Hz) = 71.0
seconds, exactly matching the paper's stated "71-second scenario" — an
independent internal-consistency check that passed cleanly.

**Attempt 1 — whole-scene coherent/non-coherent change, same relative
pulse window (5585:7449) in both passes (coincident-geometry repeat
passes per AFRL's own description).** FFT phase-correlation check found
zero global misregistration between passes (shift = 0,0) — ruling out
gross misalignment as an explanation. But mean coherent correlation
across the whole scene was low (0.238) and essentially uniform: strong
deterministic scatterers (buildings) correlated well, diffuse clutter
did not, regardless of motion. This is expected repeat-pass speckle
decorrelation, not a processing bug, but it means whole-scene search is
swamped by clutter decorrelation — consistent with AFRL's own paper
admitting the same failure mode ("moving Durango is not evident in either
[change detection] image due to the competing cultural clutter," their
Figure 9), where they fall back to multi-phase-center STAP.

**Attempt 2 — targeted AOI at the documented signature.** Found a point
matching the ingest-verification docstring almost exactly (29.6 dB
contrast over scene median vs. the documented 29.3 dB) at row 323, col
834. Visually, the coherent-correlation map showed what looked like a
distinct dark (decorrelated) blocky patch at that exact location against
a lighter background — a plausible motion signature.

**Self-correction (caught before it went in the preprint):** quantified
it rather than trusting the visual impression. Mean coherence in a 7x7
patch centered on the candidate point: 0.204. Mean coherence in the
surrounding background ring: 0.206. **Statistically indistinguishable.**
The "blocky dark patch" was a perceptual artifact of the 5x5 smoothing
window's block structure, not a real decorrelation anomaly; the very low
min value (0.005) that looked promising is an ordinary speckle null, the
kind any correlation map has scattered through it by chance. Checked the
non-coherent map at the same location too — no clear signature there
either.

**Conclusion, reported honestly per this project's stopping-rule/negative-
result discipline (same treatment as Section 5.7's learned-codec run):**
single-channel change detection, as naively applied here, does not
cleanly separate this candidate target from background decorrelation.
This is not evidence the target is undetectable — it is evidence that
the simple method AFRL itself describes as sometimes-insufficient is, in
fact, insufficient here too, exactly where their own paper says it can
be. The documented next step (multi-phase-center STAP, using channels 2
and 3, needs antenna baseline/platform-velocity parameters not yet
extracted) is a genuinely bigger build — real signal-processing R&D, not
an extension of this attempt — and stays proposed Phase I scope rather
than something to pursue in this exploratory phase. The decision, weighing
cost against benefit, was to stop here, report both attempts plainly, and
move to other open items.

**What this leaves on the record:** a documented attempt at the simpler
method, a specific, correctly-diagnosed failure mode, and a precise
account of what the harder method (multi-phase-center STAP) needs that
this attempt did not have — without overclaiming a result that does not
hold up under its own scrutiny.

## GOTCHA TRANSFORM-DOMAIN ARM — the ringing mechanism replicates
## independently, plus a rounding-artifact correction to R_c (2026-08-08)

Extended the Gotcha evaluation to the focused
(range-Doppler) domain, direct analog of the Illinois `tfocus` study.
Gotcha's phase history is already motion-compensated, so its "focus"
step is a plain 2-D DFT pair (`form_image`/new `inverse_image` in
`radarcodec/data/gotcha.py`) — no dechirp/RCMC/azimuth chain needed,
unlike Sentinel-1. Verified exactly invertible before use (mean relative
error 4.4e-7, float32 precision) per the same discipline applied to the
Sentinel-1 transform. New `tfocus_gotcha_codec` wraps JPEG2000/HEVC in
this domain; `scripts/eval_gotcha.py` extended to sweep it.

**CORRECTION to the R_c figure reported in the previous entry.** That
entry stated "HEVC qp20: Pd = 0.900 exactly at the registered floor" —
this was a rounding artifact from reading a 3-decimal print statement.
The actual stored value is **0.8997289972899729** — just under the 0.9
floor. HEVC qp20 does **not** sustain the two-sided criterion; it never
did. Caught while computing R_c programmatically off the raw `runs.jsonl`
values (not off a printed/rounded number) for the expanded sweep — same
lesson as the "60x" abstract correction earlier: never read numbers off
rounded print output when the exact value is available in the log.

**Corrected, expanded result.** With the transform-domain arm included,
the lowest-rate sustaining point is `tfocus`-JPEG2000 at ratio=4: **R_c =
7.99 bits/complex-sample** (Pd 0.943, 26 spurious against the 36.9
budget) — narrowly ahead of raw-domain JPEG2000 at the same nominal rate
(8.00 bps, Pd 0.905, 30 spurious). No point below ~8 bps sustains in
either domain.

**The mechanism replicates cleanly, independently of the R_c value.**
At matched low rates, the focused-domain codecs win decisively on Pd —
e.g. at ~1 bps, `tfocus`-JPEG2000 holds Pd 0.805 vs. raw JPEG2000's
0.442 — but pay for it in spurious detections an order of magnitude or
more above the raw-domain codecs at the same rates (2,000-3,000+ vs.
100-160 for JPEG2000; 600-1,000 vs. 20-70 for HEVC). This is the exact
concentration-buys-Pd-but-floods-false-alarms pattern from Section 5.3 of
the preprint, now observed on a completely independent sensor (X-band
airborne vs. C-band spaceborne), geometry (motion-compensated
range-Doppler vs. stripmap), and scene (small urban vs. large
agricultural) — a materially stronger claim than a single-scene finding.

**Preprint Section 5.8 rewritten** to report the corrected R_c, the
transform-domain results, Figures 5-6 regenerated with the new series and
corrected R_c annotation (7.99, was 7.35).

## GOTCHA LEARNED CODEC — interpretation rules declared BEFORE training
## (2026-08-08; no training run yet, no checkpoints exist)

Extending to the learned codec on Gotcha data. This
is exploratory extension work, not a reopening of the closed,
pre-registered Illinois study -- but the same discipline applies by
choice, not obligation: rules fixed before the run exists.

**Data:** 13,920 focused-domain (range-Doppler) patches, 64x64 complex,
extracted from 80 non-overlapping 1864-pulse windows tiling the full
154,180-pulse `mis2` file, with any window overlapping the eval crop
(pulses 5585-7449) dropped entirely -- full held-out separation, not mere
adjacency. 11,832 train / 2,088 val split (`scripts/extract_gotcha_patches.py`).
Patch size is 64px, not Illinois's 128px: the encoder's four stride-2
layers give 16x downsampling, and 32px (this scene's naive first choice,
given the 384px range axis) leaves a degenerate 1x1 latent; 64px gives a
4x4 latent (Illinois's 128px gave 8x8) -- smaller but not degenerate,
sized to what this scene's dimensions actually allow.

**Architecture and lambdas: reused unchanged from Illinois
(`configs/ae_gotcha.yaml` mirrors `configs/ae_small.yaml`), not retuned.**
Same compact learned codec, same lambda bracket
[50, 300], same 5,000 steps, same batch=8, same lr=1e-4. Deliberate
choice: retuning lambdas for this dataset before seeing results would be
cherry-picking hyperparameters to force a better outcome. If [50,300]
reproduces the same failure pattern as Illinois (50 collapses to
near-zero rate, 300 undertrained/miscalibrated), that itself is an
informative parallel finding, not a wasted run.

**Interpretation rules, fixed now:**
1. Loss trajectory ships with the checkpoint (unchanged practice). If
   loss is still materially decreasing at the final step (final-decile
   slope worse than -1%), the run is a LOWER BOUND, not evidence for or
   against the architecture -- same as Amendment 6's rule.
2. Sanity gate: the trained codec must beat the best classical
   Gotcha baseline (raw or `tfocus`, whichever is stronger at the
   matched rate) on both Pd and spurious count to count as a finding
   rather than a convergence failure.
3. Evaluation is on the SAME held-out crop used for every other Gotcha
   result (`chan1`/`mis2`, pulses 5585-7449) -- never seen during
   training, by construction (the patch extraction dropped it entirely,
   not just left it unsampled).
4. Three-number headline on report, same as Illinois: (1) achieved rate
   at sustained two-sided utility, if any; (2) position vs. this scene's
   R_c (7.99 bps) and the raw-domain baseline; (3) ops-per-sample class
   (unchanged from Illinois -- same architecture, same parallel-MAC
   accounting applies).

## GOTCHA LEARNED CODEC — READOUT (2026-08-08): both lambdas converge to
## the transmit-nothing solution; reported per the rules above

Scored through the identical pipeline (`scripts/eval_gotcha_neural.py`),
same held-out crop as every other Gotcha result:

| model | conv. slope | rate (bps) | Pd | spurious (budget 36.9) |
|---|---|---|---|---|
| lam=50 | -0.0% (flat) | 0.029 | 0.003 | 677 |
| lam=300 | -0.0% (flat) | 0.023 | 0.003 | 265 |

**Reading, mechanically applied:** both runs CONVERGED (flat final-decile
slope — rule 1's undertrained branch does not apply) but to a DEGENERATE
operating point: rate collapsed to ~0.02 bps within the first ~200 steps
and MSE pinned at exactly 0.500 for the rest of training. 0.500 is the
tell: for per-patch RMS-normalized complex data each real channel has
variance 0.5, so MSE = 0.500 means the decoder outputs ~zero — the
optimizer found the transmit-nothing solution and stayed there. Final
losses (25.010, 150.010) are exactly lambda x 0.5 plus rate residue,
confirming zero information transmitted. Both runs fail the rule-2 sanity
gate trivially. **Three-number headline: (1) no sustaining rate; (2) not
comparable to R_c = 7.99 or any baseline — the codec transmits nothing;
(3) ops class unchanged (same architecture; the parallelism argument is
untouched by this run's failure).**

**The failure differs from Illinois's in an informative way.** Illinois
lam=300 was still descending at the final step (undertrained, lower
bound); Gotcha's lam=300 converged flat to degenerate — at these lambdas,
on this data, transmit-nothing appears to be a genuine optimum of the
training objective, not an unreached waypoint. Candidate mechanism,
recorded as HYPOTHESIS not finding: per-patch RMS normalization erases
cross-patch dynamic range — exactly where the focused domain's energy
concentration (the AM/GM variance disparity that coding gain lives on)
resides. Most 64px Gotcha patches are pure clutter; after normalization
their content is approximately unit-variance complex speckle — a
near-memoryless Gaussian source, for which spending ~0 bits and eating
distortion 0.5 is genuinely close to rate-distortion-optimal at these
lambda values in this small model's reachable set; and once the entropy
bottleneck collapses (sigma small, all latents rounding to zero), no
gradient path leads back out. If correct, this is a SECOND, independent
indictment of per-tile normalization, converging with the Illinois
seam-artifact hypothesis from the model readout of 2026-08-06 — two
different failure signatures on two different datasets pointing at the
same design element. The Phase I fix list sharpens accordingly:
scene-level (global) normalization or normalization schemes that preserve
cross-patch dynamic range, calibrated lambda schedules (both scenes'
evidence says [50, 300] is 1-2 orders too low for unit-normalized data),
and GPU-scale budgets. Deliberately NOT tried here: retuning lambda on
this data until something works — that is exactly the cherry-picking the
pre-declared config was designed to prevent, and it is proposed Phase I
work.
