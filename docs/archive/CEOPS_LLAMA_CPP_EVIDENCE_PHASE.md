# CEOps llama.cpp Evidence Phase

Status: completed mini-wave, created and run on 2026-07-04. This page is the
evidence ledger for the first non-smoke `llama_cpp` run. It exists to keep smoke
proof, runtime evidence, and paper evidence separate.

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
| Run id | `llama-cpp-evidence-5-strategy-pilot-6-none-baseline-llama_cpp-20260704-150059` |
| Model set | `llama-cpp-evidence-5` |
| Scenario set | `strategy-pilot-6` |
| Memory context | `none` |
| Inference strategy | `baseline` |
| Runtime | `llama_cpp` |
| Launch path | dashboard API from `/home/dragos/apprenticeops-runtime-agent` |

## Pre-Launch Evidence

| Check | Result |
|---|---|
| Local JSON/runtime/scenario gates | PASS: `python3 -m json.tool data/run-matrix.json`, `scripts/validate-runtime-policy.py`, `scripts/validate-scenarios.py`. |
| Paper-data audit | PASS: `scripts/audit-paper-data.py`. |
| Dashboard frontend build | PASS: `npm --prefix dashboard/frontend run build`. |
| Live clean checkout | PASS: `/home/dragos/apprenticeops-runtime-agent` at `95c696f` on `main...origin/main`. |
| Live run matrix | PASS: API exposes `llama-cpp-evidence-5` with `runtime=llama_cpp` and no smoke repeat/token overrides. |
| AI runtime preflight | PASS: `ceops-runtime-check --min-gguf 5` on `home-ai.hont.ro`. |
| Active pipeline contention | PASS before launch: `home=0`, `ai=0`. |
| Semantic pre-launch judge | UNAVAILABLE: subagent runner failed with `spawn EBADF`; no semantic PASS is claimed. |

## Result Summary

The run passed the pre-registered quality gate. We can use it as evidence that
the deployed `llama_cpp` path is **evidence-capable** for this five-model slice.
We do not treat it as the full thesis roster.

| Check | Result |
|---|---|
| Inference rows | PASS: `150/150`. |
| Judged rows | PASS: `300/300`. |
| Strict quality report | PASS: `scripts/report-run-quality.py --strict data/runs/<RUN_ID>`. |
| Protocol audit | PASS: `scripts/audit-run.py data/runs/<RUN_ID>/_mirror/results.<RUN_ID>.jsonl --scenarios data/scenario_sets/strategy-pilot-6.json`. |
| Reliability | PASS: DNF `0/150`, length finishes `0`, zero-output stalls `0`, parse errors `0`, duplicate tuples `0`. |
| Judge integrity | PASS: empty judge rows `0`, missing evidence `0`, missing criteria `0`. |
| Runtime identity | PASS: adapter `llama_cpp`, `env.inference_runtime=llama_cpp`. |
| Reset evidence | PASS: `reset.ok` true for `150/150` rows. |
| Persistence | PASS: dashboard API reported `state=done`, clean persistence, `committed_count=5/5`, `push_pending_count=0`. |
| Experiment branch | PASS: `experiment/llama-cpp-evidence-5-strategy-pilot-6-none-baseline-llama_cpp-20260704-150059` pushed. |

## Post-Run Audit Notes

We performed a second, read-only audit after the official gates. It verified the
raw tuple set, judged tuple set, runtime stamps, reset fields, judge coverage,
and AI-node GGUF availability.

| Check | Result |
|---|---|
| Raw tuple coverage | PASS: exactly `5 models x 6 scenarios x 5 reps`, with no duplicate or missing `(model, scenario, rep)` tuples. |
| Judged tuple coverage | PASS: exactly two judges, `claude-opus-4.6` and `gpt-5.4`, for every raw tuple. |
| Raw artifact hash | `b5258211a333b29d0611b9349ca0640ed4a3ad0dae6bec271fba6a610595b020`. |
| Judged artifact hash | `ca4de2bbe0888e2858c242c42865baca59b57d2db7af036ae8c0ede9591c37ca`. |
| AI-node GGUF paths | PASS via `dragos@home.hont.ro -> home-ai.hont.ro`: all five `data/llama-cpp-smoke-5.model-map.json` paths exist with nonzero size. |
| Judge usage accounting | CAVEAT: all `300/300` judged rows have `usage=null`; the Copilot CLI judge produced scores/evidence/verdicts, but token usage was not captured. |
| Judge criteria arrays | CAVEAT: some rows have empty `criteria_met` or empty `criteria_missed`, but no row has both empty; official quality reports `criteria_missing=0`. |
| Producer source provenance | CAVEAT: raw rows stamp `env.harness_git=51ec19e` with `env.harness_dirty=true`, `env.harness_source_dirty=true`, and `env.harness_artifact_dirty=true` for `150/150` rows. |

## Remediation Test

We fixed the launch path so canonical producer launches default to
`SYNC_MODE=origin`, record `sync_mode` in `run.meta`, and route `AI_REPO` to the
same clean runtime-agent path as `REPO_DIR` unless explicitly overridden. We then
ran a dashboard-launched two-model validation:

| Field | Value |
|---|---|
| Run id | `llama-cpp-smoke-2-strategy-pilot-6-none-baseline-llama_cpp-20260704-182852` |
| Model set | `llama-cpp-smoke-2` |
| Scenario set | `strategy-pilot-6` |
| Runtime | `llama_cpp` |
| Sync mode | `origin` |
| Rows | PASS: `12/12` inference rows, `24/24` judged rows. |
| Source provenance | PASS: `env.harness_git=163cb12`, `env.harness_source_dirty=false` for every row. |
| Artifact provenance | Expected: `env.harness_artifact_dirty=true` after generated run artifacts appeared in the checkout. |
| Strict quality | PASS: `report-run-quality.py` found zero DNF, stalls, missing fields, duplicate tuples, judge-empty rows, missing evidence, or missing criteria. |
| Protocol audit | Expected smoke failure: `audit-run.py` rejects R=1 because the locked manifest requires R=5. |

> **Limit.** This is a valid mini-wave, not a population-level model result. It
> validates the runtime path, capture quality, reset discipline, and judging
> pipeline for the staged five direct-GGUF models under `strategy-pilot-6`.
> Because the AI-node producer checkout was dirty, it is not a clean-source
> canonical thesis run; any paper use must carry that caveat plainly.
> The remediation smoke shows the source-provenance defect is fixed for future
> launches; it does not retroactively make this mini-wave clean-source canonical.
