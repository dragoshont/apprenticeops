# Statistics Plan

Status: active statistics spine, created 2026-07-03.

## Estimands

Primary estimands:

- judged quality as percent of the 1-5 judge ceiling;
- deterministic-check score;
- destructive-action refusal rate for guard/secure tasks;
- energy per answer and tokens/s-per-watt;
- latency and memory fit metrics.

The selection object is a deployment, so comparisons must be scoped by model,
runtime, quantization, hardware profile, prompt policy, memory context, inference
strategy, and evaluation policy.

## Repetitions

Locked paper-era runs use 5 repetitions per model/scenario where available.
Dev/app runs must state their repetition count in `run.meta` and in any review
doc.

## Confidence Intervals

For bracket or tier summaries, use bootstrap confidence intervals over the
appropriate unit. The current paper-era analysis reports bootstrap 95% CIs for
legacy brackets. Future thesis-track analysis should report CIs by T1-T5
parameter tier.

## Paired Comparisons

When the same scenarios/repetitions exist across models or conditions, prefer
paired comparisons. If pairing is broken by DNF/missing rows, report the missing
policy before any test statistic.

## Multiple Comparisons

Per-model leaderboards are descriptive unless corrected. Primary claims should
be bracket/tier-level or Pareto-level unless the model-level comparison survives
the planned correction. Where many pairwise tests are run, use a correction such
as Holm-Bonferroni or state that the table is exploratory.

## Missing, DNF, And Length Rows

Do not drop failed rows silently.

- DNF/stall is a reliability outcome.
- Length truncation is a reliability outcome.
- Zero-output stalls are a reliability outcome.
- Pull/serve failures need an explicit exclusion reason.

`scripts/report-run-quality.py --strict` is the structural gate before quality
interpretation. It does not make a run scientifically sufficient; it only says
the artifact is complete enough to read.

## Pareto Robustness

The current Pareto front is computed on point estimates. For doctoral reporting,
add a robustness check:

- CI-aware dominance or near-tie treatment;
- sensitivity to energy metric choice;
- sensitivity to judge family;
- sensitivity to excluding served failures;
- sensitivity to T1-T5 parameter-tier grouping.

Until that exists, report Pareto membership as a point-estimate selection result,
not a mathematically final ordering.