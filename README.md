**Research paper · open benchmark · arXiv preprint → NeurIPS Datasets & Benchmarks track**

**Online summary & live paper — [dragoshont.github.io/apprenticeops](https://dragoshont.github.io/apprenticeops/)** — figures, the sovereign-selection Pareto, and judge agreement at a glance · [paper PDF](https://dragoshont.github.io/apprenticeops/paper.pdf) · reviewing this work? [start here](https://dragoshont.github.io/apprenticeops/reviewers.html) or [`REVIEWER.md`](REVIEWER.md)

**Verified (2026-06-22):** every number was re-derived from the committed snapshot and every citation resolved against arXiv / CrossRef.

**Run it in your browser —** open the [**reviewer query notebook**](https://github.com/dragoshont/apprenticeops/blob/main/docs/analysis/reviewer.ipynb) on [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/dragoshont/apprenticeops/main?labpath=docs%2Fanalysis%2Freviewer.ipynb) , [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/dragoshont/apprenticeops/blob/main/docs/analysis/reviewer.ipynb) , or [![Open in Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](https://kaggle.com/kernels/welcome?src=https://github.com/dragoshont/apprenticeops/blob/main/docs/analysis/reviewer.ipynb) — reproduce every headline number, then **edit the queries and re-run** (no install).

[![Built with Architrave](https://img.shields.io/badge/Built%20with-Architrave-5b21b6?logo=github&logoColor=white)](https://github.com/dragoshont/architrave)

# ApprenticeOps: Evaluating Small Locally-Sovereign LLMs as Homelab Operations Assistants

> *Every AIOps paper runs a frontier model in a lab. We ran a 2018 ThinkPad in a closet — because that's where the interesting question lives.*

---

The AIOps community has produced impressive results: benchmarks with live fault-injection, frontier models with tool-calling, thousand-node clusters as the arena. All of it points at what AI *can* do given unlimited resources and a cloud account.

This paper asks the inverse question: **what can a small local model do when there is no escape hatch?** No Claude, no GPT, no Azure endpoint, no frontier escalation — just a 2018 ThinkPad running Ollama and a real production cluster's worth of incidents. The model is the last line. It must reason with what it has, or admit that it can't.

We call this the **locally-sovereign inference constraint**: the brain runs on *your* hardware. We measure where that floor is, what it costs in accuracy and energy, whether these models are safe to have in front of a real cluster — and whether a 3 GB model is meaningfully different from an 8 GB one on the tasks that matter.

---

## Why this is different from existing AIOps benchmarks

| | AIOpsLab / ITBench / OpsEval | ApprenticeOps |
|---|---|---|
| **Model assumption** | Frontier (GPT-4, Claude, Gemini) | Small, locally-sovereign (≤ 5 GB, CPU-only) |
| **Hardware** | Server / cloud | 2018 consumer laptop, 15 W TDP |
| **Scenarios** | Synthetic fault-injection, live clusters | Frozen real incidents from a production homelab |
| **Inference** | Always-online, API-callable | No external model API during graded inference |
| **Telemetry** | Task accuracy | Accuracy + energy + speed + CPU microarchitecture |
| **Safety** | Implied by model capability | Explicit `guard` class: refusal of destructive actions |
| **Grounding** | Oracle or live retrieval | Both measured separately, upper-bound labelled as such |

The axis we care about — reasoning per GB of model, on commodity hardware, in a sovereignly-operated system — is largely unmeasured. ApprenticeOps fills that gap.

---

## What we instrument per inference call

Every request emits a structured record aligned with [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai). A short summary of the main groups:

| Group | Signals captured |
|---|---|
| **Latency** | TTFT · prefill tok/s · decode tok/s · wall time · cold-load warmup |
| **Token budget** | In/out tokens and chars · think-vs-answer split (reasoning models get separated chain-of-thought time so they are neither rewarded nor penalised for it) |
| **Stream quality** | Inter-token jitter p50/p95/max — a model with a good mean tok/s but a high p95 *stutters* the UX |
| **Energy** | Intel RAPL `package-0` joules → Wh/task · Wh/correct-answer · tok/s-per-watt |
| **Memory** | RSS start→peak · peak swap (MB) · minor/major page faults · context switches |
| **CPU microarchitecture** | IPC · LLC miss rate · branch miss count — a low IPC + high LLC-miss is the fingerprint of memory-bandwidth-bound decode |
| **DRAM bandwidth** | IMC requestor split: IA (CPU) / GT (iGPU) / IO — confirms the bottleneck is memory, not compute |
| **Model internals** | Parameter count · quantisation · MoE expert count/active · native context length (from Ollama `/api/show` and `/api/ps`) |
| **Ollama runtime** | `load` / `eval` / `total` durations from the response payload — authoritative, not inferred |

This telemetry depth is unusual for LLM evaluation. The reason is simple: on CPU-only inference, "why is this model slower?" is a non-trivial question. The numbers above let you answer it.

---


There is a common conflation between *inference sovereignty* (no external model API) and *information poverty* (no external data). We reject the second. A locally-sovereign model can and should have access to local RAG, in-organisation MCP servers, runbooks, and cluster telemetry. The constraint is on where the *reasoning* happens, not on what data feeds it.

This redraws the requirement stack for a small local ops model:

1. **Reason without an external model** — its judgment is final; no second opinion.
2. **Grounding-faithfulness** — use supplied local context and do not contradict or hallucinate beyond it.
3. **Calibration** — say "I don't know" rather than inventing. This is the prerequisite for safety.
4. **Safety-by-default** — refuse destructive actions without a human in the loop to catch the error.
5. **Fit and speed** — must run interactively on owned hardware.

This is why we measure two grounding modes per scenario: **closed-book** (in-weights knowledge only) and **grounded** (correct reference material supplied in-context, simulating perfect local retrieval). The gap between them is directly actionable — it answers "do I need a vector database next to my tiny model, and how much does it buy me?"

---

## Research questions

Seven falsifiable hypotheses were **pre-registered** before the measurement run
(the locked spec lives in [`docs/PAPER.md`](docs/PAPER.md) §3). We report each one
against what actually happened — **including the predictions the data did not
confirm** — rather than quietly revising them after the fact:

| RQ | Pre-registered prediction | Outcome |
|---|---|---|
| RQ1 | Quality rises with diminishing returns; a knee around **3–4B**. | **Supported** — knee landed one bracket smaller, at **2–3B**. |
| RQ2 | The **3–4B** bracket dominates the speed/quality Pareto. | **Partial** — the balanced pick is 3–4B, but the non-dominated front spans **all five** brackets. |
| RQ3 | Safety is **not monotonic** in size; some small models endorse destructive commands. | **Supported** — driven by **training type, not size**. |
| RQ4 | "Thinking" models gain on diagnosis but at prohibitive CPU latency. | **Not directly tested** — no per-class accuracy × latency split (future work). |
| RQ5 | Best ≤5 GB model reaches **~60–80 %** of a frontier reference. | **Not directly tested** — no frontier baseline run; ≈ 71 % of the judge's ceiling (a proxy). |
| RQ6 | Local **RAG** lift is large for small models and shrinks with size. | **Not causally tested** — closed-book vs grounded are different task classes (confound disclosed). |
| RQ7 | Energy/answer rises with params; the knee is the efficiency sweet spot. | **Supported** — energy rises with params; knee one bracket smaller (**2–3B**). |

Three of the seven hold as stated; the quality knee landed **one bracket smaller**
than predicted; three (RQ4–RQ6) were **not directly testable** with this design and
are flagged as such, not silently dropped. Full prediction-vs-outcome detail and
the deviation log: [`docs/PAPER.md`](docs/PAPER.md) §8c.

---

## Headline result — the quality × safety × energy Pareto

The contribution is not any single axis; it is choosing on **all three together**.
Treat each model as a point in **(judged quality ↑, destructive-action refusal ↑,
energy-per-answer ↓)** and compute the **Pareto-optimal set** — the models nothing
else beats on every axis at once. On the consolidated **94-model** data, **12 of 94 models are
Pareto-optimal; the other 82 are dominated**, and the two heuristics a practitioner
reaches for — *biggest that fits* and *has a “reasoning” mode* — select **dominated**
models. `deepseek-r1:7b` is among the worst *combined* cases: among the **most
energy-expensive** models in the study (top 5 of 94), and the least-safe large
reasoning-distilled refuser.

The three axes, briefly:

- **Quality** — judged %-of-frontier knees at **2–3B**; *quantization*, not parameter
  count, carries the marginal lift.
- **Safety (axis #2)** — judge-free deterministic refusal, governed by **training
  type, not size**. This **corroborates** a saturated agent-/SLM-safety literature
  (GAP, OS-Harm, Beyond-the-Tip, Q-resafe, …); we replicate it offline, we do not
  claim to discover it.
- **Energy** — the under-reported axis: Wh/answer and tok/s-per-watt you pay to run
  the model yourself.

Figures and the dominance computation live in
[`docs/analysis/wave_analysis.ipynb`](docs/analysis/wave_analysis.ipynb) §7–§8; the
full result is [`docs/PAPER.md`](docs/PAPER.md) §8b. The quality axis is the
**5-rep × 2-judge ensemble** (cross-judge κ_quad ≈ 0.91); residual judge↔human
agreement is the remaining open item (see [`REVIEWER.md`](REVIEWER.md) §7).

---

## The scenarios

The original paper run used **19 scenarios**. The working corpus now contains
**27 scenarios** in [`data/scenarios.json`](data/scenarios.json): the original
homelab incidents plus later repo-grounded security, capacity, tool-action, and
Sideport high-CPU cases. The 2026-06-24 external research pass recommends a
**20-case core roster** for the next expensive run; see
[`docs/SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md`](docs/SCENARIO_INDEPENDENT_ANALYSIS_2026-06-24.md)
for the decision summary,
[`docs/SCENARIO_RESEARCH_2026-06-24.md`](docs/SCENARIO_RESEARCH_2026-06-24.md)
for the source-backed scan, and the earlier inventory audit in
[`docs/SCENARIO_AUDIT_2026-06-24.md`](docs/SCENARIO_AUDIT_2026-06-24.md).

The scenarios are drawn from a production homelab cluster (`home.hont.ro`,
Kubernetes, Flux, Traefik, Plex, *arr stack) and synthetic-but-repo-grounded
extensions that preserve the same operational shapes. They span these task
classes:

| Class | What the model must do |
|---|---|
| `detect` | Triage a crashloop or probe failure from logs and events |
| `diagnose` | Identify root cause from a multi-signal incident dump |
| `monitor` | Interpret metrics/alerts correctly |
| `foresee` | Spot a *misleading healthy surface signal* hiding a real problem (trap scenarios) |
| `expand` | Plan adding a new application to a GitOps cluster |
| `upgrade` | Plan a Helm release upgrade with correct flag choices |
| `augment` | Emit structured telemetry (JSON log events, OTel spans) from existing code |
| `guard` | **Refuse** a destructive or unsafe action (hard gate) |
| `secure` | Identify a security misconfiguration |

Scenarios are labelled `easy / medium / hard`. The **easy** tier is a passable floor — any useful model should clear it. The **hard** `foresee-*` scenarios are deliberate traps: the SMART health check is `PASSED` while reallocated sectors are climbing; the TLS cert is `Ready=True` while the DNS-01 auto-renewal has been 403-ing for days. Labels are validated empirically against the accuracy-by-difficulty table — if the ordering doesn't hold, the label is revised.

The corpus marks grounding explicitly. The captured subset is real `home.hont.ro`
telemetry; the synthetic-but-repo-grounded subset is constructed from this
homelab's actual conventions and failure surfaces. That distinction matters for
claims about contamination and generalisation.

---

## Measurement: not just accuracy numbers

The harness captures far more than pass/fail. Per-request fields include:

**Quality**
- `det_score` — deterministic check pass rate (unambiguous facts; no judge required)
- `judge_score` — frontier LLM-as-judge score (1–5), reported as % of frontier reference
- `safety_pass` — binary hard gate on the `guard` class

**Systems transparency** — aligned with [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
- TTFT, prefill tok/s, decode tok/s, wall time, in/out tokens and characters, cold-load warmup
- Think/answer split for reasoning models — chain-of-thought time reported separately so models are neither rewarded nor penalised for hidden reasoning
- Inter-token jitter (p50/p95/max ms) — stream *smoothness*, not just mean rate
- RAPL energy (joules → Wh/task) at the `package-0` domain — on-die SoC draw, not facility power
- Intel IMC memory bandwidth (IA/GT/IO requestor split), peak swap, RSS growth
- IPC, LLC miss rate, and branch-miss counts — the memory-bandwidth-bound decode fingerprint
- Ollama-native internals: architecture, MoE expert count, quantisation, `load`/`total`/`eval` durations from the response payload — not inferred, read directly

**Reproducibility controls**
- Governor locked to `performance`, turbo disabled, clocks pinned to base (~1.70 GHz, sustainable) for the systems pass
- Per-model `quiesce()` step: fan to max, drop page-cache, reset swap, compact memory, wait for package temperature to settle
- Randomised model order with fixed `--order-seed` to decorrelate carryover from model identity
- CPU frequency logged at 1 Hz as throttle evidence

This level of measurement depth is unusual for LLM evaluation. The reason: on CPU-only inference, the question "why is this model slower?" is non-trivial. A low IPC with high LLC-miss rate is the fingerprint of a memory-bandwidth-bound decode. A model that looks fast on token/s may be stalling on swap. These numbers tell you *why*, not just *what*.

---

## Hardware: the 2018 ThinkPad is not a weakness

The node is a **ThinkPad T480s, Intel i5-8350U** (4C/8T, base 1.70 GHz, 15 W TDP, AVX2, no AVX-512), **24 GiB DDR4-2400 dual-channel** (asymmetric flex mode, ~38.4 GB/s theoretical peak). It costs roughly **150 USD** second-hand. It is representative of the low end of what a serious homelab practitioner actually has — not the median cloud instance, not a MacBook Pro M-series.

Running the benchmark on this hardware is not a limitation to apologise for. It is the *measurement point*. A model that performs well here works on the hardware you can afford to dedicate to local inference. A model that struggles here tells you exactly what you are giving up.

---

## Quick start

**Prerequisites:** Ollama ≥ 0.30 on any OS; Python ≥ 3.10 (stdlib only for the harness).

```bash
git clone https://github.com/dragoshont/apprenticeops.git && cd apprenticeops
ollama --version                                      # verify >= 0.30
python3 run.py --help                                 # stdlib-only; no pip needed for the harness
python3 baselines.py --out /tmp/bl.jsonl              # sanity-check: no model; random~0.26 keyword~0.73
```

**Pilot run — one model, current scenario corpus (~5-10 min):**
```bash
printf '# bracket: 0-1B\nqwen2.5:0.5b\n' > one.txt
python3 run.py --models one.txt
# Watch: det=x/y tok/s per scenario; results.jsonl with OTel fields + system telemetry.
```

**Full variance run (hours to days; the paper run):**
```bash
# Deterministic pass: temp=0, 1 rep — the point estimate
python3 run.py --models data/models.txt --temp 0 --repeats 1 --out results.det.jsonl

# Variance pass: temp=0.7, R=5 fixed seeds — enables 95% CIs
python3 run.py --models data/models.txt --temp 0.7 --repeats 5 --seed-base 1 --out results.var.jsonl
```

See [`REPRODUCE.md`](REPRODUCE.md) for the full pipeline — including locking the node into a reproducible power state, running the judge, generating the paper tables, and exporting an ML-ready flat dataset.

---

## Documents

| File | What it is |
|------|-----------|
| [`REVIEWER.md`](REVIEWER.md) | **Reviewer's guide** — what the paper claims, how it was produced (human-guided, AI-assisted), the review rubric mapped to NeurIPS dimensions, how to reproduce safely, and AI-assisted-review etiquette. **Start here if you were asked to review.** |
| [`docs/PAPER.md`](docs/PAPER.md) | **Experimental design spec** — the science: all 7 RQs with falsifiable hypotheses, full factor table, scenario design rationale, threat-to-validity analysis, stats plan (bootstrap CIs, Friedman test, Cohen's κ), honesty caveats. Read this before interpreting any number. |
| [`REPRODUCE.md`](REPRODUCE.md) | **Reproducibility contract** — every command to regenerate every number, dependency pinning, environment capture script, node-locking protocol, caveats for non-Linux and GPU hardware. |
| [`docs/PLAN.md`](docs/PLAN.md) | **Operational how-to** — task taxonomy, scoring rubrics, judge backend configuration, watchdog, repeatability mechanics. |
| [`docs/TAXONOMY.md`](docs/TAXONOMY.md) | **Task-class taxonomy** — the 8 classes with examples and cross-references to the AIOps maturity ladder. |
| [`docs/TELEMETRY.md`](docs/TELEMETRY.md) | **Telemetry data dictionary** — every emitted field, its source, units, and coverage gaps. Aligned with OTel GenAI semantic conventions. |
| [`docs/MODELS.md`](docs/MODELS.md) | **Model manifest** — size, quantisation, license, tool-call capability, source for all tested models. |
| [`docs/MARKET.md`](docs/MARKET.md) | **Adversarial market analysis** — benchmark contamination risks, model-card reasoning claims vs. evidence, supply-chain (digest pinning), what each bracket demonstrably can and cannot do. |
| [`docs/analysis/`](docs/analysis/) | **Analysis notebooks + figures** — the sovereign quality × safety × energy story ([`wave_analysis.ipynb`](docs/analysis/wave_analysis.ipynb)) + judge agreement, with machine-readable exports in [`data/site/`](data/site) and a one-command static-site build ([`scripts/build-analysis-site.sh`](scripts/build-analysis-site.sh)). |
| [`data/SCENARIOS.md`](data/SCENARIOS.md) | **Scenario book (human-readable)** — the current scenario corpus with context, task, **gold answer, deterministic checks, and judge rubric**. Auto-generated from `scenarios.json` by [`render_scenarios.py`](render_scenarios.py); the file a human reviewer actually reads. |
| [`data/MODEL-PROMPTS.md`](data/MODEL-PROMPTS.md) | **Byte-frozen prompts** — exact prompt text for every scenario, generated from `run.build_prompt()`. Reproducibility requires these to be immutable after the run begins. |

---

## Repository layout

```
apprenticeops/
├── run.py               # main harness — inference loop, telemetry, quiesce, OTel schema
├── baselines.py         # non-LLM baselines (random, keyword, structural)
├── judge.py             # LLM-as-judge scoring, multi-backend, usage/billing capture
├── report.py            # markdown + CSV rollups, paper-ready tables
├── dataset.py           # flat ML-ready dataset export (features + labels)
├── calibrate.py         # hardware ceiling measurements (RAPL, membw, disk, observer overhead)
├── REPRODUCE.md         # reproducibility contract
├── requirements.txt     # analysis deps only; harness is stdlib-first
├── data/
│   ├── scenarios.json   # the benchmark corpus — 27 current scenarios
│   ├── models.txt       # model manifest (bracket, tag, quant)
│   └── MODEL-PROMPTS.md # byte-frozen prompt text
├── docs/
│   ├── PAPER.md         # experimental design spec
│   ├── PLAN.md          # operational how-to
│   ├── TAXONOMY.md      # task-class taxonomy
│   ├── TELEMETRY.md     # telemetry data dictionary
│   ├── MODELS.md        # vetted model list
│   └── MARKET.md        # adversarial analysis
└── scripts/
    ├── node-power.sh    # reproducible power state: setup / teardown / status
    └── run-experiment.sh # autonomous multi-stage experiment driver
```

---

## Honest limitations

**1. Judge egress.** We use Claude 4.8 off-node to *score* answers. The system-under-test never calls it. But the judge sees the scenario text, which contains real cluster detail: namespace names, Azure Key Vault references, Cloudflare DNS, `*.hont.ro`. This is real ops data sent to a third party. Released scenarios are scrubbed and anonymised. This egress must be disclosed in any publication. See the public-service dependency map in [`docs/PAPER.md`](docs/PAPER.md).

**2. Grounded = oracle retrieval upper bound.** We inject the correct reference text directly into context. A real local-RAG pipeline adds retrieval error, chunking artifacts, and embedding drift. Our grounded numbers are the *ceiling* of what local retrieval can buy, not the expected value in a deployed system.

**3. Telemetry is Linux-specific.** Energy (RAPL), RAM/swap (`/proc`), and memory-bandwidth counters require Linux. The harness runs on macOS/Windows — quality scores reproduce; the systems telemetry will be empty. This is a documented limitation, not a bug.

**4. CPU-only inference.** The benchmark characterises inference on the *worst reasonable hardware*. On a machine with a discrete GPU or Apple Silicon, tok/s numbers will be higher and thermal behaviour different. The quality scores should generalise; the systems numbers will not.

**5. Single hardware point.** All systems measurements are from one specific node (i5-8350U, 24 GiB DDR4-2400). Hardware interaction effects may differ on different CPU generations, memory configurations, or NVMe speeds. We disclose the full environment in `ENVIRONMENT.md`.

---

## The AIOps maturity ladder

The broader motivation: where does a local small model sit on the path toward autonomous operations?

```
5 · Autonomous   — closed-loop self-healing, no human required
4 · Preventive   — acts to prevent known failure modes before they occur  
3 · Predictive   — forecasts failures from time-series signals
2 · Proactive    — acts ahead of user request, surface-triggered
1 · Reactive     — responds to incidents that have already occurred
    ↑
    This paper measures the quality and safety of the reasoning FOUNDATION
    at rung 1 (reactive) and the early boundary of rung 2 (proactive/foresee).
    Claiming higher rungs from these results would be overreach.
```

A model that can reliably detect, diagnose, and safely refuse on rung 1 has earned the right to be *considered* for higher-trust work. This benchmark provides the evidence base for that judgment — and makes the evidence falsifiable and reproducible.

---

## For reviewers

This repo is built to be **easy to review — including with AI assistance — with a
human in charge of the judgement.** If you were invited to review the paper, start
with **[`REVIEWER.md`](REVIEWER.md)**: it maps your assessment onto the NeurIPS
review dimensions (quality / clarity / significance / originality), tells you which
numbers reproduce on any laptop vs. which need the specific node, and covers
confidentiality etiquette for AI-assisted review.

> **arXiv is moderated, not peer-reviewed.** The first release is an arXiv preprint
> (a moderation check on scholarly standards and format — *not* peer review); the
> intended peer-reviewed venue is the **NeurIPS Datasets & Benchmarks track**.

## Use of AI in this work

This benchmark, its analysis, and its prose were produced with **substantial AI
assistance under human direction**. A human author directs the work and **takes full
responsibility for every claim, number, and line of code**, regardless of how it was
generated; no AI system is listed as an author. This follows arXiv's policy on
authors' use of generative-AI language tools. Every headline number is reproducible
from released artifacts ([`REPRODUCE.md`](REPRODUCE.md)), so the work can be checked
independently of the prose.

## Standards

- **Telemetry schema**: [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — `gen_ai.*` spans, metrics, events.
- **Judge pattern**: MT-Bench / AlpacaEval frontier-as-judge; two-family ensemble (Copilot + OpenAI) with Cohen's κ agreement.
- **Stats**: bootstrap 95% CIs; Friedman test for within-subject bracket comparison; Wilcoxon signed-rank for pairwise.
- **Baseline provenance**: [EleutherAI lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) — the open standard for repeatable LLM evaluation.

---

## Citation

```bibtex
@misc{hont2026apprenticeops,
  title   = {ApprenticeOps: Evaluating Small Locally-Sovereign LLMs as
             Homelab Operations Assistants},
  author  = {Hont, Dragos},
  year    = {2026},
  url     = {https://github.com/dragoshont/apprenticeops},
  note    = {Open benchmark and reproducible study. Apache 2.0.}
}
```

Update with venue and DOI after submission.

## License

Apache 2.0. See [`LICENSE`](LICENSE).

---

**Start here:** [`docs/PAPER.md`](docs/PAPER.md) for the research design, [`REPRODUCE.md`](REPRODUCE.md) to reproduce the results.

**Contribute:** issues and PRs welcome — especially new scenarios, additional models, and hardware configurations.

