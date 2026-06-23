# Experiment pipeline — two independent schedulers, one deterministic run

> **Status:** plan persisted 2026-06-24. This is the authoritative design for the
> full roster run. Low-level run mechanics live in [REPRODUCE.md](../REPRODUCE.md)
> §3; this doc is the **orchestration architecture** (who runs what, how the two
> schedulers decouple, determinism, branch/commit, recovery).

## 1. Goal

Run the **whole model list once**, deterministically, on a locked CPU node, and
evaluate every model with the 2‑judge pair **as soon as it finishes** — without a
human babysitting it. The producer (inference) and the consumer (judge + commit)
are **two independent schedulers**: either can crash and restart on its own, and
we probe progress whenever we have time. There are **no "waves"** — one canonical
list, run once, resumable at model granularity.

## 2. Topology (verified 2026-06-24)

| Role | Node | Identity | Does | Has |
|---|---|---|---|---|
| **AI node** (producer) | `home-ai.hont.ro` (hostname `ai`) | i5‑8350U, 4C/8T, 24 GB, **ollama 0.30.8** | **inference only**, locked + offline | ollama, the locked power state |
| **Home node** (consumer/orchestrator) | hostname `home`, user `dragos` | x86_64 | **judge + git + orchestration** | git, gh (authed `dragoshont`, ssh), python 3.12, **GitHub Copilot CLI 1.0.36**, rsync, jq |

`home → ai` is **passwordless SSH** (key authorized, host key trusted). The home
node holds the repo clone, runs the judges through the Copilot CLI, and commits
data to GitHub. **Everything is driven from the home node**; the AI node is a
headless inference worker it reaches over SSH.

```
            home node (orchestrator + judge + git)
   ┌──────────────────────────────────────────────────────────┐
   │  Producer control            Consumer scheduler           │
   │  (launch/monitor on ai) ───▶ (judge + commit, independent)│
   │         │ ssh                       ▲   │ copilot CLI      │
   │         │                           │   │ (claude-opus-4.6 │
   │         ▼                    .done   │   │  + gpt-5.4)      │
   │   ╔═══════════╗   rsync results/ ┌───┴─┐ │                 │
   │   ║  AI node  ║ ───────────────▶ │pull │ ▼  commit+push    │
   │   ║  ollama   ║   outputs/       └─────┘ ─────────────▶ GitHub
   │   ║ (locked)  ║                          experiment branch │
   │   ╚═══════════╝                                            │
   └──────────────────────────────────────────────────────────┘
```

## 3. Determinism contract (every run)

A run is reproducible because the node is **locked and proven**, not assumed:

- **Engine pinned:** ollama **0.30.8**; the preflight refuses to start if the node's
  engine drifts (`env.ollama_version` is stamped into every row).
- **Power locked:** `node-power.sh setup` → Turbo off, governor `performance`,
  `min/max_perf_pct=100`, RAPL `package-0`, `perf_event_paranoid≤2`. The preflight
  (`run.py --preflight-only`) **refuses to run** on any drift (exit 3).
- **Protocol fixed:** temp `0.7`, seeds `seed_base + rep` (reps 5), `num_ctx 8192`,
  `think=false`, and the `scenarios.json` content hash — all asserted by the preflight.
- **Reset before EACH model:** between models `quiesce()` resets the environment
  (fan‑max cool to target °C, `drop_caches`, `swapoff/swapon`, compact); the next
  model stamps **`reset.*` evidence** into its rows (cpu_no_turbo, freq, temp,
  mem_avail, swap, load1, procs, perf_paranoid + `reset.ok`/`reset.warnings`) — a
  dirty start is flagged, never silently accepted.
- **Mid‑run drift guard:** volatile env is re‑read **before every model**; the run
  **aborts (exit 4)** if the node moves (e.g. thermald re‑enables Turbo) instead of
  mislabelling rows. Re‑lock and resume — rows already written are fine.
- **Self‑describing data:** every row carries `env.*` (host, kernel, ollama_version,
  harness_git, cpu_no_turbo, governor, rapl_domain, num_ctx, run_id, scenarios_sha)
  and `reset.*`, so the regime is auditable from the data alone.

## 4. The pipeline — seven named stages

Every model flows through the **same fixed pipeline**. These names are the shared
vocabulary for the **code (log + status), the docs, and the paper** — use them
everywhere so the implementation and the write-up describe the same thing.

