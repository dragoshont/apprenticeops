# Paper Intent Memo

Status: Draft intent memo for peer alignment before submission writing.

## Title (working)

ApprenticeOps: Evaluating Small Locally-Sovereign LLMs for Homelab Operations Reasoning

## Problem and motivation

Small local LLMs are attractive for homelab/edge operations because they are cheap,
private, and always available, but current evidence is weak on whether they can
reason safely and usefully on real operations tasks without cloud fallback.

## Core claim (the thesis the paper proves) — reframed 2026-06-19

> Supersedes the safety-led claim locked 2026-06-18; see
> [`PAPER_POSITIONING.md`](PAPER_POSITIONING.md) for the decision and the
> competing-work scan that motivated it (the safety finding is saturated in the
> literature, so it cannot lead).

For a **locally-sovereign** ops assistant — offline (no frontier to escalate to),
CPU-only, ≤5 GB, the last line — **model selection is the whole game, and every
proxy a practitioner reaches for (parameter count, benchmark score, a “reasoning”
badge, perplexity) misleads on a *different* axis.** We profile **quality × safety
× energy together** on commodity offline hardware and reduce the choice to a
**measured Pareto front**. The three axes: a judged-quality knee at ~3-4B (where
*quantization*, not parameters, carries the lift); **safety** as the judge-free
deterministic refusal axis, governed by *training type, not size* — a result that
**corroborates** a saturated agent-/SLM-safety literature rather than discovering
it; and **energy** (Wh/answer, tok/s-per-watt) you pay to run it yourself. The
contribution is the **integration**: on the front, the “biggest” and “reasoning”
picks come out **dominated**.

## Top contributions (proposed)

1. ApprenticeOps benchmark artifact (scenario corpus + scoring + telemetry schema).
2. Controlled empirical results across 25 local models and 19 scenarios on one
   commodity node, with explicit uncertainty/statistical treatment.
3. **The three-axis selection map and its Pareto front** — quality × safety ×
   energy measured *together* for the offline/CPU model-selection decision, a
   regime no prior benchmark targets whole. Safety is **one axis** of three
   (judge-free deterministic refusal, governed by training type not size) and is
   presented as **corroboration** of the agent-/SLM-safety literature, not
   discovery; energy is the under-reported axis that prices capability above the knee.

## Wave-1 findings (data-grounded, 2026-06-18)

From the complete Wave-1 run (25 models × 19 scenarios; deterministic refusal/
check scores across 5 repeats, plus a deterministic single-judge quality pass):

1. **Knee at 3-4B.** Judged %-of-frontier rises 33 / 43 / 52 / 57 / 59 % across
   the 0-1B→4-5GB brackets; the 4-5GB bracket adds only +1.7 pt over 3-4B with
   overlapping CIs (pre-registered gate → **HOLD 4-5GB**). Best small model ≈ 74 %.
2. **Quant beats parameters at the knee.** A 4B at q4 (`qwen3:4b-...-q4_K_M`,
   71.6 %) ties its own q8 and beats `qwen2.5:7b` and a 6.9B Granite.
3. **Capability is perception-first.** Strong on detect/localize/monitor/test
   (80-100 %), weak on guard/expand/upgrade (38-55 %).
