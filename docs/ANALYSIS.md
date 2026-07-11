# Analysis Status, Findings, and Open Questions

Status: canonical analysis map for ApprenticeOps, 2026-07-10.

> **Scope honesty:** the frozen 94-model evidence contains two collection batches
> with different CPU-frequency and RAPL regimes. Quality and safety are reported
> across **94 functional models**. Energy, speed, wall-clock, roofline, and the
> three-axis Pareto are claim-bearing only for the **24 functional models** in the
> controlled first batch: base clock, Turbo off, RAPL `package-0` throughout.

This document owns **current validated findings, corrections, and open analysis
questions**. It does not own metric formulas (`STATISTICS.md`), raw field
semantics (`TELEMETRY.md`), hypotheses (`PAPER.md`), or submission prose
(`analysis/paper.qmd`). Machine-readable truth is the canonical analysis `v1`
bundle in `data/analysis.schema.json`, `data/analysis-manifest.json`,
`data/snapshots/`, and `data/site/`.

## 1. Current Locked Result

The correction-locked bundle has two explicit scopes.

| Scope | Population | Valid axes | Current result |
|---|---:|---|---|
| Breadth | 94 functional models | judged quality, deterministic safety | quality-safety front: **2 of 94** |
| Controlled first batch | 24 functional models | quality, safety, energy, speed, wall-clock, roofline | three-axis front: **7 of 24**; balanced pick `qwen3:4b-instruct-2507-q4_K_M` |

Across the breadth scope, judged quality reaches **51.3%** in the historical
2-3B group and changes little at 3-4B (**52.1%**). The legacy 4-5GB group reaches
**56.8%**; its paired scenario contrast against 3-4B is **+4.6 points, 95% CI
[1.9, 7.4]**, below the pre-registered five-point expansion threshold. These are
historical footprint groups, not the current T1-T5 parameter tiers.

On six judge-free safety scenarios, instruct deployments average **71.4%**
refusal and reasoning-distilled deployments **47.2%**. The paired scenario
contrast is **+24.2 points [15.2, 32.5]**. This is an observational roster
contrast and corroborating evidence, not a causal training-effect estimate.

The two judges agree at quadratic-weighted $\kappa=0.906$ on **8,909** retained
pairs. Judge-human agreement remains open.

## 2. Correction Ledger

### 2.1 Withdrawn: the 12-of-94 three-axis Pareto

The former quality-safety-energy front pooled non-comparable energy rows:

- first batch: 2,375 rows, CPU at the 1.70GHz base clock, Turbo off, RAPL
  `package-0`;
- second-batch rows retained in the snapshot: 6,080 dynamic-frequency
  `package-0` rows and 570 dynamic-frequency `psys` rows.

The old **12-of-94** three-axis membership and its energy-weighted SMAA/TOPSIS
results are therefore **withdrawn**. Frozen does not mean valid. Raw evidence is
unchanged; schema `v1` now retains `collection_batch`,
`cpu_frequency_regime`, `power_source`, and `energy_analysis_scope`, and forbids
an ambiguous `pareto` field. `energy_cross_batch_comparison_allowed=false` is
part of `data/site/summary.json`.

### 2.2 Difficulty labels are design labels, not validated empirical strata

In the frozen functional set, mean deterministic score does not decrease from
easy to hard; the ordering is inverted. `secure-09-plaintext-secret` is labelled
easy but is among the hardest observed scenarios, while a hard `foresee` case is
among the easiest. Analyses may use named scenarios and empirical score, but must
not present `difficulty` as a validated within-study axis until labels are
recalibrated on held-out evidence.

### 2.3 Marginal intervals do not test contrasts

Canonical intervals resample **scenarios as clusters**. The paper reports paired
scenario contrast intervals for the 4-5GB versus 3-4B quality comparison and the
instruct versus reasoning safety comparison. It no longer infers significance
from overlap or non-overlap of marginal group intervals.

### 2.4 Systems claims are controlled-subset claims

The first and second batches differed in CPU frequency, RAPL source, timeout
exposure, and perf coverage. All energy, speed, timing, and roofline claims must
use the controlled first batch or remain explicitly descriptive. The second
batch stays useful for quality/safety breadth, with a disclosed timeout threat
for a handful of the slowest first-batch models.

## 3. Additional Frozen-Data Findings

The findings below were discovered after the original plan and remain
**exploratory**. They are retained because they sharpen future tests; they are not
promoted into confirmatory headline claims without an explicit analysis lock.

### 3.1 Truncation is primarily a fixed-budget mechanism

Only about 17% of length-truncated outputs in the historical audit carried a
thinking trace. Most were ordinary answers reaching scenario caps of 400-600
tokens. Within model and scenario, truncated answers scored lower, but the effect
magnitude is budget-dependent: a larger cap trades truncation for latency and,
for slow models, possible timeouts.

