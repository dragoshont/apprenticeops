# ApprenticeOps Project, Paper, and Analysis Consolidation

Status: completed implementation and correction lock, 2026-07-10; all five
phases passed independent GPT- and Claude-family review. The active doctoral run
remains outside claim-bearing analysis until its separate completed-run data and
analysis locks pass.

> **Outcome:** after this consolidation, a contributor can identify the one
> authoritative source for the project definition, protocol, telemetry,
> statistics, manuscript, and findings; can reproduce each published number; and
> can run one tested implementation of every derived analysis metric.

## 1. Scope And Non-Goals

This consolidation covers:

- project-description and operator documentation;
- paper intent, design, manuscript, readiness, and reviewer guidance;
- experiment protocol, pipeline, telemetry, statistics, and artifact contracts;
- analysis code, snapshots, notebook/site exports, and derived metric names;
- completed plans, dated audits, research notes, and obsolete scripts.

It does **not** change:

- the active run, its roster, scenarios, prompts, seeds, sampler, token/time
  budgets, judges, runtime, or artifacts;
- the locked H1-H7 hypotheses or frozen 94-model result;
- raw evidence retained for reproducibility;
- unrelated working-tree changes;
- Git history, branches, or remote state.

## 2. Root Cause

The repository grew through several operational and research waves. Each wave
correctly wrote down its decisions, but ownership was never reduced afterward.
The same concepts now appear in four forms:

1. **canonical-looking narrative** (`README.md`, `PAPER.md`, `paper.qmd`);
2. **operational contracts** (`AGENTS.md`, `PROTOCOL.md`,
   `EXPERIMENT-PIPELINE.md`, `REPRODUCE.md`);
3. **completed plans and audits** (`COLD_AUDIT_*`, `CEOPS_*`,
   `CONSOLIDATION-PLAN.md`, dated scenario/external-dataset notes);
4. **parallel calculations** (`report.py`, `scripts/metrics.py`, notebook cells,
   and one-off `interim_analysis.py`).

This created recurrent drift:

- result prose and analysis plans can both appear authoritative;
- completed plans still say `active`;
- historical footprint boundaries coexist with the current parameter boundary;
- generated report prose hard-codes historical runtime facts;
- MBU, energy-per-correct, KV-cache, safety, and Friedman semantics differ by
  analysis path.

The durable fix is **one owner per concept plus one implementation per metric**.
Deleting a few files without those ownership boundaries would only hide the
symptom.

## 3. Canonical Source Hierarchy

| Concern | Canonical owner | Supporting evidence, never the owner |
|---|---|---|
| Public project description and current headline | `README.md` | `CITATION.cff`, site landing page |
| Operator commands and live topology | `AGENTS.md` | `docs/EXPERIMENT-PIPELINE.md`, run logs |
| Reproduction procedure | `REPRODUCE.md` | `docs/ARTIFACT_INVENTORY.md` |
| Research positioning decision | `docs/PAPER_POSITIONING.md` | literature catalog, market analysis |
| Research questions, hypotheses, design, amendments | `docs/PAPER.md` | protocol and statistics contracts |
| Submission manuscript and claim-bearing prose | `docs/analysis/paper.qmd` | rendered HTML/PDF |
| Reviewer guide and review criteria | `REVIEWER.md` | `docs/analysis/reviewers.qmd` is the short web view |
| Executable reviewer queries | `docs/analysis/reviewer.ipynb` | rendered `reviewer.html`; it consumes frozen v1 exports |
| Paper readiness and open evidence gates | `docs/PAPER_PHASES.md` | artifact inventory, judge validation |
| Model eligibility and locked experimental protocol | `docs/PROTOCOL.md` plus machine-readable locks | historical roster notes |
| Runtime/orchestration contract | `docs/EXPERIMENT-PIPELINE.md` | completed runtime audits |
| Hardware target/static facts | `docs/HARDWARE.md` plus `data/hardware-profile.home-ai.json` | run rows and node snapshots |
| Per-run environment-capture contract | `docs/ENVIRONMENT.md` | generated run-local `ENVIRONMENT.md` artifacts |
| Scenario taxonomy and lifecycle | `docs/TAXONOMY.md` plus lifecycle schema | dated scenario research/audits |
| Raw row field semantics | `docs/TELEMETRY.md` | generated `ROW_FIELD_CATALOG.md` |
| Statistical estimands and inference | `docs/STATISTICS.md` | analysis review/history |
| Current validated findings and open analysis questions | new `docs/ANALYSIS.md` | frozen manuscript and archived analysis logs |
| Judge validation | `docs/JUDGE_VALIDATION.md` | judge-comparison notebook |
| Privacy/egress publication gate | `docs/PRIVACY_AND_EGRESS.md` | privacy scan output |
| Committed artifact contract | `docs/ARTIFACT_INVENTORY.md` | raw-data READMEs |
| Analysis implementation | new root `analysis_metrics.py` | CLI/report adapters and notebooks |
| Frozen 94-model analysis execution | `docs/analysis/wave_analysis.ipynb` | `data/site/*`, figures |
| Public analysis landing and reviewer pages | `docs/analysis/index.qmd`, `docs/analysis/reviewers.qmd` | rendered `_site/*` |
| Analysis-site build/configuration | `docs/analysis/_quarto.yml`, `scripts/build-analysis-site.sh`, `.github/workflows/publish-analysis.yml` | generated `_site/*` |
| Generated observed row catalog | `docs/ROW_FIELD_CATALOG.md`, `docs/row-field-catalog.generated.json` | `data/row-field-descriptions.json`, observed run rows |
| Frozen prompt/scenario renderings | `data/MODEL-PROMPTS.md`, `data/SCENARIOS.md` | machine-readable scenario sets and prompt hashes |
| Historical model roster research | `docs/MODELS.md` | `docs/PROTOCOL.md` and `data/models.lock.jsonl` remain authoritative |
| Market/novelty evidence | `docs/MARKET.md` | `docs/PAPER_POSITIONING.md` remains the accepted decision |
| Judge prompt/review artifacts | `docs/frontier-prompt.md`, `docs/gold-review-prompt.md`, `docs/gold-review*.jsonl` | `docs/JUDGE_VALIDATION.md` remains the validation owner |
| Raw frozen evidence and derivation map | `data/raw/README.md` | archives in `data/raw/` and snapshot builders |

