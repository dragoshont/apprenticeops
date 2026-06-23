# Literature catalog — ApprenticeOps

A working index of every reference in the project bibliography
([references.bib](references.bib)), grouped by theme, with a one-line description and
**why it matters for this paper**. For the papers read end-to-end during the deep-analysis
literature rounds, the exact **quotable line** is included.

**How the citation keys work.** The bib is **BibTeX**: each entry is `@type{key, ...}`. In the
Quarto/Markdown source you cite with `[@key]` (e.g. `[@dettmers2023case]`) and the reference list
renders itself — you never hand-format a citation. The **key** column below is exactly what you type.

**Verification legend.**
✅ = read this session against the arXiv abstract page (title/authors/year/venue confirmed; quote verbatim).
📚 = pre-curated in the bib (bib header notes a 2026-06-20 arXiv verification pass); not re-read this session.

> Honesty note: descriptions for 📚 entries are topical (from title + role in our argument). Verbatim
> quotes are given **only** for ✅ entries actually read. arXiv IDs in the `2026xx` range are 2026
> submissions; they are carried as the bib received them and are flagged where a re-check is wise.

---

## 1. Evaluation methodology, leaderboards & benchmark robustness

| Key | Paper | Year / venue | What it is & why it matters here |
|---|---|---|---|
| `liang2023helm` ✅ | Holistic Evaluation of Language Models (HELM) | TMLR 2023 · 2211.09110 | The canonical **multi-metric** evaluation. Grounds our quality/safety/speed/energy axes (don't collapse to accuracy). |
| `dehghani2021lottery` ✅ | The Benchmark Lottery | 2021 · 2107.07002 | Rankings are **fragile** to benchmark/method choice. Grounds our multi-method τ-agreement robustness check (§15). |
| `dehghani2021efficiency` ✅ | The Efficiency Misnomer | 2021 · 2110.12894 | Cost indicators (FLOPs/params/latency/energy) **disagree**; report several. Grounds reporting all cost axes, not one. |
| `chiang2024arena` ✅ | Chatbot Arena | 2024 · 2403.04132 | Pairwise human-preference leaderboard with **Bradley–Terry/Elo**. Grounds the Arena-style aggregation in §15. |
| `zheng2023judge` ✅ | Judging LLM-as-a-Judge (MT-Bench) | NeurIPS D&B 2023 · 2306.05685 | Validates **LLM judges** (>80% human agreement) *and* names **verbosity bias** — independently confirms our judge-calibration finding (§19). |
| `schaeffer2023emergent` 📚 | Are Emergent Abilities a Mirage? | NeurIPS 2023 · 2304.15004 | "Emergence" can be an artifact of the **metric**. Supports careful, continuous metrics over threshold effects. |
| `cohen1968weighted` 📚 | Weighted Kappa | Psych. Bulletin 1968 | The **quadratic-weighted κ** we use for inter-judge agreement (κ_quad 0.906). |
| `landis1977kappa` 📚 | Observer Agreement for Categorical Data | Biometrics 1977 | The κ **interpretation bands** ("substantial/almost perfect") we cite for judge agreement. |

**Quotable lines (✅):**
- HELM: *"we adopt a multi-metric approach … This ensures metrics beyond accuracy don't fall to the wayside, and that trade-offs are clearly exposed."*
- Benchmark Lottery: *"many factors, other than fundamental algorithmic superiority, may lead to a method being perceived as superior … highlighting the fragility of the current paradigms."*
- Efficiency Misnomer: *"researchers and practitioners often assume that these metrics are correlated … incomplete reporting of cost indicators can lead to partial conclusions."*
- MT-Bench: *"strong LLM judges like GPT-4 can match … human preferences well, achieving over 80% agreement"* and *"the usage and limitations of LLM-as-a-judge, including position, verbosity, and self-enhancement biases."*
- Chatbot Arena: *"Our methodology employs a pairwise comparison approach … the tried-and-true statistical methods we are using for efficient and accurate evaluation and ranking of models."*

---

## 2. Small / on-device / efficient LLMs & architecture

| Key | Paper | Year / venue | What it is & why it matters here |
|---|---|---|---|
| `belcak2025slm` ✅ | Small Language Models are the Future of Agentic AI | NVIDIA 2025 · 2506.02153 | **The closest thesis match.** Argues SLMs are the right tool for repetitive agent tasks; supports our premise and the tiered/per-bracket champion idea. |
| `lu2024slmsurvey` ✅ | Small Language Models: Survey, Measurements, and Insights | 2024 · 2409.15790 | Surveys 70 SLMs and **benchmarks on-device latency + memory** — grounds our systems-telemetry methodology. |
| `srivastava2025thinkslm` 📚 | Towards Reasoning Ability of Small Language Models (ThinkSLM) | EMNLP 2025 · 2502.11569 | Whether reasoning **transfers** to small models — context for our reasoning-arm results. |
| `gu2023mamba` ✅ | Mamba: Linear-Time Sequence Modeling with Selective State Spaces | 2023 · 2312.00752 | The **SSM** architecture behind hybrids; grounds the `granite4` bandwidth-thrift result (§14/§20). |
| `sui2025overthinking` ✅ | Stop Overthinking: A Survey on Efficient Reasoning | TMLR 2025 · 2503.16419 | Names the **"overthinking phenomenon"** — grounds our `deepseek-r1:7b` timeout case (§2) and reasoning latency penalty. |

**Quotable lines (✅):**
- SLM-agents: *"applications in which language models perform a small number of specialized tasks repetitively and with little variation"*; *"SLMs are sufficiently powerful, inherently more suitable, and necessarily more economical for many invocations in agentic systems"*; *"heterogeneous agentic systems … are the natural choice."*
- SLM survey: *"SLM research aims to make machine intelligence more accessible, affordable, and efficient … we benchmark their inference latency and memory footprints."*
- Mamba: *"Mamba enjoys fast inference (5× higher throughput than Transformers) … Mamba-3B … matches Transformers twice its size."*
- Stop Overthinking: *"longer CoT reasoning sequences improve performance, they also introduce significant computational overhead due to verbose and redundant outputs, known as the 'overthinking phenomenon'."*

---

## 3. Systems: inference cost, energy, roofline & quantization

| Key | Paper | Year / venue | What it is & why it matters here |
|---|---|---|---|
| `williams2009roofline` 📚 | Roofline: An Insightful Visual Performance Model | CACM 2009 | The **roofline model** itself — the lens for "memory-bandwidth-bound decode" (§20). |
| `alizadeh2024llmflash` ✅ | LLM in a flash: Inference with Limited Memory | ACL 2024 · 2312.11514 | Treats inference on memory-constrained devices as **data-transfer bound** — grounds our memory-wall reading (§20). |
| `dettmers2023case` ✅ | The case for 4-bit precision: k-bit Inference Scaling Laws | ICML 2023 · 2212.09720 | **4-bit is Pareto-optimal**; bit-equal models differ — grounds our quant sweet-spot (§6) **and** the quant-ladder confound (§18). |
| `luccioni2024power` ✅ | Power Hungry Processing: Watts Driving the Cost of AI | FAccT 2024 · 2311.16863 | Measures **energy per inference**; generality is costly even at equal params — grounds our mWh axis + `granite4` (§6/§14). |
| `otel_genai` 📚 | OpenTelemetry — Semantic Conventions for GenAI | spec | The `gen_ai.*` telemetry conventions our harness emits. |

**Quotable lines (✅):**
- LLM in a flash: *"their substantial computational and memory requirements present challenges, especially for devices with limited DRAM capacity"*; cost model aimed at *"reducing the volume of data transferred … reading data in larger, more contiguous chunks."*
- 4-bit precision: *"4-bit precision is almost universally optimal for total model bits and zero-shot accuracy"*; *"a 30B 8-bit model and a 60B 4-bit model have the same number of bits but may have very different zero-shot accuracies."*
- Power Hungry Processing: *"multi-purpose, generative architectures are orders of magnitude more expensive than task-specific systems … even when controlling for the number of model parameters."*

---

## 4. AIOps / IT-operations benchmarks & on-prem deployment

| Key | Paper | Year / venue | What it is & why it matters here |
|---|---|---|---|
| `notaro2021survey` 📚 | A Survey of AIOps Methods for Failure Management | ACM TIST 2021 | The **AIOps** framing (detection→diagnosis→remediation) our scenarios echo. |
| `aiopslab2025` 📚 | AIOpsLab: Evaluate AI Agents for Autonomous Clouds | 2025 · 2501.06706 | An **agentic AIOps benchmark** — closest neighbor; we differ by targeting *small, offline, CPU-only, single-node* models. |
| `itbench2025` 📚 | ITBench: AI Agents across Real-World IT Automation | 2025 · 2502.05352 | Broad **IT-automation** agent benchmark — related work; same "differ by constraint envelope" contrast. |
| `bendimerad2023onprem` 📚 | On-Premise AIOps Infrastructure for an SME | 2023 · 2308.11225 | Experience report on **on-prem** AIOps — supports the sovereignty/offline motivation. |

---

## 5. Safety: reasoning, agent/tool-call, small-model & quantization

> These corroborate **axis #2 (safety)** and the reasoning-arm and quantization caveats. Pre-curated in the
> bib; not re-read this session. Several carry `2026xx` arXiv IDs — re-check before final submission.

| Key | Paper | Year / venue | What it is & why it matters here |
|---|---|---|---|
| `yong2026selfjailbreak` 📚 | Self-Jailbreaking after Benign Reasoning Training | ICLR 2026 · 2510.20956 | Reasoning training can **erode safety alignment** — context for the reasoning arm's lower refusal. |
| `zhou2025hiddenrisks` 📚 | The Hidden Risks of Large Reasoning Models (R1) | 2025 · 2502.12659 | Safety assessment of **R1-style** reasoners — supports our reasoning-arm safety gap. |
| `jiang2025safechain` 📚 | SafeChain: Safety with Long Chain-of-Thought | 2025 · 2502.12025 | Long-CoT **safety** behavior — relevant to reasoning-arm refusal. |
| `gap2026` 📚 | Mind the GAP: Text Safety ≠ Tool-Call Safety | 2026 · 2602.16943 | Text-level safety **doesn't transfer** to tool calls — supports per-action safety scoring (§17). |
| `osharm2025` 📚 | OS-Harm: Safety of Computer-Use Agents | NeurIPS D&B 2025 · 2506.14866 | Benchmark for **computer-use agent** harm — related safety work. |
| `ownerharm2026` 📚 | Owner-Harm: A Missing Threat Model | 2026 · 2604.18658 | **Owner-directed** harm threat model — frames our destructive-command scenarios. |
| `agentharm2025` 📚 | AgentHarm: Harmfulness of LLM Agents | ICLR 2025 · 2410.09024 | Widely-cited **agent harm** benchmark — related work. |
| `agenthazard2026` 📚 | AgentHazard: Harmful Behavior in Computer-Use Agents | 2026 · 2604.02947 | Computer-use agent hazards — related safety work. |
| `beyondtip2025` 📚 | Beyond the Tip of Efficiency: Jailbreaks in SLMs | Findings of ACL 2025 · 2502.19883 | **Small models** are more jailbreakable — supports the stakes-inverse-refusal caution. |
| `qresafe2025` 📚 | Q-resafe: Safety of Quantized LLMs | ICML 2025 · 2506.20251 | **Quantization** can degrade safety — context for the quant-ladder caveat (§18). |
| `caq2025` 📚 | Safety-Preserving PTQ via Contrastive Alignment | 2025 · 2511.07842 | Quant-aware **safety patching** — mitigation context. |
| `ease2026` 📚 | EASE: Safety Alignment for Small Language Models | AAAI 2026 · 2511.06512 | **SLM safety alignment** — mitigation context. |
| `guardslm2026` 📚 | GUARD-SLM: Defense Against Jailbreaks for SLMs | 2026 · 2603.28817 | Activation-based **SLM jailbreak defense** — mitigation context. |

---

## 6. Decision methods (MCDA) & statistics

| Key | Paper | Year / venue | What it is & why it matters here |
|---|---|---|---|
| `miettinen1999` 📚 | Nonlinear Multiobjective Optimization | Springer 1999 | Foundational **multi-objective / Pareto** theory — selecting one point from a front needs a preference (§3). |
| `hwangyoon1981` 📚 | Multiple Attribute Decision Making (TOPSIS) | Springer 1981 | **TOPSIS** — the distance-to-ideal ranker in PAPER §8d. |
| `lahdelma1998smaa` 📚 | SMAA — Stochastic Multiobjective Acceptability Analysis | EJOR 1998 | **SMAA** — the weight-distribution robustness method (win-share) in PAPER §8d. |
| `littlerubin2019` 📚 | Statistical Analysis with Missing Data | Wiley 2019 | **Missing-data** handling (DNF/timeout rows) discipline. |
| `chambers2013registered` 📚 | Registered Reports | Cortex 2013 | The **pre-registration** lineage for our locked hypotheses (§3). |
| `nosek2018prereg` 📚 | The Preregistration Revolution | PNAS 2018 | Why **pre-registration** matters — methods integrity. |
| `lakens2024deviate` 📚 | When and How to Deviate From a Preregistration | Collabra 2024 | How to **honestly deviate** — backs our disclosed post-hoc analyses. |

---

## Candidate additions (found useful but **not yet in the bib** — confirm before adding)

None pending — every paper read in the deep-analysis literature rounds has been added to
[references.bib](references.bib) and is catalogued above. New finds should be appended here first
with the intended key + arXiv ID, then promoted into the bib once verified.

---

*Maintenance:* when you read a new paper, add a row (with the intended bib key, the verbatim
quote you'll cite, and the section it grounds), then mirror the entry into
[references.bib](references.bib). Keep ✅/📚 honest — only mark ✅ for papers actually read.
