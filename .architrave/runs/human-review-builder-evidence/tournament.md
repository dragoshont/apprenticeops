# Tournament

## Decision Matrix

| Option | Pros/cons | Risk | Durability | Verification | Result |
|---|---|---|---|---|---|
| Old Markdown/CSV | Reuse; cumbersome, clipped, exposed/enriched | Low code impact | Does not fix cause | Existing tests | Reject |
| Stdlib local form | Native radios and safe resumable persistence; bounded custom code | Local new files only | Full-text packet and atomic revision saves | Integrity/HTTP/storage/export tests | Winner |
| Hosted framework | More features; setup and network surface | Unnecessary stack | Maintenance burden | App/deployment tests | Reject |

YAGNI: reuse label meanings, scenario class and source hash contracts; native
browser controls, Python stdlib, then minimal local code. No scoring abstraction.

Refinement tournament: manual-only notes are smaller but fail the explicit
autosave request. Reuse the revisioned endpoint with a 700 ms typing debounce;
serialize it with manual navigation and keep later edits dirty until acknowledged.
This wins over a second store or dependency; no timer advances the item.

Durability correction: keeping human-authored data in .tmp with stronger warnings
does not remove the cleanup risk. Persistent `data/human-review-local/`, one narrow
ignore entry, byte-preserving legacy migration, and resume-only normal launch win.
No daemon, OS startup integration, dependency, or new preparation flag is needed.
