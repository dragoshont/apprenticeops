# CEOps Runtime Agent Deployment Plan

Status: implementation-backed plan, 2026-07-04. This document defines the
deployable runtime-agent contract for ApprenticeOps / CEOps. It is not a new
benchmark result. It records the configuration surface that lets the same
pipeline run through either `ollama` or `llama_cpp`, with this deployment using
`llama_cpp` for experiment smoke and future locked thesis runs.

## Outcome

After this plan is implemented, an operator can launch a run from the dashboard
using a server-approved runtime adapter, and every run surface records which
runtime was used:

```text
Deployment = model_set + scenario_set + memory_context + inference_strategy
           + inference_runtime + runtime_config + hardware_profile
           + evaluation_policy
```

For the current homelab deployment, `inference_runtime=llama_cpp` is the default
dashboard selection and `ollama` remains available for service/API and legacy
snapshot reproduction.

## Configuration Contract

The source of truth is `data/run-matrix.json`.

| Field | Purpose | Current value / rule |
|---|---|---|
| `defaults.inference_runtime` | Dashboard default runtime. | `llama_cpp` |
| `runtime_options[]` | Server-owned runtime allowlist. | `llama_cpp`, `ollama` |
| `model_sets[].runtime` | Optional required runtime for a model set. | `llama-cpp-smoke-5` requires `llama_cpp` |
| `model_sets[].llama_cpp_model_map` | Direct GGUF path map for `llama_cpp`. | `data/llama-cpp-smoke-5.model-map.json` |
| `model_sets[].llama_cpp_artifacts` | Staged artifact/hash manifest. | `data/llama-cpp-smoke-5.artifacts.json` |
| `model_sets[].llama_cpp_extra_args` | Server-owned subprocess args. | `-t 4 -c 1024` for smoke |
| `model_sets[].run_repeats` | Non-canonical smoke repeat override. | `1` for smoke only |
| `model_sets[].max_tokens_cap` | Non-canonical smoke token cap. | `96` for smoke only |
| `llama-cpp-evidence-5` | First non-smoke mini-wave using the staged GGUFs. | Default locked `R=5`, no token cap |

The browser submits only ids. Paths, subprocess args, repeat overrides, and token
caps are resolved by the backend from `data/run-matrix.json` and then shell-quoted
before launch. A `llama_cpp` launch without a server-owned model map fails closed.

## Implemented Phases

| Phase | State | Evidence |
|---|---|---|
| Runtime preflight on AI node | done | Homelab role `ceops_runtime_agent`; `ceops-runtime-check --min-gguf 5` passes. |
| llama.cpp toolchain provenance | done | `LLAMA_CPP_GIT_COMMIT=ef2d770117db45b05aa7ecd1b0acca36370c5470` stamped by `/etc/profile.d/ceops-runtime.sh`. |
| Direct-GGUF smoke artifact lock | done | `data/llama-cpp-smoke-5.artifacts.json` records filenames, sizes, hashes, and license classes. |
| Runner adapter | done | `INFERENCE_RUNTIME=llama_cpp` uses the non-interactive llama.cpp subprocess backend, default `llama-completion`. |
| Dashboard launch contract | done | Backend validates `inference_runtime`; frontend shows runtime options and passes runtime ids. |
| UI runtime evidence | done | Current-run scope, session rows, input inspector, node cards, and launch receipt expose runtime/adapter information. |

## Smoke Evidence

The runtime path has been proven with bounded smoke runs, not canonical thesis
evidence. The latest adapter-aware smoke used:

- `model_set=llama-cpp-smoke-5`
- `scenario_set=strategy-pilot-6`
- `inference_runtime=llama_cpp`
- `RUN_REPEATS=1`
- `MAX_TOKENS_CAP=96`

The smoke produced rows with `adapter=llama_cpp`, `env.inference_runtime=llama_cpp`,
`llama_cpp.cli=/usr/local/bin/llama-completion`, and `finish=stop` for every row.

After the first evidence mini-wave exposed dirty producer-source provenance, we
made canonical producer launches use `SYNC_MODE=origin` by default and added a
two-model validation set, `llama-cpp-smoke-2`. The latest dashboard-launched
validation run
`llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-190623`
passed the runtime and capture checks after the telemetry remediation:

