# External Dataset Integration Plan

Status: phased plan with Phases 1-6 completed and Phase 7 blocked. This plan is
for improving ApprenticeOps scenario coverage and failure taxonomy. It is **not**
a plan to change the locked 94-model paper result, and it is **not** a plan to
fine-tune Pareto models until held-out contamination gates exist.

## Scope honesty

External AIOps/SRE datasets are useful, but they are not neutral. Most are
synthetic, public, and structurally different from ApprenticeOps' homelab-rooted
scenarios. In this project they currently improve **scenario design and failure
taxonomy only**. Judge calibration, training, RAG, and Core promotion remain
blocked until a later phase explicitly reopens them with separate gates. External
material must not silently enter the held-out test set or the off-the-shelf
Pareto-model paper claim.

## Acceptance criteria

1. Every external source has a local manifest entry: source URL, license,
   redistribution status, training status, derivative-scenario status, row count,
   schema, synthetic/real provenance, and recommended use.
2. Downloaded data remains outside git under `downloads/` unless a tiny manifest is
   intentionally promoted.
3. Current `core-current` remains frozen as the baseline Core v1 scenario set.
4. External-derived scenarios go into candidate or dev pools first, never directly
   into Core.
5. Any future tuned model is reported as `ApprenticeOps-tuned`, separate from the
   off-the-shelf model-selection result.

## Phase ledger

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 0 | Decision and boundary | completed | Use external datasets for scenario/taxonomy improvement first; defer Pareto fine-tuning. | User accepted direction after adversarial discussion. | Proceed with safeguards. |
| 1 | Inventory and schema profile | completed | Read local downloaded datasets under `downloads/external-datasets/`; emit manifest, schema summaries, label distributions, and source risk notes. | `scripts/analyze-external-datasets.py` completes and writes `manifest.json`, `schema-summary.md`, and `candidate-map.md`. | Completed; evidence archived at `docs/archive/EXTERNAL_DATASET_PHASE1_SUMMARY.md`. |
| 2 | Rights and contamination ledger | completed | Classify every source as training/dev allowed, scenario-inspiration-only, judge-calibration-only, literature-only, or do-not-use. | Human-readable ledger exists; proprietary/non-redistributable sources are blocked from data import. | Completed at source level in `docs/EXTERNAL_DATASET_RIGHTS_LEDGER.md`; raw redistribution blocked, training deferred, pattern-level candidate design conditionally allowed. |
| 3 | Candidate scenario generation | completed | Convert selected source patterns into ApprenticeOps candidate scenarios, not Core. | Every candidate has source trace, class, difficulty, grounding, gold answer, deterministic checks, and judge rubric. | Completed in `data/scenarios.external-candidates-v0.json`; validator `scripts/validate-external-candidates.py` passes. |
| 4 | Scenario adversarial review | completed | Attack candidate scenarios for leakage, easy checks, unsafe gold answers, low operational value, and class imbalance. | High/medium findings resolved; promoted set has a versioned name such as `api-rca-v1` or `core-external-derived-v1`. | Completed as an unpromoted candidate gate: first review returned REVISE, repairs were applied, and follow-up leakage/safety plus quality reviews returned PASS. No candidate has been promoted. |
| 5 | Dev evaluation | completed | Run selected off-the-shelf Pareto models on candidate/dev scenario sets after Phase 4 candidate-gate review. | Reliability report clean enough to interpret; results reported separately from Core v1. | Dryrun smoke, `strategy-pilot-2`, and `spread10` completed for `external-candidates-v0`; v0 remains dev-only. Judge calibration remains blocked. |
| 6 | Candidate-v1 repair | completed | Convert Phase 5 error review into a repaired candidate pack with lifecycle metadata. | v1 validates separately, is wired as `kind: dev`, and does not mutate v0 or Core. | Completed in `data/scenarios.external-candidates-v1.json`; evidence archived at `docs/archive/EXTERNAL_DATASET_CANDIDATE_V1_REPAIR_REVIEW.md`. |
| 7 | Optional tuned-model track | blocked | Fine-tune/LoRA/RAG experiments only if the user later approves a separate tuned-model project. | Model card, training data manifest, held-out hash exclusions, and separate tuned-vs-base reporting. | Blocked; no training or RAG data use is approved by this plan. |

