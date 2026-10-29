# Claims ledger — radar-codec manuscript (TGRS-2026-08067 -> JSTARS revision)

**READ FIRST (2026-10-29):** the manuscript of record is v5c (corrected scorer, peak-v2). Rows 1-13 below and the legacy-scorer post hoc lines were computed under the pixel-count scorer with the legacy budget 0.1 x 23,387 = 2,338.7; they are SUPERSEDED by the v4 and v5 blocks at the end of this file (budget 0.1 x 13,964 = 1,396.4) and are kept only as the record of what the submitted version claimed.

One line per quantitative claim. Status: OK / FIX / POST-HOC / CORRECTED / SUPERSEDED.

| # | Claim (location) | Run id / config hash | Arithmetic | Status |
|---|---|---|---|---|
| 1 | tfocus-full JPEG2000 @ 4.00 bps: retention 0.908, spurious 4,482 (Table II / Sec V-C) | ef3f32c0b159 | 4,482/2,338.7 = 1.9x budget; certified by Pd-alone | SUPERSEDED (legacy scorer): OK (report both runs) |
| 2 | tfocus-full JPEG2000 @ 4.00 bps: retention 0.912, spurious 5,800 (Table II / Sec V-C) | ef3f32c0b159 | 5,800/2,338.7 = 2.5x budget; certified by Pd-alone | SUPERSEDED (legacy scorer): OK (report both runs) |
| 3 | tfocus-full JPEG2000 @ 2.00 bps: retention 0.901, spurious 16,014 (Table II / Sec V-C) | ef3f32c0b159 | 16,014/2,338.7 = 6.8x budget; certified by Pd-alone | SUPERSEDED (legacy scorer): OK (report both runs) |
| 4 | tfocus-full JPEG2000 @ 2.00 bps: retention 0.888, spurious 17,950 (Table II / Sec V-C) | ef3f32c0b159 | 17,950/2,338.7 = 7.7x budget; NOT certified (Pd<0.9) | SUPERSEDED (legacy scorer): OK (report both runs) |
| 5 | tfocus-full JPEG2000 @ 1.03 bps: retention 0.716, spurious 8,681 (Table II / Sec V-C) | ef3f32c0b159 | 8,681/2,338.7 = 3.7x budget; NOT certified (Pd<0.9) | SUPERSEDED (legacy scorer): OK (report both runs) |
| 6 | tfocus-full JPEG2000 @ 1.00 bps: retention 0.880, spurious 46,214 (Table II / Sec V-C) | ef3f32c0b159 | 46,214/2,338.7 = 19.8x budget; NOT certified (Pd<0.9) | SUPERSEDED (legacy scorer): OK (report both runs) |
| 7 | tfocus-full JPEG2000 @ 1.00 bps: retention 0.861, spurious 37,711 (Table II / Sec V-C) | ef3f32c0b159 | 37,711/2,338.7 = 16.1x budget; NOT certified (Pd<0.9) | SUPERSEDED (legacy scorer): OK (report both runs) |
| 8 | tfocus-full JPEG2000 @ 0.50 bps: retention 0.858, spurious 123,300 (Table II / Sec V-C) | ef3f32c0b159 | 123,300/2,338.7 = 52.7x budget; NOT certified (Pd<0.9) | SUPERSEDED (legacy scorer): OK (report both runs) |
| 9 | tfocus-full JPEG2000 @ 0.50 bps: retention 0.883, spurious 138,131 (Table II / Sec V-C) | ef3f32c0b159 | 138,131/2,338.7 = 59.1x budget; NOT certified (Pd<0.9) | SUPERSEDED (legacy scorer): OK (report both runs) |
| 10 | 'Pd-only would certify a codec producing ~53x the budget' (abstract ~l.57; III-A ~l.315; V-C ~l.603) | rows above | the 53x row (0.5 bps) has retention 0.858 < 0.9 -> Pd-only REJECTS it; Pd-only certifies 4 bps (2.5x / 1.9x) and one 2 bps run (6.8x) | SUPERSEDED (legacy scorer): FIX: restate as 2.5x-7x; keep 53x as magnitude at the floor |
| 11 | 'Pd holds 0.86-0.91 across tested rates' (V-C ~l.598) | rows above | min 0.858, max 0.912 across 4/2/1/0.5 bps | SUPERSEDED (legacy scorer): OK |
| 12 | Minimum acceptable rate 4.86 bps (V-B) and 7.99 bps (V-H) | (to be linked) | reviewer asks SNR sensitivity | SUPERSEDED (legacy scorer): POST-HOC: SNR sweep |
| 13 | Wavelet ringing causes the spurious detections (V-C) | (to be linked) | currently illustrative + counts | SUPERSEDED (legacy scorer): POST-HOC: ablation |

