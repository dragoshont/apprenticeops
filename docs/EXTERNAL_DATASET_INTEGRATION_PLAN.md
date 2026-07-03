# External Dataset Integration Plan

Status: phased plan with Phase 1 completed and a conservative Phase 2 ledger
started. This plan is
for improving ApprenticeOps scenario coverage and failure taxonomy. It is **not**
a plan to change the locked 94-model paper result, and it is **not** a plan to
fine-tune Pareto models until held-out contamination gates exist.

## Scope honesty

External AIOps/SRE datasets are useful, but they are not neutral. Most are
synthetic, public, and structurally different from ApprenticeOps' homelab-rooted
scenarios. They can improve **scenario design, taxonomy, judge calibration, and
future dev data**. They must not silently enter the held-out test set or the
off-the-shelf Pareto-model paper claim.

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
| 2 | Rights and contamination ledger | in-progress | Classify every source as training/dev allowed, scenario-inspiration-only, judge-calibration-only, literature-only, or do-not-use. | Human-readable ledger exists; proprietary/non-redistributable sources are blocked from data import. | Preliminary conservative ledger in `docs/EXTERNAL_DATASET_RIGHTS_LEDGER.md`; all active uses blocked pending review. |
| 3 | Candidate scenario generation | not-started | Convert selected source patterns into ApprenticeOps candidate scenarios, not Core. | Every candidate has source trace, class, difficulty, grounding, gold answer, deterministic checks, and judge rubric. | Not started. |
| 4 | Scenario adversarial review | not-started | Attack candidate scenarios for leakage, easy checks, unsafe gold answers, low operational value, and class imbalance. | High/medium findings resolved; promoted set has a versioned name such as `api-rca-v1` or `core-external-derived-v1`. | Not started. |
| 5 | Dev evaluation | not-started | Run selected off-the-shelf Pareto models on candidate/dev scenario sets. | Reliability report clean enough to interpret; results reported separately from Core v1. | Not started. |
| 6 | Optional tuned-model track | not-started | Fine-tune/LoRA/RAG experiments against train/dev material only. | Model card, training data manifest, held-out hash exclusions, and separate tuned-vs-base reporting. | Not started. |

## Source classes and intended use

| Source family | Use first | Do not use for |
|---|---|---|
| AIOpsLab / ITBench | Scenario architecture, live-agent task shape, evaluation rubric ideas. | Direct training rows unless task data and licenses are explicitly imported. |
| SMOLTRACE SRE tasks | Tool-call/action-format dev tasks and SRE tool-use examples. | Core paper claims; it is synthetic and small. |
| AI Agent Failure Benchmark | Failure taxonomy, judge calibration, guardrail diagnostics. | Model-quality scoring unless held out and calibrated. |
| AFID API failure logs | API/log RCA patterns, remediation labels, scenario generation. | Off-the-shelf Core v1 scoring or claims about real incident frequency. |
| CI/CD Pipeline Failures | Build/test/deploy triage scenarios. | Direct Core replacement. |
| AIOps Log Monitoring | Detect/monitor/log-summary candidates. | Safety/mitigation claims by itself. |
| AI Agent Observability | Meta-failure taxonomy and operational incident dashboards. | SRE benchmark claims without curation. |
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