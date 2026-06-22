# Waves 1 + 2 → single consolidated dataset — plan

**Status: EXECUTED 2026-06-22.** The waves were merged into a single dataset and
the paper/docs/notebooks reframed off it.

> **Actual outcome (supersedes the "88-model uniform full-telemetry" decision
> below).** We adopted **per-axis / available-case** reporting instead of listwise
> deletion: the dataset is **94 functional models** (95 snapshot rows incl. the
> `phi:2.7b` served-failure) with the **three decision axes — quality, safety,
> energy — 100 % complete**, and **MBU/roofline reported on the 88-of-94** models
> that have bandwidth telemetry (the other 6 are an instrumentation gap, *missing
> at random*; we do **not** drop them from the study). The reasoning arm is the
> **4 DeepSeek-R1-distilled** models. Headline shifted to **12 of 94 Pareto-optimal**,
> the quality knee to **2–3B** (4–5GB +4.6 pts), the safety arm to **71.4 % vs
> 47.2 %**, and the consolidated cross-judge **κ_quad = 0.91** over 8,909 pairs.
> The MBU-ceiling worry was moot: the notebook always normalized against the
> datasheet peak (38.4 GB/s), never the lost `calibration.json`.

---

*(Original plan retained below for provenance. Owner decision points marked **[DECIDE]**.)*

## 0. Framing (the point)

Waves 1 and 2 are **one experiment, split into two batches for operational
reasons only** (the broader roster was added after Wave 1; Ollama's flaky `hf.co`
pulls forced a resume sweep). Same node, same 19 scenarios, same protocol (temp
0.7, R=5), same 2-judge quality pass. The paper and docs must present **one
dataset of N models on one node** — "Wave 1 / Wave 2" demoted to a one-line
provenance note, not a result.

## 1. Findings (verified 2026-06-21, from the live raw data)

- **Headline axes are already at parity.** Safety (`det_score`) and energy
  (`energy_wh`, watts) are **100%** populated for every Wave-2 row; quality
  (2-judge `claude-opus-4.8` + `gpt-5.5`) is the in-flight pass.
- **The ~10% "gap" is NOT the failed models.** It is exactly **7 complete,
  working models** that each lack *all* memory-bandwidth/perf telemetry — a
  perf-counter capture gap during their run, not a model failure:
  `falcon3:3b-instruct-q8_0`, `qwen3:0.6b-fp16`, `qwen2:0.5b-instruct-q8_0`,
  `granite3.1-dense:2b-instruct-q8_0`, `qwen3:1.7b-fp16`, `stablelm2:1.6b-zephyr`,
  `smollm2:360m`. The other **64/71** models have full membw. → **Cleaning the
  failed models will NOT close this gap.**
- **Failed models = 9 with zero usable rows** (transient `hf.co`/registry
  pull-failures). They are already absent from the dataset (no rows to clean).
- **Wave-1 ∩ Wave-2 overlap = 1 model: `smollm2:360m`.** Conveniently, the
  **Wave-1 copy has full membw**, so keeping Wave-1's copy resolves 1 of the 7.
- **`calibration.json` is lost** (not on the Mac, not in the node snapshot). The
  MBU% ceiling (`peak_membw_mb_s`) must be recovered (§4). Max-observed membw:
  Wave-1 17.2 GB/s, Wave-2 22.8 GB/s.

## 2. Cleaning rules — the definition of the single dataset

A row/model is **in the consolidated dataset** iff:

1. **Include a model** iff it has **≥ 93 non-DNF rows** in either wave.
2. **Keep DNF rows** inside included models (a DNF is a real behaviour result —
   Wave-1 already keeps its 178).
3. **Dedup overlaps**: if a model is in both waves, **keep the Wave-1 copy**
   (fuller telemetry) and drop the Wave-2 copy. → drop Wave-2 `smollm2:360m`.
4. **Exclude (with an explicit appendix, like Wave-1 already does for
   `phi:2.7b`)**:
   - the **9 pull-failed** models (0 rows) — `exaone3.5:2.4b(+q4/q8)`,
     `exaone-deep:2.4b`, `granite3.1-moe:1b(+q8)`, `stablelm-zephyr:3b`,
     `hf.co/google/gemma-3-{1b,4b}-it-qat-q4_0-gguf`;
   - **`phi:2.7b`** (Wave-1 served-failure, all 95 DNF);
   - the **7 membw-gap models** (Wave-2 copies only) — full telemetry is required
     (§3), so they are dropped to keep the dataset uniform;
   - any other all-DNF model surfaced at merge time.
5. **Headline 3-axis (safety, energy, quality) must be 100%** for every included
   model. (It is.)
6. **Every axis (incl. MBU / IPC / DRAM power) is 100%** across the 88-model
   dataset — the 7 membw-gap models are excluded (§3), so there are no holes.

## 3. The 7 membw-gap models — **[DECIDED 2026-06-21: exclude them]**

