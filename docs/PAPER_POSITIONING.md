# Paper positioning — decision: one sovereign-first paper

> **Status:** Accepted 2026-06-19. **Amended 2026-07-23** (see
> [Amendment below](#amendment-2026-07-23--two-dual-family-gates-refine-the-framing)):
> two dual-family (GPT + Claude) adversarial gates refined the framing — the
> *collinearity-as-primary* claim was **REJECTED**, and the *"sovereign
> deployability"* relabel + ΔE-flagship was **REVISED**. The paper keeps the
> three-axis **selection** spine but promotes the **survivorship-robust completion
> cliff** as the empirical headline and demotes ΔE to future-work.
> Supersedes the implicit "safety is the spine"
> framing introduced in the [`PAPER.md`](./PAPER.md) Abstract/§1 rewrite (commit
> `1d4845f`) and the "two-paper" idea. This is a positioning ADR; it tells
> [`PAPER_PHASES.md`](./PAPER_PHASES.md) and `PAPER.md` how to frame the claim.

## Amendment 2026-07-23 — two dual-family gates refine the framing

Between the 2026-06-19 decision and today, two positioning candidates were run
through the **dual-family Adversarial Judge** (an independent GPT-family and
Claude-family verdict on each). Both were caught over-reaching. This amendment
records the outcomes and the framing the evidence actually supports; the original
ADR below stays as the historical record and is still correct on the spine
(sovereign-first, three-axis *selection*, safety corroborating).

### Gate 1 — "make the safety↔quality collinearity the primary claim" → **REJECT** (both families)

A proposal to lead with *"safety and quality are near-collinear (r ≈ 0.97) in
small local ops models"* was rejected by both judges as **not a defensible primary**:

- **Part-whole inflation.** Safety is a judge mean over the guard+secure *subset*;
  quality is a judge mean over *all* scenarios — they share rater and rows, so the
  correlation is mechanically inflated (r 0.970 → 0.953 on disjoint rows →
  ~0.84–0.89 once the shared-rater variance is removed).
- **Range restriction** hides the *top-tier* trade-off (the co-leaders where the
  choice actually bites); **43 %** of models still fail `guard-08`, so "safe ≈ good"
  is false where it matters.
- **Unfalsifiable / retroactive / non-novel** as framed.

**Primary claim is therefore the confound-controlled tool-training effect**
(`b3_mixedeffects`: **+0.31 quality, model-clustered p = 0.001**, replicates
94 → 152) — a **BH-exempt primary *statistic***, labelled **corroborating, carries
no novelty** (per the gate). Safety stays axis #2, corroborating.

### Gate 2 — "reframe the novelty as *sovereign deployability*, flagship = ΔE" → **REVISE** (both families)

The instinct (pivot novelty to *quantities/regime nobody measures*) was judged
correct; the **packaging over-reached on three axes**:

| Over-reach | Why it fails | Fix |
|---|---|---|
| **"Sovereign deployability / completion-under-envelope" as a *new quantity*** | The concept is **occupied**: EdgeReasoning (2511.01866) already optimizes reasoning-vs-non-reasoning accuracy under edge latency/token/power/**energy** budgets; Rethinking-Scale (2604.19299) already reports a **"Completion Rate"** excluding timeouts across 27 SLMs; goodput/SLO (2410.14257) is established. That literature is **serving-side**. | Reposition as a **model-*selection* signal**, not a new metric; cite the occupied cluster explicitly. |
| **ΔE (energy cost of a safety constraint) as the flagship** | **Blocked + internally contradicted**: RAPL package-0 excludes DRAM while decode is memory-bandwidth-bound, so ΔE would price safety on the component the mechanism says isn't where the energy is. Uncomputed; needs held-out data. "Heaviest weight on the least-ready leg." | **Demote to pre-registered future-work** with a DRAM-*bounded* estimate. Never the flagship. |
| **"The proxies *systematically mislead* on deployability"** (all three) | Holds for **one** of three. Reasoning-badge → misleads (clean). **Param-count → contradicted by finding 9** (quality *rises* with size, ρ = 0.73). Benchmark-score → **category error** (our instrument is underpowered to rank the top tier ≠ "scores mislead"). | **Retire "all proxies mislead."** Keep the sharper committed claim: each proxy misleads on a **different, named** axis; drop the param-count-misleads-on-quality leg. |

Plus: the **−42 pp completion gap** was not analysis-lock clean — it
double-weighted the qwen3-4B lineage (Q4 + Q8) and folded in a **>5B** EXAONE pair.
**Fixed 2026-07-23** in [`reasoning_budget_reanalysis.py`](../deep-dive/reasoning_budget_reanalysis.py):
lineage-clean, ≤5B only, one weight per lineage, scenario-clustered bootstrap CIs →
**qwen3-4B −62 pp [−76,−46], Phi-4-mini −11 pp [−24,−1]** (n = 2 clean lineages → a
**range, not a point**; EXAONE-7.8B −36 pp shown out-of-population). The cliff
tracks **measured verbosity** (median output tokens ≥ 800), **not the "thinking"
badge** — `smallthinker` (badge, terse) completes 100 %; `starcoder2` (no badge,
runaway) fails 41 %.

### The framing the evidence supports (adopted)

> **Goodput-gated model *selection* for locally-sovereign CPU ops agents.** On
> commodity offline hardware you pay for yourself, the model-selection proxies
> (parameter count, benchmark score, a "reasoning" badge) each fail on a
> **different named axis**; the decisive, under-measured one is **whether the model
> finishes the real ops task within a self-paid watt-and-second envelope**. We show
> a **survivorship-robust (ITT / competing-risks) completion cliff** — instruct
> lineages finish ~100 %, verbose long-chain lineages 34–89 % — on **real GitOps
> incidents**, couple it to **deterministic destructive-action safety** and
> (bounded) energy, and **release the harness**. The contribution is the
> **integration + regime + the selection-time completion statistic** — not any
> single axis, not a new "deployability" lens, not ΔE.

**The defensible delta (what we own vs the crowded space):** **selection**, not
serving/orchestration (EdgeReasoning, LMEdge) · **real GitOps incidents**, not
synthetic/mobile/medical · **survivorship-robust ITT / competing-risks** treatment
of the informative (MNAR) 600 s censoring — the genuine **methods contribution** ·
**coupled deterministic action-safety** · the **≤5B / CPU / offline / commodity
2018 hardware** regime.

### Required revisions (the durable checklist)

1. **Keep the committed three-axis *selection* spine** (this ADR + `PAPER.md`).
   **Do not** rename it "deployability."
2. **Promote COMPLETION to the empirical headline, honestly scoped:** report it as
   **ITT / goodput at envelope E₂ = (4096 tok, 600 s) on the 2018 i5-8350U**; state
   the joint-envelope confound and the wall-binding mechanism; disaggregate
   verbosity-vs-"thinking." Position **explicitly** against goodput-serving
   (2410.14257) and edge-SLM benchmarks as *"selection signal, not serving
   optimization; ITT/competing-risks, not survivor means."*
3. **Demote ΔE** to scoped future-work with a DRAM-bounded estimate — never flagship.
4. **Retire "all proxies mislead."** Keep per-axis, per-proxy: reasoning-badge →
   completion + safety; param-count → energy-above-the-knee (the blocked axis);
   benchmark → top-tier resolution. Drop the param-count-on-quality leg (finding 9).
5. **Keep tool-training** as the pre-registered **BH-exempt primary statistic**
   (corroborating, not novelty); **safety** corroborating.
6. **Scope honestly:** single-environment **case study** + released harness; n = 2
   clean ≤5B reasoning lineages; one 2018 CPU; 20 scenarios.

### Literature to cite / differentiate against (surfaced by the gates)

- **Nearest occupants (serving/benchmarking, cite as "occupied, but serving-side"):**
  EdgeReasoning 2511.01866 · Rethinking-Scale 2604.19299 · goodput/SLO 2410.14257 ·
  MobileAIBench 2406.10290 · PalmBench 2410.05315 · SLM-Bench 2508.15478 ·
  "Tiny Models, Tough Limits" (edge-budgeted protocol for security-critical tasks).
- **Nearest *adjacent/competing* (differentiate hard):** **MAM-AI 2606.29580** —
  on-device 4B medical RAG that independently finds a model **"cannot be both
  helpful and safe,"** judge-validated + released harness. Differentiate: it is
  medical RAG, a single 4B, not ops/agentic, no 152-model sweep, no
  completion-under-envelope / competing-risks.

**Venue:** **NeurIPS D&B** (best conditional fit — released benchmark + failure
taxonomy + human validation) or **SIGMETRICS** (after whole-system/DRAM-inclusive
energy + a second hardware point). **MLSys main = likely reject today** (EdgeReasoning
has stronger systems modeling + artifact). arXiv / efficient-ML workshop is credible now.

> **What this supersedes in the original ADR below:** the "new headline result =
> energy × safety × quality Pareto / *what does the safe model cost in watts*" (the
> ΔE framing) is **demoted**; the thesis's "each proxy misleads" is **kept but
> sharpened** to per-named-axis with the param-count leg dropped; the **completion
> cliff** is the promoted empirical headline. `claim_status` is unchanged
> (`provisional`); nothing here is promoted without a human gate.

## Context

The manuscript had drifted into *two* latent papers — a **behavioural safety
finding** ("reasoning-distillation degrades destructive-action refusal in small
local models") and a **measurement artifact** (a CPU-only telemetry + judge
harness). Before committing, we ran an adversarial literature scan to test
whether the safety finding is novel enough to lead — or to stand alone.

**It is not.** Every individual pillar of the safety thesis is already published,
typically at larger scale and stronger venues, frequently on the same
Qwen3/DeepSeek/Gemma families. The scan (arXiv, 2026-06-19) is summarised below.
A standalone safety paper would be **corroboration, not discovery**, and would be
out-scaled (our 19 scenarios / n=1 environment vs 150–17,420-item benchmarks).

### What is already covered (the reason *not* to lead with safety)

| Claim we might have led with | Already established by | Venue |
|---|---|---|
| **Text-refusal ≠ tool-call/action refusal** | GAP, *"Text Safety Does Not Transfer to Tool-Call Safety in LLM Agents"* — arXiv 2602.16943 (17,420 datapoints) | 2026 |
| Agents **harming their own deployer**; deterministic post-audit verifier + gate | Owner-Harm — arXiv 2604.18658; OS-Harm — arXiv 2506.14866 (automated judge, 0.76/0.79 F1 vs human) | OS-Harm: **NeurIPS 2025 D&B Spotlight** |
| Refusing **malicious agent actions** at scale | AgentHarm — arXiv 2410.09024 (440 tasks); AgentHazard — arXiv 2604.02947 (2,653) | AgentHarm: **ICLR 2025** |
| **Small models** unsafe; *compression / quantization / distillation* degrade safety | "Beyond the Tip of Efficiency" — arXiv 2502.19883 (13 SLMs) | **ACL 2025** findings |
| **Reasoning-distillation** degrades safety | Self-Jailbreaking — arXiv 2510.20956 (names DeepSeek-R1-distilled); Hidden Risks of R1 — 2502.12659; SafeChain — 2502.12025 | Self-Jailbreaking: **ICLR 2026** |
| **Quantization** degrades safety | Q-resafe — arXiv 2506.20251; Critical-Weight-Protection — 2601.12033 | Q-resafe: **ICML 2025** |
| **Perplexity is a misleading deployment-readiness proxy** | Safety-Preserving PTQ (CAQ) — arXiv 2511.07842 (states this almost verbatim) | 2026 |
| **SLM-as-judge / deterministic eval** | Luna-2 — arXiv 2602.18583; OS-Harm automated judge | 2026 |

> **Honesty (state up front):** "reasoning models are unsafe," "small/quantized
> models are unsafe," "action-safety ≠ text-safety," "don't trust perplexity,"
> and "use a deterministic verifier + LLM-judge" are **each already known.** Our
> safety numbers *replicate* them in a new regime; they do not discover them.

## Decision

**Ship one paper, framed on *local sovereignty*.** Sovereignty (offline = no
external *model* API; the model is the **last line**; runs on **commodity CPU**)
is the spine that *binds three axes into a single contribution*:

1. **Reasoning floor / quality** — can a ≤5B-parameter offline model reason about real ops, and what footprint does that deployment require?
2. **Safety** — will it refuse destructive actions when *there is no frontier to
   escalate to and no reviewer downstream*? (corroborates the literature above)
3. **Energy / fit** — what does running it *yourself* cost in Wh/answer, tok/s,
   thermal headroom on hardware you own?

No prior work measures **all three together for the model-selection decision in
the offline/CPU/locally-sovereign regime.** That integration — not any single
axis — is the contribution.

### The thesis (reframed, sovereign-first)

> *For a **locally-sovereign** ops assistant — offline, CPU-only, and, for the current doctoral protocol, ≤5B parameters, the last
> line with no frontier to escalate to — the model-selection proxies a
> practitioner reaches for (parameter count, benchmark score, a "reasoning" badge,
> perplexity) each mislead, and they mislead on **different axes**: a "reasoning"
> model can win on diagnosis yet be the **least safe**; a bigger model can cost
> 3× the energy for no judged lift; quantization can preserve quality while
> training type governs safety. We profile **quality × safety × energy** in one
> reproducible harness on commodity offline hardware, so the choice is made on
> **measured behaviour**, not a proxy.*

Safety is **axis #2**, presented as *"the known reasoning/quant safety
degradation replicates offline — and here is its energy/Pareto cost,"* citing
GAP / Owner-Harm / Beyond-the-Tip rather than claiming the phenomenon.

## What is genuinely new (the defensible delta)

1. **The regime no one targets together:** small open-weight models up to the 5B-parameter thesis target, **quantized, CPU-only, fully
  offline / locally-sovereign**, **commodity 2018 hardware** — the agent-safety
   benchmarks run frontier/cloud or GPU-edge models.
2. **The integration:** safety measured *beside* **energy (Wh/answer,
   tok/s-per-watt), the 3–4 B quality knee, and roofline cross-hardware transfer**
   in one harness. No safety paper measures energy/thermal/roofline; no systems
   paper measures destructive-action refusal. The novel question is **"what does
   choosing the *safe* model cost you in watts and tokens/s?"**
3. **Real GitOps incidents** (SOPS/ESO/Flux/Cloudflare), not synthetic agent
   tasks — provenance the agent-safety benchmarks lack.
4. **Deterministic, judge-free** destructive-action checks as a cheap safety
   signal, cross-validated by a two-judge ensemble (κ_quad ≈ 0.91) — a
   methodology contribution adjacent to OS-Harm's automated judge.

## Consequences (what changes in `PAPER.md`)

- **Abstract + §1:** re-lead with **sovereignty + the three-axis selection
  problem**; the safety result moves from the headline to "one of three axes."
- **§8b safety:** reframe as *replication + cost* — keep the numbers, but cite
  GAP (2602.16943), Owner-Harm (2604.18658), Beyond-the-Tip (2502.19883),
  Q-resafe (2506.20251); drop any "we discover" tone.
- **New headline result:** the **energy × safety × quality Pareto** (the white
  space). Promote the Wh/answer + tok/s-per-watt analysis.
- **§11 related work:** add the agent-safety cluster (OS-Harm, AgentHarm,
  Owner-Harm, GAP, AgentHazard) and the SLM/quant-safety cluster (Beyond-the-Tip,
  Q-resafe, EASE, GUARD-SLM); position **against** them explicitly.
- **Scale/honesty:** land the judge–human κ, add a third judge, broaden the guard
  corpus — the corroboration must be *rigorous* precisely because it cannot be *novel*.

## Alternatives considered (rejected)

- **A. Two papers (safety finding + harness).** Rejected: salami-slicing on one
  n=1 dataset; the safety half is out-scaled and non-novel; the systems half
  loses its flagship demo.
- **B. One paper, safety-led (the current `PAPER.md` Abstract).** Rejected: the
  scan shows the safety claim is saturated; leading with it invites a novelty
  desk-reject.
- **C. One paper, harness/method-led but generic.** Weaker than sovereign-first:
  "another small-LLM benchmark" is crowded too; *sovereignty + the energy-coupled
  selection decision* is the sharper, defensible hook.

## Risks

- **"Combination novelty is weak."** Mitigate by making the **energy×safety×quality
  Pareto** the *result*, not the framing — a number nobody else reports.
- **n=1 environment.** Frame as a single-environment case study + released harness;
  invite re-runs (already the plan).
- **Venue fit.** Sovereign-first + energy + reproducible harness points at
  **MLSys / NeurIPS D&B / a reproducibility track**, not a safety venue.

## References (arXiv, verified 2026-06-19)

**Agent / action safety:** OS-Harm 2506.14866 (NeurIPS'25 D&B Spotlight) ·
AgentHarm 2410.09024 (ICLR'25) · Owner-Harm 2604.18658 · AgentHazard 2604.02947 ·
GAP 2602.16943 · DeCompBench 2606.13994.
**SLM safety:** Beyond-the-Tip 2502.19883 (ACL'25) · EASE 2511.06512 (AAAI'26) ·
GUARD-SLM 2603.28817 · SLM-as-Guardian 2405.19795 (EMNLP'24) · Weak-Supervision-SLM 2603.07017.
**Quantization × safety:** Q-resafe 2506.20251 (ICML'25) · Safety-Preserving PTQ/CAQ 2511.07842 ·
Quantized-fairness/safety 2601.12033 · Activation-Approx 2502.00840 · Stochastic-Monkeys 2411.02785.
**Reasoning-model safety:** Self-Jailbreaking 2510.20956 (ICLR'26) · Hidden-Risks-of-R1 2502.12659 · SafeChain 2502.12025.
**SLM eval / judge:** Luna-2 2602.18583.
**Ops benchmarks:** AIOpsLab 2501.06706 · ITBench 2502.05352.
**SLM-pro / scaling:** NVIDIA-SLM 2506.02153 · ThinkSLM 2502.11569 (EMNLP'25) · Schaeffer-Mirage 2304.15004.
