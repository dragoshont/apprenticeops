# DRAFT — Full-run re-analysis section (for review before integration into `PAPER.md`)

> Status: **draft for review.** This section re-centers the empirical results on the
> single-collection `full-chatok-core20-r5` run (152 models, one controlled regime).
> It does **not** overwrite the frozen 94-model paper-era results; on integration it
> becomes the primary results section, with the frozen two-batch snapshot repositioned
> as the pre-registered pilot / robustness cross-check. Every claim below is reproduced
> by a committed script in `deep-dive/` and recorded in `deep-dive/FINDINGS.md` (items
> 15–23). Adversarial caveats are kept inline on purpose — they are what make each
> claim defensible.

## X.1 The full run and why it is the primary dataset

The `full-chatok-core20-r5-ollama-20260705-150053` bundle is a single, content-addressed
collection of **152 models × 20 scenarios × 5 repetitions = 15,200 primary rows**, each
judged by a two-model ensemble (`claude-opus-4.6` + `gpt-5.4`, 30,400 canonical
judgements). Critically, **every one of the 15,200 rows was collected under one operating
point** — `cpu_no_turbo = 1`, RAPL `package-0`, base clock — with a valid
`power.energy_wh` on 100% of rows. This removes the cross-batch power-regime confound that
constrained the two-batch snapshot: quality, safety, and **energy** are all comparable
across the same 152 models simultaneously (25 → 152 models with comparable energy).

The re-center does not overturn the prior ranking: on the 90 models shared with the frozen
snapshot, the two rankings correlate at **Spearman 0.974** despite a judge-version change
(4.6/5.4 vs 4.8/5.5) and a prompt-format change — the model ordering is robust to both. The
two full-run judges themselves agree substantially (quadratic-weighted κ = **0.853**, 98.6%
within one point, r = 0.86 over 15,200 rows), with a small disclosed systematic bias
(`claude-opus-4.6` mean 2.21 vs `gpt-5.4` 2.07) that the consensus mean absorbs.
*(FINDINGS 15, 24; `full_report.py`, `full_adversarial_review.py`.)*

## X.2 Scale: the ~4B sweet spot, and diminishing returns

Over the full spectrum, capability plateaus well before the largest models tested. Mean
quality by size band is 1.90 (<3B), **2.42 (3–6.5B, best)**, and 2.16 (≥6.5B), and the
overall correlation between parameters and quality is weak (Spearman 0.14–0.32). The best
~4B instruct model outscores every 7–8B model in the pool. For bounded CPU operations,
parameters past ~4B do not pay for themselves. *(FINDINGS 15; `full_report.py`.)*

## X.3 Training and inference choices

**Tool-training helps.** Models trained for tool use score **+0.37 quality (p = 0.018)**
over those that are not — the effect reproduces on the full roster. *(FINDINGS 16.)*

**Thinking/reasoning mode is a poor fit for a tight budget — not worse reasoning.** Holding
the base model fixed and flipping only the mode (five same-lineage instruct↔thinking pairs:
Qwen3-4B ×2, Phi-4-mini, Qwen2.5-3B→SmallThinker, EXAONE), thinking loses **−0.42 quality**
at a fixed 512-token cap (paired *t* p ≈ 10⁻⁶). **But this is largely a token-budget
artifact.** Both modes share the 512 cap; thinking variants exceed it **74–100%** of the
time, generate 2.2× the tokens, and use 2.3× the energy. On the answers where thinking
*finishes*, **three of five pairs match or beat their instruct sibling** (mean Δ −0.07). The
honest claim is therefore about **fit**: thinking mode exhausts a tight token/latency budget
before answering on bounded ops tasks — it is not that its reasoning is worse. The effect is
largest on `toolcall` (−1.50) and neutral on `secure`. The one genuine exception is
EXAONE-Deep (worse even when it finishes; also the least-matched pair). A budget-sensitivity
re-run at higher `max_tokens` (`data/models.reasoning-budget-v1.txt`) is queued to confirm
the penalty collapses as the budget grows. *(FINDINGS 17; `full_reasoning_pairs.py`.)*

**Quantization to Q4 is close to free on quality.** Across 16 same-base high-precision-vs-Q4
pairs, Q4 costs **−0.09 quality** — a mean absolute delta of 0.12, far below the median
within-model repetition SD of 0.89, i.e. **statistically indistinguishable** — while buying
**0.66× size, 1.42× decode speed, 0.70× energy**. Q4 is the correct default. *Caveat:* Q4
can reduce **safety** more than quality on some strong models (`qwen3:4b`, −0.56 safety),
so safety-critical deployments should verify the specific Q4 variant. *(FINDINGS 20;
`full_quant_pairs.py`.)*

## X.4 Architecture: MoE is an efficiency story

