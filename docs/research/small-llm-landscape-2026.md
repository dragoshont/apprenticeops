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

## 7. Full reads (2026-07-15 / -16) — all eight papers, extracted and mapped

*All eight queued papers are now **read in full** (the SLM survey + the two KD papers
were finished 2026-07-16). Concrete numbers + the ApprenticeOps mapping below are citable.*

### 7.1 E3 — "Do AI Agents Know When a Task Is Simple?" (2607.13034, Jul 14; Yin & Feng, UT/CURENT, thanks MSR)
- **Claim/method:** agents lack *execution-scope estimation* — they gather max
  context on trivial tasks. Formalizes *minimum-sufficient execution* + the **Agent
  Cognitive Redundancy Ratio** ACRR = (C_act−C_min)/C_min, and **E3 = Estimate →
  Execute → Expand** (optimistic start + verified progressive expansion). Evaluated
  on MSE-Bench (121 edits in a *capability-invariant* simulator) + a real gpt-4o
  harness (LLM-Case) graded by real pytest.
- **Numbers:** E3 keeps 100% success while cutting **cost 85%, tokens 91%, files
  92%** vs max-context-first (ACRR 12.9→0.55); beats a strong adaptive-retrieval
  baseline by 16%. **Redundancy is largest on the simplest tasks** (ACRR 22.1 L1 vs
  5.4 L3). Survives held-out wording (+8.7% cost) and 99.8% of 4000 cost weightings.
  Real gpt-4o: milder but real; the heaviest-reading runs are the ones that fail.
- **Maps to ApprenticeOps:** names our reasoning result — "when *not* to think." Our
  thinking-mode-exhausts-the-budget is the deployment/energy instance of ACRR. **Caveat:**
  headline is a simulator (no LLM in loop); real-model part is a 3-run case study.

### 7.2 Reliability without Validity (2606.19544, Jun 17; Norman/Rivera/Hughes, UC Berkeley)
- **Largest LLM-judge study:** 21 judges × 3 benchmarks × 3 protocols, ~541k
  judgments — and it **includes ApprenticeOps' exact judges, Claude Opus 4.6 and GPT-5.4.**
- **Findings:** (1) *kappa deflation* universal — exact-match overstates chance-corrected
  κ by **33–41 pp** ("85% agreement" ≈ κ 0.48); (2) rankings move up to 14 positions
  across benchmarks; (3) *consistency–bias paradox* (test-retest >0.95 with position
  bias >0.10); (4) **verbosity bias tiny (<0.011)** cohort-wide.
- **Our judges specifically:** **Claude Opus 4.6 = JudgeBench κ 0.875 (best of all 21),
  position bias 0.004, verbosity 0.0032** — with Gemini 3.1 Pro the only judges holding
  top-3 across all benchmarks; **GPT-5.4 = κ 0.606, pos-bias 0.083.** Anthropic family
  has the lowest cohort bias.
- **Maps to ApprenticeOps:** primary citation for lesson 6 (**agreement≠validity**);
  validates Claude Opus 4.6 as a near-best judge and motivates reporting κ (our 0.853),
  not raw agreement, plus the second-family (GPT-5.4) cross-check. Its verbosity<0.011
  corroborates our finding 7. **Caveat:** judge-vs-*human*, English/text, thinking suppressed.

### 7.3 LLM Judges Too Generous Without a Reference (2607.12885, Jul 14; Kranti & Vajjala, Potsdam/NRC)
- **Method:** two-stage — calibration (accept-correct C1 vs accept-incorrect C2) +
  sensitivity (No-Ref / Ref-Visible / Ref-Compared). 3 judges, 3 languages (EN/AR/TE).
- **Findings:** judges **over-credit incorrect answers without a reference**; adding a
  reference **flips verdicts up to 85%** (mostly Correct→Incorrect), and the flips **align
  with humans** (agreement up to 0.98, highest in Ref-Compared). Worst in low-resource
  (Telugu); the *same* extracted answer can flip verdict once a reference is present.
