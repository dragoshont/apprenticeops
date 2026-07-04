# Cold Audit Implementation Phases

Status: active phase ledger, created 2026-07-03. This file tracks the autonomous
implementation of `docs/COLD_AUDIT_RESPONSE_PLAN.md`.

## Phase Ledger

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 1 | Model-lock foundation | completed | Add model schema, generated lockfile, builder, validator. | `python3 scripts/build-model-lock.py`; `python3 scripts/validate-model-lock.py` | Lock represents all 173 roster tags; 18 >5B rows excluded; current thesis-track count is 155, so the 150+ <=5B count target is met. |
| 2 | Canonical thesis wording | completed | README update plan and public-facing docs boundary repair. | Search gate shows remaining `5 GB` / `8B` references are explicitly legacy snapshot or footprint context. | Public-facing docs now state the doctoral target as <=5B parameters and keep legacy 94-model footprint-bounded results scoped. |
| 3 | Protocol spine | completed | `docs/PROTOCOL.md` and control-doc sync. | Protocol defines eligibility, tiers, variants, run settings, judging, missing-run policy. | Completed in `docs/PROTOCOL.md`; it explicitly marks the current <=5B lockfile as 155 candidates and keeps provenance gaps open. |
| 4 | Privacy and egress gate | completed | `docs/PRIVACY_AND_EGRESS.md`, `scripts/privacy-scan.py`. | Secret patterns block; intentional public infra terms are reported. | Completed; scan distinguishes local inference from judge egress and reports disclosure classes without treating them as automatic failures. |
| 5 | Artifact inventory/audit | completed | `docs/ARTIFACT_INVENTORY.md`, `scripts/audit-paper-data.py`. | One command validates snapshots/site/model/scenario/run-artifact contracts. | Completed; committed v1 run now includes `run.meta` and passes strict reporting. |
| 6 | Hardware, judge, statistics specs | completed | `docs/HARDWARE.md`, `docs/JUDGE_VALIDATION.md`, `docs/STATISTICS.md`, `data/hardware-profile.home-ai.json`. | Docs make measured-vs-target hardware and judge/human status explicit. | Completed; human-vs-judge validation remains explicitly open. |
| 7 | Final consolidation | completed | Status docs, final search checks, final gates, commit/push. | All validators pass and P0 public claims are reconciled. | Completed for this remediation pass; the repo is more defensible, but the doctoral artifact is not yet complete until the open gaps below are resolved. |

## Phase 1 Finding

The first generated `data/models.lock.jsonl` included only 140 models in the
`thesis_5b_candidate` track. Phase 8 added verified <=5B candidates, bringing the
lock to 173 total rows with 155 included thesis-track models. The remaining 18
rows exceed 5B parameters and are excluded with
`exclusion_reason="above_5b_parameters"`.

This means the repository now satisfies the **count** side of the intended 150+
model, <=5B-parameter thesis universe. The next model-universe task is metadata
quality: verify licenses, source URLs, Ollama digests, and GGUF hashes.

## Adversarial Review Notes

- Do not infer licenses or digests. Source URLs may be mechanically derived from
  the pull tag/repository path, but license and digest/hash fields stay `unknown`
  until verified.
- Do not delete legacy 7B/8B rows from historical evidence. Mark them out of the
  thesis track while preserving snapshot reproducibility.
- Do not rewrite README claims before the canonical replacement language and
  validator exist.

## Remaining Open Gaps After This Pass

1. Model `source_url` is now populated for included rows and audited. Model
  `license`, `ollama_digest`, and `gguf_sha256` still require verification before
  serious review.
2. Human-vs-judge validation remains open, but a committed 45-item blind packet
  now exists for the v1 dev run.
3. Privacy scan reports intentional disclosure classes; a human must decide which
  hostnames/domains/IPs stay public in a thesis package.
4. `env.harness_dirty` has been split for future rows into source and artifact
  dirtiness. Existing rows keep their historical aggregate value.

## Phase 8 Finding

The current lockfile gate now reports:

```text
rows=173 included_thesis_5b=155 excluded=18 above_5b_excluded=18
tiers={'T1': 30, 'T2': 41, 'T3': 39, 'T4': 30, 'T5': 15}
target_150_status=met
```

The added rows are verified as existing Ollama/Hugging Face tags, but several
licenses remain `unknown` or coarse (`other`) until source cards are reviewed in
detail.