Mixture-of-experts models decode **faster than their footprint predicts** — a size→speed
roofline residual of **+0.87 vs −0.02** for dense models (p = 0.043) — and win within the
Granite family on decode-tokens-per-GB (5.2 vs 3.7), reproducing the controlled-scope
roofline result. The apparent MoE quality advantage (+0.22) is confounded (MoE and dense are
different models) and is *not* claimed. *Caveats:* only two small MoE models are reliably
metadata-tagged (few small MoE exist; "hybrid" ≠ MoE, and uncertain labels were not forced),
so the efficiency result is directional and underpowered; raw tokens-per-GB is
size-confounded and the roofline residual is the correct size-controlled metric.
*(FINDINGS 21; `full_moe_dense.py`.)*

## X.5 Makers: rank at matched size

Per-maker quality **must be size-controlled**. The raw ranking is a size-mix artifact —
Cohere, LG, DeepCogito, and Mistral top it only because each contributed just two models,
both 7–8B (the largest allowed). Within the 3–4B band, where makers compete head-to-head,
**Alibaba/Qwen dominates (2.85, n = 16)**, ahead of IBM (2.52), Meta (2.51), Google (2.48),
and Microsoft (2.40); code-specialist makers (BigCode/StarCoder) are worst at ops. This
refines the pilot's "IBM tops org quality": IBM leads the small/efficient bands, but Qwen
leads at matched size on the broader roster. Instruction-tuning could not be tested — the ops
roster is entirely instruct/chat by curation, with no base/pretrained siblings. *De-dup
caveat:* Qwen's raw band count was inflated by `qwen3:4b` quant variants; collapsed to
distinct base models the Qwen lead survives (2.75, 6 bases) but narrows, so the honest claim
is that the qwen3:4b line leads rather than broad Qwen superiority.
*(FINDINGS 22; `full_org_effects.py`.)*

## X.6 The scenario suite: difficulty vs discrimination

Task difficulty and discrimination are strongly, and inconveniently, correlated
(Spearman **+0.84**): the hardest classes (`detect` 1.44, `expand`, `upgrade`) **floor
every model** and thus carry little information, while mid-difficulty tasks separate models
best. **`toolcall` is the single most discriminating class** (between-model SD 1.29) — the
same axis where thinking mode is most harmful — making tool-calling the central
differentiator of the suite. Two near-floor scenarios (`detect-01-crashloop-triage`,
`secure-14-injection-destructive`) carry little signal and should be revised. *(FINDINGS 23;
`full_task_difficulty.py`.)*

## X.7 Threats specific to the re-center

- **Judge provenance.** The full run used `claude-opus-4.6` + `gpt-5.4`, older than the
  frozen paper's `4.8`/`5.5`. The 0.974 cross-version rank agreement (X.1) is the defence;
  a re-judge of the 15,200 rows with the newer judges is available at zero node cost if a
  strict version match is required.
- **Claim status.** The bundle is gate-passed and content-addressed but `provisional`;
  promotion to canonical requires its own locks and an independent GPT- and Claude-family
  review.
- **Roster gap.** `deepseek-r1` (the pilot's "reasoning hurts" driver) is absent from the
  full run; the pilot carries the R1-specific claim, or it is reframed as the budget-fit
  finding in X.3.
- **Reliability censoring.** 208 rows are DNF and 1,452 are length-censored across 21
  affected models; these are retained as separate strata, and the ongoing 21-model
  timeout-sensitivity follow-up addresses the timeout question directly.
- **Energy integrity (validated).** Within one regime the energy axis is not order- or
  thermally-confounded: thermal start is stable (48–62 °C) and the within-model correlation
  between thermal start and energy is +0.015 (only 4/152 models exceed |0.3|), confirming the
  quiesce-between-models control works.
- **Multiple comparisons.** Roughly eight axes were tested without a family-wise correction;
  the strongly-significant results (reasoning p≈10⁻⁶, quantization) are robust, but the marginal
  ones (MoE p=0.043, tools p=0.018) should be read as suggestive, not confirmatory.
- **Statistical power.** The MoE contrast (n=2 reliably-tagged) and the reasoning matched
  pairs (~4 distinct lineages) are underpowered; they are reported directionally with the
  confirmation run queued.

## X.8 Reproduce

```
cd deep-dive && .venv/bin/python full_report.py            # X.1–X.2
.venv/bin/python full_reasoning_pairs.py                   # X.3 reasoning
.venv/bin/python full_quant_pairs.py                       # X.3 quantization
.venv/bin/python full_moe_dense.py                         # X.4 MoE
.venv/bin/python full_org_effects.py                       # X.5 makers
.venv/bin/python full_task_difficulty.py                   # X.6 suite
.venv/bin/python full_truncation_scan.py                   # budget-victim triage
```
