# External Dataset Phase 1 Summary

Status: Phase 1 completed after adversarial revision. Raw downloads and generated
analysis remain under ignored `downloads/external-datasets/`. This file records
the durable summary only.

## Scope

The external datasets are being evaluated for **scenario coverage, failure
taxonomy, judge calibration, and future dev/training material**. They are not part
of the locked 94-model paper result and are not allowed into `core-current`
without a separate promotion gate.

## Sources profiled

| Source | Rows / tasks | License from metadata | Provenance risk | Recommended first use |
|---|---:|---|---|---|
| SMOLTRACE SRE tasks | 80 tasks (README hint; parquet schema not parsed) | MIT | synthetic-not-real-frequency | Tool-use/action-format dev tasks |
| AIOps Log Monitoring & Failure Detection | 1,747 rows | MIT | realness-unverified | Detect/monitor/log-summary scenario inspiration |
| AI Agent Observability | 10,000 rows | Apache-2.0 | synthetic-not-real-frequency | Agent incident taxonomy and operational dashboard patterns |
| AFID API Failure Intelligence | 220,000 rows | Apache-2.0 | synthetic-not-real-frequency | API/log RCA scenario generation and remediation labels |
| CI/CD Pipeline Failures | 45,000 rows | Apache-2.0 | synthetic-not-real-frequency | Build/test/deploy triage and rollback/flaky-test scenarios |
| ITSM Incident-System Relationship | 500 rows | Apache-2.0 | realness-unverified | Thin incident-system relationship examples only |
| AI Agent Failure Benchmark | 1,815 CSV rows (card says 1,500) | Apache-2.0 | synthetic-not-real-frequency | Failure taxonomy and judge/guardrail calibration |

## Key observations

- The public datasets are useful, but mostly **synthetic or unverified-realness**.
  They must not be used to infer real incident frequencies.
- The AI Agent Failure Benchmark has the best failure-taxonomy schema:
  `prompt`, `context`, `expected_answer`, `agent_answer`, `failure_type`,
  `failure_severity`, and `notes`.
- AFID is the largest source and is useful for API/log RCA patterns, but its
  `root_cause` and `resolution_action` labels should seed candidate scenarios,
  not become direct gold answers.
- CI/CD Pipeline Failures fills a gap in ApprenticeOps: build/test/deploy failure
  triage, rollback, flaky-test, and resource-exhaustion cases.
- SMOLTRACE is small but useful for action/tool-call discipline; the parquet rows
  need a reviewed parser before row-level use.
- ITSM Incident-System Relationship is too thin for model training by itself, but
  can inspire graph/relationship tasks.

## Adversarial revisions applied

The first Phase 1 output was revised after review:

- Added canonical source URLs and platform metadata to the manifest.
- Added explicit `needs-human-review` rights statuses for redistribution,
  training, and derivative-scenario use.
- Changed large CSV label distributions from implicit sampling to full-row counts.
- Added `realness-unverified` when a public dataset does not independently prove
  real operational provenance.
- Added SMOLTRACE parquet file listing and 80-task README hint.

## Decision

Proceed to Phase 2 only as a **rights and contamination ledger**. Scenario
generation, Core promotion, model fine-tuning, and judge calibration remain blocked
until the ledger clears a source for that exact use.
