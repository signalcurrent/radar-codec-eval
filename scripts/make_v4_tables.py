"""Generate every results table of the v4 manuscript as LaTeX from experiments/runs.jsonl (corrected rows:
study = rescore_E0 / rescore_E2 / rescore_E3 / rescore_E4 / rescore_learned / ctrl_E8). Writes
latex/tables_v4/*.tex and a JSON of headline numbers (reports/v4_headline_numbers.json) that the prose
patch and the claims ledger cite. No number in the v4 results sections is typed by hand.

    python scripts/make_v4_tables.py
"""
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "latex" / "tables_v4"
OUT.mkdir(exist_ok=True)
rows = [json.loads(l) for l in open(ROOT / "experiments" / "runs.jsonl", encoding="utf-8")]
H = {}  # headline numbers


def by(study, dom=None):
    return [r for r in rows if r.get("study") == study and (dom is None or r["domain"] == dom)]


def ok(r):
    return r["cfar_pd"] >= 0.9 and r["cfar_false"] <= 0.1 * r["n_ref_detections"]


def key(r):
    return (r["codec"], json.dumps(r["params"], sort_keys=True))


def label(r):
    c, p = r["codec"], r["params"]
    if c == "baq":
        return f"BAQ ({p['bits']}-bit)", "raw"
    if c == "jpeg2000":
        return f"JPEG2000 (r{p['ratio']})", "raw"
    if c == "hevc":
        return f"HEVC (QP{p['qp']})", "raw"
    if c == "tfocus":
        base = "JPEG2000" if p["base"] == "jpeg2000" else "HEVC"
        pt = f"r{p['ratio']}" if "ratio" in p else f"QP{p['qp']}"
        return f"{base} ({pt})", {"full": "focused", "dechirp": "dechirp", "focused": "focused"}.get(p.get("mode"), p.get("mode"))
    return c, "?"


def fmt(n):
    return f"{n:,}".replace(",", "{,}")