Canonical does not mean monolithic. Protocol, telemetry, statistics, and
manuscript remain separate because they answer different questions and change at
different rates.

### 3.1 One Canonical Analysis Schema: v1

There is **one analysis schema: `v1`**. It is the corrected, canonical, and final
contract for derived ApprenticeOps metrics and analysis exports. This
consolidation does not maintain parallel analysis definitions.
This rule applies only to **derived, claim-bearing analysis artifacts**. Existing
raw-result, run-metadata, scenario, and lifecycle schema versions remain separate
operational contracts and are not renamed by this consolidation.

- Raw inference, judge, sidecar, and environment evidence remains immutable.
- The 94-model paper snapshots, notebook exports, `data/site/*`, figures, public
  landing page, reviewer notebook, and manuscript are regenerated from the
  committed snapshots under the corrected `v1` definitions. The first-batch raw
  per-judge rows and the recovered second-batch per-judge verdict rows are
  committed and hash-bound. `scripts/export-judge-pairs.py --check` reconstructs
  all 8,909 locked complete pairs and their frozen provenance sidecar. Because
  these paper-era rows predate the full condition contract, the sidecar marks
  them incomplete and prohibits cross-run reuse.
- The active doctoral run is not read into claim-bearing analysis until it
  completes and passes the strict data-lock gate. Its eventual derived outputs
  use the same `v1` definitions.
- Incorrect pre-consolidation derived fields are migrated or replaced; they do
  not survive as a second supported schema. Their provenance remains available
  in immutable raw evidence and Git history.

Any corrected value that changes a published number must pass a new analysis
lock: deterministic regeneration, updated figures/tables and manuscript claims,
claim-evidence audit, and dual-family review. That is a correction within the
single `v1` contract, not a schema-version fork.

The implementation will enforce the schema through one checked-in machine-readable file,
`data/analysis.schema.json`, with `schema_version: 1`. It defines exact columns,
types, units, nullability, grains, and source estimands for every canonical
snapshot and `data/site/*` export. `scripts/audit-paper-data.py` validates each
artifact against it; prose tables are not the schema.

Every canonical analysis bundle also contains `analysis-manifest.json`, validated
by the same schema, with `analysis_schema_version: 1`, `source_kind`
(`frozen_snapshot` or `completed_run`), `source_id`, source SHA256 values, and
`claim_status` (`locked` or `provisional`). These are provenance/status fields
inside the one `v1` contract, not separate schema versions. Claim-bearing public
surfaces accept only `claim_status=locked`; a completed current run remains
`provisional` until its analysis-lock gate passes.

## 4. Document Disposition

### 4.1 Keep And Tighten