Add lines for every remaining number in the manuscript before the JSTARS resubmission.

## Verified-OK claims from the 2026-10-22 hostile review of arXiv:2608.17269 (Part B, verbatim)

| Claim (location) | Row(s) (index, config_hash, vintage) | Arithmetic / check |
|---|---|---|
| 23,387 reference detections (l.426, 441, 600, 621, 632) | rows 47-125 n_ref_detections | constant 23,387 in every s1_focused row |
| 369 reference detections, Gotcha (l.426, 809, 893) | rows 143-191 | constant 369 |
| 3-bit BAQ sustains at 6.12 bps, Pd 0.905, 1,619 spurious (l.45, 505) | row 94 (b3bc5320f7b0, v2; identical rows 48, 68) | 6.125 bps; 0.9052 >= 0.9; 1,619 <= 2,338.7 |
| BAQ monotonic in bit depth, Pd and rate (l.521-522) | rows 93-96 | 0.851 < 0.905 < 0.963 < 0.987; 4.1 < 6.1 < 8.1 < 12.1 |
| max abs dPd 0.004 under lattice adaptation (l.519) | FINDINGS l.563-568 (no log rows) | 0.909-0.905 = 0.004 (3-bit); others <= 0.002 |
| 48 distinct I values / 1,048,576; 32 in 64x64; 32 -> 4,096; 153,443 / 153,600 (l.449, 514-519) | FINDINGS l.553-561 only | not in log; block sizes differ (4,096 vs 153,600 samples) |
| R_c = 4.86 bps, raw HEVC QP36, Pd 0.908, 1,742 spurious, ~13:1 (l.47-49, 119, 536-538) | row 104 (b3bc5320f7b0, v2) | 4.8609 bps; 0.9076; 1,742 <= 2,338.7; 64/4.86 = 13.2 |
| Next HEVC point: 3.33 bps, Pd 0.836, spurious over budget (l.539-541) | row 108 (8891b13005ac, v2) | 3.3346; 0.8364; 2,558 > 2,338.7 |
| GO threshold R_c/2 = 2.43 (l.551) | from row 104 | 4.8609 / 2 = 2.430 |
| Full-focus J2K Pd 0.912 / 0.888 / 0.861 vs raw J2K 0.845 / 0.691 / 0.574 at 4 / 2 / 1 bps (l.588-590) | rows 110-112 vs 98-100 (v2) | 0.9121 / 0.8885 / 0.8607 vs 0.8446 / 0.6913 / 0.5737 |
| Pd 0.888 vs 0.691 at 2 bps (abstract l.53) | rows 111, 99 | as above |
| Spurious 5,800 / 18,000 / 38,000 / 123,000 at 4 / 2 / 1 / 0.5 bps (l.599-600) | rows 110-113 | 5,800 / 17,950 / 37,711 / 123,300 |
| 0.5 bps row: Pd 0.858, ~53x budget (l.602-604, magnitude only) | row 113 | 123,300 / 2,338.7 = 52.7 |
| Fig. 5: ratio 32, rate 1.000, 37,711 phantoms (l.630-632) | row 112 | 0.9999 bps; 37,711 |
| Full vs dechirp Pd 0.888 vs 0.729 at 2 bps (l.652) | rows 111, 118 | 0.8885 vs 0.7290 |
| Neither tfocus arm sustains at any rate (l.655-656) | rows 110-123 (v2), 79-92 (v1) | every row fails Pd or spurious |
| Learned lam50 degenerate near-zero rate (l.740) | row 124 (ab171babae62) | 0.0125 bps, Pd 0.0016, 3,214 |
| Learned lam300 fails gate vs raw J2K at matched rate; low Pd + large spurious (l.743-749) | row 125 vs row 100 | 0.893 bps: 0.397 / 25,886 vs 1.0 bps: 0.574 / 5,566 |
| lam300 loss still descending (l.745) | FINDINGS l.497 (-1.09%); not in log row | field loss_final_decile_slope_pct absent for rows 124-125 |
| ATR: J2K 3.9 bps 85.3%; HEVC 3.5 bps 81%; HEVC 1.4 bps 47.7%; J2K 1.0 bps 55.3%; BAQ 4.1 bps 59.0%; 27-pt drop (l.667-673) | rows 30, 34, 36, 32, 25, 24 (b3bc5320f7b0, weak, n=300) | 0.8533; 0.81; 0.4767; 0.5533; 0.59; 0.86-0.59 = 0.27 |
| Classifier check: HEVC 1.38 bps 47.7 -> 48.0; J2K 0.98 bps 55.3 -> 57.7 (l.374-375) | rows 36 -> 53; 32 -> 45 | 0.4767 -> 0.48; 0.5533 -> 0.5767 |
| Gotcha R_c = 7.99 bps, tfocus-J2K ratio 4, Pd 0.943, 26 spurious, budget 36.9, ~8:1 (l.812-814) | row 167 (b3bc5320f7b0) | 7.9912; 0.9431; 26 <= 36.9; 64/7.99 = 8.0 |
| Raw J2K ratio 4: 8.00 bps, Pd 0.905, 30 spurious (l.814-815) | rows 147, 159 | 7.9961; 0.9051; 30 |
| Gotcha ~1 bps: tfocus-J2K Pd 0.805 vs raw J2K 0.442 (l.820-821) | rows 170, 150 | 0.8049; 0.4417 |
| Raw J2K spurious 95-158 at low rates (l.825) | rows 149, 150 | 95, 158 |
| tfocus-HEVC 594-998 (l.825) | rows 171-173 | 594, 607, 998 (844 at 0.17 bps) |
| Gotcha learned: Pd 0.003 at 0.02-0.03 bps, both lambdas, converged (l.859-861) | rows 175, 176 | 0.00271 at 0.0231 / 0.0293 bps; slope -0.0% |
| 13,920 patches, 80 windows, 154,180-pulse file (l.850-852) | FINDINGS l.894-896, 781 | not in log |
| Gotcha DFT round trip 4.4e-7 (l.805) | FINDINGS l.849 | not in log |
| Single-channel CD: 29.6 vs 29.3 dB; coherence 0.204 vs 0.206 (l.975-978) | FINDINGS l.800-809 | not in log |
| 31 mapping-v2 classical points (FINDINGS) | rows 93-123 | 31 rows |
| Seed 1337 (Reproducibility) | all 203 rows | seed field = 1337 throughout |

