# AGENTS.md — how to run the ApprenticeOps experiment pipeline

This repo benchmarks CPU-only local LLM deployments as homelab ops assistants.
The doctoral target is open-weight models up to **5B parameters**; older
footprint-bounded experiment snapshots may include larger 7B/8B models and must
be labelled as legacy evidence. The
experiment is a **two-node, two-scheduler pipeline** that runs **autonomously**:
one command launches it and it keeps running after you disconnect. Full design:
[docs/EXPERIMENT-PIPELINE.md](docs/EXPERIMENT-PIPELINE.md); determinism + reproduction:
[REPRODUCE.md](REPRODUCE.md).

## Analysis & paper integrity — lessons (read before touching the deep-dive or paper)

Hard-won rules from the full-run re-center; each one cost a real bug, so enforce them:

1. **The 152-model `full-chatok-core20-r5` run is its own self-contained study.** Do
   NOT bolt the frozen 94-model snapshot onto it as a comparison — the two differ in
   models (152 vs 94), **scenarios (only 12 of ~20 IDs shared)**, judges (`4.6`/`5.4`
   vs `4.8`/`5.5`), and prompt format. Cross-run rank correlations (the old "0.974")
   blend all four and prove little. Park the 94-model set as a separate legacy dataset
   others can reuse; the current paper is the 152 run alone. Analyses that must feed the
   paper (the A/B-series ranking/efficiency/scaling/capability/judge/variance/IRT/
   clustering/mixed-effects/roofline work) were computed on the 94-model set and must be
   **re-run on the 152 run** before use.
2. **Parameters come from the integer `param_count` (÷1e9), never the `param_size`
   text.** Parsing "999.89M" as a naked number treated 15 sub-1B models as 100–1000B and
   *inverted* the size finding. Corrected: quality rises with size (Spearman ≈ 0.73);
   ~4B is the efficiency knee, not proof that "bigger doesn't win."
3. **Scenario class = the authoritative `class` field in the scenario set, not the name
   prefix** (`toolcall-20`'s class is `test`; `localize-02`'s is `diagnose`).
4. **Gate every non-trivial claim through BOTH judge families (Claude + GPT),
   independently.** A single-family review missed the parameter bug and a
   survivorship-biased defense; two independent families caught both.
