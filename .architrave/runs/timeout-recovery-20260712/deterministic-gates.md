# Deterministic Gates

## checks

- `gates/checks.sh --quick`: PASS after knowledge-profile bootstrap.
- Architrave v0.10.3 JSON schema validation: PASS.
- `harness/validate-run.sh .architrave/runs/timeout-recovery-20260712`: PASS after substantive artifact population; one active phase.
- `gates/checks.sh`: PASS. Shell syntax, Python compilation, analyzer/run/report/privacy/promoter tests, document links, and `git diff --check` all passed.

## backend-checks

Not applicable (`kind: knowledge`; no backend/IaC lane).

## reconcile

Not applicable (`kind: knowledge`; no UI/token lane).

## other

- Parent bundle verify: PASS, bundle `dd262a5c...`, `claim_status=provisional`.
- Parent strict report: PASS, 15,200 results, 30,400 canonical from 30,441 attempts, 41 retries.
- Parent privacy scan: PASS, zero secret hits.
- Proposal semantic gate: initial Claude 4.8 PASS; initial GPT-5.6 Sol REVISE; repaired P0 re-judgement pending after deterministic PASS.

### Phase 3 implementation matrix

- `test-analyze-completed-run-failures.py`: PASS.
- `test-run-env-static.py`: PASS.
- `test-report-run-quality.py`: PASS.
- `test-privacy-scan.py`: PASS.
- `test-lock-completed-run.py`: PASS, 26 tests.
- Real parent strict report: PASS, zero missing/extra/competing canonical judge keys.
- Real bundle verification: PASS.
- Full privacy scan: PASS, 21,130 files/archive members, zero secret hits.
- Shell syntax and Python compilation: PASS.
- Documentation links: PASS, 119 files / 174 links.
- `git diff --check`: PASS.
- VS Code diagnostics: zero errors in touched Python files.
- Anti-scaffold diff scan: zero findings.

### Phase 3 revise loop 1

- GPT-5.6 Sol found same-cardinality explicit judge substitution could override modern `run.meta.judge_identities`; verdict REVISE.
- Reporter now treats metadata identities as authoritative and emits `judge-domain-conflict` when explicit identities differ.
- Promoter metadata validation now rejects requested identities that differ from authoritative metadata.
- Added matching and same-count substitution negatives for reporter and promoter.
- `test-report-run-quality.py`: PASS after repair.
- `test-lock-completed-run.py`: PASS, 27 tests after repair.
- Full `gates/checks.sh`, Architrave run validation, real strict parent report, bundle verify, privacy, and diagnostics: PASS after repair.

### Phase 3 revise loop 2

- Added strict shared modern judge metadata parser; only field absence is legacy.
- Added malformed/null/empty/duplicate/cardinality attacks for reporter/promoter and future producer-shape assertions.
- Bound real authoritative-domain engagement and substitution rejection into P4/P5.
- `gates/checks.sh`: PASS; promoter tests: 28.
- Architrave validation, real explicit-legacy parent report, bundle verify, privacy 21,130/0, diagnostics, and lesson-count audit: PASS after bookkeeping repair.

### Phase 3 semantic loop 3 — stopped

- Claude Opus 4.8: PASS.
- GPT-5.6 Sol: REVISE on lenient/unstructured `judges` count coercion.
- Deterministic gates before review were green, but the semantic gate is not PASS.
- Per the three-loop stopping condition, Phase 3 is blocked and no further repair was attempted without human approval.

### Human-approved bounded loop 4

- Shared strict positive-integer `metadata_judge_count` implemented; no `int(...)` trust-boundary coercion.
- Reporter/promoter tests cover valid positive integer and invalid fractional, numeric string, arbitrary string, object, list, boolean, zero, negative, null, and missing values.
- Focused reporter/promoter suites: PASS; promoter tests: 29.
- Full `gates/checks.sh`: PASS.
- Architrave run validation, diagnostics, `git diff --check`, phase-state audit, and anti-scaffold scan: PASS.
- Post-repair real parent strict report: PASS, 15,200 results / 30,400 canonical from 30,441 attempts / 41 retries / zero strict failures.
- Post-repair bundle verification: PASS.
- Post-repair privacy scan: PASS, 21,130 files/archive members / zero secret hits.
- GPT-5.6 Sol final human-approved review: PASS.
- Claude Opus 4.8 final human-approved review: code PASS, formal REVISE only on stale pending bookkeeping; confirmation pending after synchronization.
