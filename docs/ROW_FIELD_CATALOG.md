# ApprenticeOps Row Field Catalog

Status: generated field catalog. Regenerate with `scripts/generate-row-field-catalog.py` from an actual run artifact.

Source run: `llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-201750`

This file is generated from observed JSON artifacts plus `data/row-field-descriptions.json`. If a field is listed as undocumented, update the description map rather than editing this table by hand.

## Counts

| Artifact | Rows | Fields |
|---|---:|---:|
| Raw result rows | 12 | 276 |
| `samples[]` entries | 158 | 23 |
| Judged rows | 24 | 17 |
| `run.meta` rows | 1 | 36 |

## Raw Result Row Fields

| Field | Category | Type(s) | Non-null | Missing | Description |
|---|---|---|---:|---:|---|
| `adapter` | identity | str | 12 | 0 | Runtime adapter label stamped into snapshots and raw rows, for example ollama or llama_cpp. |
| `aiopslab_task` | scenario | str | 10 | 2 | AIOpsLab-inspired lifecycle/task mapping for the scenario. |
| `bracket` | model | null | 0 | 12 | Legacy footprint bracket from older rosters; current thesis tiering uses model_lock.* fields. |
| `class` | scenario | str | 12 | 0 | Scenario taxonomy class such as detect, diagnose, guard, test, expand, or upgrade. |
| `decode.dt_max_ms` | timing | float | 12 | 0 | Decode chunk/inter-token timing statistic captured from streaming output. |
| `decode.dt_p50_ms` | timing | float | 12 | 0 | Decode chunk/inter-token timing statistic captured from streaming output. |
| `decode.dt_p95_ms` | timing | float | 12 | 0 | Decode chunk/inter-token timing statistic captured from streaming output. |
| `decode_tok_s` | timing | float | 12 | 0 | Decode throughput metric. |
| `det_detail` | deterministic-quality | list | 12 | 0 | Deterministic scenario check result or check details. |
| `det_passed` | deterministic-quality | int | 12 | 0 | Deterministic scenario check result or check details. |
| `det_score` | deterministic-quality | float | 12 | 0 | Deterministic scenario check result or check details. |
| `det_total` | deterministic-quality | int | 12 | 0 | Deterministic scenario check result or check details. |
| `difficulty` | scenario | str | 12 | 0 | Author-assigned scenario difficulty label. |
| `disk.read_mb` | systems | float | 12 | 0 | Disk I/O summary for the request window. |
| `distill.example_schema` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.input_messages` | distillation | list | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.input_sha256` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.judge_rubric` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.judge_rubric_sha256` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.messages` | distillation | list | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.output_message` | distillation | dict | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.output_sha256` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.reference_answer` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.reference_answer_sha256` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `distill.reference_answer_source` | distillation | str | 12 | 0 | Fine-tuning/distillation helper field derived from prompt, reference, output, or labels. |
| `dnf` | reliability | bool | 12 | 0 | Did-not-finish flag. True rows are reliability failures, not missing data. |
| `effective.max_tokens` | policy | int | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.policy_reasons` | policy | list | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.retry_attempts` | policy | list | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.retry_count` | policy | int | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.retry_reason` | policy | null | 0 | 12 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.stall_s` | policy | int | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.timeout_policy_id` | policy | str | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `effective.timeout_s` | policy | int | 12 | 0 | Effective timeout/token/retry policy after scenario/model/runtime adjustments. |
| `env.cpu_governor` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.cpu_max_perf_pct` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.cpu_min_perf_pct` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.cpu_no_turbo` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.harness_artifact_dirty` | environment | bool | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.harness_dirty` | environment | bool | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.harness_git` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.harness_source_dirty` | environment | bool | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.host` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.inference_runtime` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.inference_strategy` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.kernel` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.llama_cpp_cli` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.llama_cpp_git_commit` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `env.llama_cpp_git_describe` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `env.llama_cpp_version` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `env.memory_context` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.memory_context_file` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `env.memory_context_sha` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `env.num_ctx` | environment | int | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.ollama_version` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.perf_core` | environment | bool | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.perf_event_paranoid` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.perf_membw` | environment | bool | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.rapl_domain` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.run_id` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.sample_interval_s` | environment | float | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.scenario_set` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.scenarios_path` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.scenarios_sha` | environment | str | 12 | 0 | Static or run-level environment/provenance field stamped by the runner. |
| `env.strategy_prompt_file` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `env.strategy_prompt_sha` | environment | null | 0 | 12 | Static or run-level environment/provenance field stamped by the runner. |
| `gen_ai.completion` | generation | str | 12 | 0 | Verbatim model answer retained for re-judging, transcript inspection, and distillation exports. |
| `gen_ai.input.messages` | generation | list | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.operation.name` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.output.messages` | generation | list | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.output.sha256` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.output.type` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.provider.name` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.frequency_penalty` | generation | float | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.max_tokens` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.model` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.presence_penalty` | generation | float | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.repeat_penalty` | generation | float | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.seed` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.stream` | generation | bool | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.temperature` | generation | float | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.top_k` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.request.top_p` | generation | float | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.response.finish_reasons` | generation | list | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.response.model` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.server.time_to_first_token_s` | generation | float | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.system_instructions` | generation | list | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.thinking` | generation | null | 0 | 12 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.thinking.chars` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.usage.input_tokens` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.usage.output_chars` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.usage.output_tokens` | generation | int | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gen_ai.usage.token_source` | generation | str | 12 | 0 | OpenTelemetry-style generative AI request, response, usage, or content field. |
| `gpu.peak_freq_mhz` | systems | int | 12 | 0 | GPU/iGPU observation used mainly to prove CPU-only or offload state. |
| `grounding` | scenario | str | 12 | 0 | Whether the scenario answer is derivable from supplied context or requires closed-book knowledge. |
| `http.exception` | http-forensics | null | 0 | 12 | HTTP runtime connection/content timing or exception field. |
| `llama_cpp.bench.backends` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.build_commit` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.build_number` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.cpu_info` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.cpu_mask` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.cpu_strict` | llama.cpp-bench | bool | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.devices` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.embeddings` | llama.cpp-bench | bool | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.fit_min_ctx` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.fit_target` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.flash_attn` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.gpu_info` | llama.cpp-bench | str | 0 | 12 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.main_gpu` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.model_filename` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.model_n_params` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.model_size` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.model_type` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_batch` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_cpu_moe` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_gen` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_gpu_layers` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_prompt` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_threads` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.n_ubatch` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.no_host` | llama.cpp-bench | bool | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.no_kv_offload` | llama.cpp-bench | bool | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.no_op_offload` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.path` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.poll` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.avg_ns` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.avg_ts` | llama.cpp-bench | float | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.n_depth` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.n_gen` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.n_prompt` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.samples_ns` | llama.cpp-bench | list | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.samples_ts` | llama.cpp-bench | list | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.stddev_ns` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.stddev_ts` | llama.cpp-bench | float | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.pp.test_time` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.repetitions` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.returncode` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.rows` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.sha256` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.split_mode` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.stderr_tail` | llama.cpp-bench | null | 0 | 12 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tensor_buft_overrides` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tensor_split` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.test_summaries` | llama.cpp-bench | list | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.avg_ns` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.avg_ts` | llama.cpp-bench | float | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.n_depth` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.n_gen` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.n_prompt` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.samples_ns` | llama.cpp-bench | list | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.samples_ts` | llama.cpp-bench | list | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.stddev_ns` | llama.cpp-bench | int | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.stddev_ts` | llama.cpp-bench | float | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.tg.test_time` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.type_k` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.type_v` | llama.cpp-bench | str | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.use_direct_io` | llama.cpp-bench | bool | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.bench.use_mmap` | llama.cpp-bench | bool | 12 | 0 | Parsed llama-bench calibration sidecar field for this model/runtime configuration. |
| `llama_cpp.cli` | llama.cpp | str | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.command_args` | llama.cpp | list | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.model_error` | llama.cpp | null | 0 | 12 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.model_path` | llama.cpp | str | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.proc.ctxt_invol` | llama.cpp-process | int | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.proc.ctxt_vol` | llama.cpp-process | int | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.proc.majflt` | llama.cpp-process | int | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.proc.max_rss_kb` | llama.cpp-process | int | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.proc.minflt` | llama.cpp-process | int | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.proc.system_s` | llama.cpp-process | float | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.proc.user_s` | llama.cpp-process | float | 12 | 0 | Child-process resource usage captured from os.wait4 for llama.cpp. |
| `llama_cpp.runtime_options` | llama.cpp | list | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.sampler.min_p` | llama.cpp-sampler | float | 12 | 0 | Sampler parameter parsed from llama.cpp stderr. |
| `llama_cpp.size_bytes` | llama.cpp | int | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.status` | llama.cpp | str | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.stderr_tail` | llama.cpp | str | 12 | 0 | llama.cpp runtime, model, command, sidecar, or error field. |
| `llama_cpp.timing.eval_s` | llama.cpp-timing | float | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.eval_tok_s` | llama.cpp-timing | float | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.eval_tokens` | llama.cpp-timing | int | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.load_s` | llama.cpp-timing | float | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.prompt_eval_s` | llama.cpp-timing | float | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.prompt_eval_tok_s` | llama.cpp-timing | float | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.prompt_eval_tokens` | llama.cpp-timing | int | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.timing.total_s` | llama.cpp-timing | float | 12 | 0 | Internal llama.cpp timing parsed from --perf stderr. |
| `llama_cpp.version` | llama.cpp | null | 0 | 12 | llama.cpp runtime, model, command, sidecar, or error field. |
| `mem.avail_start_mb` | systems-memory | int | 12 | 0 | Memory/RSS measurement for the request or runtime child process. |
| `mem.peak_rss_mb` | systems-memory | float | 12 | 0 | Memory/RSS measurement for the request or runtime child process. |
| `mem.rss_start_mb` | systems-memory | null | 0 | 12 | Memory/RSS measurement for the request or runtime child process. |
| `membw.peak_mb_s` | systems-memory | float | 12 | 0 | Memory-bandwidth measurement from perf/IMC counters. |
| `membw.requests` | systems-memory | dict | 12 | 0 | Memory-bandwidth measurement from perf/IMC counters. |
| `membw.series` | systems-memory | list | 12 | 0 | Memory-bandwidth measurement from perf/IMC counters. |
| `min_mem_avail_mb` | systems | int | 12 | 0 | Minimum value observed over the request window. |
| `model` | identity | str | 12 | 0 | Model deployment identifier requested for this row. |
| `model_lock.license` | model | str | 12 | 0 | Model metadata from the lockfile, such as parameter tier or license class. |
| `model_lock.license_class` | model | str | 12 | 0 | Model metadata from the lockfile, such as parameter tier or license class. |
| `model_lock.params_b` | model | float | 12 | 0 | Model metadata from the lockfile, such as parameter tier or license class. |
| `model_lock.tier` | model | str | 12 | 0 | Model metadata from the lockfile, such as parameter tier or license class. |
| `net.peak_kb_s` | systems-network | float | 12 | 0 | Network I/O invariant/summary for offline-local inference checks. |
| `net.total_kb` | systems-network | float | 12 | 0 | Network I/O invariant/summary for offline-local inference checks. |
| `ollama.ps.after` | ollama | dict | 12 | 0 | Ollama runtime metadata or compatibility placeholder. |
| `ollama.ps.before` | ollama | dict | 12 | 0 | Ollama runtime metadata or compatibility placeholder. |
| `pair_id` | scenario | str | 4 | 8 | Identifier for paired scenario variants when present. |
| `peak_swap_mb` | systems | int | 12 | 0 | Peak value observed over the request window. |
| `perf.core` | systems-perf | dict | 12 | 0 | perf-derived CPU or memory performance counters. |
| `phase.decode_s` | timing | float | 12 | 0 | Prompt/prefill/decode/thinking phase duration. |
| `phase.prefill_s` | timing | float | 12 | 0 | Prompt/prefill/decode/thinking phase duration. |
| `phase.think_s` | timing | null | 0 | 12 | Prompt/prefill/decode/thinking phase duration. |
| `power.energy_wh` | systems-power | float | 12 | 0 | Power and energy measurement for the request window. |
| `power.idle_watts` | systems-power | float | 12 | 0 | Power and energy measurement for the request window. |
| `power.mean_watts` | systems-power | float | 12 | 0 | Power and energy measurement for the request window. |
| `power.peak_dram_w` | systems-power | float | 12 | 0 | Power and energy measurement for the request window. |
| `power.peak_watts` | systems-power | float | 12 | 0 | Power and energy measurement for the request window. |
| `power.source` | systems-power | str | 12 | 0 | Power and energy measurement for the request window. |
| `prefill_tok_s` | timing | float | 12 | 0 | Prompt/prefill throughput metric. |
| `proc.ctxt_switches` | systems-process | int | 12 | 0 | Process-level page fault or context-switch summary. |
| `proc.majflt` | systems-process | int | 12 | 0 | Process-level page fault or context-switch summary. |
| `proc.minflt` | systems-process | int | 12 | 0 | Process-level page fault or context-switch summary. |
| `progress_trace` | timing | list | 12 | 0 | Cumulative output progress curve over wall time. |
| `prompt.capture.enabled` | prompt | bool | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.capture.policy` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.char_count` | prompt | int | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.estimated_tokens` | prompt | int | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.full` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.memory_char_count` | prompt | int | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.scenario_context_char_count` | prompt | int | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.sha256` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.task_char_count` | prompt | int | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.template_id` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.template_sha256` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.user_content` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `prompt.user_content_sha256` | prompt | str | 12 | 0 | Exact prompt, prompt hash, prompt section counts, or prompt-capture policy field. |
| `rep` | design | int | 12 | 0 | Repeat index for variance runs. |
| `reset.cpu_freq_mhz` | reset-state | int | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.cpu_governor` | reset-state | str | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.cpu_no_turbo` | reset-state | str | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.cpu_temp_c` | reset-state | float | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.load1` | reset-state | float | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.mem_avail_mb` | reset-state | int | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.ok` | reset-state | bool | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.perf_event_paranoid` | reset-state | str | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.running_procs` | reset-state | int | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.swap_used_mb` | reset-state | int | 12 | 0 | Per-model reset-state evidence captured before model inference. |
| `reset.top_proc` | reset-state | null | 0 | 12 | Per-model reset-state evidence captured before model inference. |
| `reset.warnings` | reset-state | null | 0 | 12 | Per-model reset-state evidence captured before model inference. |
| `samples` | timeseries | list | 12 | 0 | Per-request sampler time series; see samples[] field catalog. |
| `scenario` | identity | str | 12 | 0 | Scenario identifier. |
| `scenario.context_sha256` | scenario | str | 12 | 0 | Scenario content/check/reference hash captured for reproducibility and distillation. |
| `scenario.deterministic_checks_sha256` | scenario | str | 12 | 0 | Scenario content/check/reference hash captured for reproducibility and distillation. |
| `scenario.gold_answer_sha256` | scenario | str | 12 | 0 | Scenario content/check/reference hash captured for reproducibility and distillation. |
| `scenario.judge_rubric_sha256` | scenario | str | 12 | 0 | Scenario content/check/reference hash captured for reproducibility and distillation. |
| `scenario.question_sha256` | scenario | str | 12 | 0 | Scenario content/check/reference hash captured for reproducibility and distillation. |
| `seed` | design | int | 12 | 0 | Sampling seed for this repeat. |
| `socket_exception` | http-forensics | null | 0 | 12 | Legacy socket exception or stall classification field. |
| `stall.phase` | reliability | null | 0 | 12 | Did-not-finish stall phase/classification field. |
| `stall_phase` | reliability | null | 0 | 12 | Did-not-finish stall phase/classification field. |
| `strategy.candidate_count` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.candidates` | strategy | list | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.extra_calls` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.failure_mode` | strategy | null | 0 | 12 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.id` | strategy | str | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.prompt_sha256` | strategy | null | 0 | 12 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.sample_index` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.selected_candidate` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.selection_method` | strategy | str | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.total_input_tokens` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.total_output_tokens` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.total_retry_count` | strategy | int | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.total_wall_s` | strategy | float | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `strategy.version` | strategy | str | 12 | 0 | Inference-strategy metadata, candidate details, or selected-candidate trace. |
| `swap.start_mb` | systems-memory | int | 12 | 0 | Swap measurement at request start or peak. |
| `temp` | design | float | 12 | 0 | Sampling temperature used for this row. |
| `thermal.peak_c` | systems-thermal | float | 12 | 0 | Thermal state before or during the request. |
| `thermal.start_c` | systems-thermal | float | 12 | 0 | Thermal state before or during the request. |
| `think` | design | bool | 12 | 0 | Whether thinking/reasoning mode was requested. |
| `ts` | identity | float | 12 | 0 | Unix timestamp when the row was written. |
| `wall_s` | timing | float | 12 | 0 | End-to-end row wall-clock duration in seconds. |
| `warmup_err` | runtime | null | 0 | 12 | Model warmup duration or warmup error. |
| `warmup_s` | runtime | float | 12 | 0 | Model warmup duration or warmup error. |

## Sample Fields

| Field | Category | Type(s) | Non-null | Missing | Description |
|---|---|---|---:|---:|---|
| `core_freq` | sample-cpu | list | 158 | 0 | Per-sample CPU core utilization, frequency, or power. |
| `core_util` | sample-cpu | list | 146 | 12 | Per-sample CPU core utilization, frequency, or power. |
| `core_w` | sample-cpu | float | 146 | 12 | Per-sample CPU core utilization, frequency, or power. |
| `cpu_freq_mhz` | sample-cpu | int | 158 | 0 | Per-sample aggregate CPU utilization, frequency, or temperature. |
| `cpu_temp_c` | sample-cpu | float | 158 | 0 | Per-sample aggregate CPU utilization, frequency, or temperature. |
| `cpu_util_pct` | sample-cpu | float | 146 | 12 | Per-sample aggregate CPU utilization, frequency, or temperature. |
| `ctxt_invol` | sample-process | null | 0 | 158 | Per-sample context switch counter when a runtime process is attached. |
| `ctxt_vol` | sample-process | null | 0 | 158 | Per-sample context switch counter when a runtime process is attached. |
| `disk_mb_s` | sample-io | float | 146 | 12 | Per-sample disk I/O rate. |
| `dram_w` | sample-power | float | 146 | 12 | Per-sample DRAM RAPL power. |
| `gpu_freq_mhz` | sample-gpu | int | 158 | 0 | Per-sample integrated GPU frequency or activity signal. |
| `load1` | sample-system | float | 158 | 0 | Per-sample system load average. |
| `majflt` | sample-process | null | 0 | 158 | Per-sample major page fault counter. |
| `mem_avail_mb` | sample-memory | int | 158 | 0 | Per-sample memory availability or pressure field. |
| `minflt` | sample-process | null | 0 | 158 | Per-sample minor page fault counter. |
| `net_kb_s` | sample-network | float | 146 | 12 | Per-sample non-loopback network I/O rate. |
| `rapl_watts` | sample-power | float | 146 | 12 | Per-sample RAPL package power. |
| `rss_mb` | sample-process | null | 0 | 158 | Per-sample runtime child RSS when attached. |
| `swap_used_mb` | sample-memory | int | 158 | 0 | Per-sample swap usage. |
| `t` | sample-time | float | 158 | 0 | Seconds since request sampler start. |
| `threads` | sample-time | null | 0 | 158 | Seconds since request sampler start. |
| `uncore_w` | sample-power | float | 146 | 12 | Per-sample uncore RAPL power. |
| `watts` | sample-power | null | 0 | 158 | Per-sample smart-plug power if configured. |

## Judged Row Fields

| Field | Category | Type(s) | Non-null | Missing | Description |
|---|---|---|---:|---:|---|
| `adapter` | identity | str | 24 | 0 | Runtime adapter label stamped into snapshots and raw rows, for example ollama or llama_cpp. |
| `criteria_met` | judge | list | 13 | 11 | Judge criteria list for met or missed requirements. |
| `criteria_missed` | judge | list | 22 | 2 | Judge criteria list for met or missed requirements. |
| `evidence` | judge | str | 24 | 0 | Judge explanation/evidence for the score and verdict. |
| `inference_runtime` | run-meta | str | 24 | 0 | Run-level selected inference runtime or strategy. |
| `inference_strategy` | run-meta | str | 24 | 0 | Run-level selected inference runtime or strategy. |
| `judge_backend` | judge | str | 24 | 0 | Judge backend/model/configuration field. |
| `judge_model` | judge | str | 24 | 0 | Judge backend/model/configuration field. |
| `memory_context` | run-meta | str | 24 | 0 | Run-level memory context id/path/hash field. |
| `model` | identity | str | 24 | 0 | Model deployment identifier requested for this row. |
| `rep` | design | int | 24 | 0 | Repeat index for variance runs. |
| `scenario` | identity | str | 24 | 0 | Scenario identifier. |
| `scenarios_path` | run-meta | str | 24 | 0 | Run metadata or judged-row scenario file path/hash field. |
| `scenarios_sha256` | run-meta | str | 24 | 0 | Run metadata or judged-row scenario file path/hash field. |
| `score` | judge | int | 24 | 0 | Judge ordinal score for the answer. |
| `usage` | judge | null | 0 | 24 | Judge backend usage object when available; null for Copilot CLI judge rows that do not report token usage. |
| `verdict` | judge | str | 24 | 0 | Judge natural-language verdict for the answer. |

## Run Metadata Fields

| Field | Category | Type(s) | Non-null | Missing | Description |
|---|---|---|---:|---:|---|
| `class_counts` | run-meta | dict | 1 | 0 | Run metadata count of scenarios by class. |
| `difficulty_counts` | run-meta | dict | 1 | 0 | Run metadata count of scenarios by difficulty. |
| `expect` | run-meta | int | 1 | 0 | Number of models the consumer expects to fully persist for this run. |
| `grounding_counts` | run-meta | dict | 1 | 0 | Run metadata count of scenarios by grounding label. |
| `inference_runtime` | run-meta | str | 1 | 0 | Run-level selected inference runtime or strategy. |
| `inference_strategy` | run-meta | str | 1 | 0 | Run-level selected inference runtime or strategy. |
| `judges` | run-meta | int | 1 | 0 | Expected number of judges per inference row. |
| `llama_cpp_extra_args` | run-meta | str | 1 | 0 | run.meta llama.cpp selection, map, hash, or argument field. |
| `llama_cpp_model_map` | run-meta | str | 1 | 0 | run.meta llama.cpp selection, map, hash, or argument field. |
| `llama_cpp_model_map_sha256` | run-meta | str | 1 | 0 | run.meta llama.cpp selection, map, hash, or argument field. |
| `max_tokens_cap` | run-meta | int | 1 | 0 | Run-level max-token cap override, usually present only for smoke runs. |
| `memory_context` | run-meta | str | 1 | 0 | Run-level memory context id/path/hash field. |
| `memory_context_file` | run-meta | null | 0 | 1 | Run-level memory context id/path/hash field. |
| `memory_context_sha256` | run-meta | null | 0 | 1 | Run-level memory context id/path/hash field. |
| `model_set` | run-meta | str | 1 | 0 | Run matrix model-set id selected for the run. |
| `models` | run-meta | str | 1 | 0 | Run metadata for selected model list path, count, or hash. |
| `models_count` | run-meta | int | 1 | 0 | Run metadata for selected model list path, count, or hash. |
| `models_sha256` | run-meta | str | 1 | 0 | Run metadata for selected model list path, count, or hash. |
| `reps` | run-meta | int | 1 | 0 | Repeat count for the run. |
| `run_allow_unlocked` | run-meta | bool | 1 | 0 | Run metadata override or execution flag. |
| `run_id` | run-meta | str | 1 | 0 | Run identifier. |
| `run_repeats_override` | run-meta | int | 1 | 0 | Run metadata override or execution flag. |
| `run_temp_override` | run-meta | float | 1 | 0 | Run metadata override or execution flag. |
| `scenario_count` | run-meta | int | 1 | 0 | Run metadata for selected scenario set, scenario count, or scenario ids. |
| `scenario_ids` | run-meta | list | 1 | 0 | Run metadata for selected scenario set, scenario count, or scenario ids. |
| `scenario_set` | run-meta | str | 1 | 0 | Run metadata for selected scenario set, scenario count, or scenario ids. |
| `scenarios` | run-meta | str | 1 | 0 | Run metadata or judged-row scenario file path/hash field. |
| `scenarios_sha256` | run-meta | str | 1 | 0 | Run metadata or judged-row scenario file path/hash field. |
| `schema_version` | run-meta | int | 1 | 0 | run.meta schema version. |
| `started_at` | run-meta | int | 1 | 0 | Unix timestamp when run metadata was created. |
| `strategy_candidate_count` | run-meta | int | 1 | 0 | Run metadata for selected inference strategy prompt or candidate count. |
| `strategy_prompt_file` | run-meta | null | 0 | 1 | Run metadata for selected inference strategy prompt or candidate count. |
| `strategy_prompt_sha256` | run-meta | null | 0 | 1 | Run metadata for selected inference strategy prompt or candidate count. |
| `sync_mode` | run-meta | str | 1 | 0 | Producer source sync mode, for example origin or working-tree. |
| `timeout_policy_id` | run-meta | str | 1 | 0 | Timeout policy id used by the runner. |
| `user` | run-meta | str | 1 | 0 | Dashboard/auth user label that launched the run. |
