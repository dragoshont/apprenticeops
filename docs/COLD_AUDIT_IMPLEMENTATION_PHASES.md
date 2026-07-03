# Cold Audit Implementation Phases

Status: active phase ledger, created 2026-07-03. This file tracks the autonomous
implementation of `docs/COLD_AUDIT_RESPONSE_PLAN.md`.

## Phase Ledger

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 1 | Model-lock foundation | completed | Add model schema, generated lockfile, builder, validator. | `python3 scripts/build-model-lock.py`; `python3 scripts/validate-model-lock.py` | Lock represents all 158 roster tags; 18 >5B rows excluded; current thesis-track count is 140, so 150+ <=5B target is not yet met. |
| 2 | Canonical thesis wording | completed | README update plan and public-facing docs boundary repair. | Search gate shows remaining `5 GB` / `8B` references are explicitly legacy snapshot or footprint context. | Public-facing docs now state the doctoral target as <=5B parameters and keep legacy 94-model footprint-bounded results scoped. |
| 3 | Protocol spine | not-started | `docs/PROTOCOL.md` and control-doc sync. | Protocol defines eligibility, tiers, variants, run settings, judging, missing-run policy. | pending |
| 4 | Privacy and egress gate | not-started | `docs/PRIVACY_AND_EGRESS.md`, `scripts/privacy-scan.py`. | Secret patterns block; intentional public infra terms are reported. | pending |
| 5 | Artifact inventory/audit | not-started | `docs/ARTIFACT_INVENTORY.md`, `scripts/audit-paper-data.py`. | One command validates snapshots/site/model/scenario/run-artifact contracts. | pending |
| 6 | Hardware, judge, statistics specs | not-started | `docs/HARDWARE.md`, `docs/JUDGE_VALIDATION.md`, `docs/STATISTICS.md`. | Docs make measured-vs-target hardware and judge/human status explicit. | pending |
| 7 | Final consolidation | not-started | Status docs, final search checks, final gates, commit/push. | All validators pass and P0 public claims are reconciled. | pending |

## Phase 1 Finding

The current `data/models.txt` roster has 158 tags, but the first generated
`data/models.lock.jsonl` includes only 140 models in the `thesis_5b_candidate`
track. The remaining 18 rows exceed 5B parameters and are excluded with
`exclusion_reason="above_5b_parameters"`.

This means the repository has a strong model roster but **does not yet satisfy**
the intended 150+ model, <=5B-parameter thesis universe. The next model-universe
task is not another run; it is replacing those over-5B legacy footprint rows with
verified <=5B open-weight candidates or lowering the claim until the roster is
filled.

## Adversarial Review Notes

- Do not infer licenses, source URLs, or digests. The generated lockfile records
  them as `unknown` until verified.
- Do not delete legacy 7B/8B rows from historical evidence. Mark them out of the
  thesis track while preserving snapshot reproducibility.
- Do not rewrite README claims before the canonical replacement language and
  validator exist.