"""Readout of JSTARS E1 (fidelity vs task) and E5 (matching/CFAR sensitivity) rows against the
pre-declared endpoints (FINDINGS.md, 2026-10-29). Appends the results entry to FINDINGS.md and
the claim lines to reports/claims_ledger.md when run with --write; otherwise prints only."""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(line) for line in open(ROOT / "experiments" / "runs.jsonl", encoding="utf-8")]
STUDY = next((a.split("=",1)[1] for a in sys.argv if a.startswith("--study=")), "jstars_E1E5")
E = [r for r in rows if r.get("study") == STUDY]
assert len(E) == 68, len(E)
if STUDY == "jstars_E1E5":
    assert all(r["determinism"]["ok"] for r in E)


def verdict(pd, nf, nref):
    return pd >= 0.9 and nf <= 0.1 * nref


def cfg(r):
    return f"{r['codec']} {json.dumps(r['params'], sort_keys=True)}"


KEYS = ["pfa0.0001_tol1", "pfa0.0001_tol2", "pfa0.0001_tol3", "pfa0.0001_tol5", "pfa0.001_tol3", "pfa1e-05_tol3"]
out = []
ledger = []
for dom, label in (("s1_focused", "Sentinel-1 Illinois (focused scoring)"), ("gotcha_gmti", "Gotcha Durango"), ("umbra", "Umbra Vancouver")):
    S = [r for r in E if r["domain"] == dom]
    passing = [r for r in S if r["cfar_pd"] >= 0.9]
    rho, p = spearmanr([r["fidelity_img"]["sqnr_db"] for r in passing], [r["cfar_false"] for r in passing])
    disc = []
    for a, b in itertools.combinations(S, 2):
        d = abs(a["fidelity_img"]["sqnr_db"] - b["fidelity_img"]["sqnr_db"])
        if d <= 1.0 and verdict(a["cfar_pd"], a["cfar_false"], a["n_ref_detections"]) != verdict(b["cfar_pd"], b["cfar_false"], b["n_ref_detections"]):
            disc.append((d, a, b))
    disc.sort(key=lambda t: t[0])
    out.append(f"\n**{label}** ({len(S)} configurations). E1 primary: among the {len(passing)} configurations with Pd >= 0.9, "
               f"Spearman rho(image SQNR, spurious count) = {rho:.3f} (p = {p:.2g}). E1 secondary: {len(disc)} discordant pair(s) within 1 dB"
               + (":" if disc else "."))
    for d, a, b in disc:
        out.append(f"- {d:.2f} dB apart: {cfg(a)} (SQNR {a['fidelity_img']['sqnr_db']:.2f} dB, Pd {a['cfar_pd']:.3f}, {a['cfar_false']} spurious) vs "
                   f"{cfg(b)} (SQNR {b['fidelity_img']['sqnr_db']:.2f} dB, Pd {b['cfar_pd']:.3f}, {b['cfar_false']} spurious)")
    ledger.append(f"| E1-{dom} | Spearman rho(image SQNR, spurious) among Pd>=0.9 configs = {rho:.3f}, n = {len(passing)} (revision Sec V, fidelity) | study=jstars_E1E5 rows, domain={dom} | scipy.stats.spearmanr on fidelity_img.sqnr_db vs cfar_false | POST-HOC |")
    ledger.append(f"| E1-{dom}-disc | {len(disc)} configuration pair(s) within 1 dB image SQNR with opposite two-sided verdicts (revision Sec V, fidelity) | same rows | pairwise |SQNR_a - SQNR_b| <= 1.0 and verdict_a != verdict_b | POST-HOC |")
    out.append("E5 (R_c = lowest rate at which any configuration sustains the two-sided criterion; sustaining set size in brackets):")
    base_key = "pfa0.0001_tol3"
    base_set = {cfg(r) for r in S if verdict(**{k: r["sensitivity"][base_key][j] for k, j in (("pd", "pd"), ("nf", "n_false"), ("nref", "n_ref"))})}
    for k in KEYS:
        sus = [r for r in S if verdict(r["sensitivity"][k]["pd"], r["sensitivity"][k]["n_false"], r["sensitivity"][k]["n_ref"])]
        nref = S[0]["sensitivity"][k]["n_ref"]
        if sus:
            w = min(sus, key=lambda r: r["rate_bps"])
            delta = {cfg(r) for r in sus} ^ base_set
            out.append(f"- {k}: n_ref {nref}, R_c = {w['rate_bps']:.3f} bps ({cfg(w)}) [{len(sus)}]"
                       + (f"; set differs from the registered setting by: {', '.join(sorted(delta))}" if delta else "; same sustaining set as registered"))
        else:
            out.append(f"- {k}: n_ref {nref}, NO configuration sustains [0]")
        ledger.append(f"| E5-{dom}-{k} | R_c = {(min(r['rate_bps'] for r in sus) if sus else float('nan')):.3f} bps, {len(sus)} sustaining (revision Sec V, sensitivity table) | sensitivity[{k}] on study=jstars_E1E5 rows | min rate over rows with pd>=0.9 and n_false<=0.1*n_ref at that setting | POST-HOC |")

