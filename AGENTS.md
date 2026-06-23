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
| **ai** (`home-ai.hont.ro`, hostname `ai`) | **locked inference only** | i5-8350U, ollama **0.30.8**, Turbo off, governor performance |

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
ssh home-ai.hont.ro "pkill -9 -f '[r]un-roster'; pkill -9 -f '[r]un.py'"
# restart: just run the ONE command again. The producer is MODEL-LEVEL RESUMABLE
# (skips already-complete models) and the consumer skips already-judged models —
# re-launching the same RUN_ID continues where it stopped.
```

## Prerequisites (one-time; already provisioned on these nodes)

- **ai:** passwordless `sudo`, `rsync`, ollama 0.30.8, `node-power.sh` can lock the box.
- **home:** `node` **and** `copilot` symlinked into `/usr/local/bin` (the Copilot CLI is a
  `#!/usr/bin/env node` script, so a detached daemon's PATH must resolve **both**),
  `gh` SSH auth, `rsync`, `jq`, `flock`.

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

## Determinism (why a run is reproducible)

`run.py --preflight-only` **refuses to start** unless the node matches
`data/run-manifest.json` (Turbo off, governor performance, `min/max_perf_pct=100`,
RAPL `package-0`, perf readable, **ollama 0.30.8**, the `scenarios.json` hash). The
environment is reset and re-verified before every model (`reset.*` evidence stamped
per row), and the run aborts (exit 4) if the node drifts mid-run. See REPRODUCE.md §3.
