# External Dataset Integration Plan

Status: phased plan with Phases 1-3 completed and Phase 4 next. This plan is
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
| 1 | Inventory and schema profile | completed | Read local downloaded datasets under `downloads/external-datasets/`; emit manifest, schema summaries, label distributions, and source risk notes. | `scripts/analyze-external-datasets.py` completes and writes `manifest.json`, `schema-summary.md`, and `candidate-map.md`. | Completed; durable summary in `docs/EXTERNAL_DATASET_PHASE1_SUMMARY.md`. |
| 2 | Rights and contamination ledger | completed | Classify every source as training/dev allowed, scenario-inspiration-only, judge-calibration-only, literature-only, or do-not-use. | Human-readable ledger exists; proprietary/non-redistributable sources are blocked from data import. | Completed at source level in `docs/EXTERNAL_DATASET_RIGHTS_LEDGER.md`; raw redistribution blocked, training deferred, pattern-level candidate design conditionally allowed. |
| 3 | Candidate scenario generation | completed | Convert selected source patterns into ApprenticeOps candidate scenarios, not Core. | Every candidate has source trace, class, difficulty, grounding, gold answer, deterministic checks, and judge rubric. | Completed in `data/scenarios.external-candidates-v0.json`; validator `scripts/validate-external-candidates.py` passes. |
| 4 | Scenario adversarial review | next | Attack candidate scenarios for leakage, easy checks, unsafe gold answers, low operational value, and class imbalance. | High/medium findings resolved; promoted set has a versioned name such as `api-rca-v1` or `core-external-derived-v1`. | Ready to start; no candidate has been promoted. |
| 5 | Dev evaluation | not-started | Run selected off-the-shelf Pareto models on candidate/dev scenario sets after Phase 4 promotion. | Reliability report clean enough to interpret; results reported separately from Core v1. | Not started; judge calibration remains blocked. |
| 6 | Optional tuned-model track | blocked | Fine-tune/LoRA/RAG experiments only if the user later approves a separate tuned-model project. | Model card, training data manifest, held-out hash exclusions, and separate tuned-vs-base reporting. | Blocked; no training or RAG data use is approved by this plan. |

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
scenario catalog. It is intentionally not referenced by `data/run-matrix.json`,
`data/run-manifest.json`, or `core-current`. The file can be reviewed and
validated, but it is not a benchmark set until Phase 4 decides what, if anything,
survives.

The validator is:

```bash
python3 scripts/validate-external-candidates.py
```

It enforces no Core ID overlap, candidate-only provenance metadata, source hash
traceability, gold-answer deterministic checks, and a negative-control failure
for every candidate.

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