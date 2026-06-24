# SDD: Run Matrix And Scenario-Set Selection

Status: implemented and locally validated.
Date: 2026-06-24.
Scope: ApprenticeOps / CEOps dashboard, runner orchestration, file-backed run metadata.

## 1. Scope Honesty

This SDD changes how a run is selected and launched. It does **not** change the
scientific scoring method, the judge ensemble, or the scenario corpus content in
`data/scenarios.json` by itself.

The current dashboard exposes one `batch` selector backed by `data/batches.json`.
That selector is really a model-list selector: `dryrun` maps to
`data/models.dryrun.txt`; `full` maps to `data/models.txt`. The scenario axis is
implicit and currently defaults to `data/scenarios.json` throughout the orchestration
stack. Because this product is not launched, we will replace this contract instead
of carrying legacy compatibility.

The new requirement is to make the run shape explicit:

```text
model set x scenario set x repeats x judges
```

For example, the operator should be able to launch `dryrun x core-current`,
`dryrun x extended`, `full x core-current`, or `full x all`, with the expanded
work units shown before launch.

## 2. User-Visible Outcome

The CEOps dashboard shows:

1. **Model lists**: server-approved model roster presets such as `dryrun` and
   `full`.
2. **Scenario sets**: server-approved scenario presets such as `core-current`,
   `extended`, and `all`.
3. **Scenario inventory**: a readable split between Core scenarios and Additional /
   rotation scenarios, with id, class, difficulty, grounding, and brief purpose.
4. **Run matrix preview**: the selected model set and scenario set, including
   `models x scenarios x repeats` inference units and `inference units x judges`
   judge units.
5. **Launch contract**: a run records the selected model set and scenario set in
   `data/runs/<RUN_ID>/run.meta`, so status, resume, and later analysis can prove
   what was actually run.

The first implemented UI should remain compact and operational. This is a run
planning/control surface, not a marketing page.

## 3. Grounding And External Validation

Local grounding:

- `dashboard/backend/app.py` previously validated a server-side model-batch id
  before shelling into `run-e2e.sh`; the new contract replaces that with two axes.
- The old `data/batches.json` proved file-backed launch presets fit this app, but
  it is intentionally not kept as a live contract.
- `run.py` already accepts `--scenarios`, but orchestration does not pass it.
- `scripts/run-e2e.sh`, `scripts/run-from-homelab.sh`, and
  `scripts/run-roster.sh` currently pass only `MODELS`.
- `scripts/pipeline-status.py` currently derives scenario count/classes from
  `data/scenarios.json`, so progress and safety summaries are wrong for any
  non-default scenario file.

External validation:

- GitHub Actions matrix jobs treat a run as the cross-product of independent
  dimensions and show the expanded combinations before execution.
- MLflow Tracking records run parameters, metrics, artifacts, and local file-backed
  metadata by default; run parameters are first-class comparison context.
- JSON Schema is an appropriate validation model for file-backed JSON contracts:
  shared structure, automated checks, and human-readable documentation.
- Twelve-Factor config argues for orthogonal controls rather than grouped
  environment bundles. For this app, `model_set` and `scenario_set` should remain
  independent axes rather than exploding `batch` into `dryrun-core`, `dryrun-all`,
  `full-core`, and so on.

## 4. Decision

Use a new file-backed run matrix contract:

```text
data/run-matrix.json
```

Do **not** introduce a database. The app is a file-backed mission-control surface;
runs already persist their state in `data/runs/<RUN_ID>/`, and the experiment
pipeline already treats files as the reproducibility artifact.

Make `data/run-matrix.json` the only launch contract. Remove `/api/batches` and
legacy `{batch: ...}` launch support in the same implementation slice so there is
only one source of truth.

## 4.1 Storage Format And Corruption Safety

Use the simplest durable format for each job:

| Data | Format | Write pattern | Why |
|---|---|---|---|
| Declarative catalogs (`run-matrix`, scenario sets, manifests) | JSON | committed files, validated before use | Small, human-reviewable, reproducible. |
| Mutable run contract (`run.meta`) | JSON | atomic temp-file write + `fsync` + `os.replace` | Must never be half-written; resume depends on it. |
| Logs, ledgers, results, judged rows | JSONL | append one complete line, flush; readers skip malformed trailing line | Append-only, streamable, resilient to crash during final write. |
| Markers (`.paused`, `.canceled`) | empty files | create/remove only | Simple state flags; no structured content to corrupt. |

Required safeguards:

- Any code that writes JSON runtime state must use an `atomic_write_json(path, obj)`
  helper: write to a same-directory `.<name>.tmp.<pid>` file, `json.dump`, newline,
  flush, `os.fsync`, then `os.replace`.
- After writing important JSON, re-open and parse it in tests or validation scripts.
- JSONL readers must ignore empty lines and malformed final/trailing lines, but must
  not silently ignore malformed lines in the middle of a file when used as a gate.
- `run.meta` is the only mutable JSON control file. It must be written once at
  launch and never rewritten to "fix" history; corrections happen in a new run.
- Shell scripts should delegate structured JSON writes to Python snippets instead
  of composing JSON with `printf`.

## 5. Contract

### 5.1 `data/run-matrix.json`

Example shape:

```json
{
  "schema_version": 1,
  "defaults": {
    "model_set": "dryrun",
    "scenario_set": "core-current"
  },
  "model_sets": [
    {
      "id": "dryrun",
      "label": "Dry run - 2 small models",
      "path": "data/models.dryrun.txt",
      "kind": "validation",
      "description": "End-to-end smoke test."
    },
    {
      "id": "full",
      "label": "Full roster - all models",
      "path": "data/models.txt",
      "kind": "experiment",
      "description": "Complete locked model roster."
    }
  ],
  "scenario_sets": [
    {
      "id": "core-current",
      "label": "Core current - implemented scenarios",
      "path": "data/scenario_sets/core-current.json",
      "kind": "default",
      "description": "Default serious-run roster using implemented scenarios only."
    },
    {
      "id": "extended",
      "label": "Additional / rotation scenarios",
      "path": "data/scenario_sets/extended.json",
      "kind": "rotation",
      "description": "Non-core scenarios for targeted claims."
    },
    {
      "id": "all",
      "label": "All scenarios",
      "path": "data/scenarios.json",
      "kind": "canonical",
      "description": "Full current corpus."
    }
  ]
}
```

Rules:

- Browser submits IDs only, never paths.
- IDs match `^[A-Za-z0-9._-]{1,40}$`.
- Paths are repo-relative, no absolute paths, no `..`, no whitespace, no shell
  metacharacters.
- Model paths must be `.txt` files.
- Scenario paths must be `.json` files with top-level `{"scenarios": [...]}`.
- Scenario IDs must be unique inside each scenario set.
- The backend computes counts, class counts, and SHA-256 hashes from files; it does
  not trust counts stored in the matrix file.

### 5.2 Scenario Set Files

Add:

```text
data/scenario_sets/core-current.json
data/scenario_sets/extended.json
```

Phase 1 uses `core-current`, not `core`, because the six planned Core 20 delta
scenarios have not yet been authored with gold answers and deterministic checks.
The planned Core 20 remains a documentation target until those scenario objects
exist. The first scenario-set files are therefore:

```text
data/scenario_sets/core-current.json
data/scenario_sets/extended.json
```

These files use the same shape as `data/scenarios.json`:

```json
{ "scenarios": [ ... ] }
```

Phase 1 may duplicate scenario objects from `data/scenarios.json`. That is
acceptable because the scenario set is an immutable run artifact. A later phase can
introduce generated scenario sets from ID lists if duplication becomes painful.