- **Maps to ApprenticeOps:** validates the **gold-answer + rubric + deterministic-check**
  design — ApprenticeOps grades *reference-aware*, exactly the calibration they prescribe;
  reference-free scoring inflates. **Caveat:** QA-specific; needs some gold to calibrate.

### 7.4 TinyLLM — SLMs for Agentic Tasks on Edge (2511.22138, Nov 27; Haque et al, Clark Atlanta)
- **Closest evaluation neighbor.** BFCL v4 function-calling, models xLAM-2-3b/1b,
  Qwen3-4B/1.7B/0.6B, TinyLlama/TinyAgent-1.1B; SFT/PEFT/RL/DPO/hybrid tuning.
- **Numbers:** hard size hierarchy 1–3B ≫ <1B. xLAM-2-3b best **65.74% overall / 88.22%
  AST / 55.62% multi-turn**; Qwen3-4B 62% but multi-turn only 35%; Qwen3-0.6B 45.8% /
  **1.38% multi-turn**; TinyLlama/TinyAgent ~19.7% / **0% multi-turn** (only abstention).
- **Maps to ApprenticeOps:** corroborates finding 9 (bigger helps, ~4B knee) and R6/R13
  (tiny models fail hard, esp. multi-turn). **But it measures function-call accuracy only
  — no energy, no safety, no CPU-local, no capability honesty** = exactly ApprenticeOps'
  gap. **Caveat:** cloud/GPU eval; "edge" aspirational; energy not measured.

