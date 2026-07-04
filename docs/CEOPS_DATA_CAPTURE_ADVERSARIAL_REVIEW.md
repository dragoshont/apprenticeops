# CEOps Data-Capture Adversarial Review

Status: adversarial review, created 2026-07-04. This is a **pre-long-run gate**
for the `llama_cpp` path. It asks whether the current rows capture enough signal
to justify a weeks-long run, and where public practice or `llama.cpp` itself says
we are leaving useful evidence behind.

## Executive Verdict

**Do not launch the weeks-long all-model run yet.** The provenance defect is fixed
for future launches (`SYNC_MODE=origin`, `env.harness_source_dirty=false` in the
two-model smoke). The first two implementation slices also fix the major
direct-`llama.cpp` telemetry gaps and exact prompt/message capture for clean R=1
smokes, but we still need a clean R=5 mini-wave before promoting this path to
canonical long-run status.

The current capture is strong enough for:

- row/judge/persistence integrity;
- deployment identity and source provenance;
- reset-state evidence;
- RAPL power, thermal, CPU frequency, memory bandwidth, disk/network rates;
- full model completions and judge evidence.

The original direct-`llama.cpp` adapter was not strong enough for a canonical
weeks-long systems run because:

1. `llama_cpp` generation is captured through `subprocess.run()`, so stdout is
   buffered. This loses true time-to-first-token, per-chunk timing, and jitter.
2. The sampler is not attached to the `llama.cpp` child process, so child RSS,
   threads, page faults, and context-switch fields are present but empty.
3. Token counts for `llama_cpp` rows are character estimates, not tokenizer- or
   runtime-reported counts.
4. `llama.cpp` exposes structured benchmark/perf metadata (`llama-bench`,
   internal timings, cache/thread/backend settings) that we are not ingesting.
5. Activations and dynamic expert routing are not exposed by the normal CLI path;
   collecting them would require custom instrumentation and is outside this
   benchmark's current claim.

> **Scope honesty:** this review does not say the last rows are useless. It says
> they are **deployment-plumbing evidence**, not yet the final measurement shape
> for a weeks-long canonical systems run.

## Implementation Update

Commit `2575ec5` implements the first remediation slice:

- streams `llama.cpp` stdout/stderr instead of buffering with `subprocess.run()`;
- records TTFT, multi-point `progress_trace`, and decode chunk jitter;
- parses `llama.cpp` prompt/eval token counts and timing from `--perf` stderr;
- records OpenTelemetry GenAI scalar fields such as provider, output type,
   response model, and stream mode;
- captures per-child max RSS, page faults, context switches, and CPU time with
   `os.wait4()`;
- emits per-model `llama-bench -o jsonl` sidecars and records their hashes.

Clean dashboard smoke
`llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-190623`
validated the implementation from `origin/main`:

| Check | Result |
|---|---|
| Source provenance | PASS: `env.harness_git=2575ec5`, `env.harness_source_dirty=false`. |
| Rows | PASS: `12/12` inference rows, `24/24` judged rows. |
| Quality gate | PASS: `report-run-quality.py` found `strict_failures=0`. |
| Streaming timing | PASS: TTFT, prefill, decode jitter, and multi-point `progress_trace` populated for `12/12` rows. |
| Token source | PASS: `gen_ai.usage.token_source=llama_cpp_timing`. |
| Process telemetry | PASS: row-level max RSS, minor faults, and context switches populated for `12/12` rows. |
| Bench sidecar | PASS: `llama_cpp.bench.returncode=0`, `llama_cpp.bench.rows=2`, and bench SHA present. |
| Persistence | PASS: clean persistence; experiment branch pushed and finalized at `b8146c3`. |

## Deep Runtime-Capture Addendum

The first telemetry slice fixed the subprocess adapter, but a later source review
found that `llama-server` exposes more data than `llama-completion`. See
`docs/CEOPS_CPP_MLX_CAPTURE_RESEARCH.md` for the source-backed comparison.

The key additional fields are token IDs, per-token top logprobs/probabilities,
normalized generation settings, `tokens_cached`, `tokens_evaluated`,
`tokens_predicted`, `truncated`, `stop_type`, `/props`, `/metrics`, and slot/cache
state. These matter for optimization, cache analysis, and future distillation.

