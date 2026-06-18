# Raw run data — Wave 1 (variance + deterministic)

This directory is the released raw artifact for the Wave-1 ApprenticeOps run, so
the headline tables and the analysis notebook are reproducible, **not just
asserted**.

## Files

| File | What | Rows / notes |
|---|---|---|
| `results.var.jsonl.gz` | **Variance run** — temperature 0.7, R=5 reps/seed. One row per `(model, scenario, rep)` with the full OTel-GenAI + telemetry schema. | 2375 rows (25 models × 19 scenarios × 5 reps), 0 parse errors |
| `results.det.jsonl.gz` | **Deterministic run** — temperature 0, greedy, 1 sample/(model×scenario). | 475 rows (25 × 19) |
| `outputs.var.tar.gz` | The raw model **answer texts** for the variance run (`<model>__<scenario>.txt`). | — |
| `experiment.var.log` / `experiment.det.log` | Run logs (per-scenario timings, det scores, finish reasons). | — |

Field dictionary: [`docs/TELEMETRY.md`](../../docs/TELEMETRY.md). A flat,
text-free per-result CSV (for quick analysis) lives at
[`data/snapshots/results_snapshot.csv`](../snapshots/results_snapshot.csv).

## Integrity (verified before release)

- **Completeness:** every model has exactly **95** variance rows; all 25 models
  present; `det_score` ∈ [0, 1]; 0 JSON parse errors.
- **DNF (a first-class result):** 178/2375 variance rows are DNF —
  `DNF:timeout` (83, mostly thinking models exceeding the watchdog) and
  `DNF:error:HTTPError` (95).
- **Failed model (disclose):** **`phi:2.7b` did not serve** — all 95 of its rows
  are `DNF:error:HTTPError` (an Ollama serve/template incompatibility, not a
  reasoning failure). Treat `phi:2.7b` as **DNF / no valid quality data** in any
  ranking; do **not** read its scores as performance.

## Privacy / secrets (scanned before release)

The run was scanned for tokens, API keys, JWTs, private keys, and real private
IPs — **none were found**. Secret-like strings that appear in the answer texts
(`SuperSecret123`, `eso-verify-*`, etc.) are the **synthetic test fixtures** that
are already part of the public scenarios in
[`data/scenarios.json`](../scenarios.json) (e.g. the plaintext-secret and
ExternalSecret scenarios) — they are **not real credentials**. Any IP addresses
in answers are model-generated examples, not the real node. The scenarios are
**synthetic-but-repo-grounded**: real config *shapes*, no real secret *values*.

## Judge columns

The frontier-judge (`judge_score` / `% of frontier`) is **not yet populated** in
these files — that pass runs off-node post-hoc (`judge.py`). Until then, treat
Wave-1 as **deterministic-only**.
