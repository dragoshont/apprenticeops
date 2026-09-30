# Selection stability in the 152-deployment study

**Date:** 2026-09-09. **Status:** retained P2 computations accepted after parent
replay and independent GPT/Claude review. All results remain **provisional and
exploratory**; no human-validity or publication gate is closed.

> **Scope honesty.** We measure sensitivity to scenario composition for **137
> fixed deployment tags**, not superiority over a population of independent
> models. The quality instruments remain unvalidated. Pareto membership does
> not establish usability, safety or a universal deployment recommendation.

## 1. Frozen inputs and estimands

We extend the [approved closure programme](152-analysis-closure.md) and
[statistics plan](../STATISTICS.md#10-rank-and-pareto-robustness), using the frozen
[`analysis-repair-152-20260909-r4`](../../deep-dive/out/analysis-repair-152-20260909-r4/)
receipt, eligibility and identity tables, and its hash-bound results/judged
snapshots. No earlier study outcomes, live data or human labels enter this analysis.
We preserve r2/r3 and original selection receipts. This r4 refresh incorporates
the parent-requested authoritative-class/A2 corrections plus named judge-policy
and canonical-condition guards, then re-anchors the reused helpers to their
new hashes. All six selection CSVs remain
byte-identical; the numerical selection results below do not change.

The selected grid is **137 tags × 20 scenarios × five repetitions = 13,700
assigned attempts**, each with both recorded judges. The new loader checks the
anchored predecessor receipt, exact joins/roster/repetitions, energy measurement
scope, consensus agreement with the frozen repair output, and per-tag point means.
Missing/nonfinite scores or energy, negative energy, and incomplete/duplicate
cells fail the calculation. There is **no complete-case filtering or imputation**.

The compact key is compatible only with these hash-bound snapshots: the core
audit now requires the exact Copilot Claude Opus 4.6/GPT-5.4 policy, proves one
canonical condition per tag, and matches all **30,400** judgments to those
condition IDs. This is not a generic “any two judges” or multi-condition join.
New evidence and claim promotion retain the statistics plan's full canonical-key
requirements.

We use **4,000 scenario-bootstrap draws**, seed **20260725**, retaining every
sampled scenario's five repetitions and all tags. A repeated scenario contributes
once **per draw occurrence**. The same draw indices are used for every arm and
both axes. We do not resample tags, infer weight independence, or resample the
five observed repetitions as if they were additional scenarios.

The **primary two-axis selection** maximizes mean recorded consensus judge score
and minimizes measured **RAPL package-0 Wh per assigned attempt**. Every attempt's
energy enters the denominator/numerator accounting; we do not condition on
completion or success, and we do not introduce an additional failure-value
transformation of the recorded scores. This is not wall-power or DRAM-inclusive
energy.

We compute **15 descriptive sensitivity arms**:

- consensus, Claude-only and GPT-only mean score;
- for each score source, observed per-attempt success at thresholds
  **2.5, 3.0, 3.5 and 4.0**, keeping the same Wh/attempt axis.

Threshold success is a different quality axis, not thresholded mean quality or
all-five reliability. The primary threshold remains **3.0**. For the integer
individual-judge scores, thresholds 2.5/3.0 and 3.5/4.0 yield identical success
arms; these are not independent pieces of evidence. Zero-success deployments
remain present. We do **not** replace Wh/attempt with finite-only Wh/success.

We omit a third action-safety axis: incomplete applicability and vacuous passes
in the existing check instrument cannot establish a credible operational-safety
tradeoff. No new hypothesis preregistration or claim promotion occurs.

## 2. Ranks, ties and Pareto membership

We rank the quality axis in descending order using **midranks for ties**.
For top-1/5/10, a boundary tie receives **remaining slots divided by tied tags**:
if two tags tie for the last top-five slot, each receives 0.5 credit. Credits sum
to exactly k in every draw. Their averages are inclusion frequencies under
uniform tie-breaking, not an advantage assigned by tag name or input order.

A tag is Pareto-dominated only if another tag has at least as much quality and
at most as much energy, with **at least one strict improvement**. Identical
quality/energy points all remain on the front; at equal energy, lower quality
is dominated. We reuse the repaired `a2_efficiency.pareto_mask`.

The reported 2.5th–97.5th percentiles are **central scenario-resampling ranges**,
not posterior probabilities, confidence bounds on operational validity or
proof of generalization to new SRE incidents. Monte Carlo error remains: with
4,000 draws, the largest Bernoulli Monte Carlo standard error is about
**0.79 percentage points**. A membership frequency of 1 is not real-world certainty.

## 3. Results

For consensus mean quality, the mean Kendall τ-b agreement with the point ranking
is **0.908709**, with central range **[0.864270, 0.943020]**. All 4,000 rank
agreement calculations are defined. The point Pareto front contains **11 tags**;
resampled front size has mean **11.19125**, central range **[8, 14]**. Mean
Jaccard overlap with the point front is **0.684736 [0.500000, 0.909091]**.
A relatively stable ranking does not make the point Pareto set invariant.

The five highest **point mean scores** illustrate the distinction. Percentages
below are resampling inclusion frequencies; the rank ranges include midranks.

| Deployment tag | Mean score | Wh/attempt | Point rank; central rank range | Top-1 | Top-5 | Pareto |
|---|---:|---:|---|---:|---:|---:|
| `qwen3:4b-instruct-2507-q8_0` | 3.590 | 0.160507 | 1; [1, 3.5] | 76.946% | 99.825% | 76.625% |
| `qwen3:4b-q8_0` | 3.400 | 0.138943 | 2; [1, 4] | 6.958% | 100.000% | 31.375% |
| `hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M` | 3.380 | 0.093340 | 3; [1, 5] | 15.821% | 97.908% | 91.875% |
| `qwen3:4b-instruct-2507-q4_K_M` | 3.360 | 0.108998 | 4; [2, 5] | 0.088% | 98.175% | 45.475% |
| `gemma4:e2b-it-qat` | 3.185 | 0.050452 | 5; [3, 9] | 0.063% | 66.838% | 99.425% |

The second row is on the point front but survives only **31.375%** of resampled
fronts. Conversely, the fourth is not on the point front but enters **45.475%**
of resampled fronts. These are separate selection outcomes, not contradictory
rankings. Low-cost, low-quality tags can also be stable Pareto members:
`gemma3:270m` has mean quality **1.280** and Pareto frequency **99.250%**.
Pareto membership alone is not an adequate deployment criterion.

| Mean-score source | Mean τ-b; central range | Point front size | Mean front size; central range | Top-1 credit for `qwen3:4b-instruct-2507-q8_0` |
|---|---|---:|---|---:|
| Consensus | 0.908709 [0.864270, 0.943020] | 11 | 11.19125 [8, 14] | 76.946% |
| Claude-only | 0.914709 [0.872725, 0.947422] | 12 | 12.18075 [9, 15] | 77.221% |
| GPT-only | 0.896565 [0.847832, 0.936166] | 10 | 10.09225 [7, 13] | 62.942% |

Per-judge agreement with its own point ranking is **not judge validity**.
The changed selection frequencies demonstrate sensitivity, not permission to
choose the most favourable judge.

| Consensus success threshold | Point front size | Mean resampled front size; central range | Mean τ-b; central range |
|---:|---:|---|---|
| 2.5 | 10 | 8.98750 [6, 12] | 0.896349 [0.851084, 0.934707] |
| **3.0** | **13** | **10.84400 [8, 14]** | **0.892857 [0.842155, 0.935661]** |
| 3.5 | 11 | 10.22650 [7, 13] | 0.875045 [0.794155, 0.946396] |
| 4.0 | 9 | 9.16450 [7, 12] | 0.865242 [0.746570, 0.953194] |

At consensus ≥3, both zero-success tags (`codegemma:2b`, `starcoder2:3b`) remain
in the 137-member calculation; each has Pareto frequency **0**. No finite-cost
subset replaces the assigned roster.

## 4. Integer-derived tier descriptions

We apply the integer authority already specified in `AGENTS.md`:
T1 ≤1B, T2 (1B,2B], T3 (2B,3B], T4 (3B,4B], T5 (4B,5B].
This deterministic classification requires no new human choice of authority.
We also retain the frozen lock labels, recording **27 differing assignments**.
We do not change `models.lock.jsonl` or recast nominal tag names as integer counts.

| Tier | Integer-derived tags | Frozen lock-labelled tags | Integer-group mean consensus score | Integer-group mean Wh/attempt |
|---|---:|---:|---:|---:|
| T1 | 25 | 27 | 1.467400 | 0.020784 |
| T2 | 34 | 37 | 1.686176 | 0.055400 |
| T3 | 17 | 29 | 2.242941 | 0.077193 |
| T4 | 43 | 29 | 2.326977 | 0.109299 |
| T5 | 18 | 15 | 2.779167 | 0.132741 |

These are **fixed-tag descriptive means**, not independent training replicates
or causal size effects. `tier_descriptives.csv` keeps both tier systems separate
for all 15 arms, including expected top-k slot counts; it never averages the two
classification systems together.

## 5. Reproduction and verification

New implementation and test files:
[`selection_stability.py`](../../deep-dive/selection_stability.py) and
[`test_selection_stability.py`](../../deep-dive/test_selection_stability.py).
The existing deep-dive interpreter and installed libraries are sufficient.

```bash
deep-dive/.venv/bin/python deep-dive/test_selection_stability.py
deep-dive/.venv/bin/python deep-dive/selection_stability.py \
  --out deep-dive/out/selection-stability-152-20260909-r4
```

The output path must be **unused**; choose a new path for replay. The driver
refuses to overwrite evidence. It reads only the frozen portable snapshots and
predecessor evidence; no raw-bundle download, inference, rejudging or remote
operation is required.

| Current artifact under `deep-dive/out/selection-stability-152-20260909-r4/` | Content |
|---|---|
| `population.csv` | 137 tags, integer counts, both tier labels and frozen artifact/lineage status. |
| `scenario_draws.csv` | 4,000 shared draws; indices refer to the ordered scenario list in the receipt. |
| `selection.csv` | **2,055 tag–arm rows**: point axes/ranks, rank ranges, top-1/5/10 and Pareto frequencies. |
| `arm_summary.csv` | Fifteen arm-level rank/front summaries. |
| `draw_summary.csv` | **60,000 arm–draw rows**: τ-b, front size and Jaccard overlap. |
| `tier_descriptives.csv` | 150 arm–tier-system descriptions; no tier reassignment in source data. |
| `receipt.json` | Anchored input/code/output SHA-256, scenario order, seed, packages and definitions. |
| `verification.json` | Historical implementation test/replay record. Final parent acceptance is recorded below and in the linked sensitivity-closure report; the original receipt remains unchanged. |

Receipt SHA-256:
`4b929c382f69c7e8d07a75d4e4be2b49540b43cc6d90b08e90708ac372d70fd2`.
`selection.csv` SHA-256:
`b37b7e19d2fa185aeb3cf477f281e06a4c3f60332fc4a8d08ccefe8b59ccab2d`.
The frozen predecessor receipt is
`22fac59e27ec3df40406d00c5b31cd39ae55596140c0d16f817abc1af185371a`.

**18 focused tests PASS:** ties and fractional slots, strict/equal-cost
dominance, repeated draw multiplicity, exact roster/repetitions, unknown and
nonfinite inputs, consensus pairing, row/model ordering, zero success, undefined
rank agreement, integer boundaries, separate tier systems, hash refusal and
deterministic replay. Config wiring remains with the parent; the first command
above is the new test entry point.

All input, code and six output hashes were independently rechecked. A fresh
new-directory invocation produced **six byte-identical CSVs and a byte-identical
computation receipt**. Configured repository checks, compilation, links and
whitespace gates **PASS**. The scoped privacy scan found **zero secrets and zero
disclosures** in 24 new-file/run artifacts including the verification
receipt during the original extension. The r4 source hashes reflect the
explicitly authorized review corrections; all six selection CSVs and all
16 non-identity core CSV/PNG files remain unchanged. The identity audit now also
contains canonical condition IDs and the named policy. Current replay and scoped-scan evidence
is in `verification.json`; the parent retains config ownership.

## 6. Disposition and remaining gates

| Candidate statement | Disposition |
|---|---|
| Fixed-roster rank/top-k/Pareto selection sensitivity | **Retain as exploratory machine-calculation evidence**; now computed rather than deferred. |
| Point-front membership is stable or a universal “best” exists | **Reject**; report the observed membership frequencies and the specified axes. |
| Integer-tier descriptions | **Retain as fixed-roster descriptions**, alongside the frozen conflicting lock labels. |
| Safety, real-world usability, independent-weight or hardware generalization | **Not established**; no supporting labels, lineage verification or new platform evidence was added. |
| Confirmatory hypothesis or paper-final claim | **Not promoted**; prior inspection and unvalidated instruments remain explicit. |

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 2 | Additional P2 selection stability | complete for retained machine calculations | New module/tests/output/report only | Deterministic checks and independent parent review | Parent tests, hashes and byte-identical replay PASS; final GPT/Claude PASS. |
| 3 | Scientific and claim approval | not-started | Validity evidence and human decisions | Independent review and required approvals | Not performed here. |

**Implemented:** the selection module, tests, output and report, initially as
new files, followed by the parent's authorized source-anchor refreshes.
The parent separately authorized the first-batch scenario-class and A2-label
corrections; their numerical receipts were regenerated into new directories,
never overwritten. Config, site assets and human-data files remain untouched.
No reviewer agent was launched. Additional nonhuman closure computations are
authorized; the remaining gates are evidence/review requirements, not a lack
of permission to compute.

The installed legacy `harness/validate-run.sh` again rejects the canonical v2
summary schema. This audit-tool incompatibility is recorded, not bypassed by
manual run edits or a kit change. It does not invalidate the independent numeric
replay, and it is not reported as a passed audit gate.

The [final bounded sensitivity extension](152-selection-sensitivity-results.md)
adds the completion-proxy and alternative-energy comparisons and explicitly
dispositions unmeasured screened failures. The parent independently replayed
this report's six CSVs and receipt exactly; both judge families accepted the
retained computational scope.

**Next evidence gate:** human instrument validation. Any required second-platform
work and claim/publication decisions remain **not started by this task**.

| Threat | Type | Mitigation |
|---|---|---|
| Curated tasks and screened tag roster | External validity | Fixed-roster scenario-composition sensitivity only; no random-population claim. |
| Multiple tags may share weights | Statistical | Preserve all tags as the declared selection universe; do not infer training independence. |
| Unvalidated judge thresholds | Construct validity | Separate score/rate axes and all sensitivities; no favourable-cutoff selection. |
| A cheap failure can be Pareto-efficient | Decision validity | Retain zero successes, name axes, and explicitly reject Pareto-as-deployment-approval. |
| Bootstrap frequencies mistaken for certainty | Interpretation | Report resampling ranges, tie policy and Monte Carlo precision separately from scientific validity. |