## Source classes and intended use

| Source family | Use first | Do not use for |
|---|---|---|
| AIOpsLab / ITBench | Scenario architecture, live-agent task shape, and review rubric ideas. | Direct training rows, judge calibration, or Core scoring. |
| SMOLTRACE SRE tasks | Tool-call/action-format dev tasks and SRE tool-use examples. | Core paper claims; it is synthetic and small. |
| AI Agent Failure Benchmark | Failure taxonomy and guardrail diagnostics. | Judge calibration, model-quality scoring, or Core promotion. |
| AFID API failure logs | API/log RCA patterns, remediation labels, scenario generation. | Off-the-shelf Core v1 scoring or claims about real incident frequency. |
| CI/CD Pipeline Failures | Build/test/deploy triage scenarios. | Direct Core replacement. |
| AIOps Log Monitoring | Detect/monitor/log-summary candidates. | Safety/mitigation claims by itself. |
| AI Agent Observability | Meta-failure taxonomy and operational incident-dashboard patterns. | Judge calibration, training, or SRE benchmark claims. |
| ITSM Incident-System Relationship | Graph/relationship examples. | Language-model fine-tuning by itself; the schema is too thin. |
| Salesforce PRB RCA paper | Literature evidence that PRB incident text is valuable for RCA. | Data import; the 2K PRB corpus appears proprietary. |

## Required gates before promotion

- **Rights gate:** license, ToS, redistribution, derivative-scenario, and training
  status recorded per source.
- **Contamination gate:** exact-row hashes and near-duplicate checks for any row
  that influences a held-out scenario.
- **Scenario quality gate:** candidate is evidence-shaped, action-oriented,
  class-labelled, and model-discriminating.
- **Safety gate:** no gold answer endorses destructive or irreversible action
  without explicit guardrails.
- **Reporting gate:** external-derived results are reported separately from
  `core-current` until a new version is explicitly locked.

## Phase 3 candidate artifact

Phase 3 produced `data/scenarios.external-candidates-v0.json`, a candidate-only
scenario catalog. After Phase 4 review, Phase 5 wires it as
`external-candidates-v0` in `data/run-matrix.json` and `data/run-manifest.json`
with `kind: dev`. It remains outside `core-current`, outside `data/scenarios.json`,
and outside the locked paper result.

The validator is:

```bash
python3 scripts/validate-external-candidates.py
```

It enforces no Core ID overlap, candidate-only provenance metadata, source hash
traceability, gold-answer deterministic checks, and a negative-control failure
for every candidate.

The scenario-set gate is:

```bash
python3 scripts/validate-scenarios.py
```

It verifies `external-candidates-v0` and `external-candidates-v1` are approved by
the manifest, contain only non-Core candidate IDs, and are not the default
scenario set.

## Phase 5 dryrun gate

The first evaluation is deliberately small:

```bash
RUN_ID=external-v0-dryrun-baseline-$(date -u +%Y%m%d-%H%M%S) \
  MODEL_SET=dryrun MODELS=data/models.dryrun.txt \
  SCENARIO_SET=external-candidates-v0 \
  SCENARIOS=data/scenarios.external-candidates-v0.json \
  MEMORY_CONTEXT=none INFERENCE_STRATEGY=baseline \
  setsid nohup ./scripts/run-e2e.sh >/tmp/external-v0-dryrun.boot 2>&1 </dev/null &
```

Completed run: `external-v0-dryrun-baseline-20260703-063154` on branch
`experiment/external-v0-dryrun-baseline-20260703-063154`.

