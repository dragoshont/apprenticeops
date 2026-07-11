# Artifact Inventory

Status: active reproducibility inventory, created 2026-07-03.

This file lists the committed artifacts that support the current paper-era
snapshot and the post-audit dev evidence. It does not claim that the final
doctoral <=5B-parameter roster is complete.

## Canonical Analysis v1

| Artifact | Purpose | Gate |
|---|---|---|
| `data/analysis.schema.json` | The one corrected and final derived-analysis contract (`schema_version=1`). | `status=corrected-final`; required/forbidden fields checked by `scripts/validate-analysis-schema.py`. |
| `data/analysis-manifest.json` | Locks raw result/judge archives, normalized snapshots, and frozen pair evidence by SHA-256; records `claim_status`. | Public claims require `claim_status=locked`; every source hash must match. |
| `data/raw/results.var.jsonl.gz` | First collection batch; controlled systems source. | Bound by manifest; 2,375 result rows, base-clock/Turbo-off, `package-0`. |
| `data/raw/results.wave2.jsonl.gz` | Second collection batch; quality/safety breadth only for claim-bearing analysis. | Bound by manifest; systems values are `descriptive_only`. |
| `data/raw/judged.var.{claude,gpt55}.jsonl.gz` / `judged.wave2.jsonl.gz` | Raw per-judge verdict rows for both variance batches. | Bound by manifest; backend/model identity and partial-family rows retained; `scripts/export-judge-pairs.py --check` reconstructs the locked complete pairs. |
| `data/snapshots/results_snapshot.csv` | Canonical inference snapshot with row-level batch, CPU-frequency, RAPL-source, and energy-scope provenance. | Exactly 9,025 rows, `runtime_adapter`, schema v1, exact raw lineage. |
| `data/snapshots/judged_snapshot.csv` | Two-judge quality consensus with batch/regime provenance. | Exactly 9,025 rows, schema v1. |
| `data/snapshots/judged_snapshot.det.csv` | Earlier deterministic/single-pass judged snapshot retained for comparison. | Exactly 475 rows, schema v1. |
| `data/site/summary.json` | Machine-readable locked headline and scope summary. | Breadth 94 / quality-safety front 2; controlled 24 / three-axis front 7; cross-batch energy disallowed. |
| `data/site/models.csv` / `models.json` | 94-model quality/safety breadth mirror. | Exactly 94 typed, mirrored rows; no energy field. |
| `data/site/controlled_models.csv` | 24-model controlled quality/safety/energy table. | One batch, CPU regime, and power source; exactly 24 rows. |
| `data/site/pareto.csv` | Controlled quality/safety/energy front. | Exactly 7 rows; `analysis_scope` is explicit. |
| `data/site/quality_safety_pareto.csv` | 94-model breadth quality/safety front. | Exactly 2 rows; no energy field. |
| `data/site/axis_*.csv` | Scenario-cluster quality/safety and controlled energy summaries. | Exact schema v1 fields; energy table declares controlled scope. |
| `data/site/judge_pairs.csv` | Retained raw two-judge pairs. | Exactly 8,909 rows, schema v1. |
| `data/snapshots/judge_pair_provenance.csv` | One-to-one frozen lineage for every retained pair: batch, CPU/power scope, evaluation policy, and backend/model identities. | Exactly 8,909 unique frozen keys; explicitly `condition_identity_incomplete=1`, so it cannot authorize cross-run reuse. |
| `scripts/lock-completed-run.py` | Promotes a fully persisted run into a provisional, content-addressed analysis-v1 evidence bundle. | Full-shape fixture suite; exact-domain, retry, sidecar, drift, and reconciliation gates; bundle verification; no partial override. |
| `data/completed-runs/<RUN_ID>-<BUNDLE_ID>/` | Future completed-run evidence bundles containing aggregate/canonical rows, contracts, compressed per-model results, candidate traces, and logs; none is created for a live run. | `source_kind=completed_run`, `claim_status=provisional`, all listed bytes SHA-256 verified, then privacy-scanned before analysis handoff. |
| `data/human_eval/paper-94-model-corrected-v1/` | Blind 50-item paper human-validation packet sourced from locked answers and complete `claude-opus-4.8` / `gpt-5.5` pairs. | `scripts/validate-human-eval.py`; human scores intentionally blank until independent scoring; `human_eval.py score-packet` refuses incomplete packets. |
| `data/croissant.json` / `data/DATA_RIGHTS.md` | Croissant 1.0 discovery/loading metadata and mixed-rights disclosure for the frozen 94-model dataset. | Deterministic generator; local validator; official `mlcroissant==1.0.22`; exact parity with all manifest sources and model-license URLs. |
| `scripts/build-release-package.py` / `scripts/audit-release-metadata.py` | Deterministic Zenodo-ready package and citation/rights/release audit. | Archive members match source bytes; normalized tar metadata; package SHA-256; Zenodo DOI remains an explicit operator gate. |
| `.python-version` / `requirements-lock.txt` / `data/tool-license-policy.json` | Exact Python 3.14.5 and universal hash-locked transitive analysis/release environment, with sourced tool-license policy. | `pip --require-hashes`; constrained semantic `uv` fixed-point check; installed-version and `pip check`; all 83 universal packages covered through active distribution metadata or exact-version marker policy; immutable license evidence for marker-gated packages and for uv, Pillow, and mlcroissant. |
| `scripts/compare-notebook-outputs.py` | Compares cached and fresh notebook text plus inline binary outputs while normalizing only checkout/interpreter paths and pip notices. | All inline PNG dimensions and decoded pixels checked with a strict anti-alias envelope; non-image binary payloads use exact SHA-256; regression proves scientific text/image changes fail. |

