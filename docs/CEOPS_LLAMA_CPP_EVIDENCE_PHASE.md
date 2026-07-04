# CEOps llama.cpp Evidence Phase

Status: pre-registered mini-wave, created 2026-07-04. This page is the evidence
ledger for the first non-smoke `llama_cpp` run. It exists to keep smoke proof,
runtime evidence, and paper evidence separate.

## Scope

This phase uses the five staged direct-GGUF models already locked for the runtime
smoke:

- `data/models.llama-cpp-smoke-5.txt`
- `data/llama-cpp-smoke-5.model-map.json`
- `data/llama-cpp-smoke-5.artifacts.json`

The launch surface is `model_set=llama-cpp-evidence-5` in
`data/run-matrix.json`. It uses `inference_runtime=llama_cpp`, the
non-interactive `llama-completion` adapter, `strategy-pilot-6`, and the default
locked repeat count `R=5`. It does **not** use the smoke token cap.

This is a mini-wave, not the full thesis roster. Passing it permits us to treat
the deployed `llama_cpp` path as evidence-capable; it does not replace the future
full <=5B-parameter thesis run.

## Pre-Launch Gate

Before launch:

1. `data/run-matrix.json` validates as JSON and contains exactly one
   `llama-cpp-evidence-5` entry.
2. The model set requires `runtime=llama_cpp` and declares a server-owned
   `llama_cpp_model_map`.
3. The model set does not declare `run_repeats`, `max_tokens_cap`, or
   `run_allow_unlocked`.
4. `ceops-runtime-check --min-gguf 5` passes on `home-ai.hont.ro`.
5. The clean dashboard checkout on `home` is at `origin/main` before launch.

## Quality Gate

The result may be interpreted only if all of these pass:

| Gate | Required result |
|---|---|
| Runtime identity | `run.meta.inference_runtime=llama_cpp`, model-map hash present. |
| Row count | `5 models x 6 scenarios x 5 reps = 150` inference rows. |
| Judge count | `300` judged rows for two judges, unless judging is explicitly skipped and documented. |
| Reliability | DNF, zero-output stalls, length failures, parse errors, and duplicate tuples are zero. |
| Judge integrity | Empty judge rows, missing evidence, and missing criteria are zero. |
| Persistence | `.push-pending` is empty and the `experiment/<RUN_ID>` branch is pushed. |
| Protocol audit | `scripts/audit-run.py` passes for the mirrored result JSONL. |
| Reset evidence | `reset.ok` is true for every row, or every warning is explicitly caveated. |

If any gate fails, the run remains diagnostic evidence and must not be promoted to
paper/thesis evidence.

## Launch Record

| Field | Value |
|---|---|
| Run id | not yet launched |
| Model set | `llama-cpp-evidence-5` |
| Scenario set | `strategy-pilot-6` |
| Memory context | `none` |
| Inference strategy | `baseline` |
| Runtime | `llama_cpp` |
| Launch path | dashboard API from `/home/dragos/apprenticeops-runtime-agent` |

## Result Summary

Not yet run.
