# AGENTS.md — how to run the ApprenticeOps experiment pipeline

This repo benchmarks ≤8B CPU-only local LLMs as homelab ops assistants. The
experiment is a **two-node, two-scheduler pipeline** that runs **autonomously**:
one command launches it and it keeps running after you disconnect. Full design:
[docs/EXPERIMENT-PIPELINE.md](docs/EXPERIMENT-PIPELINE.md); determinism + reproduction:
[REPRODUCE.md](REPRODUCE.md).

## Topology

| Node | Role | Notes |
|---|---|---|
| **home** (hostname `home`) | orchestrator + judge + git | runs the schedulers, judges via the Copilot CLI, commits to GitHub |
| **ai** (`home-ai.home.domain`, hostname `ai`) | **locked inference only** | i5-8350U, ollama **0.30.8**, Turbo off, governor performance |

`home → ai` is **passwordless SSH**. `home` holds the repo clone at
`~/apprenticeops`, has `gh` SSH auth, and the Copilot CLI. **After launch the pipeline
runs entirely on home + ai — no workstation/Mac is in the loop.**

## Run it — the ONE command (from `home`, in `~/apprenticeops`)

```bash
# DRY RUN (2 tiny models, full end-to-end validation):
RUN_ID=e2e-$(date -u +%Y%m%d-%H%M) MODELS=data/models.dryrun.txt \
  setsid nohup ./scripts/run-e2e.sh >/tmp/e2e.boot 2>&1 </dev/null &

# FULL RUN (the 158-model roster):
RUN_ID=roster-$(date -u +%Y%m%d-%H%M) MODELS=data/models.txt \
  setsid nohup ./scripts/run-e2e.sh >/tmp/e2e.boot 2>&1 </dev/null &
```

`run-e2e.sh` launches **both** schedulers detached and returns immediately:
- **producer** (inference) on `ai` — `run-from-homelab.sh` → `run-roster.sh`: locks the
  node, runs the preflight, **resets the environment before every model**, infers all
  scenarios × reps, and appends each finished model to `results.<RUN_ID>.jsonl.done`.
- **consumer** (judge + commit) on `home` — `judge-scheduler.sh`: watches the `.done`
  marker, pulls each finished model, judges it (**claude-opus-4.6 + gpt-5.4** via the
  Copilot CLI), and commits to the `experiment/<RUN_ID>` branch.

The `setsid nohup … </dev/null &` wrapper is what makes it **detach from your SSH
session** — verified: the launch returns the same second it starts, and a fresh
connection shows it still running.

Code sync mode: dashboard/dev launches default to `SYNC_MODE=working-tree`, which
mirrors the deployed home checkout to `ai` so a validated local change is not
silently replaced by `origin/main`. For canonical paper runs, commit and push
first, then launch with `SYNC_MODE=origin`; rows stamp `env.harness_git` and
`env.harness_dirty` so the regime is auditable.

## Run the memory axis autonomously

Use this when the question is: run the same model and scenario set with multiple
memory contexts as separate sequential runs. The worker is file-backed under
`data/run-batches/<BATCH_ID>/`, holds a single lock, and advances one memory context
at a time so the `ai` node is never double-booked.

From **home** (full CEOps pipeline: inference on `ai`, judge + commit on `home`):

```bash
BATCH_ID=mem-dryrun-core-$(date -u +%Y%m%d-%H%M%S)
setsid nohup python3 scripts/run-memory-batch.py launch \
  --batch-id "$BATCH_ID" \
  --model-set dryrun \
  --scenario-set core-current \
  --memory-context none \
  --memory-context homelab-okf-v1 \
  --runner e2e \
  >/tmp/${BATCH_ID}.boot 2>&1 </dev/null &
```

From **ai only** (portable inference-only runner on an identical node checkout):

```bash
BATCH_ID=mem-dryrun-core-$(date -u +%Y%m%d-%H%M%S)
setsid nohup python3 scripts/run-memory-batch.py launch \
  --batch-id "$BATCH_ID" \
  --model-set dryrun \
  --scenario-set core-current \
  --memory-context none \
  --memory-context homelab-okf-v1 \
  --runner local-roster \
  >/tmp/${BATCH_ID}.boot 2>&1 </dev/null &
```

`--runner local-roster` calls `run-roster.sh` on the current node, so it still uses
the locked preflight, model download, per-model reset/quiesce, telemetry, and
`--rm-after` behavior. It does **not** run the home-side Copilot judge/commit
scheduler; use `--runner e2e` when judged results and commits are required.

## Run the inference-strategy axis

Strategy is separate from memory. Use it when the question is whether extra
inference-time work helps the same model and scenario set. Available strategies:
`baseline`, `single_call_tournament_brief`, `best_of_3_detcheck`,
`self_consistency_3`, and `evaluator_optimizer_1`.

