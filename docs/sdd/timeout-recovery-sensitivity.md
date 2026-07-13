# SDD: Timeout Recovery Sensitivity Program

Status: Phase 5 timeout-sensitivity execution running from clean source `e35ef3f`; 2/2,100 rows observed at launch verification
Date: 2026-07-12
Source run: `full-chatok-core20-r5-ollama-20260705-150053`
Source bundle: `dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa`

## 1. User-Visible Outcome

After this program, an operator can determine whether ApprenticeOps' wall-clock timeout policy, rather than model capability alone, caused recoverable inference failures, and can adopt, hold, or reject a targeted longer-timeout profile using a pre-specified, reproducible decision rule without rewriting the original experiment.

## 2. Baseline And Non-Negotiable Boundaries

The completed source run remains immutable and primary:

- 152 models x 20 scenarios x 5 repetitions = 15,200 inference rows;
- 30,400 canonical judgements from 30,441 raw attempts;
- 41 failed judge parse attempts retained as retries;
- 208 DNF rows: 204 `DNF:timeout` and four `DNF:after_done_missing`;
- 1,452 `length` finishes, analyzed separately from timeout recovery;
- zero primary rows replaced, deleted, or relabeled;
- source bundle remains `claim_status=provisional` and cannot replace the frozen public paper source automatically.

The recovery condition is exploratory. It must not be merged into the primary run, used to conceal DNF or truncation rates, or generalized from the post-selected 21-model cohort to the full model population.

## 3. Root-Cause Model

### 3.1 Judge failures

The 41 judge failures are parse-failed attempts followed by exactly one structurally valid success for the same canonical key. The durable fix is canonical attempt reconciliation: one successful judgement per expected result/judge key, failed attempts retained as retry evidence, and multiple successful attempts rejected as ambiguous. No rejudging is required.

### 3.2 Inference DNF

All 208 DNF rows retained partial output and were judged by both declared judges. The evidence separates two mechanisms:

1. **Wall-clock censoring:** 204 calls reached their 120-202 second budget while producing output. Increasing only `timeout_s` can discriminate policy censoring from persistent runtime/model failure.
2. **Completion-frame transport defect:** four calls produced output but did not receive a terminal done frame. These remain a separate stratum and are not counted as timeout-policy recoveries.

No stalls or zero-output failures occurred. `length` is token-budget censoring, not wall-clock censoring, and is outside the treatment.

### 3.3 Recurrence

Timeout and reliability failures have appeared in prior ApprenticeOps runs and model cohorts. A tuple-only rerun would repair symptoms while conditioning on observed failure. The durable design runs the entire 20 x 5 matrix for every affected model so successful and failed parent tuples share the same treatment and provenance contract.

## 4. Tournament Of Options

| Option | Calls | Pros | Cons / Bias | Blast Radius | Durability | Verdict |
|---|---:|---|---|---|---|---|
| Keep existing partial outputs only | 0 | Immediate failure-inclusive evidence; already judged | Does not estimate timeout-policy effect | None | High for baseline reporting | Use as baseline sensitivity |
| Rerun only the 208 failed tuples | 208 | Cheapest compute | Conditions directly on observed failure; biased recovery rate | Low | Low | Reject for policy decision |
| Rerun all 2,100 rows for 21 affected models | 2,100 | Paired treatment within affected cohort; preserves successful controls | Cohort remains post-selected; about 2.4 days | Medium | High | **Selected** |
| Rerun all 15,200 rows | 15,200 | Population-wide comparison | Unnecessary multi-day cost; repeats 131 unaffected models | High | High | Defer unless targeted evidence is insufficient |
| Switch failures to llama.cpp | At least 100 | Tests a different runtime | Only 2/21 catalog-eligible and 1/21 staged; not same condition | Medium | Low for timeout question | Reject as recovery; optional future runtime study |

## 5. Treatment Contract

The sensitivity condition changes only the per-scenario wall-clock budget:

