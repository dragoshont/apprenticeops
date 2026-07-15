# Small-LLM landscape research brief — mid-2026 (live-sourced)

> **Method & honesty.** Compiled from live web fetches on 2026-07-15 (arXiv cs.CL
> recent + targeted searches, HuggingFace daily papers, the Ollama model library).
> Entries are **abstract-level reads with dated arXiv IDs** — verified to exist and
> be current, *not* full-paper reads. Where a claim needs the full paper before it
> can be cited in `PAPER.md`, it is marked **[read-in-full]**. This brief does **not**
> assume from training data; every dated item was fetched.

## 0. Headline: the field is converging on ApprenticeOps' questions

Three of our re-centered findings have independent, days-old external analogues:
- **"Thinking mode over-generates and blows the budget"** ↔ a wave of *complexity-aware
  execution* work (agents that estimate task difficulty before spending tokens).
- **"Judge agreement ≠ judge validity"** ↔ two 2026 judge-methodology papers saying
  precisely that, plus "judges over-credit without a reference answer."
- **"Small local models are the right substrate for bounded ops"** ↔ big-company
  small/on-device *agentic* models shipping (Microsoft, Apple, Qualcomm, IBM, Google).

That convergence is good positioning: ApprenticeOps is a **CPU-local, energy-measured,
safety-inclusive ops-assistant benchmark** — a niche these works circle but don't fill.

## 1. Big-company move into small / on-device agentic models (the "precipitation")

Dated, verifiable signals that large orgs are investing in *small* agentic models:
- **Microsoft — Fara-7B: An Efficient Agentic Model for Computer Use** (arXiv:2511.19663;
  MSR authors incl. Ahmed Awadallah). A 7B computer-use agent + synthetic-trajectory
  data engine.
- **Microsoft — Phi Silica** on-device rewriting (arXiv:2606.00462) — the Windows
  on-device SLM in production use.
- **Apple — Ferret-UI Lite: Lessons from Building Small On-Device GUI Agents**
  (arXiv:2509.26539; Zhe Gan, Yinfei Yang et al.).
- **Qualcomm — When Cloud Agents Meet Device Agents** (arXiv:2605.30102) — hybrid
  cloud/device agent trade-offs (ICML 2026 AIWILD workshop).
- **IBM — Evoflux: Inference-Time Evolution of Executable Tool Workflows for Compact
  Agents** (arXiv:2606.12674).
- **Model releases (Ollama library, © 2026):** IBM Granite 4.1 (tools, Apache-2.0),
  Google Gemma 4 (e2b/e4b edge) + FunctionGemma-270M (function-calling), LiquidAI
  LFM2 / LFM2.5-8B-A1B (edge tool-calling), NVIDIA Nemotron-3-Nano-4B (agentic),
  Cohere command-r7b / North-Mini-Code (30B-A3B), Qwen3.5/3.6, SmolLM3, OLMo-3.
- Thesis-supporting quote: *"Scaling the language model is often an inefficient way to
  improve this component"* (NOEM³A, arXiv:2511.19780, mobile agents).

**Implication for the paper:** frame small-local-ops as riding a real 2026 industry
shift, not a hobbyist niche. Cite Fara-7B / Ferret-UI Lite / Granite-4 as the
"industry is going small + agentic + on-device" evidence.

## 2. Reasoning / "thinking" budget — independent validation of our finding

- **Do AI Agents Know When a Task Is Simple?** (arXiv:2607.13034, Jul 14) — agents
  follow a "maximum-context-first" strategy and over-work simple tasks; proposes **E3
  (Estimate–Execute–Expand)** and the **Agent Cognitive Redundancy Ratio**; cuts cost
  **85%** / tokens **91%** at equal success. *This is the same mechanism as our
  thinking-mode-exhausts-the-budget result, generalized.* **[read-in-full]** — the
  strongest single citation for our reasoning finding.
- **An Alternative Trajectory for Generative AI** (arXiv:2603.14147) — the energy burden
  has "shifted from one-time training to recurring, unbounded inference … exacerbated by
  reasoning." *Directly supports our energy + reasoning-cost axis.*
- **The Quality-Utility Paradox: Why High-Reward Data Impairs Small Model Mathematical
  Reasoning** (arXiv:2606.16152, ICML 2026) — distilling strong reasoning traces *into*
  small models can **hurt** them. Nuances our "reasoning is a poor fit at small scale."
