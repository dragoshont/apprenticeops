**Research paper · open benchmark · arXiv preprint → NeurIPS Datasets & Benchmarks track**

**Online summary & live paper — [dragoshont.github.io/apprenticeops](https://dragoshont.github.io/apprenticeops/)** — figures, the sovereign-selection Pareto, and judge agreement at a glance · [paper PDF](https://dragoshont.github.io/apprenticeops/paper.pdf) · reviewing this work? [start here](https://dragoshont.github.io/apprenticeops/reviewers.html) or [`REVIEWER.md`](REVIEWER.md)

**Verified (2026-06-22):** every number was re-derived from the committed snapshot and every citation resolved against arXiv / CrossRef.

**Run it in your browser —** open the [**reviewer query notebook**](https://github.com/dragoshont/apprenticeops/blob/main/docs/analysis/reviewer.ipynb) on [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/dragoshont/apprenticeops/main?labpath=docs%2Fanalysis%2Freviewer.ipynb) , [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dragoshont/apprenticeops/blob/main/docs/analysis/reviewer.ipynb) , or [![Open in Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/kernels/welcome?src=https://github.com/dragoshont/apprenticeops/blob/main/docs/analysis/reviewer.ipynb) — reproduce every headline number, then **edit the queries and re-run** (no install).

[![Built with Architrave](https://img.shields.io/badge/Built%20with-Architrave-5b21b6?logo=github&logoColor=white)](https://github.com/dragoshont/architrave)

# ApprenticeOps: Evaluating Small Locally-Sovereign LLMs as Homelab Operations Assistants

> *Every AIOps paper runs a frontier model in a lab. We ran a 2018 ThinkPad in a closet — because that's where the interesting question lives.*

---

The AIOps community has produced impressive results: benchmarks with live fault-injection, frontier models with tool-calling, thousand-node clusters as the arena. All of it points at what AI *can* do given unlimited resources and a cloud account.

This paper asks the inverse question: **what can a small local model do when there is no escape hatch?** No Claude, no GPT, no Azure endpoint, no frontier escalation — just a 2018 ThinkPad running Ollama and a real production cluster's worth of incidents. The model is the last line. It must reason with what it has, or admit that it can't.

We call this the **locally-sovereign inference constraint**: the brain runs on *your* hardware. We measure where that floor is, what it costs in accuracy and energy, whether these models are safe to have in front of a real cluster — and whether a 3 GB model is meaningfully different from an 8 GB one on the tasks that matter.

---

## Why this is different from existing AIOps benchmarks

| | AIOpsLab / ITBench / OpsEval | ApprenticeOps |
|---|---|---|
| **Model assumption** | Frontier (GPT-4, Claude, Gemini) | Small, locally-sovereign (≤ 5 GB, CPU-only) |
| **Hardware** | Server / cloud | 2018 consumer laptop, 15 W TDP |
| **Scenarios** | Synthetic fault-injection, live clusters | Frozen real incidents from a production homelab |
| **Inference** | Always-online, API-callable | No external model API during graded inference |
| **Telemetry** | Task accuracy | Accuracy + energy + speed + CPU microarchitecture |
| **Safety** | Implied by model capability | Explicit `guard` class: refusal of destructive actions |
| **Grounding** | Oracle or live retrieval | Both measured separately, upper-bound labelled as such |

The axis we care about — reasoning per GB of model, on commodity hardware, in a sovereignly-operated system — is largely unmeasured. ApprenticeOps fills that gap.

---

## What we instrument per inference call

Every request emits a structured record aligned with [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai). A short summary of the main groups:

| Group | Signals captured |
|---|---|
| **Latency** | TTFT · prefill tok/s · decode tok/s · wall time · cold-load warmup |
| **Token budget** | In/out tokens and chars · think-vs-answer split (reasoning models get separated chain-of-thought time so they are neither rewarded nor penalised for it) |
| **Stream quality** | Inter-token jitter p50/p95/max — a model with a good mean tok/s but a high p95 *stutters* the UX |
| **Energy** | Intel RAPL `package-0` joules → Wh/task · Wh/correct-answer · tok/s-per-watt |
| **Memory** | RSS start→peak · peak swap (MB) · minor/major page faults · context switches |
| **CPU microarchitecture** | IPC · LLC miss rate · branch miss count — a low IPC + high LLC-miss is the fingerprint of memory-bandwidth-bound decode |
| **DRAM bandwidth** | IMC requestor split: IA (CPU) / GT (iGPU) / IO — confirms the bottleneck is memory, not compute |
| **Model internals** | Parameter count · quantisation · MoE expert count/active · native context length (from Ollama `/api/show` and `/api/ps`) |
| **Ollama runtime** | `load` / `eval` / `total` durations from the response payload — authoritative, not inferred |

This telemetry depth is unusual for LLM evaluation. The reason is simple: on CPU-only inference, "why is this model slower?" is a non-trivial question. The numbers above let you answer it.

---


There is a common conflation between *inference sovereignty* (no external model API) and *information poverty* (no external data). We reject the second. A locally-sovereign model can and should have access to local RAG, in-organisation MCP servers, runbooks, and cluster telemetry. The constraint is on where the *reasoning* happens, not on what data feeds it.

This redraws the requirement stack for a small local ops model:

1. **Reason without an external model** — its judgment is final; no second opinion.
2. **Grounding-faithfulness** — use supplied local context and do not contradict or hallucinate beyond it.
3. **Calibration** — say "I don't know" rather than inventing. This is the prerequisite for safety.
4. **Safety-by-default** — refuse destructive actions without a human in the loop to catch the error.
5. **Fit and speed** — must run interactively on owned hardware.

This is why we measure two grounding modes per scenario: **closed-book** (in-weights knowledge only) and **grounded** (correct reference material supplied in-context, simulating perfect local retrieval). The gap between them is directly actionable — it answers "do I need a vector database next to my tiny model, and how much does it buy me?"

The updated experiment adds two orthogonal comparison axes: **memory context**
and **inference strategy**. The dashboard and runner can execute the same
model/scenario set with `memory_context=none`, `homelab-okf-v1`, or
`homelab-okf-3kb-v1`; the condition is stamped into every raw row as
`env.memory_context`. Separately, `inference_strategy` records *how* the answer
was produced: `baseline`, `single_call_tournament_brief`,
`best_of_3_detcheck`, `self_consistency_3`, or `evaluator_optimizer_1`.

The distinction is load-bearing. Memory tests whether curated homelab background
helps. Strategy tests whether extra inference-time computation helps. Mixing the
two would make any lift uninterpretable. Multi-candidate strategies write
auditable candidate sidecars and stamp selection metadata (`strategy.*`) into the
final row; reports group DNF/stall/length by both memory and strategy so quality
cannot improve by silently dropping harder rows.

Use the deliberately small pilot before multiplying the full `spread10` matrix:
`model_set=strategy-pilot-2` (qwen3:4b plus granite4:micro),
`scenario_set=strategy-pilot-6` (six structured/safety/multi-step scenarios),
`memory_context=none` or `homelab-okf-3kb-v1`, and the strategy variants above.

---

## Research questions

Seven falsifiable hypotheses were **pre-registered** before the measurement run
(the locked spec lives in [`docs/PAPER.md`](docs/PAPER.md) §3). We report each one
against what actually happened — **including the predictions the data did not
confirm** — rather than quietly revising them after the fact:

| RQ | Pre-registered prediction | Outcome |
|---|---|---|
| RQ1 | Quality rises with diminishing returns; a knee around **3–4B**. | **Supported** — knee landed one bracket smaller, at **2–3B**. |
| RQ2 | The **3–4B** bracket dominates the speed/quality Pareto. | **Partial** — the balanced pick is 3–4B, but the non-dominated front spans **all five** brackets. |
| RQ3 | Safety is **not monotonic** in size; some small models endorse destructive commands. | **Supported** — driven by **training type, not size**. |
| RQ4 | "Thinking" models gain on diagnosis but at prohibitive CPU latency. | **Not directly tested** — no per-class accuracy × latency split (future work). |
| RQ5 | Best ≤5 GB model reaches **~60–80 %** of a frontier reference. | **Not directly tested** — no frontier baseline run; ≈ 71 % of the judge's ceiling (a proxy). |
| RQ6 | Local **RAG** lift is large for small models and shrinks with size. | **Not causally tested** — closed-book vs grounded are different task classes (confound disclosed). |
| RQ7 | Energy/answer rises with params; the knee is the efficiency sweet spot. | **Supported** — energy rises with params; knee one bracket smaller (**2–3B**). |

Three of the seven hold as stated; the quality knee landed **one bracket smaller**
than predicted; three (RQ4–RQ6) were **not directly testable** with this design and
are flagged as such, not silently dropped. Full prediction-vs-outcome detail and
the deviation log: [`docs/PAPER.md`](docs/PAPER.md) §8c.

---

## Headline result — the quality × safety × energy Pareto

The contribution is not any single axis; it is choosing on **all three together**.
Treat each model as a point in **(judged quality ↑, destructive-action refusal ↑,
energy-per-answer ↓)** and compute the **Pareto-optimal set** — the models nothing
else beats on every axis at once. On the consolidated **94-model** data, **12 of 94 models are
Pareto-optimal; the other 82 are dominated**, and the two heuristics a practitioner
reaches for — *biggest that fits* and *has a “reasoning” mode* — select **dominated**
models. `deepseek-r1:7b` is among the worst *combined* cases: among the **most
energy-expensive** models in the study (top 5 of 94), and the least-safe large
reasoning-distilled refuser.

The three axes, briefly:

- **Quality** — judged %-of-frontier knees at **2–3B**; *quantization*, not parameter
  count, carries the marginal lift.
- **Safety (axis #2)** — judge-free deterministic refusal, governed by **training
  type, not size**. This **corroborates** a saturated agent-/SLM-safety literature
  (GAP, OS-Harm, Beyond-the-Tip, Q-resafe, …); we replicate it offline, we do not
  claim to discover it.
- **Energy** — the under-reported axis: Wh/answer and tok/s-per-watt you pay to run
  the model yourself.

Figures and the dominance computation live in
[`docs/analysis/wave_analysis.ipynb`](docs/analysis/wave_analysis.ipynb) §7–§8; the
full result is [`docs/PAPER.md`](docs/PAPER.md) §8b. The quality axis is the
**5-rep × 2-judge ensemble** (cross-judge κ_quad ≈ 0.91); residual judge↔human
agreement is the remaining open item (see [`REVIEWER.md`](REVIEWER.md) §7).

---

## The scenarios

The original paper run used **19 scenarios**. The working corpus now contains
**33 scenarios** in [`data/scenarios.json`](data/scenarios.json): the original
homelab incidents plus later repo-grounded security, capacity, tool-action, and
private app/device-ops incident cases. The 2026-06-24 external research pass recommends a
**20-case core roster** for the next expensive run; see
[`docs/SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md`](docs/SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md)
for the decision summary,
[`docs/SCENARIO_RESEARCH_2026-06-24.md`](docs/SCENARIO_RESEARCH_2026-06-24.md)
for the source-backed scan, and the earlier inventory audit in
[`docs/SCENARIO_AUDIT_2026-06-24.md`](docs/SCENARIO_AUDIT_2026-06-24.md).

The scenarios are drawn from a production homelab cluster (`home.home.domain`,
Kubernetes, Flux, Traefik, Plex, *arr stack) and synthetic-but-repo-grounded
extensions that preserve the same operational shapes. They span these task
classes:

| Class | What the model must do |
|---|---|
| `detect` | Triage a crashloop or probe failure from logs and events |
| `diagnose` | Identify root cause from a multi-signal incident dump |
| `monitor` | Interpret metrics/alerts correctly |
| `foresee` | Spot a *misleading healthy surface signal* hiding a real problem (trap scenarios) |
| `expand` | Plan adding a new application to a GitOps cluster |
| `upgrade` | Plan a Helm release upgrade with correct flag choices |
| `augment` | Emit structured telemetry (JSON log events, OTel spans) from existing code |
| `guard` | **Refuse** a destructive or unsafe action (hard gate) |
| `secure` | Identify a security misconfiguration |

Scenarios are labelled `easy / medium / hard`. The **easy** tier is a passable floor — any useful model should clear it. The **hard** `foresee-*` scenarios are deliberate traps: the SMART health check is `PASSED` while reallocated sectors are climbing; the TLS cert is `Ready=True` while the DNS-01 auto-renewal has been 403-ing for days. Labels are validated empirically against the accuracy-by-difficulty table — if the ordering doesn't hold, the label is revised.

The corpus marks grounding explicitly. The captured subset is real `home.home.domain`
telemetry; the synthetic-but-repo-grounded subset is constructed from this
homelab's actual conventions and failure surfaces. That distinction matters for
claims about contamination and generalisation.

---

## Measurement: not just accuracy numbers

The harness captures far more than pass/fail. Per-request fields include:

**Quality**
- `det_score` — deterministic check pass rate (unambiguous facts; no judge required)
- `judge_score` — frontier LLM-as-judge score (1–5), reported as % of frontier reference
- `safety_pass` — binary hard gate on the `guard` class

**Systems transparency** — aligned with [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- TTFT, prefill tok/s, decode tok/s, wall time, in/out tokens and characters, cold-load warmup
- Think/answer split for reasoning models — chain-of-thought time reported separately so models are neither rewarded nor penalised for hidden reasoning
- Inter-token jitter (p50/p95/max ms) — stream *smoothness*, not just mean rate
- RAPL energy (joules → Wh/task) at the `package-0` domain — on-die SoC draw, not facility power
- Intel IMC memory bandwidth (IA/GT/IO requestor split), peak swap, RSS growth
- IPC, LLC miss rate, and branch-miss counts — the memory-bandwidth-bound decode fingerprint
- Ollama-native internals: architecture, MoE expert count, quantisation, `load`/`total`/`eval` durations from the response payload — not inferred, read directly

**Reproducibility controls**
- Governor locked to `performance`, turbo disabled, clocks pinned to base (~1.70 GHz, sustainable) for the systems pass
- Per-model `quiesce()` step: fan to max, drop page-cache, reset swap, compact memory, wait for package temperature to settle
- Randomised model order with fixed `--order-seed` to decorrelate carryover from model identity
- CPU frequency logged at 1 Hz as throttle evidence

This level of measurement depth is unusual for LLM evaluation. The reason: on CPU-only inference, the question "why is this model slower?" is non-trivial. A low IPC with high LLC-miss rate is the fingerprint of a memory-bandwidth-bound decode. A model that looks fast on token/s may be stalling on swap. These numbers tell you *why*, not just *what*.

---

## Telemetry field reference

The CEOps runner schema is intentionally append-only. The `spread10` memory-axis
audit on 2026-06-27 observed a structurally complete **129-field base inference
row** and **14-field base judge row**; the current runner extends that contract
with strategy, timeout-policy, prompt-size, stall-forensics, and reliability
fields. Treat the field list below as the **current semantic contract**, not as a
fixed column count.

> **Scope honesty:** field presence does not mean every value is informative. For
> `DNF:stall` rows, Ollama may never return final token counters, so fields such
> as `gen_ai.usage.input_tokens` can be `0`/`null`. That is a measured failure
> mode, not a missing column. The current schema records `stall_phase`, HTTP
> timing, prompt diagnostics, effective timeout policy, and compact Ollama process
> snapshots so the next run can distinguish prompt-eval/API stalls from ordinary
> slow decode.

<details>
<summary><strong>Inference rows: current semantic groups</strong></summary>

### Core scenario, scoring, and request identity

| Field | Meaning |
|---|---|
| `aiopslab_task` | Coarse AIOps task mapping used for comparison with AIOps-style taxonomies. |
| `bracket` | Model footprint/size bracket from the model roster comment, such as `3-4B`. |
| `class` | ApprenticeOps scenario class, such as `diagnose`, `secure`, `guard`, or `capacity`. |
| `decode_tok_s` | Response decode throughput in output tokens per second, using Ollama's final eval counters when available. |
| `det_detail` | Per-check deterministic evaluation results: description, check type, and pass/fail. |
| `det_passed` | Number of deterministic checks passed for this scenario answer. |
| `det_score` | Deterministic score as `det_passed / det_total`. |
| `det_total` | Number of deterministic checks attached to the scenario. |
| `difficulty` | Scenario difficulty label: `easy`, `medium`, or `hard`. |
| `dnf` | Boolean: the request did not finish normally (`DNF:*` finish reason). |
| `grounding` | Grounding regime label, such as `closed-book` or `grounded`. |
| `min_mem_avail_mb` | Minimum host `MemAvailable` observed during the request. |
| `model` | Ollama model tag used for the request. |
| `pair_id` | Optional pairing identifier for paired scenario variants; `null` when unpaired. |
| `peak_swap_mb` | Peak host swap usage during the request. |
| `prefill_tok_s` | Prompt prefill throughput in input tokens per second, when Ollama returns prefill counters. |
| `progress_trace` | Streaming progress curve: elapsed seconds and cumulative output characters. |
| `rep` | Repetition index for this model/scenario pair. |
| `samples` | Full host sampler time series captured during the request. |
| `scenario` | Scenario identifier. |
| `seed` | Sampling seed for this repetition. |
| `temp` | Sampling temperature used for this request. |
| `think` | Whether Ollama thinking mode was enabled for this run. |
| `ts` | Unix timestamp when the row was emitted. |
| `wall_s` | Request wall-clock duration in seconds. |
| `warmup_err` | Cold-load/warmup error string, if warmup failed; otherwise `null`. |
| `warmup_s` | Cold-load warmup duration for the model before scenario requests. |

### Decode stream quality

| Field | Meaning |
|---|---|
| `decode.dt_max_ms` | Maximum inter-token/chunk gap observed in the streamed response. |
| `decode.dt_p50_ms` | Median inter-token/chunk gap for stream smoothness. |
| `decode.dt_p95_ms` | 95th-percentile inter-token/chunk gap; high values indicate visible stutter. |

### Disk and network activity

| Field | Meaning |
|---|---|
| `disk.read_mb` | Approximate disk read volume during the request. |
| `net.peak_kb_s` | Peak non-loopback network throughput during the request; expected to be near zero during local inference. |
| `net.total_kb` | Total non-loopback network bytes observed during the request, in KiB. |

### Run environment and reproducibility stamp

| Field | Meaning |
|---|---|
| `env.cpu_governor` | Live CPU frequency governor at row time. |
| `env.cpu_max_perf_pct` | Intel p-state max performance percentage. |
| `env.cpu_min_perf_pct` | Intel p-state min performance percentage. |
| `env.cpu_no_turbo` | Intel p-state turbo-disable flag (`1` means Turbo is disabled). |
| `env.harness_git` | Short git commit of the harness used on the inference node. |
| `env.harness_dirty` | Whether the inference-node working tree had uncommitted changes. Canonical paper runs should be `false`; dashboard/dev runs may be `true`. |
| `env.host` | Hostname of the inference node. |
| `env.kernel` | Linux kernel version on the inference node. |
| `env.inference_strategy` | Inference strategy identifier, such as `baseline`, `best_of_3_detcheck`, or `evaluator_optimizer_1`. This is separate from memory. |
| `env.memory_context` | Memory condition identifier, such as `none`, `homelab-okf-v1`, or `homelab-okf-3kb-v1`. |
| `env.memory_context_file` | Memory-context file path injected into the prompt, or `null` for `none`. |
| `env.memory_context_sha` | SHA-256 of the memory-context file, or `null` for `none`. |
| `env.num_ctx` | Ollama context length requested by the harness. |
| `env.ollama_version` | Ollama version string reported by the node. |
| `env.perf_core` | Whether CPU-core `perf` counters were enabled. |
| `env.perf_event_paranoid` | Linux perf access setting at row time. |
| `env.perf_membw` | Whether memory-bandwidth `perf` counters were enabled. |
| `env.rapl_domain` | Intel RAPL domain used for energy, normally `package-0`. |
| `env.run_id` | Run identifier stamped into the row. |
| `env.sample_interval_s` | Host sampler interval in seconds. |
| `env.scenario_set` | Scenario-set identifier, such as `core-current`. |
| `env.scenarios_path` | Scenario file used by the run. |
| `env.scenarios_sha` | SHA-256 of the scenario file. |
| `env.strategy_prompt_file` | Optional strategy prompt file path used by prompt-only inference strategies. |
| `env.strategy_prompt_sha` | SHA-256 of the strategy prompt file, or `null` for strategies without a prompt file. |

### Effective policy and prompt diagnostics

| Field | Meaning |
|---|---|
| `effective.max_tokens` | Effective `num_predict` cap after scenario/model/memory/strategy policy resolution. |
| `effective.policy_reasons` | Reasons that modified the base timeout policy, such as `memory_context` or `known_slow_model`. |
| `effective.retry_attempts` | Compact summaries of retry attempts for zero-output stalls. |
| `effective.retry_count` | Number of zero-output stall retries used by the selected answer. |
| `effective.retry_reason` | Retry trigger; currently `zero_output_stall` when a retry was used. |
| `effective.stall_s` | Effective no-token stall watchdog in seconds. |
| `effective.timeout_policy_id` | Named timeout policy, so old/new regimes are not mixed in analysis. |
| `effective.timeout_s` | Effective wall-clock timeout in seconds. |
| `prompt.char_count` | Full final prompt character count before strategy wrapping. |
| `prompt.estimated_tokens` | Token estimate from character count; useful when Ollama never returns prompt token counters. |
| `prompt.memory_char_count` | Injected memory-context character count. |
| `prompt.scenario_context_char_count` | Scenario context character count. |
| `prompt.task_char_count` | Scenario task/question character count. |

### Strategy selection metadata

| Field | Meaning |
|---|---|
| `strategy.candidate_count` | Number of local model calls used to produce the selected answer. |
| `strategy.candidates` | Candidate summaries, including selected flag, deterministic score, finish reason, retry count, and completion text. |
| `strategy.extra_calls` | Additional local calls beyond baseline. |
| `strategy.failure_mode` | Selected answer failure mode when the final answer is a DNF. |
| `strategy.id` | Strategy id copied from `env.inference_strategy`. |
| `strategy.prompt_sha256` | Strategy prompt SHA when a prompt file is used. |
| `strategy.sample_index` | Reserved for future repeated strategy samples; currently `0`. |
| `strategy.selected_candidate` | Candidate index selected as the final answer. |
| `strategy.selection_method` | Selection rule, such as `max_det_score_then_non_dnf`. |
| `strategy.total_input_tokens` | Sum of Ollama input tokens across all candidate calls that returned counters. |
| `strategy.total_output_tokens` | Sum of Ollama output tokens across all candidate calls. |
| `strategy.total_retry_count` | Sum of zero-output stall retries across candidate calls. |
| `strategy.total_wall_s` | Total strategy wall time across candidate calls. |
| `strategy.version` | Strategy implementation version. |

### OpenTelemetry GenAI fields

| Field | Meaning |
|---|---|
| `gen_ai.completion` | Raw assistant answer text used for checks and judging. |
| `gen_ai.operation.name` | GenAI operation name; currently `chat`. |
| `gen_ai.request.max_tokens` | `num_predict` cap sent to Ollama. |
| `gen_ai.request.model` | Model name sent to the Ollama API. |
| `gen_ai.request.seed` | Seed sent in Ollama options. |
| `gen_ai.request.temperature` | Temperature sent in Ollama options. |
| `gen_ai.response.finish_reasons` | Final reason list, e.g. `stop`, `length`, `DNF:timeout`, or `DNF:stall`. |
| `gen_ai.server.time_to_first_token_s` | Seconds to first thinking/content chunk; `null` if no token arrived. |
| `gen_ai.thinking` | Raw thinking text, when a thinking model emits it. |
| `gen_ai.thinking.chars` | Character count of thinking text. |
| `gen_ai.usage.input_tokens` | Ollama prompt token count from the final response; can be `0` when no final response arrives. |
| `gen_ai.usage.output_chars` | Character count of the answer text. |
| `gen_ai.usage.output_tokens` | Ollama output token count, or a best-effort estimate for partial output. |

### GPU and CPU-only proof

| Field | Meaning |
|---|---|
| `gpu.peak_freq_mhz` | Peak Intel iGPU frequency during the request; used as evidence that Ollama is not using the iGPU for inference. |

### Host memory and process footprint

| Field | Meaning |
|---|---|
| `mem.avail_start_mb` | Host `MemAvailable` at request start. |
| `mem.peak_rss_mb` | Peak RSS of the Ollama runner process. |
| `mem.rss_start_mb` | Runner RSS at request start. |
| `swap.start_mb` | Host swap usage at request start. |

### DRAM bandwidth

| Field | Meaning |
|---|---|
| `membw.peak_mb_s` | Peak DRAM bandwidth observed by Intel uncore IMC counters. |
| `membw.requests` | Aggregate IMC requestor split: CPU cores (`ia`), iGPU (`gt`), and IO. |
| `membw.series` | Per-sample DRAM read/write bandwidth series. |

### Ollama model identity and runtime metadata

| Field | Meaning |
|---|---|
| `ollama.block_count` | Transformer block/layer count reported by Ollama model metadata. |
| `ollama.capabilities` | Ollama-declared model capabilities. |
| `ollama.context_length` | Native model context length from Ollama metadata. |
| `ollama.cpu_pct` | Percent of loaded model bytes resident on CPU memory according to `/api/ps`. |
| `ollama.digest` | Ollama model digest; detects tag drift. |
| `ollama.embedding_length` | Model embedding width. |
| `ollama.expert_count` | Total MoE expert count, when the architecture reports it. |
| `ollama.expert_shared_count` | Shared expert count for MoE models, when present. |
| `ollama.expert_used_count` | Experts used per token for MoE models, when present. |
| `ollama.family` | Model family reported by Ollama, such as `llama` or `qwen2`. |
| `ollama.feed_forward_length` | Feed-forward hidden width from model metadata. |
| `ollama.gpu_pct` | Percent of loaded model bytes resident on GPU/VRAM according to `/api/ps`. |
| `ollama.head_count` | Attention query-head count. |
| `ollama.head_count_kv` | KV head count; useful for GQA/KV-cache compression. |
| `ollama.load_duration_s` | Ollama load duration from the response payload. |
| `ollama.parameter_count` | Exact parameter count from Ollama metadata. |
| `ollama.parameter_size` | Human-readable model parameter-size label from Ollama. |
| `ollama.parameters` | Model Modelfile parameter defaults captured for sampler audit. |
| `ollama.quantization` | Quantization level, such as `Q4_K_M`. |
| `ollama.quantization_version` | GGUF quantization version, when reported. |
| `ollama.rope_dimension_count` | RoPE dimension count from metadata. |
| `ollama.rope_freq_base` | RoPE frequency base from metadata. |
| `ollama.size_bytes` | Loaded model size in bytes from `/api/ps`. |
| `ollama.size_vram_bytes` | Loaded model bytes in VRAM; `0` is direct evidence of CPU-only inference. |
| `ollama.tokenizer_model` | Tokenizer model name reported by GGUF metadata. |
| `ollama.total_duration_s` | Ollama total request duration from the final response payload. |
| `ollama.vocab_size` | Vocabulary size from model metadata. |

### HTTP and stall forensics

| Field | Meaning |
|---|---|
| `done_at` / `http.done_at_s` | Seconds until Ollama's final `done` event, if any. |
| `first_byte_at` / `http.first_byte_at_s` | Seconds until the first streamed byte. |
| `first_content_at` / `http.first_content_at_s` | Seconds until first thinking/content token. |
| `first_json_at` / `http.first_json_at_s` | Seconds until first parseable streamed JSON event. |
| `http.connected_at_s` / `http_connected_at` | Seconds until response headers were received. |
| `http.exception` / `socket_exception` | Socket/URL exception class and short message for failed streams. |
| `ollama.ps.after` | Compact `/api/ps` snapshot after a DNF. |
| `ollama.ps.before` | Compact `/api/ps` snapshot before the request. |
| `stall.phase` / `stall_phase` | Stall classification: before response headers, before first byte/JSON/token, during decode, or after missing done. |

### Perf and request phases

| Field | Meaning |
|---|---|
| `perf.core` | Derived CPU-core perf counters, such as IPC and cache-miss counts, when enabled. |
| `phase.decode_s` | Ollama decode/eval duration in seconds. |
| `phase.prefill_s` | Ollama prompt prefill duration in seconds. |
| `phase.think_s` | Time until answer content begins after thinking output, for thinking models. |

### Power and energy

| Field | Meaning |
|---|---|
| `power.energy_wh` | Request energy in watt-hours. |
| `power.idle_watts` | Idle baseline power measured before the run. |
| `power.mean_watts` | Mean request power. |
| `power.peak_dram_w` | Peak DRAM subdomain power, when RAPL exposes it. |
| `power.peak_watts` | Peak package/plug power during the request. |
| `power.source` | Energy source, e.g. `rapl:package-0` or smart-plug telemetry. |

### Process counters

| Field | Meaning |
|---|---|
| `proc.ctxt_switches` | Voluntary plus involuntary context-switch delta for the model runner. |
| `proc.majflt` | Major page-fault delta for the model runner. |
| `proc.minflt` | Minor page-fault delta for the model runner. |

### Per-model reset-state evidence

| Field | Meaning |
|---|---|
| `reset.cpu_freq_mhz` | Mean CPU frequency immediately before the model run. |
| `reset.cpu_governor` | CPU governor immediately before the model run. |
| `reset.cpu_no_turbo` | Turbo-disable flag immediately before the model run. |
| `reset.cpu_temp_c` | Package temperature immediately before the model run. |
| `reset.load1` | One-minute system load immediately before the model run. |
| `reset.mem_avail_mb` | Available memory immediately before the model run. |
| `reset.ok` | Boolean: reset-state guard found no start-state warnings. |
| `reset.perf_event_paranoid` | Perf access setting at reset snapshot. |
| `reset.running_procs` | Number of processes in running state at reset snapshot. |
| `reset.swap_used_mb` | Swap used at reset snapshot. |
| `reset.top_proc` | Top non-harness CPU process if one looked suspicious. |
| `reset.warnings` | Semicolon-separated reset warnings, or `null`. |

### Thermal telemetry

| Field | Meaning |
|---|---|
| `thermal.peak_c` | Peak CPU package temperature during the request. |
| `thermal.start_c` | CPU package temperature at request start. |

</details>

<details>
<summary><strong>Judge rows: 15 fields</strong></summary>

| Field | Meaning |
|---|---|
| `criteria_met` | Judge-reported rubric criteria satisfied by the answer. |
| `criteria_missed` | Judge-reported rubric criteria missed by the answer. |
| `evidence` | Judge rationale/evidence for the assigned score. |
| `inference_strategy` | Strategy condition copied into the judge row for direct comparison. |
| `judge_backend` | Judge execution backend; currently Copilot CLI for the live CEOps path. |
| `judge_model` | Judge model identifier, such as `claude-opus-4.6` or `gpt-5.4`. |
| `memory_context` | Memory condition copied into the judge row for direct comparison. |
| `model` | Evaluated Ollama model tag. |
| `rep` | Repetition index judged. |
| `scenario` | Scenario identifier judged. |
| `scenarios_path` | Scenario file used by the judge. |
| `scenarios_sha256` | SHA-256 of the scenario file used by the judge. |
| `score` | Judge score on the 1–5 rubric. |
| `usage` | Judge-provider usage object when available; `null` for backends that do not return it. |
| `verdict` | Short structured verdict from the judge; `empty` is used for empty/DNF answers. |

</details>

---

## Hardware: the 2018 ThinkPad is not a weakness

The node is a **ThinkPad T480s, Intel i5-8350U** (4C/8T, base 1.70 GHz, 15 W TDP, AVX2, no AVX-512), **24 GiB DDR4-2400 dual-channel** (asymmetric flex mode, ~38.4 GB/s theoretical peak). It costs roughly **150 USD** second-hand. It is representative of the low end of what a serious homelab practitioner actually has — not the median cloud instance, not a MacBook Pro M-series.

Running the benchmark on this hardware is not a limitation to apologise for. It is the *measurement point*. A model that performs well here works on the hardware you can afford to dedicate to local inference. A model that struggles here tells you exactly what you are giving up.

---

## Quick start

**Prerequisites:** Ollama ≥ 0.30 on any OS; Python ≥ 3.10 (stdlib only for the harness).

```bash
git clone https://github.com/dragoshont/apprenticeops.git && cd apprenticeops
ollama --version                                      # verify >= 0.30
python3 run.py --help                                 # stdlib-only; no pip needed for the harness
python3 baselines.py --out /tmp/bl.jsonl              # sanity-check: no model; random~0.26 keyword~0.73
```

**Pilot run — one model, current scenario corpus (~5-10 min):**
```bash
printf '# bracket: 0-1B\nqwen2.5:0.5b\n' > one.txt
python3 run.py --models one.txt
# Watch: det=x/y tok/s per scenario; results.jsonl with OTel fields + system telemetry.
```

**Full variance run (hours to days; the paper run):**
```bash
# Deterministic pass: temp=0, 1 rep — the point estimate
python3 run.py --models data/models.txt --temp 0 --repeats 1 --out results.det.jsonl

# Variance pass: temp=0.7, R=5 fixed seeds — enables 95% CIs
python3 run.py --models data/models.txt --temp 0.7 --repeats 5 --seed-base 1 --out results.var.jsonl
```

See [`REPRODUCE.md`](REPRODUCE.md) for the full pipeline — including locking the node into a reproducible power state, running the judge, generating the paper tables, and exporting an ML-ready flat dataset.

---

## Documents

| File | What it is |
|------|-----------|
| [`REVIEWER.md`](REVIEWER.md) | **Reviewer's guide** — what the paper claims, how it was produced (human-guided, AI-assisted), the review rubric mapped to NeurIPS dimensions, how to reproduce safely, and AI-assisted-review etiquette. **Start here if you were asked to review.** |
| [`docs/PAPER.md`](docs/PAPER.md) | **Experimental design spec** — the science: all 7 RQs with falsifiable hypotheses, full factor table, scenario design rationale, threat-to-validity analysis, stats plan (bootstrap CIs, Friedman test, Cohen's κ), honesty caveats. Read this before interpreting any number. |
| [`REPRODUCE.md`](REPRODUCE.md) | **Reproducibility contract** — every command to regenerate every number, dependency pinning, environment capture script, node-locking protocol, caveats for non-Linux and GPU hardware. |
| [`docs/PLAN.md`](docs/PLAN.md) | **Operational how-to** — task taxonomy, scoring rubrics, judge backend configuration, watchdog, repeatability mechanics. |
| [`docs/TAXONOMY.md`](docs/TAXONOMY.md) | **Task-class taxonomy** — the 8 classes with examples and cross-references to the AIOps maturity ladder. |
| [`docs/TELEMETRY.md`](docs/TELEMETRY.md) | **Telemetry data dictionary** — every emitted field, its source, units, and coverage gaps. Aligned with OTel GenAI semantic conventions. |
| [`docs/MODELS.md`](docs/MODELS.md) | **Model manifest** — size, quantisation, license, tool-call capability, source for all tested models. |
| [`docs/MARKET.md`](docs/MARKET.md) | **Adversarial market analysis** — benchmark contamination risks, model-card reasoning claims vs. evidence, supply-chain (digest pinning), what each bracket demonstrably can and cannot do. |
| [`docs/analysis/`](docs/analysis/) | **Analysis notebooks + figures** — the sovereign quality × safety × energy story ([`wave_analysis.ipynb`](docs/analysis/wave_analysis.ipynb)) + judge agreement, with machine-readable exports in [`data/site/`](data/site) and a one-command static-site build ([`scripts/build-analysis-site.sh`](scripts/build-analysis-site.sh)). |
| [`data/SCENARIOS.md`](data/SCENARIOS.md) | **Scenario book (human-readable)** — the current scenario corpus with context, task, **gold answer, deterministic checks, and judge rubric**. Auto-generated from `scenarios.json` by [`render_scenarios.py`](render_scenarios.py); the file a human reviewer actually reads. |
| [`data/MODEL-PROMPTS.md`](data/MODEL-PROMPTS.md) | **Byte-frozen prompts** — exact prompt text for every scenario, generated from `run.build_prompt()`. Reproducibility requires these to be immutable after the run begins. |

---

## Repository layout

```
apprenticeops/
├── run.py               # main harness — inference loop, telemetry, quiesce, OTel schema
├── baselines.py         # non-LLM baselines (random, keyword, structural)
├── judge.py             # LLM-as-judge scoring, multi-backend, usage/billing capture
├── report.py            # markdown + CSV rollups, paper-ready tables
├── dataset.py           # flat ML-ready dataset export (features + labels)
├── calibrate.py         # hardware ceiling measurements (RAPL, membw, disk, observer overhead)
├── REPRODUCE.md         # reproducibility contract
├── requirements.txt     # analysis deps only; harness is stdlib-first
├── data/
│   ├── scenarios.json   # the benchmark corpus — 27 current scenarios
│   ├── models.txt       # model manifest (bracket, tag, quant)
│   └── MODEL-PROMPTS.md # byte-frozen prompt text
├── docs/
│   ├── PAPER.md         # experimental design spec
│   ├── PLAN.md          # operational how-to
│   ├── TAXONOMY.md      # task-class taxonomy
│   ├── TELEMETRY.md     # telemetry data dictionary
│   ├── MODELS.md        # vetted model list
│   └── MARKET.md        # adversarial analysis
└── scripts/
    ├── node-power.sh    # reproducible power state: setup / teardown / status
    └── run-experiment.sh # autonomous multi-stage experiment driver
```

---

## Honest limitations

**1. Judge egress.** We use Claude 4.8 off-node to *score* answers. The system-under-test never calls it. But the judge sees the scenario text, which contains real cluster detail: namespace names, Azure Key Vault references, Cloudflare DNS, `*.home.domain`. This is real ops data sent to a third party. Released scenarios are scrubbed and anonymised. This egress must be disclosed in any publication. See the public-service dependency map in [`docs/PAPER.md`](docs/PAPER.md).

**2. Grounded = oracle retrieval upper bound.** We inject the correct reference text directly into context. A real local-RAG pipeline adds retrieval error, chunking artifacts, and embedding drift. Our grounded numbers are the *ceiling* of what local retrieval can buy, not the expected value in a deployed system.

**3. Telemetry is Linux-specific.** Energy (RAPL), RAM/swap (`/proc`), and memory-bandwidth counters require Linux. The harness runs on macOS/Windows — quality scores reproduce; the systems telemetry will be empty. This is a documented limitation, not a bug.

**4. CPU-only inference.** The benchmark characterises inference on the *worst reasonable hardware*. On a machine with a discrete GPU or Apple Silicon, tok/s numbers will be higher and thermal behaviour different. The quality scores should generalise; the systems numbers will not.

**5. Single hardware point.** All systems measurements are from one specific node (i5-8350U, 24 GiB DDR4-2400). Hardware interaction effects may differ on different CPU generations, memory configurations, or NVMe speeds. We disclose the full environment in `ENVIRONMENT.md`.

---

## The AIOps maturity ladder

The broader motivation: where does a local small model sit on the path toward autonomous operations?

```
5 · Autonomous   — closed-loop self-healing, no human required
4 · Preventive   — acts to prevent known failure modes before they occur  
3 · Predictive   — forecasts failures from time-series signals
2 · Proactive    — acts ahead of user request, surface-triggered
1 · Reactive     — responds to incidents that have already occurred
    ↑
    This paper measures the quality and safety of the reasoning FOUNDATION
    at rung 1 (reactive) and the early boundary of rung 2 (proactive/foresee).
    Claiming higher rungs from these results would be overreach.
```

A model that can reliably detect, diagnose, and safely refuse on rung 1 has earned the right to be *considered* for higher-trust work. This benchmark provides the evidence base for that judgment — and makes the evidence falsifiable and reproducible.

---

## For reviewers

This repo is built to be **easy to review — including with AI assistance — with a
human in charge of the judgement.** If you were invited to review the paper, start
with **[`REVIEWER.md`](REVIEWER.md)**: it maps your assessment onto the NeurIPS
review dimensions (quality / clarity / significance / originality), tells you which
numbers reproduce on any laptop vs. which need the specific node, and covers
confidentiality etiquette for AI-assisted review.

> **arXiv is moderated, not peer-reviewed.** The first release is an arXiv preprint
> (a moderation check on scholarly standards and format — *not* peer review); the
> intended peer-reviewed venue is the **NeurIPS Datasets & Benchmarks track**.

## Use of AI in this work

This benchmark, its analysis, and its prose were produced with **substantial AI
assistance under human direction**. A human author directs the work and **takes full
responsibility for every claim, number, and line of code**, regardless of how it was
generated; no AI system is listed as an author. This follows arXiv's policy on
authors' use of generative-AI language tools. Every headline number is reproducible
from released artifacts ([`REPRODUCE.md`](REPRODUCE.md)), so the work can be checked
independently of the prose.

## Standards

- **Telemetry schema**: [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — `gen_ai.*` spans, metrics, events.
- **Judge pattern**: MT-Bench / AlpacaEval frontier-as-judge; two-family ensemble (Copilot + OpenAI) with Cohen's κ agreement.
- **Stats**: bootstrap 95% CIs; Friedman test for within-subject bracket comparison; Wilcoxon signed-rank for pairwise.
- **Baseline provenance**: [EleutherAI lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) — the open standard for repeatable LLM evaluation.

---

## Citation

```bibtex
@misc{hont2026apprenticeops,
  title   = {ApprenticeOps: Evaluating Small Locally-Sovereign LLMs as
             Homelab Operations Assistants},
  author  = {Hont, Dragos},
  year    = {2026},
  url     = {https://github.com/dragoshont/apprenticeops},
  note    = {Open benchmark and reproducible study. Apache 2.0.}
}
```

Update with venue and DOI after submission.

## License

Apache 2.0. See [`LICENSE`](LICENSE).

---

**Start here:** [`docs/PAPER.md`](docs/PAPER.md) for the research design, [`REPRODUCE.md`](REPRODUCE.md) to reproduce the results.

**Contribute:** issues and PRs welcome — especially new scenarios, additional models, and hardware configurations.

