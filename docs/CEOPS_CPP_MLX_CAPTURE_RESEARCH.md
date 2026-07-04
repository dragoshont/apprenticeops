# CEOps `llama.cpp` / MLX Capture Research

Status: source-backed research note, created 2026-07-04. This is a **stop-and-
think gate** for the `llama_cpp` long run. It records what the runtime ecosystem,
frontier APIs, and established eval/training tools expose that ApprenticeOps does
not yet fully capture.

## Current Run State

We stopped the clean R=5 run
`llama-cpp-evidence-5-strategy-pilot-6-none-baseline-llama_cpp-20260704-194603`
early, at `3/150` inference rows and `6/300` judged rows. The run is canceled and
must remain diagnostic only.

Stopping was correct: the prompt/distillation and timing fixes are in place, but
the deeper runtime research found additional `llama.cpp` server-only fields that
matter for optimization and future training data.

## Executive Verdict

The current subprocess adapter now captures enough for a **clean systems smoke**:
source provenance, exact prompt/message data, completions, judge labels, TTFT,
prefill/decode timing, row-level process resources, and `llama-bench` sidecars.

It still does **not** exhaust what `llama.cpp` can expose. The missing high-value
signals are mostly available through `llama-server`, not `llama-completion`:

- generated token IDs;
- per-token top logprobs/probabilities;
- processed prompt text after template/application;
- full generation settings as normalized by the runtime;
- prompt/cache metrics such as `tokens_cached`, `tokens_evaluated`, `cache_n`,
  prompt/decode token counts and timings;
- `/props` model/server settings, build info, slot count, chat template, default
  generation settings;
- `/metrics` Prometheus counters for prompt/generation tokens, seconds, decode
  calls, busy slots, and deferred/processing requests;
- `/slots` and slot save/restore if we later test prompt/KV cache persistence.

Therefore the next canonical implementation should be either:

1. a `llama_cpp_server` adapter for scenario rows; or
2. a required `llama-server` sidecar/probe per model and prompt-shape, with the
   current subprocess path marked **not exhaustive**.

For the long run we want option 1 unless it proves unstable in smoke.

## Sources Reviewed

| Source | Relevant finding |
|---|---|
| `llama.cpp` server docs | `/completion` supports `return_tokens`, `n_probs`, `completion_probabilities`, `generation_settings`, `tokens_cached`, `tokens_evaluated`, `truncated`, `timings`, `return_progress`, `timings_per_token`, `cache_prompt`, `n_cache_reuse`; `/props`, `/slots`, `/metrics`, `/tokenize`, `/apply-template`, and slot save/restore expose more runtime state. |
| `llama.cpp` bench docs | `llama-bench -o json/jsonl/sql` records build commit, build number, CPU/GPU/backend, model size/params, batch/ubatch, KV cache types, offload/mmap/direct-IO flags, prompt/gen sizes, avg/stddev ns and tok/s samples. |
| `llama.cpp` perplexity docs | Perplexity and KL-divergence workflows can save logits; useful for quantization/drift/calibration probes, but logit files are large. |
| MLX / MLX-LM docs | MLX exposes active/peak/cache memory, cache limits, wired memory limits, Metal capture/logging, compilation caching, `stream_generate`, custom samplers/logits processors, prompt caching, rotating KV cache, and fine-tuning support. |
| vLLM prefix caching docs | Prefix caching reuses KV blocks for shared prompt prefixes; benefits prefill, not decode. Useful fields: cache block/hash, cached tokens/blocks, prefix hash, evictions, cache salts, hit rate, TTFT/prompt latency delta. |
| OpenAI prompt caching docs | Cache hits depend on exact prefix matches; log `cached_tokens`, prompt token counts, prompt-cache key/retention, latency, and static/dynamic prompt split. |
| Anthropic prompt caching docs | Log `cache_creation_input_tokens`, `cache_read_input_tokens`, remaining `input_tokens`, TTL, cache breakpoints, and pre-warm behavior. Cache writes/read tokens explain cost/latency. |
| `lm-evaluation-harness` | Established eval practice: save configs, seeds, model args, `--log_samples` inputs/outputs, output paths, cache settings, and sample-level outputs for post-hoc analysis. |
| HELM | Reproducible transparent evaluation includes prompts/responses, multi-metric scores beyond accuracy, efficiency, and web UI inspection. |
| TRL SFT/DPO docs | SFT expects `messages` or `(prompt, completion)`; DPO expects `(prompt, chosen, rejected)` and logs logps/rewards/margins. Tool calling examples need `tools` columns. |
| SmolLM / SmolLM3 posts and discussions | SLM progress depends heavily on public data mixtures, synthetic data, reasoning traces, preference pairs, configs, training logs, intermediate checkpoints, and exact chat templates. Community questions focus on released datasets, W&B logs, tokenizer details, and chat template/mode formatting. |

## `llama-server` Probe

We ran a temporary `llama-server` probe against the staged LFM2 GGUF. The
non-streaming `/completion` response with `n_probs=5`, `return_tokens=true`,
`timings_per_token=true`, and `return_progress=true` included:

- `content`;
- `tokens` (`12` generated token IDs in the probe);
- `completion_probabilities` (`12` entries, each with generated token id,
  token text, logprob, bytes, and top-5 alternatives);