Implementation update: commit `fcf1f44` adds `INFERENCE_RUNTIME=llama_cpp_server`
as a distinct adapter. It starts `llama-server` per model, captures `/tokenize`,
`/props`, `/slots`, `/metrics`, and native `/completion` probability data, stores
the full payload in `*.llama-server.json` sidecars, and stamps row summaries plus
sidecar hashes.

Smoke validation: `llama-server-smoke-20260704-232755` passed strict run-quality
and `audit-run` (`6/6` rows, `12/12` judged rows, no DNF, no zero-output stalls).
Every row had server sidecar hashes, prompt token counts, logprob summaries,
metrics deltas, and GGUF artifact metadata. The run used a `64` token cap and all
rows ended as `length`, so it validates capture plumbing rather than task quality.

The canceled R=5 run
`llama-cpp-evidence-5-strategy-pilot-6-none-baseline-llama_cpp-20260704-194603`
stopped at `3/150` inference rows and must remain diagnostic only.

Commit `8641e33` implements the second remediation slice for reproducibility and
future fine-tuning/distillation data:

- exact serialized prompt capture: `prompt.full`, `prompt.sha256`, and
   `prompt.user_content`;
- structured OpenTelemetry-style content: `gen_ai.system_instructions`,
   `gen_ai.input.messages`, and `gen_ai.output.messages`;
- scenario/reference hashes: context, question, deterministic checks, gold answer,
   and judge rubric hashes;
- distillation scaffolding: `distill.input_messages`, `distill.output_message`,
   `distill.messages`, reference answer/source/hash, and output hash;
- explicit capture policy fields: `prompt.capture.enabled` and
   `prompt.capture.policy`.

Clean dashboard smoke
`llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-194150`
validated the prompt/distillation capture from `origin/main`:

| Check | Result |
|---|---|
| Source provenance | PASS: `env.harness_git=8641e33`, `env.harness_source_dirty=false`. |
| Rows | PASS: `12/12` inference rows, `24/24` judged rows. |
| Field count | PASS: `222` top-level raw fields. |
| Prompt capture | PASS: `prompt.full`, `prompt.sha256`, `gen_ai.input.messages`, and `gen_ai.system_instructions` populated for `12/12` rows. |
| Output capture | PASS: `gen_ai.output.messages` and `distill.output_sha256` populated for `12/12` rows. |
| Distillation data | PASS: `distill.messages` length `3` and `distill.reference_answer` populated for `12/12` rows. |
| Existing telemetry | PASS: TTFT, process RSS, and `llama-bench` SHA still populated for `12/12` rows. |
| Quality gate | PASS: `report-run-quality.py` found `strict_failures=0`. |
| Persistence | PASS: clean persistence; experiment branch pushed and finalized at `9d45330`. |

## Actual Field Inventory

We audited two `llama_cpp` runs:

| Run | Purpose | Raw rows | Raw top-level fields | `samples[]` fields | Run-meta fields | Judged rows | Judged fields |
|---|---|---:|---:|---:|---:|---:|---:|
| `llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-182852` | clean-source two-model smoke | 12 | 157 | 23 | 36 | 24 | 17 |
| `llama-cpp-evidence-5-strategy-pilot-6-none-baseline-llama_cpp-20260704-150059` | five-model R=5 mini-wave | 150 | 157 | 23 | 35 | 300 | 17 |

The 157 raw fields in both runs break down as:

| Category | Count | Examples |
|---|---:|---|
| Identity/design factors | 44 | `model`, `scenario`, `rep`, `env.inference_runtime`, `env.harness_source_dirty` |
| Generation telemetry | 25 | `gen_ai.*`, `phase.*`, `decode_tok_s`, `progress_trace` |
| Policy/forensics | 29 | `effective.*`, `prompt.*`, `strategy.*`, `http.exception` |
| Systems memory/I/O | 16 | `membw.*`, `mem.*`, `proc.*`, `disk.read_mb`, `net.total_kb` |
| Reset state | 12 | `reset.cpu_governor`, `reset.mem_avail_mb`, `reset.ok` |
| Power/thermal/GPU | 9 | `power.*`, `thermal.*`, `gpu.peak_freq_mhz` |
| `llama_cpp` adapter | 8 | `llama_cpp.model_path`, `llama_cpp.cli`, `llama_cpp.stderr_tail` |
| Model lock | 4 | `model_lock.params_b`, `model_lock.license_class` |
| Deterministic checks | 4 | `det_passed`, `det_total`, `det_detail`, `det_score` |
| Ollama compatibility placeholders | 2 | `ollama.ps.before`, `ollama.ps.after` |
| Other / containers | 4 | `samples`, `warmup_s`, `warmup_err`, `bracket` |