Important honesty note: the six new Core scenario designs are not implemented yet.
Until they exist as full scenario objects with gold answers and deterministic
checks, `core-current.json` includes only implemented scenarios. Do **not** label
it "Core 20" in the UI. The UI may show "planned Core 20" as documentation, but
must not launch it until the scenario files exist.

Later, when the six scenario designs are implemented, we can either:

- rename `core-current` to `core`, or
- add a separate `core` scenario set only if it passes the same schema/review gates
  as existing scenarios.

### 5.3 Backend API

Add:

```http
GET /api/run-matrix
```

Returns resolved, server-approved launch options:

```json
{
  "defaults": { "model_set": "dryrun", "scenario_set": "core-current" },
  "model_sets": [
    {
      "id": "dryrun",
      "label": "Dry run - 2 small models",
      "path": "data/models.dryrun.txt",
      "kind": "validation",
      "description": "End-to-end smoke test.",
      "model_count": 2,
      "sha256": "..."
    }
  ],
  "scenario_sets": [
    {
      "id": "core-current",
      "label": "Core current",
      "path": "data/scenario_sets/core-current.json",
      "kind": "default",
      "description": "Default serious-run roster.",
      "scenario_count": 14,
      "class_counts": { "diagnose": 1 },
      "difficulty_counts": { "medium": 9, "hard": 5 },
      "grounding_counts": { "closed-book": 10, "grounded": 4 },
      "sha256": "...",
      "scenario_ids": ["detect-01-crashloop-triage"]
    }
  ],
  "scenarios": [
    {
      "id": "detect-01-crashloop-triage",
      "class": "detect",
      "difficulty": "medium",
      "grounding": "closed-book",
      "sets": ["core-current", "all"],
      "brief": "Kubernetes restart restraint."
    }
  ]
}
```

Update:

```http
POST /api/control/start
```

New request:

```json
{
  "model_set": "dryrun",
  "scenario_set": "core-current"
}
```

There is no compatibility request. `{ "batch": "dryrun" }` is rejected with
HTTP 422/400 because `batch` is no longer part of the product contract.

### 5.4 Run Metadata

`data/runs/<RUN_ID>/run.meta` becomes the durable launch contract:

```json
{
  "schema_version": 2,
  "run_id": "dryrun-core-current-20260624-120000",
  "model_set": "dryrun",
  "models": "data/models.dryrun.txt",
  "models_sha256": "...",
  "models_count": 2,
  "scenario_set": "core-current",
  "scenarios": "data/scenario_sets/core-current.json",
  "scenarios_sha256": "...",
  "scenario_count": 14,
  "class_counts": { "detect": 2 },
  "reps": 5,
  "judges": 2,
  "expect": 2,
  "user": "dragos",
  "started_at": 1782302400
}
```

### 5.5 Runner Environment

Thread these variables through all shell layers:

```bash
MODELS=data/models.dryrun.txt
MODEL_SET=dryrun
SCENARIOS=data/scenario_sets/core-current.json
SCENARIO_SET=core-current
```

Update:

- `dashboard/backend/app.py`: resolve model/scenario IDs; write env vars into the
  `run-e2e.sh` launch command; include `data/run-matrix.json` and
  `data/scenario_sets/` in `_SYNC`.
- `scripts/run-e2e.sh`: write schema v2 `run.meta` with a Python atomic-write
  snippet; compute `EXPECT` from model count; compute `SCENARIO_COUNT` and class
  counts from `SCENARIOS`; pass env to producer and consumer.
- `scripts/run-from-homelab.sh`: propagate `SCENARIOS`, `MODEL_SET`, and
  `SCENARIO_SET` to `run-roster.sh`.
- `scripts/run-roster.sh`: use `SCENARIOS=${SCENARIOS:-data/scenarios.json}`;
  preflight with `--scenarios "$SCENARIOS"`; real run with `--scenarios "$SCENARIOS"`;
  compute `NSCEN` from `$SCENARIOS`.
