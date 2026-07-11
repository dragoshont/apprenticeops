# SLM Metrics and Correlation Review - 2026-07-10

Status: source-backed research and code audit. This is **not a benchmark result**,
not a paper claim, and not a request to mutate the active run. The provisional
screen below used only completed, thesis-eligible models available during the
still-running `full-chatok-core20-r5-ollama-20260705-150053` run. All numbers must
be recomputed from the final audited artifact.

## 1. Executive verdict

**Yes, ApprenticeOps should look for additional SLM patterns, but not by adding a
large undisciplined correlation matrix.** The existing 94-model analysis already
covers most obvious marginals: size, quality, safety, speed, energy, truncation,
reasoning overhead, family-controlled quantization, judge agreement, Pareto
membership, and the Turbo/wave confound. Repeating those analyses over 152 tags
would make a larger table, not necessarily a stronger result.

The next useful layer is interaction-aware:

1. **Reliability across repeated attempts** (`pass^k`-style all-attempt success),
   not only mean quality and a majority-consistency score.
2. **Task-by-model interactions**, especially where increasing parameter tier
   stops helping or reverses.
3. **Within-lineage quantization effects by task type**, rather than global
   `Q4` versus `Q8` averages.
4. **Black-box uncertainty from repeat disagreement**, followed by risk-coverage
   analysis.
5. **Tokenizer and output-budget fairness**, because equal token caps are not
   equal character or semantic budgets.
6. **Total versus active model economics** for MoE and hybrid models, while
   keeping total RAM footprint separate from active compute.
7. **Rank and Pareto stability under scenario resampling**, rather than treating
   point-estimate membership as permanent.

Before those analyses, four metric/statistics defects need repair: the Friedman
matrix orientation, conflicting MBU definitions, conflicting energy-per-correct
estimators, and an FP16 KV-cache estimate applied to a live `q8_0` KV-cache
runtime.

## 2. What was audited

### 2.1 Repository sources

- [`run.py`](../../run.py): result-row capture, Ollama metadata, runtime policy,
  retries, strategy fields, and sampler behavior.
- [`report.py`](../../report.py): model summaries, confidence intervals, Friedman
  test, safety gate, systems metrics, and report prose.
- [`scripts/metrics.py`](../../scripts/metrics.py): row-level derived metrics and
  consistency summaries.
- [`docs/TELEMETRY.md`](../TELEMETRY.md): metric contract and formulas.
- [`docs/STATISTICS.md`](../STATISTICS.md): current inference and missingness plan.
- [`docs/PAPER.md`](../PAPER.md): locked H1-H7 and current CEOps extensions.
- [`docs/DEEP-ANALYSIS-DRAFT.md`](DEEP-ANALYSIS-DRAFT.md): prior 94-model
  exploratory analysis and its corrections.
- [`data/models.lock.jsonl`](../../data/models.lock.jsonl) and
  [`data/model.schema.json`](../../data/model.schema.json): thesis eligibility and
  static model covariates.
- Live result and judge rows for the active run, read-only.

### 2.2 Primary online sources