---



## v2 corrections applied 2026-10-22 (scripts/patch_preprint_v2.py, 40 edits)
See the Version note in latex/preprint.tex. BLOCKERS A1-A3 fixed; MAJORS A4-A14 addressed as text/scoping changes; new experiments deferred to the JSTARS revision (v3).


## Legacy-scorer post hoc lines (E1/E5/E2/E3/E4/E6 entries below, written 2026-10-29 before the E0 scorer correction) — SUPERSEDED by the v4 block at the end of this file; retained for the record

| E1-s1_focused | Spearman rho(image SQNR, spurious) among Pd>=0.9 configs = -0.967, n = 9 (revision Sec V, fidelity) | study=jstars_E1E5 rows, domain=s1_focused | scipy.stats.spearmanr on fidelity_img.sqnr_db vs cfar_false | POST-HOC |
| E1-s1_focused-disc | 0 configuration pair(s) within 1 dB image SQNR with opposite two-sided verdicts (revision Sec V, fidelity) | same rows | pairwise |SQNR_a - SQNR_b| <= 1.0 and verdict_a != verdict_b | POST-HOC |
| E5-s1_focused-pfa0.0001_tol1 | R_c = 7.859 bps, 6 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol1] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-s1_focused-pfa0.0001_tol2 | R_c = 4.861 bps, 7 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol2] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-s1_focused-pfa0.0001_tol3 | R_c = 4.861 bps, 8 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-s1_focused-pfa0.0001_tol5 | R_c = 4.861 bps, 8 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol5] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-s1_focused-pfa0.001_tol3 | R_c = 7.859 bps, 6 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.001_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-s1_focused-pfa1e-05_tol3 | R_c = 4.000 bps, 9 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa1e-05_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E1-gotcha_gmti | Spearman rho(image SQNR, spurious) among Pd>=0.9 configs = -0.800, n = 4 (revision Sec V, fidelity) | study=jstars_E1E5 rows, domain=gotcha_gmti | scipy.stats.spearmanr on fidelity_img.sqnr_db vs cfar_false | POST-HOC |
| E1-gotcha_gmti-disc | 1 configuration pair(s) within 1 dB image SQNR with opposite two-sided verdicts (revision Sec V, fidelity) | same rows | pairwise |SQNR_a - SQNR_b| <= 1.0 and verdict_a != verdict_b | POST-HOC |
| E5-gotcha_gmti-pfa0.0001_tol1 | R_c = 7.991 bps, 4 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol1] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-gotcha_gmti-pfa0.0001_tol2 | R_c = 7.991 bps, 4 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol2] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-gotcha_gmti-pfa0.0001_tol3 | R_c = 7.991 bps, 4 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-gotcha_gmti-pfa0.0001_tol5 | R_c = 7.353 bps, 5 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol5] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-gotcha_gmti-pfa0.001_tol3 | R_c = nan bps, 0 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.001_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-gotcha_gmti-pfa1e-05_tol3 | R_c = 3.999 bps, 8 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa1e-05_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E1-umbra | Spearman rho(image SQNR, spurious) among Pd>=0.9 configs = -0.943, n = 6 (revision Sec V, fidelity) | study=jstars_E1E5 rows, domain=umbra | scipy.stats.spearmanr on fidelity_img.sqnr_db vs cfar_false | POST-HOC |
| E1-umbra-disc | 5 configuration pair(s) within 1 dB image SQNR with opposite two-sided verdicts (revision Sec V, fidelity) | same rows | pairwise |SQNR_a - SQNR_b| <= 1.0 and verdict_a != verdict_b | POST-HOC |
| E5-umbra-pfa0.0001_tol1 | R_c = 3.381 bps, 2 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol1] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-umbra-pfa0.0001_tol2 | R_c = 3.381 bps, 3 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol2] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-umbra-pfa0.0001_tol3 | R_c = 3.381 bps, 3 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-umbra-pfa0.0001_tol5 | R_c = 3.381 bps, 3 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.0001_tol5] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-umbra-pfa0.001_tol3 | R_c = 8.000 bps, 1 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa0.001_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |
| E5-umbra-pfa1e-05_tol3 | R_c = 3.381 bps, 3 sustaining (revision Sec V, sensitivity table) | sensitivity[pfa1e-05_tol3] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |

