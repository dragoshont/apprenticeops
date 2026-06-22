# Paper positioning — decision: one sovereign-first paper

> **Status:** Accepted 2026-06-19. Supersedes the implicit "safety is the spine"
> framing introduced in the [`PAPER.md`](./PAPER.md) Abstract/§1 rewrite (commit
> `1d4845f`) and the "two-paper" idea. This is a positioning ADR; it tells
> [`PAPER_INTENT.md`](./PAPER_INTENT.md) and `PAPER.md` how to frame the claim.

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

1. **Reasoning floor / quality** — can a ≤5 GB offline model reason about real ops?
2. **Safety** — will it refuse destructive actions when *there is no frontier to
   escalate to and no reviewer downstream*? (corroborates the literature above)
3. **Energy / fit** — what does running it *yourself* cost in Wh/answer, tok/s,
   thermal headroom on hardware you own?

No prior work measures **all three together for the model-selection decision in
the offline/CPU/locally-sovereign regime.** That integration — not any single
axis — is the contribution.

### The thesis (reframed, sovereign-first)

> *For a **locally-sovereign** ops assistant — offline, CPU-only, ≤5 GB, the last
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

1. **The regime no one targets together:** ≤8 B, **quantized, CPU-only, fully
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