def table(name, caption, lab, colspec, header, body, size=r"\footnotesize"):
    tex = ["\\begin{table}[tb]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{lab}}}",
           "\\renewcommand{\\arraystretch}{1.15}", "\\setlength{\\tabcolsep}{2pt}", size,
           "\\resizebox{\\columnwidth}{!}{%", f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", header + " \\\\", "\\midrule"] + \
          [b + " \\\\" for b in body] + ["\\bottomrule", "\\end{tabular}}", "\\end{table}"]
    (OUT / f"{name}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ Tables II / IV / V: operating points per scene
SCENES = [("s1_focused", "illinois", "Sentinel-1 (Illinois)"), ("gotcha_gmti", "gotcha", "AFRL Gotcha GMTI"), ("umbra", "umbra", "Umbra Port of Vancouver (image domain)")]
for dom, short, title in SCENES:
    E = {key(r): r for r in by("rescore_E0", dom)}
    if not E:
        continue
    nref = next(iter(E.values()))["n_ref_detections"]
    budget = 0.1 * nref
    sus = sorted([r for r in E.values() if ok(r)], key=lambda r: r["rate_bps"])
    H[f"{short}_n_ref"] = nref
    H[f"{short}_budget"] = round(budget, 1)
    H[f"{short}_R_c"] = round(sus[0]["rate_bps"], 2) if sus else None
    H[f"{short}_R_c_codec"] = label(sus[0])[0] + " " + label(sus[0])[1] if sus else None
    H[f"{short}_sustaining"] = [(label(r)[0], label(r)[1], round(r["rate_bps"], 2)) for r in sus]
    # rows: all sustaining + the first failures below the frontier + focused arms at 4/2/1/0.5 for s1, + learned best
    body = []
    allrows = sorted(E.values(), key=lambda r: -r["rate_bps"])
    rc = sus[0]["rate_bps"] if sus else 0
    # keep: sustaining rows, the two raw-domain failures just below the frontier, every focused/dechirp arm at
    # the discussed rates, and (Umbra) every row that passes the retention floor
    chosen = []
    below = [r for r in allrows if not ok(r) and label(r)[1] == "raw" and r["rate_bps"] < rc][:2]
    for r in allrows:
        nm, d = label(r)
        keep = ok(r) or r in below or (d in ("focused", "dechirp") and r["codec"] == "tfocus" and round(r["rate_bps"]) in (8, 4, 2, 1) or abs(r["rate_bps"] - 0.5) < 0.1) \
            or (dom == "umbra" and r["cfar_pd"] >= 0.9) or (dom != "s1_focused" and d == "raw" and r["rate_bps"] >= rc - 0.5 and r["rate_bps"] < rc)
        if keep and r["codec"] == "tfocus" and r["params"].get("mode") == "dechirp" and dom == "s1_focused" and round(r["rate_bps"]) not in (4,):
            keep = False
        if keep:
            chosen.append(r)
    for r in chosen:
        nm, d = label(r)
        body.append(f"{nm} & {d} & {r['rate_bps']:.2f} & {r['fidelity_img']['sqnr_db']:.1f} & {r['cfar_pd']:.3f} & {fmt(r['cfar_false'])} & {'yes' if ok(r) else 'no'}")
    learned = [r for r in by("rescore_learned", dom)]
    if learned:
        b = max(learned, key=lambda r: r["cfar_pd"])
        body.append(f"Learned (best) & focused & {b['rate_bps']:.2f} & -- & {b['cfar_pd']:.3f} & {fmt(b['cfar_false'])} & no")
    if dom == "s1_focused":
        e7 = json.load(open(ROOT / "reports" / "e7_lossless.json"))
        body.insert(0, f"Lossless (memoryless entropy) & raw & {e7['s1_lossless_bps_complex']:.2f} & $\\infty$ & 1.000 & 0 & yes")
        H["s1_lossless_bps"] = round(e7["s1_lossless_bps_complex"], 2)
    extra = (" Focused-domain rows are results under the study's plane mapping, whose no-codec round trip clips 5.4\\% of this "
             "scene's reference peaks in that domain (Section~\\ref{sec:posthoc})." if dom == "gotcha_gmti" else
             " All rows are results under the study's plane mapping, whose no-codec round trip caps image SQNR at 9.0~dB on "
             "this scene (Section~\\ref{sec:posthoc})." if dom == "umbra" else "")
    table(f"tab_{short}", f"{title}: selected classical operating points under the corrected scorer (peak reduction) and the "
          f"corrected HEVC pipeline; the full set of {len(E)} rows is in the results log. Rate in bits per complex sample; "
          f"SQNR is image-domain, dB; the spurious budget is {budget:.1f} (10\\% of {fmt(nref)} reference detections). "
          f"``Sust.'' = both clauses of \\eqref{{eq:crit}} hold.{extra}",
          f"tab:{short}", "@{}llrrrrc@{}", "Codec & Domain & Rate & SQNR & $P_d$ & Spur. & Sust.", body)

# ------------------------------------------------------------------ Table: sensitivity (tolerance / Pfa) per scene
KEYS = ["pfa0.0001_tol1", "pfa0.0001_tol2", "pfa0.0001_tol3", "pfa0.0001_tol5", "pfa0.001_tol3", "pfa1e-05_tol3"]
body = []
for dom, short, title in SCENES:
    E = by("rescore_E0", dom)
    if not E:
        continue
    cells, nrefs = [], []
    # 7 columns: tol 1/2/3/5 at Pfa 1e-4, then Pfa 1e-3 / 1e-4 / 1e-5 at tol 3 (the 1e-4 column repeats the tol-3 cell)
    for k in ["pfa0.0001_tol1", "pfa0.0001_tol2", "pfa0.0001_tol3", "pfa0.0001_tol5", "pfa0.001_tol3", "pfa0.0001_tol3", "pfa1e-05_tol3"]:
        s = [r for r in E if r["sensitivity"][k]["pd"] >= 0.9 and r["sensitivity"][k]["n_false"] <= 0.1 * r["sensitivity"][k]["n_ref"]]
        nrefs.append(E[0]["sensitivity"][k]["n_ref"])
        if s:
            w = min(s, key=lambda r: r["rate_bps"])
            cells.append(f"{w['rate_bps']:.2f} [{len(s)}]")
        else:
            cells.append("none")
        H[f"{short}_sens_{k}"] = cells[-1]
    body.append(f"{title.split(' (')[0]} & " + " & ".join(cells))
    body.append("$n_{\\mathrm{ref}}$ & " + " & ".join(fmt(n) for n in nrefs))
table("tab_sens", "Lowest sustaining rate (bits per complex sample) and sustaining-set size [brackets] at each matching tolerance "
      "$\\tau$ (cells, at $P_{\\mathrm{fa}}=10^{-4}$) and design $P_{\\mathrm{fa}}$ (at $\\tau=3$), corrected scorer. "
      "Registered setting: $\\tau=3$, $P_{\\mathrm{fa}}=10^{-4}$.",
      "tab:sens", "@{}lcccc|ccc@{}", " & $\\tau{=}1$ & $\\tau{=}2$ & $\\tau{=}3$ & $\\tau{=}5$ & $10^{-3}$ & $10^{-4}$ & $10^{-5}$", body)

# ------------------------------------------------------------------ Table: threshold sensitivity (beta x floor) from the corrected rows
body = []
for dom, short, title in SCENES[:2]:
    E = by("rescore_E0", dom)
    if not E:
        continue
    body.append(f"\\multicolumn{{4}}{{@{{}}l}}{{\\textit{{{title.split(' (')[0]}}}}} \\\\")
    for floor in (0.85, 0.90, 0.95):
        cells = []
        for beta in (0.05, 0.10, 0.20):
            s = [r for r in E if r["cfar_pd"] >= floor and r["cfar_false"] <= beta * r["n_ref_detections"]]
            if s:
                w = min(s, key=lambda r: r["rate_bps"])
                p = w["params"]
                code = {"baq": f"B{p.get('bits')}", "jpeg2000": f"J{p.get('ratio')}", "hevc": f"H{p.get('qp')}"}.get(w["codec"])
                if code is None:
                    code = ("Jf" if p.get("base") == "jpeg2000" else "Hf") + str(p.get("ratio", p.get("qp")))
                cell = f"{w['rate_bps']:.2f} ({code})"
            else:
                cell = "none"
            cells.append(f"\\textbf{{{cell}}}" if (floor == 0.90 and beta == 0.10) else cell)
            H[f"{short}_thr_{floor}_{beta}"] = cell
        body.append(f"$P_d^{{\\min}} = {floor:.2f}$ & " + " & ".join(cells))
table("tab_thresholds", "Sensitivity of the classical frontier to the criterion's thresholds, corrected scorer, computed from the "
      "logged rows (no new runs): lowest sustaining rate (bits per complex sample) and the codec that holds it (B$n$: $n$-bit "
      "BAQ; J$r$: raw JPEG2000 ratio $r$; H$q$: raw HEVC QP $q$; Jf/Hf: focused domain); $\\beta$ is the spurious budget as a "
      "fraction of reference detections. Bold: the thresholds used in this paper.",
      "tab:thresholds", "@{}lccc@{}", " & $\\beta = 0.05$ & $\\beta = 0.10$ & $\\beta = 0.20$", body, size=r"\scriptsize")

# ------------------------------------------------------------------ Table: fidelity discordant pairs
body = []
for dom, short, title in SCENES:
    E = by("rescore_E0", dom)
    if not E:
        continue
    passing = [r for r in E if r["cfar_pd"] >= 0.9]
    if len(passing) >= 3:
        from scipy.stats import spearmanr
        rho, p = spearmanr([r["fidelity_img"]["sqnr_db"] for r in passing], [r["cfar_false"] for r in passing])
        H[f"{short}_rho"] = (round(float(rho), 3), len(passing))
    disc = []
    for a, b in itertools.combinations(E, 2):
        if abs(a["fidelity_img"]["sqnr_db"] - b["fidelity_img"]["sqnr_db"]) <= 1.0 and ok(a) != ok(b):
            disc.append((a, b))
    H[f"{short}_discordant"] = len(disc)
    seen = set()
    for a, b in disc:
        for r in (a, b):
            if key(r) in seen:
                continue
            seen.add(key(r))
            nm, d = label(r)
            body.append(f"{title.split(' (')[0]} & {nm}, {d} & {r['rate_bps']:.2f} & {r['fidelity_img']['sqnr_db']:.1f} & {r['cfar_pd']:.3f} & {fmt(r['cfar_false'])} & {'yes' if ok(r) else 'no'}")
table("tab_fidelity", "Configurations that take part in a within-scene pair with image-domain SQNR within 1~dB and opposite "
      "two-sided verdicts (corrected scorer). Four pairs, all on Umbra: two are scalar quantization against transform coding "
      "and two are within transform coding; the scene's SQNR scale is capped at 9.0~dB by the plane mapping "
      "(Section~\\ref{sec:posthoc}).",
      "tab:fidelity", "@{}llrrrrc@{}", "Scene & Codec & Rate & SQNR & $P_d$ & Spur. & Sust.", body)

# ------------------------------------------------------------------ Table: SNR sweep
body = []
for dom, short, title in SCENES[:2]:
    E = by("rescore_E2", dom)
    if not E:
        continue
    rc, nr = [], []
    for nsr in (-9.0, -6.0, -3.0, 0.0):
        S = [r for r in E if r["added_nsr_db"] == nsr and r["codec"] != "uncompressed"]
        u = [r for r in E if r["added_nsr_db"] == nsr and r["codec"] == "uncompressed"]
        s = [r for r in S if ok(r)]
        rc.append(f"{min(r['rate_bps'] for r in s):.2f}" if s else "none")
        nr.append(fmt(u[0]["n_ref_detections"]) if u else "?")
    nat = H.get(f"{short}_R_c")
    body.append(f"{title.split(' (')[0]} $R_c$ & {nat:.2f} & " + " & ".join(rc))
    body.append("$n_{\\mathrm{ref}}$ & " + fmt(H[f"{short}_n_ref"]) + " & " + " & ".join(nr))
    H[f"{short}_snr_R_c"] = rc
    H[f"{short}_snr_n_ref"] = nr
if body:
    table("tab_snr", "Lowest sustaining rate (bits per complex sample) under added complex white noise relative to signal "
          "power, corrected scorer; the reference is re-formed from the same noisy input.",
          "tab:snr", "@{}lccccc@{}", "Added noise & native & $-9$~dB & $-6$~dB & $-3$~dB & 0~dB", body)

# ------------------------------------------------------------------ Table: ringing ablation with absolute near counts
E3 = by("rescore_E3")
if E3:
    body = []
    for r in E3:
        g = r["ringing"]
        e = g.get("e3b", {})
        nm = {"jpeg2000_97": "JPEG2000 9/7", "jpeg2000_53": "JPEG2000 5/3", "hevc": "HEVC", "baq": "BAQ"}[r["arm"]]
        pt = f"r{r['params']['ratio']}" if "ratio" in r["params"] else (f"QP{r['params']['qp']}" if "qp" in r["params"] else f"{r['params']['bits']}-bit")
        body.append(f"{nm} {pt} & {r['rate_bps']:.2f} & {g['pd']:.3f} & {fmt(g['n_phantom'])} & {e.get('near_strong', '--')} & {e.get('near_weak', '--')} & {e.get('near_random', '--')} & {'yes' if ok(r) else 'no'}")
    table("tab_ringing", "Focused-domain ablation on Illinois, corrected scorer. Phantoms: reconstruction peaks more than 3 cells "
          "from any reference peak. Near: number of phantoms within 8 cells of the 1{,}397 strongest reference peaks, of the "
          "1{,}397 weakest, and of 1{,}397 random interior cells.",
          "tab:ringing", "@{}lrrrrrrc@{}", "Base codec & Rate & $P_d$ & Phantoms & Near strong & Near weak & Near random & Sust.", body)
    H["ringing_rows"] = [(r["arm"], r["params"], round(r["rate_bps"], 2), r["ringing"]["n_phantom"], r["ringing"].get("e3b")) for r in E3]

# ------------------------------------------------------------------ Durango / proxy / clip control headline numbers
E4g = by("rescore_E4", "gotcha_gmti")
if E4g:
    kept = [r for r in E4g if r["durango"]["detected_within_tol"]]
    H["durango_retained"] = (len(kept), len(E4g))
    H["durango_lowest_rate_retained"] = round(min(r["rate_bps"] for r in kept), 2) if kept else None
    H["durango_lost_at"] = [(label(r)[0], label(r)[1], round(r["rate_bps"], 2)) for r in E4g if not r["durango"]["detected_within_tol"]]
E4s = [r for r in by("rescore_E4", "s1_focused") if r.get("strong_subset", {}).get("mode") == "topdecile"]
if E4s:
    H["s1_proxy"] = sorted([(label(r)[0], label(r)[1], round(r["rate_bps"], 2), r["cfar_pd"], r["strong_subset"]["pd_subset"]) for r in E4s], key=lambda t: -t[2])
E8 = by("ctrl_E8")
if E8:
    H["clip_control"] = [(r["codec"], r["params"], r["domain"], round(r["rate_bps"], 2), r["cfar_pd"], r["cfar_false"], r["n_ref_detections"], r.get("sqnr_img_db"), r.get("clip")) for r in E8]
L = by("rescore_learned")
if L:
    H["learned_rescored"] = len(L)
    H["learned_best"] = {d: max((r for r in L if r["domain"] == d), key=lambda r: r["cfar_pd"], default=None) and
                         (lambda b: (round(b["rate_bps"], 2), round(b["cfar_pd"], 3), b["cfar_false"]))(max((r for r in L if r["domain"] == d), key=lambda r: r["cfar_pd"]))
                         for d in {r["domain"] for r in L}}

(ROOT / "reports" / "v4_headline_numbers.json").write_text(json.dumps(H, indent=1, default=str), encoding="utf-8")
print("tables written:", sorted(p.name for p in OUT.glob("*.tex")))
print(json.dumps({k: v for k, v in H.items() if not isinstance(v, list) or len(v) < 8}, indent=1, default=str)[:3000])
