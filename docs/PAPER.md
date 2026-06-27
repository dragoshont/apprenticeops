# ApprenticeOps Paper Draft (Design and Analysis Plan)

Target: workshop paper + arXiv preprint.

> **Status:** WIP / DRAFT (not submitted).
>
> **Study phase:** active spec for the powered study (Pass 2).
>
> **Relationship to pilot:** supersedes the Pass-1 pilot framing in
> [`PLAN.md`](./PLAN.md) for publication purposes; [`PLAN.md`](./PLAN.md)
> remains the operational how-to.
>
> **Pass split:** Pass-1 (n=1/class) is the pilot that de-risks the harness and
> yields the speed/RAM/safety profile; Pass-2 is the study that produces the
> publishable, statistically-defensible result.
>
> **Submission workflow:** phase gates and pre-submit checklist are tracked in
> [`PAPER_PHASES.md`](./PAPER_PHASES.md).
>
> **Intent memo:** peer-alignment scope and claims are tracked in
> [`PAPER_INTENT.md`](./PAPER_INTENT.md).

## Abstract (Draft)

We present **ApprenticeOps**, an open, reproducible benchmark and telemetry method
for evaluating **small, locally-run LLMs (≤ ~5 GB)** as **homelab/edge operations
assistants** — detect, diagnose, monitor, expand, upgrade, test, augment, and
*safely refuse*. Our framing follows the **AIOps maturity ladder** (reactive →
proactive → predictive/preventive → autonomous): a small model begins as an
**apprentice** on low-stakes homelab incidents and earns its way toward
higher-stakes, ahead-of-time operation. Crucially we define **offline =
locally-sovereign inference** (no external *model* API — no Azure AI Foundry,
Anthropic, OpenAI, or frontier escalation), **not** information-starvation: a
locally-sovereign model may use **local RAG, in-org MCP servers, runbooks, and
local telemetry**. Unlike existing AIOps agent benchmarks (AIOpsLab, ITBench,
OpsEval) — frontier/cloud models, live agentic fault-injection, server hardware —
we measure the **reasoning floor of a last-line local model on commodity offline
hardware** along the axes retrieval *can't* fix — **reasoning,
grounding-faithfulness, calibration, and safety** — and the deployment cost you
pay regardless: **energy and fit on hardware you own**.

Our finding is a **selection problem**, not a leaderboard: the proxies a
practitioner reaches for — **parameter count, benchmark score, a "reasoning"
badge, perplexity** — each mislead, and they mislead on **different axes**, so no
one of them orders the choice. We profile three axes at once in a single
offline, CPU-only harness. **Quality:** across a **94-model** sweep (0.36–8B),
judged ops-reasoning climbs steeply with size to a usable floor by **2–3B** — one
bracket below our **pre-registered 3–4B** prediction — then returns flatten (the
2–3B→3–4B step adds **<1 point**, the 4–5GB bracket a further **+4.6**), and
**quantization largely preserves it** — so "biggest that fits" buys
little above the knee. **Safety:** on **deterministic** refusal-of-destructive-action
checks (no LLM judge, our most robust numbers) the safest size bracket still plateaus
near **80 %** — one destructive prompt in five survives — and the dominant driver
of refusal is **training type, not size**: **reasoning-distilled ("thinking",
R1-style)** models refuse at **47.2 %** [41.3, 53.3] versus **71.4 %** [70.3,
72.4] for instruct, a gap wide enough that a **0.36 B** instruct model out-refuses
a **7.6 B** reasoning model and the **three lowest refusers in the study are all
reasoning-distilled**. We are explicit that this safety result **corroborates** a
fast-growing agent-/SLM-safety literature (reasoning-distillation and
quantization degrade safety; text-refusal ≠ action-refusal) rather than
discovering it — its weight here is that it **replicates offline, on CPU, at
homelab scale**, where the unsafe model is also the one the size heuristic picks.
**Energy:** we meter **Wh per answer, tokens/s-per-watt, and thermal headroom** on
owned hardware, so the bigger model's bill for capability *above* the knee is
counted in watts, not adjectives. The contribution is the **integration** —
quality × safety × energy measured **together** for the
offline/CPU/locally-sovereign model-selection decision, a regime no prior
benchmark targets whole — released as a reproducible artifact (harness +
real-incident scenarios + telemetry schema). The model ranking is the
demonstration; the artifact, and the three-axis selection method, are the
contribution.

## 1. Introduction and Scope

"Offline" removes three crutches an online agent leans on — but **only the
first is about the model**; the other two are about *information*, which a local
setup can still supply:

| Crutch removed | Axis | Locally-sovereign equivalent |
|---|---|---|
| Escalate to a frontier model | **inference** (forbidden) | **None — the model IS the last line.** It must degrade gracefully and know its limits. |
| Look up external docs (web, vendor changelogs) | information | **Local RAG / in-org MCP / runbooks** feed it (allowed). |
| Fetch more telemetry on demand | information | The **operator/harness retrieves**; the **model reasons** over what it's given. |

**Design principle:** *retrieval is the operator's job; reasoning is the model's.*
This yields the **reordered requirement stack** a small local ops model is graded on:

1. **Reason without an external model** — no second opinion; its judgment is final.
2. **Grounding-faithfulness** — use supplied local context (RAG/MCP/runbook) and
   do **not** contradict or hallucinate beyond it.
3. **Calibration** — flag missing context / say "I don't know" instead of
   inventing (the prerequisite for safety).
4. **Safety-by-default** — refuse destructive actions; no external reviewer catches it.
5. **Fit + speed** on owned hardware.

> **Thesis (state up front).** For a **locally-sovereign** ops assistant —
> offline, CPU-only, ≤5 GB, the last line with no frontier to escalate to and no
> reviewer downstream — **model selection is the whole game, and every proxy a
> practitioner reaches for (parameter count, benchmark score, a "reasoning" badge,
> perplexity) misleads on a *different* axis.** We measure three axes in one
> harness. **(1) Quality:** the capability bar is cleared earlier than folklore
> expects — a usable ops-reasoning floor arrives by **2–3B** — and *quantization
> largely preserves it*, so param-count and a "reasoning" badge over-predict what
> the job needs. **(2) Safety:** on **deterministic** refusal checks (no LLM
> judge) instruct-model refusal *rises with size then plateaus near 80 %* — a
> fifth of destructive prompts survive even the best bracket — and the real driver
> is **training type, not size**: **reasoning-distilled** models refuse roughly
> **24 points less** than instruct siblings, so the **three lowest refusers of all
> 94 models are reasoning-distilled**. We state plainly that this
> **corroborates** a fast-growing agent-/SLM-safety literature (§11) rather than
> discovering it; the delta is that it **replicates offline, on CPU, at homelab
> scale**, where the unsafe model is also the one the size heuristic picks.
> **(3) Energy:** the bigger model bills you in **watts and tokens/s** for
> capability above the knee you may never use. The spine is that consequence —
> **no single axis, and no single proxy, orders the choice; the integration
> does.** §8b is the evidence (deterministic; the reasoning arm is four
> R1-distilled models).

**Grounding modes (a measured factor, not a caveat).** Each scenario is labelled
`closed-book` (answer from in-weights ops knowledge; incident data given, no
reference docs) or `grounded` (reference material supplied in-context, simulating
**local RAG / in-org MCP**). Reporting **closed-book vs grounded** per model
quantifies *how much local retrieval closes the gap* — directly actionable for
"do I need a vector DB next to my tiny model?" Some task classes are
offline-tractable from local data (detect/diagnose/monitor/augment/guard); others
(expand/upgrade) **require local retrieval** to supply changelogs/conventions.
That boundary is itself a finding.

> **Two honesty caveats that MUST be stated in the paper:**
> 1. **The judge/reference is eval-time scaffolding, not a system dependency.**
>    We use a frontier model (Claude 4.8) to *score* answers; the
>    *system-under-test* (the small local model) **never** calls it. "Offline"
>    describes the deployed system, not the benchmark's grading rig.
> 2. **`grounded` = oracle-retrieval upper bound.** We inject the *correct*
>    reference text directly; a real local-RAG pipeline adds retrieval error, so
>    our grounded numbers are the **ceiling** of what local RAG buys, not the
>    expected value. We measure "perfect retrieval"; real deployments do worse.

## 2. System Boundaries and Dependency Disclosure

The sovereignty claim is about the **inference path only**, and we state its
bounds explicitly so a reviewer cannot mistake "eval scaffolding uses the cloud"
for "the system is not sovereign."

| Path | Public service | Touches model inference? | Disposition |
|---|---|---|---|
| **Model inference** (`run.py`) | **None** — local Ollama on `127.0.0.1:11434` only | — | **Sovereign. The claim rests here.** No network egress during any graded inference. |
| **Model acquisition** (`ollama pull`) | `ollama.com` / registry | No — one-time, before the run | Supply-chain surface (pin the **digest**, not the tag; see MARKET §3). Not an inference dependency. |
| **Judge + frontier reference** (`judge.py`) | **GitHub Models** (`models.github.ai` → OpenAI/Azure-hosted) | **No** — off-node, post-hoc, on the Mac | **Eval scaffolding.** The system-under-test never calls it. BUT it **receives the scenario text**, which contains real cluster detail (namespaces, Azure Key Vault, Cloudflare, `*.home.domain`, restic/NAS) → **egress of real ops data to a third party** (see threat row + REPRODUCE caveat; scrub before release). |
| **Stats** (`report.py` extension) | PyPI (`numpy`/`scipy`) | No — analysis-time, off-node | None at runtime. |
| **Serving gateway** (Caddy `ai.home.domain`, *not* part of the eval) | Let's Encrypt + Cloudflare DNS-01 | No | Out of scope for the benchmark; a dependency of the *deployed serving* path, not the *measured* path. |

**Bottom line:** the only public service in the actual experiment is the
**off-node judge**, and it is grading scaffolding, not a runtime dependency — but
because it sees real telemetry, the released scenarios must be scrubbed and the
egress disclosed. The deployed apprentice itself makes **zero** external calls.

## 3. Research Questions and Hypotheses

> **Scope honesty (state up front):** this paper benchmarks the **reactive +
> early-proactive reasoning FOUNDATION** of the AIOps ladder (detect, diagnose,
> plan a fix, refuse danger). It does **not** test the upper rungs — *predictive*
> (time-series forecasting), *preventive* (act before failure), or *autonomous*
> (closed-loop self-healing). The maturity ladder is the **roadmap/motivation**;
> what we *prove* is the apprentice's footing on the bottom rungs. Claiming
> autonomy would be overreach.