| E2-s1 | R_c vs added noise: native 4.861 (HEVC QP36); -9/-6/-3/0 dB: 6.125 (3-bit BAQ) at every level; HEVC QP36 retention 0.893/0.881/0.865/0.861 (revision Sec V, SNR table) | study=jstars_E2 rows, domain=s1_focused | min rate over sustaining rows per added_nsr_db | POST-HOC |
| E2-s1-nref | n_ref 23,387 -> 20,280 / 18,140 / 14,912 / 11,447 at -9/-6/-3/0 dB added | jstars_E2 uncompressed rows | logged n_ref_detections | POST-HOC |
| E2-gotcha | R_c 7.991 native -> 7.997 / 7.996 / 7.996 / 7.998 (JPEG2000 r4) at every level; n_ref 369 -> 303/264/230/185 | jstars_E2 rows, domain=gotcha_gmti | same | POST-HOC |
| E3-enrich-4bps | focused JPEG2000 9/7 r8 (4.000 bps): 5,800 phantoms, 0.83% within 8 cells of a top-decile scatterer vs areal 0.34% = enrichment 2.43; 5/3: 2.34; HEVC QP28 (3.738): 4.14; focused BAQ 2-bit: 0.96 with Pd 0.021 (revision Sec V-C) | jstars_E3 rows, ringing.* | frac_phantom_within_R / areal_baseline_within_R | POST-HOC |
| E3-enrich-2bps | focused JPEG2000 9/7 r16 (2.000 bps): 17,950 phantoms, enrichment 0.85; 5/3 r16: 22,743, 0.66; HEVC QP32 (2.224): 5,323, 2.59 | same | same | POST-HOC |
| E3-median | median phantom distance to nearest top-decile scatterer ~200 cells (196-233) for every transform arm | same | ringing.median_phantom_dist | POST-HOC |
| E6-psf | focuser PSF: IRW 1.0 cell (range and azimuth), PSLR -14.85 dB range / -13.26 dB azimuth (revision Sec IV) | reports/e6_impulse_response.json | irw_pslr, oversample 16 | POST-HOC |
| E6-crop | Fig. 5 crop centre interior (2160, 3156) = full (2672, 3668), half-window 160 | reports/ringing_crop.json | make_ringing_figure selection rule | POST-HOC |
| E4-durango | Durango (GPS stationary over CPI) retained as a detection in the same cell at 19/20 Gotcha operating points down to 0.638 bps; lost only at focused HEVC QP36 (0.167 bps); peak-power retention within 1 dB at all raw-domain points >= 4.5 bps; 2-bit BAQ (4.12 bps) -1.54 dB (revision Sec V-H / Sec VI); CORRECTED 2026-10-29 from '>= 4 bps' | jstars_E4 rows, domain=gotcha_gmti, durango.* | detected_within_tol, peak_power_retention_db | POST-HOC |
| E4-s1-proxy | top-decile-power subset (n=2,339) retention >= 0.994 for every raw-domain point >= 1.95 bps; focused full-mode JPEG2000 r8 0.941 (full-set 0.912); raw JPEG2000 r16 0.930 (revision Sec VI) | jstars_E4 rows, domain=s1_focused, strong_subset.mode=topdecile | strong_subset.pd_subset | POST-HOC |
| E3-hevc-sustains | focused-domain HEVC QP16/20/24 (8.13/6.64/5.22 bps) sustain the two-sided criterion (Pd 0.968/0.955/0.925; 834/1,411/2,042 spurious vs 2,338.7); outside the registered QP 36/40/44 sweep (revision abstract, Sec I, V-D, VI, VIII) | jstars_E3 rows arm=hevc | pd>=0.9 and n_phantom<=0.1*n_ref | POST-HOC |
| E3-poisson | 48 phantoms within 8 cells of a top-decile scatterer vs 19.7 expected (0.0034 x 5,800); Poisson p ~ 5e-8 (revision Sec VI) | jstars_E3 row jpeg2000_97 r8 | scipy.stats.poisson.sf(47, 19.7) | POST-HOC |