| # | Stage | Node | What | Guarantee |
|---|---|---|---|---|
| S1 | `lock` | ai | preflight asserts the node matches the frozen manifest | refuse-to-run determinism gate |
| S2 | `reset` | ai | quiesce + capture `reset.*` evidence | proven-identical start per model |
| S3 | `infer` | ai | all scenarios × reps; telemetry + deterministic (safety/energy) scores | the measurement |
| S4 | `emit` | ai | append the model to `…done` | per-model completion event (the handoff) |
| S5 | `collect` | home | rsync the model's rows + answer texts | data off the node, durably |
| S6 | `judge` | home | 2-judge pair (claude-opus-4.6 + gpt-5.4) | the quality axis |
| S7 | `persist` | home | merge + commit to the experiment branch + push | versioned, off-node evidence |

**S1–S4 are the *measurement* stage** (the producer, on the locked node);
**S5–S7 are the *evaluation* stage** (the consumer, on home). They are decoupled by
the S4 event, so the pipeline **streams**: while model *N* is in `judge`/`persist`,
model *N+1* is already in `reset`/`infer`. Per-model granularity is what makes the
pipeline **resumable** (restart at the next model that hasn't reached S4) and
**incrementally durable** (S7 commits each model the moment it is evaluated).

**How to explain it in the paper / docs.** *"Each model is evaluated through a fixed,
instrumented pipeline. A measurement stage runs on a power-locked CPU node under a
frozen environment manifest (Turbo off, governor fixed, RAPL domain pinned) and
resets and re-verifies the environment before every model so each starts from a
proven-identical state (`reset.*` evidence recorded per row). A decoupled evaluation
stage scores each model's outputs with a two-judge LLM ensemble plus deterministic
checks and persists results per model. The two stages communicate through a
per-model completion event, making the pipeline streaming, resumable, and
idempotent."* The per-model **pipeline ledger** (§4d) is the reproducibility
appendix: it shows every model traversed the identical S1→S7 sequence.

### 4a. Producer — inference scheduler, stages S1–S4 (runs ON `ai`)
`scripts/run-roster.sh` → `run.py`. Locks the node, preflight must pass, then runs
`data/models.txt` one model at a time through all **24 scenarios × 5 reps**.

- **Idempotent + resumable at MODEL level:** on start it scans the results file and
  **skips any model already complete** (has a row for every scenario×rep). A crash
  mid‑roster restarts from the next incomplete model — no repeated compute. A
  half‑finished model is re‑run from scratch; the duplicate partial rows are
  harmless and collapse in dedup.
- **Handoff signal:** when a model finishes all its scenarios, run.py appends one
  line to **`results.<RUN_ID>.jsonl.done`** (`{model, bracket, ts, units}`). This is
  the only coupling to the consumer.
- **Outputs:** `results.<RUN_ID>.jsonl`, `outputs/<model>__<scenario>__rN.txt`
  (+ `.think.txt`), `logs/<RUN_ID>/`.
- Runs **detached** (nohup/systemd) on `ai`. It knows nothing about the judge.

### 4b. Consumer — judge + commit scheduler (runs ON `home`)
`scripts/judge-scheduler.sh` *(to build)*. A long‑running loop, **independent
lifecycle**:

1. Pull new `.done` entries + the corresponding result rows + `outputs/` for newly
   complete models from `ai` (rsync over SSH).
2. For each completed model **not yet judged**, run the **2‑judge pair** via the
   Copilot CLI — `JUDGE_BACKEND=copilot judge.py --judge --ensemble copilot:gpt-5.4`
   (primary `claude-opus-4.6` + ensemble `gpt-5.4`) — on that model's answer texts.
   (These are the strongest Claude + GPT judges this Copilot CLI build exposes;
   `judge_model` is recorded per row.)
3. Store the judged rows on `home` (the clone).
4. **Commit that model** to the experiment branch and **push** to GitHub.
5. Sleep, repeat.

- **Idempotent:** tracks which models are already judged (the judged file is the
  source of truth + judge.py itself skips done rows); safe to `kill -9` and restart.
- It knows nothing about the producer's internals — only the `.done` marker + the
  pulled data.

### 4c. Decoupling
The `.done` marker (S4) is the entire contract. The producer never blocks on the
judge; the consumer consumes at its own pace. Both recover from durable on‑disk
state (results file, `.done` marker, judged file) — classic producer/consumer.

### 4d. Pipeline ledger (the stage trace)
`scripts/judge-scheduler.sh` appends one line per **stage transition** to
`data/runs/<RUN_ID>/pipeline-ledger.jsonl` — `{model, stage, ts, ok, detail}` for
`collect`/`judge`/`persist` — which, combined with the producer's per-row `reset.*` +
`env.*` and the `.done` (`emit`) event, reconstructs the full S1→S7 trace for every
model. The ledger is both the **operational status board** (probe = tail the last
lines per model) and the **paper's reproducibility trace** (proof that every model
executed the identical pipeline). It never holds secrets.

