# Tournament of Options

## Option A — Chat-Only Tracking

Keep status and decisions in conversation. Lowest initial cost, but loses phase truth across compaction, cannot be validated, and already allowed implementation to outrun governance. Durability: low. Verification burden: manual. Loses.

## Option B — Checklist In Existing Promotion SDD

Add a recovery checklist to the completed-run promotion SDD. Small diff, but conflates a closed evidence-lock boundary with a new multi-day experiment and produces competing phase ledgers. Durability: medium. Blast radius: low. Loses.

## Option C — Dedicated Architrave Run And Recovery SDD

Use Architrave's knowledge profile, durable run artifacts, and gates; keep one recovery SDD with P0-P7, pre-specified analysis, explicit wins, and operator boundaries. Reuses installed v0.10.3 assets and current repository scripts. Durability: high. Test burden: deterministic run validation plus dual semantic gates. Wins.

## Option D — Immediate Sensitivity Launch

Launch the 2,100-call run from the current dirty tree. Fastest to data, but provenance would record dirty source, contracts are still ignored under `.tmp`, P6/P7 rules could be chosen after outcomes, and model identity may drift. Blast radius: high. Loses.

## Option E — Defer Recovery

Keep the immutable source bundle and stop. Scientifically safe, but leaves a diagnosed timeout-policy question unresolved. Durability: safe but incomplete. Use only if launch-readiness cannot pass.

## Decision Matrix

| Option | Product / research truth | Simplicity | Reversibility | Integrity | Progress visibility | Verdict |
|---|---:|---:|---:|---:|---:|---|
| A. Chat only | 2/5 | 5/5 | 5/5 | 1/5 | 1/5 | Reject |
| B. Existing-SDD checklist | 3/5 | 4/5 | 5/5 | 2/5 | 2/5 | Reject |
| C. Architrave run + recovery SDD | 5/5 | 3/5 | 5/5 | 5/5 | 5/5 | **Winner** |
| D. Immediate launch | 2/5 | 4/5 | 2/5 | 1/5 | 2/5 | Reject |
| E. Defer | 2/5 | 5/5 | 5/5 | 5/5 | 3/5 | Fallback |

## Winner

Option C. It reaches the first YAGNI rung that satisfies current acceptance criteria: reuse repository source truth and installed Architrave capability, add only one recovery SDD and one run ledger, and keep the long run behind deterministic and semantic gates.

## Phase 5 Persistence Tournament

> **Superseded 2026-07-13.** This tournament assumed remote push was not
> authorized. The user later authorized only dedicated source, smoke, and
> `experiment/<RUN_ID>` result branches. The active decision is the existing
> Git-backed per-model path, with strict receipt/domain/index validation and no
> authority to push `main`, merge, mutate parent evidence, or change claims.

The source scheduler normally commits and pushes each completed model. That is incompatible with this run's explicit no-push boundary, so Phase 5 compared three bounded options before launch.

| Option | Pros | Cons / risk | Durability | Verification burden | Verdict |
|---|---|---|---|---|---|
| Keep `git-push` scheduler | Existing streaming/resume path | Violates no-push boundary and mutates shared checkout/remote | High off-node, policy-invalid | Existing tests | Reject |
| Infer all rows, judge/persist afterward | No scheduler change or push | Loses streaming recovery, increases tail time, weakens unattended resumability | Medium | End-of-run only | Reject |
| Explicit `local-files` job with receipts | Preserves streaming; no Git mutation; promotable, content-verified evidence | No off-node replication until bundle transfer; requires readiness/receipt gates | High locally, reversible | Command-level restart/readiness/tamper tests + promoter integration | **Winner** |

The abandoned local-files implementation was rejected repeatedly because restart
authority, readiness, and archive mediation remained more complex than the
established Git path. After explicit branch authorization, the simpler durable
path won: derive `experiment/<RUN_ID>`, validate the exact result/judge/candidate
domain, write and verify deterministic archives plus a receipt, require an empty
index, stage and commit only the six declared evidence paths, push that dedicated
branch, and refuse every other branch.

## Paper Reliability Disclosure Tournament

| Option | Pros | Cons / risk | Durability | Verification burden | Verdict |
|---|---|---|---|---|---|
| Footnote only | Smallest edit | Easy to miss; cannot explain distinct censoring mechanisms | Low | Link check | Reject |
| Update `docs/PAPER.md` only | Full design accounting | Leaves the claim-bearing Quarto manuscript and readiness status stale | Medium | Docs gate | Reject |
| Synchronize the three canonical paper owners | Exact limitation disclosure and truthful readiness state without touching results | Requires claim audit and two renders | High | Configured gate, claim audit, HTML/PDF, dual judges | **Winner** |
| Promote parent/follow-up findings into results | Richer headline | No new analysis lock; follow-up incomplete; claim leakage | Invalid | Full analysis lock | Reject |
| Defer | No manuscript churn | Withholds already-locked reliability evidence | Low | None | Reject |

The winner stops at the existing-source-of-truth YAGNI rung: reuse the paper
plan, submission manuscript, and readiness control; add no new document,
analysis, dependency, or claim.