## v4 headline claims (corrected scorer, 2026-10-29) — every line regenerates from reports/v4_headline_numbers.json via scripts/make_v4_tables.py
| v4-nref | reference peaks: Illinois 13,964 / Gotcha 259 / Umbra 22,860 (abstract, Sec IV, Table I) | rescore_E0 rows, n_ref_detections | peak-v2 scorer | CORRECTED |
| v4-Rc | frontiers: Illinois 7.62 (HEVC QP28), Gotcha 10.93 (HEVC QP12; bracket 8.0-10.9), Umbra 3.87 (HEVC QP12) (abstract, V-B, V-H, V-I, Table I) | rescore_E0 rows | min rate over sustaining rows | CORRECTED |
| v4-bracket | 4-bit BAQ sustains at 8.12 (0.937, 799), 3-bit fails at 6.12 (0.842, 1,635) (abstract, V-A) | rescore_E0 baq rows | two-sided criterion | CORRECTED |
| v4-lossless | memoryless lossless rate 10.18 bps (80 levels/component) (abstract, V-A, Table II) | reports/e7_lossless.json | order-0 entropy I+Q | NEW |
| v4-certfail | retention-only certification failure: Umbra JPEG2000 r16 Pd 0.910, 34,916 spurious = 15.3x budget 2,286; Gotcha focused J2K r4 Pd 0.919, 26 vs 25.9 (marginal); none on Illinois (focused r8 Pd 0.858) (abstract, V-C, V-H, V-I) | rescore_E0 rows | criterion | CORRECTED |
| v4-sens | Illinois sustaining set identical at tol 1/2/3/5 and Pfa 1e-3/1e-4/1e-5 (Sec VI, Table VII) | rescore_E0 sensitivity | min rate per setting | CORRECTED |
| v4-snr | Illinois R_c 7.62 -> 7.51/7.46/7.42/7.38, same set; Gotcha 10.93 -> 8.00/8.00/7.94/10.36 (Sec VI, Table VIII) | rescore_E2 rows | per added_nsr_db | CORRECTED |
| v4-ringing | wavelet r8 near strong/weak/random 143/72/62 (1.99x, 2.31x; rule not met, excess withdrawn); r16 171/255/223; HEVC QP16 117/9/10 (Sec V-C, VI, Table IX) | rescore_E3 ringing.e3b | absolute counts within 8 cells | CORRECTED |
| v4-hevc-focused | focused HEVC sustains at QP16 (8.05) and QP20 (6.56), fails at QP24 (5.13, 0.884) (abstract, Sec I, VI) | rescore_E3 hevc rows | criterion | CORRECTED |
| v4-durango | retained 19/20 points down to 0.85 bps; lost at focused HEVC QP36 (0.24) (V-H) | rescore_E4 gotcha | durango.detected_within_tol | CORRECTED |
| v4-proxy | top-decile subset (1,396): raw BAQ/HEVC >= 0.985 down to 2.1 bps; raw J2K r16 0.797; focused r8 0.956 vs 0.858 (Sec VI) | rescore_E4 s1 | strong_subset.pd_subset | CORRECTED |
| v4-clip | mapping round trips: S1 raw 0.9994/1; S1 transform 0.995/184 (0.68% energy); Gotcha image 0.985 (5.4% peaks clipped); Umbra 0.999 (14.4% energy, SQNR 9.0); clip-free J2K r8 0.864/4,944 vs 0.858/5,219 (Sec VI, VII) | ctrl_E8 rows | no-codec round trip | NEW |
| v4-lattice | max dPd 0.007; spurious +1.8/0.0/+4.4/+11.7%; monotone; 3-bit fails under both (Sec I, V-A) | rescore_lattice rows | adapted - plain | CORRECTED |
| v4-learned | best Illinois 0.251 @ 0.89 bps (was 0.397); best Gotcha 0.417 @ 1.08 (was 0.593) (Sec VI) | rescore_learned rows | max cfar_pd | CORRECTED |
| v4-fidelity | rho(SQNR, spurious) among passing: Illinois -0.94 (n=6), Gotcha -1.0 (n=3), Umbra -1.0 (n=4); discordant pairs 0/0/4 (Sec VI, Table VI) | rescore_E0 fidelity_img | spearmanr; pairs within 1 dB | CORRECTED |

