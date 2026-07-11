# Statistics Plan

Status: active statistics spine, created 2026-07-03; expanded 2026-07-10 after
the SLM metric/correlation audit.

> **Analysis-status honesty.** The legacy H1-H7 plan in `docs/PAPER.md` remains
> the pre-registration for the released 94-model snapshot. The additions below
> were written after partial inspection of the active 152-tag run. They are
> therefore **exploratory robustness analyses for that run**, even though they
> are specified before the run finishes. They become confirmatory only on an
> independent future run or held-out scenario pack. Metric-definition repairs
> are corrections, not new hypotheses.

## 1. Analysis Object And Population

The selection object is a **deployment**, not bare weights:

```text
deployment = model weights + runtime + quantization + hardware profile
					 + chat template + sampler policy + prompt policy + memory context
					 + inference strategy + evaluation policy
```

Every comparison must either hold these factors fixed or include them explicitly.
For the doctoral track, the primary population is the rows whose model-lock entry
has `included=true` (T1-T5, no more than 5B parameters). Above-5B rows are a
separately labelled legacy comparison; they are never pooled into a thesis-tier
coefficient or mean.

The data are crossed and repeated:

- model/deployment;
- scenario;
- repetition within `(model, scenario)`;
- judge family within an inference row;
- optional runtime, memory, and inference-strategy conditions.

Rows sharing a model or scenario are not independent observations.

Judge scores are joined to inference rows by the full canonical
`analysis_condition_key_sha256`. Every new judge row also carries the requested
`evaluation_policy`, including judge families that were requested but failed to
return a row, so partial judge output cannot silently change the condition hash.
Historical judge rows without a condition hash are rejected by default. An
explicit legacy-compatibility flag may use their
model/scenario/repetition/memory/strategy/runtime key only when the selected
inference artifact proves that key identifies exactly one canonical condition.
If those rows do not carry `evaluation_policy`, compatibility mode also requires
the operator to provide the complete requested policy explicitly; surviving
judge rows cannot define it. A
key that spans multiple hardware, quantization, artifact, prompt, or sampling
conditions is an interpretation blocker even in compatibility mode: adapters
raise an error and the rows are rejudged. No last-row-wins or available-case
fallback is permitted.

Judge identity is `(judge_backend, judge_model)`, not model ID alone. A
condition/scenario/repetition receives a consensus score only when its observed
judge identities exactly equal the complete requested set in
`evaluation_policy`. Partial ensembles remain missing evidence; they are never
renormalized over the successful family.

## 2. Primary Estimands

Report the following as separate axes:

1. **Conditional judged quality:** judge score among usable completions.
2. **Unconditional deployment quality:** the same outcome with a locked failure
	 value for DNF and blank outputs, so unreliable models do not benefit from
	 survivorship.
3. **Deterministic-check score:** fractional check pass rate, with exact
	 `det_detail` failure families retained.
4. **Safety:** refusal / non-endorsement across the explicit safety set (guard,
	 secure, or lifecycle-tagged destructive risk), including an all-repetitions
	 safety outcome.
5. **Repeated-attempt reliability:** `pass_1`, `pass_k`, and `all_safe_k`, not
	 only mean score or majority agreement.
6. **Completion reliability:** separate probabilities for `stop`, `length`,
	 blank-stop, timeout, other DNF, and incomplete stream finalization.
7. **Systems cost:** TTFT, decode and wall time, chars/s, jitter, memory fit,
	 Wh/answer, and tokens/s-per-watt. Do not substitute one efficiency proxy for
	 the complete set.
8. **Selection robustness:** rank and Pareto inclusion frequency under scenario
	 resampling and judge/metric sensitivity.

`judge_score / 5` is a normalized judge-ceiling score, not literal percent of a
frontier model's task accuracy. Use "percent of judge ceiling" in new analysis;
retain the historical label only when quoting the frozen legacy artifact.

## 3. Repetitions And Reliability

Locked runs use five repetitions per model/scenario. Dev/app runs must state
their repetition count in `run.meta` and review artifacts.

Define a success rule for each scenario before aggregating. It may be a hard
deterministic requirement, a validated structured-output check, a safety rule,
or a locked judge threshold. Do not assume `det_score == 1` is equally meaningful
for every scenario.

For `k` observed repetitions:

$$
\operatorname{pass}^{k}_{m,s} = \prod_{r=1}^{k} I(\text{success}_{m,s,r})
$$

where $m$ is a model/deployment, $s$ a scenario, $r$ a repetition, and $I$ the
indicator function. Aggregate this indicator over independent scenarios. This is
the probability that **all** attempts succeed; it is not `pass@k` (at least one
success). Define `all_safe_k` analogously: no unsafe action in any repetition.

Keep repeatability distinct from correctness. A model that fails identically five
times is perfectly repeatable and operationally useless. Report:

- agreement of deterministic check vectors;
- score dispersion;
- `pass_1` and `pass_k`;
- worst-repetition and lower-tail score;
- `all_safe_k` for safety-critical tasks.

## 4. Missingness And Failure Policy

Do not drop failed rows silently.

- DNF/stall is an inference reliability outcome.
- Length is an observed, potentially truncated answer plus a reliability flag.
- Blank-stop is a model/runtime outcome, not a judge failure.
- Pull/serve failure needs an explicit exclusion reason and remains in the
	deployment-reliability denominator where appropriate.
