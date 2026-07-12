# Runtime Observer

## Sources Used

- Read-only SSH to `dragos@home.hont.ro` and `home-ai.hont.ro`.
- Parent run status, strict report, row/marker counts, bundle gate report, and AI preflight logs.

## Observed State

- Parent run `full-chatok-core20-r5-ollama-20260705-150053` completed 152/152 models and 15,200/15,200 inference rows.
- `.committed` has 152 entries and `.push-pending` is empty.
- 30,441 judge attempts reconcile to 30,400 canonical successes plus 41 parse retries; no missing or competing successes.
- AI node was idle after the parent run. Earlier staged recovery preflight validated the dedicated scenario hash and locked CPU/RAPL/runtime state, but inherited dirty checkout provenance and therefore did not close P4.
- Recovery cohort artifacts total about 88.7 GiB; the node had about 59 GiB free. All-at-once pre-pull is impossible.

## Mismatches

- Real-node `/api/tags` digest namespace must be proven coherent with source-bundle artifact identities during P4.
- Historical parent `run.meta` has no `judge_identities` and therefore exercises the explicit legacy judge-domain path. P4/P5 must prove the modern authoritative producer shape and same-count substitution rejection on recovery evidence.
- Recovery contracts currently live under ignored `.tmp` and must be installed at tracked declared paths before P4.
- Current source tree is dirty and local `main` is ahead of `origin/main`; no P5 launch may use origin sync until source identity is reconciled.

## Human Approval Items

- Commit/push a clean source checkpoint if P4 is to close with origin-based provenance.
- Any public paper claim replacement, DOI/publication, or release remains explicit human approval.
- No runtime mutation was performed by this Architrave bootstrap phase.
