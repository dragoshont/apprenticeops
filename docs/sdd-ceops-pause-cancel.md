# SDD: CEOps Pause And Cancel Semantics

Status: proposed for immediate implementation.
Date: 2026-06-27.
Scope: CEOps dashboard controls, `dashboard/backend/app.py`, `scripts/run-memory-batch.py`.

## 1. Scope Honesty

The Ollama runner does not checkpoint a model mid-request or mid-model. CEOps must
not present a true model-level pause. The honest operation is:

```text
Pause = stop active inference/judge work, discard the current incomplete model,
keep the batch/run resumable from that model.
```

Cancel is terminal: stop the active process tree and mark the current child and
queued children canceled.

## 2. User-Visible Outcome

When a run or memory batch is active, Experiment Control exposes:

- **Pause** with confirmation. The active model is discarded; completed models stay
  intact. Resume restarts the discarded model from its first scenario.
- **Resume** for paused work. For memory batches, the file-backed batch worker is
  relaunched against the existing batch-state file.
- **Cancel** with confirmation. Running and pending children become `canceled`.

## 3. Contract

Pause writes `data/runs/<RUN_ID>/.paused` and, for memory batches, sets the batch
state to `paused`. It trims rows for the last incomplete model from result and
judge JSONL files before resume.

Resume clears `.paused` and relaunches either the standalone `run-e2e.sh` path or
`scripts/run-memory-batch.py resume --batch-id <BATCH_ID>`.

Cancel writes `.canceled`, sets batch state to `canceled`, and does not resume.

## 4. Validation

- Existing memory-batch tests continue to pass.
- The dashboard shows a confirmation before Pause and Cancel.
- A paused batch has no `run.py`, `run-roster.sh`, `judge.py`, or
  `judge-scheduler.sh` process left running.
