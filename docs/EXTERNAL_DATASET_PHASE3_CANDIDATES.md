# External Dataset Phase 3 Candidate Scenarios

Status: Phase 3 completed. These scenarios are **candidate-only**. They are not
Core, not paper scoring material, not judge calibration material, and not
training data.

## Scope honesty

We used the reviewed external datasets as pattern sources, not as row sources.
No exact external row text, prompt, context, expected answer, label rationale,
hostname, ID, or numeric row was copied into the candidates. This does not make
the candidates ready for a benchmark; it makes them ready for Phase 4 attack.

## Artifact

- Candidate catalog: `data/scenarios.external-candidates-v0.json`
- Validator: `scripts/validate-external-candidates.py`
- Gate command: `python3 scripts/validate-external-candidates.py`

The validator checks that candidate IDs do not overlap `data/scenarios.json`,
that every scenario has source trace metadata, that `pattern_only=true`, that
`copied_source_rows=false`, that `source_rows_used=[]`, that
`row_hashes_used=[]`, that `core_eligible=false`, that no live-looking secret
pattern is present, and that each gold answer passes its deterministic checks
while negative controls and adversarial fixtures fail as expected.

## Provenance Method

The Phase 3 synthesis inputs were the Phase 1/2 source summaries, the rights
ledger, and the generated source-file hashes. Raw dataset rows were not read to
write the candidate contexts or gold answers. Because no concrete source row was
used, every candidate records `source_rows_used=[]` and `row_hashes_used=[]`.
If a later phase uses a concrete row, that phase must add row hashes and a
near-duplicate review before the item can be considered for a held-out set.

## Candidate Set

| Candidate | Class | Source pattern | What it tests |
|---|---|---|---|
| `ext-detect-01-log-baseline-shift` | detect | AIOps log monitoring | Baseline-aware incident detection and dependency triage. |
| `ext-diagnose-02-api-contract-regression` | diagnose | API failure intelligence | Contract-boundary RCA for deterministic 400s. |
| `ext-test-03-cicd-flaky-vs-regression` | test | CI/CD failures | Flaky-test versus deterministic regression triage. |
| `ext-guard-04-agent-runaway-tool-loop` | guard | Agent failure / observability | Tool-loop detection, stop policy, and trace preservation. |
| `ext-monitor-05-zero-output-timeout-policy` | monitor | Agent observability | Reliability reporting for multi-call zero-output timeout. |
| `ext-diagnose-06-itsm-blast-radius` | diagnose | ITSM dependency graph | Dependency-aware RCA and blast-radius reasoning. |
| `ext-tooluse-07-sre-readonly-json-plan` | augment | SRE tool-use tasks | Strict JSON tool-call planning without unsafe mutation. |
| `ext-secure-08-agent-secret-in-logs` | secure | Agent observability / failure | Secret redaction, credential rotation, and logging remediation. |

## Phase 3 Verdict

The candidate artifact is concrete enough for review and constrained enough to
avoid accidental benchmark contamination. Phase 4 should now attack each item for
leakage, weak deterministic checks, overfit gold answers, unsafe remediation,
class imbalance, and low operational value. No candidate should be promoted until
that review is complete.

## Phase 4 Review Status

The first Phase 4 review returned `REVISE`, not `PASS`. The findings were useful:
the original validator only proved shape/gold sanity, negative controls were too
easy, one scenario contained a live-looking token string, and several candidates
needed explicit provenance review rather than assertion-only metadata.

Repairs applied:

- Replaced the live-looking token with `EXAMPLE_BEARER_TOKEN_DO_NOT_USE` and added
	validator-level checks for common live-looking secret patterns.
- Added candidate-level `contamination_review` metadata stating that raw source
	rows were not read and no row-derived content was used.
- Added at least two adversarial fixtures per candidate, with expected failure
	thresholds and specific `must_fail` checks where partial credit is legitimate.
- Replaced the strict exact-JSON equality check in the SRE tool-use candidate with
	property checks for read-only tools, namespace, target, and no mutation.

Follow-up Phase 4 reviews returned `PASS` for leakage/safety/provenance and for
candidate quality-gate mechanics. This is a **reviewed candidate gate**, not a
promotion verdict. No candidate has been promoted or wired into runs.