| File/family | Action | Reason |
|---|---|---|
| `README.md`, `AGENTS.md`, `REPRODUCE.md`, `REVIEWER.md` | KEEP | Distinct public, operator, reproduction, and review audiences. Add one documentation map; remove duplicate method detail where a canonical contract exists. |
| `docs/PAPER.md` | KEEP | Design and pre-registration owner. Keep locked hypotheses and amendments; link rather than duplicate telemetry/statistics formulas. |
| `docs/analysis/paper.qmd` | KEEP | Submission manuscript owner. It may summarize methods but must cite canonical contracts. |
| `docs/PAPER_POSITIONING.md` | KEEP | Accepted ADR-like decision with rejected alternatives and novelty scan. |
| `docs/PAPER_PHASES.md` | KEEP | Paper/evidence readiness control plane. Absorb the remaining live items from `PAPER_DATA_COMPLETION_PLAN.md`. |
| `docs/PROTOCOL.md`, `docs/EXPERIMENT-PIPELINE.md` | KEEP | Distinct protocol and orchestration contracts. |
| `docs/TELEMETRY.md`, `docs/STATISTICS.md` | KEEP | Raw/derived field semantics and inference contract. Remove formula duplication from other docs. |
| `docs/HARDWARE.md`, `docs/ENVIRONMENT.md` | KEEP | `HARDWARE.md` owns the target/static profile; `ENVIRONMENT.md` owns the per-run capture template and released artifact name. Strengthen the placeholder rather than deleting the contract. |
| `docs/TAXONOMY.md`, `docs/SCENARIO_LIFECYCLE_SCHEMA.md` | KEEP | Current taxonomy and machine-readable lifecycle semantics. |
| `docs/JUDGE_VALIDATION.md`, `docs/PRIVACY_AND_EGRESS.md`, `docs/ARTIFACT_INVENTORY.md` | KEEP | Current publication gates. |
| `docs/analysis/README.md`, notebooks, `literature-catalog.md` | KEEP | Analysis execution, exports, and literature index. |
| `docs/analysis/index.qmd`, `docs/analysis/reviewers.qmd`, `_quarto.yml` | KEEP | Claim-bearing public landing/reviewer copy and site configuration. Repair the current `<= 5 GB` thesis-boundary drift in `index.qmd`. |
| `.github/workflows/publish-analysis.yml`, `scripts/build-analysis-site.sh`, `scripts/make-paper-figures.py` | KEEP | Publication execution and generated-figure path. The local build must execute the notebook before the render-only workflow publishes it. |
| `docs/PLAN.md` | MERGE + ARCHIVE | It is an evolving historical study plan that duplicates `PAPER.md`/`PROTOCOL.md`; retain unique baseline/context/task details, then archive it as provenance. |
| `docs/MODELS.md`, `docs/MARKET.md` | KEEP AS SUPPORTING | Historical roster research and market/novelty evidence; neither may override `PROTOCOL.md` or `PAPER_POSITIONING.md`. |
| `data/SCENARIOS.md`, `data/MODEL-PROMPTS.md` | KEEP GENERATED/FROZEN | Human-readable scenario and byte-frozen prompt artifacts. Regenerate/validate from machine-readable sources rather than editing as narrative owners. |
| `docs/ROW_FIELD_CATALOG.md`, `docs/row-field-catalog.generated.json` | KEEP GENERATED | Exhaustive observed-field output; `TELEMETRY.md` remains the conceptual contract. |
| `data/raw/README.md` | KEEP | Raw 94-model evidence and derivation provenance. Expand `ARTIFACT_INVENTORY.md` to point to it. |
| `docs/frontier-prompt.md`, `docs/gold-review-prompt.md`, `docs/gold-review*.jsonl` | KEEP AS EVIDENCE | Judge/reference prompt and adjudication artifacts owned operationally by `JUDGE_VALIDATION.md`. |
| External-dataset rights ledger and integration plan | KEEP | Rights/provenance and lane-level decision are not reproduced elsewhere. Consolidate phase status into the integration plan. |
| `docs/EXTERNAL_DATASET_SOURCE_BACKLOG.md` | KEEP AS SUPPORTING | Reviewed but unimported source backlog; it cannot become Core/paper evidence without the integration-plan gate. |
| `docs/ADMISSIONS_DATASET_PREDICTION_PLAN.md` | KEEP PARKED | User-requested future project note, explicitly outside ApprenticeOps claims and analysis. Move under a future-work grouping only if links remain stable. |

### 4.2 Merge Then Delete