5. **Statistics:** matched pairs at the **lineage** level (qwen3:4b Q8/Q4 are one
   lineage — don't pseudoreplicate); paired-t + t-critical CI and TOST for equivalence
   (not a rep-SD hand-wave); no p-value on n=2; unknown metadata → NaN (excluded), never
   `False`; disclose the energy scope (RAPL `package-0`, DRAM excluded).
6. **Judge agreement ≠ judge validity.** κ measures consistency; correctness needs the
   human-eval packet. Don't launder a correlation into a robustness proof.
7. **Reproducibility (implemented for the 152 run):** claim-bearing analysis must read the
   durable, content-addressed **locked bundle** `data/completed-runs/<run>-<bundle_id>/`
   (hash-bound by `bundle-manifest.json`) — never gitignored `.tmp/`. The heavy raw
   (1.1 GB `.tmp`, 433 MB bundle) stays gitignored **by design**; do NOT `git add` it.
   The tracked, reproducible evidence is instead the compact `data/snapshots/<run>.{results,judged}.csv`
   + `data/analysis-manifest.<run>.json` (claim lock, sha256-bound), regenerated from the
   bundle by `deep-dive/full_snapshot.py`; `deep-dive/full_data.py` resolves bundle → `.tmp`
   → snapshot, so a fresh clone reproduces every number offline. `claim_status` stays
   `provisional` until a human promotes it to paper-final. The heavy bundle is served
   **out-of-band from an Azure Blob**, fetched by content hash (`bundle_id`); the in-repo
   reproducibility path stays the snapshot + manifest, so git never carries the raw.
8. **The `reasoning-budget-v1v2-nocap` re-run is a STANDALONE mechanism study, NOT a patch
   for the 152.** It re-runs 14 models under a raised budget (`max_tokens` →4096,
   `timeout_s`→600 via `core-current-nocap.json`, *only* those two fields changed; all else
   — regime, judges `4.6`/`5.4`, temp 0.7, seed-base 1, ollama 0.30.8 — identical). Use it
   ONLY **within-run**: instruct@4096 vs thinking@4096 (finding 17) and victim vs weak
   controls (finding 19). Do NOT splice these rows into the 152 — mixing 14 models@4096 with
   138 @per-scenario-budget is a worse confound than the truncation it removes. The 152 keeps
   its **disclosed** per-scenario-budget premise as the primary dataset; its truncation is
   covered by the finding-25 sensitivity (headline robust across drop-subsets). A *uniform*
   no-truncation 152 would require re-running all **92** truncated models (the 60 clean are
   cap-invariant — proven `512==4096`), ~1–2 weeks — deliberately NOT done (decision: keep
   the disclosed-budget premise). Judge the re-run with the same 2-judge pair before any use.
9. **The public site is claim-locked; NEVER push provisional evidence to it.** The public
   Quarto site (`docs/analysis/`) **auto-publishes to GitHub Pages on every push to `main`**,
   and `analysis_metrics.validate_analysis_manifest` REFUSES claim-bearing analysis unless
   `claim_status == "locked"`. It currently serves the **locked 94-model** manifest via the
   OLD notebook pipeline (`wave_analysis`/`judge_comparison`/`reviewer` read
   `data/snapshots/{judged,results}_snapshot.csv` + `analysis-manifest.json`) — NOT the 152
   `full-chatok-*` snapshots. Refreshing the public face to the 152 is gated, in order:
   (1) the reasoning re-run completes + is judged; (2) a **human** promotes the 152
   `provisional → locked` (paper-final decision); (3) migrate the site notebooks 94→152
   (repoint + schema-reconcile + recompute the site's own controlled-front/Pareto on the 152)
   and relabel scope to **≤5B** tiers (per `ceops-audit-cold.md`); (4) push once. Do NOT commit
   a 152 site build to `main` before step 2 — it would publish provisional evidence publicly.
   The internal `ceops.hont.ro` dashboard shares the same 94-model staleness but is LAN/Auth-gated.

## Topology

| Node | Role | Notes |
|---|---|---|
| **home** (hostname `home`) | orchestrator + judge + git | runs the schedulers, judges via the Copilot CLI, commits to GitHub |
| **ai** (`home-ai.hont.ro`, hostname `ai`) | **locked inference only** | i5-8350U, Ollama **0.30.8** retained for service/legacy runs, llama.cpp provisioned as preferred future experiment runtime, Turbo off, governor performance |

`home → ai` is **passwordless SSH**. `home` holds the repo clone at
`~/apprenticeops`, has `gh` SSH auth, and the Copilot CLI. **After launch the pipeline
runs entirely on home + ai — no workstation/Mac is in the loop.**

Runtime policy: `data/runtime-policy.json` keeps **Ollama** as the service/API and
legacy snapshot runtime, and sets **llama.cpp** as the preferred runtime for future
locked thesis experiments. The adapter is `INFERENCE_RUNTIME=llama_cpp` via the
non-interactive llama.cpp subprocess backend (default `llama-completion`) for
direct local GGUF files. Do not label broad thesis results as llama.cpp-produced
until a locked full-run artifact exists.

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

Code sync mode: launches default to `SYNC_MODE=origin`, so the producer runs from
the pushed `origin/main` source by default. Use `SYNC_MODE=working-tree` only as
an explicit dev override when testing an uncommitted home checkout. Rows stamp
`env.harness_git`, `env.harness_source_dirty`, and `env.harness_artifact_dirty`
so the regime is auditable.

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

## AI-node-only inference smoke

Use this when the requirement is: prove `ai` can run autonomously with no Mac and
no `home` scheduler after launch. It is inference-only; no Copilot judging or
experiment-branch commits happen in this mode.

```bash
BATCH_ID=ai-local-small-$(date -u +%Y%m%d-%H%M%S)
setsid nohup python3 scripts/run-memory-batch.py launch \
  --batch-id "$BATCH_ID" \
  --model-set ai-local-small-3 \
  --scenario-set strategy-pilot-6 \
  --memory-context none \
  --inference-runtime ollama \
  --runner local-roster \
  >/tmp/${BATCH_ID}.boot 2>&1 </dev/null &
```

`run-roster.sh` pulls missing models, keeps models already present at run start,
and removes only models it pulled for this run after that model completes.
Artifacts are mirrored under `data/runs/<RUN_ID>/` with `judge_expected=false`.

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

## Promote a completed run into analysis v1

Do not point analysis at a live `data/runs/<RUN_ID>/` directory. After producer,
judge, and persistence are complete, promote the run through the fail-closed
evidence boundary:

```bash
python3 scripts/lock-completed-run.py promote \
  --run-dir data/runs/<RUN_ID> \
  --persist-mode git-push \
  --judge copilot:claude-opus-4.6 \
  --judge copilot:gpt-5.4
```

The command derives canonical v1 condition identity from frozen result rows,
preserves the append-only judge log, separates failed retries from the one valid
verdict per backend/model, checks exact roster/scenario/repetition/persistence
coverage, preserves compressed per-model results, candidate traces, and logs,
and creates a content-addressed bundle under `data/completed-runs/`.
It has no partial or force override. `claim_status` remains `provisional` until
a separate privacy, analysis, and claim review.

`--persist-mode` is mandatory and must match authoritative `run.meta`. Use
`local-files` only for the receipt-backed no-push recovery path; promotion then
requires and revalidates one receipt, result archive, and candidate archive per
roster model.

```bash
python3 scripts/lock-completed-run.py verify --bundle data/completed-runs/<bundle>
python3 scripts/privacy-scan.py
python3 scripts/lock-completed-run.py status --run-id <RUN_ID>
```

Decision, gates, and rollback:
[`docs/sdd/completed-run-promotion.md`](docs/sdd/completed-run-promotion.md).

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

Copilot authentication is **CLI/account-level**, not per judge model. Interactive
setup uses `copilot login`; in unattended use the CLI checks
`COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN`, its stored OAuth credential,
then authenticated `gh` as a fallback. Copilot Free includes the CLI but exposes
models through automatic selection only. This experiment's fixed
`claude-opus-4.6` + `gpt-5.4` judge domain therefore requires an entitled paid or
organization account with sufficient AI credits. The model does not perform a
second authentication step.

## Browser verification (mission-control dashboard)

When verifying the dashboard in a browser — screenshots or the Playwright MCP — use
**Microsoft Edge** (`--browser msedge`), **not Chrome** (Chrome isn't installed on this
Mac). The Playwright MCP is pinned to Edge in `sideport/.vscode/mcp.json`. The dev
backend serves the built UI at `http://127.0.0.1:8770` (`uvicorn app:app` from
`dashboard/backend`); the durable copy is `https://ceops.hont.ro`.

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
  ceiling before it rate-limits — historical evidence is archived at
  `docs/archive/CONSOLIDATION-PLAN.md`). Set lower if the
  CLI throttles, `1` for serial. This is what keeps the 158-model judge in hours, not days.

## Determinism (why a run is reproducible)

`run.py --preflight-only` **refuses to start** unless the node matches
`data/run-manifest.json` (Turbo off, governor performance, `min/max_perf_pct=100`,
RAPL `package-0`, perf readable, **ollama 0.30.8**, the `scenarios.json` hash). The
environment is reset and re-verified before every model (`reset.*` evidence stamped
per row), and the run aborts (exit 4) if the node drifts mid-run. See REPRODUCE.md §3.

<!-- architrave:begin -->
<!-- This block is managed by Architrave (tools/install.sh / install.ps1). Edit the kit, not this copy. -->
## Delivery Workflow — Architrave

This repo uses **Architrave**, a config-grounded, judge-gated workflow for knowledge/automation, UI, backend, full-stack features, plan-only infrastructure, and durable learning artifacts. Read root **`architrave.config.json`** first.

**When `kind` is `knowledge`:**
- Ground in repository docs, scripts, skills, schemas, tests, existing instructions, and learning artifacts.
- Run configured `build` and `test` commands.
- Do not infer or request a UI platform, Storybook, design map, tokens, backend, IaC, or runtime lane. UI reconciliation is not applicable.

When `kind` is absent, use the legacy application fields: `platform`, `stack`, UI source of truth (`designSource`, `designMap`, `tokens`), optional `backend` / `iac` / `ops`, and optional `learning` paths.

**Before any UI change in an application-profile repo:**
- **Ground first; reproduce, don't reinvent.** Open the design source of truth named in `architrave.config.json` (the `designSource` Storybook + the `designMap` glossary) and the matching platform knowledge pack. **On a native platform, also load the repo-root constitution — `constitution-apple.md` (Apple) or `constitution-windows.md` (Windows)** — the deep, source-cited native rule base (verbatim type tables/ramp, materials layering, system icons, the native component catalog, and the shared-screenshot conformance-audit protocol). Reproduce the existing component by its glossary name and specify only the deltas. Net-new UI must be mocked in Storybook and confirmed first.
- **Tokens are the single source of truth.** Take values from `architrave.config.json` → `tokens`; if a value must change, change the **token first**, then regenerate. Never hard-code colors/space/type that a token already owns.

**Before any backend/full-stack change:**
- **Contract first.** If `backend` is configured, ground in its architecture docs and contracts before code. The Service Architect owns the API/data contract; the Backend Planner turns it into the human sign-off artifact; the Backend Implementer builds only after that plan is approved.
- **Infrastructure is plan-only.** If `iac` is configured, Architrave may propose diffs and run plan/what-if/policy checks, but a human applies. Never materialize secrets or run apply-shaped commands.

**Before any implementation:**
- **YAGNI ladder.** Do not build presumptive features. First try: delete/skip, reuse existing repo source of truth, native/platform feature, standard library, already-installed dependency, tiny local implementation. New abstractions, dependencies, flags, config, factories, or layers need current evidence, not a guessed future. Never cut validation, data-loss handling, security, accessibility, capability honesty, or the smallest useful test.
- **Phase ledger.** For non-trivial SDD/backend/full-stack/multi-slice work, keep a visible phase ledger before implementation. Mark exactly one phase `in-progress`, state each phase's scope/out-of-scope/gate, and explicitly separate completed phases from phases that are `not-started`. Do not silently begin the next phase.

**Gates — must be green before a change is "done":**
- Deterministic: `gates/checks.sh` (POSIX) or `gates/checks.ps1` (Windows) runs configured generate/build/test and profile-appropriate JSON checks. `gates/reconcile.*` reports UI token drift when configured and is not applicable to knowledge profiles. `gates/backend-checks.*` covers backend plus plan-only IaC when configured.
- Semantic: for non-trivial features, use the **Architrave** agent (the judge-gated harness); the **Adversarial Judge** grades against `gates/rubric.md` and must return PASS.

**Learning loop:** For non-trivial work, keep the run artifacts under `.architrave/runs/` (or `learning.runArtifactsPath`), maintain the concise repo profile at `.architrave/learning/repo-profile.md` (or `learning.repoProfilePath`), and record repeated lessons in `.architrave/learning/repo-lessons.md` (or `learning.lessonsPath`). Validate persisted facts against the current branch before using/promoting them, never store secrets, and promote stable lessons into config, `AGENTS.md`, `.github/instructions/`, or docs only after review.

**Never:** invent an unconfigured lane, introduce platform-foreign UI, use raw values where a token exists, create parallel backend abstractions, materialize secrets, run apply-shaped IaC commands, or claim a capability the repository cannot truthfully perform.
<!-- architrave:end -->
