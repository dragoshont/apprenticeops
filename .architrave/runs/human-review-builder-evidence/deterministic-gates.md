# Deterministic gates

Interpreter: original repo .venv/bin/python3, Python 3.14.7.
All candidate commands run inside the isolated worktree.

| Gate | Result |
|---|---|
| scripts/test-review-human-eval.py | PASS: 38 synthetic tests (packet, literal full text/self-identification/thought tags, privacy allowlist, applicability, unsure, storage/corruption/fsync/replace failure, initial setup retry, input bounds, CAS/thread/process locking, HTTP protections, partial exports, async note-autosave races/errors, persistent defaults and migration) |
| scripts/test-human-eval.py | PASS: existing 3 tests |
| node --check scripts/human-review.js | PASS |
| gates/checks.sh | FAIL: existing scripts/test-run-from-homelab.py:135 assertion |
| Same test in unchanged original checkout | Same FAIL at line 135; not caused by candidate files |
| Configured build | PASS |
| Configured tests before failure | recovery 10, failure analysis, persistence 17, scheduler, readiness PASS |
| Remaining configured tests run explicitly | judge-resume, judge-row-schema, run-env-static, report-quality 22, privacy, lock-completed-run 45, doc links PASS |
| Real packet prepare-only + verification | PASS: 10 items, 2 safety-scoped, 13,700 eligible cells / 137 <=5B deployments; zero reviewer sessions |
| Python compilation, JavaScript syntax, git diff --check | PASS |
| harness/validate-run.sh | PASS |

Initial focused test invocation accidentally used the root cwd and reported
new files missing; rerun in the isolated tree passed. No files were changed by that failure.

UI reconciliation not applicable to knowledge profile.

Operations UX refinement: native Node VM test PASS (existing Node only, no
dependency installed). It proves note-only autosave, no advancement, typing
preservation during an in-flight request, manual-save serialization/revision use,
save-error draft retention, and skipped-draft preservation. Browser/Edge acceptance
remains parent-owned. A test-only path comparison initially missed macOS /var →
/private/var resolution; corrected to compare resolved paths, then 31/31 passed.
No real pilot files or labels were modified during this refinement.

Persistent-storage correction: 7 added tests PASS. The migration preserves every
packet/progress byte and reviewer identity; active locks, corrupt state, existing
destinations and failed rename refuse. Repeated normal default launches never
invoke preparation. Fixture persistent-directory rejection and narrow ignore
coverage PASS. The original real pilot has not yet moved: parent applies the
ignore/source patch first, then normal launch performs the verified migration.