| Source | Canonical destination | Unique content to retain | Delete gate |
|---|---|---|---|
| `docs/PAPER_INTENT.md` | `PAPER.md`, `PAPER_PHASES.md`, `REVIEWER.md`, then archive | Explicit non-claims, readiness bar, peer-review questions not already present | Search proves every inbound link is rewritten and no unique paragraph remains in the canonical set. |
| `docs/PAPER_DATA_COMPLETION_PLAN.md` | `PAPER_PHASES.md`, `ARTIFACT_INVENTORY.md`, then archive | Still-open paper/data gates and lane separation | Every open item has an owner/status in the destinations. |
| `docs/README_UPDATE_PLAN.md` | `README.md`, `PROTOCOL.md`, `docs/analysis/index.qmd`, then DELETE | Canonical ≤5B wording and acceptance criteria, already implemented elsewhere | All public surfaces pass the boundary search; archived cold-audit links are rewritten to the canonical docs; no live action or unique evidence remains. |
| `docs/DEEP-ANALYSIS-DRAFT.md` | new `docs/ANALYSIS.md`, then archive | All validated 94-model exploratory findings, corrections, caveats, and open threads | Finding-by-finding checklist complete; manuscript links updated; archive copy retained. |
| `docs/SLM_METRICS_CORRELATION_REVIEW_2026-07-10.md` | new `docs/ANALYSIS.md`, `STATISTICS.md`, then archive | New literature-backed hypotheses, metric defects, provisional-screen status, priority plan, and phase ledger | Consolidation ledger explicitly supersedes its repair ledger; no provisional values enter claim-bearing prose; archive copy retained. |
| `interim_analysis.py` | `analysis_metrics.py` plus tested analysis adapters and supported notebook/site path | Retain only valid generic statistics/helpers; do not port its invalid assumption that raw result rows contain `wh_per_correct` | Replace stale `REPRODUCE.md` interim-notebook instructions; no tracked caller/backlink remains; replacement tests cover retained behavior. |

### 4.3 Archive As Evidence

Move completed, dated, or superseded-but-evidentiary documents under
`docs/archive/` and add `docs/archive/README.md`. Archive files remain tracked and
searchable but are excluded from the canonical navigation.

| Archive family | Files | Why archive instead of delete |
|---|---|---|
| Completed consolidation/audits | `CONSOLIDATION-PLAN.md`, `COLD_AUDIT_RESPONSE_PLAN.md`, `COLD_AUDIT_IMPLEMENTATION_PHASES.md` | Preserve decision provenance, corrections, and old population rules. |
| Completed runtime research/reviews | `CEOPS_CPP_MLX_CAPTURE_RESEARCH.md`, `CEOPS_DATA_CAPTURE_ADVERSARIAL_REVIEW.md`, `CEOPS_LLAMA_CPP_EVIDENCE_PHASE.md`, `CEOPS_METRICS_SOURCE_ANALYSIS.md`, `CEOPS_RUNTIME_AGENT_DEPLOYMENT_PLAN.md`, `WEEKS_LONG_INFERENCE_READINESS_AUDIT_2026-07-05.md` | Preserve why current capture/runtime contracts exist. |
| Dated scenario research/reviews | `SCENARIO_*_2026-06-24.md`, `CORE_CURRENT_SCENARIO_REVIEW_2026-07-04.md` | Preserve external-source research and adversarial review evidence. |
| Dated model search | `MODEL_SEARCH_2026-06-30.md` | Separate application-specific investigation, not current roster truth. |
| External-dataset phase evidence | `EXTERNAL_DATASET_PHASE1_SUMMARY.md`, `EXTERNAL_DATASET_PHASE3_CANDIDATES.md`, `EXTERNAL_DATASET_PHASE5_ERROR_REVIEW.md`, `EXTERNAL_DATASET_PHASE5_SPREAD10_REVIEW.md`, `EXTERNAL_DATASET_CANDIDATE_V1_REPAIR_REVIEW.md` | Preserve exact promotion/repair evidence after status is summarized canonically. |

Archive moves use exact repo-relative filenames and history-preserving renames.
Before a move, rewrite inbound live-doc links to the canonical owner. After a
move, rewrite relative links inside the archived document so the archive remains
self-contained. `docs/archive/README.md` records original path, archive path,
date, superseding owner, reason, and whether the original path was publicly
linked. Run a whole-repo Markdown/QMD link check after every move. A published
external path keeps a short moved notice or compatibility stub; repo-internal
paths are rewritten directly.

SDDs are not archived solely because implementation landed. They remain the
behavioral contract until their feature is removed or a successor explicitly
supersedes them; status headings must match code reality.

