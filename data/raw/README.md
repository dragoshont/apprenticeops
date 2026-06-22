# Raw run data — the 94-model dataset (two collection batches)

This directory is the released raw artifact for the ApprenticeOps runs, so the
headline tables and the analysis notebook are reproducible, **not just
asserted**. The data was collected in **two batches** for operational reasons (the
broader roster was added after the first batch, and Ollama's intermittent `hf.co`
pulls forced a resume sweep); **together they form the single 94-model analysis
dataset** in [`data/snapshots/`](../snapshots/). The raw files below stay
**batch-labelled** for audit — `results.var.*` is the first batch, `results.wave2.*`
the second. Same protocol throughout: 19 scenarios, deterministic (temp 0) and
variance (temp 0.7, R=5), one commodity node.

## First batch — `results.var.*` (core)

| File | What | Rows / notes |
|---|---|---|
| `results.var.jsonl.gz` | **Variance run** — temperature 0.7, R=5 reps/seed. One row per `(model, scenario, rep)` with the full OTel-GenAI + telemetry schema. | 2375 rows (25 models × 19 scenarios × 5 reps), 0 parse errors |
| `results.det.jsonl.gz` | **Deterministic run** — temperature 0, greedy, 1 sample/(model×scenario). | 475 rows (25 × 19) |
| `outputs.var.tar.gz` / `outputs.det.tar.gz` | The raw model **answer texts** (`outputs/<model>__<scenario>[__r<rep>].txt`). | 2413 / 475 files |
| `judged.var.claude.jsonl.gz` / `judged.var.gpt55.jsonl.gz` | **Variance judge** — per-judge 1–5 scores (`claude-opus-4.8` + `gpt-5.5`); `judged_snapshot.csv` is their per-rep mean (verified). | 2375 rows each |
| `judged.det.jsonl.gz` / `judged.det.gpt55.jsonl.gz` | Deterministic-pass judge scores (`claude-opus-4.8` + `gpt-5.5`). | 475 rows each |
| `experiment.var.log` / `experiment.det.log` | Run logs (per-scenario timings, det scores, finish reasons). | — |
| `judge-logs.tar.gz` | Judge-run logs (cost/timing for the det + variance judge passes). | — |

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

## Second batch — `results.wave2.*` (broader roster)

Same variance protocol (temp 0.7, R=5, 19 scenarios), a broader model set per
bracket; run on the node 2026-06-19/20.

| File | What | Rows / notes |
|---|---|---|
| `results.wave2.jsonl.gz` | Variance run, raw. Same schema as Wave 1. | 7543 lines = 7410 result rows + 133 `pull_failed` stubs |
| `outputs.wave2.tar.gz` | Raw **answer texts** (`outputs/<model>__<scenario>__r<rep>.txt`). | 9728 files |
| `experiment.wave2.log.gz` / `driver.wave2.out` | Run log + driver output. | — |

**Completeness (Wave 2):** ~80 models attempted. After dropping `pull_failed`
stubs and deduping `(model, scenario, rep)` on best det_score: **71 complete**
(95 rows each); **9 with no usable rows** — **transient pull-failures** (Ollama's
intermittent `hf.co` redirect bug
[#15661](https://github.com/ollama/ollama/issues/15661) + registry blips), not
model failures. Those 9 (plus a further 7 all-DNF served-failures and the first
batch's `phi:2.7b`) are **excluded** from the analysis and named in the paper's
excluded appendix. The second batch *does* carry the systems telemetry: raw
`membw_peak_mb_s` / perf-core are present for **~94%** of rows (safety + energy
are 100%). The STREAM calibration did not complete on the node, so the **MBU%**
normalization uses the node's **datasheet** peak bandwidth (38.4 GB/s, dual-channel
DDR4-2400) and is read as a relative efficiency; **6 of the 94 functional models
lack per-run bandwidth telemetry** entirely (a perf-counter capture gap, missing at
random), so MBU is reported on the **88-of-94** covered subset. Privacy: scanned
(same synthetic fixtures as the first batch — `SuperSecret123`, `eso-verify-*`,
example JWT — no new secrets).

**Quality (judged):** the second batch's 2-judge pass (`claude-opus-4.8` + `gpt-5.5`)
ran off-node post-hoc on the answer texts above. Consolidated across both batches,
the two judges agree at **quadratic-weighted κ = 0.91** over **8,909** jointly-scored
reps (77.3% exact, 99.8% within-1).

## Reproducing the snapshots

`data/snapshots/*.csv` are derived from these raw files by
[`../../scripts/merge-wave.py`](../../scripts/merge-wave.py). Field dictionary:
[`docs/TELEMETRY.md`](../../docs/TELEMETRY.md).