```text
timeout_s = min(600, max(300, round(parent_timeout_s * 2.5)))
```

The factor is an exploratory high-headroom treatment selected from the completed-run diagnosis: original failures occurred at 120-202 seconds while producing partial output, and slow 3-8B CPU models can require substantially more decode time at unchanged 400-700 token caps. A lower factor risks repeating censoring without discriminating the mechanism; a higher cap creates unnecessary resource exposure. The treatment is not itself evidence that 2.5x is optimal.

Everything else remains fixed and hash-bound:

- 21 affected models in source-roster order;
- all 20 source scenarios and five repetitions;
- temperature 0.7 and seeds 1-5;
- prompts, deterministic checks, max-token caps, context, memory, and strategy;
- Ollama 0.30.8 on the locked CPU/power/RAPL regime;
- exact model artifact digest per affected model;
- dedicated scenario, run-manifest, roster, and artifact-lock hashes;
- disk-bounded pull -> digest verify -> inference -> remove for models absent at launch.

A missing model may be pulled only when its resulting local digest exactly matches the source-bundle artifact lock before warmup or inference. A mismatched pre-existing or newly pulled model fails closed.

## 6. Prespecified Analysis Contract

### 6.1 Pairing and populations

Pair rows by `(model, scenario, rep)` within the fixed 21-model cohort. Analyze all 2,100 pairs, not only parent failures. Preserve these strata:

- parent `DNF:timeout` (204 rows);
- parent `DNF:after_done_missing` (four rows);
- parent completed rows (1,892 rows);
- parent `length` rows as a separate token-censoring descriptor.

The estimand is the timeout-policy effect within this post-selected affected-model cohort and fixed Core 20 task set. It is not a population-wide 152-model effect.

### 6.2 Primary outcome

Paired absolute change in `DNF:timeout` rate across all 2,100 rows:

```text
sensitivity timeout-DNF rate - parent timeout-DNF rate
```

Report absolute percentage-point change, relative reduction, transition counts (`DNF->complete`, `complete->DNF`, unchanged), and a 95% two-way cluster bootstrap interval.

### 6.3 Uncertainty

Use 10,000 deterministic bootstrap samples with analysis seed `20260712`. In each sample, resample the 21 models and 20 scenarios independently with replacement and retain all five repetitions for each sampled model-scenario cell. Compute paired deltas on the crossed resample. Report the percentile 2.5% and 97.5% limits. Also report exact fixed-matrix point estimates and per-model/per-scenario distributions; do not imply the interval represents an unobserved global model population.

### 6.4 Secondary outcomes

For all paired rows and separately by parent stratum:

- any DNF and successful completion rates;
- mean two-judge consensus score, failure-inclusive;
- deterministic-check score;
- wall time, p50 and p95;
- energy per row and energy per completed row;
- output tokens and finish reason;
- `after_done_missing` transitions, separate from timeout recovery;
- `length` rate, reported but not treated as timeout success.

No row is dropped because one condition failed. Missing sensitivity tuples, unresolved judge keys, competing successful judgements, artifact drift, source drift, or provenance mismatch fail the analysis gate.

### 6.5 Multiplicity and interpretation

The primary outcome is singular. Secondary outcomes are descriptive/non-inferiority guards; report all of them and do not promote isolated secondary p-values. Subgroup results are exploratory. No public paper claim changes until a separate analysis lock, deterministic gates, and both semantic judge families pass.

## 7. Prespecified Policy Decision

The sensitivity result yields one of three outcomes.

### Adopt targeted longer-timeout profile

All conditions must hold:

1. timeout-DNF absolute reduction is at least 5 percentage points within the affected cohort;
2. the 95% bootstrap interval for the paired timeout-DNF delta is entirely below zero;
3. the lower 95% interval for consensus judge-score delta is greater than -0.10 on the 1-5 scale;
4. the lower 95% interval for deterministic-score delta is greater than -0.02;
5. no model artifact, scenario, runtime, seed, prompt, judge-domain, persistence, or privacy gate fails;
6. median wall-time increase across all 2,100 rows is at most 15%;
7. mean energy per completed row increases by at most 25%;
8. `after_done_missing` and `length` are reported separately and not counted as timeout recoveries.

