# DRAFT — Full-run re-analysis section (for review before integration into `PAPER.md`)

> Status: **draft for review — revised after a dual-family adversarial gate.**
> An independent Adversarial Judge pass (Claude Opus 4.8 = REVISE, GPT-5.6 Sol =
> FAIL) attacked an earlier version and found real defects, since fixed: a
> parameter-unit bug that had **inverted** the size finding, a survivorship-biased
> reasoning defense, pseudoreplicated p-values, a wrong "512-token cap" premise, a
> scenario-taxonomy mislabel, and over-stated equivalence/robustness claims. This
> revision incorporates those fixes and reports every result honestly, but it is
> **not yet promotable**: the primary data still lives outside the tracked tree and
> the bundle is `provisional`, and magnitude claims still await a re-judge with the
> paper's newer judges (see X.7). Reproduced by scripts in `deep-dive/`
> (`FINDINGS.md` 15–24).

## X.1 The full run and why it is the candidate primary dataset

`full-chatok-core20-r5-ollama-20260705-150053` is a single content-addressed
collection of **152 models × 20 scenarios × 5 repetitions = 15,200 rows**, each
judged by a two-model ensemble (`claude-opus-4.6` + `gpt-5.4`, 30,400 canonical
judgements), collected under **one operating point** (`cpu_no_turbo = 1`, RAPL
`package-0`, per-scenario token budgets of 400–700). Energy is present on 100% of
rows, so quality × safety × **CPU-package energy** are comparable across the same
152 models (25 → 152 models with comparable package energy).

The two full-run judges agree substantially (quadratic-weighted κ = **0.853**,
98.6% within one point, r = 0.86 over 15,200 rows), with a disclosed systematic
bias (`claude-opus-4.6` mean 2.21 vs `gpt-5.4` 2.07) that the consensus mean
absorbs. As an **exploratory** cross-check, a rank comparison against the frozen
94-model snapshot on 90 name-matched models gives Spearman 0.974 — this indicates
**rank stability only**; it is *not* a formal cross-run join (the frozen manifest
forbids joining on incomplete condition identity) and it cannot license the paired
**magnitudes** below, which require a same-output re-judge with `4.8`/`5.5`.
*(FINDINGS 15, 24.)*

## X.2 Scale: bigger helps; ~4B is the efficiency knee

*(Corrected — an earlier draft claimed "bigger doesn't win" from a parameter-unit
bug that mis-sized 15 sub-1B models as 100–1000B.)* With parameters read from the
canonical `param_count`, quality **rises with size**: mean quality by band is 1.81
(<3B), 2.44 (3–6.5B), and **2.84 (≥6.5B)**, with **Spearman(params, quality) =
0.73**. Size is therefore *not* irrelevant. What survives is a narrower, efficiency
claim: the single best model is a **4B** (`qwen3:4b-instruct-2507`, 3.59, edging
`qwen3:8b` 3.51 at **~equal energy** — 0.160 vs 0.161 Wh, a tie, not a saving), so
~4B is a strong quality-per-cost operating point on the efficiency frontier — but
larger models are, on average, better. *(FINDINGS 15.)*

## X.3 Training and inference choices

**Tool-training is associated with higher quality.** Among models with known
tool-capability metadata, tool-capable models score **+0.44 quality (p = 0.006)**;
models with unknown metadata are excluded rather than treated as non-tool. This is
an observational association (annotation-based), not a controlled contrast.
*(FINDINGS 16.)*

**Thinking/reasoning mode underperforms at a small token budget — directional, and
mostly a fit effect.** Flipping only the mode on same-lineage pairs (Qwen3-4B at
two quants, Phi-4-mini, Qwen2.5-3B→SmallThinker*, EXAONE→Deep*), and testing at the
**lineage level** (n ≈ 4 distinct lineages — Qwen3-4B Q8/Q4 are one lineage), the
thinking variant is **−0.40 quality at the per-scenario budget, which is NOT
statistically significant (paired t p = 0.19)**. On **matched** non-truncated cells
(instruct restricted to the same scenarios/reps where the thinking variant did not
truncate) the gap halves to −0.24 (p = 0.30), and the two clean mode-flip pairs
(Qwen3-4B, Phi-4-mini) are ≈ 0.00 — the residual is driven by the near-match
EXAONE-Deep (−0.80). The mechanism is budget exhaustion: thinking truncates ~74% of
cells against per-scenario budgets of 400–700 tokens. **Honest reading:** thinking
mode is a poor fit for tight bounded-ops budgets, but the evidence that it degrades
*reasoning quality* is weak and underpowered — the queued budget-sensitivity re-run
(higher `max_tokens`) is the confirmation. *(FINDINGS 17; `full_reasoning_pairs.py`.)*

