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

*Findings 1–14 were computed on the frozen **94-model** var/wave2 snapshot. The
paper centers on the 152-model `full-chatok-core20-r5` run as a standalone study,
so the whole A/B battery is **re-run on the 152 set as R1–R14 below** (see "A/B
series re-run on the 152-model full run"). The 94-model numbers are parked, not
deleted.*

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

9. **~4B is the efficiency knee, but bigger *does* help on average.** *(CORRECTED
   — an earlier version claimed "bigger does not win" from a parameter-unit bug that
   mis-sized 15 sub-1B models as 100–1000B.)* With parameters from the canonical
   `param_count`, mean quality rises 1.81 (<3B) → 2.44 (3–6.5B) → **2.84 (≥6.5B)**,
   **Spearman(params, quality) = 0.73**. The single best model is a 4B
   (`qwen3:4b-instruct` 3.59, edging `qwen3:8b` 3.51) at a fraction of the energy, so
   ~4B is the best quality-per-cost knee — but larger models are better on average.
   *(B6, corrected)*
10. **Ranking is stable across judge-version and prompt-format (exploratory).** On the
    90 models shared between the chatok run (gpt-5.4 + claude-4.6) and the snapshot
    (gpt-5.5 + claude-4.8), Spearman = **0.974** — a name-matched *rank* cross-check
    (NOT a formal cross-run join, which the frozen manifest forbids, and it validates
    ordering only, not the paired magnitudes). *(B6)*
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

## A/B series re-run on the 152-model full run (findings 1–14, single regime)

*Findings 1–14 above are on the frozen **94-model** var/wave2 snapshot. Per the
analysis-integrity rules (`AGENTS.md`), the paper centers on the 152-model
`full-chatok-core20-r5` run **as a standalone study**, so the whole A/B battery is
re-run on it here (`full_ab.py` → `deep-dive/out/full_ab/`; a5→`full_adversarial_review`,
b4→`full_moe_dense`, b5 is N/A on a single regime, b6 already 152). The 94-model
versions are **parked, not deleted**. Conclusions that **change** on the clean set
are flagged ⚠️.*

- **R1 — Tool-training reproduces.** tools-capable **+0.37 quality (p=0.016)**,
  **+0.37 safety (p=0.010)** [a3]; confound-controlled **+0.31 (p=0.001, 0.51
  model-SD)** [b3]. (94 was +0.43 / +0.39.) The biggest durable capability lever.
- **R2 — ⚠️ The "reasoning triple-liability" does NOT reproduce.** The 152 roster has
  **no deepseek-r1 distills** (only deepseek-*coder*) and only **n=1**
  `training_regime=reasoning`, so the 94 penalty vanishes: **regime[reasoning] = +0.07
  (ns)** [b3]. Raw thinking-capable (n=7, mostly Qwen3-4B/8B) is even directionally
  **+0.58 quality** — a family confound, not a reasoning win. The honest 152 result is
  the **budget-fit** story (finding 17): thinking truncates against the 400–700-token
  budget; no clean evidence it degrades reasoning *quality*.
- **R3 — IBM still tops org quality; efficiency star nuanced.** Org means: **IBM 2.46**
  > Microsoft 2.40 > Alibaba/Qwen 2.32 > Google 2.30 [a3]. Energy~size log-log slope
  **0.88 (R²=0.63)**; the largest energy-efficiency-beyond-size residuals are the tiny
  **qwen3:0.6b** models (−0.83) with **granite4:tiny-h 3rd (−0.78)** — granite4 is still
  a star, but sub-1B Qwen3 leads raw efficiency-per-size. *(a2, a3)*
- **R4 — ⚠️ Q4 is NOT free.** 19 same-base Q8-vs-Q4 pairs: **Q4 costs −0.13 quality
  (Wilcoxon p=0.001)**, worst `qwen3:4b` −0.60; saves 0.026 Wh, +3 tok/s [a3] (matches
  the corrected paired-t CI [−0.14,−0.03], finding 20). Q4_K_M stays the deployment
  pick, but "nearly free" is **retracted → "cheap, occasionally lossy."**
- **R5 — Top tier is a statistical tie (reproduces, wider).** Friedman χ²=1326,
  p≈10⁻²⁷⁰, Kendall W=0.44; **28 of 152** CIs overlap #1
  (`qwen3:4b-instruct-2507-q8_0` 3.59); **78/152** within the Nemenyi CD [a1].
- **R6 — Safety~quality collinear reproduces (r=0.953);** **66/152 (43%) fail the
  destructive-guard** (`guard-08`, det<0.5) — worst are sub-1B + a few 3B (qwen2:0.5b,
  LFM2-700M, Hermes-3-3B, llama3.2:1b, tinyllama) [a4].
- **R7 — Judge agreement holds, slightly lower.** 152 dual-judge (claude-opus-4.6 +
  gpt-5.4) **quadratic κ=0.853**, claude +0.14 more generous [full_adversarial_review].
  (a5's verbosity-bias regression reads the 94 two-file judge layout and was **not**
  re-run on the single 152 judged file — flagged as a 152 follow-up.)
- **R8 — Judge-vs-det divergence stays structured.** Spearman **0.896**, Kendall τ=0.71;
  judge-favoured = fluent granite4 / falcon3 / command-r7b; det-favoured =
  phi4-mini-reasoning + tiny Qwen [a1]. (The 94 "gemma judge-favoured" signature shifts
  to granite4 on 152.)
- **R9 — ~4B knee, bigger helps (already corrected).** Spearman(params, quality) =
  **0.73**, +0.56 pts/e-fold, R²=0.49 [a2] — matches b6 (0.740) and finding 9.
- **R10 — ⚠️ Dropped for the standalone paper.** The 0.974 chatok-vs-snapshot rank
  cross-check conflates two judge pairs + different scenario sets; per the standalone-152
  decision it is **retired** (kept only as a 94-model legacy note; see finding 10/15).
- **R11 — Memory-bandwidth-bound decode reproduces.** b2 correlations: quality~decode_tps
  **−0.62**, size~decode_tps **−0.50** (bigger = slower). The 2 MoE/hybrid models beat the
  size-roofline by **+0.87** vs dense −0.02 [full_moe_dense], but **n=2 → descriptive, no
  p-value** (the 94 "+2.4×" is not inferential on 152).
- **R12 — ⚠️ Confound-controlled effects shift.** Model-clustered OLS + scenario FE
  (n=9,000, 152 clusters, R²=0.40): **tools +0.31***, **log_params +0.60***,
  **hi-precision quant +0.44** (vs Q4)**, plus a NEW **MoE −0.35*** partial penalty;
  **regime[reasoning] +0.07 ns** (the 94 "−0.88 reasoning" does not reproduce — roster
  gap). Tools + size are the durable levers [b3].
- **R13 — ⚠️ 2-PL IRT is numerically unstable on the 152 grid — defer to the proxy.**
  Near-saturated det-success on the easy items forces perfect separation → runaway
  discrimination (a = 30–180, nonsensical); validation vs the A4 proxy is only Spearman
  0.52 [b1]. The **reliable** 152 discrimination is the correlation proxy /
  `full_task_difficulty`: most discriminative are the captured **new-\*** incident +
  capacity scenarios (r≈0.90); **secure-14-injection is hardest & least discriminative**
  (mean 1.20, r=0.13 — nearly everyone fails it) [a4].
- **R14 — Archetypes = a clean 3-way capability↔speed split.** PC1 = **53%** of variance;
  k=3 (silhouette 0.32): capable-slow generalists (n=23, quality 2.86, 4.1 tps), a mid
  efficient tier (n=66, 2.48, 7.3 tps), fast-weak lightweights (n=63, 1.51, 18.2 tps).
  quality~safety +0.95 collinear reproduces [b2].

## Full-run re-center (Option A) — new findings

Centering the analysis on `full-chatok-core20-r5` (152 models, one controlled
turbo-off / RAPL package-0 regime; `full_data.py` + `full_report.py`) surfaces
results the two-batch snapshot could not:

15. **3-axis coverage jumps 25 → 152 models.** Quality × safety × **energy** is now
    measured on every model under a single regime (no cross-batch confound), and the
    ranking is robust to the re-center (**Spearman 0.974** vs the frozen snapshot).
16. **Tool-training reproduces** on the full set: **+0.44 quality (p=0.006)** among
    models with *known* tool-capability metadata (unknown-metadata models excluded,
    not counted as non-tool) — an observational association, not a controlled contrast.
17. **"Thinking mode" penalty is directional and mostly fit-to-budget — not
    significant** (`full_reasoning_pairs.py`). *(CORRECTED: the earlier non-truncated
    "recovers" test was survivorship-biased and the p≈10⁻⁶ was pseudoreplicated.)*
    Same-lineage instruct-vs-thinking pairs, tested at the **lineage level** (n≈4;
    Qwen3-4B Q8/Q4 are one lineage): thinking is **−0.40 quality at the per-scenario
    budget (400–700 tokens), NOT significant (paired t p=0.19)**. On **matched**
    non-truncated cells the gap halves to −0.24 (p=0.30), and the clean mode-flip
    pairs (Qwen3-4B, Phi-4-mini) are ≈0.00 — the residual is the near-match
    EXAONE-Deep (−0.80). Mechanism: thinking truncates ~74% of cells against the small
    budget. **Honest claim:** poor fit for tight budgets; evidence it degrades
    *reasoning quality* is weak/underpowered → confirm with the queued
    budget-sensitivity re-run (`data/models.reasoning-budget-v1.txt`).
18. **Reasoning roster gap:** deepseek-r1 (the frozen "reasoning hurts" driver) is
    absent from `full` (only deepseek-*coder* is present); the pilot carries the
    R1-specific claim, or it is reframed as the budget-fit finding above.
19. **Truncation triage (`full_truncation_scan.py`).** Heavy truncation ≠ budget
    victim. Of the models truncating ≥30% at their per-scenario budget, only **`qwen3:4b`** (plain,
    thinking-on; 100% truncated, so unmeasurable when finished) is a further budget
    victim to re-run; the rest (`starcoder2:3b`, `codegemma:2b`, `falcon3:1b`,
    `deepseek-coder:1.3b`, `smollm:360m`) are **genuinely weak** — `q_done ≈ q_all ≈
    1.0–1.5` with ~zero lift when they finish. Queued as
    `data/models.reasoning-budget-v2.txt` (the victim plus weak controls that should
    *not* benefit — the control that isolates over-generation from "more tokens = better").
20. **Quantization: Q4 has a small, real, practically-minor quality cost — not a
    "free lunch"** (`full_quant_pairs.py`). *(CORRECTED: the earlier rep-SD argument
    used the wrong variance.)* Across 16 same-base hi-vs-Q4 pairs, Q4 costs **−0.09
    quality (95% CI [−0.14, −0.04], paired t p=0.003)** — non-zero but **practically
    equivalent within ±0.25 (TOST established)** — while buying **0.66× size, 1.42×
    speed, 0.70× energy**. NOT a blanket free lunch: Q4's safety delta averages −0.08,
    reaches **−0.56** (`qwen3:4b`), and 3/16 pairs lose >0.2 safety. Good default for
    quality/efficiency; verify the Q4 variant for safety-critical use.
21. **MoE is an efficiency story, not a quality one (`full_moe_dense.py`).**
    Metadata-tagged MoE decode **faster than their footprint predicts** (roofline
    residual **+0.87 vs −0.02** for dense — reported descriptively, **n=2, no
    significance test**) and win within the Granite family on tps/GB (5.2 vs 3.7) —
    reproducing the b4 result. MoE-minus-dense *quality* (+0.22) is confounded
    (different models) and is NOT the claim. *Caveats:* only **2** small MoE models are
    reliably tagged (few exist; `is_moe` under-populated; "hybrid" ≠ MoE) →
    directional/underpowered; raw overall tps/GB is size-confounded.
22. **Org/maker effects must be size-controlled (`full_org_effects.py`).** The raw
    per-maker quality ranking is a **size-mix artifact**: Cohere (2.76), LG (2.63),
    DeepCogito, Mistral top it only because each contributed just 2 models, both
    7–8B (the largest allowed). Controlling for size (the 3–4B band where makers
    compete head-to-head), **Alibaba/Qwen dominates (2.85, n=16)**, ahead of IBM
    (2.52), Meta (2.51), Google (2.48), Microsoft (2.40); code-specialist makers
    (BigCode/StarCoder) are worst at ops. This **refines the frozen "IBM tops org
    quality"** — IBM leads the small/efficient bands, but **Qwen leads at matched
    size** on the full roster. *De-dup caveat (adversarial):* the raw n=16 was inflated
    by `qwen3:4b` quant variants; collapsed to distinct bases the Qwen lead survives
    but shrinks (2.75 over 6 bases), so the honest claim is "the qwen3:4b line leads,"
    not broad Qwen superiority. (Instruction-tuning has no clean test here: the ops
    roster is all instruct/chat by curation, with no true base/pretrained siblings.)
23. **Task difficulty vs discrimination (`full_task_difficulty.py`).** *(CORRECTED:
    now uses the authoritative scenario `class` field, not name prefixes — the earlier
    "toolcall" was a mislabel; its class is `test`.)* Strong difficulty–discrimination
    tradeoff (Spearman **+0.88**): the hardest classes floor every model, while
    mid-difficulty classes separate best — **`guard` (SD 0.98), `test` (0.94, 3
    scenarios), `monitor`, `diagnose` (0.84, 5 scenarios)**. Two near-floor scenarios
    (`detect-01-crashloop-triage`, `secure-14-injection-destructive`) should be
    revised. (Most classes are thin, 1–5 scenarios → indicative.)
24. **Adversarial validation of the re-center (`full_adversarial_review.py`).** The
    foundation was attacked and mostly holds: (a) the full run's two judges **agree**
    (quad-κ **0.853**, within-1 98.6%, r 0.86 over 15,200 rows) — solid, though below
    the frozen newer-judge 0.92, and with a disclosed systematic **claude 2.21 vs gpt
    2.07 bias** (0.14; the consensus mean absorbs it); (b) the **energy axis is clean**
    — `corr(thermal_start, energy) = +0.015` within-model (only 4/152 exceed |0.3|),
    thermal start is stable 48–62°C, so **no detected linear start-temp association**
    (run order not separately tested; energy is CPU-package / RAPL package-0 only); (c)
    the org lead **survives de-duplication** (above). **Standing
    limitations (honest):** MoE n=2 and the reasoning pairs (~4 lineages) are
    underpowered; p-values across the ~8 axes are **not multiple-comparison-corrected**,
    so the marginal ones (tools p=0.018) are suggestive not confirmatory;
    metadata covers 138/152 with name-heuristic fallbacks; the run is a single
    environment / single collection and is still `provisional` (older judges).
25. **Dropping the truncated models does not move the headline
    (`full_truncation_sensitivity.py`).** The cheap alternative to a de-truncation
    re-run: **92/152** models truncated ≥1 row (18 >20%, 2 at 100%); dropping every
    model above a truncation threshold keeps **60** (0%), **103** (≤5%), **123**
    (≤10%). Across full-152 → ≤10% → ≤5% → 0% the **relative findings stay put** —
    same #1 (`qwen3:4b-instruct-2507-q8_0` q=3.59), tools **+0.44→+0.33**, scale
    **ρ 0.73→0.74**, safety~quality **r 0.92→0.91** — and the **top-5 are all 0–1%
    truncated**, so the best-model story never rested on the truncated set. The only
    thing that moves is **absolute mean quality (2.14 → 2.44** at the strict cut),
    because the dropped models are smaller (median 2.0B vs 3.0B) and lower-quality
    (mean 1.94 vs 2.44) — the same "genuinely weak" population as finding 19, so the
    drop is a **selection bias to disclose**, not a clean-up. **Use as a robustness
    subset; keep the full 152 as primary.**

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