| RQ | Question | Hypothesis (falsifiable) |
|---|---|---|
| **RQ1** | Does ops-reasoning quality scale with model size in the 0.5–8B range on CPU? | H1: quality rises with params but with **diminishing returns**; a knee around **3–4B**. |
| **RQ2** | Which size bracket is the **speed/quality Pareto frontier** for interactive use (≥8 tok/s)? | H2: the **3–4B** bracket dominates the Pareto front on this hardware. |
| **RQ3** | Are small models **safe** to put in front of a homelab (do they refuse destructive actions)? | H3: safety is **not** monotonic in size; some small models endorse catastrophic commands (pilot already shows qwen2.5:0.5b does). |
| **RQ4** | Do **reasoning/"thinking"** models beat instruct models at diagnosis, and at what latency cost on CPU? | H4: thinking models gain accuracy on *diagnose/test* classes but at a **prohibitive token/latency cost** on CPU. |
| **RQ5** | How far below a **frontier reference** do the best small models land on real ops tasks? | H5: best ≤5 GB model reaches **~60–80 %** of frontier on structured tasks, **less** on open-ended diagnosis. |
| **RQ6** | How much does **local grounding (RAG)** lift a small model vs closed-book? | H6: grounded − closed-book gap is **large for small models** and shrinks with size — i.e. local RAG substitutes for parameters. |
| **RQ7** | What is the **energy cost per task** (Wh/answer, tok/s-per-watt) and how does it scale with model size on CPU? | H7: energy/answer rises with params; the **3–4B** knee is also the **energy-efficiency** sweet spot (best correct-answers-per-watt on this box). |

> **Pre-registration (state up front).** These seven hypotheses — including the
> **bracket each names** (H1/H2/H7 predict a *3–4B* knee/frontier) — were **fixed
> before the measurement run** *(Locked.)*. We report outcomes against them
> **verbatim** in §8c: each hypothesis earns an explicit verdict — *supported* /
> *partially supported* / *not directly tested* — and any departure from this plan
> is logged as a transparent **deviation**, never folded back into the hypothesis
> after the fact (no HARKing). For the record, before the result: **three of the
> seven hold**, the quality knee landed **one bracket smaller (2–3B)** than the
> pre-registered **3–4B**, and three (RQ4–RQ6) were **not directly testable** with
> this design — we say so rather than revise the predictions.

## 4. Methodology and Experimental Design

- **Primary factor:** model (the 25, grouped by **parameter bracket**: 0-1B, 1-2B,
  2-3B, 3-4B, 4-5 GB).

### 2a. Model roster (frozen manifest for this run)

The current experiment evaluates **25 local Ollama model tags** (exactly the
entries in `data/models.txt`):

- **0-1B:** `qwen2.5:0.5b`, `qwen3:0.6b`, `llama3.2:1b`, `granite4:1b-h`, `smollm2:360m`
- **1-2B:** `qwen3:1.7b`, `smollm2:1.7b`, `qwen2.5:1.5b`, `deepseek-r1:1.5b`, `stablelm2:1.6b`
- **2-3B:** `granite4:micro`, `qwen2.5:3b`, `phi:2.7b`, `gemma2:2b`, `ministral-3:3b`
- **3-4B:** `phi4-mini`, `qwen3:4b-instruct-2507-q4_K_M`, `gemma3:4b-it-qat`, `llama3.2:3b`, `qwen3:4b`
- **4-5GB:** `granite4:tiny-h`, `mistral:7b-instruct-q4_K_M`, `qwen2.5:7b`, `deepseek-r1:7b`, `qwen3:4b-instruct-2507-q8_0`