- Judge parse/empty failures are evaluation missingness. Rejudge them; if still
	unresolved, do not convert them into model-quality failures.
- Invalid token counters (`<=0`) are excluded from token-ratio metrics and
	reported by model/finish reason.

Every quality table must state whether it is **conditional** or **unconditional**
on completion. `scripts/report-run-quality.py --strict` is the structural gate
before interpretation; it is necessary-not-sufficient for scientific validity.

## 5. Confidence Intervals And Resampling Units

The interval must match the population claim:

- **Per-model generalization over tasks:** resample scenarios as clusters,
	retaining their repetitions and judges.
- **Tier/family summary:** resample models as clusters and, for a broader task
	claim, scenarios as a second cluster or nested bootstrap dimension.
- **Model/condition contrast:** paired scenario/repetition cluster bootstrap.
- **Judge sensitivity:** recompute with each judge family and the consensus;
	do not treat two judges on one answer as two independent task observations.

A row-level bootstrap may describe variation in the observed artifact, but it
does not estimate generalization to new scenarios. Label it accordingly.

## 6. Crossed Explanatory Analysis

Global correlations are screening statistics, not explanatory results. After the
post-run model dimension is frozen, estimate task-aware associations using a
model appropriate to the outcome. A target structure is:

$$
y_{msr} = \beta_0 + \beta_1 \log(P_m) + \beta_2 Q_m +
\beta_3 T_m + \beta_4 A_m + \beta_5 X_s +
\beta_6(Q_m \times X_s) + u_{family(m)} + v_s + \epsilon_{msr}
$$

where $P_m$ is parameter count, $Q_m$ quantization, $T_m$ training regime,
$A_m$ architecture, $X_s$ scenario/task properties, and $u$ and $v$ family and
scenario effects. Use a binary model for hard pass/safety outcomes, an ordinal or
carefully justified aggregate model for judge scores, and a log/continuous model
for latency and energy.

These coefficients are **observational associations**, not causal effects:
families were not randomized across size, training, architecture, or
quantization. Classes represented by fewer than three independent scenarios are
descriptive named-scenario results, not class-level inference.

## 7. Paired Quantization And Condition Comparisons

Use only verified same-lineage pairs for quantization claims. Pair on scenario
and repetition, and report deltas for:

- judged and deterministic quality;
- `det_detail` failure families;
- `pass_k` and safety;
- length/DNF/blank outcomes;
- latency, memory, and energy.

Likewise, memory, strategy, or runtime comparisons are valid only when model,
scenario, repetition/seed, prompt bytes, and evaluation policy are aligned. If
pairing is broken, report the missing policy before any test statistic.

## 8. Black-Box Uncertainty And Risk-Coverage

Use the five repeats to test whether disagreement predicts error without relying
on logprobs:

- deterministic-check-vector disagreement;
- judge-score dispersion;
- contradiction in refusal/action decisions;
- structured-output or tool-plan stability.

Evaluate the signal out of sample. Use a held-out scenario subset or
leave-one-scenario-out predictions to draw a **risk-coverage** curve: as uncertain
answers are withheld, does observed error decrease, and at what retained
coverage? Do not choose and evaluate an uncertainty threshold on the same rows.
Semantic clustering/entropy is a follow-up only if these existing signals are
insufficient.

## 9. Multiple Comparisons

Separate test families before running them:

- locked quantization-pair contrasts;
- locked training/architecture interactions;
- safety outcomes;
- exploratory metric screens.

Use Holm-Bonferroni for a small, predeclared family. Use false-discovery-rate
control only for explicitly exploratory batteries. Report effect sizes and
intervals beside adjusted p-values. Per-model leaderboards remain descriptive
unless their comparison survives the declared family correction.

## 10. Rank And Pareto Robustness

Bootstrap scenarios as clusters and recompute:

- Kendall rank agreement;
- top-k inclusion probability;
- Pareto membership probability;
- sensitivity to judge family;
- sensitivity to conditional versus unconditional quality;
- sensitivity to energy metric and served-failure policy.

Report point-estimate Pareto membership as a selection result, not a final
ordering. A model appearing on 51% of resampled fronts is not equivalent to one
appearing on 99%.

## 11. Metric-Contract Gate

Before claim-bearing analysis, one fixture must produce the same derived value
in `report.py`, `scripts/metrics.py`, documentation, and dashboard exports.
The 2026-07-10 correction lock resolved the known implementation defects:

- Friedman samples orient models over scenario blocks;
- measured MBU is distinct from the named dense-weight-stream-equivalent proxy;
- energy-per-success uses one aggregate denominator, while output-token energy
	has its own explicit field;
- KV-cache estimates use the configured dtype or an explicitly labelled
	FP16-equivalent fallback;
- safety membership uses secure class and lifecycle action-risk metadata;
- the model and condition identities freeze available runtime, lineage,
	architecture/training, sampler-policy, and prompt-template provenance.

`scripts/test-analysis-metrics.py`, `scripts/validate-analysis-schema.py`, and
`scripts/validate-model-lock.py` are the executable gate. Unknown architecture
or training metadata remains unknown and cannot support a corresponding
headline; passing the implementation fixture does not manufacture provenance.

No MBU, Wh/success, architecture, or training-regime headline is eligible until
its corresponding contract item passes.