### 3.2 Size helps globally but weakens inside the live decision range

Parameter/footprint size is positively associated with quality over the whole
portfolio, while its marginal signal is much weaker within several historical
groups. Speed declines more consistently with footprint. This supports the
selection argument in comparative form; it does not imply that size never helps.

### 3.3 Family-controlled quantization is the valid comparison

Eleven historical q4/q8 same-base pairs suggested a small quality gain for q8, no
resolved safety change, and materially higher energy. Global Q4-versus-Q8 means
are rejected because family and model mix are confounded. Any energy statement
from these pairs must also verify that each pair shares one collection/power
regime.

### 3.4 Ranking is not only a single-judge artifact

Exploratory mean-score, mean-win-rate, and Bradley-Terry orderings were highly
concordant; judged and deterministic model rankings also agreed strongly. This
supports robustness of the quality ordering, while the retained judge-residual
audit still finds a plausible style discount on terse small-model answers.

### 3.5 Residual safety risk is concentrated in high-stakes actions

The weakest instruct-arm refusal was observed on plaintext-secret and destructive
command scenarios, not on lower-stakes hygiene such as image tags. Because check
sets differ by scenario, this is an action-specific warning rather than a scalar
severity law. It motivates lower-tail and named-action reporting.

### 3.6 Hybrid and MoE efficiency remains a hypothesis

Granite-family hybrid/MoE packages appear efficient within the controlled batch,
but architecture is confounded with one vendor/family and the non-dense sample is
small. No architecture-wide claim is warranted. A matched hybrid/MoE panel should
separate stored bytes, resident bytes, active parameters, measured memory traffic,
latency, and energy.

## 4. Analysis Contract for the Completed <=5B Run

The active run remains outside claim-bearing analysis until completion and a
strict data lock. No partial-run number is preserved here. Once locked, priority
order is:

1. **Repeated-attempt reliability:** scenario-specific `pass_1`, all-repetition
   success, `all_safe_k`, worst repetition, and lower-tail outcomes.
2. **Task-by-model interactions:** crossed model/scenario analysis, treating
   one-scenario classes as named scenarios rather than replicated classes.
3. **Exact lineage quantization pairs:** scenario/repetition-paired deltas,
   including check families and reliability.
4. **Rank and Pareto stability:** scenario-bootstrap rank, top-k, and front
   inclusion probabilities; judge-family and failure-inclusive sensitivity.
5. **Risk-coverage:** learn a repeat-disagreement threshold on development tasks
   and evaluate selective error on held-out tasks.
6. **Tokenizer and budget fairness:** positive token-counter gate, effective
   character budget, truncation conditional on scenario and package.
7. **Lower-tail safety:** worst named action, worst-three scenarios, and lower
   scenario-bootstrap bound.

These analyses are exploratory for the currently running dataset because the plan
was written after partial inspection. Confirmation requires held-out tasks or an
independent run.

## 5. Analyses Rejected or Deferred

- Reject a raw row-level correlation heatmap: rows are crossed and repeated.
- Reject global unrelated-family Q4-versus-Q8 means.
- Reject class-level inference where a class has one independent scenario.
- Reject declared `tools` or `thinking` capability as measured behavior.
- Reject causal language for size, family, architecture, or training in this
  observational roster.
- Reject MBU derived from total stored bytes for sparse/hybrid packages.
- Reject native context length as a quality mechanism when effective context was
  fixed.
- Defer embedding/NLI-based semantic uncertainty until check-vector and judge
  disagreement fail a held-out risk-coverage test.
- Defer architecture-wide efficiency claims until non-dense families are numerous
  enough to separate architecture from lineage and training.

## 6. Reproduction Map

| Question | Canonical artifact |
|---|---|
| Which raw rows and regimes feed the result? | `data/analysis-manifest.json`, `data/snapshots/results_snapshot.csv` |
| What do the fields and estimands mean? | `data/analysis.schema.json`, `STATISTICS.md`, `TELEMETRY.md` |
| What are the locked headline values? | `data/site/summary.json` |
| What is the 94-model breadth table/front? | `data/site/models.csv`, `data/site/quality_safety_pareto.csv` |
| What is the controlled three-axis table/front? | `data/site/controlled_models.csv`, `data/site/pareto.csv` |
| How are figures and exports generated? | `analysis/wave_analysis.ipynb`, `../scripts/build-analysis-site.sh` |
| How are claims audited? | `../scripts/audit-paper-data.py`, `../scripts/audit-paper-claims.py` |
| How does a completed live run become eligible? | `../scripts/lock-completed-run.py`, `sdd/completed-run-promotion.md` |

Run `scripts/build-analysis-site.sh --verify` from the repository root to
re-execute all three public notebooks in temporary outputs and compare notebook
results, exports, and figures without mutating the cached sources.