| Source | Status | Relevant evidence | ApprenticeOps consequence |
|---|---|---|---|
| [Small Language Models: Survey, Measurements, and Insights](https://arxiv.org/abs/2409.15790) | arXiv v3, 2025 | Defines the SLM range as roughly 100M-5B and analyzes architecture, training data, training algorithms, latency, and memory together. | Parameter count alone is an incomplete explanatory variable. Add architecture/training/lineage covariates before multivariate claims. |
| [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | Position paper, arXiv v2, 2025 | Argues SLMs fit repetitive specialized agent tasks and heterogeneous agents are natural where general conversation is still needed. | Analyze class-specific champions and routing potential, not only one global winner. Treat this as motivation, not empirical proof. |
| [The case for 4-bit precision](https://arxiv.org/abs/2212.09720) | Inference-scaling study | Finds 4-bit generally strong on the model-bits/zero-shot trade-off and shows that equal total bits do not imply equal accuracy. | Use exact within-lineage quantization pairs; never aggregate unrelated Q4 and Q8 models as if quantization were randomized. |
| [Can Compressed LLMs Truly Act? / ACBench](https://arxiv.org/abs/2505.19433) | ICML 2025 poster | Reports task-sensitive compression effects: 4-bit largely preserves workflow/tool use in its setting but degrades real-world application accuracy more. | Estimate `quantization x task` interactions and ranking correlation, not one global quantization coefficient. |
| [Quantization Meets Reasoning](https://arxiv.org/abs/2505.11574) | arXiv v4, 2026 | Finds low-bit reasoning degradation can emerge early and cascade, with method/execution errors affected more than high-level concepts in the tested math setting. | Use `det_detail` to localize which checks fail first within Q4/Q8 pairs. Do not generalize its math result directly to ops. |
| [Sustainable LLM Inference for Edge AI](https://arxiv.org/abs/2504.03360) | arXiv preprint, 2025 | Evaluates 28 Ollama quantized models on Raspberry Pi across accuracy, latency, memory, and hardware-measured energy. | Keep measured energy and latency beside quality; compare configurations on a Pareto set rather than one efficiency proxy. |
| [Stop Overthinking](https://arxiv.org/abs/2503.16419) | TMLR 2025 survey | Longer reasoning can add verbose/redundant computation; efficiency methods act at model, output, or prompt level. | Keep thinking length, answer length, timeout, and truncation separate. Test whether reasoning helps particular tasks after reliability costs. |
| [BFCL: From Tool Use to Agentic Evaluation](https://dl.acm.org/doi/10.5555/3780338.3782270) | ICML 2025 | Uses AST-based evaluation, serial/parallel calls, abstention, and stateful multistep evaluation; finds long-horizon and dynamic behavior remain hard. | One structured-restart scenario is not enough to claim tool capability. Build a small deterministic tool-robustness pack after the current run. |
| [On the Robustness of Agentic Function Calling](https://arxiv.org/abs/2504.00914) | TrustNLP at NAACL 2025 | Tests natural query variation and expanding a toolkit with semantically similar tools. | Add paraphrase and distractor-tool perturbations; report invariance, not just clean-case accuracy. |
| [tau-bench](https://arxiv.org/abs/2406.12045) | arXiv, 2024 | Introduces `pass^k` for repeated-trial reliability; reports large degradation when success must hold repeatedly. | Add all-five success alongside single-run success. Means and majority consistency hide operational wobble. |
| [Semantic Uncertainty](https://arxiv.org/abs/2302.09664) | ICLR 2023 Spotlight | Clusters semantically equivalent generations before computing uncertainty; semantic entropy predicts accuracy better than lexical baselines in its QA setting. | Start with judge/check-vector disagreement already available; add semantic clustering only as a follow-up, not a new dependency by default. |
| [SelfCheckGPT](https://arxiv.org/abs/2303.08896) | EMNLP 2023 | Uses disagreement among black-box stochastic samples as a factuality signal without model probabilities. | Five repeats can support black-box uncertainty screening even for Ollama models without logprobs. |
| [Language Models (Mostly) Know What They Know](https://arxiv.org/abs/2207.05221) | arXiv, 2022 | Shows self-evaluation and sample-conditioned confidence can be calibrated in tested settings, but generalization to new tasks is difficult. | A later confidence-elicitation experiment is defensible, but it must be calibrated on held-out ops tasks. It is not available from the current baseline rows. |
| [HELM](https://arxiv.org/abs/2211.09110) | TMLR 2023 | Uses dense scenario coverage and multiple metrics so accuracy does not hide calibration, robustness, or efficiency trade-offs. | Keep axes separate and state underrepresented classes; do not collapse everything into one score. |
| [Judging LLM-as-a-Judge](https://arxiv.org/abs/2306.05685) | NeurIPS Datasets and Benchmarks 2023 | Names position, verbosity, self-enhancement, and limited-reasoning biases. | Continue two-judge plus deterministic checks; explicitly model answer length when auditing judge residuals. |
| [The Benchmark Lottery](https://arxiv.org/abs/2107.07002) | arXiv, 2021 | Shows rankings can change with benchmark task choice. | Bootstrap scenarios and report top-k/Pareto inclusion frequency plus Kendall rank stability. |
| [The Efficiency Misnomer](https://arxiv.org/abs/2110.12894) | arXiv, 2022 | Warns that efficiency indicators can conflict and incomplete cost reporting yields partial conclusions. | Preserve TTFT, decode, wall time, memory, and energy as distinct metrics. |
| [Power Hungry Processing](https://arxiv.org/abs/2311.16863) | FAccT 2024 | Measures energy per inference and finds architecture/purpose matter even after controlling for parameter count. | Model energy with size and architecture/family covariates; do not infer energy from parameters. |
| [Mamba](https://arxiv.org/abs/2312.00752) and [LLM in a Flash](https://arxiv.org/abs/2312.11514) | arXiv / ACL 2024 | Motivate hardware-aware analysis of state-space/sparse designs and data movement under constrained memory. | Separate total stored bytes, resident bytes, active compute, and measured memory traffic for hybrid/MoE models. |

## 3. Current metric surface

The capture is already sufficient for a much stronger post-run analysis. A new
inference run is not required for the first six priorities below.

| Axis | Captured fields | Existing derived surface | Main gap |
|---|---|---|---|
| Quality | `det_score`, `det_detail`, two judge rows, criteria/evidence | Mean det, mean judge, percent-of-ceiling | Hierarchical uncertainty and unconditional quality when inference fails |
| Safety | guard/secure checks, destructive-risk lifecycle metadata | Refusal/check rates and a guard verdict | Report safety by action/stakes; current report verdict only gates `guard` |
| Reliability | five reps, finish reason, DNF, length, blank, retry/stall phases | DNF count, length, majority consistency | `pass^k`, all-safe probability, competing failure outcomes, lower-tail risk |
| Latency | TTFT, prefill, decode, wall, jitter, progress trace | Median tok/s, TPOT, chars/s | Quantiles by scenario and decomposition of timeout risk |
| Energy/fit | RAPL, idle, thermal, RSS, swap, faults, measured bandwidth | Wh/task, J/token, tok/s/W, MBU | Canonical formulas; active-vs-total MoE accounting; KV dtype capture |
| Model identity | exact params, quant, family, context, heads, blocks, experts, digest | Static lock + raw runtime metadata | Freeze one post-run model dimension; add release date, lineage, architecture subtype, active params |
| Prompt/policy | exact prompt/hash, context size, token counts, model parameters | Tokenizer bloat, prompt sizes | Chat-template hash and normalized effective sampler policy |
| Experimental | memory context, strategy, adapter/runtime, reset/environment | Faceted reporting | Explicit interaction models; never pool conditions silently |

## 4. Analyses already done - do not duplicate them blindly

[`docs/DEEP-ANALYSIS-DRAFT.md`](DEEP-ANALYSIS-DRAFT.md) already investigates:

- fixed output caps as the dominant truncation mechanism;
- timeout as a speed-by-verbosity/thinking interaction;
- disagreement among size, quality, safety, speed, and energy proxies;
- within-bracket size effects;
- descriptive model archetypes;
- 11 family-controlled Q4/Q8 pairs;
- reasoning-versus-instruct and paired grounding hypotheses;
- rep-to-rep variance and scenario discrimination;
- underpowered hybrid/MoE efficiency hints;
- tokenizer-independent throughput and resident footprint;
- invalid author difficulty labels and confounded raw grounding means;
- model metadata, family skew, and tool-capability flags;
- rank robustness across mean score, mean win rate, Bradley-Terry, and
  deterministic checks;
- action-specific safety failures;
- judge verbosity/style residuals;
- the Turbo/RAPL/wave confound and its correction.

The new 152-tag run should **replicate, refine, or falsify** those findings under
the locked regime. It should not quietly present them as newly discovered.

## 5. Metric and statistics defects to fix first

### 5.1 Friedman test orientation is wrong for the stated claim

In [`report.py`](../../report.py), the matrix is built as
`[scenario][model]` and passed as `friedmanchisquare(*mat)`, but SciPy treats each
outer vector as a treatment. The resulting test compares scenarios across models,
while the report labels the result as "models differ."

The matrix for that claim must be `[model][scenario]`:

```python
mat = [[mean(md[model][scenario]) for scenario in common]
       for model in models]
```

This needs a regression test with a synthetic dataset where only model effects
exist and another where only scenario effects exist.

### 5.2 The row bootstrap ignores the crossed design

`report.py.boot_ci()` resamples individual rows as if the 20 scenarios and five
repeats were exchangeable independent observations. They are nested/crossed:
repeats share one scenario, and every model sees the same scenarios.

Use:

- scenario-cluster bootstrap for a per-model generalization interval;
- model-cluster bootstrap for tier/family summaries;
- paired scenario/repetition resampling for model or condition contrasts;
- a crossed model/scenario analysis for explanatory covariates.

The row bootstrap may remain as a descriptive sampling interval, but it must not
be presented as the only uncertainty for generalization over ops tasks.

### 5.3 `MBU` has two incompatible meanings

- `report.py` and `TELEMETRY.md` define MBU as measured
  `mean(membw.peak_mb_s) / calibrated_peak_mb_s`.
- `scripts/metrics.py` defines it as
  `model_size_bytes * decode_tok_s / calibrated_peak`, capped at `1.5`.

The second quantity assumes every stored byte is streamed for every token. It is
not utilization for sparse MoE or hybrid/SSM models. Keep the measured quantity
as **MBU**. Rename the second to something explicit such as
`dense_weight_stream_equivalent_ratio`, and never use it as an architecture-
neutral utilization value.

### 5.4 `energy per correct` also has two meanings

- `report.py`: `mean(energy_wh) / mean(det_score)`.
- `scripts/metrics.py`: per-row `energy_wh / det_score`, omitting rows where
  `det_score == 0`, then averaging those ratios.

The latter creates survivorship bias and a different estimand. Canonicalize one
aggregate formula and name it honestly. Because `det_score` is fractional, the
current quantity is **Wh per deterministic-check-equivalent**, not literally Wh
per correct answer. A separate judged-success energy metric requires a locked
success threshold and must count failed/DNF attempts in the energy numerator.

### 5.5 KV-cache estimate assumes FP16, but the live runtime uses Q8

`scripts/metrics.py` multiplies KV elements by two bytes. The active Ollama
service reports:

```text
OLLAMA_FLASH_ATTENTION=1
OLLAMA_KV_CACHE_TYPE=q8_0
```

The estimate is therefore roughly two times the configured KV payload before
allocator/runtime overhead. Capture `env.ollama_kv_cache_type` and calculate from
the actual dtype; otherwise label the field `kv_cache_fp16_equivalent_mb`.

### 5.6 Majority consistency can reward consistent failure

Current `pass_consistency` bins `det_score >= 0.5`, finds the majority outcome,
and reports the fraction matching it. A model that fails identically five times
can score `1.0` consistency. Keep repeatability and correctness as separate axes:

- `repeat_agreement`: did repetitions produce the same outcome?
- `pass_1`: probability one attempt meets the scenario success rule;
- `pass_k`: probability all `k` attempts meet it;
- `all_safe_k`: no unsafe action in any of `k` attempts.

### 5.7 The report safety gate covers `guard`, not all safety scenarios

`report.py.safety_fail_for()` filters only `class == "guard"`, while the paper's
safety analysis combines `guard` and `secure`. A selection verdict can therefore
pass despite a repeated high-stakes `secure` failure. Define the gate from
scenario lifecycle metadata (`destructive_risk`, forbidden actions) or an
explicit locked safety set, not a single class string.

### 5.8 Packaged inference policy is a model-level confound

The Ollama path pins temperature, seed, output cap, and context size, but inherits
each model's Modelfile `top_p`, `top_k`, repeat penalty, and stop directives.
Among the first 105 observed models, the audit found:

- 28 distinct raw Modelfile parameter strings;
- 12 distinct parsed numeric sampler signatures;
- 75 models with one or more packaged stop directives.

This is valid when the estimand is the **deployable package**, but not when a
claim is phrased as an isolated weights, parameter-count, or quantization effect.
The final model dimension should carry a sampler-policy hash. A small sensitivity
panel should compare packaged defaults against one normalized policy.

Ollama `/api/show` also returns a model chat template, but `run.py` does not store
its hash. Add `ollama.chat_template_sha256` for future runs or sensitivity panels.

### 5.9 Static lock metadata is incomplete; runtime metadata is much better

All 152 active tags exist in `models.lock.jsonl`, and every tag has a parameter
count. However, the lock currently has:

- `architecture=unknown` for 142/152 tags;
- unknown training type for 78/152;
- missing artifact size for 64/152;
- missing context length for 142/152;
- missing Ollama digest for 142/152.

The live rows rescue most of this: all first 105 observed models had exact
parameter count, quantization, family, native context, tokenizer, blocks, and
embedding dimensions; 104/105 had size and digest. After completion, build one
validated `model_dimension` table from the raw runtime facts plus reviewed
lineage/training metadata. Do not regress against the sparse lock columns alone.

### 5.10 Token counters need a validity gate

The provisional thesis subset contained 22 rows with `input_tokens == 0`.
Tokenizer-bloat code must exclude non-positive counters and report their causes
by finish reason/model. Zero should not become an infinite ratio or silently set
the per-scenario denominator.

### 5.11 Generated report prose still names the wrong RAPL domain

The locked regime uses `rapl:package-0`, but `report.py` output prose still says
the primary source is `psys`. The row field is authoritative. Generated prose
must derive the source from the run or say "see `power.source`" rather than
hard-code a historical regime.

## 6. Provisional signal screen - not for publication

The screen used 92 completed, thesis-eligible models (`92 x 20 x 5 = 9,200`
inference tuples) available at the time of review. Each tuple had a numeric judge
aggregate. The run was still active; model ordering and the unfinished tail make
this a **hypothesis screen only**.

### 6.1 Model-level rank correlations

| Pair | Spearman `rho` | Reading |
|---|---:|---|
| parameters vs deterministic score | +0.584 | Size helps globally, but does not isolate family/training/task effects. |
| parameters vs judged score | +0.733 | Strong global association; still observational and portfolio-confounded. |
| parameters vs decode speed | -0.856 | The systems cost of size is stronger than its deterministic-quality association. |
| artifact size vs energy | +0.752 | Supports measured energy modeling, not an energy-from-size shortcut. |
| artifact size vs speed | -0.909 | Weight footprint is a strong CPU decode predictor in this regime. |
| parameters vs length finish | -0.157 | Truncation is not a simple size effect. Budget/style/task dominate. |
| parameters vs DNF | +0.190 | Weak global association; timeout mechanism needs speed and task policy. |
| speed vs DNF | -0.312 | Direction is plausible, but DNF is sparse and model/task dependent. |
| chars/token vs length finish | -0.085 | No useful global tokenizer explanation without model/scenario controls. |
| chars/token vs judge-minus-det residual | -0.216 | Weak hint of style/tokenizer bias; insufficient as a claim. |

The negative association between repeat instability and mean score was large
(`rho` about `-0.8`), but bounded-score floor/ceiling effects mechanically couple
means and variances. Do not present it as "uncertainty predicts quality" without
a calibrated held-out risk-coverage analysis.

### 6.2 Repeated success reveals a reliability gap

Using the strict provisional rule `det_score == 1`:

- one-draw full-check pass rate: **30.0%**;
- all-five full-check success: **12.7%**;
- model-scenario groups: `1,840`.

| Full-pass repetitions out of five | Model-scenario groups |
|---:|---:|
| 0 | 865 |
| 1 | 278 |
| 2 | 181 |
| 3 | 177 |
| 4 | 105 |
| 5 | 234 |

This is the clearest new analysis candidate. A model that succeeds once is not
the same deployment as one that succeeds every time. The final analysis must use
scenario-specific success rules, not assume `det_score == 1` is equally meaningful
for every scenario.

### 6.3 Tier gains depend on task

Provisional deterministic means by parameter tier:

| Class | Scenarios | T1 | T2 | T3 | T4 | T5 |
|---|---:|---:|---:|---:|---:|---:|
| capacity | 3 | .543 | .607 | .695 | .718 | .716 |
| detect | 1 | .742 | .787 | .880 | .924 | .882 |
| diagnose | 5 | .589 | .691 | .714 | .744 | .688 |
| expand | 1 | .478 | .700 | .783 | .743 | .750 |
| guard | 1 | .366 | .435 | .547 | .520 | .504 |
| monitor | 1 | .641 | .869 | .977 | .939 | .935 |
| secure | 4 | .588 | .609 | .658 | .638 | .718 |
| test | 3 | .619 | .687 | .799 | .789 | .876 |
| upgrade | 1 | .569 | .696 | .793 | .809 | .769 |

The shape is not a single scaling curve. T5 is lower than T4 on detect,
diagnose, guard, monitor, and upgrade in this partial subset, while it improves
secure and test. This could reflect training/family composition rather than a
true tier effect. It justifies a task interaction model.

Five of nine class labels contain only one scenario. Class-level p-values would
therefore be pseudo-replication. Analyze those as named scenarios until the class
has sufficient independent tasks.

### 6.4 Capability metadata is not behavior

Declared tool capability did not produce a stable tier-controlled pattern on the
single structured-restart scenario. It was slightly negative at T1, positive at
T2-T4, and reversed in the small T5 non-tool group. This is exactly why BFCL uses
multiple call shapes, abstention, and stateful evaluation. Treat
`ollama.capabilities` as metadata, not a score.

### 6.5 Training-regime analysis is blocked by metadata, not rows

Only two of the 92 screened models were labeled `reasoning` in the current lock,
while 46 were `unknown`. Any current reasoning-vs-instruct comparison would mostly
measure annotation completeness. Repair training regime and lineage before
repeating the older H4 analysis.

## 7. Recommended post-run analysis contract

### Priority 0 - repair and freeze the measurement contract

1. Fix the Friedman orientation and add synthetic regression tests.
2. Canonicalize MBU and energy-per-success formulas and field names.
3. Capture/use actual KV-cache dtype; correct the Q8 estimate.
4. Define safety membership and per-scenario success rules explicitly.
5. Freeze the post-run model dimension from runtime metadata plus reviewed
   lineage/training fields.
6. Rejudge parse failures and classify zero token-counter rows.

**Gate:** the same fixture produces one unambiguous value for every derived
metric in `report.py`, `scripts/metrics.py`, docs, and dashboard exports.

### Priority 1 - analyses available from the completed run

#### A. Conditional and unconditional quality

Report both:

- quality conditional on a usable completion;
- unconditional deployment quality, assigning the locked failure outcome to
  DNF/blank responses rather than dropping them.

Keep `stop`, `length`, blank-stop, timeout, and stream-finalization failure as
separate competing outcomes.

#### B. Repeated-attempt reliability

For each model and scenario, report:

- `pass_1`;
- `pass_5` or the all-five analogue justified by the success rule;
- `all_safe_5`;
- judge-score/check-vector disagreement across repetitions;
- worst-repetition and lower-tail score.

Do not replace mean quality with these metrics; show reliability beside it.

#### C. Crossed task/model analysis

At minimum, analyze model-scenario aggregates with scenario effects and
family-aware uncertainty. A target explanatory form is:

$$
y_{msr} = \beta_0 + \beta_1 \log(P_m) + \beta_2 Q_m +
\beta_3 T_m + \beta_4 A_m + \beta_5 X_s +
\beta_6(Q_m \times X_s) + u_{family(m)} + v_s + \epsilon_{msr}
$$

where $P_m$ is parameter count, $Q_m$ quantization, $T_m$ training regime,
$A_m$ architecture, $X_s$ task/scenario properties, $u$ a family effect, and
$v$ a scenario effect. The exact likelihood must match the outcome: binary for
hard safety/pass rules, ordinal or carefully averaged for judge scores, and
continuous/log scale for latency/energy.

This is explanatory association, **not causal attribution**. Model families were
not randomized across size, quantization, or training.

#### D. Exact quantization-pair interactions

Reuse only verified same-lineage Q4/Q8/F16 pairs. Pair on scenario and repetition,
then report deltas for:

- deterministic and judged quality;
- exact check families from `det_detail`;
- `pass_5` and safety;
- length/DNF/blank outcomes;
- decode, memory, and energy.

Correct the planned family of pairwise tests (Holm for a small locked family; FDR
only for explicitly exploratory batteries). Report effect sizes and intervals,
not p-values alone.

#### E. Rank and Pareto stability

Bootstrap scenarios as clusters and recompute:

- Kendall rank agreement;
- top-k inclusion probability;
- Pareto membership probability;
- sensitivity to judge family;
- sensitivity to unconditional quality and energy metric choice.

A model on 51% of bootstrap Pareto fronts is not equivalent to one on 99%, even
if both appear on the point-estimate front.

#### F. Black-box uncertainty and risk-coverage

Begin without embeddings or a new model:

- entropy/disagreement of deterministic check vectors;
- judge-score distribution across repeats;
- contradiction in safety/action decisions;
- lexical/structured-output stability for JSON/tool scenarios.

Learn an uncertainty threshold on one subset, then evaluate on held-out scenarios:
as uncertain cases are rejected, does error fall, and at what coverage? Only then
consider semantic clustering/entropy as a second method.

#### G. Tokenizer and budget fairness

For each model/scenario:

- input tokens per prompt character;
- output characters per token;
- effective character budget at the scenario token cap;
- length probability conditional on scenario, family, and model size;
- TTFT conditional on input token count and parameter count.

The provisional global tokenizer correlations were weak or counterintuitive,
which is evidence to control confounds, not evidence that tokenization is
irrelevant.

#### H. Lower-tail deployment quality

Means can hide catastrophic misses. Report per model:

- worst named safety/action scenario;
- mean of the worst three scenarios;
- lower confidence bound under scenario bootstrap;
- failure concentration by action stakes.

Do not merge this into one opaque utility score. Use it as a deployment gate or
separate risk axis.

### Priority 2 - small targeted sensitivity runs

These should start only after the full baseline run is audited.

1. **Sampler-policy panel:** 8-12 representative SLMs, packaged defaults versus
   one normalized `top_p/top_k/repeat_penalty/stop` policy.
2. **Tool robustness pack:** single call, parallel call, no-call/abstain,
   semantically similar distractor tools, paraphrase, malformed arguments, and
   short stateful sequences. Use AST/schema/state validation, not prose judging
   alone.
3. **Logprob/calibration panel:** use `llama_cpp_server` on a representative
   subset to relate token margins/logprob summaries to correctness and
   repeat-disagreement.
4. **MoE/hybrid panel:** add reviewed active-parameter metadata and compare total
   footprint, resident footprint, active compute, measured memory traffic,
   latency, and energy at matched quality.
5. **Confidence elicitation panel:** ask for a probability or abstention in a
   format calibrated on development scenarios, then test risk-coverage on held-
   out scenarios.

## 8. Analyses to reject or defer

- **Reject:** one giant raw correlation heatmap over all rows. It violates the
  repeated/crossed design and multiplies false discoveries.
- **Reject:** global Q4 versus Q8 means across unrelated families.
- **Reject:** class-level inference for classes represented by one scenario.
- **Reject:** native context length versus quality as a capability claim; the run
  fixes effective context at 8,192.
- **Reject:** `tools_capable` or `thinking_capable` as observed behavior.
- **Reject:** MBU computed from total stored bytes for sparse/hybrid models.
- **Reject:** causal wording for parameter, family, architecture, or training
  coefficients in this observational roster.
- **Defer:** semantic entropy requiring an external NLI/embedding model until
  check/judge disagreement proves insufficient.
- **Defer:** architecture-wide claims until non-dense families are numerous
  enough to separate architecture from IBM/Granite training effects.

## 9. Phase ledger

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 0 | Metrics/code/literature review | completed | Audit current capture, formulas, prior analyses, primary sources, and partial signal. | Sources verified; no runtime mutation; recommendations mapped to fields. | This document. |
| 1 | Measurement-contract repair | not-started | Fix formulas/tests, success/safety rules, metadata dimension, and generated prose. | Unit fixtures plus `report.py`/`metrics.py` agreement. | Awaiting review. |
| 2 | Final-run integrity audit | not-started | Strict run report, row audit, rejudge parse failures, freeze analysis dataset. | Expected rows/judges/models, hashes, no unexplained gaps. | Run still active. |
| 3 | Primary SLM analysis | not-started | Reliability, crossed effects, quant pairs, rank/Pareto stability, tokenizer fairness, lower-tail risk. | Locked analysis script reproduces tables/figures from final artifacts. | Not started. |
| 4 | Sensitivity experiments | not-started | Sampler, tools, logprobs, MoE/hybrid, confidence elicitation. | Separate preregistered run IDs and reliability gates. | Not started. |

## 10. Recommended decision

Approve **Phase 1 only after reviewing this audit**. Do not modify the active run.
When the run completes, Phase 2 should freeze a clean analysis dataset before any
new paper prose is written. Phase 3 should prioritize repeated-attempt reliability
and task-by-model interactions; those are the strongest genuinely new patterns
supported by both the current data shape and the SLM/agent-evaluation literature.
