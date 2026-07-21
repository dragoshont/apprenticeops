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
- Final production preflight `timeout-sensitivity-preflight6-20260712` ran through the intended topology (`home` control to `home-ai`) from clean snapshot `e35ef3f25a1c089eb2de482a1057ba5784547948`.
- The AI node matched Ollama 0.30.8 and the locked CPU/RAPL protocol, calibration completed, and preflight returned PASS.
- The preflight emitted zero result rows and zero output files, launched no inference or judge consumer, and restored the original power/radio state.
- `run.meta` schema v2 recorded the exact authoritative judge domain `copilot:claude-opus-4.8` plus `copilot:gpt-5.6-sol`; a same-cardinality substitution was rejected with `judge-domain-conflict`.
- Ollama exposed two installed models, neither in the 21-model recovery lock; there was no installed affected-model digest mismatch. Missing affected models remain subject to pull-then-exact-digest verification before inference.
- Parent bundle `dd262a5c...` has a second independently verified 434 MB copy at `/home/dragos/apprenticeops-evidence/`; the original 2.0 GB operational run and synchronized experiment branch remain intact.
- Dedicated treatment source branch `experiment/timeout-sensitivity-source-v1-20260713` points to clean commit `e35ef3f25a1c089eb2de482a1057ba5784547948`.
- A non-treatment six-call smoke completed 6 inference rows and 12 parent-judge rows, persisted to synchronized branch commit `18a5d0a...`, promoted to verified provisional bundle `f683a54e...`, and passed privacy with zero hits.
- Treatment run `timeout-sensitivity-v1-20260713` launched on `home-ai` from exact source `e35ef3f...`. Preflight passed, `qwen3:8b` was pulled and digest-verified, and 2/2,100 rows were complete at launch verification. Producer and consumer were both alive; parent judges were streaming.
- Later health snapshot: 375 inference rows, three completed models, 54 GB free, CPU/power lock intact, one committed model, and synchronized result branch. Judging was stalled at 200 rows because Granite lacked explicit sampler parameters.
- Narrow live repair `bbcc8d9` applies the same deterministic runtime-default sampler normalization used by promotion before judge condition hashing. Producer remained alive; repaired consumer resumed without duplicate Qwen rows and produced 113 Granite judgements by verification.
- Latest verified health snapshot: 380/2,100 inference rows, 346/4,200 judge rows (`qwen3:8b` 200, `granite3.3:8b` 146), three producer-completed models, one committed/pushed model, zero pending pushes, producer and consumer active, and 54 GB AI disk free.
- Judge integrity incident: paused at 1,790 attempts / 832 unique keys / 958 extras. Full raw journal retained in incident archive; canonical recovery reset to unaffected Qwen 200-row baseline. Fixed resume identity verified against real Granite evidence.
- Post-recovery health: 473 inference rows; canonical judged journal 209 rows / 209 unique / zero duplicates (`qwen3:8b` 200, Granite 9 and advancing); producer and repaired consumer active.
- Mission Control `0.6.1` is healthy and `/api/status` returns HTTP 200 for the active run. It now observes `/home/dragos/apprenticeops-timeout-treatment-v1-20260713` and AI repo `/home/dragos/apprenticeops-timeout-sensitivity-v1-20260713`; status SSH timeouts return structured error state instead of uncaught 500.

## Mismatches

- Historical parent `run.meta` has no `judge_identities` and intentionally remains on the explicit legacy judge-domain path; the recovery preflight independently proves the modern authoritative path.
- The maintainer worktree remains dirty and is not used for P5. Treatment runs from the clean dedicated source branch/checkpoint through `local-commit` and persists only to its dedicated result branch.
- No affected recovery model was installed during preflight, so real post-pull digest comparison is deferred to the mandatory per-model Phase 5 gate rather than inferred from unrelated installed models.

## Human Approval Items

- User authorized dedicated experiment branches. Source, smoke, and treatment result branches are isolated from `main`; no merge or public-claim change is authorized.
- Any public paper claim replacement, DOI/publication, or release remains explicit human approval.
- Preflight temporarily applied the already-defined node power lock and restored it; no inference, model pull, judge execution, public mutation, or claim mutation occurred.
