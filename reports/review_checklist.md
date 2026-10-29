# Pre-submission hostile-review checklist (radar-codec; reusable across lanes)

Derived from the TGRS-2026-08067 reviews (2026-10-19) and the DV026 adversarial pass. Run by a FRESH
reviewer context with the manuscript, `experiments/runs.jsonl`, and `reports/claims_ledger.md`. The
reviewer's job is to find what is wrong, not to improve prose.

## A. Numbers and claims
1. Every quantitative sentence maps to a ledger line; every ledger line maps to a run id / config hash.
2. Every counterfactual ("criterion X would have accepted Y") is checked against X's threshold on Y's own row.
3. Text, tables, and figures agree on every shared number (rates, Pd/retention, counts, thresholds).
4. Where several runs exist per configuration, all are reported (or mean + spread); no single-run cherry-pick.
5. Headline ratios are recomputed from the table by the reviewer, not trusted from the text.

## B. Metrics and criteria
6. Metric names say what is measured (retention of reference detections, not "detection probability",
   unless validated against ground truth).
7. Every threshold (0.9 retention, 10% spurious budget, CFAR parameters, matching tolerance) has a stated
   rationale and, where feasible, a sensitivity check.
8. Matching / deduplication rules are explicit (one-to-one? tolerance? multiple peaks per target?).
9. Fidelity metrics (SQNR/PSNR/MSE) are reported for the SAME configurations as task metrics whenever the
   paper argues fidelity is insufficient.

## C. Causality and scope
10. Every causal attribution (e.g., "wavelet ringing causes the false alarms") has an ablation or a
    controlled comparison, not only an illustrative image.
11. Negative results distinguish implementation failure from inherent limitation, with the evidence for each.
12. Every claim is scoped (N scenes, sensors, SNR levels, data lineage); any "minimum acceptable rate" is
    reported as a function of the conditions it depends on (SNR at least).
13. Reference sets (e.g., CFAR detections) are validated against ground truth where ground truth exists.

## D. Form
14. Acronyms expanded at first use; architectures and configurations specified (layers, sizes, training).
15. Future-work material lives in future work, not in methods.
16. Pre-registration status of every analysis is marked (pre-registered / amendment / post hoc).

## Output format
A numbered list of findings: location (section/line), the claim, the row(s) that contradict or fail to
support it, and the minimal correct statement. Severity: BLOCKER (false claim) / MAJOR (unsupported) /
MINOR (form). No praise, no rewriting.
