# Weeks-Long Inference Readiness Audit - 2026-07-05

Status: live readiness audit, not a benchmark result. This document records the
state of the ApprenticeOps harness after the `llama.cpp` subprocess,
`llama.cpp` server, scenario-lifecycle, and AI-node-only runner hardening work.

## 1. Scope Honesty

The question is not whether the harness can produce rows. It can. The question is
whether it is ready to run for days or weeks without this Mac or a human terminal
session keeping it alive.

There are two valid modes:

1. **AI-node-only inference**: runs entirely on `ai` with `run-roster.sh` through
   the local-roster worker. It downloads missing models, runs the locked preflight,
   resets between models, emits rows and sidecars, and removes models it pulled
   after they complete. It does **not** judge or commit results, because the
   current judge backend lives on `home`.
2. **Full judged pipeline**: `home` orchestrates and judges; `ai` performs locked
   inference. This is the evidence path for judged results and GitHub experiment
   branches.

The user request targets mode 1: autonomous inference on `ai` only. That is the
right gate before spending weeks of CPU time.

## 2. Current Capture Contract

Observed field counts from recent runs:

| Runtime regime | Representative run | Raw fields | Sample fields | Judge fields | Run-meta fields | Sidecars |
|---|---|---:|---:|---:|---:|---:|
| `llama_cpp` subprocess | `timeout-risk-clean-20260704-210054` | 276 | 23 | 17 | 36 | 0 server sidecars |
| `ollama` service | `bracket5-2-core-20260704-221337` | 244 | 23 | 17 | 38 | 0 server sidecars |
| `llama_cpp_server` | `llama-server-smoke-20260704-232755` | 233 | 23 | 17 | 38 | 6 server sidecars |

Interpretation: direct `llama_cpp` currently has the widest top-level row because
it includes subprocess timing/process data and `llama-bench` summaries. The
server adapter deliberately pushes the full token/logprob payload into per-row
sidecars so the main JSONL stays bounded.

## 3. Code And Documentation Audit

| Area | Current state | Finding | Action |
|---|---|---|---|
| Runtime adapters | `ollama`, `llama_cpp`, `llama_cpp_server` implemented. | Good, but docs must keep them separate. | Keep reporting faceted by `env.inference_runtime`. |
| Direct GGUF model identity | Artifact manifest path/hash and per-model GGUF checksum/license fields are captured. | Good for direct GGUF rows. | Keep manifests in `data/llama-cpp-*.artifacts.json`. |
| Scenario source/lifecycle | Core 20 has explicit `lifecycle` metadata; rows stamp `scenario.lifecycle.*`. | Good for stratified analysis and source-trace honesty. | Add lifecycle metadata to future scenario packs before promotion. |
| AI-only inference | `run-roster.sh` already supports model pull, preflight, reset, telemetry, `--rm-after`, and resume. `run-memory-batch.py --runner local-roster` provides a file-backed worker. | Mostly ready, but local mirroring needed output/log completeness. | Patch local mirror and validate with 3 small models. |
| Judging | Full judging still depends on `home` and Copilot CLI. | Expected. AI-only mode is inference-only. | Do not claim AI-only judged evidence unless a local judge is later added. |
| Field catalog | Generated catalog exists for a direct-GGUF smoke. | Useful but runtime-specific. | Regenerate after final chosen runtime smoke. |
| `audit-run.py` | Now honors `run.meta` repeat count for validation runs. | Good. | Use it after each stop-and-audit batch. |

## 4. Readiness Verdict

Current verdict: **ready for a longer AI-node-only inference run**, with the
judged/full-evidence path still requiring the two-node `home + ai` pipeline.

The AI-only gate passed after fixing two local-roster metadata bugs:

- environment values passed to `subprocess.Popen(env=...)` are now stringified;
- `run.meta` now honors the selected model-set repeat override instead of
  defaulting validation runs to the canonical R=5.

The successful smoke was `ai-local-small-20260704-235715-m1`: `3` models × `6`
scenarios × `R=1`, all on `ai` with `runner=local-roster`, no home-side scheduler,
and no Mac dependency after launch. `report-run-quality.py --strict` passed
(`18/18` rows, no judged rows expected), and `audit-run.py` passed. The run
mirrored `18` answer files plus logs under `data/runs/<RUN_ID>/`, and wrote `3`
model completion markers.

This proves the inference cycle. A weeks-long **judged** run still uses the
two-node e2e path because the judge and GitHub persistence live on `home`.

## 5. AI-Only Smoke Result

Smoke command shape:

```text
runner=local-roster
model_set=ai-local-small-3
scenario_set=strategy-pilot-6
memory_context=none
inference_strategy=baseline
inference_runtime=ollama
repeats=1
```

Observed result:

- Run id: `ai-local-small-20260704-235715-m1`.
- Rows: `18/18`.
- Judged rows: `0`, expected because `judge_expected=false`.
- Strict report: PASS.
- Audit: PASS.
- Reliability: `0` DNF, `1` length finish, `0` zero-output stalls.
- Mirrored artifacts: `18` answer files and driver logs.
- Done markers: `3`, one per model.
- Prepared-model behavior: all three models were already present on disk and
  remained present after the run, which is the correct `--rm-after` behavior for
  pre-existing prepared models.

This smoke did **not** prove deletion of newly pulled transient models, because
the selected models were already prepared locally. That delete path is already in
`run.py` (`was_present` + `--rm-after`) and has been used in prior roster work,
but a future disk-pressure smoke should include one deliberately absent tiny model
if we want an explicit fresh-pull deletion proof.

## 6. Deferred Work

Deferred, not required for the AI-only smoke:

- local/offline judging on `ai`;
- converting `run-roster.sh` to a systemd service;
- scaling `llama_cpp_server` from smoke to the full direct-GGUF roster;
- regenerating the row field catalog from the final chosen runtime after the
  next successful smoke.

These are useful, but they should not block the immediate AI-only inference
cycle test.