# Intake

## Understanding

Build and execute an autonomous, phase-gated recovery program for ApprenticeOps. Preserve the completed 152-model source run and frozen paper claims; determine whether wall-clock timeout policy caused recoverable failures; stage and, after launch-readiness gates, run a separate 21-model timeout-sensitivity condition; then make an evidence-backed policy decision.

## Acceptance Criteria

1. Keep all 15,200 original inference rows immutable and primary.
2. Preserve exactly 30,400 canonical judgements and 41 failed retry attempts.
3. Track P0-P7 in one Architrave ledger with at most one active phase.
4. Record deterministic evidence and independent GPT-5.6-family plus Claude-4.8 verdicts for each implementation gate.
5. Reject wrong scenario, roster, model artifact, runtime, timeout-policy, judge-domain, resume, or output identity.
6. Prove production preflight on the real AI node emits zero rows and zero output files.
7. Run the sensitivity condition as 21 models x 20 scenarios x 5 original seeds = 2,100 rows, separate from the parent run.
8. Apply the pre-specified paired, two-way cluster-bootstrap analysis and Adopt/Hold/Reject thresholds in `docs/sdd/timeout-recovery-sensitivity.md`.
9. Do not push, publish, reserve a DOI, or replace frozen public claims without a separate explicit maintainer action.

## Grounding Sources

- `architrave.config.json`
- `docs/sdd/timeout-recovery-sensitivity.md`
- `docs/sdd/completed-run-promotion.md`
- `data/completed-runs/full-chatok-core20-r5-ollama-20260705-150053-dd262a5c94593cb4b35bbb3554cc7ed1d608fab8b16160a3215329637c614baa/`
- `scripts/analyze-completed-run-failures.py`
- `run.py` and `scripts/run-{e2e,from-homelab,roster}.sh`
- `scripts/report-run-quality.py`, `scripts/privacy-scan.py`, and focused tests
- `knowledge/yagni.md`, `knowledge/learning-loop.md`, and `gates/rubric.md`
- authoritative read-only runtime evidence through `dragos@home.hont.ro`

## Assumptions

- The source run's Ollama CPU condition is the recovery parent; llama.cpp is a different runtime study.
- The 21-model cohort is post-selected by any parent DNF; conclusions are cohort-specific.
- A long run may proceed autonomously only after P4 passes from a clean committed source identity. Commit/push remain maintainer boundaries unless separately authorized.
- GPT-5.6 is represented by the available GPT-5.6 Sol family variant because the bare `gpt-5.6` identifier is not exposed by the current tools.

## Blocking Questions

None for P0-P3. P4 must resolve real-node digest namespace coherence and capture a production-wrapper zero-row preflight. P5 requires P4 completion; no immediate launch is authorized by bootstrap alone.

## Paper Reliability Disclosure Amendment (2026-07-13)

**Understanding:** Add the locked parent run's reliability issues to both paper
owners without changing frozen results or interpreting the ongoing sensitivity
condition.

**Acceptance criteria:** Record the exact 15,200-row accounting (204 timeout
DNF, four missing terminal frames, 1,452 token-limit endings, and 30,441 judge
attempts reconciled to 30,400 canonical successes plus 41 retries); preserve the
four mechanisms as separate categories; disclose partial-output retention,
judge provenance, provisional status, and cohort post-selection; synchronize
the design plan, submission manuscript, and readiness control; keep Section 8,
the abstract, results, and conclusion unchanged.

**Grounding:** `docs/PAPER.md`, `docs/analysis/paper.qmd`,
`docs/PAPER_PHASES.md`, the locked bundle report/manifest, this run's SDD and
phase ledger, and the consolidation source hierarchy.

**Assumptions:** Reliability accounting may appear in limitations while
analytical outcomes remain excluded pending a new analysis lock. No blocking
questions.
