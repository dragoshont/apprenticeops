# Tournament of Options

## Option A — One-Off Report

Fastest, but repeats discovery work and loses query/source history. Rejected for
poor durability.

## Option B — Append To Canonical Catalog

Reuses an existing file, but mixes unreviewed candidates with citation-ready
evidence and bloats the paper source of truth. Rejected.

## Option C — Structured Radar

On-demand skill, append-only JSONL ledgers, dated reports, formal schemas, and a
small stdlib validator. Low blast radius, reproducible, and canon-safe. Selected.

## Option D — Automated Crawler / Database

Could automate discovery, but introduces APIs, rate limits, deduplication state,
and maintenance before repeated use proves the need. Deferred.

## Decision Matrix

| Option | Durability | Canon safety | Verification | Maintenance | Decision |
|---|---|---|---|---|---|
| A | low | high | low | low | reject |
| B | medium | low | medium | medium | reject |
| C | high | high | high | low | select |
| D | high | high | high | high | defer |

## Winner

Option C. JSONL is append-only, diffable, and stdlib-readable. The radar lives
beside the canonical literature catalog but remains candidate evidence. External
discovery tools may assist search, but none enforces ApprenticeOps-specific claim
lineage, social-source demotion, or promotion boundaries.