**Quantization to Q4 has a small, real, practically-minor quality cost.** Across 16
same-base high-precision-vs-Q4 pairs, Q4 costs **−0.09 quality (95% CI [−0.14,
−0.04], paired t p = 0.003)** — statistically non-zero, but **practically
equivalent** within a ±0.25 margin (TOST established) — while buying **0.66× size,
1.42× decode speed, 0.70× energy**. It is *not* a blanket "free lunch": across the
16 pairs Q4's safety delta averages −0.08 and reaches **−0.56** (`qwen3:4b`), with
3/16 pairs losing more than 0.2 safety. Q4 is a good default for quality/efficiency;
safety-critical deployments should verify the specific Q4 variant. *(FINDINGS 20;
`full_quant_pairs.py`.)*

## X.4 Architecture: MoE efficiency (case study, underpowered)

The two reliably-tagged MoE models decode **faster than their footprint predicts**
— a size→speed roofline residual of **+0.87 vs −0.02** for dense — and win within
the Granite family on decode-tokens-per-GB (5.2 vs 3.7). This is reported
**descriptively as a case study with no significance test** (n = 2 is far too few),
consistent with the controlled-scope roofline result. The apparent MoE quality edge
is confounded (different models) and not claimed; raw tokens-per-GB is
size-confounded (the residual is the correct metric); few small MoE exist and
"hybrid" ≠ MoE, so uncertain labels are not forced. *(FINDINGS 21; `full_moe_dense.py`.)*

## X.5 Makers: rank at matched size (de-duplicated)

Per-maker quality must be size-controlled *and* de-duplicated. Raw maker means are a
size-mix artifact (Cohere, LG, DeepCogito, Mistral top it only via two 7–8B models
each). Within the 3–4B band, de-duplicated to distinct base models (quant variants
of `qwen3:4b` had inflated the raw count), **Alibaba/Qwen still leads (2.75, 6
bases)**, ahead of TII (2.49), Microsoft (2.40, 7 bases), Meta (2.34). The honest
claim is that **the qwen3:4b line leads at matched size**, not broad Qwen
superiority. Instruction-tuning could not be tested — the roster is all instruct/chat
by curation. *(FINDINGS 22; `full_org_effects.py`.)*

## X.6 The scenario suite: difficulty vs discrimination (authoritative taxonomy)

Using the scenario set's authoritative `class` field (not name prefixes — an
earlier draft mislabeled `toolcall-20`, whose class is `test`), difficulty and
discrimination correlate strongly (Spearman **+0.88**): the hardest classes floor
every model and carry little information, while mid-difficulty classes separate best
— **`guard` (SD 0.98), `test` (0.94, 3 scenarios), `monitor`, `diagnose` (0.84, 5
scenarios)**. Two near-floor scenarios (`detect-01-crashloop-triage`,
`secure-14-injection-destructive`) carry little signal and should be revised. Most
classes are thin (1–5 scenarios), so class-level numbers are indicative.
*(FINDINGS 23; `full_task_difficulty.py`.)*

## X.7 Threats and what must happen before integration

- **Not yet reproducible / not paper-eligible.** The primary results and 30,400
  judgements are read from gitignored `.tmp/`; the bundle is `claim_status =
  provisional`. Before integration the canonical bundle must be committed to the
  tracked archival path and claim-locked.
- **Judge provenance and magnitudes.** The full run used `claude-opus-4.6` +
  `gpt-5.4`. The 0.974 cross-check validates *ranking only*; every paired magnitude
  (−0.40, −0.09, +0.44, +0.87) requires a **re-judge of the same outputs with
  `4.8`/`5.5`** (queued, zero node cost) before it is a primary claim.
- **Judge validity ≠ agreement.** κ = 0.853 measures consistency, not correctness;
  two frontier judges share priors, so the consensus is one correlated ensemble.
  The committed human-eval packets are unscored and should be scored.
- **Energy scope.** Energy is CPU-package (RAPL `package-0`) only; DRAM/system energy
  is excluded (and is size-correlated, so it specifically bounds the MoE-efficiency
  and cross-model energy claims). Scope the energy claim to CPU-package.
- **Power / multiplicity.** MoE (n = 2) and reasoning (~4 lineages) are underpowered
  and reported directionally; p-values across ~8 axes are not family-wise corrected,
  so marginal results are suggestive, not confirmatory.
- **Reliability censoring.** 208 DNF + 1,452 length-censored rows across 21 models
  are retained as separate strata; the ongoing 21-model timeout-sensitivity run
  addresses the timeout question directly.

## X.8 Reproduce

```
cd deep-dive
.venv/bin/python full_report.py            # X.1-X.2
.venv/bin/python full_reasoning_pairs.py   # X.3 reasoning (matched, lineage-level)
.venv/bin/python full_quant_pairs.py       # X.3 quantization (paired-t + TOST)
.venv/bin/python full_moe_dense.py         # X.4 MoE (descriptive)
.venv/bin/python full_org_effects.py       # X.5 makers (de-duplicated)
.venv/bin/python full_task_difficulty.py   # X.6 suite (authoritative taxonomy)
.venv/bin/python full_truncation_scan.py   # budget-victim triage
.venv/bin/python full_adversarial_review.py # foundation attacks
```
