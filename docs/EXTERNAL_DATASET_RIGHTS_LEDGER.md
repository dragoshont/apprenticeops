# External Dataset Rights and Contamination Ledger

Status: preliminary Phase 2 ledger. Conservative by design: **no source is cleared
for training, derivative scenarios, redistribution, or judge calibration until the
corresponding status is changed from `blocked-pending-review`**.

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
| SMOLTRACE SRE tasks | https://huggingface.co/datasets/MCP-1st-Birthday/smoltrace-site-reliability-engineering-tasks | MIT | synthetic | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Tool-use pattern research only |
| AIOps Log Monitoring & Failure Detection | https://www.kaggle.com/datasets/expertshubham/aiops-log-monitoring-and-failure-detection-dataset | MIT | realness-unverified | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Detect/monitor pattern research only |
| AI Agent Observability | https://www.kaggle.com/datasets/hamzaabbasai/ai-agent-observability-dataset | Apache-2.0 | synthetic | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Taxonomy research only |
| AFID API Failure Intelligence | https://www.kaggle.com/datasets/mirzayasirabdullah07/api-failure-intelligence-dataset-afid | Apache-2.0 | synthetic | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | API/RCA pattern research only |
| CI/CD Pipeline Failures | https://www.kaggle.com/datasets/mirzayasirabdullah07/cicd-pipeline-failure-logs-dataset-for-aiops | Apache-2.0 | synthetic / real-world-inspired | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | CI/CD failure pattern research only |
| ITSM Incident-System Relationship | https://www.kaggle.com/datasets/nalisha/itsm-incident-system-relationship-dataset | Apache-2.0 | realness-unverified | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Graph/relationship pattern research only |
| AI Agent Failure Benchmark | https://www.kaggle.com/datasets/sunil123kumar/ai-agent-failure-benchmark-dataset | Apache-2.0 | synthetic | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Failure-taxonomy research only |
| Salesforce PRB RCA paper | https://arxiv.org/abs/2204.11598 | CC BY paper; data not public | proprietary incident investigations | blocked | blocked | blocked | blocked | Literature citation only |
| AIOpsLab | https://github.com/microsoft/AIOpsLab | MIT repo | live benchmark framework | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Scenario architecture research only |
| ITBench | https://github.com/itbench-hub/ITBench | Apache-2.0 repo | live benchmark framework | blocked-pending-review | blocked-pending-review | blocked-pending-review | blocked-pending-review | Scenario architecture research only |

## Required fields before unblocking a source

- License text and dataset terms captured.
- Redistribution and derivative-use decision recorded.
- Exact source file hash recorded.
- Row-level hashes recorded for any row used to create a candidate scenario.
- Near-duplicate check defined for any promoted candidate scenario.
- Human/adversarial review confirms the candidate is not a disguised public row.
- Scenario set name is new and separate from `core-current`.

## Phase 2 verdict

This ledger is enough to prevent accidental misuse. It is **not** enough to start
training, judge calibration, or candidate scenario generation. The next safe step
is source-by-source rights review and a row-hash extraction pass for sources that
survive that review.