## 5. Analysis-Code Target

### 5.1 Shared Pure Module

Create `analysis_metrics.py` with dependency-light, unit-tested functions for:

- finish-reason and completion-outcome classification;
- measured MBU (`measured bandwidth / calibrated peak`);
- explicitly named dense-weight-stream-equivalent ratio;
- energy per deterministic-check-equivalent using one aggregate estimator;
- canonical `j_per_output_token` (any Wh/k-token display is a presentation-only
  unit conversion, not another stored field);
- KV-cache payload estimate requiring a known dtype or returning an explicitly
  labelled FP16-equivalent value;
- repeat agreement, scenario success, `pass^k`, and `all_safe^k`;
- safety-set membership from explicit classes/lifecycle metadata;
- model-oriented Friedman samples;
- deterministic scenario-cluster bootstrap helpers used by the current analysis
  plan.

No pandas/scipy dependency belongs in this module. Statistical tests may consume
its prepared samples in an adapter with the existing optional dependencies.

### 5.2 Adapters

All adapters group rows by the same fail-closed identity. The canonical
`analysis_condition_key` is the ordered tuple:

```text
model
runtime_adapter                 # env.inference_runtime / adapter
artifact_identity               # ollama.digest or direct-GGUF SHA256
quantization
hardware_condition              # host + locked CPU/power/RAPL/num_ctx facts
prompt_template_sha256
memory_context + memory_context_sha
inference_strategy + strategy_prompt_sha
sampling_policy                 # temperature + think + effective sampler policy
scenario_set + scenarios_sha256
evaluation_policy               # deterministic-check policy + locked judge ensemble id
```

Missing artifact identity or a missing condition field does not silently merge
rows across runs. The adapter emits `condition_identity_incomplete=true`; such
rows may be summarized within their source run but are excluded from cross-run,
paired-variant, judge, and deployment-ranking joins. `report.py`, `scripts/metrics.py`,
`dataset.py`, reliability exports, Friedman preparation, and audits all use this
same key. Judge-family rows remain nested under the condition key and are never
counted as independent task observations.

New `judged.jsonl` rows stamp `analysis_condition_key_sha256` from the source
inference row and the complete requested evaluation ensemble. The declared
`evaluation_policy` remains stable when one requested family fails to emit a row.
Historical judged rows without the hash are rejected by default; an explicit
legacy-compatibility mode may use the narrower key only when it resolves to one
condition in the selected results. Any one-to-many mapping fails closed and
requires rejudging; report, dataset, and snapshot-merge adapters cannot overwrite
one condition with another.
Judge identity is backend plus model. Consensus is emitted only for the complete
requested identity set; partial-family output remains unjudged and resumable.

- `report.py` remains the human-readable rollup and consumes shared functions.
- `scripts/metrics.py` remains a CLI enrichment/export tool and consumes the same
  shared functions; misleading parallel formulas and names are removed.
- `dataset.py` remains the ML-ready per-repetition row exporter; it does **not**
  broadcast group-level reliability values onto each repetition. `scripts/metrics.py`
  emits a separate per-`(model, scenario, condition)` reliability export with
  repeat count, repeat agreement, `pass_1`, `pass_all_k`, and `all_safe_k`.
- the frozen notebook may retain publication-specific aggregation, but canonical
  metric formulas must import or reproduce values validated against the shared
  fixture. No new active-run result is written into the frozen notebook.
- `scripts/audit-paper-data.py` gains analysis-contract tests in its gate.
- `.github/workflows/publish-analysis.yml` has a `verify-analysis-v1` job
  before Pages build. It uses `actions/setup-python` with Python 3.14.5, installs
  `requirements-lock.txt` with hash enforcement, validates dependency versions
  and licenses, executes
  `scripts/build-analysis-site.sh --verify`, and fails on unexpected changes to v1
  `data/site/*`, `docs/analysis/figures`, or the source notebook. The workflow
  runs on every push to `main` and on manual dispatch; Pages deploy needs this
  job and remains render-only after verification.
- `scripts/build-analysis-site.sh` gains two explicit modes. Default `--update`
  executes in place only when intentionally refreshing the correction-lock
  bundle. `--verify` runs from the repo root, creates a temporary directory, and
  invokes `python -m jupyter nbconvert --to notebook --execute` with the tracked
  notebook as input and the temporary notebook as output. Notebook code therefore
  regenerates canonical exports/figures from the repo-root snapshots while
  execution counts and cached output land only in the temporary copy. It compares
  `data/site/*` and `docs/analysis/figures` with committed artifacts, removes the
  temporary directory, and never changes the source notebook. CI uses only
  `--verify`; it does not depend on a pre-existing `.venv`.
