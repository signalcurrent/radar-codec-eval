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
- 00:41:58 — pre-registration commit 08c420d (6 of 12 rows already on disk; corrected 2026-10-22 from "7 of 12" by recount of runs.jsonl timestamps)
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

<!-- Ported from the private working notebook on 2026-10-22 for arXiv v2. Programmatic notes are redacted with visible markers; technical content is untouched. Sections dated 2026-08-14 to 08-15 that are outside the paper's scope are not included in this mirror. -->

## AMENDMENT 7 — global-normalization bug fix, pre-registered BEFORE the run
## (2026-08-13; NO global-norm code or results exist at commit time)

**Status of the stopping rule.** The experimental phase was closed 2026-08-06.
This re-opens it deliberately, under two of the three declared exceptions: (1) a
positively-diagnosed BUG — per-patch/per-tile RMS normalization, now implicated
independently by both learned-codec failures (Illinois seam artifacts 08-06;
Gotcha transmit-nothing 08-08), present in `train.py:45`, `neural.py:34`, and
`neural_gotcha.py:37`; and (2) a METHODOLOGY CHANGE — global normalization.
This is done at PRIVATE EXPENSE on PUBLIC DATA (house rule #5), as deliberate
[redacted: programmatic note] ([redacted: programmatic note]." The earlier note
("retuning lambda is proposed funded work, not evening work") is superseded for
this specific, pre-registered, bug-driven change — and the guardrail it protected
is honored below: the lambda ladder is a LOCATING sweep reported IN FULL, not a
retune-until-it-works, and Amendment 6's sanity gate still governs what counts.

**On disk at declaration (house rule #4).** Failed checkpoints
`{gotcha_,illinois_,}hyperprior_lam{50,300}_seed1337.pt` (per-patch norm);
training patches `data/gotcha_patches/` and `data/tfocus_patches/`; NO
global-normalization code; NO global-norm checkpoints; NO global-norm results.

**The bug, precisely.** Every patch/tile is divided by its OWN RMS before the
codec sees it. This erases cross-patch dynamic range — the arithmetic/geometric
variance disparity that transform-coding gain lives on (Amendment 3) — and
makes every patch ~unit-variance, so `mse=0.5` (decoder outputs zero) is a
near-optimal fixed point with no gradient path out once the entropy bottleneck
collapses (the Gotcha readout's own diagnosis, 08-08 lines).

**The fix.** GLOBAL (dataset-level) normalization: a single scalar
`g = sqrt(mean|x|^2)` estimated once over a random sample of training patches,
applied to every patch; stored in the checkpoint; used identically at eval (one
32-bit global constant charged once, replacing the per-tile +32 side-info).
High-energy patches keep MSE >> 0.5 under transmit-nothing → real gradient to
transmit; clutter patches keep MSE << 0.5 → correctly cheap. Cross-patch
dynamic range is preserved by construction. Selectable via `norm: global` in
config; `per_patch` (legacy) retained for reproducibility of the closed runs.

**Lambda ladder, declared in advance:** `[300, 1000, 3000]` (higher than the
closed [50,300], per the recorded "1-2 orders too low" evidence), run as a
locating sweep. All three outcomes are reported regardless of where they land;
no single winner is cherry-picked.

**Diagnostic budget:** Gotcha first (smallest data, cleanest transmit-nothing
signal). Steps sized to the measured CPU rate; Amendment 6's lower-bound rule
applies unchanged if final-decile slope > -1%.

**Endpoints, declared before results exist:**
1. PRIMARY (diagnostic): does global normalization BREAK the collapse? Operational
   definition — at least one lambda yields a NON-degenerate converged operating
   point: rate materially > 0 (out of the ~0.02 bps transmit-nothing floor) with
   reconstruction MSE materially below the patch-variance-weighted transmit-nothing
   value (decoder carries real information).
2. SANITY GATE (Amendment 6, unchanged): to count as a FINDING rather than a
   convergence failure, the trained codec must beat the best classical baseline
   at matched rate on BOTH Pd and spurious. This requires the full two-sided eval
   and is the follow-on step.
3. INTERPRETATION, fixed now: (a) collapse breaks AND clears sanity gate →
   confirms the failures were engineering (normalization/calibration), not
   architecture; tilts go/no-go toward GO; strengthens the "credible,
   mechanism-grounded path" claim. (b) collapse breaks but fails the sanity gate
   → architecture/objective genuinely limited at this budget; motivates the
   detection-aware training loss (Q3) as the next, separate probe. (c) collapse
   does NOT break → per-tile normalization was not the (sole) culprit; re-examine
   before any further build. This is a NULL-informative design: every outcome
   advances the go/no-go.

**Scope.** This is the Q2 fix (normalization/calibration) ONLY. The
detection-aware loss [redacted: programmatic note] is a SEPARATE subsequent probe, meaningful
only if Q2 clears the sanity gate. Not attempted in this amendment.

## AMENDMENT 7 READOUT — global norm is NECESSARY BUT NOT SUFFICIENT; the
## transmit-nothing collapse breaks only at the top lambda, undertrained
## (2026-08-13; Gotcha, `configs/ae_gotcha_gnorm.yaml`, 5000 steps, CPU)

Global scale `g=0.0354143` (from 4096 sampled patches). Same 0.53M-param
architecture as the closed run — only normalization and lambda changed, so any
difference isolates the fix. Final operating points (mean over the last logged
decile; full trajectory in `experiments/logs/gotcha_gnorm_train.log`):

| lambda | rate (bps) | MSE (batch-varying) | final-decile slope | verdict |
|---|---|---|---|---|
| 300  | ~0.010 | ~0.37 | +3.1% | COLLAPSED — transmit-nothing |
| 1000 | ~0.010 | ~0.14 | +6.0% | COLLAPSED — transmit-nothing |
| 3000 | ~0.52  | ~0.48 | -7.1% | ESCAPED — real information, still descending |

**PRIMARY endpoint (does the collapse break?): MET, narrowly, by lam=3000
only.** rate ~0.52 bps is ~50x the ~0.01 bps transmit-nothing floor, and MSE
tracks per-batch energy (0.11 on low-energy batches while bright batches carry
>>1) — the decoder genuinely reconstructs rather than outputting zero. The
smoke-window signature (MSE 2.96 -> 0.21 in 20 steps while rate held) confirmed
the escape mechanism directly. Per Amendment 6, lam=3000 is still descending
(-7.1%) so it is reported as a LOWER BOUND, not a converged operating point;
5000 CPU steps is undertrained for this arm and the rate is still climbing.

**The sharper, honest finding: normalization was necessary but not sufficient.**
lam=300 and lam=1000 STILL collapse to ~0.01 bps under global normalization —
the transmit-nothing local optimum is escapable, but only when lambda is high
enough (3000 here) to make transmitting worth it before the entropy bottleneck
closes. This is a two-part diagnosis, not one: the per-tile-normalization bug
AND lambda calibration both had to be wrong for the closed runs to fail, and
fixing only one is not enough. The recorded "[50,300] is 1-2 orders too low"
estimate is corroborated and sharpened: even 300-1000 is too low WITH the
normalization fixed; the working regime starts around 3000 on this data.

**Interpretation (a), scoped honestly:** the collapse is escapable by the
engineering fix (global norm + sufficient lambda), which SUPPORTS "the failures
were engineering, not architecture" — but the evidence to date is a single,
undertrained, low-rate (~0.5 bps) escape, far below the Gotcha R_c = 7.99 bps
region of interest. It is a mechanism confirmation, NOT yet a strong codec, and
must be stated that way. No claim beyond "the transmit-nothing failure mode is
now understood and escapable" is licensed by this run.

**SANITY GATE (Amendment 6): not yet evaluated.** The two-sided eval is the
follow-on; the escaping arm is undertrained and low-rate, so a matched-rate
comparison against classical is only meaningful after convergence. Declared next
step (resolving the lower bound the rule flags): extend lam=3000 to convergence
(more steps), re-read the slope, THEN run `eval_gotcha_neural.py` on the
gnorm checkpoints for the first genuine two-sided learned-codec datapoints.
Illinois (128px, 3.98 GB tfocus set) repeats the same protocol after Gotcha.

## AMENDMENT 7 EVAL READOUT — converged but FAILS the sanity gate on spurious;
## the engineering confound is removed and the real gap is isolated (2026-08-13)

Extended lam=3000 to 25,000 steps (`configs/ae_gotcha_gnorm_long.yaml`): converged,
final-decile slope **+0.0%** (the undertrained lower bound is resolved), settling
at ~0.6-0.7 bps. Scored through the identical two-sided pipeline
(`scripts/eval_gotcha_neural.py`, same held-out crop, uses the stored global scale):

| codec | rate (bps) | Pd | spurious (budget 36.9) | sustains? |
|---|---|---|---|---|
| **gnorm lam3000 (converged)** | **0.627** | **0.501** | **2534** | no |
| classical @ nearest low rate: J2K r32 | 0.99 | 0.442 | 158 | no |

**Sanity gate (Amendment 6 rule 2): FAILED, on the spurious axis.** At a LOWER
rate the learned codec has HIGHER Pd (0.501 > 0.442) but ~16x MORE spurious
(2534 vs 158); J2K at 0.6 bps would be worse on Pd but far better on spurious.
It does not beat classical on BOTH axes. Nothing sustains the absolute criterion
at 0.6 bps (Gotcha R_c = 7.99), so this is a relative, matched-rate verdict.

**What this rules IN and OUT — the value of the run.** The model CONVERGED
(slope +0.0%), which FALSIFIES rule 2's own premise that "failure => non-
convergence." This is a converged model that still fails to beat classical.
Therefore the remaining gap is NOT the normalization bug (fixed: transmit-nothing
collapse is gone, the codec carries real information) and NOT undertraining
(converged). By elimination it is (1) model capacity — 0.53M params at CPU scale
— and/or (2) the training objective — MSE is blind to detection, and 2534 spurious
at 0.6 bps is precisely the fidelity-objective-floods-false-alarms signature the
whole study predicts. Both are proposed follow-on scope (GPU-scale model; detection-aware
loss, Q3).

**Mapped to the pre-registered interpretation:** Amendment 7 PRIMARY (collapse
breaks) MET; SANITY GATE failed at converged small-MSE scale -> pre-registered
branch (b): "architecture/objective genuinely limited at this budget; motivates
the detection-aware training loss (Q3) as the next, separate probe," now joined
by model scale as the second candidate. Neither confirmed nor refuted that a
proper codec can win — the run REMOVED the engineering confounds (normalization,
calibration, convergence) and isolated the real, fundable question: can a larger
model and/or a detection-aware objective beat classical at matched rate?

**P2 note:** the signature (low Pd AND high spurious) matches neither P2 pole
(blur nor ring), as on Illinois — the converged MSE codec floods false alarms
rather than blurring. Candidate mechanism still open: independent per-tile
compression at eval leaves seams that focusing amplifies into phantoms — distinct
from the now-fixed normalization issue, and the next diagnostic if the detection-
aware objective is pursued.

**Go/no-go, honestly:** net-positive evening. A diagnosed bug is fixed and
verified; the failure is no longer degenerate; the remaining gap is exactly the
proposed follow-on work. This strengthens the "credible, mechanism-grounded
path" claim (the engineering objections are now answered with a converged run),
without overclaiming a working codec — which there is not, yet.

## AMENDMENT 8 — detection-aware training loss [redacted: programmatic note], pre-registered
## BEFORE the run (2026-08-13; NO detection-aware code or results exist)

**Motivation from Amendment 7.** The normalization bug is fixed and the converged
small MSE codec still fails the sanity gate by FLOODING false alarms (0.627 bps:
Pd 0.501, spurious 2534, vs classical 0.442/158). MSE is blind to detection. This
amendment tests whether a DETECTION-AWARE objective controls the false alarms AT
THE SAME MODEL SCALE — isolating the OBJECTIVE variable from the model-capacity
variable. This is follow-on Task 3 ([redacted: programmatic note]), tested first at private expense on
public data (house rule #5), small/CPU scale, BEFORE any GPU spend.

**On disk at declaration (house rule #4).** Amendment 7 gnorm checkpoints and the
MSE-baseline eval row (0.627/0.501/2534) in runs.jsonl; NO detection-aware loss
code; NO detaware checkpoints or results.

**The loss, declared exactly.** Operate in the focused (detection) domain — for
Gotcha this IS the patch domain (patches are range-Doppler). Per pixel, power
p = Re^2 + Im^2 from the 2-channel tensor. Local background bg = k x k average-pool
of the REFERENCE power (k=9), differentiable. Detection-aware distortion:

    L_det = mean( (p_hat - p_ref)^2 / (bg_ref + eps) )

Rationale: dividing the power error by the local reference background UP-WEIGHTS
errors in dark regions (small bg) — exactly where phantom energy becomes a CFAR
false alarm — and DOWN-weights bright regions, while still penalizing missed bright
peaks (zero output at a scatterer costs p_ref^2/bg, large where p_ref >> bg). It is
a soft CFAR-consistency surrogate: penalize creating or destroying local contrast,
which is what CFAR detects. Training loss = bps + lambda * L_det. Global
normalization retained (Amendment 7). Selectable via `loss: detaware`; `loss: mse`
retained as the Amendment 7 default.

**Comparison design (apples-to-apples).** SAME 0.53M architecture, SAME Gotcha data,
SAME global normalization, SAME converged step budget — ONLY the loss changes.
Lambda calibrated so the detaware codec lands near the MSE codec's 0.627 bps for a
matched-rate comparison; the lambda locating sweep is reported in full.

**Endpoints, declared before eval results:**
1. PRIMARY: at matched rate (~0.6 bps), does the detection-aware codec REDUCE
   spurious vs the MSE codec's 2534? Positive signal = spurious materially below
   2534 and moving toward/below the classical reference (~158 at 0.99 bps) WITHOUT
   collapsing Pd below the MSE codec's 0.501.
2. SECONDARY (full sanity gate, Amendment 6): does it now BEAT classical at matched
   rate on BOTH Pd and spurious? (Pd may still need GPU-scale capacity.)
3. INTERPRETATION, fixed now: (a) spurious drops sharply at matched rate with Pd
   held/improved -> the detection-aware OBJECTIVE controls the false-alarm failure
   mode at fixed scale -> mechanism validated -> GPU bigger-model scale-up
   (for Pd) is the justified next spend. (b) spurious does not drop -> the flooding
   is not (only) an objective problem (tiling seams, capacity); iterate the loss /
   diagnose seams. (c) spurious drops but Pd collapses -> loss over-penalizes
   dark-region energy; rebalance with a fidelity term.

**Convergence rules (Amendment 6) carry over.** Scope: objective-isolation at small
CPU scale on public data. The GPU bigger-model scale-up is the declared FOLLOW-ON,
contingent on outcome (a) — validate the objective before paying for scale.

## AMENDMENT 8 READOUT — the detection-aware objective CONTROLS false alarms
## (2534 -> 0); it overshoots Pd; the objective brackets the tradeoff (2026-08-13)

Same 0.53M model, same Gotcha data, same global norm, same 25k-step budget as the
MSE run — ONLY the loss differs (`configs/ae_gotcha_detaware.yaml`). Two-sided eval,
identical held-out crop and CFAR config:

| codec | loss | rate (bps) | Pd | spurious (budget 36.9) | conv. slope |
|---|---|---|---|---|---|
| MSE baseline (Amend. 7) | MSE | 0.627 | 0.501 | 2534 | +0.0% |
| detaware lam=1000 | L_det | 0.543 | 0.266 | **0** | -10.6% (descending) |
| detaware lam=3000 | L_det | 0.609 | 0.244 | **0** | +12.8% |
| classical J2K (nearest) | — | 0.99 | 0.442 | 158 | — |

**PRIMARY endpoint (does spurious drop from 2534 at matched rate?): MET,
decisively.** At matched rate (~0.55-0.6 bps) the detection-aware codec produces
ZERO spurious detections vs the MSE codec's 2534 and classical's 158. The objective
demonstrably controls the false-alarm failure mode that MSE is blind to. This is the
core mechanism — the training objective steers detection behavior — shown
directly at fixed model scale.

**But Pd collapsed (0.501 -> 0.26): pre-registered branch (c).** The v1 form
L_det = mean((p_hat-p_ref)^2 / bg) over-penalizes dark-region energy: at low rate the
model finds it cheaper to ZERO everything but the strongest scatterers than to spend
bits reconstructing weak ones, so it eliminates phantoms and weak targets alike.
Diagnosis matches the pre-registration exactly: "spurious drops but Pd collapses ->
loss over-penalizes dark-region energy; rebalance with a fidelity/target-preservation
term." lam=1000 is still descending (-10.6%) -> Amendment 6 lower bound; Pd may rise
with more training, but the qualitative over-suppression is clear.

**The decisive interpretation: the OBJECTIVE brackets the detection tradeoff.**
- MSE (fidelity): high recall, floods false alarms  (Pd 0.50 / spurious 2534)
- detaware v1 (aggressive FA penalty): zero false alarms, low recall  (Pd 0.26 / 0)
The two-sided operating point (Pd >= 0.9 AND spurious <= 37) lies BETWEEN these corners,
and the loss is the lever that moves between them. This is the cleanest validation to
date of the study's central thesis: detection behavior is set by the training
objective, not the architecture. Neither corner passes the sanity gate — this is NOT a
working codec — but the mechanism is no longer hypothetical.

**Scope / honesty (house rules #3, small-sample discipline).** One scene (Gotcha),
0.53M CPU model, lam=1000 undertrained. This demonstrates OBJECTIVE CONTROLLABILITY and
a bracketed tradeoff; it does NOT establish a codec that meets the criterion. Every
claim scoped to N=1 here (Illinois repeat pending), consistent with the study's N=2
discipline.

**Next (declared): v2 loss, then scale.** The scouts' prescription and the RDP
bounded-cost result (full distribution-matching costs <= ~3 dB, near-free in rate with
a shared-seed stochastic decoder) say the middle point is reachable. v2 = a TWO-SIDED
threshold hinge (Eban-style): keep true target cells ABOVE the local CFAR threshold
(recover Pd) AND push background cells BELOW it (hold spurious), plus a light fidelity
anchor — replacing v1's one-sided L2-under-a-weight. Implemented in this commit as
`loss: detaware2`; a scored run requires its own pre-registration (Amendment 9). CPU
balances the tradeoff first; GPU bigger-model scale-up then lifts absolute Pd.

## AMENDMENT 9 — theory-grounded two-sided loss (detaware2), pre-registered
## BEFORE the run (2026-08-13; loss-design scout literature folded in)

**Context.** Amendment 8 v1 showed the detection-aware OBJECTIVE controls false alarms
(2534 -> 0) but v1's one-sided L2/(bg) over-suppressed Pd (0.50 -> 0.26). A targeted
literature scout (4 agents; results in `prior_art.md` addendum + the curated set) gives
the math to reach the MIDDLE of the tradeoff. This amendment folds that theory into the
loss and pre-registers the run.

**The loss, declared exactly (each term cited to its source).** On focused-domain power
p = Re^2+Im^2, local background bg = kxk avg-pool of REFERENCE power (k=9), CFAR statistic
T = p/bg, threshold multiplier tau, target mask tgt = (T_ref > tau), background bgm = 1-tgt:

    dist = w_fid * MSE(x_hat, x)                                   [stability anchor]
         + beta_md * mean_tgt( relu(tau - T_hat)^2 )               [Eban 2017: keep targets above tau -> Pd]
         + beta_fa * mean_bg(  relu(T_hat - tau)^2 )               [Eban 2017: push clutter below tau -> spurious]
         + beta_dist * [ (mean_bg T_hat - mean_bg T_ref)^2
                       + (std_bg T_hat  - std_bg T_ref)^2 ]        [CFARnet + Blau-Michaeli RDP 2019]
    loss = bps + lambda * dist

Theory grounding, term by term:
- **Two-sided threshold hinge (Eban et al., AISTATS 2017, arXiv:1608.04802).** Detection is
  a THRESHOLD decision, not an L2 distance (the scouts' consensus critique of v1). Encodes
  our spec as a two-sided constraint: recall (Pd) via a hinge that keeps target cells above
  the local CFAR threshold, false-alarms via a hinge that pushes clutter below it. A cell
  only needs to CROSS tau, not be perfectly reconstructed -> cheaper than L2 at low rate,
  which is exactly why v1 could not afford to keep weak targets and v2 can.
- **Clutter-statistic distribution matching (CFARnet, Diskin & Wiesel 2022-24,
  arXiv:2206.05747/2208.02474; Blau-Michaeli RDP, ICML 2019, arXiv:1901.07821).** RDP theory
  says MSE converges to the posterior mean, which WARPS the clutter distribution the CFAR is
  calibrated to -> false alarms; the prescribed fix is a distribution divergence between
  reconstruction and reference on LOCAL clutter statistics. CFARnet makes it concrete: match
  the null distribution of the CFAR test statistic over background cells. We approximate that
  divergence by matching the first two moments (mean, std) of T over background -- re-
  calibrating the null at the source, GENTLY (it demands correct statistics, not zero energy,
  so it should not reproduce v1's over-suppression).
- **Fidelity anchor is plain MSE, NOT perceptual/GAN, on purpose (HiFiC anti-pattern,
  Mentzer 2020, arXiv:2006.09965).** A perceptual/adversarial term would SYNTHESIZE plausible
  bright structure -> manufacture false alarms. Deliberately excluded.

**Deliberately DEFERRED (staged, with reason -- keeps this run interpretable):**
- Eban's LEARNED Lagrange multiplier (auto-balancing beta_md/beta_fa): betas hand-set here
  so the run is a clean objective test, not a min-max tuning.
- Wagner common-randomness STOCHASTIC decoder (arXiv:2202.04147; near-free rate cost for
  distribution matching): an ARCHITECTURE change -> confounds objective isolation; GPU/Phase-I.
- Smooth-AP ranking surrogate (arXiv:2007.12163): alternative to the hinge; try if hinge
  underperforms.
- Detector-in-the-loop (Chamain, DCC 2020): backprop the actual CFAR/detector -> the endgame,
  a bigger change; staged after the surrogate is validated.
- Explicit tail/quantile (CVaR) or full MMD match: moment-match is the cheap first cut; upgrade
  if the Pfa TAIL (not the bulk) proves under-controlled.

**Comparison design.** SAME 0.53M model, data, global norm, and 25k-step budget as the MSE
(Amend. 7) and v1 (Amend. 8) runs -- ONLY the loss changes. Lambda calibrated (rate-only
sweep) to land near ~0.6 bps for a matched-rate comparison; the ladder is reported in full.
tau=8 is an approximation of the eval CA-CFAR operating threshold, recorded as such.

**Endpoints, declared before eval results:**
1. PRIMARY: does v2 LIFT Pd above v1's 0.26 while HOLDING spurious low (<< the MSE codec's
   2534, ideally at/below the classical 158) at matched rate -- i.e., move toward the MIDDLE
   of the tradeoff both prior corners missed? Positive = Pd materially > 0.26 AND spurious
   far below 2534.
2. SECONDARY (full sanity gate, Amendment 6): beat classical at matched rate on BOTH Pd and
   spurious. Absolute Pd >= 0.9 may still require GPU-scale capacity.
3. INTERPRETATION: (a) Pd up + spurious low -> the theory-grounded two-sided loss reaches the
   middle -> objective is steerable to the operating point -> GPU bigger-model scale-up is the
   justified next spend (to lift absolute Pd). (b) Pd stays ~0.26 with spurious low -> the
   small model cannot hold both at this scale -> capacity is binding -> GPU. (c) spurious
   climbs back toward MSE levels -> hinge/dist balance is off -> tune betas / add the tail term.

**Convergence rules (Amendment 6) carry over.** Scope: objective test at small CPU scale,
public data, private expense. On disk at declaration: MSE + v1 checkpoints/eval rows; the
detaware2 code (committed); NO detaware2 scored results.

## AMENDMENT 9 READOUT — the theory-grounded loss REACHES THE TRADEOFF MIDDLE
## and lands on the classical operating region; undertrained (2026-08-13)

Same 0.53M model, data, global norm, 25k-step budget as MSE (Amend. 7) and v1 (Amend. 8) --
only the loss changed. Calibrated lambdas [300, 1000]. Two-sided eval, identical crop/CFAR:

| run | loss | rate (bps) | Pd | spurious (budget 36.9) | conv. slope |
|---|---|---|---|---|---|
| MSE (Amend. 7) | fidelity | 0.627 | 0.501 | 2534 | +0.0% |
| v1 (Amend. 8) | one-sided L2/bg | 0.54 | 0.266 | 0 | -10.6% |
| **v2 lam=1000** | theory two-sided | 1.044 | 0.320 | 73 | -13.4% (descending) |
| **v2 lam=300** | theory two-sided | 1.058 | 0.420 | 163 | -14.8% (descending) |
| classical J2K (ref) | — | 0.99 | 0.442 | 158 | — |

**PRIMARY endpoint (lift Pd off v1's 0.26 while holding spurious far below MSE's 2534):
MET.** v2 walks UP the Pd axis (0.266 -> 0.320 -> 0.420) with spurious held at 73-163 --
two orders of magnitude below MSE's 2534. The theory-grounded two-sided loss steers the
codec to INTERMEDIATE operating points that neither prior corner (MSE flood / v1 zero-Pd)
could reach. The three-run arc at fixed scale -- MSE floods, v1 over-suppresses, v2 lands
in the middle -- is the clean demonstration that the TRAINING OBJECTIVE is the lever on
the detection tradeoff. That is the study's central thesis, shown across three controlled
runs differing only in the loss.

**Rate note (honest):** v2 converged to ~1.05 bps, HIGHER than the ~0.6 bps calibration
target (the 2,500-step calibration underestimated the converged rate). The clean matched-
rate comparison is therefore v2 vs classical J2K at ~1 bps, not vs MSE/v1 at ~0.6.

**SECONDARY endpoint (sanity gate -- beat classical at matched rate on BOTH): NOT met;
v2 lands ON the classical operating region, marginally behind.** At ~1 bps, v2 lam=300
(Pd 0.420, 163 spurious, 1.058 bps) sits just behind classical J2K (Pd 0.442, 158 spurious,
0.99 bps): slightly higher rate, slightly lower Pd, comparable spurious. v2 does NOT beat
classical -- but it has escaped both catastrophic corners and reached the frontier's
neighborhood. BOTH v2 runs are still descending (-13 to -15%) -> Amendment 6 lower bounds;
Pd is undertrained and expected to rise with more steps.

**INTERPRETATION (pre-registered branches a/b).** The objective is validated as steerable
across the tradeoff and reaches the classical operating region (branch a: the loss reaches
the middle). At this small (0.53M) undertrained CPU scale it MATCHES-minus classical rather
than beating it (branch b: capacity/training now binding). The binding constraint has moved
from the OBJECTIVE (solved: MSE->flood, v1->over-suppress, v2->middle) to MODEL CAPACITY +
TRAINING BUDGET. Two cheap-before-expensive next steps, in order: (1) CONVERGE v2 on CPU
(both arms still descending -- free, may lift Pd further before any spend); (2) if it
plateaus at/below classical, the GPU bigger-model scale-up is now the justified spend, with
a validated objective to scale.

**Scope / honesty (house rule #3, small-sample discipline).** N=1 scene (Gotcha), 0.53M CPU
model, undertrained lower bounds. This establishes OBJECTIVE CONTROLLABILITY, TRADEOFF
TRAVERSAL, and PARITY-MINUS with classical at ~1 bps -- NOT beating the frontier, and not
yet meeting the absolute two-sided criterion (nothing does below R_c=7.99 on Gotcha).
Illinois repeat and GPU scale-up remain the path. Every number scoped to N=1 here.

## AMENDMENT 10 — v3 loss: round-2 theory folded in (CFAR-principled tau, soft-hinge,
## tail-CCDF match, lambda warm-up), pre-registered BEFORE the run (2026-08-13)

**Context.** v2 (Amend. 9) reached the tradeoff middle (Pd 0.42, spurious 163 @ ~1 bps) but
only parity-MINUS with classical, and was undertrained (slope -14% at 25k). A round-2
literature scout (training dynamics; CFAR statistics; architecture -- see `prior_art.md`
addendum) supplies principled fixes. This amendment folds the loss/schedule ones into v3
(detaware3) and pre-registers the run. Architecture changes (width, complex layers) and the
Stage-2 hard-round fine-tune are DEFERRED (see below).

**Changes vs v2, each cited:**
1. **CA-CFAR training-ring background -> principled tau (Richards FoRSP Ch.16; Gandhi-Kassam
   T-AES 1988).** Background is now the mean over the evaluator's guard/train RING
   (cfar_win=21 minus cfar_guard=5 -> N=416), not a 9x9 pool. For CA-CFAR the threshold is
   tau = N(Pfa^(-1/N)-1); at Pfa 1e-4, N=416 -> **tau = 9.31**, calibrated to the evaluator by
   construction. v2's tau=8.0 corresponded to Pfa ~3.4e-4 (~3.3x too loose).
2. **Temperature-annealed SOFT hinge (softplus) replacing hard relu (Guo "Soft-then-Hard"
   spirit; Balanced-RD).** A hard hinge gives zero gradient in its flat region (easy targets /
   well-below-threshold clutter -> no learning signal), a diagnosed cause of v2's slow descent.
   Soft-hinge gives gradient everywhere; temperature anneals smooth->sharp over training.
3. **Tail-CCDF clutter matching replacing mean+std moment match (Weinberg 2014; CFARnet).**
   CA-CFAR is CFAR in clutter POWER but not SHAPE; SAR clutter is heavy-tailed (K/Pareto), and
   the evaluator's nominal Pfa is only truthful if residual clutter is ~exponential. So match
   the upper-tail soft-CCDF P(T>t) of reconstruction clutter to the reference at t in
   {0.5,0.75,1.0}xtau, in log space -- the region the CA-CFAR false-alarm integral sees --
   rather than global moments.
4. **Lambda warm-up (Balanced RD, CVPR 2025).** Distortion-heavy early (lam x mult, annealed)
   to avoid the rate-collapse basin (rate->0, dead encoder) seen in the low-lambda MSE runs.

**DEFERRED, with reason:**
- **Stage-2 hard-round fine-tune (Guo 2021).** Highest-value "reclaim Pd for free" item, but
  needs a STRAIGHT-THROUGH ESTIMATOR added to the model's quantizer (current `_quant` hard-
  rounds with NO gradient at eval). Staged as v3.1 immediately after this run.
- **Architecture (width scale-up; complex-valued layers; keep LeakyReLU/no-GDN).** GPU-scale
  work (FINDINGS/prior_art); this run isolates the loss/schedule fixes at fixed 0.53M scale.
- Learned Lagrange multiplier; stochastic decoder (common randomness) -- as before.

**Comparison design.** SAME 0.53M model, data, global norm, 25k budget as v2 -- only the loss
+ schedule change. Lambda calibrated (rate-only sweep) to land near v2's ~1 bps for matched
comparison; ladder reported in full.

**Endpoints, declared before eval results:**
1. PRIMARY: does v3 IMPROVE on v2's (Pd 0.420, spurious 163 @ 1.06 bps) at matched rate --
   higher Pd at equal-or-lower spurious, or lower spurious at equal Pd (a better point on the
   Pd/spurious frontier)? AND does it converge better (final-decile slope less negative than
   v2's -14% at 25k)?
2. SECONDARY (sanity gate): beat classical J2K at matched rate on BOTH (vs 0.442/158 @ ~1 bps).
3. INTERPRETATION: (a) v3 beats v2 AND reaches/exceeds classical -> the calibration+convergence
   fixes closed the gap, possibly without GPU. (b) v3 beats v2 but still parity-minus classical
   -> capacity binding -> GPU width scale-up (with a sharpened loss). (c) v3 ~ v2 -> loss
   calibration wasn't the lever at this scale -> capacity is the story -> GPU.

**Open calibration caveats (CFAR scout, honest).** tau=9.31 assumes single-look exponential
clutter + IID reference cells. If the focused image is multi-look, the true multiplier is
lower (Gamma-L); post-focus pixel correlation reduces effective N and raises true tau. Both
need a quick check against the Gotcha data; recorded as approximations. Convergence + small-
sample (N=1) discipline carry over. On disk: v2 checkpoints/eval rows; detaware3 code
(committed); NO detaware3 scored results.

## AMENDMENT 10 READOUT — v3 REGRESSED (catastrophic Pd collapse); the naive
## high-threshold hinge over-suppresses -> motivates the v4 margin loss (2026-08-13)

Same 0.53M model/data/global-norm/25k budget as v2; only loss+schedule changed
(`configs/ae_gotcha_detaware3.yaml`). Two-sided eval, identical crop/CFAR:

| run | loss | rate (bps) | Pd | spurious (budget 36.9) | conv. slope |
|---|---|---|---|---|---|
| v2 (Amend. 9) | two-sided hinge, tau=8 | 1.06 | 0.420 | 163 | -14.8% |
| **v3 lam=300** | detaware3, tau=9.31 | 0.501 | **0.005** | 0 | -3.0% (converged) |
| **v3 lam=1000** | detaware3, tau=9.31 | 0.548 | **0.011** | 0 | -5.2% (converged) |

**PRIMARY endpoint (improve on v2's 0.420/163): FAILED, badly.** v3 collapses Pd to ~1% --
worse than v1 (0.26) and far worse than v2 (0.42). It did NOT improve; it regressed to the
detect-nothing corner. Convergence was BETTER than v2 (slopes -3/-5% vs -14% -- the soft-hinge
helped convergence exactly as predicted), so this is NOT undertraining: **the loss converged to
over-suppression.** An honest negative result, reported per house rules.

**Diagnosis (what over-suppressed).** Three v3 changes compounded to push the model off targets:
1. **Principled-but-higher tau=9.31 (vs v2's 8.0).** A detection now requires the recon cell
   statistic to exceed 9.31 over an N=416 ring. At ~0.5 bps on a 0.53M model, weak scatterers
   cannot be pushed that high, so the missed-detection hinge is unsatisfiable and the model
   abandons them. The "correct" evaluator threshold is *harder to train against* than a lower one.
2. **beta_dist=10** over-weighted clutter suppression (tail-CCDF) relative to target preservation
   (beta_md=1) -> the model optimizes "kill clutter" over "keep targets."
3. **Naive hard-threshold hinge** `relu(tau - t_hat)^2` -- exactly the saturating/over-penalizing
   form the Swerling scout flagged: it demands cells reach an absolute threshold rather than
   rewarding the achievable SNR margin, so under capacity pressure it gives up entirely.

**This is not "the theory was wrong" -- it is evidence FOR the v4 design.** v3's failure is the
concrete demonstration that a hard hinge at the true CFAR threshold collapses under capacity/rate
pressure. The v4 spec's **SNR-margin loss** (`L_md = softplus(beta*(r_req - r_hat))`, r_req from the
closed-form operating point) is designed precisely to avoid this: it rewards moving a target's SNR
toward detectability with non-vanishing gradient, instead of an all-or-nothing threshold crossing.
v3 de-risks that choice by showing the naive alternative fails.

**Standing best: v2 (0.420/163 @ ~1 bps).** v3 is set aside as a mis-parameterized branch.
**Next:** (1) fold in the pending v2-100k convergence result (capacity vs undertraining on the
WORKING v2 loss); (2) build v4 with the margin-based detection loss + rebalanced betas (lower
beta_dist), which v3's collapse directly motivates; optionally a quick v3-rebalance
(margin loss, beta_dist~1, tau back toward 8) as a control. Scope: N=1 (Gotcha).

## v2 100k CONVERGENCE FOLLOW-UP — more training lifts Pd but spurious balloons;
## points to capacity + operating-point control (2026-08-13)

v2 lam=300 extended 25k -> 100k steps (`ae_gotcha_detaware2_long.yaml`). Two-sided eval:

| run | rate (bps) | Pd | spurious (budget 36.9) | slope |
|---|---|---|---|---|
| classical J2K | 0.99 | 0.442 | 158 | — |
| v2-25k | 1.058 | 0.420 | 163 | -14.8% |
| **v2-100k** | 1.056 | **0.575** | **777** | -14.5% (STILL descending) |

**Reading.** (1) Undertraining WAS suppressing Pd — 4x steps raised Pd 0.42 -> 0.575. (2) But the
false-alarm side degraded badly (163 -> 777) as the model reconstructs more of *everything*,
targets and phantoms alike. (3) v2-100k beats classical on Pd (0.575 > 0.442) but loses heavily
on spurious (777 >> 158) -> still NOT a clean win. (4) v2's HARD hinge never converges (-14.5% at
100k) -- corroborating the training-dynamics scout (soft-hinge needed); v3's soft-hinge did
converge (slopes -3/-5%), it just over-suppressed on the tau/beta balance.

**Diagnosis, combining v3 + v2-100k.** At 0.53M params the model can raise Pd with more
training/rate but CANNOT hold the false-alarm operating point while doing so. That is exactly two
things at once: **capacity** (too small to separate target from phantom at higher Pd) and
**operating-point control in the loss** (nothing pins Pfa as Pd rises). This is precisely what v4
is designed for: the analytic-Pfa term drives residual clutter to the exponential null so the
nominal tau *is* the 1e-4 point (holds spurious), and the SNR-margin detection term lifts Pd with
non-vanishing gradient (avoids v3's collapse). v4 is free (CPU) and targets the loss half; GPU
width scale-up  targets the capacity half.

**GATE = loss-quality + capacity (both).** Order: build **v4** (free, soft margin + analytic Pfa +
rebalanced betas, tau trainable), eval; if v4 improves the tradeoff but stays capacity-bound, do
the **GPU width scale-up** on the v4 loss. Standing best remains v2 (0.42/163, or 0.575/777 at
100k -- a different point on the same unsatisfactory frontier). Scope: N=1 (Gotcha).

## AMENDMENT 11 — v4 analytic operating-point loss (detaware4), pre-registered
## BEFORE the run (2026-08-13; math adversarially verified)

**Context.** v3 collapsed (naive hard hinge at the true tau=9.31 -> detect-nothing); v2-100k
showed more training lifts Pd (0.42->0.575) but spurious balloons (163->777) -- the model can't
hold the false-alarm operating point as Pd rises. v4 targets BOTH failure modes with an analytic
operating-point loss (spec + adversarial math check: `reports/v4_analytic_pfa_loss_spec.md`).

**The loss (each side math-verified):**
1. **FA side -- scintillation-index anchor.** Over background cells, drive the reconstruction power
   distribution to the exponential null: `L_fa = (log SI_hat - log si_target)²`, SI = E[p²]/E[p]²,
   si_target=2 (single-look). Because Pfa=(1+tau/N)^-N holds exactly for exponential clutter, this
   makes the nominal tau=9.31 THE 1e-4 operating point -- holding Pfa as Pd rises (the thing
   v2-100k could not do). Verified: SI=2(1+1/nu), SI=2 <=> exponential (nu->inf).
2. **Pd side -- SNR margin, not a threshold hinge.** `L_md = mean_tgt(softplus(beta*(r_req-r_hat)))`,
   r_hat = t_hat-1, `r_req = (Pfa^-1/N-1)/(0.9^-1/N-1)-1 = 87.4 (19.4 dB)` from the closed-form
   operating point. Non-vanishing gradient rewards partial SNR progress -> avoids v3's saturating
   all-or-nothing collapse. EXACT for Swerling I/II; conservative for dominant SAR scatterers.
3. Light MSE fidelity anchor (NOT perceptual -- HiFiC).

**Verified caveats (from the adversarial check).** si_target=2 is single-look-only (=1+1/L for
L-look -- verify look count); Pfa-inflation magnitude is texture-correlation-dependent but the
SI->exponential anchor is safe under any correlation model; Swerling-I is the conservative target.

**Comparison design.** SAME 0.53M model/data/global-norm/25k budget; only the loss changes.
Lambda calibrated (rate-only sweep) to ~1 bps for matched comparison; ladder reported.

**Endpoints, declared before eval results:**
1. PRIMARY: does v4 HOLD the false-alarm operating point as Pd rises -- higher Pd at LOWER spurious
   than v2 at matched rate (v2: 0.42/163 @ 1.06; v2-100k: 0.575/777)? Positive = Pd >= 0.42 with
   spurious materially below v2's, moving toward classical's 158 / the 37 budget.
2. Does it AVOID v3's collapse (Pd not near-zero)? (The margin loss should.)
3. SECONDARY (sanity gate): beat classical J2K (0.442/158 @ ~1 bps) on BOTH.
4. INTERPRETATION: (a) v4 holds spurious as Pd rises -> the analytic operating-point loss works,
   the LOSS half is solved; any residual gap is capacity -> GPU width. (b) v4 improves but stays
   capacity-bound -> GPU on the v4 loss. (c) v4 collapses like v3 -> margin/SI/beta balance needs
   tuning. Convergence + small-sample (N=1) discipline carry over. On disk: v1/v2/v3 checkpoints +
   eval rows; detaware4 code (committed); NO detaware4 scored results.


## [omitted in mirror: two programmatic sizing notes, 2026-08-13, no technical content]

## AMENDMENT 11 READOUT — v4 loss DESIGN validated (no collapse, spurious controlled)
## but landed low-rate -> matched-rate win INCONCLUSIVE (2026-08-13)

Same 0.53M model/data/global-norm/25k budget; only the loss changed (`ae_gotcha_detaware4.yaml`).

| run | rate (bps) | Pd | spurious (budget 36.9) | slope |
|---|---|---|---|---|
| v3 (Amend 10) | 0.50 | 0.005 | 0 | collapse |
| **v4 lam=1000** | 0.300 | 0.306 | 109 | -0.8% (converged) |
| **v4 lam=3000** | 0.379 | 0.290 | 92 | -3.7% (converged) |
| v2 (Amend 9) | 1.058 | 0.420 | 163 | -14.8% |

**Endpoints:** (2) AVOID v3's collapse -> MET (Pd 0.30 not 0.01; the SNR-margin softplus rewards
partial progress as designed). Spurious control -> POSITIVE (92-109 vs MSE 2534 / v2-100k 777; the
SI-anchor holds the operating point). Convergence -> best of any run (-0.8/-3.7%; the soft margin +
SI-anchor give stable non-degenerate convergence). (1) PRIMARY (beat v2 0.42/163 at matched rate) ->
INCONCLUSIVE: both lambdas landed at 0.3-0.4 bps, not the ~1 bps needed for a matched comparison (the
rate-calibration risk flagged pre-run materialized). v4 sits at a lower-rate operating point that
avoids both catastrophic corners; whether it beats v2 needs lambda recalibrated up.

**Net.** The v4 loss DESIGN is validated -- it converges cleanly, avoids collapse, and controls
spurious, which is what the analytic operating-point construction (SI-anchor + SNR margin) was for.
The clean matched-rate WIN vs v2/classical is not established, and the honest reason is calibration +
capacity, not loss structure. Combined with v2-100k (capacity is half the gap) this confirms: **the
loss half is essentially settled; the remaining gap is capacity (GPU width) + matched-rate lambda.**
We are at the diminishing-returns edge of loss-craft on a 0.53M / N=1 setup.

**Decision.** The feasibility story is now COMPLETE without beating classical: (1) opportunity sized
(~1-3 bits, the 0.25-raw->focused inversion), (2) objective controllability demonstrated across five
runs, (3) analytic operating-point loss validated (converges, no collapse, spurious controlled). The
matched-rate v4 number and the classical-beating result are CAPACITY/GPU work -> follow-on. Optional
cheap follow-up: recalibrate v4 lambda up (~x3-10) for the matched-rate point. Otherwise PIVOT TO
WRITING (preprint + follow-on skeleton). Scope: N=1 (Gotcha).

## AMENDMENT 12 / C10 READOUT — Stage-2 hard-round fine-tune: calibration gap is
## SMALL; by elimination the binding constraint is CAPACITY (2026-08-13)

Stage-2 fine-tune of the v2 standing-best checkpoint (lam=300, 0.420/163 @ 1.06 bps): freeze
encoder, hard-round via straight-through, tune synthesis+entropy 5k steps
(`ae_gotcha_stage2_v2.yaml`). Tests whether reported Pd is suppressed by the AUN(train)/round(eval)
mismatch (Guo 2021).

| run | rate (bps) | Pd | spurious (budget 36.9) |
|---|---|---|---|
| v2 baseline | 1.058 | 0.420 | 163 |
| **C10 Stage-2** | 1.055 | 0.434 | 253 |

**Result: hypothesis LARGELY REFUTED.** Stage-2 lifts Pd only +0.014 and worsens spurious +90 -- a
small move up the same tradeoff, not a clean Pd reclaim. The AUN->round calibration gap is not a
material suppressor here; hard-round training just reallocates along the frontier.

**The elimination argument is now complete.** Three independent free levers, all ruled out as THE gap:
- LOSS structure -> ruled out (v4 Amend 11: validated design, converges, no collapse, spurious controlled)
- TRAINING budget -> ruled out (v2-100k: 4x steps lifts Pd but spurious balloons 163->777)
- CALIBRATION gap -> ruled out (C10: Stage-2 barely moves the operating point)
=> By elimination, the binding constraint is **CAPACITY** (0.53M params, N=1 Gotcha). The free CPU
levers are exhausted and converge on the same diagnosis.

**Decision consequence.** The GPU width scale-up (B6) is now the clearly-justified next lever -- not a
guess, but the residual after eliminating loss/training/calibration. Options: (a) one scoped ~$5 GPU
width run (well-justified; may still be inconclusive if one width bump is insufficient), or (b) accept
"capacity is follow-on" and pivot to writing. Either is defensible; the feasibility story is complete
regardless (opportunity sized, objective controllable, loss validated, free levers exhausted).

## AMENDMENT 13 / GPU CAPACITY READOUT — wide models do NOT beat classical; the
## whole v1-v4 (reconstruction) family is exhausted (2026-08-13, RunPod RTX 2000 Ada)

Wide model (4.14M params, ~8x the CPU runs) on GPU, two configs, two-sided eval on the laptop:

| run | loss | rate (bps) | Pd | spurious (budget 36.9) | slope |
|---|---|---|---|---|---|
| classical J2K | - | 0.99 | 0.442 | 158 | - |
| wide+v2 lam300 | detaware2 | 1.551 | 0.542 | 491 | -11.6% |
| wide+v4 lam10000 | detaware4 | 1.077 | 0.593 | 706 | -7.1% |

**Verdict: neither beats classical.** Both raise Pd (wide+v4 gives our best-ever 0.593) but neither
controls spurious at matched rate (491, 706 vs classical's 158). Capacity + [redacted: programmatic note] operating-point
loss did NOT crack the false-alarm problem. Undertrained (still descending) and N=1, but the pattern
is unambiguous and consistent with every prior run: **we can buy Pd, we cannot buy low spurious.**

**This is theory-predicted (v5 task-based scout):** reconstruction-trained codecs emit excess false
alarms because the objective warps the clutter null distribution the CFAR is calibrated to. The
entire v1-v4 family (reconstruction codec + surrogate detection loss, at any scale) is now EXHAUSTED
as a path to beating classical on the two-sided criterion.

**Consequence -> v5 is the path AND the decisive test.** See `reports/v5_build_plan.md`: compress the
detection sufficient statistic (not the image), differentiable CFAR head with the threshold re-pinned
to Pfa 1e-4 every step, MMD anchor to the uncompressed clutter, VIB rate + NP-constrained loss. The
business go/no-go now rests cleanly on v5: either the theory-optimal two-sided codec beats FDBAQ
(business + a first-in-literature result) or it does not (the ~4.86-7.99 bps floor is fundamental,
not a codec deficiency, and we walk having proven it). Cost of this GPU run: ~$0.10.

## v5 STEP-2 READOUT — detector-in-the-loop collapses to transmit-nothing at these
## betas; calibration, not mechanism (2026-08-13)

detaware5 (differentiable CA-CFAR head in the training loss, reference detections = target mask):
| run | rate (bps) | Pd | spurious |
|---|---|---|---|
| lam=300 | 0.014 | 0.095 | 25 |
| lam=1000 (partial) | ~0.06 | - | - |

**Collapsed to transmit-nothing.** The false-alarm term is trivially minimized by reconstructing
nothing (no detections -> no false alarms); the Pd term is too weak at these betas/lambda to force
transmission -> the same over-suppression basin as v1/v3. The detector-in-the-loop MECHANISM is
validated (runs, steers, gradients flow, differentiable CA-CFAR reproduces the frozen detector) --
this is a CALIBRATION failure. Fix (known from prior collapses): lambda warm-up (distortion-heavy
early) + stronger fidelity/Pd pull to hold it off the transmit-nothing floor. Next: recalibrated
detaware5 (+ optionally the assembled v5 = +MMD +VIB gate) with warm-up.

## v5 STEP-5 READOUT — statistic-domain codec collapses to Pd 0 under a weighted-MEAN
## fidelity; root cause is count-domination, fix is per-region normalization (2026-08-14)

Step 5 compresses the CFAR sufficient statistic T̂ directly (not the image), thresholded at
α=9.31 (Pfa 1e-4). Two configs run:
| run | train rate | eval rate | Pd | spurious |
|---|---|---|---|---|
| stat (background-avg fidelity) | ~0.021 | — | degenerate | — |
| stat_tw (w_tgt=50 weighted mean, lam=10000) | 0.002 | 0.007 | **0.000** | 0 |

**Collapsed to clutter-match, Pd 0.** T̂ converged to ~constant below threshold → zero detections.
Root cause is NOT a transmit-nothing-preserves-Pd degenerate (that does not exist in the statistic
domain — the whole point of step 5). It is that a weighted **MEAN** fidelity is dominated by cell
**COUNT**: clutter is ~2000× the target cells, so even w_tgt=50 contributes 50×0.05% = 0.025 of the
mean vs. clutter's 0.9995 — the sparse targets are still swamped. w_tgt would need to exceed ~2000
to matter, which is the unstable regime.

**Fix = per-region normalization.** Normalize target and clutter fidelity EACH by its own cell count,
then weight: `l_fid = w_tgt·mean_over_targets(sq) + mean_over_clutter(sq)`. Now targets sit at O(1)
regardless of how few there are, so w_tgt weights *magnitudes*, not count-diluted contributions.
Smoke (800 steps, per-region, w_tgt=20): rate 0.1–0.6 bps (transmitting, OFF the 0.002 collapse
floor), distortion O(hundreds) driven by real target reconstruction. Necessary precondition met.
Full run launched: `ae_gotcha_stat_pr.yaml`, 25k steps, lambdas [1000, 3000].

**FIRST REAL POINT (stat_pr lam=1000):** rate 0.569 bps → **Pd 0.301, false 976** (n_ref 369).
The degeneracy is fixed (Pd 0.000 → 0.301: the codec transmits and reconstructs targets). But at
this operating point it sits BELOW the classical curve: jpeg2000 at 0.992 bps gets Pd 0.442 / false
158; ours at 0.569 bps gets Pd 0.301 / **false 976** — 6× more spurious, lower Pd. The false-alarm
wall (excess FAs from warping the clutter null) reappears in the statistic domain. This is ONE
(lowest-rate) point and does NOT settle go/no-go. The decision needs the full rate-detection curve:
does the codec meet the two-sided criterion (Pd≥0.9, false≤~37) at ANY rate below R_c≈8 bps?
Next: rate sweep λ ∈ {1k, 3k, 10k, 30k, 100k} (GPU — ~10h CPU vs ~1.5h pod). lam=3000 in progress.

## v5 STEP-5 DECISIVE READOUT — GPU λ-sweep + calibration-free ROC: statistic-domain codec
## does NOT approach the two-sided criterion; the rate plateaus and the target tail is not
## preserved (2026-08-14, RTX A4500)

Full 5-point λ sweep trained on GPU (RTX A4500), per-region-normalized stat codec, seed 1337.
Fixed-threshold eval (T̂ at classical α=9.31):
| λ | rate (bps) | Pd | false | (n_ref=369, budget≤37) |
|---|---|---|---|---|
| 100000 | 0.492 | 0.119 | 27 |
| 10000  | 0.525 | 0.160 | 98 |
| 3000   | 0.566 | 0.141 | 158 |
| 1000   | 0.672 | 0.352 | 846 |
| 30000  | 0.914 | 0.122 | 48 |

**Calibration ruled out.** Calibration-free ROC (`eval_gotcha_stat_roc.py`) sweeps T̂'s own
threshold and reports the best Pd at false≤37 (oracle operating point on the reconstructed
statistic): **0.106–0.122 for ALL five checkpoints.** Required Pd is 0.9. So the low Pd is not a
threshold-scale artifact — the reconstructed statistic simply does not preserve the target tail at
a controlled false-alarm rate.

**Two independent failure signatures, both fundamental-looking:**
1. **Rate plateau.** 100× λ range moved rate only within 0.49–0.91 bps. The codec refuses to spend
   bits to encode the 0.05%-sparse target tail — under rate+λ·dist, precise target encoding is never
   "worth it" against the clutter-dominated average. The high-rate regime (where classical succeeds,
   ~8 bps) is unreachable by this objective.
2. **False-alarm/Pd coupling.** The only way the codec lowers false alarms (846→27 as λ rises) is by
   detecting less overall — Pd falls WITH false. It never learns to separate target from clutter; it
   just turns detection down. Opposite of what the criterion needs.

**Verdict (scoped).** Across BOTH domains — reconstruction (v1–v4, exhausted) and sufficient-statistic
(v5, this sweep) — and across capacity (wide model), λ (100×), and calibration-free thresholding, no
learned configuration approaches Pd≥0.9 at false≤37 below R_c≈8 bps. Classical dominates at every
matched rate (jpeg2000 @1 bps: Pd 0.44/158 fa; @8 bps: Pd 0.905/30 fa). This is strong evidence the
~5–8 bps two-sided floor is a **source + task property**, not a codec deficiency, FOR THIS SCENE.
**Scope:** Gotcha durango chan1 mis2, N=2 regime. Not yet replicated on Sentinel-1 in the statistic
domain — that is the single highest-value confirmation step (expected to confirm, not reverse).

## v5 CONSTRAINED READOUT — Neyman-Pearson dual ascent: under UNBOUNDED Pd pressure the codec
## spends ZERO bits (rate->0.002), because bits don't buy Pd. Strong fundamental-floor signal
## (2026-08-14, Gotcha, RTX A4500)

statcon = minimize rate s.t. Pd>=0.9, Pfa<=1e-4, with Lagrange multipliers mu_pd, mu_fa driven by
dual ascent (grow while the constraint is violated). 25k steps, Gotcha. Result:
- **mu_pd and mu_fa both pinned at their 5000 cap** (constraint never satisfiable).
- **pd_soft = 0.000** throughout (one flicker to 0.018).
- **rate collapsed to 0.002 bps** — the codec drove rate to zero rather than spend bits.

**Interpretation.** Given an unbounded incentive to spend bits to hold Pd, the optimizer chose to
spend NONE. That is only rational if spending bits does not raise Pd — i.e. more rate buys no
detection. This is the strong form of the negative: not "insufficient budget" but "the target
information is not recoverable through this codec at any reachable rate." Consistent with the
sweep's calibration-free ROC (best Pd 0.12 at budget) and the exhausted reconstruction domain.

**What it closes / doesn't.** Closes: fixed-weight AND constrained training, image AND statistic
domain, 100x lambda, wide capacity — all fail; more bits do not help. Does NOT close: this is one
ENCODER representation (real/imag split). If the target phase coherence is destroyed at ENCODE by
the real/imag representation (not at the bottleneck), a complex-valued encoder could still change
the answer — the one remaining orthogonal lever ([redacted: programmatic note] own suggestion). Foveated/spatial bit
allocation is now largely ruled out (if bits don't help Pd, allocating them spatially won't either).
S1 confirmation (per-region, held-out SM scene) running to test cross-sensor generalization.

## THEORY + WHITENESS VERDICT — the floor is a citable theorem; our own data confirms the
## reconstruction-codec headroom over FDBAQ is <=0.16 bit/sample (2026-08-14)

**Composite theorem (deep-research, all citations verified).** For compress whitened SAR ->
reconstruct -> CFAR at fixed Pfa, on a near-white circular-Gaussian source:
(a) entropy-coded uniform/adaptive quantization is within ~0.25 bit/sample of R(D) and no
    reconstruction codec beats it materially [Gish-Pierce 1968];
(b) the Neyman-Pearson miss-exponent theta(R) is monotone in R and reaches the centralized optimum
    only as R -> H(source); every bit cut strictly degrades detection [Ahlswede-Csiszar 1986; Han
    1987; Shalaby-Papamarcou 1992; Rahman-Wagner 2012];
(c) the detection-sufficient statistic for a target that could be ANYWHERE in i.i.d. clutter is not
    lower-dimensional than the data, so the IB/task-optimal auxiliary coincides with the
    reconstruction-optimal one [Tishby-Pereira-Bialek 1999] -> explains the statistic-domain failure;
(d) any realism/detection-aware objective provably injects synthetic structure that breaks Pfa
    control [Blau-Michaeli 2019; Theis-Wagner 2021; Zhang 2021] -> explains our 976 false alarms.
This is the citable version of the negative result. Two escape routes: (A) the residual is NOT
white (exploitable structure survives), (B) reframe deliverable to detection-product transport.

**Whiteness diagnostic (`scripts/whiteness_diagnostic.py`, our own scenes) settles route A:**
| | Gotcha | S1 SM |
|---|---|---|
| linear coding gain (real part) | 0.005 bit | 0.161 bit |
| FDBAQ-residual coding gain | 0.002 bit | 0.158 bit |
| FDBAQ-residual kurtosis | +0.38 | +0.34 (near-Gaussian) |
| power lag-1 (range/azimuth) | 0.55/0.66 | 0.32/**0.94** |
The strong texture (K nu=0.22) and magnitude correlation are NONLINEAR (phase is random -> real/imag
nearly white -> linear/transform codec gain ~0, exactly why every reconstruction codec failed), and
FDBAQ's block-normalization already captures most of it (kurtosis +125 -> +0.38). Residual headroom
over FDBAQ is <=0.16 bit/sample, concentrated in S1 azimuth oversampling. Corroborated by the [redacted: programmatic note]
OWN cited reference: Asiyabi 2025 states raw SAR is "very low correlation," exploitable only in the
lowpass/oversampled band. **Conclusion: reconstruction-codec venture-scale win is ruled out (theorem
+ measurement); Opening A is real but sub-bit/incremental (AI-BAQ-scale); Opening B (detection
transport) is the only order-of-magnitude win, but it is a different product.**

## IDEA-3 (COMPLEX ENCODER) RESULT + CAMPAIGN CLOSE (2026-08-14)

**Complex-valued analysis transform, 3-lambda sweep (GPU):** fixed-threshold Pd=0.000 all three;
calibration-free ROC best-Pd-at-budget = **0.000** all three (rate 0.011-0.018 bps, collapsed).
The phase-preserving encoder did NOT rescue detection — it collapsed harder than the real encoder.
**Representation was not the bottleneck** (theory predicted this: the limit is source information,
not the I/Q split). Every empirical lever is now exhausted: reconstruction (v0-v4), statistic (v5),
wide capacity, constrained dual-ascent, complex encoder — all fail the two-sided criterion.

**Literature deep-dive (classical + learned allocation) closes the external question:**
- Units: BAQ/FDBAQ "bits/sample" = PER COMPONENT; complex = 2x. S1 FDBAQ ~2.5-3 bps/component =
  ~5-6 bits/complex (matches our R_c axis).
- The ENTIRE adaptive-allocation literature (FDBAQ [Attema10], ECBAQ [Algra02], PO-BAQ [Martone22],
  AI-BAQ/ARTISTE [Gollin25], BAVQ [Moreira]) optimizes SQNR / coherence / InSAR phase — **NEVER
  detection (Pd/Pfa/CFAR).** Our two-sided detection evaluation is uncontested whitespace.
- Ceiling over FDBAQ: ECBAQ +1.55 dB (~0.3 bit) over BAQ-3; FDBAQ vs ECBAQ +0.1-0.5 dB (<0.1 bit);
  entropy coding captures essentially the whole scalar-quant gain, VQ/trellis add ~nothing. **AI-BAQ
  has never published a rate number vs FDBAQ**; its value is guaranteed focused-domain SQNR +
  InSAR-awareness, not new bits. Realistic headroom over FDBAQ on conventional stripmap = sub-bit.
- Only untapped structure = oversampling correlation; DLR: conventional SAR has "very little." Big
  (20-60%) reductions need deliberately-oversampled modes (MC/staggered/FScan) AND must beat known
  DFT/predictive transforms, not FDBAQ.

**CAMPAIGN VERDICT (stopping rule fired).** Venture-scale learned-codec win over classical on the
two-sided criterion does not exist, proven four independent ways (empirics, theory, our whiteness
data, the full literature). The genuine, defensible contributions for the follow-on feasibility study:
(1) the two-sided detection-preserving evaluation the entire field omits; (2) a theorem-backed floor;
(3) empirical confirmation across every codec lever. Remaining honest business openings are OUTSIDE
the reconstruct-then-detect codec: detection-product transport (different product) or the evaluation
methodology itself. Next action is WRITING, not more experiments.

## RATE-DISTORTION (primary fidelity metric) — learned codec loses on fidelity too, on our data
## (2026-08-14)

Ran the comparison the detection study never ran: plain MSE reconstruction codec (high-lambda sweep
100k/1M/10M to reach a fair rate) vs classical, SQNR measured in the focused domain on the Gotcha
eval crop. Result:
| rate (bps) | codec | SQNR (dB) | Pd | false |
|---|---|---|---|---|
| 0.95 | learned lam1M | 0.14 | 0.477 | 1569 |
| 0.99 | jpeg2000 | 4.31 | 0.442 | 158 |
| 1.00 | learned lam100k | 0.09 | 0.575 | 5081 |
| 4.00 | jpeg2000 | 14.32 | 0.799 | 47 |
| 8.00 | jpeg2000 | 26.46 | 0.905 | 30 |

The learned codec loses on rate-distortion (0.1 dB vs 4.3 dB SQNR at ~1 bps) and PLATEAUS at ~1 bps
regardless of lambda (100k->10M). Mechanism: training distortion looked good (~0.13, ~9 dB) because
it averages over clutter-dominated random patches; the full-crop SQNR is dominated by the sparse
bright targets (0.05% of cells, most of the energy), which the low-rate codec reconstructs clutter
instead of. Classical transform coders allocate bits to the high-energy target coefficients; the
small learned codec does not. Same sparse-target structure that defeats detection also defeats
fidelity. Asiyabi's ~40% fidelity win is a DIFFERENT regime (raw S1, vs BAQ, ~2-3 bps, large model);
not reproduced on near-white focused data vs strong classical with a CPU-budget model. The floor is
not specific to the two-sided detection criterion; it appears on the [redacted: programmatic note] primary metric too.

## S1 CROSS-SENSOR CONFIRMATION — the floor holds on a second, independent sensor (2026-08-14)

Per-region stat codec trained + evaluated on Sentinel-1 C-band spaceborne (held-out SM scene,
n_ref=23387 dense urban), independent of the Gotcha X-band airborne result:
| checkpoint | rate (bps) | Pd | bestPd@budget |
|---|---|---|---|
| s1_stat_pr lam1000 | 0.006 | 0.000 | 0.000 |
Collapsed to transmit-nothing, identical to Gotcha. The two-sided-criterion floor is now confirmed
on TWO independent sensors (X-band airborne + C-band spaceborne), consistent with the theorem
(Ahlswede-Csiszar / Gish-Pierce / Blau-Michaeli) and the whiteness measurement. RADAR CHAPTER
CLOSED: no learned configuration beats classical on the two-sided criterion, across domains,
architectures, capacity, constraint formulation, complex representation, the primary rate-distortion
metric, and two sensors. Redirect: the task-oriented-TRANSPORT thesis (compress the task
representation, not the signal) is where the win is — validated 170x on EO video (DV019 wedge),
because video's semantic content is compact AND recoverable, which SAR's sparse targets never were.


## NOTE (2026-10-22) — notebook sections withheld from this mirror

Private-notebook sections dated 2026-08-14 and 2026-08-15 are not included in this mirror. They concern GPU fidelity gates on the Gotcha image (SQNR only, plus two learned squared-error points scored for detection, summarized in the paper's Section V-H) and a separate line of work outside the paper's scope. No number in the paper is computed from them.

## UMBRA VANCOUVER EVALUATION (record added 2026-10-22; runs dated 2026-08-06)

Seventeen rows in `experiments/runs.jsonl` with `domain = umbra`, `scene = umbra_vancouver_prt`,
timestamps 2026-08-06T16:54–16:57, `n_ref_detections = 41,425`, produced by `scripts/eval_umbra.py` on a
4096x4096 centre crop of the public Umbra Port of Vancouver SICD product (Umbra-07, 2025-12-10, HH, 1 m
spotlight; CC BY 4.0), with the same plane mapping and CA-CFAR configuration as the Sentinel-1 study and a
128-cell interior trim at scoring. No focusing step (SICD is an image). Status: EXPLORATORY, run after the
2026-08-06 stopping rule; no endpoint beyond the existing two-sided criterion was declared for it; nothing
adjusted after seeing it. Not written up at the time (reports/umbra_report.md v0.1 only); it entered the
manuscript at arXiv v2 (2026-10-22) after an independent review found it unreported. Results: HEVC QP12
sustains at 3.381 bps (Pd 0.947, 2,572 spurious; budget 4,142.5); JPEG2000 r4/r8 sustain at 8.0/4.0;
JPEG2000 r16/r32/r64 pass the retention floor (0.951/0.939/0.906) with 40,711/56,993/42,584 spurious =
9.8x/13.8x/10.3x budget (retention-only certified, two-sided rejected); HEVC QP20 at 1.34 bps: 0.896 with
22,739 spurious (5.5x); BAQ fails at every bit depth (best 0.795 at 12.1 bps). Vendor onboard handling of
the product before delivery is not disclosed; treated as an image-domain extension, not a raw-data result.
