# SDD-01 — Run self-heal: zero-output stalls + empty judge verdicts

Date: 2026-06-29
Status: spec / phase 1 in progress
Owner: dragoshont

## User-visible outcome
After this, **a completed run has no silently-empty cells**: a model that stalls
to zero output is auto-retried before being recorded DNF, and a judge that returns
an empty verdict is auto-re-judged — so `report-run-quality.py` shows DNF only for
genuine model failure and `empty=0` for the judge, with no manual patch needed.

## Trigger / evidence
m1 (`batch-strategy-pilot-2 × strategy-pilot-6 × none × evaluator_optimizer_1`):
60/60 rows, 120/120 judged, 0 parse/dup/field errors, but **3 DNF (5%) all
qwen3:4b on the single scenario `new-backup-restore-drill` (reps 0/3/4)** and
**6 empty judge verdicts (granite4:micro)**. Both are recoverable gaps, not lost data.

## Root cause
1. **Zero-output stall.** `new-backup-restore-drill` is hard (timeout 150s, 700
   tok). On a 4B CPU model, prefill of the long prompt can exceed `DEFAULT_STALL_S=60`
   before the first token, so the stall guard fires → `DNF:stall` with empty
   `gen_ai.completion`. The `ceops-v2-zero-stall-retry` policy retries once, but a
   scenario that reliably exceeds first-token budget re-stalls. Not flaky — budget.
2. **Empty judge verdict.** The judge (Copilot CLI) occasionally returns an empty
   completion; nothing re-issues it, so the verdict cell is blank.

## Decision
- **Zero-output retry by phase.** When `stall.phase=prefill` (no first token), retry
  with a first-token budget scaled to prompt size, not the flat 60s. Cap retries; if
  still zero, record honest DNF. (Don't widen the global stall — keep decode stalls fast.)
- **Judge empty-retry.** Re-issue any empty verdict ≤2× before recording empty;
  preserves row-idempotency (only empties are redone).
- **Self-heal pass.** A `report --heal` re-infers only DNF-zero rows + re-judges only
  empties for a finished run, lock-aware, never double-booking the ai node.

## Rejected alternatives
- Widen global stall 60→150s: makes real decode hangs cost 2.5× — rejected.
- Drop hard scenarios for ≤4B: hides the capability signal we're measuring — rejected.
- Manual re-run each time: not durable; re-litigated every run — rejected (this SDD).

## Phases
1. **Heal m1 now (validation).** Re-infer 3 qwen3:4b reps + re-judge 6 empties on the
   idle node; prove report → DNF 0, empty 0. ← current
2. Prefill-aware retry in `run.py` (first-token budget ∝ prompt tokens).
3. Judge empty-retry in the judge path.
4. `report-run-quality.py --heal` to automate phase 1 for any run.

## Acceptance (falsifiable)
- m1 re-report: `DNF ≤ baseline`, `judge empty=0`, rows 60/60, judged 120/120, committed.
- node never double-booked (lock honored); reproducible (manifest match, reset stamped).