- `scripts/audit-paper-claims.py` verifies every public/reviewer claim-bearing
  numeric surface: `README.md`, `REVIEWER.md`, `docs/analysis/index.qmd`,
  `docs/analysis/reviewers.qmd`, and `docs/analysis/paper.qmd`, including the
  Pareto tables, plus the cached outputs and claim-bearing cells in
  `docs/analysis/reviewer.ipynb`, against canonical `summary.json`, axis exports,
  judge-pair exports, and `pareto.csv`. The generated `reviewer.html` is covered
  by deterministic rendering from that audited notebook. No other public
  document may contain claim-bearing result numerics; historical/archive
  documents are labelled provenance and excluded from current-claim checks.
  Pages/PDF rendering depends on this audit, so hand-copied numbers cannot bypass
  the schema gate.
- `scripts/audit-paper-data.py` rejects analysis bundles whose manifest is
  missing, whose `analysis_schema_version` is not exactly `1`, whose source hashes
  do not match, or whose `claim_status` is incompatible with the consuming public
  surface.

### 5.3 Canonical v1 Fields And Migration

The corrected field names below are the only supported analysis names. Current
claim-bearing snapshots and `data/site/*` are regenerated under this contract.
Historical pilot outputs may remain as provenance artifacts, but are not active
schema implementations and are not consumed by the canonical analysis path.

| Pre-consolidation name | Canonical v1 name/meaning | Migration decision |
|---|---|---|
| `bracket` | `parameter_tier` (`T1`-`T5` or null) and `legacy_footprint_bracket` (historical label or null) | Remove bare `bracket` from canonical exports. Never mix parameter and footprint groupings. |
| `mbu` in `report.py` | `mbu`: measured bandwidth / calibrated peak | Keep name and semantics. |
| `mbu` in `scripts/metrics.py` | `dense_weight_stream_equivalent_ratio`: artifact bytes × decode rate / calibrated peak | Rename; remove the misleading alias and its arbitrary `1.5` display cap. Emit measured `mbu` when row bandwidth exists. |
| `energy_wh`, `mWh`, `wh_per_ans` in public model/axis exports | `mean_energy_wh_per_answer`: arithmetic mean measured Wh across all attempted answer rows in scope | Use one canonical unit/field. Convert to mWh only at presentation time; do not store a second estimand. |
| `tok_per_w` | `decode_tokens_per_s_per_watt`: median decode tokens/s divided by the documented aggregate power estimator | Keep the efficiency estimand but make unit and aggregation explicit. |
| `wh_per_correct`, `energy_per_correct_wh` | `wh_per_det_check_equivalent`: sum energy / sum fractional deterministic-check credit | Replace the old names in canonical outputs and manuscript/report prose. |
| `energy_per_ktok_wh`, `j_per_tok` | `j_per_output_token` | Replace both names with one unit and field. |
| `pass_consistency` | `repeat_agreement` | Rename because agreement can describe repeated failure. |
| none | `pass_1`, `pass_all_k`, `all_safe_k` | New reliability export at model-scenario-condition grain. |
| `kv_cache_mb` | `kv_cache_<dtype>_payload_mb` when dtype is known, else `kv_cache_fp16_equivalent_mb` | Never imply the configured Q8 payload from an FP16 assumption. |

Adapter tests assert exact `v1` column names. `ARTIFACT_INVENTORY.md` records the
single schema and the raw evidence from which each canonical export is rebuilt.
Both valid KV-cache columns are enumerated in the machine-readable schema and
tested: the dtype-specific payload field for known dtype and the explicitly
labelled FP16-equivalent field for unknown dtype. No generic `kv_cache_mb` remains.

### 5.4 Known Repairs

1. Orient Friedman samples as models/treatments over shared scenarios/blocks.
2. Define `mbu` only as measured bandwidth divided by calibrated peak; rename the
   model-size × tok/s proxy.
3. Replace `Wh/correct` wording with
   `Wh/deterministic-check-equivalent`; include zero-score rows in the aggregate
   denominator rather than dropping them.
4. Require/capture the KV-cache dtype; do not label an FP16-equivalent estimate
   as the configured Q8 payload.
5. Separate repeat agreement from `pass^k` and correctness.
6. Use the explicit safety set (`guard` + `secure` or lifecycle destructive
   risk), not `class == guard` only.
