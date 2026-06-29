# SDD-01 — Run self-heal: zero-output stalls + empty judge verdicts

Date: 2026-06-29
Status: spec / phase 1 in progress
Owner: dragoshont

## User-visible outcome
After this, **a completed run has no silently-empty cells**: a model that stalls
to zero output is auto-retried before being recorded DNF, and a judge that returns
an empty verdict is auto-re-judged — so `report-run-quality.py` shows DNF only for
genuine model failure and `empty=0` for the judge, with no manual patch needed.

## Trigger / evidence (corrected after audit)
m1 (`batch-strategy-pilot-2 × strategy-pilot-6 × none × evaluator_optimizer_1`):
60/60 rows, 120/120 judged, 0 parse/dup/field errors. **One real gap, not two:**
- **3 DNF (5%) — qwen3:4b zero-output on the single scenario `new-backup-restore-drill`
  (reps 0/3/4).**
- The **"6 empty judge verdicts" are NOT a separate problem** — they are those same
  3 DNF × 2 judges. `report` counts `verdict=="empty"` (line 141); for a DNF the
  judge *correctly* records `score=1, verdict="empty"` (no answer to grade). The
  first analysis (and the assistant's confirmation) double-counted; verified by a
  heal that found **0 `score=None` rows**.

## Root cause
1. **Zero-output stall (the real gap).** The socket read timeout passed to `/api/chat`
   **is** `stall_s`. `resolve_policy` gives qwen3:4b `stall_s≈75s` (60×1.25). On a hard
   scenario (`new-backup-restore-drill`), prefill of the long prompt on a 4B CPU model
   exceeds 75s **before the first token**, so the socket times out → `DNF:stall` — the
   scenario's own ~234s `timeout_s` never applies (no byte arrived to enter the in-loop
   wall-clock check). `with_zero_output_retry` re-runs with the **same** 75s budget, so
   a reliably-slow-prefill case re-stalls (3/5). Not flaky — the prefill budget is too
   short for hard×slow.
2. **Empty judge text (a *separate*, latent bug — not what m1 hit).** `judge_one`
   swallowed an empty backend completion into a `score=None` verdict on the first try
   (the 4-attempt loop only caught exceptions), and resume treated it as done.

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
1. **Audit + judge hardening (DONE).** Confirmed counts; corrected the 6-empty
   miscount; shipped the empty-judge-text fix (`judge.py`, `ea496a4`): empty backend
   text now raises `EmptyJudgeResponse` (retried 4×, left unwritten if still empty) and
   resume re-judges `score=None` rows. This hardens a real latent path; it does **not**
   change m1 (whose 6 empties are correct DNF records).
2. **Prefill budget (the real m1 fix).** Give the **first byte** its own budget,
   separate from the decode stall: socket timeout = a prefill window ∝ prompt size
   (≈ `timeout_s`), and `with_zero_output_retry` **escalates** the first-byte budget per
   attempt (75 → 150 → `timeout_s`). Decode-stall stays `stall_s`. Then re-infer
   `new-backup-restore-drill`×qwen3:4b reps 0/3/4.
3. `report-run-quality.py --heal` to automate (drop `verdict==empty` only when the
   underlying answer is non-empty; re-infer DNF-zero; re-judge).

## Acceptance (falsifiable)
- m1 after re-infer: `DNF < 3` (ideally 0) on `new-backup-restore-drill`; the matching
  `verdict==empty` count drops with it; rows 60/60, judged 120/120, 0 dup, committed.
- node never double-booked (lock honored); reproducible (manifest match, reset stamped).