text = "\n".join(out)
print(text)
if "--write" in sys.argv:
    entry = f"""

## JSTARS E1 + E5 READOUT (2026-10-29; 68 rows `study = jstars_E1E5`, ts 06:46-07:11; commit of pre-declaration 8365f24)

Determinism: all 68 reruns reproduce the archived rate, Pd and spurious count within the declared tolerance
(in fact exactly). SQNR reconciliation: the notebook's first Gotcha set (line ~1912: 4.31 / 14.32 / 26.46 dB
at ~1 / 4 / 8 bps) is RAW-domain JPEG2000 (r32 / r8 / r4) and reproduces exactly; the second set (line ~1995:
8.76 / 12.17 / 16.78 dB at 1 / 2 / 4 bps) is FOCUSED-domain JPEG2000 (tfocus r32 / r16 / r8) and also
reproduces exactly. They were never in disagreement; they are different arms. Both stand.
{text}

Reading against the pre-declared rules.
- E1: the interpretation rule is MET (discordant pairs exist on Gotcha and Umbra), so the manuscript may
  state that image-domain fidelity does not determine the two-sided verdict, but the statement must be
  scoped: WITHIN the raw-domain classical family on one scene, SQNR orders spurious counts almost perfectly
  (S1 rho -0.97, Umbra -0.94); the discordance appears ACROSS codec families at equal SQNR (BAQ vs
  transform codecs on Umbra, 0.17 dB apart with Pd 0.795 vs 0.989; raw-domain BAQ vs focused-domain
  JPEG2000 on Gotcha, 0.33 dB apart with opposite verdicts). On S1 no discordant pair exists; the
  near-pairs there (BAQ 2-bit 10.47 dB vs focused JPEG2000 r8 10.39 dB) both fail, but for opposite
  reasons (retention vs spurious), which is the paper's existing point, not a new one.
- E5 matching tolerance: S1 R_c = 4.861 (HEVC QP36) unchanged for tol 2, 3, 5 (ROBUST by the rule; tol 1
  stress case moves it to 7.859). One sensitivity inside that verdict must be stated: at tol 2 the 3-bit
  BAQ point (Pd 0.905 at tol 3) falls below the retention floor and leaves the sustaining set, so the
  abstract's "3-bit BAQ sustains utility at 6.12 bps" holds at the registered tolerance of 3 cells and
  at 5, not at 2. The manuscript states the tolerance with that claim. Gotcha R_c = 7.991 unchanged for tol 1-3; tol 5 admits HEVC QP20 at 7.353, inside the
  paper's 7.4-8.0 bracket to two figures (ROBUST). Umbra 3.381 unchanged for all tol (ROBUST).
- E5 CFAR Pfa: this is where the sensitivity is real and must be reported as such. Pfa 1e-3 (stress)
  raises n_ref 3x and the spurious budget with it, yet R_c RISES on every scene (S1 7.859, Umbra 8.000,
  Gotcha: nothing sustains) because the retention floor is now applied to a reference set dominated by
  weak detections. Pfa 1e-5 lowers R_c on S1 to 4.000 (focused-domain JPEG2000 dechirp r8 now sustains)
  and on Gotcha to 3.999 (n_ref only 163, small-sample); Umbra unchanged. The rule (one grid point between
  1e-4 and 1e-5) is met on S1 and Umbra and NOT met on Gotcha (two grid points, on 163 reference
  detections). Manuscript: R_c is a property of the CFAR operating point as much as of the scene;
  Section V gets a sensitivity table and the Gotcha bracket is stated at Pfa 1e-4 only.
"""
    with open(ROOT / "reports" / "FINDINGS.md", "a", encoding="utf-8") as f:
        f.write(entry)
    with open(ROOT / "reports" / "claims_ledger.md", "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(ledger) + "\n")
    print("\nFINDINGS.md and claims_ledger.md appended")
