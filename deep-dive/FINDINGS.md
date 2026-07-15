# CEOps / ApprenticeOps — deep-dive findings

*A reproducible re-analysis of the full 9,025-run corpus (95 models × 19 ops
scenarios × 5 reps), beyond the locked site summary. All numbers come from the
scripts in this folder against `data/snapshots/*` + `data/model_metadata.csv`.
Methods are grounded in the eval-statistics literature (cited inline).*

## Corpus (what the site does not show)

The public site publishes a conservative slice: 94-model quality+safety fractions
and a 24-model controlled three-axis Pareto. The corpus underneath is much richer
— **9,025 runs** with energy, decode/prefill throughput, wall latency, memory
bandwidth, MoE expert usage, DNF/finish-reason, and a full model taxonomy
(family, org, arch, quant, MoE, thinking, tools, license, training-regime;
0.13–7.6 B params, 0.29–5.9 GB). This is an **on-device small-model** study (all
≤7.6 B, one offline i5-8350U node), so the right lens is capability × energy ×
speed × memory × size (cf. Lu et al., *Small Language Models: Survey,
Measurements, and Insights*, arXiv:2409.15790).

**Two batches by design (controlled vs breadth), not a confound.** Per `PAPER.md`
§7, the frozen v1 snapshot holds two batches with different *roles*: `var` — the
pre-registered **controlled** first batch (25 tags / 24 functional; base clock
1700, turbo off, RAPL package-0; the *only* energy-comparable scope) — and `wave2`
— a **breadth-extension** second batch (70 tags, dynamic turbo-on) that grows
quality/safety coverage to 94 functional but is *excluded from energy/systems
ranking by design* (schema v1 records batch/regime/source and forbids the pooled
energy front). CPU regime changes watts and latency, not the tokens a model emits
at fixed temperature, so **quality / safety / capability pool across all 94
functional models**; **energy is confined to the 24 controlled models by design**.
A small optional *bridge subset* (the same handful under both regimes) would
additionally *price* the CPU power policy — an enhancement, not a correction.
(Separate cohorts outside this snapshot: the 152-model `full-chatok-core20-r5`
doctoral run analysed below, and an ongoing 21-model timeout-sensitivity
follow-up, DNF-selected — 21×20×5 = 2,100 rows.)

## Headline discoveries (the gold)

1. **Tool-training is the single biggest capability lever for ops-agent tasks.**
   Tools-capable models score **+0.43 quality (p=0.007)** and **+0.39 safety
   (p=0.032)** over non-tool models — both significant. Ops tasks are agentic;
   tool-trained models handle the action/format. *(A3)*
2. **Reasoning-training backfires on operational tasks — a triple liability.**
   Reasoning models have the **lowest quality (1.61 vs 2.26 instruct)**, **lowest
   safety (1.78)**, burn **2.4× the energy (0.205 vs 0.085 Wh)**, **truncate**
   constantly (hit the token cap) and **time out** (`deepseek-r1:7b` DNFs 75%).
   Long chains are the wrong tool for direct, safe, budgeted ops actions. *(A3, A6)*
3. **granite4-tiny (IBM, MoE-hybrid) is the efficiency star.** Energy scales
   ~linearly with size (log-log slope 1.00, R²=0.60 — memory-bandwidth-bound CPU
   decode), and granite4-tiny uses **~2.5× less energy than its size predicts**
   (largest negative residual) while ranking #6 in quality and dominating the
   `diagnose` task class (4.07). **IBM tops average org quality (2.74)**, ahead of
   Microsoft and Qwen. *(A2, A3, A4)*
4. **Q4 quantization is nearly free.** Within-model Q8→Q4 costs only **−0.11
   quality** (Wilcoxon p=0.024 but tiny) while saving energy and running faster.
   Q4_K_M is the sweet spot — vindicating the site's pick. *(A3)*
