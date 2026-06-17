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
hardware** along the axes retrieval *can't* fix: **reasoning,
grounding-faithfulness, calibration, and safety**. The artifact (harness +
real-incident scenarios + telemetry schema) is the primary contribution; the
model ranking is the demonstration.

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
| **Judge + frontier reference** (`judge.py`) | **GitHub Models** (`models.github.ai` → OpenAI/Azure-hosted) | **No** — off-node, post-hoc, on the Mac | **Eval scaffolding.** The system-under-test never calls it. BUT it **receives the scenario text**, which contains real cluster detail (namespaces, Azure Key Vault, Cloudflare, `*.hont.ro`, restic/NAS) → **egress of real ops data to a third party** (see threat row + REPRODUCE caveat; scrub before release). |
| **Stats** (`report.py` extension) | PyPI (`numpy`/`scipy`) | No — analysis-time, off-node | None at runtime. |
| **Serving gateway** (Caddy `ai.hont.ro`, *not* part of the eval) | Let's Encrypt + Cloudflare DNS-01 | No | Out of scope for the benchmark; a dependency of the *deployed serving* path, not the *measured* path. |

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
- **Repetitions (the power fix):** **R = 5** samples per (model × scenario) at
  **temperature = 0.7** with **fixed, distinct seeds** (1..R) → enables
  mean ± 95 % CI and variance (the **variance run**). A **separate temperature = 0**
  pass — **greedy decoding**, where the model always takes the highest-probability
  token, so its output is (near-)reproducible — gives the point estimate for the
  deterministic checks; we call this the **deterministic ("det") run**. *(Locked: R=5.)*
  > **temp-0 caveat:** greedy decode on Ollama/llama.cpp is *mostly* but **not
  > bit-exactly** reproducible across CPU threads/batch; fixed seeds reduce but do
  > not eliminate this — hence we still report CIs even on the "deterministic" pass.
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
- **Provenance:** drawn from **real `home.hont.ro` signals** (kube events,
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
  > **Power reality (state honestly):** with R=5 × ~6 scenarios/class, 25 models
  > → ~300 pairwise comparisons; after Holm correction, **individual-model**
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
- **Primary judge / reference:** **Claude 4.8 Max** = **`claude-opus-4.8`** via
  the official GitHub Copilot CLI *(locked)*. Judge ensemble adds a **2nd distinct
  family** — **`gpt-5.5`** through the same CLI — for bias control.
  > **Implementation status:** judge wiring **RESOLVED** (2026-06-16). `judge.py`
  > has a `copilot` backend driving the official Copilot CLI; `claude-opus-4.8`
  > is confirmed live (an end-to-end judge call scored a sample 5/5 with cited
  > evidence) and `--ensemble copilot:gpt-5.5` gives the 2nd family. GitHub Models
  > carries **no** Claude (verified) and Anthropic keys are not used. **Caveat:**
  batch judging spends Copilot AI Credits — **measured ~7.7 credits/call** for
  `claude-opus-4.8` via the CLI (dominated by the cached system/tool context, so
  ~6 k calls is a real, non-trivial cost). The harness now **records exact
  per-call billing** (AI credits + token in/out + prompt-cache read/write) from
  the CLI footer into judged.jsonl, with a cost/cache rollup in report.py — so the
  evaluation cost is measured, not estimated. The **pilot judging
  > has not been run yet**, so the pilot's `judge/5` / `% frontier` columns are
  > still empty — pilot findings remain **deterministic-only** until that pass runs.
- **Judge-bias probes:** position-randomized, identity-blinded; run a **2-model
  judge ensemble** and report agreement; disagreements flagged.
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

## 9. Limitations and Threats to Validity

| Threat | Type | Mitigation |
|---|---|---|
| n=1 environment (one cluster/operator) | External | Frame as **single-environment case study**; release harness so others replicate |
| Author wrote scenarios + gold + rubric | Internal/construct | **option-C gold review DONE** (Claude 4.8 audited gold+rubric+checks, hardened the gameable ones, re-verified — `gold-review*.jsonl`); held-out set; hardened deterministic checks + LLM-judge as final correctness |
| LLM-judge bias (self-pref, verbosity, position) | Conclusion | Blind, position-randomize, evidence-cited, κ vs human, judge ensemble |
| Benchmark contamination | Construct | Canary/memorization probe; real-incident tasks unlikely in pretraining |
| **Fine-tuning contamination** — domain fine-tuning on homelab-style ops data can make a tuned small model *memorize the benchmark style*, inflating scores and undermining the core "real incidents in nobody's training set" claim | Construct | **Caveat (future work).** Any fine-tuned arm must train only on data **disjoint** from the evaluated scenarios, report results on a **contamination-proof held-out set**, split by **incident** (not just wording) to avoid near-duplicate leakage, and include paraphrase/canary memorization probes. Always report **base vs fine-tuned** on the same held-out set so the lift is earned, not memorized. |
| Quant vs architecture confound | Internal | q4 held constant for headline; q8/QAT as sensitivity |
| Grounding leak (gold answer derivable only from supplied context vs needs in-weights knowledge) | Construct | Explicit `closed-book`/`grounded` label per scenario; report the two separately so neither masks the other |
| Thinking-model unfairness | Internal | Separate track + token/latency budget |
| Multiple comparisons → false winners | Conclusion | Holm–Bonferroni; pre-registered analysis |
| Hardware specificity | External | Report exact node; note bandwidth-bound caveat; invite GPU re-runs |
| Small R inflates variance | Conclusion | R≥5, bootstrap CIs, report CI widths honestly |
| **RAG-lift confound** (grounded vs closed-book are *different task classes*, not the same task with/without a doc) | Internal/construct | **Open issue.** Current `rag_lift` mixes retrieval effect with task-difficulty. Fix before the RQ6 claim: author **paired variants** (same scenario, reference-doc present vs absent) so the within-scenario delta isolates retrieval. Until then, report closed-book and grounded **separately**; do not claim a causal RAG lift. |
| **Judge egress** (real cluster telemetry sent to a 3rd-party cloud judge) | Construct/opsec | System-under-test stays sovereign; but scrub/anonymize released scenarios, disclose the egress, and prefer a self-hosted judge (§0b) |
| **Energy = SoC (RAPL `psys`) not wall power**; single node | Construct/External | RAPL `psys` is on-die platform energy — **excludes** display/PSU/peripheral draw (a feature: isolates compute energy for the size comparison, but not facility power). Report the **idle baseline** + **net-over-idle**; optionally cross-check with a wall plug; energy ranks are this-chip-specific — invite re-runs |
| **Thermal-order confound (C1)** — sequential 25-model runs heat the chip; later models throttle, confounding speed/energy with *run position* | Internal | **Fixed:** `--shuffle` randomizes model order (deterministic `--order-seed`); temp-gated `cooldown()` between models; `thermal.start_c` recorded as a per-task carryover covariate. The deterministic *quality* pass is order-insensitive; only the systems numbers need this |
| **Tokenizer non-comparability (C2)** — tok/s differs ~20% across tokenizers for identical text | Construct | **Fixed:** report **chars/s** and **energy-per-token** beside tok/s; `output_chars` captured per request |
| **Observer effect (C3)** — the sampler + perf counters perturb the throughput/energy they measure | Construct | **Fixed:** `calibrate.py` runs the probe model **with vs without** telemetry and reports the tok/s overhead; heavy `PERF_MEMBW` is env-gated, off by default; `SAMPLE_INTERVAL` tunable |
| **RAPL is a modeled estimate (M1)** — whole-socket model, not per-process wall power; counters wrap | Construct | **Fixed/disclosed:** per-**subdomain** wraparound correction (`RAPL_MAXES`); `package-0` avoids the battery-charge confound; framed as compute-energy ±error, not facility power (Weaver et al.) |
| **Sampling aliasing (M2)** — a 1 Hz sampler can alias sub-second power/freq excursions | Construct | **Fixed:** `SAMPLE_INTERVAL` configurable sub-second; peak trackers catch excursions between ticks |
| **MBU vs datasheet (M4)** — utilization against the spec bandwidth overstates headroom | Construct | **Fixed:** `calibrate.py` measures the achievable STREAM peak on *this* node; MBU/bottleneck stay **blank** until calibration exists rather than faking a ceiling |
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
4. **Empirical findings** on the size/quality/speed/safety trade-off, incl. the
   **safety non-monotonicity** result, and the local-RAG lift.
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
- **Gap we fill:** small + locally-sovereign + CPU + real-homelab incidents +
  explicit safety gate + closed-book-vs-local-RAG — not, to our knowledge, published.

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
| Byte-frozen prompts | ✅ [`data/MODEL-PROMPTS.md`](../data/MODEL-PROMPTS.md) (regenerated, all 19) |
| Telemetry capture | ✅ `run.py` (validated: OTel fields, RAM/swap series, progress trace) |
| Watchdog / DNF taxonomy | ✅ `run.py` |
| Repetitions + seed + temp control | ✅ `run.py` (`--repeats/--temp/--seed-base`) |
| Non-LLM baselines | ✅ `baselines.py` (random + keyword) |
| Judge backend = Claude 4.8 Max | ✅ `judge.py` copilot backend → `claude-opus-4.8` (confirmed live) |
| Judge ensemble + κ | ✅ `--ensemble copilot:gpt-5.5`; Cohen's κ in `report.py` |
| Safety gate (sound) | ✅ judge-primary + majority-of-R + `must_not_endorse` check |
| Paired closed-book/grounded (clean RAG lift) | ✅ 2 pairs + within-pair lift in `report.py` (more pairs = stronger) |
| Stats (CI, Friedman, κ) | ✅ `report.py` (bootstrap CI + Friedman via numpy/scipy; κ stdlib). Wilcoxon/Holm gated on R=5 data |
| Pilot judging run (populate judge columns) | ⏳ **not yet run** (Copilot AI-Credit spend — confirm budget) |
| ≥6 scenarios/class + held-out | ⏳ **needs authoring** (secure=5, capacity=4 done; others thin) |
| 2nd reviewer for gold/rubric | ⏳ run [`gold-review-prompt.md`](./gold-review-prompt.md) (regenerated for 19) + adjudicate |
