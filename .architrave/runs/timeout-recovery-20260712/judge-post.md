# Judge Gate 2

## Verdict

Phase 3 implementation gate in progress.

- Claude Opus 4.8 first pass: PASS, no blocker; future P4 wiring nits only.
- GPT-5.6 Sol first pass: REVISE, one blocker: explicit same-count judge identities could override authoritative modern `run.meta.judge_identities`.

## Findings

Revise loop 1 repair:

1. Metadata judge identities are authoritative when present.
2. Explicit judges are accepted only for legacy metadata or exact equality.
3. Reporter emits a strict `judge-domain-conflict`; promoter fails P2 before normalization.
4. Same-count substitution tests added in both surfaces.
5. Full deterministic and real-evidence matrix re-run PASS.

Re-judgement pending.

Revise loop 2 findings and repair:

1. GPT-5.6 Sol found present-but-malformed `judge_identities` could fall into legacy behavior; Claude noted real parent evidence intentionally exercises the legacy path because the field is absent.
2. Added shared `analysis_metrics.metadata_judge_identities`: only field absence is legacy; present metadata must be a non-empty list of unique non-empty backend/model objects with cardinality equal to `judges`.
3. Reporter emits strict `judge-metadata-invalid`; promoter fails P2.
4. Added null, scalar, empty, malformed-entry, duplicate, and cardinality negatives in both consumers.
5. Asserted future producer writes the exact modern shape; bound real modern-path and same-count substitution proof into P4/P5.
6. Reconciled candidate lesson count and clarified the historical parent legacy path.
7. Full configured tests PASS; promoter suite now 28; real parent explicit-legacy report, bundle, privacy, Architrave run, and diagnostics PASS.

Final re-judgement pending (loop 3 maximum).

Final loop-3 results:

- Claude Opus 4.8: PASS. It found no blocker and treated producer execution proof as the future P4 gate.
- GPT-5.6 Sol: REVISE. `metadata_judge_identities` and existing consumers use `int(...)` coercion for `run.meta.judges`; values such as `2.5` may be accepted as `2`, while other malformed scalar values may escape the required structured `judge-metadata-invalid` / P2 path.

## Final Phase 3 Gate Status

**BLOCKED — semantic loop cap reached.** Architrave permits at most three revise loops. No fourth implementation repair or re-judgement has started. To reopen Phase 3, a human must approve one additional bounded repair:

1. Add one shared positive-integer count validator that accepts only `int` values greater than zero and rejects booleans, floats, strings, objects, lists, null, and missing counts for modern metadata.
2. Use its validated count in reporter expected-row arithmetic and promoter metadata validation, mapping failures to `judge-metadata-invalid` / P2.
3. Add reporter/promoter tests for valid integer and invalid fractional, numeric-string, arbitrary-string, object/list, boolean, zero, negative, null, and missing `judges` values.
4. Re-run all deterministic and real-evidence gates, then one explicitly human-approved dual-family review.

## Human-Approved Bounded Loop 4

Approval received. Repair scope remained limited to the recorded blocker:

1. Added shared `metadata_judge_count`, accepting only positive Python integers and rejecting booleans, floats, strings, objects, lists, null, zero, negatives, and missing values.
2. Reporter uses the validated count for expected judgement arithmetic and emits structured `judge-count-invalid` instead of coercing or crashing.
3. Promoter maps count failures to structured P2.
4. Added reporter/promoter table-driven invalid-count tests plus valid integer checks.
5. Focused tests PASS; promoter suite now 29.
6. Full `gates/checks.sh`, Architrave validation, diagnostics, diff, phase-state, and anti-scaffold gates PASS.
7. Post-repair real parent strict report PASS: 15,200 rows, 30,400 canonical judgements from 30,441 attempts, 41 retries, zero strict failures.
8. Post-repair bundle verification PASS and privacy PASS: 21,130 files/archive members, zero secret hits.

Final human-approved dual-family results:

- GPT-5.6 Sol: PASS, no blocker; Phase 3 can close after verdict persistence.
- Claude Opus 4.8: implementation PASS with zero code blockers; formal REVISE only because this file had not yet recorded the completed real-parent gate and GPT verdict. No code change requested.

Bookkeeping-only Claude confirmation: PASS. B1/B2 resolved; dual-family gate complete. Phase 3 closed.
