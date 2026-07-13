# Completed-Run Evidence Bundles

This directory contains immutable, content-addressed experiment bundles produced
by `scripts/lock-completed-run.py`.

Full bundle directories are archival payloads and are not committed to normal
Git history: completed runs can contain individual files above the GitHub 100 MiB
object limit. Each promoted bundle instead has a committed root-level
`<RUN_ID>-<BUNDLE_ID>.summary.json` containing its identity, exact counts,
verification hashes, retention status, and claim status. The complete bytes must
exist in at least two independently verified archival copies before the summary
is treated as durable.

A bundle appears only after exact result, judge, condition, roster, scenario, and
persistence gates pass. Live or partial runs remain under `data/runs/` and are
not analysis sources.

```text
<RUN_ID>-<BUNDLE_ID>/
  bundle-manifest.json
  gate-report.json
  normalization-metadata.json
  promotion-ledger.jsonl
  contract/
  raw/
    model-results/   # compressed per-model result archives, when present
    candidates/      # candidate trace archives, when present
    logs/            # operational logs, when present
  canonical/
```

Key rules:

- `analysis_schema_version` remains `1`.
- `source_kind` is `completed_run`.
- Initial `claim_status` is `provisional`.
- Raw judge attempts are preserved.
- Roster, scenarios, completion markers, compressed per-model results,
  candidate traces, and logs are hash-bound when present.
- Byte-duplicate uncompressed per-model result files and transient locks are
  intentionally excluded.
- Canonical judgements contain exactly one successful row per requested
  backend/model and answer.
- `canonical/judge-retries.jsonl.gz` preserves rejected attempts.
- Every evidence file listed in `source_sha256` must verify.
- Bundle paths are never overwritten. Byte-identical promotion is idempotent.
- A bundle does not replace `data/analysis-manifest.json` or public claims
  automatically.

Verify a bundle with:

```bash
python3 scripts/lock-completed-run.py verify \
  --bundle data/completed-runs/<RUN_ID>-<BUNDLE_ID>
```

The summary is an index, not a substitute bundle: `verify` still requires one of
the retained full payload copies.

The implementation decision and rollback contract are in
[`docs/sdd/completed-run-promotion.md`](../../docs/sdd/completed-run-promotion.md).