The judged rows carry 17 fields:

```text
adapter, criteria_met, criteria_missed, evidence, inference_runtime,
inference_strategy, judge_backend, judge_model, memory_context, model, rep,
scenario, scenarios_path, scenarios_sha256, score, usage, verdict
```

The important missingness in judged rows is `usage=null`: `24/24` in the clean
smoke and `300/300` in the R=5 mini-wave. Scores, evidence, verdicts, judges,
scenario hashes, and adapter/runtime stamps are present.

## Original Present-But-Empty Gaps For `llama_cpp`

Field count alone overstates coverage. The clean two-model smoke had 159 total
sample ticks. These fields were present but had zero non-null sample values:

```text
rss_mb, threads, majflt, minflt, ctxt_vol, ctxt_invol, watts
```

`watts` is acceptable when no smart plug is configured because `rapl_watts` is
non-null for 147/159 samples. The process fields are not acceptable for a systems
claim: `rss_mb`, `threads`, page faults, and context switches should attach to
the active `llama.cpp` child process.

Top-level fields that are present but null for every clean-smoke row include:

```text
gen_ai.server.time_to_first_token_s, phase.prefill_s, prefill_tok_s,
decode.dt_p50_ms, decode.dt_p95_ms, decode.dt_max_ms,
mem.rss_start_mb, mem.peak_rss_mb, proc.minflt, proc.majflt,
proc.ctxt_switches, llama_cpp.version, env.llama_cpp_version
```

Some all-null fields are expected because the condition was inactive
(`env.memory_context_file`, `env.strategy_prompt_file`, `gen_ai.thinking`,
`http.exception`, `socket_exception`, `reset.warnings`). The timing, tokenizer,
version, and child-process fields are real gaps.

Status after `2575ec5` and `8641e33`: the timing, token-source,
child-process, prompt/message, reference-answer, and distillation-message gaps are
resolved for clean R=1 smoke rows. The final promotion gate is a clean R=5
mini-wave with the same fields populated.

## Public Baseline Comparison

| Baseline | What it expects | Current state | Verdict |
|---|---|---|---|
| OpenTelemetry GenAI semantic conventions | Operation/model/provider identity, duration, token usage, finish reasons, TTFT/time-per-output-token when available, errors, and optional content capture. | We have `gen_ai.operation.name`, `gen_ai.request.model`, max tokens, temperature, seed, completion, finish reasons, output chars, estimated input/output tokens, and wall/decode time. We lack `gen_ai.provider.name`, `server.address`, `server.port`, `gen_ai.request.stream`, `gen_ai.response.model`, top-p/top-k/repeat settings, true TTFT, true time-per-output-token, and real tokenizer counts for `llama_cpp`. | **Should-fix before long run.** Add cheap scalar fields and fix streaming timing. |
| HELM | Dense shared scenarios, raw prompts/completions, multiple metrics, and explicit missing/underrepresented metrics. | We release completions, scenario IDs, deterministic checks, judge evidence, reliability, and efficiency. We do not claim HELM's calibration/fairness/toxicity dimensions, which is acceptable if stated. | **Pass with scope caveat.** Do not imply holistic LM evaluation. |
| MLPerf Inference | Standardized, reproducible system measurement across hardware/software, with controlled settings and repeated measurements. | We lock CPU state, RAPL, perf, repeats, seeds, scenario hashes, source SHA, and reset state. We are not using MLPerf LoadGen and should not claim MLPerf comparability. | **Pass for local benchmark; not MLPerf-compatible.** |
| Experiment Impact Tracker / energy-reporting practice | Hardware identity, power/energy, run duration, package/software context, and optional carbon/emission estimates. | We capture RAPL package/core/uncore/DRAM power, energy Wh, hardware profile, kernel, and run duration. We do not capture carbon intensity, PUE, or package environment snapshots. | **Energy pass; carbon not claimed.** Add carbon only if the paper claims emissions. |
| AIOpsLab / autonomous-cloud agent papers | Operational tasks need object, fault/workload/evidence, action surface, and evaluator shape. | Current scenarios have class/difficulty/grounding and `aiopslab_task`; newer lifecycle schema work exists. | **Sufficient for current pack; should keep lifecycle metadata in future packs.** |
| `llama.cpp` tooling | `llama-bench` provides JSON/JSONL/SQL for build commit, backend, model size/params, batch/ubatch, threads, KV cache types, offload, mmap/direct-IO, prompt/decode repetitions, average/stddev ns and tokens/s. `llama-perplexity` can compute perplexity and save logits for KL-divergence workflows. CLI help exposes internal perf timings, KV cache settings, prompt cache, context size, JSON schema/grammar, and verbose prompt/logs. | We capture only path, size, CLI, stderr tail, and some derived wall/decode fields. We do not ingest `llama-bench`, KV cache settings, backend/build fields, prompt/decode stddev, or logit/perplexity sidecars. | **Should-fix.** Add a pre-run per-model `llama-bench -o jsonl` sidecar and parse CLI timings. |