7. Generate RAPL prose from observed `power.source`, never hard-code `psys`.
8. Treat non-positive token counters as invalid/missing ratios and expose their
   count.
9. Replace row-bootstrap claim intervals with deterministic scenario-cluster
  intervals in new claim-bearing reports; retain any legacy row-bootstrap only
  under an explicit `descriptive_observed_rows_ci` label.

## 6. Tests And Deterministic Gates

Add focused tests proving:

- model-only and scenario-only synthetic effects produce the expected Friedman
  orientation;
- both adapters emit the same MBU and energy-equivalent value for one fixture;
- every adapter derives the same `analysis_condition_key`; incomplete artifact or
  policy identity fails cross-run joins instead of collapsing conditions;
- zero deterministic scores remain in the energy denominator;
- dense, MoE, and unknown-KV-dtype rows cannot be mislabeled;
- five identical failures have repeat agreement `1.0` and `pass^5 = 0`;
- one unsafe secure repetition makes `all_safe^5 = 0` and is visible to the
  report safety gate;
- token ratio helpers reject zero counters;
- scenario-cluster resampling preserves all repetitions in a selected scenario,
  is deterministic under a fixed analysis seed, and differs from row resampling
  on a deliberately unbalanced fixture;
- new report, run-quality, model, scenario, and paper audits pass.
- analysis manifests accept exactly `analysis_schema_version=1`, bind source
  hashes, and prevent provisional bundles from feeding public claims.

Final gates:

```bash
python3 scripts/test-analysis-metrics.py
python3 scripts/test-report.py
python3 scripts/test-dataset.py
python3 scripts/test-judge-row-schema.py
python3 scripts/test-merge-wave.py
python3 scripts/test-report-run-quality.py
python3 scripts/audit-paper-data.py
python3 scripts/audit-paper-claims.py
scripts/build-analysis-site.sh --verify
quarto render docs/analysis
quarto render docs/analysis/paper.qmd --to typst
git diff --check
```

The repository's hyphen-named script tests are not discovered by default
`pytest`; the enumerated script-style suite is therefore the mandatory gate.
`scripts/test-report.py`, `scripts/test-analysis-metrics.py`, and
`scripts/test-dataset.py` are new gates, not pre-existing coverage. The
publication `--verify` gate copies manifest-bound evidence into an isolated
workspace, executes all three notebooks there, regenerates canonical `v1`
`data/site/*` and figures there, and compares those products with committed
evidence without writing to source notebooks or canonical artifacts. Unexpected
scientific-output changes fail the gate and require an explicit analysis-lock
correction review.

The Pages workflow runs on every push to `main`. Its `verify-analysis-v1` job
checks the schema/data contract, analysis regressions, public claims, local links,
privacy, and non-mutating notebook/output reproduction. Its `build` and `deploy`
jobs both depend on that verification job; render-only success cannot bypass a
failed scientific or publication gate.

## 7. Migration And Rollback

1. Add `scripts/test-report.py`, `scripts/test-analysis-metrics.py`,
   `scripts/test-dataset.py`, and the shared fixture before changing metric code.
2. Add the shared metric module without deleting existing paths.
3. Migrate `report.py`, validate, then migrate `scripts/metrics.py`, validate,
  then validate `dataset.py` remains a per-repetition export and add the
  separate reliability export.
4. Expand `ARTIFACT_INVENTORY.md` and `audit-paper-data.py` to cover raw bundles,
  snapshots, all required site CSV/JSON outputs, notebooks, figures, generated
  row catalogs, and their regeneration commands.
5. Consolidate canonical docs and update inbound links.
6. Archive completed evidence documents using history-preserving moves and the
  archive-link policy above.
7. Delete only merge-complete sources and the orphan script after uniqueness and
   reference gates pass.
8. Execute the notebook/site regeneration gate, then full deterministic and
  semantic gates.

Rollback is a normal file-level revert: restore moved/deleted files and point the
three adapters back to their prior local formulas. Claim-bearing corrections are
landed as one atomic correction-lock commit containing the schema, code,
snapshots, site exports, figures, notebook outputs, public prose, manuscript, and
a before/after artifact-hash manifest. Rollback reverts that complete commit, not
selected files. The active experiment is independent of this working tree and
requires no runtime rollback.

