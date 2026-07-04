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

> **Scope honesty:** the smoke proves deployability and telemetry plumbing. It is
> intentionally rejected by `scripts/audit-run.py` as paper evidence because the
> locked protocol requires R=5.

## Remaining Work Before Canonical llama.cpp Evidence

| Task | Gate |
|---|---|
| Launch a locked mini-wave with `RUN_REPEATS=5` and no smoke token cap. | `scripts/audit-run.py` passes without the R=1 failure. |
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