## Adversarial Findings

### RESOLVED FOR SMOKE — `llama_cpp` timing is now streaming-grade

Evidence: `run.py` calls `subprocess.run(cmd, capture_output=True, text=True)` in
`run_llama_cpp`, then sets `gen_ai.server.time_to_first_token_s=None`,
`phase.prefill_s=None`, `prefill_tok_s=None`, and `decode.dt_* = None`. It also
sets `progress_trace` to one terminal point: `[[wall, len(text)]]`.

Why this matters: OpenTelemetry GenAI treats TTFT/time-per-output-token as core
LLM serving metrics when available. For local deployment UX, TTFT and decode
jitter are not decorative; they distinguish "slow to start" from "slow to
decode".

Fix status: implemented in `2575ec5` by streaming stdout/stderr from the
subprocess. The clean smoke populated TTFT, prefill, decode jitter, and
multi-point progress traces for every row.

### RESOLVED FOR ROW-LEVEL METRICS — child-process memory/fault telemetry

Evidence: in the clean two-model smoke, `rss_mb`, `threads`, `majflt`, `minflt`,
`ctxt_vol`, and `ctxt_invol` were non-null in `0/159` sample ticks. Top-level
`mem.peak_rss_mb`, `mem.rss_start_mb`, `proc.minflt`, `proc.majflt`, and
`proc.ctxt_switches` were null for every row.

Why this matters: the thesis target is local deployment fit. Without child RSS,
threads, faults, and context switches, the memory-pressure claim relies on
system-wide available memory and bandwidth but misses the actual process footprint.

Fix status: implemented in `2575ec5` with `os.wait4()` child resource usage. The
clean smoke populated row-level max RSS, minor faults, and context switches for
every row. Per-tick `samples[].rss_mb` remains best-effort for very short rows;
the row-level process fields are the long-run gate.

### RESOLVED FOR `llama.cpp` TIMING COUNTS — tokenizer counts are no longer only estimates

Evidence: `run_llama_cpp` sets input/output tokens with `max(1, len(text) // 4)`
and `max(1, len(prompt) // 4)` instead of tokenizer or runtime totals.

Why this matters: token-normalized throughput, token usage, and comparison with
Ollama rows become approximate. Character throughput remains useful, but token/s
claims should be marked approximate until fixed.

Fix status: implemented in `2575ec5` by parsing prompt/eval token counts from
`llama.cpp --perf` output. Rows stamp `gen_ai.usage.token_source`; the clean smoke
reported `llama_cpp_timing` for every row.

### PARTIALLY RESOLVED — `llama.cpp` build/version and structured bench data

Evidence: `llama_cpp.version` and `env.llama_cpp_version` are null for every
clean-smoke row, while `llama-bench` can emit `build_commit`, `build_number`,
`cpu_info`, `backends`, model size/params, thread/cache/offload settings, and
prompt/decode averages/stddevs in JSON/JSONL.