5. **The benchmark is underpowered to rank the top tier.** Friedman is
   overwhelming (χ²=908, p≈10⁻¹⁸¹, Kendall's W=0.51 — models genuinely differ),
   but the Nemenyi critical difference spans ~39 rank positions: **43 of 95 models
   are statistical co-leaders** and 18 CIs overlap #1. The "top pick" is honestly
   a *statistical tie* among the Qwen-4B/1.7B + granite4 cluster. *(A1; Demšar 2006;
   Miller 2024, arXiv:2411.00640)*
6. **Safety and quality are ~collinear (r=0.970)** for small ops models — safety
   is not an independent axis you trade against quality; it rides with it. That is
   *why* the site's quality-safety Pareto has only 2 points. **The real
   multi-objective structure is capability-vs-energy/speed/size.** But **44% of
   models (42/95) fail the destructive-guard** (`guard-08`, they take/allow a
   destructive action) — worst are reasoning-distills and tiny models. *(A4)*
7. **The LLM judge is trustworthy and — unusually — free of verbosity bias.**
   Dual-judge (claude-opus-4.8 + gpt-5.5) quadratic κ=0.92, within-1 agreement
   99.9%, no family lenience. Controlling for correctness within scenario, longer
   answers score *slightly lower* (b_length=−0.10) — the rubric-based judging
   defeats the classic length bias (contra Zheng 2023, arXiv:2306.05685). This
   defends the entire quality axis. *(A5)*
8. **Judge-vs-deterministic divergence is structured.** Overall Spearman 0.908,
   but the **gemma family is "judge-favoured"** (fluent, ranks ~24 places higher
   by judge than by deterministic correctness) while **tiny models are
   "det-favoured"** (pass checks, read poorly). Rubric-review candidates:
   `secure-12-broad-rbac`, `detect-01`, `secure-10`. *(A1, A5)*

## Deeper battery (B-series) — additional discoveries

9. **The ~4B sweet spot is real and robust — bigger does not win.** Over the
   *full 152-model spectrum* (up to 8B, the `full-chatok-core20-r5` run), the 4B
   champion beats every 7–8B model, the ≥7B tier is the *worst* on average (1.69
   vs 2.50 for 3–6.5B), and **Spearman(params, quality) = 0.14** — capability
   plateaus at ~4B on ops tasks at CPU scale. *(B6)*
10. **The ranking is robust to judge-version and prompt-format.** On the 90 models
    shared between the chatok run (gpt-5.4 + claude-4.6, chatok format) and the
    snapshot (gpt-5.5 + claude-4.8, current format), Spearman = **0.974**. With
    A5, the quality axis is validated on three fronts. *(B6)*
11. **Decode is memory-bandwidth-bound, and that explains the energy story.**
    log(decode_tps) vs log(size) slope = **−0.90** (theory −1.0), R²=0.86.
    MoE/hybrid models beat the size-roofline by **~2.4×** (`granite3.1-moe` +0.93,
    `granite4-tiny` +0.82 vs dense −0.02) because they stream only active experts
    — the mechanistic reason granite4-tiny is the energy star. *(B4)*
12. **The headline effects survive confound control.** In a model-clustered
    fixed-effects model (controls size, quant, regime, scenario): `tools` = **+0.29
    (p=0.002)**, `reasoning` = **−0.88 (p<0.001)**, `log_params` = +0.63/e-fold,
    Q8-vs-Q4 ≈ +0.10 (ns). Tools and the reasoning penalty are genuine partial
    effects, not size artifacts. *(B3)*
13. **IRT: the safety scenarios are the most *informative*** at mean ability
    (`guard-08` Fisher info 7.46, `secure-09` 6.35), and **12 of 19 scenarios
    carry 80% of the information** — the set is prunable. Phi models are
    det-strong but judge-mid (the det-vs-judge split is a Microsoft/Phi vs
    Google/Gemma signature). *(B1)*
14. **Model archetypes** (PCA/k-means): the universe is a **capability↔speed
    continuum** (PC1 = 51% of variance; quality~decode_tps = −0.59), splitting into
    capable-slow generalists (44), fast-weak lightweights (49), and 2 big-failure
    outliers. *(B2)*

## Full-run re-center (Option A) — new findings

Centering the analysis on `full-chatok-core20-r5` (152 models, one controlled
turbo-off / RAPL package-0 regime; `full_data.py` + `full_report.py`) surfaces
results the two-batch snapshot could not:

15. **3-axis coverage jumps 25 → 152 models.** Quality × safety × **energy** is now
    measured on every model under a single regime (no cross-batch confound), and the
    ranking is robust to the re-center (**Spearman 0.974** vs the frozen snapshot).
16. **Tool-training reproduces** on the full set: **+0.37 quality (p=0.018)**.
17. **"Thinking mode" penalty is mostly a token-budget artifact — adversarially
    defended** (`full_reasoning_pairs.py`). Same-lineage instruct-vs-thinking pairs
    (Qwen3-4B ×2, Phi-4-mini, Qwen2.5-3B→smallthinker, EXAONE) lose **−0.42 quality**
    at a fixed **512-token cap** (paired *t* p≈10⁻⁶). BUT both modes share that cap,
    thinking exceeds it **74–100%** of the time, and on the answers it *finishes*
    **3 of 5 pairs match or beat instruct** (mean Δ −0.07). Honest claim: **thinking
    mode is a poor FIT for a tight token/latency budget on bounded ops tasks** (it
    exhausts the budget before answering) — *not* that its reasoning is worse. Worst
    on `toolcall` (−1.50) and `monitor`; neutral on `secure`. Lone genuine exception:
    EXAONE-deep (worse even when finishing; also the least-matched pair). **To be
    confirmed** by the queued budget-sensitivity re-run at higher `max_tokens`
    (`data/models.reasoning-budget-v1.txt`).
18. **Reasoning roster gap:** deepseek-r1 (the frozen "reasoning hurts" driver) is
    absent from `full` (only deepseek-*coder* is present); the pilot carries the
    R1-specific claim, or it is reframed as the budget-fit finding above.
19. **Truncation triage (`full_truncation_scan.py`).** Heavy truncation ≠ budget
    victim. Of the models truncating ≥30% at the 512 cap, only **`qwen3:4b`** (plain,
    thinking-on; 100% truncated, so unmeasurable when finished) is a further budget
    victim to re-run; the rest (`starcoder2:3b`, `codegemma:2b`, `falcon3:1b`,
    `deepseek-coder:1.3b`, `smollm:360m`) are **genuinely weak** — `q_done ≈ q_all ≈
    1.0–1.5` with ~zero lift when they finish. Queued as
    `data/models.reasoning-budget-v2.txt` (the victim plus weak controls that should
    *not* benefit — the control that isolates over-generation from "more tokens = better").

## Methods (grounded)

| Analysis | Method | Source |
|---|---|---|
| A1 ranking rigor | scenario-clustered bootstrap CIs; Friedman + Kendall's W; Nemenyi critical difference | Miller 2024; Demšar 2006 |
| A2 efficiency | Pareto frontiers (2- & 3-axis); energy residualised on size | Luccioni 2024 (FAccT), arXiv:2311.16863 |
| A3 arch/quant | within-model paired deltas; bootstrap-CI group contrasts + Mann-Whitney | — |
| A4 capability | scenario difficulty + discrimination (IRT-style proxy); class×family; safety | Maia Polo 2024 (tinyBenchmarks), arXiv:2402.14992 |
| A5 judge | inter-judge quadratic κ; verbosity partial-regression; judge-vs-det | Zheng 2023, arXiv:2306.05685 |
| A6 variance | variance decomposition; split-half reproducibility; failure concentration | Miller 2024 |

## Where to dig deeper (ranked follow-ups)

1. **Full 2-PL IRT** on the binary `det_score` to get per-scenario *discrimination*
   + *difficulty* + per-model *ability* with SEs, and to prune/rebalance the
   scenario set (`detect-01` is near-redundant, r=0.54). *(tinyBenchmarks)*
2. **Model archetype clustering** — PCA/UMAP on the model×metric space
   (quality, safety, energy, speed, memory, stochasticity, truncation) to name
   archetypes (efficient-generalist / safe-specialist / fast-but-weak /
   reasoning-liability). Correlation structure of all metrics.
3. **Mixed-effects model** (`judge ~ 1 + (1|model) + (1|scenario) + fixed effects
   for tools/regime/quant/params`) to get partial effects with proper CIs, since
   ~23% of variance is rep-noise and the factors are unbalanced.
4. **Roofline / MBU deep-dive** using `membw_peak_mb_s` + `calibrate.py` ceilings:
   confirm decode is memory-bandwidth-bound and quantify how MoE/hybrid breaks the
   size→energy law (the granite4 result).
5. **A bridge subset across regimes** — an optional enhancement, not a fix: run
   the same handful of models at base-clock *and* dynamic-turbo to *price* the CPU
   power policy's energy/latency cost (ties to the homelab EPP=performance
   finding). The `var`/`wave2` stages are disjoint by design, so this is all that
   is needed to license cross-regime energy.
