# Recommended Plan

## Summary

Preserve the original run as immutable failure-inclusive evidence. Close historical promotion and diagnosis phases from verified artifacts. Finish hardening and tracked contracts before proving launch readiness on the real AI node. Run a separate 21-model sensitivity condition, analyze it using rules frozen before launch, and record Adopt/Hold/Reject without changing public claims automatically.

## Implementation Sequence

1. P0: bootstrap Architrave, freeze this plan, causal model, analysis contract, decision thresholds, and one phase ledger.
2. P1: record historical evidence-lock completion from bundle `dd262a5c...`.
3. P2: record historical diagnosis completion: 204 timeout, four completion-frame DNF, 1,452 length, 21 affected models.
4. P3: finish and test shared judgement semantics, privacy handling, verified/atomic analyzer, manifest/artifact locks, exact resume identity, and disk-bounded artifact verification.
5. P4: install generated contracts at tracked paths, prove hash equivalence, obtain dual implementation PASS, use a clean source identity, and run production `PREFLIGHT_ONLY=1` on `home-ai` with zero rows/files.
6. P5: first preserve a second verified copy of the parent bundle, then launch one resumable 2,100-row sensitivity run from a clean dedicated experiment branch using the established Git-backed per-model persistence path. Prove that path on non-cohort toy models before launch; promote and privacy-scan only when exact.
7. P6: run the pre-specified paired two-way cluster bootstrap and secondary cost/quality analysis; lock outputs and obtain dual PASS.
8. P7: evaluate thresholds and record Adopt/Hold/Reject; retain current defaults unless every adoption criterion passes.

## Test Strategy

- Architrave config and run validation.
- Shell syntax and Python compilation.
- Focused analyzer, run-environment, report, privacy, and promoter suites.
- Real bundle verification, privacy scan, strict canonical report, and analyzer hash reconciliation.
- Adversarial negative tests for tamper, extra files/dirs/symlinks, wrong judge domain, missing/competing success, retry substitution, scenario/roster/artifact mismatch, stale resume, wrong runtime/policy, and llama.cpp file replacement.
- Real-node production preflight with explicit zero-row/zero-output assertion.
- Command-level branch/mode conflict, lock-contention, consumer-readiness,
  unknown-status, receipt-tamper, judge-retry liveness, dirty-index, failed-add,
  and real dedicated-branch commit/push lifecycle tests.
- Completed-run promotion integration requiring exact receipt, result-archive,
  and candidate-archive inventories for both Git-backed and local persistence.
- GPT-5.6 Sol and Claude Opus 4.8 independent proposal and implementation gates.

## Rollback / Recovery

- P0: remove additive Architrave artifacts and the recovery SDD.
- P1/P2: discard bundle or derived report; source run is untouched.
- P3/P4: revert hardening and tracked contracts; no sensitivity rows exist before P5.
- P5: stop and resume the same run ID on its isolated experiment branch; never merge sensitivity rows into the parent run or merge the experiment branch into main. Failed persistence blocks promotion.
- P6/P7: discard exploratory outputs or choose HOLD/REJECT; current timeout policy remains.

## Human Approval Needed

The user explicitly authorized a dedicated experiment branch and off-machine push for this sensitivity run. This does not authorize merging it into `main`, mutating the parent run, or changing public claims. Public claim changes, DOI/publication, and any replacement of the frozen paper source remain separate approval boundaries.

## Paper Reliability Disclosure Amendment

1. Put the complete mechanism/count accounting and post-selection threat in
	`docs/PAPER.md` Section 9.
2. Put a shorter, source-linked disclosure in the claim-bearing
	`docs/analysis/paper.qmd` limitations section.
3. Correct `docs/PAPER_PHASES.md` so the completed locked/provisional parent and
	active 21-model follow-up have separate gates.
4. Do not change the abstract, Section 8, results, conclusion, frozen 94-model
	claims, or any treatment outcome.
5. Require configured checks, links, claim audit, isolated HTML/PDF renders, and
	independent GPT- and Claude-family PASS.