```bash
RUN_ID=strategy-pilot-$(date -u +%Y%m%d-%H%M%S) \
  MODEL_SET=strategy-pilot-2 MODELS=data/models.strategy-pilot-2.txt \
  SCENARIO_SET=strategy-pilot-6 SCENARIOS=data/scenario_sets/strategy-pilot-6.json \
  MEMORY_CONTEXT=none INFERENCE_STRATEGY=best_of_3_detcheck \
  setsid nohup ./scripts/run-e2e.sh >/tmp/strategy-pilot.boot 2>&1 </dev/null &
```

After a run, check reliability before interpreting quality:

```bash
python3 scripts/report-run-quality.py data/runs/<RUN_ID>
```

The report shows DNF/stall/length, zero-output stalls, judge-empty rows, and
judge token usage. Multi-candidate strategies preserve candidate completions as
sidecar artifacts committed with the model evidence.

## Watch progress (read-only, any time, any session)

```bash
RUN_ID=<id> ./scripts/run-e2e.sh progress     # one snapshot: producer + consumer
RUN_ID=<id> ./scripts/run-e2e.sh watch        # live, refreshes every 20s
git log --oneline experiment/<RUN_ID>          # one commit per judged model
```

Logs on **home**, all under `data/runs/<RUN_ID>/`: `e2e.log`, `judge-scheduler.log`,
`judge.log`, `pipeline-ledger.jsonl` (the per-model S1→S7 trace), `judge-scheduler.status`.
Producer logs on **ai**: `logs/<RUN_ID>/`.

## Stop / restart

```bash
# stop (use the bracket trick — see gotchas):
pkill -9 -f '[j]udge-scheduler'; pkill -9 -f '[j]udge.py'
ssh home-ai.home.domain "pkill -9 -f '[r]un-roster'; pkill -9 -f '[r]un.py'"
# restart: just run the ONE command again. The producer is MODEL-LEVEL RESUMABLE
# (skips already-complete models) and the consumer skips already-judged models —
# re-launching the same RUN_ID continues where it stopped.
```

## Prerequisites (one-time; already provisioned on these nodes)

- **ai:** passwordless `sudo`, `rsync`, ollama 0.30.8, `node-power.sh` can lock the box.
- **home:** `node` **and** `copilot` symlinked into `/usr/local/bin` (the Copilot CLI is a
  `#!/usr/bin/env node` script, so a detached daemon's PATH must resolve **both**),
  `gh` SSH auth, `rsync`, `jq`, `flock`.

## Browser verification (mission-control dashboard)

When verifying the dashboard in a browser — screenshots or the Playwright MCP — use
**Microsoft Edge** (`--browser msedge`), **not Chrome** (Chrome isn't installed on this
Mac). The Playwright MCP is pinned to Edge in `sideport/.vscode/mcp.json`. The dev
backend serves the built UI at `http://127.0.0.1:8770` (`uvicorn app:app` from
`dashboard/backend`); the durable copy is `https://ceops.home.domain`.

## Gotchas (learned the hard way — do not relearn them)

- **Detach:** always launch long jobs with `setsid nohup CMD >log 2>&1 </dev/null &`.
  A plain backgrounded SSH command holds the channel and the launch never returns.
- **Killing:** `pkill -f run.py` **matches its own shell's command line** and `-9`
  kills your SSH session before it acts. Use the bracket trick: `pkill -9 -f '[r]un.py'`.
- **`rsync` must exist on BOTH nodes** — the consumer pulls results/outputs from ai.
- The consumer is **flock-guarded** (one instance per RUN_ID) and **idempotent**
  (`judge.py` skips done rows); the producer is **resumable at model granularity**.
- Judges are **CLI-gated**: the headless `copilot` CLI exposes up to
  `claude-opus-4.6` / `gpt-5.4` (4.8/5.5 are VS Code IDE-only). True 4.8/5.5 judging
  needs `JUDGE_BACKEND=anthropic` + key or GitHub Models.
- **Judging runs 8-wide** by default (`JUDGE_WORKERS=8`, the Copilot-CLI concurrency
  ceiling before it rate-limits — see `docs/CONSOLIDATION-PLAN.md`). Set lower if the
  CLI throttles, `1` for serial. This is what keeps the 158-model judge in hours, not days.

## Determinism (why a run is reproducible)

`run.py --preflight-only` **refuses to start** unless the node matches
`data/run-manifest.json` (Turbo off, governor performance, `min/max_perf_pct=100`,
RAPL `package-0`, perf readable, **ollama 0.30.8**, the `scenarios.json` hash). The
environment is reset and re-verified before every model (`reset.*` evidence stamped
per row), and the run aborts (exit 4) if the node drifts mid-run. See REPRODUCE.md §3.
