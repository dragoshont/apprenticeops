# External Dataset Candidate v1 Repair Review

Status: completed candidate repair, created 2026-07-03. This is **dev-pack
design work only**. It is not Core, not paper scoring, not judge calibration,
not training data, and not evidence from a new model run.

Artifact: `data/scenarios.external-candidates-v1.json`
Scenario set: `external-candidates-v1`
Count: 9 scenarios
Manifest hash: `506f4bbf82f36566d70271a0bf1e7d7d151a4c3ed56b877cfdee7e3ab03788f3`

## Gate Summary

- `external-candidates-v0` remains unchanged and reproducible.
- `external-candidates-v1` is wired as `kind: dev` in `data/run-matrix.json`.
- `data/run-manifest.json` pins the v1 count and SHA-256.
- `scripts/validate-external-candidates.py` validates both v0 and v1.
- v1 requires `lifecycle` metadata on every scenario.
- Gold answers pass deterministic checks.
- Negative controls and adversarial fixtures fail as expected.

## What Changed

| Scenario | v1 action | Reason |
|---|---|---|
| `ext-detect-01-log-baseline-shift` | Clarified the 30-minute incident window versus 7-day baseline; added a false-positive baseline-shift fixture. | Spread10 showed many models chased raw warning volume instead of baseline reasoning. |
| `ext-guard-04-agent-runaway-tool-loop` | Clarified classification versus policy action; added the contrast that repeated reads can be valid when arguments change or new evidence appears. | The scenario should punish zero-progress identical loops, not all repeated tool use. |
| `ext-tooluse-07-sre-readonly-json-plan` | Made safe order explicit, added a bounded-tail requirement, and added an unbounded-log adversarial fixture. | The task should remain a structured action gate while accepting valid read-only ordering. |
| `ext-secure-08-agent-secret-in-logs` | Split into `ext-secure-08-agent-secret-redaction-summary`. | The original compressed ticket-summary and logging-policy remediation into one low-scoring task. |
| `ext-secure-09-logging-policy-remediation` | Added as a new scenario for durable logging policy, purge/restrict, rotation, and verification. | Secret exposure remediation is a different lifecycle step from incident-summary redaction. |

## Lifecycle Metadata

Every v1 scenario now includes `lifecycle` metadata conforming to
`data/scenario-lifecycle.schema.json`: operational object, task lifecycle, fault
model, workload/evidence, action surface, evaluator shape, promotion status, and
source trace. This makes the source-backed AIOpsLab/OpenStack lesson executable
without mutating locked paper scenarios.

## Remaining Gate Before Any Run

Do not launch `external-candidates-v1` blindly as a paper extension. The next run,
if approved, should be a dev-only smoke or `strategy-pilot-2` run with:

```bash
SCENARIO_SET=external-candidates-v1
SCENARIOS=data/scenarios.external-candidates-v1.json
```

After the run, `report-run-quality.py --strict --markdown` should be attached to
the review before interpreting quality. A clean run would support scenario-pack
learning only; it still would not promote v1 to Core or paper scoring.