- `run.py`: stamp `env.scenario_set` and `env.scenarios_path` if env vars exist.
  It already stamps `env.scenarios_sha` and already supports `--scenarios`.
- `scripts/pipeline-status.py`: read run-specific `run.meta` first. Use
  `scenario_count`, `scenario_set`, `scenarios`, and class map from that file/path
  for progress, model progress, score breakdown, security score, and sessions.
- All generated shell commands must use `shlex.quote` or equivalent for every
  environment value, including `RUN_ID`, `MODELS`, `MODEL_SET`, `SCENARIOS`,
  `SCENARIO_SET`, and `RUN_USER`. Regex validation remains necessary but is not a
  substitute for quoting.

### 5.6 Resume Semantics

Resume is the highest-risk behavior.

Current `dashboard/backend/app.py` relaunches a stopped run with only `RUN_ID`, so
it would fall back to default `MODELS` and `SCENARIOS`. That is unacceptable once
scenario selection exists.

Fix: resume must read `data/runs/<RUN_ID>/run.meta` on `home`, recover `MODELS`,
`MODEL_SET`, `SCENARIOS`, and `SCENARIO_SET`, and relaunch `run-e2e.sh` with those
values. If meta is missing a `scenarios` path, historical runs may fall back to
`data/scenarios.json` and should be marked historical in status.

Resume must also validate existing artifacts against the recorded run contract:

- If `run.meta.schema_version >= 2`, the selected scenario file must exist and its
  SHA-256 must match `run.meta.scenarios_sha256`. Mismatch is a **409 fail-closed**;
  start a new run rather than relabeling old rows.
- Existing mirrored result rows for a v2 run must either carry the same
  `env.scenarios_sha` or predate the stamp and be treated as incompatible. A
  mismatch blocks relaunch.
- Completion/resume logic in `run.py` must count expected `(scenario_id, rep)`
  pairs from the selected scenario set, not just "N rows". A model that has rows
  for the wrong scenario IDs is incomplete for this run.
- Judged rows are valid only for the same run id, model, scenario id, rep, and
  scenario hash/path contract. Historical runs without the hash fall back to
  all-scenario behavior and are marked historical in status.

Pause/resume/cancel semantics stay unchanged but must be visible:

| Action | Semantics | UI copy / backend rule |
|---|---|---|
| Pause | `SIGSTOP` producer/consumer processes and write `.paused`; run still owns the AI node | "Paused runs still reserve the ai node." |
| Resume | `SIGCONT` if processes exist; otherwise relaunch from `run.meta` | Refuse if `run.meta` contract or existing rows mismatch. |
| Cancel | write `.canceled`, clear `.paused`, kill producer/consumer | Terminal. Cannot resume. Partial artifacts remain for audit. |
| Start new run | allowed only when no run is running or paused | 409 with active `run_id` and state when locked. |

## 6. UI Plan

Phase 1 UI can be simple but honest:

- Replace the old single launch select in `Controls.tsx` with two selects:
  - Model list
  - Scenario set
- Button text becomes **Review and launch** or **Start** with a visible work-unit
  summary. If the full confirmation flow is too large for Phase 1, at minimum show:

```text
2 models x 14 scenarios x 5 reps = 140 inference units; x2 judges = 280 judge units
```

- Add a compact **Scenario inventory** panel below Sessions or in the selected-run
  area:
  - grouped by Core and Additional / Rotation;
  - rows show id, class, difficulty, grounding, and brief.
- Active run states keep launch disabled with a clear reason: the single AI node is
  reserved.

### 6.1 Launch Preflight / State Model

The backend should expose a launch-preflight object through `/api/run-matrix` or a
nearby endpoint before the UI enables launch:

```json
{
  "ready": true,
  "blockers": [],
  "warnings": [],
  "active_run": null,
  "selected": {
    "model_set": "dryrun",
    "scenario_set": "core-current",
    "model_count": 2,
    "scenario_count": 14,
    "repeats": 5,
    "judges": 2,
    "inference_units": 140,
    "judge_units": 280
  },
  "sources": {
    "matrix": "data/run-matrix.json",
    "scenarios": "data/scenario_sets/core-current.json"
  },
  "ts": 1782302400
}
```