### 7.5 SLM-for-Agentic-Systems survey (2510.03847, Oct 4 2025; Sharma & Mehta) — *[full 8-page body read 2026-07-16 via Edge/CDP + pypdf]*
- **Thesis:** SLMs (1–12B, occasionally ~20B) are sufficient/superior for **schema/API-
  constrained** agentic work; **SLM-default + LLM-fallback** with an uncertainty-aware
  router + verifier cascades (it cites NVIDIA's "SLMs are the future of agentic AI").
  Proposes engineering metrics: **cost-per-successful-task (CPS), schema-validity rate,
  executable-call rate, p50/p95 latency, energy/request.** Guided decoding + strict JSON
  Schema close the gap at **10–100× lower token cost**. Concrete recipes: LoRA-adapter-
  per-task-cluster + INT4/INT8 serving; collect 10k–50k de-identified success traces; an
  abstention/escalation pseudo-algorithm; an industrial cost model (KV-cache residency).
- **Maps to ApprenticeOps:** the framing citation; its metric set ≈ our axes (quality,
  det, energy/answer, latency). **No dataset:** it is a survey/blueprint — it synthesizes
  existing SLMs + benchmarks (BFCL v3/v4, StableToolBench); no repository, no availability
  statement, nothing to release.

### 7.6 Different Teachers — Sub-1B On-Device Distillation (2607.08268, Jul 9; V. K. Chaganti, independent)
- **Methodological near-twin of ApprenticeOps.** Distill deepseek-r1:8b → Qwen3-0.6B
  (QLoRA, 3 seeds, Q4_K_M, on-device) + a **same-size non-reasoning-teacher control** +
  a managed 120B pipeline. **Blinded reference-free 3-judge panel across 3 families that
  EXCLUDES the teacher's/student's families**, a **negative control** (0% faithful on
  mismatched, n=30), paired bootstrap (20k), per-sub-task, temp-0 deterministic reruns.
- **Findings:** student 0.8s vs teacher 39s (5.4h→7min); recovers **58% of the summary
  gap**, beats constrained decoding **+16.8 (p<0.001)** and few-shot +4.9. **A same-size
  NON-reasoning teacher trains a student no better than base (+0.6, ns) → the gain is the
  teacher's *reasoning nature*, not its scale.** But reasoning-lineage students **fabricate
  on thin sources** (55 vs 74 faithful on 22 short articles) — "reasoning-oriented training
  can raise hallucination." Seed variance first-order at 0.6B (tone 11.8–58.1% across seeds).
- **Their transferable lessons (verbatim intent):** *decompose before concluding* (per-subtask
  scoring reveals findings an aggregate hides); *check the instrument* (grade reference-free
  faithfulness against the **full source** or a truncation artifact masquerades as a model
  regression); controls are "nearly free and changed the conclusion twice."
- **Maps to ApprenticeOps:** the paper to benchmark our *method* against — same local
  on-device, same own-family-excluded multi-judge panel, same negative control + paired
  bootstrap + per-subtask + deterministic reruns. Independently corroborates: **reasoning
  helps writing but hurts faithfulness** (≈ our reasoning quality-vs-safety split);
  **decompose-before-concluding** (≈ per-scenario-class); **check-the-instrument** (≈ our
  param-unit-bug catch + full-run re-center + judge-validity gate). "Distill vs use-directly
  + per-field routing" is the design counterpart to our "which small model, used directly,
  for which ops verb." **Caveat:** silver (judge) labels; n=22 subgroup; one task family.

### 7.7 Understanding KD in Post-Training: When It Helps and When It Fails (2606.22942, Jun 22; Liu et al, U-Michigan + Zoom) — *[full read 2026-07-16]*
- **Method:** systematic post-training KD on **Tulu 3** (939k instruction–response pairs);
  on-policy **GKD**; teacher Llama3.1-70B, students Llama3.2-1B/3B + Llama3.1-8B; data
  swept **10k→939k**. Adds a stronger instruction-tuned teacher (Llama3.3-70B-Instruct)
  and a two-stage synthetic-data recipe for low-resource domains.
- **Findings — when KD helps vs fails:** KD **beats SFT only in low-data regimes** (up to
  +5% at 10k); the gain **vanishes as data grows** (SFT can win by 150k) because a
  same-dataset teacher **saturates**. KD **recovers ~4% even at full data when the teacher
  knows something beyond the training set** (stronger instruct teacher). **Smaller students
  benefit most** (1B ≫ 3B ≫ 8B). Two-stage synthetic warm-up → human-refine beats naive
  mixing (1B ARC 26.7→70.3). Confirmed cross-arch on Qwen2.5-7B.
- **Maps to ApprenticeOps:** bounds the **distill-vs-use-directly** theme — distillation's
  payoff is largest exactly where our small ops models are weakest (data-scarce, smallest
  models) and ~null where data is abundant. We study models **as shipped** (no distillation),
  so this is the training-side complement, not a method twin. **Data:** reuses public
  Tulu3/Flores-200/DialogSum/ARC; **no own dataset/repo released** (CC BY 4.0).

### 7.8 The Quality-Utility Paradox (2606.16152, Jun 15; Qian et al, incl. MSR Asia; ICML) — *[full read 2026-07-16]*
- **Releases code + data:** `github.com/Dracoqhl/Quality-Utility-Paradox` (CC BY 4.0) — the
  one paper here besides E3 with a public code+data repo.
- **Method:** four parallel datasets on ONE fixed 34k-problem set (NuminaMath, RFT-sampled by
  Qwen2.5-Math-1.5B): **SLM-RFT** (the SLM's own traces), **Oracle-Refined** (GPT-5.2 repairs
  them), **Oracle-Synthesized** (GPT-5.2 from scratch), NuminaMath subset. Reward model =
  "perceived quality"; Avg@16 = "actual utility." Validated across SFT+DFT, 4 SLMs
  (1.5B/7B/3B/7B), hyperparams, and 3 reward models.
- **Findings — the paradox:** **higher reward-model score → LOWER downstream utility.**
  SLM-RFT has the **lowest** reward (1.47) but the **highest** accuracy (37.06 Avg@16),
  beating Oracle-Refined (34.06) and Oracle-Synthesized (30.02). Mechanism: Oracle refinement
  couples logical repair with **distributional drift** ("syntactic compaction" — dense symbols
  replace the SLM's native scaffolding) that raises the learner's **adaptation cost**
  (perplexity ↔ accuracy monotone; SLM-RFT PPL 1.52 lowest). Fix = **Style-Aligned Refinement**
  (repair logic while emulating the SLM's native style) → PPL 1.46, accuracy **39.12**,
  beating BOTH Oracle-Refined and even native SLM-RFT.
- **Maps to ApprenticeOps:** the sharpest **"reasoning-into-small can hurt"** corroboration —
  and it *refines* our R2: the problem isn't reasoning per se, it's **distributional
  incompatibility** when a bigger reasoner's traces are imported verbatim. The model's **own**
  (or style-aligned) traces beat distilling a stronger reasoner — a direct argument for
  judging small models **as shipped** rather than assuming "bigger teacher = better."
  **Caveat:** math-reasoning + SLM regime only.

## 8. Where each paper releases its data (verified 2026-07-16)

*Full-text-verified per paper: where the underlying data lives, and whether the paper
releases its OWN dataset. This is the reference for positioning ApprenticeOps' release.*

| Paper | Releases its own data? | Where / mechanism |
|---|---|---|
| E3 (2607.13034) | ✅ | Public **GitHub** repo (`eejyin/Do-AI-Agents-…`): MSE-Bench + LLM-Case harness + scripts that regenerate every table/figure; simulator results deterministic from a fixed seed (20260712). |
| Reliability-without-Validity (2606.19544) | ✅ (on publication) | ~**541k** per-judgment records (verdict + reasoning + raw response + latency) keyed by `(judge_id, benchmark, protocol, item_id, run_idx, position_order)`; permissive license. |
| Different Teachers (2607.08268) | ✅ | A **"released scorecard"** (full-context multi-arm pass-rate + per-item per-check detail) that **recomputes every metric offline with no API keys**, explicitly separate from a non-canonical judge cache; releases the RSS-News test set + 401/93 split. |
| TinyLLM (2511.22138) | ❌ | Reuses public **BFCL v4 / Gorilla OpenFunctions / AgentBank**; own artifacts are "internal figures/spreadsheets/working notes." No repo/URL. |
| Generous Judges (2607.12885) | ❌ | Reuses public **TyDiQA + MATA** (each released separately); judges via Sarvam/FanAR/OpenRouter APIs. No repo/URL. |
| SLM survey (2510.03847) | ❌ (survey) | Synthesizes existing SLMs + benchmarks; **no repository, no availability statement.** |

**Net: 3 of 6 release their own data; 3 do not** (two reuse public benchmarks, one is a
survey). The field norm is a **compact, recompute-offline artifact + regeneration scripts**;
none commit a multi-GB raw dump to git. (The two secondary distillation-method papers in
§7.7–7.8 fit the same pattern: *Quality-Utility Paradox* releases code + data on GitHub; the
*KD-in-post-training* study reuses public Tulu3/ARC and releases neither.)

**Where ApprenticeOps sits — and the hosting decision.** ApprenticeOps matches or exceeds the
strongest of this cohort. The compact `data/snapshots/<run>.{results,judged}.csv` (~3.5 MB,
tracked in git) recomputes every 152-run number offline — the *Different Teachers*
"released-scorecard" pattern — and `data/analysis-manifest.<run>.json` **content-addresses
and sha256-binds** the canonical inputs (stronger than "a GitHub folder" or "released on
publication"). The heavy raw (the 433 MB locked bundle `<run>-<bundle_id>` and the 1.1 GB
`.tmp` intake) is **not** committed to git by design; it is served **out-of-band from an
Azure Blob**, fetched by its content hash (`bundle_id`) — the DVC/git-LFS-style split the
field uses for large artifacts. A reviewer reproduces the headline from the tracked snapshot
with **zero downloads**, and can re-derive the raw rows by pulling the hash-verified bundle
from the blob. *(Blob + its URL to be created by the maintainer and wired into the manifest;
the content hash is already fixed, so the pointer is verifiable the moment the blob exists.)*
