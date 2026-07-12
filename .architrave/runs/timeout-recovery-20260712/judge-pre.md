# Judge Gate 1

## Verdict

- Claude Opus 4.8: PASS on initial proposal, with P4 digest-source coherence and explicit timeout-policy launch binding as pre-launch checks.
- GPT-5.4 fallback/advisory: REVISE; P0-P3 supportable, P4 requires a real zero-row preflight and artifact identity proof. This is not a required-family closure.
- GPT-5.6 Sol: REVISE on first pass. Blockers: empty Architrave templates, competing/ambiguous ledger, unrecorded deterministic gates, P6/P7 statistical and decision contracts absent, and P3 silently appearing active before P0.
- Bare `gpt-5.6` CLI/model IDs were unavailable; VS Code exposed named GPT-5.6 family variants. GPT-5.6 Sol is the required GPT-family judge for this run.

## Findings

Repairs applied in P0:

1. Added `docs/sdd/timeout-recovery-sensitivity.md` with causal model, treatment rationale, two-way cluster bootstrap, and frozen Adopt/Hold/Reject thresholds.
2. Populated intake, tournament, plan, P0-P7 ledger, profile, and lessons.
3. Closed historical promotion SDD Phase 6 and established one active ledger.
4. Configured real syntax/test commands in `architrave.config.json`.
5. Kept P3 `not-started` until repaired P0 validators and both required proposal judges pass.

Re-judgement results:

- GPT-5.6 Sol: PASS, zero blockers/concerns; authorized P0 close and P3 start after verdict persistence.
- Claude Opus 4.8: PASS, zero blockers; minor reminder that the existing P3 diff must pass its own gate and must not be grandfathered.

Proposal semantic gate: PASS (both required families).