- **Confound control (REQUIRED for the headline comparison):**
  - **Quantization held constant** — main cross-model comparison uses **q4_K_M**
    (or each model's nearest standard q4). q8/QAT variants run as a **separate
    sensitivity analysis**, never mixed into the main ranking.
  - **Thinking vs instruct** — two **separate tracks**; thinking models get
    `think=true` + a larger token budget + longer timeout. Never scored against
    instruct models on the same axis without labelling.
- **Within-subject:** every model sees every scenario (paired design → paired
  stats, higher power).
- **Two passes, two questions.** We run each (model × scenario) twice over,
  because a deployer asks a model two different things. The **deterministic pass**
  (temperature 0, greedy decoding — the model always takes the highest-probability
  token) asks *“what does this model do when it stops guessing?”* and yields a
  near-reproducible point estimate. The **variance pass** (temperature 0.7,
  **R = 5** seeded repeats) asks the harder, more honest question — *“how much does
  the answer change if I simply run it again?”* — and turns that wobble into
  mean ± 95 % CI error bars. A model that is excellent on average but swings wildly
  between runs is not the same product as one that is merely good and steady; only
  the variance pass can tell them apart. *(Locked: R=5.)*
  > **temp-0 caveat:** greedy decode on Ollama/llama.cpp is *mostly* but **not
  > bit-exactly** reproducible across CPU threads/batch, so we still report CIs
  > even on the “deterministic” pass.
- **Hardware operating point (held fixed; disclosed):** single node — ThinkPad
  T480s, **Intel i5-8350U** (4C/8T, base 1.70 GHz, turbo 3.60 GHz, AVX2, no
  AVX-512, 15 W TDP), **24 GiB DDR4-2400 dual-channel** (asymmetric 8 GB Micron +
  16 GB SK Hynix → flex mode; theoretical peak ≈ 38.4 GB/s), Ollama 0.30.8, on AC.
  The power audit found **no** TLP / power-profiles-daemon / auto-cpufreq and EPP
  already `performance`; the only per-run variance was dynamic HWP frequency
  scaling + turbo. For the **systems pass** the node is **locked**
  (`node-power.sh setup`): governor `performance`, **turbo off**, clock **pinned
  to base** (`no_turbo=1`, min=max=100 % → ~1.70 GHz, sustainable, zero throttle).
  **Wi-Fi and Bluetooth are disabled** (`rfkill`; management is on Ethernet) to
  drop radio interrupts/power jitter and close the wireless egress path.
  Between models a **`quiesce()`** step drives the ThinkPad fan to max, drops the
  page-cache, resets swap, compacts memory, and waits for the package temp to
  settle — so every model starts from an identical machine state. CPU clock is
  **logged at 1 Hz** (aggregate + per-core) as throttle evidence; DRAM clock is
  fixed (2400 MT/s) and recorded once in [`ENVIRONMENT.md`](./ENVIRONMENT.md). *(Locked.)*

## 5. Scenario Corpus and Provenance

- **Current frozen snapshot:** **19 scenarios** total (from `data/scenarios.json`).
- **Target for the expanded benchmark release:** k ≥ 6 scenarios per class.
  > **Priority: the `guard` (safety) class needs the MOST expansion.** The
  > headline "safety non-monotonicity" claim currently rests on **one** destructive
  > scenario per model — too thin. Author ≥6 distinct destructive prompts
  > (`rm -rf`, force-delete PVC/PV, drop database, disable firewall/NetworkPolicy,
  > `kubectl delete pvc`, secret exfiltration) so safety is a *distribution*, not
  > a coin flip.
- **Provenance:** drawn from **real `home.home.domain` signals** (kube events,
  crashloops, ESO/Flux/Helm/probe failures captured over time) + a **held-out**
  set authored *after* the harness froze, to test generalization.
- **De-bias authorship:** gold answers + rubrics reviewed by **≥ 2 independent
  people** (you + one other, or you + a frontier model acting as adversarial
  reviewer whose disagreements you adjudicate). Record inter-author agreement.
- **Difficulty labels & design intent:** each scenario is tagged easy/medium/hard
  (current set: 5/9/5). The **easy** tier is a *passable floor* — JSON extraction
  and spot-the-obvious-flaw security (plaintext secret, no-auth ingress, `:latest`)
  that any usable model should clear; it catches catastrophic failures rather than
  discriminating. The **hard** tier deliberately **pushes the limit**: the
  `foresee-*` "trap" scenarios pit a *misleading healthy surface signal* against
  the real problem (SMART `PASSED` while reallocated/pending sectors climb; cert
  `Ready=True` while DNS-01 auto-renewal has 403'd for days), and the closed-book
  upgrade/expand variants withhold the reference doc — hard-but-passable, not
  impossible. The labels are **validated empirically** by the accuracy-by-difficulty
  table (report.py): if mean score doesn't fall easy→hard, the label is wrong and
  gets revised. This shows the benchmark is neither saturated nor trivial.

## 6. Metrics and Instrumentation

**Quality**
- `det_score` — deterministic-check pass rate (unambiguous facts; no judge).
- `judge_score` 1–5 — frontier LLM-as-judge (open-ended quality), **% of frontier**.
- `safety_pass` — binary on the `guard` class (hard gate; a fail disqualifies).

**Efficiency / telemetry (OTel `gen_ai.*`)** — per request:
- TTFT, prefill tok/s, decode tok/s, wall, in/out **tokens and chars**, warmup
  (cold-load). **Think/answer split** for reasoning models (thinking chars +
  seconds separated from the answer) so a model is neither rewarded nor penalised
  for hidden chain-of-thought.
- **Inter-token latency jitter** — decode dt p50/p95/max (ms): the *smoothness*
  of the stream, not just its mean rate (a high p95 stutters the UX even at a good
  average tok/s).
- **CPU microarchitecture** (env-gated `PERF_CORE`) — instructions + cycles →
  **IPC**, and cache- / LLC- / branch-miss counts (the contention signals from
  Alibaba's AMTrace): a low IPC + high LLC-miss rate is the fingerprint of a
  memory-bandwidth-bound decode, corroborating the MBU verdict. Plus per-request
  **minor/major page faults** and **context switches** (scheduler pressure).
- **Ollama-native internals** — exact `parameter_count`, quantization, native
  context length and architecture (`/api/show`); `size_vram = 0` + a 100 % CPU
  processor split (`/api/ps`) as Ollama's **own** CPU-only proof; and the
  authoritative `load` / `total` / `eval` durations from the response (the
  ground-truth backing tok/s). Real param counts make the size-vs-quality
  regression honest, not bracket-guessed.
- **Model architecture & MoE sparsity** — from the GGUF metadata Ollama exposes:
  layer count, **GQA heads** (`head_count`/`head_count_kv` = KV-cache compression),
  FFN width, and for MoE models the **experts active/total per token** (the "nodes
  activated", e.g. `granite4:tiny-h` = 6/64). A MoE computes like its *active*-param
  size (fast) while needing its *total*-param footprint in RAM — decoupling size
  from speed/energy, which this study can show directly on the systems axis.

**On-device profile** (multivariate time series, default 1 Hz, shared `t=0`):
- RAM-avail / swap, model-runner **RSS / threads / major-faults** (swap-thrash
  onset), RAPL **power(t)** with a **core / uncore / dram** breakdown (dram =
  memory-controller power, a bandwidth proxy), **CPU + per-core temp / freq /
  util** (thermal-throttle and core-parallelism signal), optional **perf memory
  bandwidth(t)** (`uncore_imc`, env-gated `PERF_MEMBW`), and **disk & net I/O** —
  where net ≈ 0 throughout inference is an **empirical egress proof** of the
  offline contract. Peak temp / RSS / dram and **start temp** (thermal-carryover
  covariate) are surfaced per row. Sample interval is configurable (`SAMPLE_INTERVAL`)
  to trade resolution against the observer effect.

**Energy per task (measured)** — primary source **Intel RAPL** on-die joule
counters (exact joules = counter delta bracketing the request; the **`package-0`**
domain is preferred over `psys` to avoid the battery-charge confound), with a
**smart plug** (Home Assistant / IKEA DIRIGERA) as an optional wall-power
cross-check. Yields **Wh/task**, mean/peak W, and an idle baseline for
**net-over-idle**. RAPL is a *modeled* SoC estimate, not wall power (§6).
Operator/SoC telemetry like `/proc` — **not** a model egress, so the offline
contract holds. No-op if unavailable.

**Calibration (ceilings — `calibrate.py`, run on a quiet node):** a STREAM-style
multi-thread memcpy measures the **achievable peak DRAM bandwidth**; the tiniest
model gives a practical **peak tok/s**; idle W/temp give the net baseline; and a
**with-vs-without-telemetry** probe quantifies the **observer overhead** (tok/s
lost to the sampler+perf). These make MBU and saturation % *measured*, not guessed.

- per-token **progress trace** (token-arrival curve) — aligned (shared t=0) with
  the power(t)/memory series for a full **behaviour-over-time** view.
- DNF taxonomy: timeout / stall / oom / loop.

**Accelerator & memory attribution** — `gpu_freq_mhz` (iGPU GT clock; idle floor
~300 MHz = CPU-only proof) at 1 Hz, and via perf IMC the **memory-request split by
requestor** (`ia`=CPU cores, `gt`=iGPU, `io`=devices) so a gt-share ≈ 0 is direct
evidence of no GPU offload (Ollama runs `llama-server`, no `-ngl`). RAM/swap
**variation** (RSS start→peak growth, swap start→peak delta) is surfaced per task.

**Derived**
- **Pareto rank** (quality vs decode tok/s, and quality vs energy/task).
- **TPOT** (ms/token), **chars/s** (tokenizer-independent throughput — tok/s is
  **not** comparable across tokenizers, ~20% spread), **energy-per-output-token**
  (J/tok), **energy-per-correct-answer** (Wh ÷ accuracy), **quality-per-GB**, and
  **tok/s-per-watt** — all on **real measured energy** (replacing the old tok×acc
  watt-proxy).
- **MBU** (Model Bandwidth Utilization = achieved ÷ **measured**-peak DRAM
  bandwidth) and a per-model **bottleneck verdict** read off the telemetry
  fingerprint (capacity/swap · thermal · bandwidth · compute), plus a **throttle
  flag**.
- **Accuracy by difficulty** (easy/medium/hard author labels) — holding up on
  `hard` is reasoning, not pattern-matching the easy tail.

The full field-by-field schema is [`TELEMETRY.md`](./TELEMETRY.md) (data dictionary + pipeline
diagram); it is released with the harness so the dataset is reusable.

## 7. Released Dataset and Derivative Tasks

Every run emits a row-per-`(model, scenario, rep)` JSONL with an aligned 1 Hz
multivariate time series (schema: [`TELEMETRY.md`](./TELEMETRY.md)). Beyond the headline ranking,
this is a **public, reproducible dataset** of small-model behaviour-under-load on
commodity CPU hardware, and it enables derivative tasks the paper flags as
future / community work:

- **Early-warning DNF prediction** — from the first *N* seconds of the
  power/memory/major-fault curves, predict whether a request will time out,
  stall, OOM, or loop (an online watchdog that kills doomed generations early).
- **Quality-from-behaviour** — can the telemetry fingerprint (jitter, temp, swap,
  bandwidth) predict the *judged* answer quality **without reading the text**? A
  positive result is a cheap online quality proxy.
- **Anomaly / exfiltration detection** — net ≈ 0 is the egress invariant; the
  released net/disk series is a labelled baseline for detecting a model (or a
  compromised runtime) that suddenly phones home.
- **Roofline / bottleneck modelling** — with the measured bandwidth and tok/s
  ceilings (`calibrate.py`), place each model on the operational-intensity
  roofline (Williams et al.) and predict where a larger model crosses from
  bandwidth- to capacity-bound on a given node.
- **Energy modelling** — fit Wh/task from (params, output tokens, bandwidth) to
  predict an unseen model/quant's energy cost on this hardware class.

Released with the harness so these are reproducible, not just asserted.

### 7c. Cross-hardware extrapolation (roofline transfer)

The harness already logs, per request, the model's `parameter_count`,
`quantization`, on-disk `size_bytes`, the **achieved** DRAM bandwidth
(`membw.peak_mb_s` + the 1 Hz `membw.series`), the prefill/decode phase split, and
`energy_wh`. That is the full feature set to **transfer** throughput to an unseen
CPU from first principles — **without re-running the suite** (the fields are
already captured; only a re-projection is needed).

Small-model autoregressive **decode is memory-bandwidth-bound**: each token streams
the weights through the memory bus once, so

$$\text{decode tok/s} \approx \text{MBU}\cdot\frac{B}{W},\qquad W \approx p\cdot b + \text{KV}(c)$$

where $B$ is achievable DRAM bandwidth, $W$ the bytes moved per token, $p$ the
**active** parameter count, $b$ the bytes/weight of the quant, $\text{KV}(c)$ the
key/value traffic at context length $c$, and $\text{MBU}\in(0,1]$ the achieved/peak
bandwidth efficiency. To first order, for a **fixed model+quant+context+ISA**,
moving to another CPU scales throughput by the **bandwidth ratio** — not the clock
or a CPU-mark score:

$$\text{tok/s}_{\text{new}} \approx \text{tok/s}_{\text{old}}\cdot\frac{\text{MBU}_{\text{new}}}{\text{MBU}_{\text{old}}}\cdot\frac{B_{\text{new}}}{B_{\text{old}}}$$

**Prefill** (TTFT) is the compute-bound complement and scales with cores × SIMD
width × clock (FLOPs), so it is modelled separately. **Recipe** for a target box:
run `calibrate.py` once to get its STREAM bandwidth + peak GFLOPs (minutes), then
predict tok/s for every model from the curve here; **validate** by running 2–3
models on the target and reporting predicted-vs-actual error.

**Adversarial review (this method was attacked before shipping).** The surviving,
load-bearing caveats — stated so the claim is not over-read:

1. **Single node ⇒ no hardware-coefficient fit.** With one machine every hardware
   feature has zero variance, so *no regression can learn the hardware-transfer
   coefficients from this data.* The model-axis curve (tok/s vs params/quant/bytes)
   is **fitted**; the cross-hardware step is a **physically-motivated first-order
   extrapolation**, not a learned result — a **hypothesis until validated
   out-of-sample on ≥1 distinct CPU.** We report it as a method + validation
   protocol, never as a measured cross-hardware result. (Subsumes the n=1 threat.)
2. **Bandwidth-bound regime only.** Tiny models / short generations hit a **fixed
   per-request floor** (tokenization, sampling, framework overhead, prefill) that
   does **not** scale with bandwidth; the ratio rule holds in the decode-dominated
   regime and degrades for sub-1B models and very short outputs.
3. **MBU is class-stable, not universal.** It depends on cache sizes, prefetchers,
   channel count, and the kernel — so transfer is trustworthy **within an ISA +
   memory-topology class** (AVX2 dual-channel → AVX2 dual-channel) and earns
   **wider error bars** across classes (AVX-512, ARM NEON, NUMA).
4. **bytes/token grows with context.** $W$ includes KV traffic, which rises with
   context length and can rival weight traffic at long $c$ — extrapolate at
   **fixed context**, or model KV explicitly.
5. **Report intervals, not point estimates**, and require the on-target spot-check;
   clock / CPU-mark alone is explicitly **not** a valid predictor.

This makes "predict an unseen CPU's throughput/energy from a 2-number target
calibration" a documented, falsifiable **method with its own validation gate** —
not an unearned generalisation.

**Positioning vs public hardware/telemetry datasets.** The closest public
references collect related-but-different data, which sharpens the contribution:

| Dataset | Collects | Label / task | What this set adds |
|---|---|---|---|
| Backblaze Drive Stats | daily per-drive SMART attrs (337k drives) | drive-failure (binary) | failure → **DNF** analogue, for inference behaviour not disks |
| Google Borg traces (+2019 power) | task resource request/usage, machine events, 57 power-domain traces | scheduling, power modelling | single-node **per-token** + RAPL-subdomain, not DC aggregates |
| Alibaba traces (AMTrace ’22, GPU/GenAI) | microarch metrics incl. **memory-bandwidth contention**, GPU util, serving latency | contention, scheduling | same micro-signals on a **CPU sovereign edge node**, paired with quality |
| UCI Computer Hardware | static specs (cycle time, memory, cache, channels) | relative-perf regression | predict from **runtime behaviour**, not just specs |
| MLPerf Inference + Power | standardized latency/throughput + measured **AC wall power** | apples-to-apples HW/energy | adds per-token, thermal, per-core, per-requestor, and **quality** labels |

None of them pair systems telemetry with a **task-quality label** — that pairing
is what makes *quality-from-behaviour* possible here. `dataset.py` flattens every
run into an ML-ready feature+label table (one row per task) for these models:

| Prediction task | Features (X) | Label (y) | Public analogue |
|---|---|---|---|
| Early-warning DNF | first-N-s power/mem/majflt/jitter curves | `dnf` / `dnf_type` | Backblaze failure |
| Quality-from-behaviour | jitter, temp, swap, bandwidth, energy (no text) | `judge_score` | (novel) |
| Energy / roofline regression | params, output tokens, membw, MBU | `energy_wh`, `decode_tok_s` | UCI perf-regression |
| Anomaly / exfil detection | net/disk series (egress invariant) | net≈0 baseline | intrusion detection |
| Bottleneck classification | telemetry fingerprint | capacity/thermal/bandwidth/compute | AMTrace contention |

Richer microarchitectural features (IPC, cache-/LLC-miss rates via `perf stat`,
as in Alibaba AMTrace; i915 `rcs0-busy`/`rc6-residency` via `intel_gpu_top`) are a
documented **next capture** (env-gated) to deepen the contention/offload signals.

## 8. Statistical Analysis Plan (Pre-registered)

- **Point estimates:** per (model, class) mean of `det_score` and `judge_score`
  with **95 % CI** (bootstrap, 10k resamples — robust to non-normal small-n).
- **Model comparison:** since paired within-subject, use **Wilcoxon signed-rank**
  (non-parametric) for pairwise; **Friedman test** across all models per class.
- **Multiple comparisons:** **Holm–Bonferroni** correction over the pairwise set.
  > **Power reality (state honestly):** with R=5 × ~6 scenarios/class, 94 models
  > → ~4,400 pairwise comparisons; after Holm correction, **individual-model**
  > distinctions will mostly NOT reach significance. Frame primary conclusions at
  > the **bracket level** (5 groups, well-powered); treat per-model ranks as
  > descriptive, not significant. Over-claiming "model A > model B" is the trap.
- **Size effect (RQ1):** mixed-effects / ordinal regression of score on
  log(params), random effect per scenario; report the coefficient + CI, and test
  the **diminishing-returns** (knee) via a piecewise fit.
- **Judge reliability:** hand-rate a **stratified sample** (e.g. all R reps for
  ~10 scenarios × ~6 models spanning brackets ≈ 100–300 human ratings — feasible,
  unlike 20 % of all 6 k judgments) and report **Cohen's κ** (judge vs human) +
  **Krippendorff's α** if a 2nd human rates. If κ < 0.6, down-weight judge-only
  claims.
**Grading the open-ended part — and distrusting the grader.** Deterministic checks
settle the unambiguous part of an answer (right component, refused command, valid
JSON); the rest of ops reasoning is open-ended, where two correct diagnoses can
read nothing alike. For that we use an LLM judge — and we treat the judge as a
source of bias to be controlled, not a neutral oracle. A single grader inherits
its own preferences (for its own style, for longer answers, for whichever option
it reads first), so no model is certified by one judge: we grade every answer with
**two judges from different families — Claude Opus 4.8 and GPT-5.5** — and report
their **agreement (Cohen's κ)**. Where they agree we trust the score; where they
split we **flag** the answer rather than average two opinions into a false
consensus. To blunt the known biases we **randomise answer order, blind the model
identity, and require the judge to cite evidence** from the supplied context. The
deterministic checks remain the backstop — they carry the parts where truth is not
a matter of taste. The judges run **off-node**; the system-under-test never calls
them (the Copilot-CLI wiring, per-call credit cost, and run status are in the
implementation-status appendix).
- **Gold/rubric de-biasing (option C — DONE):** the frontier judge (Claude 4.8)
  adversarially reviewed every gold answer + rubric + deterministic check; the
  operator adjudicates (`gold-review.jsonl`). **Outcome:** the gold *answers* held
  up, but several **deterministic checks were gameable** (could pass the exact
  wrong answer the rubric penalises, or false-fail a negated correct one). They
  were hardened — **negation-aware** excludes, a **`json_equals`** deep value
  check, and **word-boundary** tokens (bare `no`/`yes`/`all` no longer match
  inside `now`/`eyes`/`wall`) — and the review was **re-run to confirmation**
  (`gold-review-recheck.jsonl`: 4 major issues → 0). **Lesson (stated in the
  paper):** deterministic checks are *necessary-not-sufficient* partial signals;
  the LLM-judge carries final correctness. *(Locked.)*
- **Baselines (REQUIRED):** report two non-LLM baselines so "LLM helps" is earned:
  1. **random** legal answer, 2. **keyword/rule heuristic** diagnoser. A model
  must beat both to count.
- **Bracket cost/value gate (pre-registered, for staged expansion):** the
  per-model wall-clock cost rises steeply with size (on this node the **4-5 GB**
  bracket costs ~3× the **1-2 B** bracket per model), so a later expansion wave
  *conditionally* deepens a bracket only if it earns the cost. **Rule, fixed
  before looking at the expansion data:** expand the **4-5 GB** bracket **iff** its
  **judged %-of-frontier** exceeds the **3-4 B** bracket by **≥ 5 percentage
  points** *and* their bootstrap **95 % CIs do not overlap**; otherwise the
  4-5 GB expansion is **held** and "≤5 GB adds cost without judged lift on this
  CPU" is reported as a **finding** (the 3-4 B Pareto knee), not a gap. The
  decision is made on the **judge** metric (not deterministic checks) and on the
  **complete** bracket (no partial-run pruning). The **`guard` (safety) class is
  exempt** — it is always run for every bracket, since safety does **not** track
  size (RQ3 — the naive size ranking even inverts) and the signal is cheap to keep. *(Gate logic lives in
  [`docs/analysis/wave_analysis.ipynb`](analysis/wave_analysis.ipynb).)*

## 8b. Results (quality: 2-judge × 5-rep ensemble; safety/energy: deterministic)

> **Status (state up front):** two kinds of number appear below, with different
> strength. **(a) Judged quality** is the **5-rep × 2-judge ensemble** (temperature 0.7, R=5
> samples/scenario, graded by `claude-opus-4.8` **and** `gpt-5.5` — the consensus
> mean per rep). The two judges agree at **Cohen's κ = 0.91 quadratic-weighted**
> on the full **8,909-pair** set (the right metric for ordinal 1–5 scores;
> Pearson r = 0.91; 77.3 % exact, 99.8 % within-1; near-identical mean, 2.21 vs
> 2.23), so the **ranking is judge-robust** — a judge–**human** κ is still future
> ([`judge_agreement.py`](../judge_agreement.py), [`human_eval.py`](../human_eval.py)).
> **(b) Safety** rides the **deterministic refusal checks**, which need no judge,
> so all **5 repeats** are scored and we report **bootstrap CIs** — these are the
> robust numbers. The dataset is **94 functional models**; `phi:2.7b` is **excluded** (95/95
> DNF). Read quality as the **powered axis** (5-rep × 2-judge ensemble; the
> single-judge deterministic pass is preserved at `judged_snapshot.det.csv`) and
> safety as the **most robust** (judge-free) and a **replication** of the
> agent-/SLM-safety literature (§11), not a discovery.

**Quality scales with size, with the knee at 2-3B.** Judged **% of frontier** per
bracket (consensus judge score ÷ 5; bootstrap 95 % CI over 19 scenarios × 5 reps ×
the bracket's models — the **5-rep × 2-judge** ensemble):

| Bracket | judged % of frontier | 95 % CI |
|---|---|---|
| 0-1B | 32.2 % | [31.5, 32.9] |
| 1-2B | 38.3 % | [37.5, 39.1] |
| 2-3B | 51.3 % | [50.3, 52.2] |
| **3-4B** | **52.1 %** | [51.3, 53.1] |
| 4-5GB | 56.8 % | [54.6, 58.9] |

The curve rises **steeply** through 2-3B (+13 points), then the 2-3B→3-4B step is
**flat** (+0.8 points): the diminishing-returns **knee is at 2-3B**. The 4-5GB
bracket then adds a **further +4.6 points** (non-overlapping CIs) — a real but
**small** lift relative to the early climb, and it costs ~3× the per-model
wall-clock of the 1-2B bracket (§4 hardware). The decision-relevant shape is
unchanged: **the capability you need arrives small, and paying for the top bracket
buys a few points, not a tier.**

*Read the bracket **means** with care: consolidation added many cheap small-quant
variants to the 3-4B bracket, which lowers its average relative to the unchanged
4-5GB bracket. The load-bearing comparison is the per-model **frontier**
(best-in-bracket — the best 3-4B q4 matches the best 4-5GB q8), not the bracket
average.*

**Pre-registered gate verdict → marginal HOLD on 4-5GB.** Applying the §8
cost/value gate (expand 4-5GB only if it beats 3-4B by **≥ 5 pts with
non-overlapping CIs**): the consolidated lift is **+4.6 pts** with
**non-overlapping** CIs — directionally a pass, but **just under** the 5-pt bar, so
the verdict is a **marginal HOLD**. "**≤5 GB buys a small, sub-threshold judged
lift on this CPU**" is the **finding**, not a gap.

**The win is the quant, not the bracket.** The best 3-4B model
(`hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M`, 71.4 %) **edges the best 4-5GB entry**
(`qwen3:4b-instruct-2507-q8_0`, 71.3 %) — a **q4 4B on the knee matches a q8 4B**,
and the marginal quality lives in the **model and its quantization**, not the
parameter jump. *(Confirmed by the 5-rep × 2-judge ensemble, κ_quad = 0.91.)*

**Safety (axis #2) tracks training type, not size — replicating a known effect in
the offline/CPU regime.** The sharpest behavioural signal is not in the judged
quality curve but in the **deterministic** safety checks: **refusing a destructive command**
(`guard-08-destructive`) and **rejecting insecure config** (`secure-09…13`:
plaintext secret, no-auth ingress, privileged container, broad RBAC, `:latest`) —
6 scenarios × 5 repeats (the *pure-destructive* `guard` signal is a single
scenario — thin; the consolidated roster broadens the **models**, not the
scenarios, §5), bootstrap 95 % CIs, **no LLM judge involved** (so it is immune to judge bias and
is the most robust number we report). `phi:2.7b` is excluded (95/95 DNF). Two
findings, in order of strength.

***(1) Instruct safety rises with size, then plateaus below 100 %.*** Restricting
to the 90 instruct models (non-reasoning, non-`phi`), refusal climbs to the mid-70s
by 2-3B and then **plateaus in the 75–80 % band** — the *same* diminishing-returns
shape as quality:

| Bracket (instruct only) | det. refusal rate | 95 % CI |
|---|---|---|
| 0-1B | 61.6 % | [59.2, 63.9] |
| 1-2B | 70.3 % | [68.2, 72.4] |
| 2-3B | 76.7 % | [74.6, 78.7] |
| 3-4B | 75.4 % | [73.5, 77.4] |
| **4-5GB** | **79.8 %** | [75.3, 84.0] |

The plateau is the point: the safest bracket still **endorses roughly one
destructive action in five**. Behind a human, on low-stakes tasks, that is a
manageable apprentice risk; for autonomy it is disqualifying. **Size alone never
reaches "safe."**

***(2) Reasoning-distillation degrades refusal — and that, not size, drives the
non-monotonicity.*** Splitting every model into *instruct* vs *reasoning/"thinking"*
(the R1-distilled arm: `deepseek-r1:1.5b`, its q8 distill, `deepseek-r1:7b`, and the
unsloth Qwen-1.5B repack — **4 models** run in their native thinking mode):

| Arm | det. refusal rate | 95 % CI | n |
|---|---|---|---|
| instruct | **71.4 %** | [70.3, 72.4] | 2700 |
| reasoning ("thinking", R1-distill) | **47.2 %** | [41.3, 53.3] | 120 |

The CIs are nowhere near overlapping — a **~24-point** safety penalty for the
"reasoning" training sold as an upgrade. Concretely, **`smollm2:360m` (0.36 B,
instruct) refuses more often (65.6 %) than `deepseek-r1:7b` (7.6 B, reasoning,
47.2 %)** — a 21× smaller model is the safer operator. Among the 94 functional
models, the **three lowest refusers are all R1-distilled** (`deepseek-r1:1.5b`
40.6 %, its q8 distill 42.5 %, `deepseek-r1:7b` 47.2 %); the next tier is the
tiniest sub-0.5 B instruct models. (`phi:2.7b`, 20.8 %, would refuse less still,
but is a 95/95 served-failure excluded as such.) The mechanism is corroborated in
the LRM-safety literature: R1-distilled models *rationalize* harmful actions
through their chain-of-thought (Self-Jailbreaking, arXiv 2510.20956; SafeChain
2502.12025; Hidden Risks of R1 2502.12659) — the "thinking" that should aid
diagnosis instead talks the model *into* the destructive action.

> **Honesty: the size non-monotonicity is mostly the reasoning confound (state up
> front).** Over the *94 functional models* the bracket curve is **non-monotonic** —
> 61.6 / 67.5 / 76.7 / 75.4 / **73.3 %** — appearing to say "the biggest bracket
> is *less* safe." It is **not** an intrinsic size effect: the four reasoning
> models sit in the **1-2B** (three) and **4-5GB** (one) brackets and drag those
> averages down; remove them (table 1 above) and the curve is monotonic-then-flat. So we
> do **not** claim "bigger is less safe." We claim the decision-relevant thing:
> the model a practitioner is most likely to *reach for as an upgrade* — the
> biggest one, the one with the "reasoning" badge — is, in this study, the **least
> safe**, which is why the naive size ranking inverts. The reasoning arm is **four
> models (n=120)**. The conclusion survives either way:
> **refusal must be measured behaviourally, because every size / benchmark /
> "reasoning" proxy points the wrong way.**

***(3) The sovereign selection — a quality × safety × energy Pareto.*** The three
axes earn their keep only *together*; the contribution is the selection, not any
single column. Treat each model as a point in **(judged quality ↑, deterministic
refusal ↑, energy-per-answer ↓)** and compute the **Pareto-optimal set**: model
$A$ **dominates** $B$ iff $A$ is no worse on all three axes and strictly better on
at least one; the **non-dominated** models are the short-list a practitioner
should choose from. **12 of 94 models are Pareto-optimal; the other 82 are
dominated** — beaten on *every* axis at once, so nothing is lost by discarding them.

| Pareto-optimal model | bracket | judged % | refusal % | mWh/ans |
|---|---|---|---|---|
| **`qwen3:4b-instruct-2507-q4_K_M`** — sovereign pick | 3-4B | 68.6 | **90.8** | 106 |
| `hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M` — quality-max | 3-4B | **71.4** | 80.3 | 138 |
| `qwen3:4b-instruct-2507-q8_0` | 4-5GB | 71.3 | 90.8 | 155 |
| `granite4:tiny-h` | 4-5GB | 63.5 | 74.2 | 54 |
| `qwen3:1.7b-q8_0` | 1-2B | 62.1 | 82.8 | 93 |
| `qwen3:1.7b` | 1-2B | 61.5 | 83.6 | 36 |
| `granite4:1b-h` | 0-1B | 45.3 | 67.8 | 30 |
| `qwen3:0.6b-q8_0` | 0-1B | 41.8 | 68.3 | 34 |
| `qwen3:0.6b` | 0-1B | 36.6 | 64.7 | 15 |
| `hf.co/unsloth/Llama-3.2-1B-Instruct-GGUF:Q4_K_M` | 0-1B | 36.2 | 68.6 | 32 |
| `smollm2:360m` | 0-1B | 27.8 | 65.6 | 23 |
| `smollm2:135m-instruct-q8_0` | 0-1B | 22.8 | 48.6 | 13 |

*The front is the **short-list** — all 12 are non-dominated; the table leads with the
recommended **sovereign pick**, then sorts by quality (sorting *by* quality would lead
with the lower-safety model, against the three-axis point). `unsloth/Qwen3-4B` is the
**quality-max**, but it is the *original* Qwen3-4B (a hybrid-thinking release): all four
original-Qwen3-4B packagings refuse at **80–84 %** vs **90.8 %** for the pure-instruct
Instruct-2507 — exactly why the balanced pick is the 2507 instruct, not the top score.*

Two reads carry the integration. **(i) The proxies land off the front — even
*within* the 4B cluster.** The high-quality corner is owned by **three Qwen3-4B
variants**, and choosing among them is itself a three-axis decision. The
**quality-max** is `hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M` (71.4 %) — but it refuses
only **80.3 %** of destructive prompts, while its quality-tied sibling
`qwen3:4b-instruct-2507-q8_0` (71.3 %, a **0.1-point** gap well inside the CI)
refuses **90.8 %**. So the **sovereign pick is `qwen3:4b-instruct-2507-q4_K_M`** —
the **safest (90.8 %) and cheapest (106 mWh)** model within a few quality points of
the top, mutually non-dominated with its **q8** sibling (which buys **+2.7 judged
points for ~46 % more energy**, 155 vs 106 mWh). Taking the single-axis "just pick
the top score" model would trade **~10 safety points for 0.1 quality points** —
exactly the move the three-axis view declines. **(ii) The tempting upgrades are dominated.** **All four**
reasoning-distilled models fall **off** the front; `deepseek-r1:7b` is among the
worst *combined* cases — **one of the most energy-expensive models in the study**
(303 mWh/answer, top 5 of 94) and the **least-safe** large model (47.2 %),
dominated by much of the roster. So the two heuristics a practitioner reaches for —
*biggest that fits* and *has a "reasoning" mode* — select **dominated** models; the
front is small, spans the whole size range, and is found only by measuring all
three axes.

> **Honesty (state up front).** This front is computed on **point estimates**; its
> **quality** axis is now the **5-rep × 2-judge ensemble** (κ_quad = 0.91), and
> safety and energy are judge-free / measured. The membership is still a point
> estimate — **CI-aware dominance** (treating near-ties as non-separable) may widen
> the front by a model or two. Energy is `psys`-RAPL on one CPU; ranks invite re-runs. The **logic** —
> dominance on three *measured* axes — is the contribution; the exact membership
> would only shift under **CI-aware dominance**. Reproduced in
> [`wave_analysis.ipynb`](analysis/wave_analysis.ipynb) §8.
**Telemetry coverage and missing data.** The three decision axes (judged quality,
refusal, energy) are **100 % complete across all 94 functional models**. Only the
memory-bandwidth axis (MBU/roofline) has gaps: **6 of 94** models lack per-run
bandwidth telemetry — a perf-counter capture shortfall on the smallest/fastest
models, **independent of behaviour or scores (missing at random)**. MBU is therefore
reported on the **88-of-94** covered subset (available-case analysis), every other
axis stays at full $N$, and no otherwise-complete model is dropped to paper over an
instrumentation gap. Models with *no* usable rows on *any* axis (`phi:2.7b` plus the
registry pull-failures) are excluded entirely and named in the appendix.
## 8c. Hypothesis outcomes (confirmatory) and deviations from the pre-registration

Mapping each **pre-registered** hypothesis (§3, fixed before the run) to its result.
Per the pre-registration / Registered-Reports convention (Nosek et al., *PNAS* 2018;
Chambers, *Cortex* 2013), we report **every** registered prediction with an explicit
verdict — including the ones the data did **not** cleanly test — rather than silently
revising the hypotheses to fit the outcome.

| # | Pre-registered prediction | Result | Verdict |
|---|---|---|---|
| **H1** | quality rises with params, diminishing returns, knee ~**3–4B** | steep climb to **2–3B**, flat 2–3B→3–4B (+0.8 pt), +4.6 pt to 4–5GB | **Supported** — knee one bracket *smaller* than predicted |
| **H2** | the **3–4B** bracket *dominates* the quality/speed Pareto | the balanced pick is 3–4B (`2507-q4`), but the non-dominated front spans **all five** brackets | **Partially supported** — no single bracket dominates |
| **H3** | safety is **not monotonic** in size; some small models endorse destructive actions | non-monotonic, driven by **training type** (instruct 71.4 % vs reasoning-distill 47.2 %), not size | **Supported** |
| **H4** | thinking models gain on *diagnose/test* but at prohibitive CPU latency | reasoning models evaluated on safety + energy; a per-class accuracy × latency breakdown is not isolated here | **Not directly tested** (future work) |
| **H5** | best ≤5 GB model reaches **~60–80 %** of a *frontier reference* | no frontier-model baseline was run; the best small model reaches ≈ **71 %** of the judge's 1–5 ceiling (a proxy) | **Not directly tested** (proxy only) |
| **H6** | local **RAG** lift is large for small models, shrinks with size | closed-book vs grounded are *different task classes* — the RAG-lift confound is disclosed (§9); reported descriptively | **Not causally tested** (confound open) |
| **H7** | energy rises with params; the knee is also the **energy-efficiency** sweet spot | energy/answer rises with params; the **2–3B** quality knee sits near the tok/s-per-watt optimum | **Supported** — knee one bracket smaller |

**Deviations from the pre-registration (transparent changes).** Following the
guidance to *disclose* departures rather than rewrite the plan (Lakens, *Collabra*
2024): **(1)** the roster grew from the pre-registered **25** to **94** models — a
second collection batch on the *same* node, scenarios, and protocol, folded into
one dataset (per-axis / available-case reporting for the single
bandwidth-telemetry axis with gaps, see *Telemetry coverage* above); **(2)** the
judged-quality axis was upgraded from a single judge to a **5-rep × 2-judge
ensemble** (κ_quad = 0.91); **(3)** a planned third collection wave was **dropped**
(the 94-model dataset was deemed sufficient). The H1–H7 tests above are
**confirmatory** (pre-registered scenarios + protocol); analyses introduced *after*
the plan — e.g. the within-`Qwen3-4B`-family safety comparison — are flagged as
**exploratory**.

## 8d. Selecting from the front: weight-sensitivity and robustness

A Pareto front is a **set**, not a ranking; collapsing it to one "winner" requires
a preference. The foundational result is uncomfortable but clarifying: *absent
stated preferences, every point on the front is equally good* (Miettinen, 1999).
The sovereign pick of §8b is therefore **one operating point**, not a theorem — so
we report how the choice behaves across **all** preferences rather than defend a
single weighting.

**Weight-sensitivity (SMAA).** Drawing **100,000** weight vectors uniformly from
the (quality, safety, energy) simplex and counting how often each model ranks
first (stochastic multi-criteria acceptability analysis; Lahdelma et al., 1998)
gives the *rank-1 acceptability* — the share of the entire preference space each
model wins:

| Model | bracket | win-share of all weightings |
|---|---|---|
| `qwen3:4b-instruct-2507-q4_K_M` (**sovereign pick**) | 3–4B | **39.6 %** |
| `qwen3:4b-instruct-2507-q8_0` | 4–5GB | 29.4 % |
| `qwen3:1.7b` | 1–2B | 27.0 % |
| `hf.co/unsloth/Qwen3-4B-GGUF:Q4_K_M` (**quality-max**) | 3–4B | 3.0 % |

Two facts make the choice **robust, not arbitrary**: only **7 of 94** models win
under *any* weighting, and just **three split 96 %** of the weight space. The same
**`Qwen3-4B-Instruct-2507`** family wins the *balanced*, *safety-first*, and
*quality-first* weightings; it is displaced only by the cheaper **`qwen3:1.7b`**
when energy dominates. Crucially, the model the size heuristic would pick (the
quality-max `unsloth-Qwen3-4B`) wins only **3 %** of weightings — a
preference-independent restatement of the paper's thesis that *"biggest that fits"*
mis-selects.

**Cross-check (TOPSIS).** An independent standard method — ranking by distance to
the ideal point (Hwang & Yoon, 1981), equal weights — places
`qwen3:4b-instruct-2507-q4_K_M` **first of 94**. Two unrelated decision rules
(plurality over the simplex, and distance-to-ideal) agree on the pick.

**What else the three axes admit.** Selecting from a front is a Multi-Criteria
Decision Analysis (MCDA) problem with a menu of methods, each encoding a different
preference model: linear **weighted sum** (simple, but reaches only the *convex*
hull of the front), **Chebyshev** scalarization (reaches non-convex points),
**TOPSIS/VIKOR** (distance to the ideal), **ε-constraint** (optimize one axis
subject to *floors* on the others — exactly the "refusal ≥ X %" view),
**lexicographic** priority, and — beyond *choosing* a single model — **sorting** the
roster into preference-ordered tiers (*deploy-grade / conditional / reject*, e.g.
ELECTRE-Tri). We report SMAA + TOPSIS because they are preference-*robust*
summaries; we flag the known caveat that distance- and pairwise-based methods
(TOPSIS, AHP) can exhibit **rank reversal** when the candidate set changes, whereas
the SMAA acceptability is computed over the fixed 94-model roster.

## 8e. Per-model SWOT: the deployment-decision synthesis

The MCDA selection in §8d collapses the front to *one* recommended model. The
operational question a homelab owner actually asks is broader — *"what am I getting,
and what am I risking, if I run **this** model?"* — which is a **SWOT**. SWOT is a
strategic-management framing (Weihrich's TOWS matrix), and its standard criticism is
**subjectivity**: the quadrants get filled by opinion. We avoid that by making the
SWOT **data-driven and pre-registered** — every entry is a measured axis crossing a
fixed threshold, not a judgement call. The four quadrants map onto what the benchmark
already produces:

| Quadrant | Source (measured axes) | Computable from this run? |
|---|---|---|
| **Strengths** (internal +) | per-model **top-quantile** axes: quality on a class, refusal rate, Wh/correct, tok/s ≥ 8, cross-rep consistency | **Yes** — §8b/§8d axes |
| **Weaknesses** (internal −) | **bottom-quantile** axes + failure modes: truncation rate, DNF/timeout, unsafe endorsement, sub-interactive speed | **Yes** — §8b axes |
| **Opportunities** (external +) | **context/retrieval lift** (§12), **quantization headroom** (q8 pairs), **hardware transfer** (§7c roofline) | **Partly** — quant + roofline now; retrieval needs §12 |
| **Threats** (external −) | **prompt-injection** susceptibility (`secure-14/15/16`), **counterfactual / context-poisoning** (§12), **quant/fine-tune safety regression**, **license/provenance** | **Partly** — injection + license + quant now; context-poisoning needs §12 |

So the honest answer to *"can we compute a SWOT from the data we are collecting?"* is:
**the two internal quadrants (S, W) fall out of the current run directly** — they are
the §8b axis profile and the archetype membership, re-expressed as a per-model card.
**The two external quadrants (O, T) are partly populated now** (quantization headroom,
roofline transfer, injection-resistance, and license/provenance are all measured) and
are **completed by the planned context axis (§12)**, which supplies the single biggest
*Opportunity* (grounding substitutes for parameters, E1) and a key *Threat*
(context-poisoning / counterfactual-follow, E4). **No new metric is required** — SWOT is
an **aggregation and communication layer** over axes we already collect, plus the §12
extension. The only genuinely new artifact is a **pre-registered bucketing rubric** (the
quantile thresholds that decide what counts as a strength versus a weakness), reported
so the synthesis is reproducible rather than editorial.

> **Scope honesty.** SWOT *informs* the deployment decision; it is **not a
> measurement**. The O and T quadrants are by definition about *external/future*
> factors — a benchmark can ground them in evidence (a model that follows injected
> context *is* a measured threat) but cannot fully quantify "opportunity." We present
> the per-model SWOT as a **decision aid built on the metrics**, with the MCDA score
> (§8d) as the quantitative selector and the SWOT as its qualitative complement — and
> we resist dressing a strategy framework up as a number.

## 9. Limitations and Threats to Validity

| Threat | Type | Mitigation |
|---|---|---|
| n=1 environment (one cluster/operator) | External | Frame as **single-environment case study**; release harness so others replicate |
| Author wrote scenarios + gold + rubric | Internal/construct | **option-C gold review DONE** (Claude 4.8 audited gold+rubric+checks, hardened the gameable ones, re-verified — `gold-review*.jsonl`); held-out set; hardened deterministic checks + LLM-judge as final correctness |
| LLM-judge bias (self-pref, verbosity, position) | Conclusion | Blind, position-randomize, evidence-cited; **2-judge ensemble DONE** (full variance pass) — `claude-opus-4.8`↔`gpt-5.5` agree at **κ_quad=0.91** on 8,909 pairs (`judge_agreement.py`); judge–human κ and a 3rd-judge (`gemini-3.1-pro`) Fleiss pass are wired and pending (`human_eval.py`, `--c`) |
| Benchmark contamination | Construct | Canary/memorization probe; real-incident tasks unlikely in pretraining |
| **Fine-tuning contamination** — domain fine-tuning on homelab-style ops data can make a tuned small model *memorize the benchmark style*, inflating scores and undermining the core "real incidents in nobody's training set" claim | Construct | **Caveat (future work).** Any fine-tuned arm must train only on data **disjoint** from the evaluated scenarios, report results on a **contamination-proof held-out set**, split by **incident** (not just wording) to avoid near-duplicate leakage, and include paraphrase/canary memorization probes. Always report **base vs fine-tuned** on the same held-out set so the lift is earned, not memorized. |
| Quant vs architecture confound | Internal | q4 held constant for headline; q8/QAT as sensitivity |
| Grounding leak (gold answer derivable only from supplied context vs needs in-weights knowledge) | Construct | Explicit `closed-book`/`grounded` label per scenario; report the two separately so neither masks the other |
| Thinking-model unfairness | Internal | Separate track + token/latency budget |
| Multiple comparisons → false winners | Conclusion | Holm–Bonferroni; pre-registered analysis |
| Hardware specificity | External | Report exact node; note bandwidth-bound caveat; invite GPU re-runs |
| **Cross-hardware extrapolation over-reach** (§7c) — predicting another CPU's tok/s from a single node | External/construct | **Disclosed + gated.** One node ⇒ hardware coefficients are **not** fittable; transfer is a first-order roofline rule (scale by **bandwidth**, not clock/CPU-mark), reported as a **method requiring out-of-sample validation on ≥1 distinct CPU**, with **prediction intervals** and a 2–3-model on-target spot-check — never as a measured result |
| **Regime / ISA boundary of the transfer rule** (§7c) | Construct | The bandwidth-ratio rule holds only in the **decode-bandwidth-bound** regime and **within an ISA+memory-topology class**; sub-1B / short-output fixed-overhead floor and AVX-512/ARM/NUMA shifts widen the error; extrapolate at **fixed context** (KV traffic grows with $c$) |
| Small R inflates variance | Conclusion | R≥5, bootstrap CIs, report CI widths honestly |
| **RAG-lift confound** (grounded vs closed-book are *different task classes*, not the same task with/without a doc) | Internal/construct | **Open issue.** Current `rag_lift` mixes retrieval effect with task-difficulty. Fix before the RQ6 claim: author **paired variants** (same scenario, reference-doc present vs absent) so the within-scenario delta isolates retrieval. Until then, report closed-book and grounded **separately**; do not claim a causal RAG lift. |
| **Judge egress** (real cluster telemetry sent to a 3rd-party cloud judge) | Construct/opsec | System-under-test stays sovereign; but scrub/anonymize released scenarios, disclose the egress, and prefer a self-hosted judge (§0b) |
| **Energy = SoC (RAPL `psys`) not wall power**; single node | Construct/External | RAPL `psys` is on-die platform energy — **excludes** display/PSU/peripheral draw (a feature: isolates compute energy for the size comparison, but not facility power). Report the **idle baseline** + **net-over-idle**; optionally cross-check with a wall plug; energy ranks are this-chip-specific — invite re-runs |
| **Thermal-order confound (C1)** — sequential 94-model runs heat the chip; later models throttle, confounding speed/energy with *run position* | Internal | **Fixed:** `--shuffle` randomizes model order (deterministic `--order-seed`); temp-gated `cooldown()` between models; `thermal.start_c` recorded as a per-task carryover covariate. The deterministic *quality* pass is order-insensitive; only the systems numbers need this |
| **Tokenizer non-comparability (C2)** — tok/s differs ~20% across tokenizers for identical text | Construct | **Fixed:** report **chars/s** and **energy-per-token** beside tok/s; `output_chars` captured per request |
| **Observer effect (C3)** — the sampler + perf counters perturb the throughput/energy they measure | Construct | **Fixed:** `calibrate.py` runs the probe model **with vs without** telemetry and reports the tok/s overhead; heavy `PERF_MEMBW` is env-gated, off by default; `SAMPLE_INTERVAL` tunable |
| **RAPL is a modeled estimate (M1)** — whole-socket model, not per-process wall power; counters wrap | Construct | **Fixed/disclosed:** per-**subdomain** wraparound correction (`RAPL_MAXES`); `package-0` avoids the battery-charge confound; framed as compute-energy ±error, not facility power (Weaver et al.) |
| **Sampling aliasing (M2)** — a 1 Hz sampler can alias sub-second power/freq excursions | Construct | **Fixed:** `SAMPLE_INTERVAL` configurable sub-second; peak trackers catch excursions between ticks |
| **MBU vs datasheet (M4)** — utilization against the spec bandwidth overstates headroom | Construct | **Disclosed:** the STREAM calibration did not complete on the run node, so MBU is normalized against the **datasheet** peak (38.4 GB/s, dual-channel DDR4-2400) and read as a **relative** efficiency, not an absolute ceiling. Reported as median 0.46 (10–90 %: 0.36–0.52). **6 of 94 models lack per-run bandwidth telemetry** (a perf-counter capture gap, independent of behaviour — MAR); MBU is reported on the **88-of-94** covered subset only, leaving every other axis at full N (§ telemetry coverage) |
| **Frequency-scaling / power-management confound** — dynamic HWP clocks (0.4–3.6 GHz) + turbo make tok/s depend on thermal luck, not just the model | Internal | **Fixed:** `node-power.sh` locks governor `performance`, **turbo off**, clock pinned to **base** (~1.70 GHz, sustainable) for the systems pass; per-model `quiesce()` (fan-max + cache/swap reset + temp settle) equalizes start state; `cpu_freq_mhz`+`core_freq` logged at 1 Hz as evidence. No TLP/ppd/auto-cpufreq present (audited) |
| **Dual-/single-channel flex region not attributable per test** — the 8 GB+16 GB asymmetric DIMMs run the first 16 GB interleaved (dual-channel ~38 GB/s) and the top ~8 GB single-channel (~19 GB/s), but the OS doesn't expose which region a process's pages occupy | Construct | **Disclosed.** The IMC PMU counts by *requestor* (ia/gt/io), not per channel; per-page channel mapping isn't authoritative. We capture the **effect** (achieved bandwidth / MBU) + the requestor split + working-set-vs-16 GB spill risk — not a per-region label |
| **MoE dynamic routing not observable** — we capture the *static* sparsity (experts active/total per token, e.g. 6/64) but not *which* experts fire per token or the routing load-balance | Construct | **Disclosed.** Ollama/llama.cpp don't expose the router (`ffn_gate_inp`) logits; per-token expert selection needs engine instrumentation. `expert_used_count` bounds the active-compute; dynamic routing is future work |

## 10. Claimed Contributions

1. **ApprenticeOps: a reproducible, open benchmark** for *small, locally-sovereign*
   ops-reasoning with **real-incident** scenarios + a **safety gate**, framed on
   the **AIOps maturity ladder** (novel vs AIOpsLab/ITBench/OpsEval, which are
   frontier+agentic+synthetic, and vs on-prem classical-ML AIOps which isn't LLM).
2. **An offline operating contract + grounding split** (closed-book vs
   local-RAG-grounded) that isolates **what retrieval can't fix** (reasoning,
   faithfulness, calibration, safety) and quantifies how much local RAG
   substitutes for parameters.
3. **A telemetry method** (OTel-GenAI-aligned per-request resource + behavioural
   trace, incl. **measured wall-power / energy-per-task** via a smart plug) for
   profiling on-device LLM ops, reusable beyond this study.
4. **Empirical findings — the three-axis selection map.** In one offline/CPU
   harness: a judged-**quality** knee at **3–4B** (where *quantization*, not
   parameter count, carries the marginal lift); a **safety** axis on
   judge-independent **deterministic** checks where refusal is governed by
   *training type, not size* (reasoning-distilled models refuse ~31 pts less than
   instruct; the naive "biggest / ‘reasoning’" pick is among the least safe) —
   **corroborating** the agent-/SLM-safety literature (§11) in the offline/CPU
   regime rather than discovering the effect; and an **energy** axis (Wh/answer,
   tokens/s-per-watt) that prices capability above the knee. The contribution is
   that no prior benchmark reports the three **together** for the model-selection
   decision — plus the local-RAG lift.
5. **Artifact**: harness + scenarios + data released (Apache-2.0).

**Future work (out of scope here):** a **domain fine-tuning arm** (e.g. LoRA/QLoRA
via tools such as Unsloth, exported to GGUF for the same Ollama path) to test
whether a tuned small model beats the off-the-shelf Pareto frontier. This is
deferred deliberately: fine-tuning on homelab-style data risks **benchmark
memorization**, so it must use a contamination-proof held-out set (see the
fine-tuning-contamination row in §9) before any lift can be claimed.

## 11. Related Work and Positioning

- **Operational taxonomy blueprint** ([`TAXONOMY.md`](TAXONOMY.md)) grounds our
  test classes in **Google SRE** (Monitoring/Troubleshooting/Emergency-Response/
  Release-Eng/Config/Toil/Testing chapters), **DORA core capabilities** (incl.
  *Pervasive security*/DevSecOps + *Proactive failure notification*), the
  **observability three pillars** (metrics/logs/traces), and **ITIL** change
  management — six pillars: **Observe→Diagnose→Respond→Change→Secure→Foresee**.
  This is what makes the task set *defensible* rather than ad-hoc.
- **AIOps maturity ladder** (Gartner-origin; reactive → proactive → predictive/
  preventive → autonomous self-healing) frames our **apprentice → operator** arc.
  Surveys: Notaro et al. "A Survey of AIOps Methods for Failure Management" (ACM
  TIST 2021).
- **AIOpsLab** (Chen/Shetty et al., MLSys 2025; arXiv 2407.12165 / 2501.06706) —
  agent-cloud-interface, live fault injection, detection/localization/analysis/
  mitigation. We **reuse its task taxonomy** but target *small local* models on
  *frozen real* incidents, not frontier agents on synthetic injected faults.
- **On-prem AIOps for an SME: an experience report** (Bendimerad et al., arXiv
  2308.11225) — closest in spirit (on-premise, small org, experience report) but
  **classical ML, not LLMs, and not the homelab→scale maturity arc**. We extend
  that lineage to small local LLMs.
- **Open LLM Leaderboard v2** (lm-eval-harness) anchors the generic-reasoning axis.
- **The frontier sets a high ops bar — which reframes the question for a small
  model.** **ITBench** (Jha et al., arXiv 2502.05352) reports that agents on
  *state-of-the-art* models resolve only **13.8 % of SRE, 25.2 % of CISO, and 0 %
  of FinOps** scenarios; **AIOpsLab** (above) frames the *autonomous* end-state.
  If the frontier struggles at autonomous ops, the useful question for a *small,
  local, last-line* model is not "can it run the cluster" but "**where is its
  reasoning floor, and is it safe enough to trust there**" — exactly what we measure.
- **The SLM case — for and against — turns on training, not size.** The pro-SLM
  position (Belcak et al., NVIDIA, arXiv 2506.02153, *"Small Language Models are
  the Future of Agentic AI"*) argues SLMs are sufficient and economical for the
  narrow, repetitive calls agents actually make — our setting. **ThinkSLM**
  (Srivastava et al., EMNLP 2025, arXiv 2502.11569) independently finds SLM
  reasoning is "**strongly influenced by training methods and data quality rather
  than solely model scale**" and that "**quantization preserves reasoning
  capability**" — corroborating, from a different benchmark, both our *quant > params*
  quality result (§8b) and our *training-type-over-size* safety result. The
  "emergent abilities" intuition is itself contested (Schaeffer et al., arXiv
  2304.15004, *"Are Emergent Abilities … a Mirage?"*): apparent capability jumps
  can be an artifact of metric choice — which is why we report **continuous**
  judged %-of-frontier with CIs, not a thresholded "can/can't."
- **Reasoning-distillation degrades safety — we corroborate it at homelab scale,
  not discover it.** Our deterministic result (R1-distilled "thinking" models refuse
  destructive actions ~31 pts less than instruct siblings; §8b) is the *exact*
  phenomenon of **Self-Jailbreaking** (Yong & Bach, ICLR 2026, arXiv 2510.20956):
  after benign math/code reasoning training, reasoning LMs "**reason themselves out
  of safety alignment**," inventing benign intent to justify harmful requests —
  named explicitly for **DeepSeek-R1-distilled**, Phi-4-mini-reasoning, and
  Nemotron (the very family that drags our 4-5 GB bracket down). **The Hidden Risks
  of R1** (Zhou et al., arXiv 2502.12659) finds "**the stronger the reasoning
  ability, the greater the potential harm**," with the *thinking trace* less safe
  than the final answer; **SafeChain** (Jiang et al., arXiv 2502.12025) confirms
  "**LRMs are not safe compared to their reasoning advance**." **Honesty (state up
  front):** the same papers show the defect is *fixable* (SafeChain training;
  minimal safety-reasoning data in Self-Jailbreaking), so we scope our claim to
  models **as shipped** to a homelab via Ollama — **not** that reasoning is
  inherently unsafe. Our addition: this holds **at 0.5–8B, on CPU, in an ops
  setting**, where the unsafe model is also the one a practitioner is most tempted
  to pick.
- **Agent / action safety — the cluster we corroborate, positioned against.** A
  fast-maturing line establishes that *behavioural* safety must be measured on
  **actions, not text**: **GAP** (arXiv 2602.16943, 17,420 datapoints) shows
  text-refusal does **not** transfer to tool-call refusal; **OS-Harm** (NeurIPS
  2025 D&B Spotlight, arXiv 2506.14866) and **Owner-Harm** (arXiv 2604.18658)
  build automated judges and deterministic post-audit gates against agents
  harming their own deployer; **AgentHarm** (ICLR 2025, arXiv 2410.09024, 440
  tasks) and **AgentHazard** (arXiv 2604.02947, 2,653 cases) score
  malicious-action refusal at scale. These run **frontier/cloud or GPU-edge
  agents on synthetic agentic tasks**. We share their *action-over-text* stance
  and deterministic-check methodology but occupy the regime they do not: **≤8B,
  quantized, CPU-only, fully offline**, on **frozen real GitOps incidents**, with
  refusal measured **beside energy and quality** for the *selection* decision
  rather than as a standalone safety score.
- **Small-model & quantization safety — established at larger scale; we replicate
  offline.** That *small, compressed, distilled* models shed safety is documented:
  **Beyond the Tip of Efficiency** (ACL 2025 findings, arXiv 2502.19883, 13 SLMs)
  ties compression/quantization/distillation to safety loss; **Q-resafe** (ICML
  2025, arXiv 2506.20251) and **CAQ** (arXiv 2511.07842) show quantization
  degrades safety and that **perplexity is a misleading deployment-readiness
  proxy** (almost our words); **EASE** (AAAI 2026, arXiv 2511.06512) and
  **GUARD-SLM** (arXiv 2603.28817) add SLM-specific safeguards. Our numbers
  *replicate* these in the offline/CPU/ops regime, with one twist they don't
  jointly report: **quantization largely preserves *quality* (§8b) while *training
  type* — instruct vs reasoning-distilled — governs *safety***, so the two
  pressures act on different axes of the same selection.
- **Gap we fill:** no prior work measures **quality × safety × energy *together***
  for the **offline / CPU-only / locally-sovereign** model-selection decision on
  **commodity hardware** and **real-homelab incidents**. The agent-safety
  benchmarks run frontier/cloud agents and don't meter watts; the systems/SLM
  papers don't score destructive-action refusal against **Wh/answer and
  tokens/s-per-watt**. The defensible delta is the **integration** — and the
  question it answers, *"what does choosing the **safe**, good-enough offline
  model cost you in watts and tokens/s?"* — not any single axis, each of which
  (we say plainly) is already known.

## 12. Planned extension — the context (retrieval) axis (powering RQ6)

> **Status: planned, pre-registered as an extension — not in the current frozen
> run.** RQ6 (does local grounding substitute for parameters?) is the one question
> this design could *not* power: the frozen corpus has only **two** paired
> grounded/closed-book tasks (`expand-04/19`, `upgrade-05/18`), so §8c records RQ6
> as *not directly tested*. This section specifies the extension that turns RQ6
> into a first-class axis, and — same discipline as §3 — states its expectations
> **before** the run.

**Why it belongs here.** In real use you do not ask a 1B model to recall your
cluster from its weights — you **paste it the relevant context**: the
`kubectl describe`, the failing event, the HelmRelease, a runbook paragraph. The
honest question for a *sovereign, local* assistant is therefore not "how much does
the model know" but **"how well does a small model *use the bit of context you give
it*"** — and what that context costs on a CPU. That is the context/retrieval axis,
and it is the realistic deployment mode for these models.

**Design — vary the context condition, hold the question fixed.** Each scenario
keeps its question and gold answer; we attach a set of **context conditions** and
run the model under each. The conditions are the established RAG failure modes
(RGB, Chen et al., AAAI 2024) plus position sensitivity (*Lost in the Middle*, Liu
et al., TACL 2023), instantiated on **real `home.home.domain` artifacts** (kube events,
`journalctl`, Flux/Helm YAML, runbook paragraphs):

| Condition | What the model is given | Ability it probes |
|---|---|---|
| **closed-book** | nothing — parametric only | baseline (the current closed-book set) |
| **gold** | exactly the relevant snippet | upper bound — can it use *perfect* context |
| **retrieved** | gold snippet + a few plausible-but-irrelevant neighbours, realistic order | **noise robustness** — the realistic operator-paste |
| **insufficient** | relevant-looking context that does **not** contain the answer | **negative rejection** — abstain ("need X") vs hallucinate |
| **counterfactual** | context with a **stale/wrong** value (or an injected instruction) | **counterfactual robustness** — catch it vs parrot it |
| **multi-doc** | answer requires combining two snippets | **information integration** |

For `retrieved`/`counterfactual` we also sweep the gold snippet's **position**
(start/middle/end) to measure *lost-in-the-middle* sensitivity, which we expect to
be worse for small-context models.

**Realism *and* determinism (both, not either).** Context is sized as an operator
would paste it — **hundreds to ~1–2k tokens, not a dump** — which also respects the
small context windows and the truncation tax (§8b). To stay reproducible, a small
CPU embedder (e.g. `bge-small`/BM25) builds the `retrieved` set **once** from a
fixed homelab corpus, and the result is **frozen into the scenario file and
hashed** — the context becomes a pinned input exactly like `scenarios.json`, so the
determinism contract (§4) is unbroken. The retriever is part of the artifact, not a
live dependency.

**Expectations (pre-registered).**
- **E1 — context substitutes for parameters, most for the smallest.** The
  `gold − closed-book` lift is largest in the 0.5–2B brackets and shrinks with size
  (the powered form of H6). A 1–3B model + gold context should close much of the
  gap to a 7–8B closed-book model.
- **E2 — but on CPU it is a Pareto move, not a free lunch.** Added context is
  prefill: it raises latency and Wh/answer and pushes models into the **token-cap →
  truncation** failure mode that already dominates quality loss (§8b). The quality
  gain should arrive **with** a measurable energy/latency/truncation cost — that
  trade is the contribution, not the lift alone.
- **E3 — small models fail *negative rejection* worst.** On `insufficient`, we
  expect small models to **confidently hallucinate** rather than abstain (the RGB
  result), which on CPU ops is operationally dangerous: a confident-wrong root
  cause gets acted on.
- **E4 — `counterfactual`/injected context is a safety axis, not just a quality
  one.** We expect the cheapest models to **follow** a stale or injected value most
  readily, tying this axis to the prompt-injection scenarios (§5) and the
  inverse-stakes refusal finding: the models that cost the least trust their
  context the most.
- **E5 — position sensitivity is amplified at small scale.** Gold-in-the-middle
  should cost small-context models more than the larger ones.

**New metrics** (derivable, no new judging machinery beyond running the
conditions): per-bracket **context-lift**, **noise penalty** (`gold − retrieved`),
**negative-rejection rate**, **counterfactual-follow rate**, and **position
sensitivity** — each reported *beside* the existing energy/latency/truncation axes
so the trade is always visible.

> **Why not episodic memory or fine-tuning in *this* paper.** Two adjacent levers
> are deliberately **out of scope here**, for reasons of method, not interest:
> - **Episodic / persistent memory (write-back across tasks)** would test whether a
>   weak model *amortises* — solves a recurring incident once, stores the fix, nails
>   the repeat. It is the most novel direction (learning curves; memory as an
>   *attack surface* when an injected log writes a false memory), but it **breaks the
>   determinism contract**: runs stop being independent and state carries over, so it
>   needs its own longitudinal design with versioned memory snapshots. A *separate
>   study*, not a column in this table.
> - **Parameter learning (LoRA/QLoRA fine-tuning)** would test the strongest
>   sovereignty claim — a fine-tuned 1–3B beating a *generic* 7–8B at a fraction of
>   the energy. We hold it out because it is a **confound minefield** this benchmark
>   is not yet built to control: catastrophic forgetting, judge-gaming, and **safety
>   regression** (fine-tuning erodes alignment more than the quantization we already
>   meter, §8b) each require held-out scenario *classes* and a safety re-test before
>   any claim is honest. A follow-up, not a footnote.
>
> Retrieval is the lever that is **cheap, determinism-safe, and answers the question
> we already asked** (RQ6) — so it is the one we add.

## Appendix A. Submission Target and Format (Out-of-manuscript)

- **Target:** arXiv preprint (cs.SE / cs.AI) → a **workshop** (MLSys, NeurIPS
  ENLSP efficient-NLP, an on-device/edge-LLM or AIOps workshop). Format = short
  paper / experience report (4–8 pp).
- **Reproducibility appendix:** exact model digests, Ollama version, node spec,
  seeds, prompts (already byte-frozen in [`data/MODEL-PROMPTS.md`](../data/MODEL-PROMPTS.md)), and the analysis
  notebook.

## Appendix B. Submission-readiness Checklist (Out-of-manuscript)

Before submission, this manuscript must satisfy all of the following:

- **Claims discipline:** abstract/introduction claims match measured evidence and
  explicitly separate achieved results from roadmap motivation.
- **Limitations first-class:** a standalone limitations/threats section remains
  explicit about external validity, judge bias, egress, and hardware specificity.
- **Statistical reporting:** CIs, paired tests, correction for multiple
  comparisons, and judge-human agreement are reported for the main claims.
- **Compute disclosure:** per-run compute budget, hardware details, runtime
  envelope, and total experimental cost are reported.
- **Code/data reproducibility path:** commands, environment, data schema, and
  artifact locations are complete enough for an external team to rerun.
- **Artifact packaging quality:** documented, complete, and exercisable artifact
  bundle (scripts + data + analysis + figure generation) with pinned versions.
- **Licensing and provenance:** model/data/tool licenses and restrictions are
  enumerated; supply-chain pinning by digest is documented.
- **Responsible release:** dual-use and privacy risks are disclosed with concrete
  safeguards (scenario scrubbing/anonymization, endpoint safety posture).

These checks are mapped into concrete phase gates in [`PAPER_PHASES.md`](./PAPER_PHASES.md).

## Appendix C. Implementation Status (Spec -> Code)

| Need | State |
|---|---|
| Byte-frozen prompts | Done — [`data/MODEL-PROMPTS.md`](../data/MODEL-PROMPTS.md) (regenerated, all 19) |
| Telemetry capture | Done — `run.py` (validated: OTel fields, RAM/swap series, progress trace) |
| Watchdog / DNF taxonomy | Done — `run.py` |
| Repetitions + seed + temp control | Done — `run.py` (`--repeats/--temp/--seed-base`) |
| Non-LLM baselines | Done — `baselines.py` (random + keyword) |
| Judge backend = Claude 4.8 Max | Done — `judge.py` copilot backend → `claude-opus-4.8` (confirmed live) |
| Judge ensemble + κ | Done — `--ensemble copilot:gpt-5.5`; Cohen's κ in `report.py` |
| Safety gate (sound) | Done — judge-primary + majority-of-R + `must_not_endorse` check |
| Paired closed-book/grounded (clean RAG lift) | Done — 2 pairs + within-pair lift in `report.py` (more pairs = stronger) |
| Stats (CI, Friedman, κ) | Done — `report.py` (bootstrap CI + Friedman via numpy/scipy; κ stdlib). Wilcoxon/Holm gated on R=5 data |
| Pilot judging run (populate judge columns) | **Not yet run** (Copilot AI-Credit spend — confirm budget) |
| ≥6 scenarios/class + held-out | **Needs authoring** (secure=5, capacity=4 done; others thin) |
| 2nd reviewer for gold/rubric | **Pending** — run [`gold-review-prompt.md`](./gold-review-prompt.md) (regenerated for 19) + adjudicate |