Fix status: `2575ec5` stamps `LLAMA_CPP_GIT_COMMIT` / `LLAMA_CPP_GIT_DESCRIBE`
when the runtime profile exports them, and writes `llama-bench -o jsonl` sidecars
with row count, return code, and SHA. Remaining caveat: `llama_cpp.version` from
`llama-completion --version` may still be null if the binary does not implement a
version flag; the profile variables are the source of truth.

### RESOLVED FOR CORE SCALARS — GenAI semantic-convention scalar fields

Missing cheap fields include `gen_ai.provider.name`, `server.address`,
`server.port`, `gen_ai.request.stream`, `gen_ai.response.model`,
`gen_ai.request.top_p`, `gen_ai.request.top_k`, and repeat/frequency/presence
penalty settings when we rely on defaults.

Fix status: `2575ec5` adds provider, output type, response model, stream mode,
token source, and parsed sampler fields where `llama.cpp` prints them. Remaining
nice-to-have: explicit null/policy fields for settings the runtime defaults but
does not print.

### SHOULD-FIX — judge usage is null

Evidence: `usage=null` for `24/24` clean-smoke judged rows and `300/300` R=5
mini-wave judged rows.

Why this matters: score/evidence/verdict capture is intact, but judge token/cost
accounting is not. This is not a model-quality blocker, but it is a cost/reporting
gap.

Fix: either parse usage from a judge backend that returns it, or explicitly mark
Copilot CLI usage as unavailable in reports instead of displaying zero-like
summaries.

### NICE-TO-HAVE — logits/perplexity sidecars

`llama-perplexity` exposes perplexity, KL-divergence, and `--save-all-logits`.
This is useful for calibration probes or drift tests, but not necessary for the
current open-ended ops-answer benchmark. Do not write all logits for every
scenario by default; the artifacts would be large and hard to interpret. A fixed
calibration prompt set is the right place for logits/perplexity.

### OUT-OF-SCOPE — full activations and dynamic expert routing

The normal `llama.cpp` CLI does not expose full activations or per-token MoE
expert routing. Capturing them would require custom instrumentation inside
`llama.cpp`/GGML and would materially perturb performance. For this benchmark,
static model metadata plus external systems telemetry is the defensible boundary.

## Pre-Long-Run Gate

Before any weeks-long all-model `llama_cpp` run, require a new clean smoke to
pass these gates:

| Gate | Required result |
|---|---|
| Source provenance | `env.harness_source_dirty=false` for every row. |
| Runtime identity | `adapter=llama_cpp`, `env.inference_runtime=llama_cpp`, `run.meta.sync_mode=origin`. |
| Streaming timing | `gen_ai.server.time_to_first_token_s`, `phase.prefill_s`, `decode.dt_p50_ms`, `decode.dt_p95_ms`, and multi-point `progress_trace` are populated for successful rows. |
| Child process telemetry | Row-level max RSS, page faults, context switches, and CPU time are populated from `os.wait4()`; per-tick process samples are best-effort for short rows. |
| Token accounting | Token counts are runtime/tokenizer-derived, or reports explicitly label them approximate and use character-normalized metrics for runtime comparison. |
| `llama.cpp` provenance | Row or sidecar records `LLAMA_CPP_GIT_COMMIT`, build/version, model path, GGUF size/hash, cache/context/thread/offload settings. |
| Structured bench sidecar | Per-run or per-model `llama-bench -o jsonl` sidecar exists for the staged GGUFs. |
| Server capture | For canonical long-run data, row-level `llama-server` fields are captured or the run is explicitly labelled subprocess-only. |
| Cache axis | A separate cache micro-benchmark records cache hit/read/write tokens, prefix hashes, `tokens_cached`, prompt time, TTFT, and output equivalence. |
| Prompt and distillation capture | `prompt.full`, `prompt.sha256`, structured input/output messages, reference answer/hash, and `distill.messages` are populated for every successful row. |
| Existing integrity gates | `report-run-quality.py --strict` passes, reset state is clean, persistence is clean, and `audit-run.py` passes for R=5 evidence runs. |

## Recommendation

Do not start the weeks-long all-model run yet. The telemetry and prompt-capture
remediation slices are implemented and smoke-validated. The next required gate is
a clean `llama-cpp-evidence-5` R=5 mini-wave from `origin/main`; only after that
passes with the new fields populated should we promote the `llama_cpp` path to
canonical long-run status.