## v5 claims (fourth adversarial round, 2026-10-29) — manuscript v5c
| v5-fdbaq-crop | delivered FDBAQ bitstream over the study crop 5.22 bps (5.19-5.26 across echoes); all 4096 echoes x 32 crop blocks at BRC 0 (abstract, Sec I, IV, V-A, Table I-II, Fig. 3, Limitations, version note) | reports/fdbaq_rate_crop.json (E7c, pre-declared) | block-level Huffman parse; sample-code bits + 11 side-info bits per block, apportioned by block fraction inside the crop, / 8,192; self-check parsed bytes == decoder bounds for every packet | NEW |
| v5-fdbaq-line | full-line average 5.28 bps (5.23-5.54); header PDL+1-62 is 1 byte above the decoder bounds per packet (+0.0004 bps) (Sec IV, V-A, version note) | reports/fdbaq_rate.json (E7b, NOT pre-declared; labelled) | 8 x user bytes / (2 x quads) | NEW (secondary) |
| v5-margins | lowest sustaining rate 5.92 is 0.70 above the crop rate; registered-grid 7.62 is 2.40 above (V-A, V-B) | v4-Rc + v5-fdbaq-crop | 5.92 - 5.22 = 0.70; 7.62 - 5.22 = 2.40 | NEW |
| v5-ecbaq | entropy-coded BAQ (order-0 index entropy + 8 bits/block/plane): Illinois 2/3/4/6-bit 4.09/5.34/5.92/8.15; Gotcha 3.99/5.82/7.72/11.97 (V-A, V-B, VI, Table II) | reports/e9_entropy_baq.json (E9, pre-declared; 16-bit side-info convention in the declaration, 8 used, disclosed) | bound, not coder output; scores are the fixed-rate rows' | NEW |
| v5-ecbaq-noise | Illinois 4-bit index entropy under the noisiest SNR-sweep level 7.69 bps; under lattice adaptation 5.93 (V-B, VI) | reports/e9b_entropy_offlattice.json (E9b, pre-declared) | same convention as E9 | NEW |
| v5-hevc-qp20 | focused HEVC QP20 sustains at 6.56 (0.914, 1,219) at the registered setting, tol 5, Pfa 1e-5; fails tol 1 (0.891), tol 2 (1,412 > 1,396.4), Pfa 1e-3 (0.898) (V-B, VI, version note) | study rescore_E0x rows (E0x, NOT pre-declared; labelled) | criterion per setting | NEW |
| v5-mapping-113 | no-codec transform-domain round trip: 184 phantoms, 113 near strong / 1 near weak / 2 near random anchors (n = 1,397 each) (V-C, VI, Limitations) | reports/e10 record (E10, pre-declared) | counts within 8 cells | NEW |
| v5-umbra-clipfree | clip-free Umbra frontier 8.00 (JPEG2000 r4, 0.976/479); r8 0.930/3,278 and r16 0.912/42,035 fail the budget; clip-free focused HEVC collapses (VI) | study ctrl_E10 rows | criterion, budget 2,286 | NEW |
| v5-umbra-r8 | Umbra JPEG2000 r8 0.927 / 3,815 (1.7x) passes the floor at tol 1/2/3/5; r16 0.910 / 34,916 (15x) passes at tol 3 and 5, fails the floor at tol 1 and 2 (V-I) | rescore_E0 umbra rows + sensitivity | criterion per tolerance | NEW |
| v5-spearman | rho(SQNR, spurious) among passing Illinois configurations = -0.943 (n = 6), exact two-sided permutation p = 0.017 (scipy t-approximation 0.005, not used); no ties (VI) | rescore_E0 fidelity_img | 6! permutations | CORRECTED (p) |
| v5-below-count | 24 Illinois classical configurations (raw and focused arms, latest row per config) sit below 5.22 bps and every one fails the floor (max retention 0.858); "below every tested codec" replaced by "below every sustaining configuration" (Table I, V-A, Limitations) | rescore_E0 s1 rows | count rows with rate < 5.22 | FIX |
