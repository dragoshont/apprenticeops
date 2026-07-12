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
