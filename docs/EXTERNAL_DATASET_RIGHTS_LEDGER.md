# External Dataset Rights and Contamination Ledger

Status: Phase 2 source-level review completed. Conservative by design: **raw
redistribution remains blocked**, **model training remains a later tuned-model
track**, and **Core v1 remains frozen**. Phase 3 may use selected sources for
pattern-level candidate scenario design only: no exact row text, prompts,
contexts, expected answers, or label rationales may enter held-out tests.

## Rules

1. `core-current` remains frozen. External-derived material must use a new scenario
   set name.
2. No exact row text, prompt, context, expected answer, or label rationale may enter
   a held-out test set.
3. RAG/memory context derived from these sources is treated as training/dev
   material and must be excluded from held-out runs.
4. Fine-tuned models trained on these sources must be reported as
   `ApprenticeOps-tuned`, never as off-the-shelf Pareto models.
5. Proprietary or paper-only sources, including Salesforce PRB incident data, are
   literature-only unless explicit data rights are obtained.

## Ledger

| Source | URL | License | Provenance | Redistribution | Training | Derivative scenarios | Judge calibration | Current allowed use |
|---|---|---|---|---|---|---|---|---|
| SMOLTRACE SRE tasks | https://huggingface.co/datasets/MCP-1st-Birthday/smoltrace-site-reliability-engineering-tasks | MIT | synthetic | blocked-no-vendoring | phase6-conditional | phase3-conditional-pattern-only | blocked | Tool-use pattern research; parquet row use blocked until parser review |
| AIOps Log Monitoring & Failure Detection | https://www.kaggle.com/datasets/expertshubham/aiops-log-monitoring-and-failure-detection-dataset | MIT | realness-unverified | blocked-no-vendoring | phase6-conditional | phase3-conditional-pattern-only | blocked | Detect/monitor candidate patterns only |
| AI Agent Observability | https://www.kaggle.com/datasets/hamzaabbasai/ai-agent-observability-dataset | Apache-2.0 | synthetic | blocked-no-vendoring | phase6-conditional | phase3-conditional-pattern-only | phase5-conditional-split-only | Agent incident taxonomy patterns only |
| AFID API Failure Intelligence | https://www.kaggle.com/datasets/mirzayasirabdullah07/api-failure-intelligence-dataset-afid | Apache-2.0 | synthetic | blocked-no-vendoring | phase6-conditional | phase3-conditional-pattern-only | blocked | API/RCA candidate patterns only |
| CI/CD Pipeline Failures | https://www.kaggle.com/datasets/mirzayasirabdullah07/cicd-pipeline-failure-logs-dataset-for-aiops | Apache-2.0 | synthetic / real-world-inspired | blocked-no-vendoring | phase6-conditional | phase3-conditional-pattern-only | blocked | CI/CD failure candidate patterns only |
| ITSM Incident-System Relationship | https://www.kaggle.com/datasets/nalisha/itsm-incident-system-relationship-dataset | Apache-2.0 | realness-unverified | blocked-no-vendoring | blocked-too-thin | phase3-conditional-pattern-only | blocked | Graph/relationship patterns only |
| AI Agent Failure Benchmark | https://www.kaggle.com/datasets/sunil123kumar/ai-agent-failure-benchmark-dataset | Apache-2.0 | synthetic | blocked-no-vendoring | phase6-conditional | phase3-conditional-pattern-only | phase5-conditional-split-only | Failure taxonomy and guardrail patterns only |
| Salesforce PRB RCA paper | https://arxiv.org/abs/2204.11598 | CC BY paper; data not public | proprietary incident investigations | blocked | blocked | blocked | blocked | Literature citation only |
| AIOpsLab | https://github.com/microsoft/AIOpsLab | MIT repo | live benchmark framework | blocked-no-vendoring | blocked-not-row-data | phase3-conditional-pattern-only | blocked | Scenario architecture research only |
| ITBench | https://github.com/itbench-hub/ITBench | Apache-2.0 repo | live benchmark framework | blocked-no-vendoring | blocked-not-row-data | phase3-conditional-pattern-only | blocked | Scenario architecture research only |

Status vocabulary:

- `blocked-no-vendoring`: do not commit raw source data or redistributed copies.
- `phase3-conditional-pattern-only`: candidate scenarios may be inspired by
   source patterns, but cannot copy row text, prompts, contexts, expected answers,
   label rationales, hostnames, IDs, or exact numeric rows into held-out tests.
- `phase5-conditional-split-only`: judge calibration may use a reviewed split, but
   never examples later used for benchmark scoring.
- `phase6-conditional`: training/fine-tuning requires a model card, train/dev/test
   split, row hashes, held-out exclusions, and separate tuned-model reporting.
- `blocked-too-thin`: the source is not rich enough to train a language model by
   itself.
- `blocked-not-row-data`: the source is a framework/paper, not an imported row
   dataset.

## Source file hash anchors

Raw downloads remain ignored, but these hashes identify the source files used in
Phase 1.

| Source | File | Bytes | SHA-256 |
|---|---|---:|---|
| SMOLTRACE SRE tasks | `README.md` | 29319 | `9dae851dc6281bc963dbe41f8c3596f6299c9f5e604c6f5fc655eae73c2ad92e` |
| SMOLTRACE SRE tasks | `data/train-00000-of-00001.parquet` | 15094 | `c71479ad29f038381e18e5477abb6eb8c3409a4ddf90200d0fca24e7dd6c5886` |
| AIOps Log Monitoring & Failure Detection | `dataset.zip` | 65472 | `75eb160da90e3dcaf9dd5c85c0d4b50e99950874b8098f1de322e858ec0e79ef` |
| AI Agent Observability | `dataset.zip` | 418881 | `1fa861897d5ec644c04d457f8d7334c251bfa6af9e5f0b6e87b56f4b2b160201` |
| AFID API Failure Intelligence | `dataset.zip` | 12902996 | `ef5c1e26b401d339238d14a5dc4fd5094f3e04a3d41ca9a944d558d4f3f9546d` |
| CI/CD Pipeline Failures | `dataset.zip` | 7979559 | `a80b3b259f8c31fa7b468f90027efbf0d805387928f5c6759867577e9f4f7ed3` |
| ITSM Incident-System Relationship | `dataset.zip` | 2171 | `41cdc1e4880695b290b4bc8d6872226f153c712b377f12c679ed1b6377e953de` |
| AI Agent Failure Benchmark | `dataset.zip` | 106871 | `fe9d86f7cfafb66379e7072471ac5cd55042c38b21a7b42509fe6cb499c4d103` |

## Required fields before unblocking a source further

- License text and dataset terms captured.
- Redistribution and derivative-use decision recorded.
- Exact source file hash recorded.
- Row-level hashes recorded for any row used to create a candidate scenario.
- Near-duplicate check defined for any promoted candidate scenario.
- Human/adversarial review confirms the candidate is not a disguised public row.
- Scenario set name is new and separate from `core-current`.

## Phase 2 verdict

This ledger is enough to start **Phase 3 candidate scenario design** from patterns
only. It is **not** enough to train models, calibrate judges, promote scenarios to
Core, or redistribute raw data. Any candidate scenario that uses a concrete row
must first add that row's hash and pass near-duplicate review.