6. **The 897 MB `full-chatok-core20-r5` run** (unанalysed here) — a deeper single
   collection that may support the top-tier separation the 19-scenario set cannot.
7. **Human-eval expansion** (`human_eval.py`) targeted at the judge-vs-det
   divergence scenarios to adjudicate the gemma "fluency" question.

## New-data recommendations

- **More scenarios**, prioritising *discriminative* classes (capacity/foresee,
  monitor, upgrade) over the near-redundant `detect-01`, to separate the top ~43.
- **More reps or lower temperature** for the top tier only (rep-noise is 23%;
  model signal is only ~1.5× noise per cell).
- **Energy on more models** (only 25 have controlled energy) — extend the
  single-regime controlled scope so the efficiency frontier covers the full 95.
- **A destructive-safety hard set** — 44% fail `guard-08`; one guard scenario is
  too thin a safety axis for a claim.

## Caveats / honesty

Single offline hardware node (i5-8350U/24 GB); small models only (≤7.6 B); energy
comparable only within the 25-model controlled single regime; `phi:2.7b` is a
broken outlier (100% DNF) and should be excluded, not reported as "efficient".
Ratio metrics (quality/cost) are degenerate at the quality floor — use Pareto
frontiers, not leaderboards of quality-per-watt.

## Reproduce

```bash
cd deep-dive && python -m venv .venv && .venv/bin/pip install numpy pandas scipy scikit-learn matplotlib statsmodels pyarrow
.venv/bin/python ceops_data.py      # build unified dataset -> out/runs.parquet
.venv/bin/python a1_ranking.py      # ranking rigor
.venv/bin/python a2_efficiency.py   # efficiency frontiers -> figures/
.venv/bin/python a3_scaling_arch.py # quant / arch / tools / regime
.venv/bin/python a4_capability.py   # scenario difficulty + safety
.venv/bin/python a5_judge.py        # judge validity
.venv/bin/python a6_variance.py     # variance + failures
```