## Generated Publication Artifacts

| Artifact | Purpose | Gate |
|---|---|---|
| `docs/analysis/wave_analysis.ipynb` | Generates canonical site exports and the two valid fronts. | Executed in update mode; cached outputs compared to fresh execution in verify mode. |
| `docs/analysis/judge_comparison.ipynb` | Judge agreement analysis. | Complete committed pairs only; executed and output-compared. |
| `docs/analysis/reviewer.ipynb` | Editable reviewer queries with enforced breadth/controlled scopes. | Executed and output-compared; systems queries can access controlled rows only. |
| `docs/analysis/figures/` | Five paper figures. | Regenerated from `data/site`; byte-compared by verify mode. |
| `docs/analysis/paper.qmd` | Submission manuscript source. | Claim audit, Quarto HTML, and Typst PDF gates. |

## Protocol And Catalog Artifacts

| Artifact | Purpose | Gate |
|---|---|---|
| `data/models.txt` | Legacy/full roster source tags. | Covered by `data/models.lock.jsonl`. |
| `data/models.lock.jsonl` | Current model eligibility lock. | `scripts/validate-model-lock.py`. |
| `data/model.schema.json` | Model lock schema shell. | Checked by the validator. |
| `data/model-license-rules.json` | License rule table with evidence URLs/classes. | Consumed by `scripts/build-model-lock.py`; included rows must not have unknown license metadata. |
| `scripts/audit-model-metadata.py` | Model metadata coverage report. | Fails if included rows lack `source_url` or license metadata; reports missing digests/hashes and llama.cpp compatibility. |
| `data/runtime-policy.json` | Runtime split: Ollama service, llama.cpp experiments, Ollama legacy snapshot. | `scripts/validate-runtime-policy.py`. |
| `data/run-manifest.json` | Locked run environment and scenario-set hashes. | `scripts/validate-scenarios.py`. |
| `data/run-matrix.json` | Approved model/scenario/memory/strategy launch matrix. | `scripts/validate-scenarios.py`. |
| `data/scenario-lifecycle.schema.json` | Future candidate scenario lifecycle schema. | `scripts/validate-scenarios.py`. |

## Dev Evidence Artifacts

| Artifact | Purpose | Gate |
|---|---|---|
| `data/scenarios.external-candidates-v0.json` | External-pattern dev scenario pack v0. | `scripts/validate-external-candidates.py`. |
| `data/scenarios.external-candidates-v1.json` | Repaired external-pattern dev scenario pack v1. | `scripts/validate-external-candidates.py`. |
| `data/runs/external-v1-spread10-baseline-clean-20260703-164337/` | Completed dev-only v1 spread10 run artifacts. | `scripts/report-run-quality.py --strict`. |

## Audit Command

Run the structural audit:

```bash
python3 scripts/audit-paper-data.py
```

The command checks the analysis schema/manifest, exact populations, site mirrors,
snapshots, model lock, scenario validators, and strict committed dev-run quality.
Run the publication and claim gates separately:

```bash
python3 scripts/audit-paper-claims.py
scripts/build-analysis-site.sh --verify
```

These gates do not replace the future Croissant/archival package.