Minimum UI states:

| State | Required behavior |
|---|---|
| Matrix loading | Show disabled controls and "Loading launch options...". |
| Matrix malformed/missing | Disable launch; show source file and validation error. |
| No model sets or no scenario sets | Disable launch; show "No server-approved launch options." |
| Selected scenario set empty | Disable launch; show scenario set id/path. |
| Manifest hash mismatch | Disable launch; show that the scenario set is not approved for deterministic runs. |
| Home/AI status partial | Show the partial status and block launch if lock/readiness is unknown. |
| Active run running or paused | Disable launch; show active `run_id`, state, owner, and Follow action. |
| Launch accepted | Show receipt with `run_id`, model set, scenario set, and first status heartbeat. |
| Launch rejected | Preserve selections and display the backend reason. |

The launch button text may remain compact, but it must be backed by the preflight
state. Expensive combinations (`full x all`, or a unit count above a threshold)
should require an explicit confirmation in Phase 2.

Phase 2 can add richer scenario search/filter and a modal confirmation for expensive
runs.

## 7. Migration

1. Add `data/run-matrix.json`.
2. Add `data/scenario_sets/core-current.json` and `data/scenario_sets/extended.json`.
3. Remove `/api/batches` and `data/batches.json` from the dashboard launch path.
  If the file remains temporarily for old docs/scripts, it is ignored by the app.
4. Existing historical runs remain readable. If they lack `run.meta.schema_version`
  or `scenarios`, status treats them as historical all-scenario runs.

## 8. Determinism And Manifest

`data/run-manifest.json` currently pins one `protocol.scenarios_sha256`. A scenario
set different from `data/scenarios.json` will fail preflight if run against the
current manifest.

Phase 1 must not bypass the preflight with `--allow-unlocked` for dashboard runs.
Instead, update the manifest protocol to allow approved scenario hashes, for example:

```json
"scenario_sets": {
  "all": { "path": "data/scenarios.json", "sha256": "...", "scenario_count": 27 },
  "core-current": { "path": "data/scenario_sets/core-current.json", "sha256": "...", "scenario_count": 14 },
  "extended": { "path": "data/scenario_sets/extended.json", "sha256": "..." }
}
```

Then update `run.py` preflight to accept either the legacy `scenarios_sha256` or a
hash present in `protocol.scenario_sets`. Rows still stamp the actual
`env.scenarios_sha`.

## 9. Security

- Client submits IDs only; paths are server-resolved from allowlisted JSON.
- Backend rejects bad IDs, unknown IDs, bad paths, missing files, malformed JSON,
  duplicate scenario IDs, and unsafe model file paths.
- Shell invocations only interpolate server-resolved repo-relative paths that pass
  strict regex checks and are shell-quoted with `shlex.quote` or an equivalent.
- No secrets are added to run matrix files, scenario set files, or run metadata.
- No runtime mutation is performed by the SDD itself. Launch behavior remains the
  existing explicit user action.

## 10. Validation Gates

Implemented local gate results (2026-06-24):

- `data/run-matrix.json` + manifest hash/count validation: **PASS**.
- `python3 -m py_compile dashboard/backend/app.py scripts/pipeline-status.py run.py`: **PASS**.
- `bash -n scripts/run-e2e.sh scripts/run-from-homelab.sh scripts/run-roster.sh`: **PASS**.
- `scripts/pipeline-status.py` run-matrix payload (`core-current=14`, `extended=13`, `all=27`, no `batches`): **PASS**.
- Backend direct smoke (`/api/run-matrix`, old `{batch}` rejected, resume scenario-hash mismatch rejected): **PASS**.
- Atomic `run.meta` smoke (`dryrun x core-current`, `expect=2`, `scenario_count=14`): **PASS**.
- `cd dashboard/frontend && npm run build`: **PASS**.

