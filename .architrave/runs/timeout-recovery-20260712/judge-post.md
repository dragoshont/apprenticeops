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

## Phase 4 Launch-Readiness Gate

Deterministic and runtime evidence is complete.

- Clean detached source `e35ef3f25a1c089eb2de482a1057ba5784547948` reached both control and AI nodes exactly.
- Final real-node preflight PASS with zero result rows, zero output files, no consumer, no inference process, and restored node state.
- Recovery contract hashes and Ollama 0.30.8 environment matched.
- Modern `run.meta` recorded exactly `copilot:claude-opus-4.8` and `copilot:gpt-5.6-sol`; same-count substitution was rejected.
- Full configured deterministic gate PASS after the sync and sampler repairs.

Independent semantic results:

- Claude Opus 4.8: PASS. All nine Phase 4 criteria met; no blocker. It confirmed clean detached commit `e35ef3f25a1c089eb2de482a1057ba5784547948` is sufficient `local-commit` provenance without committing or pushing dirty `main`.
- GPT-5.6 Sol: PASS after bookkeeping confirmation. Its sole prior procedural blocker was resolved by persisting Claude's independent PASS; it found no contradictory phase state and explicitly authorized Phase 4 closure.

## Phase 5 No-Push Persistence Pre-Launch Gate

Initial dual-family verdict: REVISE; no inference launched.

Shared blocker: a direct consumer restart could default to `git-push` because the scheduler did not read authoritative `run.meta.persist_mode`. Additional findings covered producer-before-consumer ordering, receipt/archive durability and promotion verification, strict scenario/retry domains, lock behavior, and command-level coverage.

Repairs:

1. Scheduler loads and validates authoritative mode, judge identities, scenarios, repetitions, and expected model count from `run.meta`; conflicts fail before Git.
2. Mandatory `flock`, committed-receipt revalidation, atomic readiness, and consumer-first launch prevent inference without a viable persistence path.
3. Per-model receipts bind exact result rows, candidate archives, judge attempts, scenario domain, repetitions, and judge domain; all writes are atomic/fsynced and self-verified.
4. Promoter requires and revalidates exact local receipt/result/candidate inventories and includes receipts in source hashes.
5. Process tests prove no-Git restart, conflict/lock/tamper refusal, failed-consumer launch suppression, read-only unknown status, and retry liveness.
6. Full configured checks and Architrave run validation PASS. Final dual-family re-review pending.

Second re-review:

- Claude Opus 4.8: PASS, with minor fail-closed liveness notes.
- GPT-5.6 Sol: REVISE; launch denied on additional strict metadata, coordinated evidence, readiness, tuple, judge-journal, marker-domain, and path-boundary findings.

Second repair closes those findings with strict modern metadata/path parsing before Git, external receipt recomputation against current results/judgements/candidates, result-to-candidate semantic binding, strict integer repetitions, committed roster validation, post-readiness liveness, and crash-durable/recoverable judge JSONL. Full deterministic gates PASS; final dual-family re-review pending. No inference launched.

Final loop-3 results:

- Claude Opus 4.8: PASS. It found the prior blockers closed and authorized a fresh detached preflight contingent on the companion family PASS.
- GPT-5.6 Sol: REVISE. It found three remaining blocker classes: persistence-mode downgrade after missing metadata, coercive promoter metadata counts, and incomplete nested-path / late terminal-marker mediation.

**Phase 5 status: BLOCKED.** The configured three semantic loops are exhausted. No further repair or launch may begin without explicit human approval for a bounded additional loop. No inference or external mutation occurred.

## Human-Approved Phase 5 Loop 4

Approval received. Repair remained bounded to the final GPT findings:

1. Durable `.run-authority` prevents a local no-push run from downgrading to Git if `run.meta` disappears, including before its first receipt.
2. Promotion requires an explicit matching persistence mode and strictly typed modern counts, repetitions, overrides, and done units.
3. Scheduler and promoter mediate nested evidence/state/staging/lock/ledger paths and recheck late pause/cancel markers immediately before final lock.

All focused attacks pass; treatment contracts remain byte-identical and promoter provenance is refreshed. Final full deterministic gate and run validation PASS with 39 promoter tests and zero diagnostics.

Human-approved loop-4 semantic results:

- Claude Opus 4.8: PASS; authorized a fresh detached preflight contingent on companion PASS.
- GPT-5.6 Sol: REVISE. It found three remaining blockers: the authority marker can be bypassed if metadata changes to `git-push`; direct `validate`/`lock` commands do not independently enforce persistence-mode equality; staging-path mediation occurs after temporary evidence may be written.

**Phase 5 status: BLOCKED.** The explicitly approved additional loop is exhausted. No further repair, snapshot, preflight, or inference launch may begin without new human direction. No external mutation occurred.

## Paper Reliability Disclosure Gate

Proposal loop 1: both families returned REVISE on wording/scope details. The
repair removed unsupported active-generation causality, made canonical-key
completeness and differing judge provenance explicit, preserved Section 9
heading structure, and excluded the provisional accounting from Section 8.

Proposal loop 2: GPT-5.6 Sol PASS and Claude Opus 4.8 PASS for the exact
`docs/PAPER.md` text. After repository source hierarchy showed that
`docs/analysis/paper.qmd` owns submission prose, an adjacent proposal loop found
and repaired the contradiction between “no provisional value” and reporting
provisional reliability counts; stale “active/still-running” parent wording was
changed to historical “then-active.” Both families then PASS.

Post-implementation loop 1: Claude PASS; GPT REVISE solely because the
authoritative Open Gates table still labeled the completed parent “Active <=5B
run.” The repair split it into a completed 152-model parent gate (locked
provisional / analysis lock open) and an active 21-model follow-up gate (blocked
from paper claims).

Final post-implementation verdicts:

- GPT-5.6 Sol: **PASS**. The prior Major status contradiction is fully resolved;
	all accounting, provenance, claim-boundary, link, and deterministic criteria
	pass.
- Claude Opus 4.8: **PASS**. All three paper surfaces are synchronized; no
	causal, partial-run, or frozen-claim leakage remains.

Residual non-blocking findings are recorded, not hidden: the optional broad
paper-data orchestrator needs explicit legacy judge identities; cached
`wave_analysis.ipynb` output differs from fresh execution; and broader
consolidation/repo-profile prose contains stale historical wording outside this
bounded documentation slice. None changes the parent bundle, frozen results, or
the completed three-file amendment.

## Pre-Commit CEOps Promotion Review

The first split pre-commit review returned GPT REVISE and Claude PASS. Repairs
closed the stricter findings: reporter exact-domain validation, receipt binding
to full condition identity, safe run IDs, and removal of persisted staging
attestation as a same-UID trust anchor. Public validate/lock now rebuild staging
from source under the promotion lock and verify the final content-addressed
bundle. A second review found dead reporter attacks and metadata-downgrade /
malformed-done bypasses; dynamic test discovery and explicit schema-v2 markers
close them. A final GPT revise found persistence-mode omission, coordinated
duplicate receipt rows, and non-`PromotionError` finalization cleanup; all three
now have explicit fail-closed checks and regressions. Final tree-bound
dual-family verdict pending.