4. **Safety (axis #2) tracks training type, not size — a *replication*, not a discovery.** Guard+secure
   refusal by bracket: 62 / 67 / 79 / 82 / 73 % — peaks at 3-4B, **drops** at
   4-5GB. Reasoning/“thinking” models refuse at **43.9 % [36.7, 51.2]** vs
   instruct **75.0 % [73.1, 76.9]** (n = 60 vs 660). A 0.36B model (`smollm2:360m`,
   66 %) is safer than a 7.6B reasoning model (`deepseek-r1:7b`, 47 %). This rests
   on the **deterministic** refusal check (not the LLM judge) — methodologically
   cleaner and bias-free.
5. **`phi:2.7b` failed to serve** (95/95 DNF) — excluded as DNF, not performance.
6. **The headline is the integration: a quality × safety × energy Pareto.** Treating
   each model as a point in (judged quality ↑, refusal ↑, energy ↓), **8 of 24
   models are Pareto-optimal**; the other 16 are dominated. The “biggest” and
   “reasoning” picks land **off** the front — `deepseek-r1:7b` is simultaneously the
   least safe (47 %) and the most energy-expensive (303 mWh/answer). The selection
   short-list is found only by measuring all three axes together.

## Literature positioning (scan 2026-06-18)

- **Corroborates our R1/reasoning-unsafe headline:** Self-Jailbreaking
  (arXiv 2510.20956; the exact “rationalize harm” mechanism), Hidden Risks of R1
  (2502.12659), SafeChain (2502.12025). **Caveat:** claim “R1 distills *as
  shipped*” — RealSafe-R1 (2504.10081) / SAFEPATH (2505.14667) show it is fixable.
- **Non-monotonic safety:** Inverse Scaling (2306.09479), Perez model-written
  evals (2212.09251). **Pre-empt:** U-shaped scaling (2211.02011) → scope the
  claim to 0.5-8B and our task mix.
- **Scale isn’t destiny:** Chinchilla (2203.15556), ThinkSLM (2502.11569, quant
  preserves reasoning). **Emergence objection to defuse:** Wei (2206.07682) vs
  Schaeffer “Mirage” (2304.15004) → use graded, not binary, scoring.
- **Quant:** ACBench (2505.19433, q4 keeps tool/workflow), Quant-Meets-Reasoning
  (2505.11574, low-bit hard-math collapse — scope to q4/q8 + ops judgment).
- **The gap we fill:** AIOpsLab (2501.06706), ITBench (2502.05352; frontier solves
  only ~14 % SRE / 0 % FinOps), OpsEval (2310.07637, MCQ) — none occupy small +
  local + CPU + offline + real-incident + **quality × safety × energy measured
  together** + consistency.
- **Pro-SLM momentum (frame, don’t conflate):** NVIDIA 2506.02153, SLM survey
  2409.15790, Phi-3 2404.14219.

## Non-claims (explicit)

1. This paper does not claim autonomous self-healing or closed-loop operations.
2. This paper does not claim generalization to all infrastructure environments.
3. This paper does not claim wall-power or data-center efficiency equivalence.

## Evidence plan (claim -> evidence)

1. Performance/quality tradeoff:
   - Deterministic checks + LLM-judge scores with confidence intervals.
   - Paired comparisons by scenario and bracket.
2. Safety claim:
   - Guard-class refusal checks plus non-endorsement gates.
3. Grounding claim:
   - Closed-book vs grounded comparison, reported separately and in paired variants.
4. Systems claim:
   - Token throughput, TTFT, memory/swap behavior, and energy proxy telemetry.

## Risks to novelty or acceptance

1. Single-environment external validity limits broad claims.
2. LLM-as-judge bias must be openly disclosed and cross-checked.
3. Scenario expansion coverage is still uneven across classes.

## Target audience and venues

- Primary readers: systems/ML practitioners evaluating local LLM operations use.
- First release: arXiv preprint (moderated, **not** peer-reviewed — see
  [`REVIEWER.md`](../REVIEWER.md) for what that means and how to review this work).
- Submission targets: **NeurIPS Datasets & Benchmarks track** (single-blind
  allowed; code + data must be accessible to reviewers at submission; Croissant
  metadata) as the natural venue; MLSys / on-device & efficiency workshops as alternates.

## Readiness bar for submission

1. Claims-evidence table complete for every headline claim.
2. Statistical reporting and limitations sections are complete and consistent.
3. Reproduction path runs from clean checkout.
4. Artifact package inventory is complete and link-stable.

## Peer feedback requested now

1. Are the top 3 contributions differentiated enough from existing AIOps benchmarks?
2. Are any claims currently over-scoped versus available evidence?
3. Which single result would you require to consider this paper publishable?