Deterministic gates:

1. `python3 -m py_compile dashboard/backend/app.py scripts/pipeline-status.py run.py`
2. `bash -n scripts/run-e2e.sh scripts/run-from-homelab.sh scripts/run-roster.sh`
3. `python3` validation script for:
   - `data/run-matrix.json` parses;
   - IDs unique;
   - paths safe and existing;
   - scenario set files parse;
   - scenario IDs unique;
   - manifest approved hashes match current files.
   - v2 resume refuses scenario file hash mismatch;
   - status fixture with a two-scenario set reports two scenarios, not the full
     corpus;
   - historical run metadata falls back to all-scenario behavior and is marked
     historical.
   - `run.meta` atomic-write helper round-trips valid JSON;
   - JSONL readers tolerate an empty/truncated trailing line but fail on malformed
     middle lines in validation mode.
4. `cd dashboard/frontend && npm run build`
5. Backend smoke using FastAPI TestClient or direct function tests if `httpx` is
   unavailable:
   - `GET /api/run-matrix` returns model and scenario sets with counts;
  - new `{model_set: "dryrun", scenario_set: "core-current"}` resolves safely;
  - old `{batch: "dryrun"}` launch is rejected;
   - unknown IDs fail;
   - bad paths in a fixture fail;
   - resume reads `run.meta` rather than defaults.
   - resumed v2 runs preserve `MODEL_SET`, `SCENARIO_SET`, `MODELS`, and
     `SCENARIOS`.
6. One real operator-approved runtime gate after code review:
   - `dryrun x core-current` on home/ai;
   - status shows selected scenario set and correct work units;
   - resume preserves selected scenario set.

Semantic gates:

- Backend/service plan reviewed by Service Architect.
- Operational launch UX reviewed by UX Architect / Operations UX.
- Visual density reviewed by UI Visual.
- Full SDD reviewed by Adversarial Judge before implementation.
- Implementation reviewed by Adversarial Judge before final commit.

## 11. Phases

| Phase | Name | Scope | Gate |
|---:|---|---|---|
| 1 | SDD and contract | This document, specialist validation, adversarial review | completed: Judge PASS |
| 2 | File-backed matrix backend | `run-matrix.json`, scenario set files, backend resolver/API, launch preflight validation | completed: Python checks + direct API smoke PASS |
| 3 | Runner propagation | `SCENARIOS` env through scripts, run.meta v2, manifest approved hashes, status/resume from meta | completed: py_compile + bash -n + status/resume fixtures PASS |
| 4 | Dashboard UI | Dual selectors, scenario inventory, work-unit summary | completed: `npm run build` PASS |
| 5 | End-to-end dry run | Operator-approved `dryrun x core-current` launch on home/ai | not-started: requires explicit operator approval |

## 12. Open Decisions

1. Whether Phase 1 scenario set files should duplicate full scenario objects or store
   ID lists and generate at launch. Recommendation: duplicate full objects first;
   optimize later.
2. Whether the final UI uses a confirmation modal in Phase 1. Recommendation: if
   time is tight, show work-unit math inline and reserve modal for Phase 2.

## 13. Rejected Alternatives

| Alternative | Why rejected |
|---|---|
| Keep `data/batches.json` compatibility | Product is not launched; two launch contracts add drift and corruption risk without user value. |
| Precompute every combination in `data/batches.json` | Causes combinatorial growth and hides the independent model/scenario axes. |
| Add a database | Unnecessary for a file-backed single-operator pipeline; run artifacts already persist state. |
| Let the client send file paths | Unsafe; violates the existing server-side allowlist trust model. |
| Use `--allow-unlocked` to bypass scenario hash mismatch | Breaks the determinism contract for canonical runs. |
| Make the scenario inventory decorative only | The user needs to understand exactly what `core` or `extended` means before spending compute. |
