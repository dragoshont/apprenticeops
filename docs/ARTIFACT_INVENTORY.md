# Artifact Inventory

Status: active reproducibility inventory, created 2026-07-03.

This file lists the committed artifacts that support the current paper-era
snapshot and the post-audit dev evidence. It does not claim that the final
doctoral <=5B-parameter roster is complete.

## Paper-Era Snapshot Artifacts

| Artifact | Purpose | Gate |
|---|---|---|
| `data/snapshots/results_snapshot.csv` | Raw inference snapshot used by analysis exports. | Non-empty CSV; audited by `scripts/audit-paper-data.py`. |
| `data/snapshots/judged_snapshot.csv` | Two-judge quality snapshot. | Non-empty CSV; audited by `scripts/audit-paper-data.py`. |
| `data/snapshots/judged_snapshot.det.csv` | Deterministic/single-pass snapshot retained for comparison. | Non-empty CSV; audited by `scripts/audit-paper-data.py`. |
| `data/site/summary.json` | Machine-readable headline summary. | Expected `n_models=94`, `n_pareto=12`, `n_dominated=82`, `quality_knee_bracket=2-3B`. |
| `data/site/models.csv` | Per-model site export. | Row count must equal `summary.n_models`. |
| `data/site/pareto.csv` | Pareto-front site export. | Row count must equal `summary.n_pareto`. |

## Protocol And Catalog Artifacts

| Artifact | Purpose | Gate |
|---|---|---|
| `data/models.txt` | Legacy/full roster source tags. | Covered by `data/models.lock.jsonl`. |
| `data/models.lock.jsonl` | Current model eligibility lock. | `scripts/validate-model-lock.py`. |
| `data/model.schema.json` | Model lock schema shell. | Checked by the validator. |
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

The command checks site exports, snapshots, model lock, scenario validators, and
strict run-quality reporting for committed dev run artifacts. It is not a full
notebook rerender and does not replace a later Croissant/archival package.