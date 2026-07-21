# Architrave Repo Lessons

Candidate lessons learned while implementing in this repo. Keep this file short.
Each entry needs evidence and validation before promotion. Do not store secrets.
Promote repeated, stable lessons into `architrave.config.json`, `AGENTS.md`, `.github/instructions/`, or docs after review.

## Candidate Lessons

| Lesson | Evidence | Occurrences | Validated | Proposed Target | Status |
|---|---|---:|---|---|---|
| Retry history is not duplicate canonical evidence: require exactly one successful judgement per declared result/judge key and preserve failed attempts separately. | Parent run: 30,441 attempts -> 30,400 canonical + 41 parse retries; promoter/report tests. | 1 | yes, current branch | `AGENTS.md` or analysis docs after recurrence | candidate |
| Artifact locks on a disk-constrained node need pull-then-digest-verify, not an impossible all-model pre-pull and not mutable tag trust. | 21 affected artifacts >=88.7 GiB vs ~59 GiB free; run-environment negative tests. | 1 | yes, current branch | `AGENTS.md` after recurrence | candidate |
| Recovery governance must be written before launch; otherwise technical implementation can outrun the estimand and policy decision. | GPT-5.6 Sol proposal REVISE on empty Architrave templates and absent P6/P7 contract. | 1 | yes | `AGENTS.md` after recurrence | candidate |
| Present-but-malformed provenance metadata must fail closed; only field absence may enter an explicitly documented legacy compatibility path. | Phase 3 GPT-5.6 Sol judge-domain reviews; strict parser and malformed-domain tests. | 1 | yes | `AGENTS.md` after recurrence | candidate |
| A no-push long-running job needs mode authority and persistence readiness across every restart, not merely a launch-time flag. | Phase 5 dual-family REVISE; command-level no-Git restart/readiness/receipt tests and promoter integration. | 1 | yes, current branch | `AGENTS.md` after recurrence | candidate |
| A promotion packet must repeat exact immutable source-version IDs in every decision-bearing disposition; shorthand such as "the sources above" breaks independent traceability even when the analysis is correct. | Paper-impact GPT review REVISE; repaired 33-version trace and dual-family PASS. | 1 | yes, current branch | Research-radar protocol after recurrence | candidate |

