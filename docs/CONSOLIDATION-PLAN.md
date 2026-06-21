# Waves 1 + 2 → single consolidated dataset — plan

**Status:** draft for execution after Wave-2 judging finishes. Owner decision points marked **[DECIDE]**.

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
   - any other all-DNF model surfaced at merge time.
5. **Headline 3-axis (safety, energy, quality) must be 100%** for every included
   model. (It is.)
6. **Systems axis (MBU / IPC / DRAM power)** is **89/96 models** (the 7 membw-gap
   models excepted) **unless** Option A in §3 is taken.

## 3. The 7 membw-gap models — **[DECIDE]**

- **Option A — full parity (recommended if the systems section matters).**
  Tonight, while the node is up: re-run `calibrate.py` (→ fresh `calibration.json`)
  and re-run **only these 7 models** with `PERF_MEMBW=1 PERF_CORE=1` (they are
  mostly tiny — 0.36–3B — so ~1–2 h total). Then **replace** their Wave-2 rows
  (delete-then-merge, since the upsert keeps best `det_score`, not best
  telemetry). Result: **96/96 membw.**
- **Option B — accept + document.** Keep their headline axes (100%); mark membw
  `unknown` for the systems section. `report.py` already returns
  `"unknown (no membw)"` for these. Result: **89/96 membw**, headline unaffected.

Either way the **headline sovereign-selection result is identical** — MBU is a
secondary systems lens.

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

- **`--exclude <model[,model…]>`** (or `--exclude-file`): drop these models from
  the merge entirely → used for `phi:2.7b` and the Wave-2 overlap dup
  `smollm2:360m`, and optionally the membw-gap models under Option B if you
  choose to exclude rather than annotate.
- **Overlap guard:** do **not** let a Wave-2 row replace an existing Wave-1 row
  for a model present in both (otherwise Wave-2's membw-less `smollm2:360m` could
  overwrite Wave-1's). Simplest: `--exclude smollm2:360m` covers it; or add
  `--no-replace-existing-models`.

## 7. Acceptance criteria (done = a single dataset)

- One `results_snapshot.csv`: **N models**, 95 rows each (incl. DNF), headline
  axes **100%**, systems **≥ 89/96** (or 96/96 under Option A).
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