Smoke result:

- Inference rows: 80/80.
- Models committed: 2/2 (`qwen2.5:0.5b`, `smollm2:135m`).
- Reliability: DNF 0/80, zero-output stalls 0/80, length flags 7/80.
- Judge rows: 161/160 due to one duplicate `gpt-5.4` judge row for
  `smollm2:135m` / `ext-test-03-cicd-flaky-vs-regression` / rep 2.
- Mean judge scores, including the duplicate row: `qwen2.5:0.5b` 1.512,
  `smollm2:135m` 1.075.

This is a dev-smoke run only. It does not calibrate judges, train models, change
Core, or support paper claims. The duplicate judge row makes it unsuitable as a
clean quantitative result without de-duplication, but it is sufficient evidence
that the dev scenario set launches, preflights, infers, judges, and persists.

## Phase 5 strategy-pilot gate

After adversarial review of the dryrun smoke, the next approved run was the
smallest meaningful dev-quality signal beyond dryrun:

```bash
RUN_ID=external-v0-strategy-pilot-2-baseline-$(date -u +%Y%m%d-%H%M%S) \
  MODEL_SET=strategy-pilot-2 MODELS=data/models.strategy-pilot-2.txt \
  SCENARIO_SET=external-candidates-v0 \
  SCENARIOS=data/scenarios.external-candidates-v0.json \
  MEMORY_CONTEXT=none INFERENCE_STRATEGY=baseline \
  setsid nohup ./scripts/run-e2e.sh >/tmp/external-v0-strategy-pilot-2.boot 2>&1 </dev/null &
```

Completed run: `external-v0-strategy-pilot-2-baseline-20260703-081018` on branch
`experiment/external-v0-strategy-pilot-2-baseline-20260703-081018`.

Gate result:

- Inference rows: 80/80.
- Judge tuples: 160/160 unique; duplicate judge rows: 0.
- Reliability: DNF 0/80, zero-output stalls 0/80, length flags 0/80.
- Judge integrity: empty evidence 0, missing criteria 0.
- Models committed: 2/2 (`qwen3:4b-instruct-2507-q4_K_M`, `granite4:micro`).
- Mean judge scores: `qwen3:4b-instruct-2507-q4_K_M` 3.625,
  `granite4:micro` 2.688.

This result is a clean **dev evaluation** for the reviewed external candidate set.
It is still not Core, not paper scoring, not judge calibration, and not training
data. `spread10` remains unapproved until a separate adversarial go/no-go review.

The subsequent `spread10` dev run also completed cleanly; see
`docs/archive/EXTERNAL_DATASET_PHASE5_SPREAD10_REVIEW.md`.

## Phase 6 candidate-v1 repair

Phase 6 produced `data/scenarios.external-candidates-v1.json`, a repaired
candidate-only catalog derived from the Phase 5 error review. It keeps v0
reproducible, splits the compressed security scenario, clarifies baseline and
agent-loop semantics, adds lifecycle metadata, and wires v1 as a dev-only scenario
set in `data/run-matrix.json` and `data/run-manifest.json`.

Review artifact:

```text
docs/archive/EXTERNAL_DATASET_CANDIDATE_V1_REPAIR_REVIEW.md
```

No v1 experiment has been run yet. Any future v1 run must be labeled dev-only and
reported with `report-run-quality.py --strict --markdown` before interpretation.

## Overnight Phase 1 run

```bash
mkdir -p downloads/external-datasets/analysis
setsid nohup python3 scripts/analyze-external-datasets.py \
  --input downloads/external-datasets \
  --out downloads/external-datasets/analysis \
  >downloads/external-datasets/analysis/run.log 2>&1 </dev/null &
```

The run is intentionally read-only over source data. It writes ignored analysis
artifacts under `downloads/` and does not modify benchmark scenarios, model
rosters, or paper results.