## 8. Phase Ledger

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 1 | Truth map and design | completed | Inventory, ownership map, dispositions, pre-implementation review | Independent GPT- and Claude-family PASS | PASS after three review loops; final design uses one canonical analysis schema, `v1`. Built-in subagent launch failed with `spawn EBADF`, so isolated read-only Copilot CLI reviewers (`gpt-5.4`, `claude-opus-4.8`) supplied the independent family gates. |
| 2 | Analysis-code contract | completed | Shared metric module, adapter migration, regression tests | Focused and existing analysis tests pass | `test-analysis-metrics` 27, `test-report` 11, `test-dataset` 5, `test-judge-row-schema` 8, `test-merge-wave` 8, `test-report-run-quality` 10, and run-env tests PASS; full `audit-paper-data.py` PASS; isolated `build-analysis-site.sh --verify` PASS. |
| 3 | Documentation and v1 artifact consolidation | completed | Migrate frozen snapshots/notebook/site to canonical v1; canonical map; merge current truth; repair links/statuses | One-schema artifact audit, paper/site builds, and claim audit pass | PASS: 17 artifact contracts / 14 validated files; 10 claim surfaces; exact 9,025/9,025/475 snapshots and 8,909 raw-reconstructible judge pairs with frozen provenance; 94-model quality/safety breadth; controlled 24-model systems scope; 7-of-24 three-axis and 2-of-94 quality-safety fronts; old 12-of-94 pooled-energy front withdrawn; all three notebooks reproduce; HTML/Typst render; `git diff --check` clean. |
| 4 | Obsolete removal | completed | Archive evidence; delete merge-complete/orphan sources | No broken links or unique evidence loss | PASS: 23 removed tracked documents preserved under `docs/archive/`; only `README_UPDATE_PLAN.md` and orphan `interim_analysis.py` deleted after merge; archive ledger present; no stale live references; 79-source/163-link audit and `git diff --check` pass. |
| 5 | Final tournament and release gate | completed | Full deterministic suite and dual-family adversarial review | Both families PASS; no unresolved major finding | PASS: every script test, 17-contract/14-artifact audit, 8,909 raw-reconstructed pair/provenance rows, 10 claim surfaces, 85-source/174-link audit, complete raw plain/gzip/tar privacy scan, isolated three-notebook reproduction, workflow/shell/diff checks, and HTML/Typst renders. Stateless read-only `gpt-5.4` and `claude-opus-4.8` both returned `VERDICT: PASS` after repairs for snapshot provenance, requested-policy persistence, complete-ensemble scoring, backend-aware identity/resume/reporting, conditional strategy-prompt lineage, incomplete-condition rejection, raw judge evidence/frozen provenance, explicit hashless policy, isolated CI, full archive privacy, and the 33/20/13 taxonomy counts. |

At most one phase is active. Later phases may continue autonomously only after
the current phase gate passes.

### Post-lock release preparation (2026-07-11)

- A 50-item blind packet now binds the correction-locked 94-model answers and
  `claude-opus-4.8` / `gpt-5.5` scores. Generation, lineage validation, and
  agreement scoring are implemented; all 50 human scores remain intentionally
  blank.
- Croissant 1.0 metadata, mixed-rights documentation, deterministic archival
  packaging, and release audits pass locally and with `mlcroissant==1.0.22`.
  Zenodo is selected for the dataset record; no DOI has been reserved or
  published.
- A detached checkout with a newly created exact-pinned environment reproduces
  all three notebooks, canonical exports, figures, HTML/PDF, Croissant record
  loading, and the deterministic release package without tracked mutation. A
  second human operator sign-off remains open.
- Python 3.14.5 and all transitive analysis/release packages are locked with
  universal SHA-256 hashes. Notebook comparison checks textual outputs and all
  inline plots at decoded-pixel level; dependency-license auditing covers all
  83 universal-lock packages, including marker-gated packages absent from the
  current platform, and explicitly verifies uv, Pillow, and mlcroissant.
- The optional `gemini-3.1-pro` third-judge smoke is blocked because the model is
  unavailable to the current account. The locked two-judge policy is unchanged.
- The active 152-model doctoral run remains outside this correction lock. Its
  completed-run promotion and analysis stay blocked on exact collection and
  persistence completion.

## 9. Independent Review Contract

The pre- and post-implementation judges must attack:

- evidence loss through merge/delete;
- accidental rewriting of locked findings;
- partial-run leakage into claim-bearing prose;
- metric estimand/name mismatch;
- crossed-design/pseudo-replication errors;
- backward compatibility of report/dataset columns;
- generated-site and raw-evidence reproducibility;
- unnecessary abstraction or archive churn.

Every major finding must cite a file/line and a concrete repair. A review that
did not run due to tooling failure is recorded as unavailable, never PASS.