- `run.meta.sync_mode=origin`;
- `12/12` inference rows and `24/24` judged rows;
- `adapter=llama_cpp`, `env.inference_runtime=llama_cpp`, and `finish=stop` for every row;
- `reset.ok=True` for `12/12` rows;
- `env.harness_git=2575ec5` and `env.harness_source_dirty=false` for every row;
- TTFT, prefill, decode jitter, timing-derived token counts, row-level process
  RSS/fault/context-switch metrics, and `llama-bench` sidecar hashes populated;
- `env.harness_artifact_dirty=true`, as expected once generated `results.*`,
  `logs/`, and `outputs/` exist in the producer checkout.

The follow-up prompt-capture smoke
`llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-194150`
validated the training/distillation data shape:

- `env.harness_git=8641e33` and `env.harness_source_dirty=false`;
- `222` raw fields;
- `prompt.full`, `prompt.sha256`, `gen_ai.system_instructions`,
  `gen_ai.input.messages`, and `gen_ai.output.messages` populated for `12/12`
  rows;
- `distill.messages`, `distill.reference_answer`, reference hashes, and output
  hashes populated for `12/12` rows;
- strict quality report passed and persistence was clean.

> **Scope honesty:** the smoke proves deployability and telemetry plumbing. It is
> intentionally rejected by `scripts/audit-run.py` as paper evidence because the
> locked protocol requires R=5.

## Evidence Mini-Wave

The first non-smoke `llama_cpp` evidence phase is recorded in
`docs/CEOPS_LLAMA_CPP_EVIDENCE_PHASE.md` and exposed as
`model_set=llama-cpp-evidence-5`. It deliberately reuses the same staged direct
GGUF artifacts as the smoke, but removes the smoke-only overrides. A successful
mini-wave must therefore produce 150 inference rows for
`strategy-pilot-6` (`5 models x 6 scenarios x R=5`) and pass both
`scripts/report-run-quality.py --strict` and `scripts/audit-run.py` before any
result is promoted beyond diagnostic runtime evidence.

## Remaining Work Before Canonical llama.cpp Evidence

The data-capture gate is reviewed in
`docs/CEOPS_DATA_CAPTURE_ADVERSARIAL_REVIEW.md` and deepened in
`docs/CEOPS_CPP_MLX_CAPTURE_RESEARCH.md`. Those documents are now the source of
truth for what must be fixed before a weeks-long all-model `llama_cpp` run.

| Task | Gate |
|---|---|
| Decide and implement row-level `llama-server` capture. | Scenario rows capture token IDs, top logprobs/probs, normalized generation settings, cache fields, `/props`/`/metrics` evidence, or the run is explicitly labelled subprocess-only. |
| Add cache measurement axis. | Cache-on/off or repeated-prefix micro-benchmark records `tokens_cached`, cache read/write/evaluated tokens, prefix hashes, prompt time, TTFT, and output-equivalence checks. |
| Fill `llama_cpp` telemetry gaps. | Streaming timing, child-process RSS/faults/threads, runtime/tokenizer token counts or explicit approximation labels, and `llama-bench -o jsonl` sidecars are present. |
| Fill prompt/distillation capture gaps. | Exact serialized prompt, structured input/output messages, reference answer hashes, and distillation message triples are present. |
| Re-run the locked mini-wave with clean producer source provenance. | `env.harness_source_dirty=false` on every row, plus strict quality and audit gates. |
| Avoid monitoring SSH sessions during reset windows. | `reset.ok=True` on every row. |
| Decide whether the mini-wave is judged. | If judged, `report-run-quality.py --strict` passes for inference + judge rows. |
| Promote result only after review. | Docs label it locked `llama_cpp` evidence, not smoke. |

## Failure Modes Addressed

- `llama-cli` enters conversation mode for chat-template models; the runtime
  adapter defaults to `llama-completion` and `-no-cnv --simple-io` instead.
- `ollama` service pre-pulls can exhaust disk; default service pulls are kept
  small and experiment GGUFs are staged under `/srv/llama.cpp/models`.
- Smoke runs must not be interpreted as canonical evidence; `audit-run.py` checks
  the repeat set against the locked manifest.
- Runtime identity must be visible; raw rows, snapshots, run metadata, sessions,
  and UI surfaces all carry the adapter/runtime label.
- Producer source provenance matters; canonical launches now default to
  `SYNC_MODE=origin`, and use `env.harness_source_dirty`, not the aggregate
  `env.harness_dirty`, as the source-cleanliness gate.