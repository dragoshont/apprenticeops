# ApprenticeOps · Mission Control

A small **Vite + React** dashboard over the two-node experiment pipeline. It does
not compute anything itself: a thin **FastAPI** backend runs
[`scripts/pipeline-status.py`](../scripts/pipeline-status.py) on the `home` node
over SSH (home already mirrors the producer's results from `ai`) and serves that
JSON, plus a few control verbs. The React app polls `/api/status` every few
seconds and renders the pipeline, node health, per-model progress, a Pareto plot
(quality vs energy), and the live judge activity feed.

```
browser ──HTTP──▶ FastAPI (backend/app.py) ──ssh──▶ home ──python──▶ pipeline-status.py
                                                      └──ssh──▶ ai  (control + telemetry)
```

## What it shows

- **Pipeline** — the seven stages S1–S7 (lock → reset → infer → emit on `ai`;
  collect → judge → persist on `home`) with the live stage highlighted.
- **Producer / Consumer** — result rows, models emitted, judge rows, models
  judged & committed, against the batch's expected total.
- **Nodes** — `home` and `ai` health (load, memory, disk; on `ai` also turbo
  off / governor / live frequency / ollama version).
- **Models** — every model in flight with its current stage.
- **Pareto** — per-model mean judge quality vs Wh/answer as data accrues.
- **Activity / Skips** — the pipeline ledger and any judge skips.

## Controls

- **Start** — pick a **batch** (`dryrun` = 2 small models, `full` = the roster)
  and launch `run-e2e.sh` on home detached. Batches come from
  [`data/batches.json`](../data/batches.json).
- **Pause / Resume** — best-effort `SIGSTOP` / `SIGCONT` of the schedulers + the
  inference process (the ollama server is separate, so it is a soft hold).
- **Stop** — kill the producer (ai) and consumer (home) process trees.
- **Re-launch** — restart the same `RUN_ID`; the pipeline is model-level
  resumable, so it continues where it stopped.

## Run it — dev (on the Mac)

Two terminals. The backend SSHes to home via your `homelab` alias.

```bash
# 1) backend
cd dashboard/backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
HOME_SSH=homelab AI_SSH=home-ai.hont.ro REPO_DIR='~/apprenticeops' \
  python -m uvicorn app:app --reload --port 8770

# 2) frontend (proxies /api + /ws to :8770)
cd dashboard/frontend
npm install
npm run dev          # → http://127.0.0.1:5290
```

## Run it — container

```bash
cd dashboard
docker compose up --build      # → http://127.0.0.1:8770
```

The container mounts `~/.ssh` read-only and uses `HOME_SSH=home`, so your ssh
config must define a `Host home` (and `home` must itself reach `home-ai.hont.ro`
passwordlessly, which it already does).

## Trust model (v0.1)

Single-operator, trusted-LAN tool. Binds to localhost, **no auth**. Every
privileged action shells into `home` over SSH, so whoever can reach the backend
can drive the run. The client may only choose a server-validated *batch id* and
*run id*; nothing it sends is interpolated raw into a shell. Do not expose it to
an untrusted network.