This decision authorizes only a targeted slow/affected-model profile. It does not authorize a universal 152-model default.

### Hold for broader validation

Use HOLD when timeout reduction is credible but any latency/energy/non-inferiority threshold is inconclusive, or when a policy for the full roster is desired. A universal default requires a separately pre-specified, non-failure-selected validation cohort or full-roster run.

### Reject

Reject when the timeout-DNF interval includes zero, the point reduction is below 5 percentage points, quality non-inferiority fails, or any integrity/provenance gate fails.

## 8. Phases, Wins, And Gates

| Phase | Name | Win | Gate | Rollback |
|---:|---|---|---|---|
| 0 | Architrave bootstrap and specification | One durable source of phase truth and pre-specified P6/P7 rules | Config/run validation + GPT-5.6-family and Claude 4.8 PASS | Remove additive Architrave artifacts and this SDD |
| 1 | Evidence lock | Immutable source bundle with retries reconciled | Bundle verify + privacy PASS | Discard additive bundle only |
| 2 | Failure diagnosis | Causes, cohort, and recovery options quantified | Analyzer hashes reconcile; independent count checks | Discard derived outputs |
| 3 | Pipeline hardening | Wrong judges, artifacts, manifests, retries, resumes, or outputs fail closed | Focused tests + full recovery gate + dual judge PASS | Revert hardening diff |
| 4 | Launch readiness | Clean committed source executes production preflight and emits zero rows | Exact contract paths/hashes; real-node preflight; clean provenance | Teardown power lock; remove staged checkout |
| 5 | Timeout sensitivity | 2,100/2,100 inference rows and exact authoritative judgement domain persisted | `run.meta.judge_identities` is present, valid, and exact; same-count substitution fails end-to-end; strict run report, bundle verify, privacy, no pending pushes | Stop/resume same run ID; never merge primary rows |
| 6 | Comparative analysis | Paired effects, uncertainty, costs, and residual failures quantified | Prespecified analyzer tests + analysis lock + dual judge PASS | Discard exploratory analysis outputs |
| 7 | Policy decision | Adopt/Hold/Reject recorded with evidence | Threshold evaluation + ADR/SDD update + claim audit | Keep current timeout policy |

## 9. Human And Operational Boundaries

No phase may push, publish, replace public claims, reserve a DOI, or mutate the
original run by default. On 2026-07-13 the user explicitly authorized only the
dedicated timeout-sensitivity source, smoke, and per-run result branches with
per-model commits. That
approval does not authorize pushing `main`, merging an experiment branch,
mutating parent evidence, or changing paper claims. A clean committed source
identity is required before Phase 4 can close; creating or pushing any other
commit remains a maintainer action unless separately authorized. Phase 5 is a
long-running, reversible experiment and may start only after Phase 4 passes and
the source identity is clean.

Phase 4 must also prove the recovery producer writes non-empty, unique
`run.meta.judge_identities` objects in the exact `{judge_backend, judge_model}`
shape with cardinality equal to `judges`. A preflight fixture and the eventual
real recovery run must reject a same-count substituted judge set. Historical
parent evidence lacks this field and is intentionally validated through the
explicit legacy `--judge` path; that legacy PASS is not evidence that the modern
authoritative path engaged.

## 10. Required Evidence

- `.architrave/runs/timeout-recovery-20260712/` mirrors intake, tournament, plan, ledger, gates, judges, and runtime evidence.
- `.architrave/learning/repo-profile.md` records current source-of-truth paths and commands.
- `data/completed-runs/<run>-<bundle-id>/` remains the immutable parent.
- Tracked recovery roster, scenario contract, run manifest, and artifact lock must hash-match analyzer output.
- Every phase transition updates both `phase-ledger.md` and `summary.json` before the next phase begins.