- `generation_settings` with normalized sampler/runtime settings;
- `timings` with `prompt_n`, `cache_n`, `prompt_ms`, `prompt_per_second`,
  `predicted_n`, `predicted_ms`, `predicted_per_second`, and per-token ms;
- `tokens_cached`, `tokens_evaluated`, `tokens_predicted`, `truncated`,
  `stop_type`, and `stopping_word`;
- `/metrics` counters such as `llamacpp:prompt_tokens_total`,
  `llamacpp:prompt_seconds_total`, `llamacpp:tokens_predicted_total`,
  `llamacpp:tokens_predicted_seconds_total`, `llamacpp:n_decode_total`,
  `llamacpp:n_tokens_max`, `llamacpp:requests_processing`,
  `llamacpp:requests_deferred`, and `llamacpp:n_busy_slots_per_decode`;
- `/props` with model path, `build_info=b9871-ef2d77011`, total slots, default
  generation settings, and sampler defaults.

This is stronger than the current subprocess row. The subprocess path gets
timings and process resources now, but it cannot see token alternatives,
`tokens_cached`, normalized generation settings, or server slot/cache state.

## Caching Findings

Caching is not a minor optimization; it changes the performance model.

| Cache concept | What to capture |
|---|---|
| Prompt / prefix cache hit | cached token count, evaluated token count, cache-hit ratio, cache miss/write tokens, cache read tokens. |
| Static vs dynamic prompt split | SHA and token count for stable prefix, SHA and token count for varying suffix. |
| Cache key / salt | cache key, prefix hash, cache salt/trust boundary, TTL/retention mode if applicable. |
| Latency benefit | TTFT, prompt/prefill time, total wall time with and without cache. |
| Throughput benefit | prompt tokens/s, predicted tokens/s, decode calls, busy slots, deferred requests. |
| Correctness invariant | output equivalence under cache hit vs cache miss, or explicit note that sampling/Batch can vary. |

Frontier APIs and vLLM agree on the core lesson: prefix/prompt caching improves
prefill and TTFT, not decode. A long-run dataset that wants optimization insight
should explicitly separate prefill savings from decode cost.

## Fine-Tuning / Distillation Findings

The prompt-capture fix moved us in the right direction: rows now carry prompt,
structured messages, output, judge labels, deterministic checks, and references.
For future training datasets, we should also emit derived export formats:

| Training use | Required shape |
|---|---|
| SFT / instruction tuning | `messages` or `(prompt, completion)` with assistant-only/completion-only target mask metadata. |
| DPO/APO/preference | `(prompt, chosen, rejected)` pairs. Chosen can be judge-high or teacher output; rejected can be low-scoring local output. Include judge score/evidence and deterministic checks. |
| Distillation | teacher model id, teacher prompt, teacher completion, local model completion, score/ranking, and optionally teacher logprobs. |
| Calibration / quantization drift | fixed calibration prompts, token IDs, per-token top logprobs/logits or `llama-perplexity` KL/PPL sidecars. |
| Tool-use training | `messages` plus `tools` schemas, tool calls, and tool results. |

We should not dump full logits for every scenario row by default. Logit files are
large; `llama.cpp` perplexity docs cite multi-GB binary logit files even for
standard corpora. Use a fixed calibration subset instead.

## Missing Capture Before Canonical Long Run

### BLOCKER — row-level `llama-server` response fields

The current subprocess rows do not capture token IDs, top logprobs, normalized
generation settings, `tokens_cached`, `tokens_evaluated`, `tokens_predicted`,
`truncated`, `stop_type`, or server-side timing objects.

**Fix:** implement a `llama_cpp_server` adapter or a required server-side
completion probe. For canonical long-run data, prefer `llama_cpp_server` so the
fields are attached to each scenario row.

### BLOCKER — cache measurement axis

The current run has no explicit cache-on/cache-off or repeated-prefix design.
Without it, we cannot make claims about prompt/prefix caching benefits like
frontier APIs, vLLM, or MLX-LM.

**Fix:** add a small cache micro-benchmark axis, separate from quality scoring:
same static prefix, varying suffix, cache off/on, capture `tokens_cached`,
`cache_n`, prompt time, TTFT, and output equivalence/variance.

### SHOULD-FIX — MLX track is not specified

If we later compare MLX on Apple Silicon, the MLX capture contract must include:
active memory, peak memory, cache memory, cache limit, wired limit, compile cache
behavior/recompile triggers, Metal capture/logging settings, prompt cache file,
rotating KV cache size, and stream/device placement.

### SHOULD-FIX — training exports are implicit

Rows now contain enough raw material for SFT/preference exports, but there is no
first-class exporter yet.

**Fix:** add scripts that materialize SFT JSONL and preference JSONL from judged
rows, preserving source run id, model id, scenario id, judge scores, checks, and
hashes.

## Decision

Do **not** resume the canceled R=5 run. Do **not** start the weeks-long all-model
run yet. The next engineering phase is runtime-capture expansion:

1. implement and smoke-test a `llama_cpp_server` adapter or equivalent row-level
   server capture;
2. add a cache micro-benchmark/capture axis;
3. add SFT/preference export scripts;
4. then rerun `llama-cpp-smoke-2` and `llama-cpp-evidence-5`.

Only after those pass should the long run be considered again.