## 5. Branch, commit & secrets

- **Dedicated experiment branch:** `experiment/<RUN_ID>` (e.g.
  `experiment/roster-20260624-1200`). All experiment data lands there, never `main`.
- **Per‑model commits:** after each model is judged + stored, commit + push to the
  experiment branch — incremental, off‑node durability and a visible heartbeat
  (`git log` the branch = progress). ~158 commits over ~1 week.
- **Merge to `main`** after the full run completes and is reviewed (~1 week).
- **Secrets:** the Copilot CLI auth lives on `home` (already authenticated); `gh`
  uses SSH. **No tokens, keys, or passwords are ever committed.** Raw judge logs
  (`.tmp/judge/`) stay gitignored; only the **merged judged data** + the committed
  **judge‑pairs CSV** are versioned. Large artifacts (`results.*.jsonl`, `outputs/`)
  are gzipped in commits to keep the repo sane.

## 6. Observability — "probe whenever"

Both schedulers write a **status file** + heartbeat so a check never disturbs them:
- AI node: `logs/<RUN_ID>/driver.log` + the per‑model `reset.*` health summary.
- Home node: `judge-scheduler.status` (last action, current model, judged/total) + log.
- GitHub: `git log experiment/<RUN_ID>` — one commit per judged model.

## 7. Recovery / idempotency summary

| Failure | Behaviour |
|---|---|
| Producer crash / node reboot | Re‑lock (`node-power.sh setup`) + relaunch → **resumes at the next incomplete model**. |
| Node drifts mid‑run (Turbo back on) | Producer **aborts (exit 4)** with "re‑lock and resume"; no mislabelled rows. |
| Consumer crash | Restart → **skips already‑judged models**, picks up pending `.done` entries. |
| Re‑run the whole thing | Idempotent: complete models skipped, partials re‑run, dedup collapses duplicates. |

## 8. Open decisions (defaults chosen — override if needed)

- **Branch name:** `experiment/<RUN_ID>`. *(default)*
- **Commit granularity:** per‑model. *(default — matches "commit as soon as you have data")*
- **Large artifacts:** gzip `results.*.jsonl` + `outputs/` in commits. *(default)*
- **Scheduler mechanism:** detached `nohup` loops with PID/lock + status files now;
  can be promoted to `systemd` units for auto‑restart on reboot. *(default: nohup)*

## 9. How to run

**One command, fully autonomous + detached** (from `home`, in `~/apprenticeops`):

```bash
# dry run (2 tiny models, full end-to-end):
RUN_ID=e2e-$(date -u +%Y%m%d-%H%M) MODELS=data/models.dryrun.txt \
  setsid nohup ./scripts/run-e2e.sh >/tmp/e2e.boot 2>&1 </dev/null &
# full run: MODELS=data/models.txt
```

`scripts/run-e2e.sh` launches **both** schedulers (producer on `ai`, consumer on
`home`) detached and returns immediately; the run survives your disconnect. Watch it
from any session with `RUN_ID=<id> ./scripts/run-e2e.sh progress` (or `watch`), and see
per-model commits with `git log --oneline experiment/<RUN_ID>`. Full operator runbook:
[AGENTS.md](../AGENTS.md).

**Status (validated on a 2-model dry run):** S1 `lock` → S2 `reset` → S3 `infer` →
S4 `emit` (producer) and S5 `collect` → S6 `judge` → S7 `persist` (consumer) all run
end-to-end and detached. Built: the two schedulers, the `run-e2e.sh` orchestrator +
progress view, model-level resume, the flock single-instance guard, the ollama 0.30.8
pin, the 24-scenario corpus, and the SWOT / retrieval paper sections (§8e / §12).