**Decision: full telemetry is required, so the 7 membw-gap models are EXCLUDED
from the analysis dataset** (dropped, not re-run). This yields a **uniform
88-model dataset** in which every model has every axis — safety, energy, quality,
membw, IPC — with **no "membw unknown" exceptions**. The 7 stay in `data/raw/`
for provenance and are named in the excluded appendix. (Re-running them later for
a 95-model full-telemetry set — the old "Option A" — is deferred and not on the
critical path.)

The 7 (Wave-2 copies): `falcon3:3b-instruct-q8_0`,
`granite3.1-dense:2b-instruct-q8_0`, `qwen2:0.5b-instruct-q8_0`, `qwen3:0.6b-fp16`,
`qwen3:1.7b-fp16`, `stablelm2:1.6b-zephyr`, `smollm2:360m` — note Wave-1's
`smollm2:360m`, which **does** have membw, is **kept**.

## 4. MBU ceiling recovery (needed for both options)

`report.py` normalizes MBU as `membw_peak_mb_s / cal.peak_membw_mb_s`. Recover the
ceiling in this order:

1. **grep `data/raw/experiment.var.log`** — `run-experiment.sh` logs
   `calibration: {…}` at startup; the original `peak_membw_mb_s` is likely there.
   If found → use it as the single ceiling for **both** waves (consistent with
   Wave-1's already-published MBU).
2. Else, if Option A is taken → use **tonight's fresh** `peak_membw_mb_s`
   (DRAM bandwidth is a hardware property, valid for both waves) and **re-publish
   Wave-1 MBU** with it (note the small shift).
3. Else → document MBU as **"relative to max observed bandwidth"** (a defensible
   lower-bound ceiling) and state it. Back up the recovered/used `calibration.json`
   to `data/raw/`.

## 5. Execution steps (ordered)

1. **[in progress]** Finish Wave-2 2-judge judging (8 workers, ~overnight).
2. **Reconcile judge output:** `cat .tmp/judge/parts/judged.*.jsonl
   .tmp/judge/judged.wave2.seed.jsonl` → dedup on `(model,scenario,rep,
   judge_model)` → `judged.wave2.jsonl`. **Validate:** every non-DNF
   `(model,scenario,rep)` has exactly 2 judge rows; report any gaps.
3. **[Option A only]** Re-calibrate + re-run the 7 membw-gap models; fetch +
   replace their rows in the Wave-2 raw.
4. **Recover the MBU ceiling** (§4); back up `calibration.json` → `data/raw/`.
5. **Merge → single snapshot.** `scripts/merge-wave.py --results
   .tmp/wave2/results.wave2.jsonl --judged .tmp/judge/judged.wave2.jsonl`. Apply
   the cleaning rules (§2) — see §6 for the merge-wave.py change needed.
6. **Rebuild the analysis** from the unified snapshot: re-run
   `docs/analysis/wave_analysis.ipynb` headless → `data/site/*` + figures.
7. **Reframe paper + docs to one dataset:** present **N models on one node**;
   drop the wave split to a provenance footnote; update every count (N total, M
   complete, the excluded appendix); state the MBU coverage (89/96 or 96/96).
   Files: `docs/analysis/paper.qmd`, `PAPER.md`, `README.md`, `REVIEWER.md`,
   `data/raw/README.md`, `docs/MODELS.md`.
8. **Update `data/raw/README.md`** to the consolidated framing + the 7 membw
   exceptions + the excluded-models appendix.
9. **Commit + push; verify the Pages site** rebuilds with the new N.

## 6. `scripts/merge-wave.py` change needed

The current upsert keys on `(model,scenario,rep)` and replaces on better
`det_score`. Two additions for clean consolidation:

- **`--exclude <model[,model…]>`** (or `--exclude-file`): drop these from the
  **Wave-2** merge entirely → the **7 membw-gap models** (this also covers the
  `smollm2:360m` overlap, since Wave-1's copy with membw is the one we keep).
  `phi:2.7b` is excluded at analysis time (already is).
- **Overlap guard:** do **not** let a Wave-2 row replace an existing Wave-1 row
  for a model present in both (otherwise Wave-2's membw-less `smollm2:360m` could
  overwrite Wave-1's). Simplest: `--exclude smollm2:360m` covers it; or add
  `--no-replace-existing-models`.

## 7. Acceptance criteria (done = a single dataset)

- One `results_snapshot.csv`: **88 models** (24 Wave-1 usable + 64 Wave-2 with
  full membw), 95 rows each (incl. DNF), **every axis 100%** (safety, energy,
  quality, membw, IPC) — a uniform full-telemetry dataset.
- One `judged_snapshot.csv`: same N models, 2-judge consensus mean (1–5).
- **No "wave" distinction** in the analysis — a single population.
- Excluded models listed in one appendix with the reason each.
- `data/site/` + figures + paper counts all reflect the unified **N**; Pages site
  green.

## 8. Provenance (kept, not deleted)

`data/raw/` retains the **per-batch** archives (`results.var.*`, `results.wave2.*`,
both `outputs.*`, both judge sets, logs) so the consolidation is reproducible from
source. The *analysis* dataset is unified; the *raw* stays batch-labelled for
audit.