- **ReasonAlloc** (arXiv:2606.11164), **Token Reduction Is Not Cost Reduction**
  (arXiv:2607.12161), **Less Experts, Faster Decoding: Cost-Aware Speculative Decoding
  for MoE** (arXiv:2607.12696) — budget/decoding-cost mechanics.

## 3. Distillation — the 2026 recipe, and its limits (the "distill vs use directly")

- **Understanding Knowledge Distillation in Post-Training: When It Helps and When It
  Fails** (arXiv:2606.22942) — a when-KD-works map. **[read-in-full]**
- **On-policy distillation (OPD)** is the hot 2026 recipe: DOPD (2606.30626), ATOD for
  multi-turn agents (2606.27814), "Dense Supervision, Sparse Updates" (2606.13657),
  "Zone of Proximal Policy Optimization" (2606.18216, NVIDIA authors).
- **Different Teachers, Different Capabilities: Sub-1B On-Device Distillation for
  Structured Text Enrichment** (arXiv:2607.08268, Jul 9) — sub-1B on-device distillation
  **with a same-size non-reasoning-teacher control + a 3-judge LLM-as-judge panel with a
  negative control**. *Methodologically the closest neighbor to ApprenticeOps' rigor.*
- **Stage-specific SFT-then-RL for Small-LM Reasoning** (arXiv:2606.04466).

## 4. LLM-as-judge methodology — validates our gold+rubric+human-eval stance

- **Reliability without Validity: A Systematic, Large-Scale Evaluation of LLM-as-a-Judge
  Across Agreement, Consistency, and Bias** (arXiv:2606.19544) — **the exact point our
  adversarial gate raised: agreement/consistency ≠ validity.** Primary citation for our
  judge-validity caveat.
- **LLM Judges Can Be Too Generous When There Is No Reference Answer** (arXiv:2607.12885,
  Jul 14) — judges over-credit incorrect answers without a reference; adding a reference
  flips decisions up to **85%** and aligns with humans. *Validates our use of gold
  answers + deterministic checks + rubrics (reference-aware), and warns against
  reference-free scoring.* **[read-in-full]**
- **Can LLMs Write Reliable Rubrics?** (arXiv:2607.12835), **Who Grades the Grader?**
  (arXiv:2607.12790) — rubric/meta-eval.

## 5. Comparable benchmarks / surveys to position against

- **Small Language Models for Agentic Systems: A Survey of Architectures, Capabilities,
  and Deployment Trade-offs** (arXiv:2510.03847) — the survey to cite for framing. **[read-in-full]**
- **TinyLLM: Evaluation and Optimization of Small Language Models for Agentic Tasks on
  Edge Devices** (arXiv:2511.22138) — the closest *evaluation* neighbor; contrast our
  CPU-only, energy-measured, safety-inclusive, homelab-ops scope against it. **[read-in-full]**

## 6. What this means for ApprenticeOps (positioning)

1. **Timely, not niche.** Small + on-device + agentic is a 2026 industry front (Fara-7B,
   Ferret-UI Lite, Phi Silica, Granite-4, Gemma-edge). Lead the paper with that.
2. **Our reasoning finding has a named external frame** (complexity-aware execution / E3);
   cite it and position ours as the *deployment-side, energy-measured* instance.
3. **Our judge caveats are the field consensus** (reliability≠validity; reference-aware
   judging) — this turns the gate's critique into cited rigor, and motivates scoring the
   human-eval packet.
4. **Distillation is the field's lever** but ApprenticeOps studies models *as shipped*
   (use-directly), which is a distinct, valuable stance — and the sub-1B-distillation
   work (2607.08268) shows our same-size-control + judge-panel methodology is current.
5. **Gaps we uniquely occupy:** CPU-only local, RAPL energy per answer, safety scenarios,
   and honest capability accounting — none of the neighbors combine all four.

## 7. Read-in-full queue (before any of this is cited)

2607.13034 (E3), 2606.22942 (when-KD-works), 2606.19544 (reliability≠validity),
2607.12885 (generous judges), 2510.03847 (SLM-agentic survey), 2511.22138 (TinyLLM),
2607.08268 (sub-1B distillation methodology), 2606.16152 (quality-utility paradox).
