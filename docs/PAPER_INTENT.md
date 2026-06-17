# Paper Intent Memo

Status: Draft intent memo for peer alignment before submission writing.

## Title (working)

ApprenticeOps: Evaluating Small Locally-Sovereign LLMs for Homelab Operations Reasoning

## Problem and motivation

Small local LLMs are attractive for homelab/edge operations because they are cheap,
private, and always available, but current evidence is weak on whether they can
reason safely and usefully on real operations tasks without cloud fallback.

## Core claim (what this paper aims to prove)

A reproducible benchmark on real homelab incidents can identify the practical
reasoning and safety floor of <=5 GB local models on commodity CPU hardware,
including where retrieval helps and where it does not.

## Top contributions (proposed)

1. ApprenticeOps benchmark artifact (scenario corpus + scoring + telemetry schema).
2. Controlled empirical results across 25 local models and 19 scenarios on one
   commodity node, with explicit uncertainty/statistical treatment.
3. Safety and grounding findings: refusal behavior is non-monotonic by model size,
   and grounded context materially changes outcomes for some task classes.

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
- First release: arXiv preprint.
- Submission targets: workshop track in MLSys / NeurIPS-adjacent efficient/on-device/ops venues.

## Readiness bar for submission

1. Claims-evidence table complete for every headline claim.
2. Statistical reporting and limitations sections are complete and consistent.
3. Reproduction path runs from clean checkout.
4. Artifact package inventory is complete and link-stable.

## Peer feedback requested now

1. Are the top 3 contributions differentiated enough from existing AIOps benchmarks?
2. Are any claims currently over-scoped versus available evidence?
3. Which single result would you require to consider this paper publishable?
