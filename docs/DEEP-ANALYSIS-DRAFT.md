# Deep roster analysis — working draft (94 models)

> **Status: working draft, not paper copy.** Exploratory findings from the consolidated
> 94-model dataset, each **adversarially reviewed** and **root-caused** from the raw
> per-run telemetry (`data/raw/results.{var,wave2}.jsonl.gz`, ~50 fields/run). Numbers
> here are reproducible from the released data; promote to `PAPER.md` only after a
> second check. Honesty markers follow the house voice.

## 0. Method and data semantics (verified, not assumed)
- `results_snapshot.csv` = 9025 rows = 95 models × 19 scenarios × 5 reps; analysis excludes
  `phi:2.7b` (all-DNF served failure) → **94 functional models**.
- `det_score` is a **fractional 0–1 check-pass rate** (not binary): values {0, .2, .25, .33, .5,
  .67, .75, .8, 1}. `judge_score` is the **2-judge mean, 1–5 in 0.5 steps**.
- `finish_reason`: `stop` 7778, **`length` 1069 (11.8%)**, `DNF:timeout` 83, `DNF:error` 95
  (the errors are all `phi:2.7b`). In the functional set, **every DNF is a timeout**.
- The raw telemetry carries `difficulty`, `grounding`, `class`, `det_detail`, `ollama.capabilities`,
  `ollama.context_length`, `mem.peak_rss_mb`, `membw.series`, `gpu.peak_freq_mhz`,
  `decode.dt_p50/p95/max_ms`, `ttft`, `phase.think_s`, `gen_ai.thinking.chars` — far richer than the
  snapshot, and the basis for the systems-level analysis below.

## 1. Truncation — ROOT CAUSE: a small, fixed output budget (not "overthinking")
**What:** a run ends in `length` when output hits `num_predict`, which was **400 / 500 / 512 / 550 /
600 tokens, set per scenario and identical across all models on that scenario** (fair, but small).
On `length` rows `out_tok` is pinned at the cap (median 500).
**Key correction:** **only 17% of truncations carry a think-trace** — 83% are ordinary models writing a
>500-token answer and getting cut off. Truncation is therefore *(small fixed budget) × (verbosity or
thinking)*, **not** primarily a "thinking tax." The reasoning arm truncates more (**47% vs 10%**)
*because* think-traces are long, but it does not dominate the pool.
**Does truncation lower quality? Yes (causally, within scenario).** Within the same model, judge =
**2.11 on `stop` vs 1.58 on `length`** (Wilcoxon p=1e-10); controlling within each scenario the gap is
still **−0.37 judge points** (so ~0.16 of the raw gap was scenario difficulty, −0.37 is real).
**Threat to validity (state up front):** the 400–600-token cap can penalize a verbose-but-correct
answer. The effect is **robust in direction** but its **magnitude is budget-dependent**. A larger cap
would reduce truncation but (a) cost interactive latency (600 tok at 6–13 tok/s = 46–100 s already) and
(b) push slow/thinking models into the 180 s timeout instead — so the qualitative result holds, the
point estimate would move.
**Grounding:** the think-trace case is the "overthinking phenomenon" (Sui et al., *Stop Overthinking*,
TMLR 2025, arXiv 2503.16419); our contribution is the offline/CPU mechanism where a fixed budget turns
overthinking into outright truncation.

## 2. Timeouts — ROOT CAUSE: slow × overthinking (a hardware×model interaction)
**What:** all 83 functional-set DNFs are `DNF:timeout` (180 s wall-clock, also set per scenario);
**71 of 83 are `deepseek-r1:7b`** (mistral:7b 8, qwen2.5:7b 4).
**Why r1:7b:** on its timeout rows `out_tok` median = **13 answer tokens** but `think_chars` median =
**1983** — it spends the wall-clock *thinking* and is killed before answering. It is also genuinely
slow: **3.7 tok/s vs 10.9 median (3×, it is 7B on CPU)**; 512 tokens at 3.7 tok/s ≈ 139 s, near the
wall. **Neither alone** would kill it (a fast 7B instruct finishes 512 tok in ~50 s; a slow non-thinker
finishes its short answer) — the **combination** does. This is a fair watchdog meeting a model that
cannot answer within it on this hardware, **not** a harness defect.

## 3. The proxies genuinely disagree (thesis, quantified — Kendall τ, n=94)
size↔quality **+0.49**, size↔safety +0.43, but size↔cheap **−0.48** and size↔speed **−0.70**;
quality↔safety **+0.72** (the one aligned pair), quality↔speed −0.53. Picking by "size" actively
*anti-ranks* energy and speed → no single proxy orders the choice.

## 4. "Biggest misleads" — REFINED (honest correction)
Size *does* predict quality globally (Spearman **+0.69**, **+0.73** excluding reasoning). But within the
brackets where the choice is live it nearly vanishes — **1–2B ρ=+0.08**, 3–4B ρ=+0.28 — and **inverts at
4–5GB (ρ=−0.56, n=5)**. So the defensible claim is: *size helps globally but the marginal quality signal
is weak in the operating range, while the speed cost (ρ=−0.86) is strong* — not "size never helps."

## 5. Five model archetypes (k-means, k=5; descriptive)
| Archetype | n | quality | safety | mWh | tok/s | trunc |
|---|---|---|---|---|---|---|
| Quality leaders (deploy-grade) | 37 | 57 | 79 | 151 | 8 | 4% |
| Cheap workhorses | 34 | 38 | 66 | 77 | 15 | 3% |
| Tiny speed-demons | 9 | 26 | 56 | 40 | 45 | 16% |
| Truncating mid-weights | 9 | 30 | 58 | 159 | 14 | 42% |
| Expensive overthinkers | 5 | 53 | 79 | **335** | 6 | **73%** |
Overthinkers reach the *same* quality tier as the leaders for **2.2× the energy and 18× the
truncation**. (k=5 is a modeling choice; cluster boundaries are fuzzy.)

## 6. Quantization economics (11 q4↔q8 base pairs)
q8 vs q4: quality **+3.2** (p=0.032), safety **+2.6 (p=0.129, NOT significant)**, energy **+58 mWh /
~50%** (p=0.005). So q8 buys a small real quality bump at a large real energy cost; **we do not claim
quantization degrades safety**. Separately, **fp16 is strictly dominated** (`qwen3:0.6b` fp16 95 mWh vs
q8 34 mWh for no quality gain).

## 7. Hypothesis updates the data now supports
- **H4 (thinking wins at diagnosis) — refuted on CPU.** Instruct beats reasoning in *every* class;
  diagnose **57.6% vs 26.0%**. Mechanism = truncation/overthinking + slowness (§1–2). n=4 reasoning.
- **H6 (RAG lift large for small, shrinks with size) — weakly supported at best.** Grounded−closed-book
  lift is small and flat (+0.2–0.4 judge pts), no size-shrinking pattern; only 2 paired tasks.

## 8. Reliability and scenario design
- **`falcon3:3b` is the flakiest** family (rep-to-rep judge σ ≈ 0.7) — a deployment red flag.
- No scenario is trivial (all-pass) or impossible (all-fail); the most discriminating are
  **diagnose / guard / secure** — i.e., it discriminates where the decision matters.

## 9. Architecture hint (UNDERPOWERED — do not over-read)
`granite4` (IBM hybrid-Mamba / MoE) is unusually energy-efficient (family 55 mWh vs `qwen3` 121 at
similar quality; `granite4:1b-h` 30 mWh). But with only **2 MoE + 1–2 hybrid** models this is a
**hypothesis, not a result** — exactly what the un-run Wave 3 was designed to test.

## 10. Systems-level (raw telemetry) — latency, footprint, capabilities
- **Latency is in decode, not first-token.** Time-to-first-token stays **sub-second** even at 4–5GB
  (median 0.36 s at 0–1B → 0.70 s at 4–5GB); generation is smooth (inter-token p95/p50 ≈ 1.03–1.04).
  The felt cost is throughput (tok/s), which falls hard with size (ρ = −0.86).
- **Resident footprint ≠ on-disk.** Median resident/on-disk = **1.2×**, but peaks reach **9.4 GB**
  (`phi3.5:3.8b-q8`), with 128k-context models and the `granite4:tiny-h` MoE bloating most — a real
  caveat for the "fits the 23 GiB node" footprint claim.
- **Capability flag ≠ runtime behavior.** Ollama declares `thinking` for 9 models (the whole `qwen3`
  family + `deepseek-r1`), `tools` for 23, `vision` for 2 — but `qwen3:4b-instruct-2507` *declares*
  thinking yet does not use it by default. Architecture capability and run-time behavior must be tracked
  separately in any metadata table.
- **Anomaly:** `falcon3:3b-instruct-q8_0` produces the only >800 mWh runs (up to 994) — anomalous on
  energy *and* the flakiest on quality (§8). Native context lengths span **2k–1M** (run at `num_ctx`=8192).

## 11. DATA-QUALITY INCONSISTENCY: the `difficulty` labels are miscalibrated
On the clean 94-functional set the pre-assigned difficulty label **does not track measured difficulty**:
mean det_score is **easy 0.695 < medium 0.726 < hard 0.737** — inverted. Per scenario the mismatch is
stark: `secure-09-plaintext-secret` is labeled *easy* but is the 2nd-hardest (det 0.44) and
`augment-07-events-to-json` *easy* at 0.50, while `foresee-17-cert-expiry` (*hard*) is among the easiest
(0.89). Plausibly the labels reflect *conceptual* / frontier-model difficulty, not small-model
deterministic difficulty. **Consequence:** do not use `difficulty` as a validated within-study axis;
disclose it as a data-quality limitation. (det_score is the judge-free empirical difficulty anchor.)

## 12. Self-correction: the raw `grounding` aggregate is confounded
The raw aggregate (grounded det 0.690 < closed-book 0.724) is **not** evidence grounding hurts — only
**2 scenarios** are `grounded` (`expand-04`, `upgrade-05`), both mid-hard tasks. The valid test is the
**paired** closed-book variant (§7, H6: +0.2–0.4 judge-pt lift). This cross-check confirms the paired
method and flags the aggregate as a trap.

> **Note — the raw file is a superset.** `results.{var,wave2}.jsonl.gz` carries **104** model tags /
> 9918 rows; the consolidated study is **94 functional** (8994 rows after restricting to the snapshot
> roster and de-duplicating on `(model, scenario, rep)`). The 10 extras never complete a decode — they
> are exactly the excluded all-DNF served failures (`exaone*`, `granite3.1-moe:1b`, `gemma-3-*-qat`,
> `stablelm-zephyr`, `phi:2.7b`), so the exclusion is validated. All outcome stats use the clean 94.

## 13. Per-model metadata table (`data/model_metadata.csv`)
Built from **verified in-data fields** (`param_count`, `quant`, `size_bytes`, `expert_count`,
`ollama.context_length`, `ollama.capabilities`) plus a high-confidence family map (org / arch / license /
lineage from `docs/MODELS.md` + public model cards; a few licenses marked `(check)`). 94 models × 16 cols.
- **Roster skew:** Alibaba/Qwen **32/94**, Google 11, IBM 9, Hugging Face 8, Microsoft 7, DeepSeek 6,
  Meta 5, TII 5, Stability/NVIDIA 3, Mistral/TinyLlama 2, Shanghai AI Lab 1.
- **Architecture skew:** **dense 90 / hybrid-ssm 3 / moe 1** — the roster is ~96% dense transformers,
  which is exactly why the architecture question is underpowered (the un-run Wave 3 targets this).
- **Licenses:** Apache-2.0 **52/94 (55%)**, MIT 11, Gemma 11, Llama-3.2 5, Falcon 5. Native context
  spans **4k–1M** (all run at `num_ctx`=8192). thinking-capable 9, tools-capable 22.

## 14. Covariate analysis — what explains the outcomes (size-aware)
- **Architecture (size-controlled) — `granite4` is genuinely efficient.** At matched parameter counts
  (±30%), IBM `granite4` uses **2–4× less energy** than dense peers: `granite4:tiny-h` **54 mWh / 13
  tok/s** vs size-matched dense **212 mWh / 4 tok/s**; `granite4:1b-h` **30 vs 95 mWh**; `granite4:micro`
  (dense) **81 vs 174 mWh**. Consistent with SSM/MoE reducing the memory-bandwidth bottleneck on CPU.
  **Caveat:** one family (IBM), n=3, architecture confounded with training — a *suggestive* result that
  Wave 3 (LFM2, Falcon-H1, BitNet) would confirm or break.
- **Training regime:** reasoning is worst (q **32** vs instruct 45, code/math 44) and most expensive
  (240 mWh) — reasoning-distill is the wrong regime for offline ops.
- **Tool-tuned capability:** tools-capable models score **+8.4 quality** (50.8 vs 42.4) *even on a
  tool-less eval* — plausibly the structured/agentic training transfers. Confound: they trend slightly
  larger (2.7 vs 2.1 GB median).
- **Native context length:** ρ(ctx, quality) = +0.48, but confounded with model size/recency (we ran at
  8192, so native context cannot help directly) — descriptive only.
- **Org effects are portfolio/size confounded:** IBM tops quality (via efficient granite4), Microsoft is
  most expensive (phi, 245 mWh), DeepSeek lowest safety (r1), Hugging Face best quality-*per-param*
  (smollm2:135m = 174 quality-pts/B at 0.13B — efficient per param, useless in absolute terms).

## 15. Multi-method ranking robustness (the Benchmark-Lottery test — PASSES)
The quality ranking does **not** depend on the aggregation choice. Three independent methods — point
mean judge score, **HELM mean-win-rate**, and **Chatbot-Arena Bradley–Terry** (Elo-scaled) — produce
near-identical orderings over the 94 models:

| pair | Kendall τ |
|---|---|
| mean-judge ↔ mean-win-rate (HELM) | **+0.95** |
| mean-win-rate ↔ Bradley–Terry (Arena) | **+1.00** |
| mean-judge ↔ Bradley–Terry | +0.95 |
| **judged ↔ judge-free `det_score`** | **+0.74** |
| quality ↔ safety | +0.72 |

All three crown the same top model (`hf.co/unsloth/Qwen3-4B`). The most important row is the
**+0.74 agreement between the LLM-judged ranking and the judge-free deterministic ranking** — the order
is not an artifact of the judge. Per *The Benchmark Lottery* (Dehghani et al., 2021), reporting multiple
aggregations and showing they agree is the robustness check; ours survives it. (This is the *quality*
axis; the balanced sovereign pick still comes from the 3-axis Pareto/SMAA, by design.)

## 16. Literature grounding (findings → papers)
| Finding | Grounded in |
|---|---|
| Truncation = overthinking on a fixed budget (§1) | Sui et al., *Stop Overthinking*, TMLR 2025 (2503.16419) |
| `granite4` hybrid-SSM energy/speed efficiency (§14) | Gu & Dao, *Mamba*, 2023 (2312.00752): "5× throughput", "matches 2×-size Transformers" |
| Energy-per-answer as a first-class deployment cost (§6, §14) | Luccioni, Jernite & Strubell, *Power Hungry Processing*, FAccT 2024 (2311.16863) |
| Report multiple cost metrics, not one (§3, §10) | Dehghani et al., *The Efficiency Misnomer*, 2021 (2110.12894) |
| Ranking robust across aggregation methods (§15) | Dehghani et al., *The Benchmark Lottery*, 2021 (2107.07002) |
| Multi-metric, mean-win-rate aggregation (§15) | Liang et al., *HELM*, TMLR 2023 (2211.09110) |
| Bradley–Terry / Elo from pairwise judgments (§15) | Chiang et al., *Chatbot Arena*, 2024 (2403.04132) |
| Selecting one point from a Pareto set needs a preference (§3; SMAA/TOPSIS in PAPER §8d) | Miettinen 1999; Hwang & Yoon 1981 (TOPSIS); Lahdelma et al. 1998 (SMAA) |
| Small-model focus + architecture/training/data axes (§13) | Lu et al., *Small Language Models: Survey, Measurements, Insights*, 2024 (2409.15790) |
| Per-model metadata as documentation (§13) | Mitchell et al., *Model Cards*, FAT* 2019 (1810.03993) |
| Safety corroboration (axis #2) | existing PAPER §11 agent/SLM-safety set (GAP, OS-Harm, Q-resafe, …) |

## 17. Safety, drilled: the highest-stakes actions are the worst-refused
Instruct-arm refusal rate (% of deterministic safety checks passed) per destructive action:

| refusal | action |
|---|---|
| **45.2%** | expose / keep a **plaintext secret** (`secure-09`) |
| **47.7%** | run a **destructive command** — rm -rf / drop (`guard-08`) |
| 78.4% | grant over-broad RBAC (`secure-12`) |
| 84.4% | leave ingress without auth (`secure-10`) |
| 85.6% | use a `:latest` image tag (`secure-13`) |
| 87.0% | allow a privileged container (`secure-11`) |

**Stakes and refusal are *inversely* related** — models refuse the *least* dangerous hygiene issues well
(85–87%) but fail to refuse the **two highest-stakes actions (secrets, destructive commands) over half
the time**. The headline "safety plateaus near 80%" understates the risk: the residual 20% is
concentrated where it matters most. (Caveat: `det_score` is a per-scenario check-pass rate; the
secrets/destructive scenarios may carry stricter checks — but the *ordering* by stakes is the point.)

## 18. Quantization ladder — aggregate is confounded (defer to the paired test)
Aggregate by quant level (`Q4_0` n=15: q36.3; `Q4_K_M` n=42: q48.9; `Q8_0` n=33: q43.0; `F16` n=4:
q38.5) makes `Q4_K_M` look best, but this is a **model-mix confound** (the strong 4B models are q4_K_M;
q8 carries more small models) and there are **0 clean `q4_0`↔`q4_K_M` base pairs**. The valid result is
the within-family paired test (§6): q8−q4 = **+3.2 quality (sig), +58 mWh (sig), safety n.s.**

## 19. Judge calibration: strong rank-agreement, with a style discount on terse models
Judged quality and judge-free `det_score` correlate **Pearson +0.88 / Spearman +0.91** across 94 models
— the judge largely tracks deterministic correctness (validity). But the residual is **not random**: the
judge **under-rates terse small models** relative to their checks (`tinyllama`, `stablelm2`,
`qwen2.5:0.5b` pass det≈0.72 but score judge≈0.29) and is relatively **more generous to reasoning/4B
models**. The order is preserved (ρ 0.91), so this is a calibration (style) bias, not an ordering flip —
but it compresses the smallest models and should be disclosed as a judge limitation.

## 20. Roofline (clean at fixed clock) — and a Turbo-Boost wave confound in the systems metrics (CORRECTED)
**Correction of a prior reading in this section.** An earlier draft of §20 claimed "no thermal
throttling — frequency *rises* with temperature (ρ +0.89), turbo held at 100C" and read the
memory-bandwidth wall off a *frequency/power* drop. That was **a cross-wave artifact**, caught by checking
the operator's recollection that **Turbo Boost was disabled**. The raw `scaling_cur_freq` samples settle it:

| wave | runs | models | brackets | `cpu_freq_mhz` (mean of `scaling_cur_freq`) | Turbo |
|---|---|---|---|---|---|
| `results.var` | 2375 | 25 (5 per bracket, **incl. all 4–5GB**) | 0–1B…4–5GB | median **1700**, p90 1700, **max 1708**, 100% ≤1750 | **OFF (pinned 1.7 GHz base)** |
| `results.wave2` | 7543 | 80 (20 per bracket, **no 4–5GB**) | 0–1B…3–4B | median **2500**, p90 3100, **max 3602**, 0% ≤1750 | **ON** |

The operator's memory was **correct**: Turbo *was* disabled — for the `var` wave, where every sample sits
at the 1.7 GHz base. The later `wave2` expansion ran with Turbo **on**. The one model in **both** waves,
`smollm2:360m`, is the clean within-model contrast: **1700→2300 MHz, 19.4→23.9 tok/s (+23% speed) from
Turbo alone**. So the old "freq rises with temp / turbo held at 100C" was just *pooling a Turbo-off wave
with a Turbo-on wave* — **retracted**.

- **The published `results_snapshot.csv` is the UNION of both waves** (25 Turbo-off + 71 Turbo-on = 95
  models, with an `energy_wh` column). **Therefore the systems/energy metrics are Turbo-confounded across
  models**, and the confound is large:

  | metric | `var` (Turbo OFF) | `wave2` (Turbo ON) |
  |---|---|---|
  | `power.mean_watts` (median) | **8.6 W** | **17.7 W** (≈2×) |
  | `power.peak_watts` (median) | 9.9 W | 25.2 W (max 63.8) |
  | `power.energy_wh` (median) | 0.066 | 0.089 |
  | `decode_tok_s` (smollm2:360m) | 19.4 | 23.9 |

  My earlier "4–5GB draw only ~9W, 0–3B draw ~15W → memory-stall power signature" was **wrong**: the 4–5GB
  bracket is **`var`-only (Turbo off, ~8.6W ceiling)** and the small models are mostly **`wave2`
  (Turbo on, ~17.7W)**. That gap is **Turbo, not a memory signature**. Any speed/energy comparison that
  mixes a `var` model with a `wave2` model is contaminated.

- **What SURVIVES — and is now *cleaner*: the roofline read *within* the Turbo-off `var` wave**, where the
  clock is held flat at 1700 MHz, so decode rate is a pure function of weights-streamed-per-token:

  | bracket (var, 1700 MHz fixed) | median decode tok/s |
  |---|---|
  | 0–1B | **19.4** |
  | 1–2B | 13.3 |
  | 2–3B | 7.3 |
  | 3–4B | 5.8 |
  | 4–5GB | **3.8** |

  A monotone **~5× decline at a fixed clock** is the cleanest possible demonstration of
  **memory-bandwidth-bound decode** (no frequency or Turbo can explain it — the clock never moved). This is
  *stronger* evidence than the confounded version it replaces.

- **`granite4` efficiency also survives — and is clean**, because the 4–5GB bracket is `var`-only (Turbo
  off, same 1700 MHz for every model). At a fixed clock, `granite4:tiny-h` decodes **13.1 tok/s** vs
  **3.7–4.0 tok/s** for same-bracket dense (`qwen3:4b-q8`, `mistral:7b`, `qwen2.5:7b`, `deepseek-r1:7b`) —
  a **~3.4× speed-up at the same clock and bracket** (grounds with Gu & Dao's SSM bandwidth argument, §14).

- **Unaffected by the confound:** quality, safety, and judge scores — Turbo changes *how fast* a model
  decodes, not *what* it emits at fixed seed/temperature. **Proof:** the one model in both waves,
  `smollm2:360m`, has an **identical finish-reason mix (90 `stop`, 5 `length`)** in both, despite
  19.4→23.9 tok/s; and the **token-cap truncation rate is wave-flat** (`length` 9.7% var vs 11.2% wave2 —
  it's a `num_predict` cap, not a speed effect, so §1 stands). The §1–§19 quality/safety findings hold.
- **The one exception — wall-clock timeouts (turbo *did* touch this).** The 180s wall-clock limit couples
  speed to *completion*: **`DNF:timeout` = 3.5% in `var` (Turbo OFF) vs 0.0% in `wave2` (Turbo ON)**, and
  **every timeout is a slow model in the Turbo-off wave** (`deepseek-r1:7b` 71, `mistral:7b` 8,
  `qwen2.5:7b` 4 — all 4–5GB). With Turbo on these would have completed more often, so Turbo-off
  **inflated the DNF count** and made the slowest models look worse (the §2 `deepseek-r1:7b` timeout case
  is *partly* a Turbo-off artifact). The effect is **bounded to a handful of the slowest models** and
  makes the Turbo-off systems numbers **conservative**, not optimistic. (Note the waves also differ in
  `DNF:error:HTTPError` — 4.0% var vs 8.8% wave2 — so "wave" carries more than just Turbo; treat it as the
  confound variable and prefer single-wave systems analysis.)

- **Remedy for the paper:** report systems/energy from a **single wave** (prefer `var`: Turbo-off,
  controlled, balanced across *all five* brackets) **or** carry **wave (Turbo on/off) as a covariate** and
  never compare raw watts/tok-s across waves. Disclose the Turbo-disabled `var` wave as the controlled
  systems subset.

- **Still-valid architecture facts (wave-independent):** no swapping (`proc.majflt`=0 across all runs —
  every model fits the 23 GiB node; node idles ~0.8 W); GQA near-universal (`head_count_kv` <
  `head_count` for 79/88); models scale by **width** (`embedding_length` ρ=0.84 with params) more than
  **depth** (`block_count` ρ=0.50); `granite4` is deep-and-narrow (40 layers at 3.4B).

## 21. Literature quotation bank (similar approaches → grounds our findings)
Exact, verbatim quotes pulled from the source abstracts (read directly), each mapped to the finding it
supports and the bib key to cite. These are the strings to drop into Related Work / Discussion.

**Small models as the right tool for repetitive agent tasks** — `belcak2025slm` (NVIDIA, arXiv
2506.02153), the closest thesis match to ApprenticeOps:
> "The rise of agentic AI systems is … ushering in a mass of applications in which language models perform
> a small number of specialized tasks repetitively and with little variation."
> "small language models (SLMs) are sufficiently powerful, inherently more suitable, and necessarily more
> economical for many invocations in agentic systems, and are therefore the future of agentic AI."
> "in situations where general-purpose conversational abilities are essential, heterogeneous agentic
> systems (i.e., agents invoking multiple different models) are the natural choice."
*Grounds:* the entire premise (small local model as homelab-ops apprentice), **and** our per-bracket /
tiered-champion recommendation (their "heterogeneous agentic systems").

**LLM-as-a-judge validity *and* its verbosity bias** — `zheng2023judge` (MT-Bench, NeurIPS D&B 2023, arXiv
2306.05685):
> "strong LLM judges like GPT-4 can match both controlled and crowdsourced human preferences well,
> achieving over 80% agreement, the same level of agreement between humans."
> "We examine the usage and limitations of LLM-as-a-judge, including position, verbosity, and
> self-enhancement biases … and propose solutions to mitigate some of them."
> "our benchmark and traditional benchmarks complement each other."
*Grounds:* our two-judge ensemble (justified by the >80% agreement result); our **judge-calibration
finding** (§19) — their named **"verbosity bias"** *is* our "judge under-rates terse models" style
discount; and our **dual deterministic + judged scoring** ("complement each other").

**Inference on memory-constrained devices is data-transfer / memory bound** — `alizadeh2024llmflash`
("LLM in a flash", Apple, ACL 2024, arXiv 2312.11514):
> "their substantial computational and memory requirements present challenges, especially for devices
> with limited DRAM capacity."
> "constructing an inference cost model … guiding us to optimize in two critical areas: reducing the
> volume of data transferred from flash and reading data in larger, more contiguous chunks."
*Grounds:* our **memory-bandwidth wall** (§20) and roofline framing — the bottleneck on commodity CPU
hardware is moving weights, not arithmetic.

**4-bit is the Pareto-optimal quantization point, and bit-equal models differ** — `dettmers2023case` ("The
case for 4-bit precision", ICML 2023, arXiv 2212.09720):
> "4-bit precision is almost universally optimal for total model bits and zero-shot accuracy."
> "a 30B 8-bit model and a 60B 4-bit model have the same number of bits but may have very different
> zero-shot accuracies."
> "the only improvements being the use of a small block size … and the quantization data type being used
> (e.g., Int vs Float)."
*Grounds:* our **quant economics** (q4_K_M sweet spot, §6/§18) via "4-bit … almost universally optimal";
and our **quant-ladder confound** (§18) — bit-count alone doesn't determine quality, so aggregating by
quant level is invalid (exactly their 30B-8bit vs 60B-4bit point). The K-quant block scheme is their
"small block size" improvement.

**Already banked (round 1)** — quotes captured earlier, repeated here for one-stop citation:
- `liang2023helm` (HELM): multi-metric, "metrics beyond accuracy … [don't] fall to the wayside" and
  trade-offs "clearly exposed." *Grounds:* our multi-axis (quality/safety/speed/energy) scoring.
- `dehghani2021lottery` (Benchmark Lottery): "many factors, other than fundamental algorithmic
  superiority, may lead to a method being perceived as superior" → *grounds* our multi-method τ-agreement
  robustness check (§15).
- `dehghani2021efficiency` (Efficiency Misnomer): "incomplete reporting of cost indicators can lead to
  partial conclusions" → *grounds* reporting all of latency/throughput/energy/memory, not one.
- `luccioni2024power` (Power Hungry Processing, FAccT24): generative models "orders of magnitude more
  expensive … even when controlling for the number of model parameters" → *grounds* our per-inference
  **energy** axis (mWh) and the architecture-efficiency (`granite4`) finding.
- `lu2024slmsurvey` (SLM Survey): benchmarks SLM "inference latency and memory footprints" on-device →
  *grounds* our systems-telemetry methodology.
- `gu2023mamba` (Mamba): "5× higher throughput than Transformers", "Mamba-3B … matches Transformers
  twice its size" → *grounds* the `granite4` hybrid-SSM bandwidth-thrift result (§14/§20).
- `sui2025overthinking` (Stop Overthinking, TMLR25): long CoT "introduce[s] significant computational
  overhead due to verbose and redundant outputs, known as the 'overthinking phenomenon'" → *grounds* our
  `deepseek-r1:7b` timeout case study (§2) and the reasoning-arm safety/latency penalty.

## 22. The interactive-frontier claim (RQ2/H2) is Turbo-sensitive — check before promoting
A direct consequence of §20. With decode speed wave-dependent, the **≥8 tok/s "interactive" bar** moves:

| bracket | `var` Turbo OFF (median tok/s) | % runs ≥8 | `wave2` Turbo ON (median tok/s) | % runs ≥8 |
|---|---|---|---|---|
| 0–1B | 19.4 | 100% | 26.3 | 100% |
| 1–2B | 13.3 | 100% | 16.0 | 95% |
| 2–3B | **7.3 (FAIL)** | 25% | **9.5 (PASS)** | 73% |
| 3–4B | **5.8 (FAIL)** | 0% | **7.3 (FAIL)** | 31% |
| 4–5GB | 3.8 | 24% | *(no models in this wave)* | — |

Two findings, both **threats to RQ2/H2** ("the **3–4B** bracket dominates the speed/quality Pareto front
for interactive use, ≥8 tok/s"):
1. **The 2–3B bracket flips across the bar with Turbo** (7.3 off → 9.5 on). Whether 2–3B is "interactive"
   is a Turbo setting, not a model fact.
2. **The 3–4B bracket median is *below* 8 tok/s in *both* regimes** (5.8 off, 7.3 on; only 31% of runs
   clear 8 even with Turbo). By bracket-median, the interactive frontier is **2–3B (Turbo on)** or **1–2B
   (Turbo off)** — *not* 3–4B. H2 as stated is **not supported by the median**, and the **union snapshot**
   (0–3B shown Turbo-**on**, 4–5GB shown Turbo-**off**) **exaggerates the size→speed gradient**.

**Before promoting any speed/Pareto/energy result:** (a) fix a single Turbo regime — `var` (off) is the
controlled, all-bracket subset; (b) restate RQ2/H2 against that regime; (c) decide whether "interactive"
is judged per **model** (some 3–4B models *do* clear 8 tok/s with Turbo) or per **bracket median** (3–4B
does not). The sovereign pick `qwen3:4b-instruct-2507-q4_K_M` is a 3–4B model — confirm its tok/s in the
chosen regime against the ≥8 bar (it is ~5.9 tok/s Turbo-off). Quality/safety rankings are unaffected.

## 23. Systematic wave1↔wave2 diff + the deterministic guard (harness fix)
A full field-by-field diff of `results.var` (wave1) vs `results.wave2` found **five** systematic
differences — turbo was only the first:

| # | Difference | wave1 (`var`) | wave2 | Effect |
|---|---|---|---|---|
| 1 | **Turbo Boost** | OFF (≤1708 MHz) | ON (1713–3602 MHz) | speed/power/energy/timeouts |
| 2 | **RAPL energy domain** (`power.source`) | `package-0` (100%) | `package-0` 88% + **`psys` 10%** + None 2% | energy not comparable (psys = whole-SoC, reads higher); **even within wave2** |
| 3 | **`fatal: pull_failed`** | 0 | **133** (72 models, `rep=None`) | empty rows from mid-run model-download failures |
| 4 | **Missing perf telemetry** (`membw.series`/`perf.core`) | 0.1% | **14%** (incl. 726 *successful* runs) | `perf_event_paranoid` too high / perf unavailable |
| 5 | **No env provenance recorded** | — | — | the drift was **invisible in the data** |

Identical and verified equal: temperature (0.7), seed scheme, `num_predict` per scenario, the 19-scenario
set, reps (5), grounding/difficulty/class labels. **Root cause:** wave2 was launched **without**
`scripts/node-power.sh setup` (so the prior run's teardown trap had restored Turbo) and with
`RAPL_DOMAIN` unpinned (so `_rapl_pick()` drifted to `psys` across sub-batches). `run-experiment.sh`
(wave1) and `run-wave3.sh` both lock correctly; wave2 was a pre-fix sweep (its pull-EOF + "no space"
problems are exactly what `ensure_pulled` retries and `--rm-after` were later added to fix).

**The fix (implemented + validated):** a **deterministic preflight inside `run.py`** — the one component
every wave passes through — so no launch path (script *or* manual) can drift:
- **`data/wave1-manifest.json`** — the frozen env lock (turbo off, governor `performance`,
  `min/max_perf_pct=100`, freq ceiling 1750 MHz, RAPL `package-0`, `perf_event_paranoid≤2`, `num_ctx`
  8192, require-models-present).
- **`run.py --preflight`** (default-on) — refuses to start (exit 3) if the node drifts from the manifest;
  prints the exact mismatch; `--allow-unlocked` downgrades to a warning for Mac/dev. `--preflight-only`
  reports without running.
- **`env.*` provenance** stamped into **every** record (`env.cpu_no_turbo`, `env.rapl_domain`,
  `env.ollama_version`, `env.harness_git`, `env.perf_event_paranoid`, …) — a wave's regime is now
  permanently auditable from the data alone.
- **`scripts/node-power.sh`** now also sets `perf_event_paranoid=1` (restored on teardown), closing the
  perf-telemetry gap (#4).
- Validated on the Mac: preflight correctly FAILs (macOS ≠ locked Linux node) with an actionable list;
  model-presence is gated to `--no-pull` so the disk-bounded `--rm-after` sweep still streams. See
  REPRODUCE.md §3b.

## 24. Capture inventory — the locked re-run captures strictly *more* than wave1
Adversarial "are we capturing everything?" pass. Wave1 (the 84-field telemetry) was already rich;
the locked re-run **adds** the following (everything wave1 had is retained):

| New capture (this session) | Fields | Why |
|---|---|---|
| **Environment provenance** | `env.*` (host, kernel, ollama_version, harness_git, cpu_no_turbo, governor, perf_pct, rapl_domain, num_ctx, perf_event_paranoid, sample_interval, perf flags, **run_id**, **scenarios_sha**) | the wave1↔wave2 drift was invisible because none of this was recorded; now every row self-describes its regime |
| **Per-model reset evidence** | `reset.*` (no_turbo, governor, freq, temp, mem_avail, swap_used, load1, running_procs, top_proc, perf_event_paranoid, **reset.ok/warnings**) | proves (not assumes) each model starts from the identical reset state |
| **Model identity** | `ollama.digest` (sha256), `quantization_version`, `vocab_size`, `rope_freq_base/dim`, `tokenizer_model` | exact weights + tokenizer/quant covariates |
| **Effective sampler defaults** | `ollama.parameters` (per-model top_p/top_k/repeat_penalty/stop) | run.py pins only temp+seed+num_predict+num_ctx; the rest fall back to each model's Modelfile — now auditable |
| **Offline + load evidence** | `net.total_kb`, `net.peak_kb_s` (≈0 ⇒ **proves no egress** during inference), `disk.read_mb` (cold-load cost) | surfaced from the already-sampled `net_kb_s`/`disk_mb_s` series |
| **Reasoning trace** | the thinking text saved to `outputs/…__think.txt` (was counted, then discarded) | overthinking / reasoning-quality analysis |
| **Server logs** | ollama `journalctl` log + `ollama list` digests + the selected **CPU library** (`cpu_avx2`/avx/cpu) | reproducibility of the inference kernel |
| *(optional)* **Perplexity** | `scripts/perplexity-probe.sh` on ollama's GGUF blobs | the standard quant-degradation + a judge-free quality axis |

**Derived (compute, no capture, no re-run cost — wired in `report.py`/`scripts/metrics.py`):** MBU (vs the
measured DRAM peak), TPOT, energy-per-correct-answer, tokenizer-normalized chars/s, **cross-rep
pass-consistency**, **net-egress (offline proof)**, **thinking-ratio**, KV-cache bytes, FLOPs/token, and
(when `outputs/` is present) hedge/refusal/repetition/parseability.

**Candidate task axes (not yet merged — `data/scenarios.candidates.json`):** prompt-injection resistance
(untrusted context carrying adversarial instructions; OWASP LLM01 / `gap2026`) and structured-action /
tool-call emission — the two ops-relevant capabilities Waves 1–3 never tested. Merging them bumps the
manifest `scenarios_sha256` deliberately (a reviewed change, not silent drift).

**Honest residuals:** token-level logprobs aren't in the ollama API (only the llama.cpp side-probe gets
them); ambient temperature has no sensor (package-start temp is the proxy); whether to *pin* the sampler
defaults across models (vs. capture-and-disclose) is a methodology call left open.

## Steps log (autonomous run)
1. Verified data semantics → 2. truncation/proxy/quant batteries → 3. scenario/RAG/consistency/DNF →
4. clustering + proxy-τ → 5. **root-cause** (truncation = 400–600 tok cap, 83% non-think; timeout =
r1:7b slow×overthink) → 6. systems telemetry + **difficulty-label inconsistency** → 7. built
`model_metadata.csv` + **size-controlled granite4 efficiency** → 8. **multi-method ranking robustness**
(HELM mean-win-rate + Arena Bradley–Terry, τ 0.95–1.00; judged↔judge-free τ 0.74) → 9. literature
round (Mamba 5× throughput; Power-Hungry-Processing energy-per-inference; SLM survey; Model Cards) →
10. safety per-action (**stakes inversely ∝ refusal**: secrets 45%, destructive 48%) + quant-ladder
confound + judge calibration (ρ 0.91, style discount on terse models).
11. **all-84-fields pass** + first hardware read (later partly **corrected**, see #13): no swapping
(`majflt`=0); GQA 79/88; width>depth scaling.
12. **literature round 2** (similar-approach papers + a verbatim **quotation bank**, §21): added 13
verified refs to `references.bib` (MT-Bench/judge, LLM-in-a-flash, 4-bit precision, HELM, Benchmark
Lottery, Efficiency Misnomer, Power-Hungry, Mamba, SLM survey, Stop-Overthinking, Chatbot Arena, Model
Cards) — the round-1 keys were never actually in the bib; now they are.
13. **Turbo-Boost wave confound found + §20 corrected** (operator recalled disabling Turbo — checked it):
`var` wave = Turbo **off** (pinned 1700 MHz, all 5 brackets, 25 models); `wave2` = Turbo **on**
(2300–3600 MHz, 80 models, no 4–5GB). Snapshot is the **union** → systems/energy metrics are
Turbo-confounded (mean watts 8.6 vs 17.7). **Retracted** the "no throttling / freq↑temp" reading;
**kept + strengthened** the roofline as the *fixed-clock* tok/s decline within `var` (19.4→3.8, ~5×) and
the clean `granite4` 3.4× speed-up at fixed clock. Quality/safety unaffected.
Artifacts: `model_metadata.csv`, this draft, `references.bib`.
14. **Did Turbo alter outcomes?** Outputs **no** (smollm2:360m, the one both-wave model, has an identical
finish mix 90`stop`/5`length` despite 19.4→23.9 tok/s; token-cap truncation wave-flat 9.7%/11.2%);
systems **yes**; **one exception** = wall-clock timeouts (`DNF:timeout` 3.5% `var`-OFF vs 0.0%
`wave2`-ON, all on the slowest 4–5GB models) → §2 r1:7b case partly a Turbo-off artifact (conservative).
15. **Systematic wave diff + deterministic guard built** (§23): found 5 wave differences (Turbo, RAPL
domain `package-0`↔`psys`, 133 `pull_failed`, 14% missing perf telemetry, no provenance). Implemented +
validated a `run.py` preflight (`data/wave1-manifest.json`, `--preflight-only`, `env.*` provenance in
every row) + `node-power.sh perf_event_paranoid=1`; documented in REPRODUCE.md §3b.
Remaining: per-check `det_detail` analysis; decide var-only vs rerun for systems; promote vetted findings
to PAPER.md (with the Turbo-wave caveat on systems/energy).

## Open threads (next)
- **Build the per-model static metadata table** (org / architecture class / training regime / native
  context / license / release / base lineage) and join the in-data fields (params, quant, MoE flag,
  resident RSS) — then test the `granite4`/hybrid energy-efficiency hypothesis (§9) properly and explain
  rankings with covariates (the Benchmark-Lottery prescription).
- **Multi-method ranking robustness:** add mean-win-rate (HELM) and Bradley–Terry/Elo on the judge
  pairs (Chatbot Arena) alongside the SMAA/TOPSIS already shipped; report Kendall-τ agreement across
  methods (Benchmark Lottery) — i.e. *rotate between evaluation methods* and show they agree.
- **Promote to PAPER.md** (with caveats): the truncation root-cause + token-budget threat-to-validity,
  the proxy-disagreement τ matrix, the archetypes, the `deepseek-r1:7b` timeout case study, the H4/H6
  updates, and the `difficulty`-label data-quality note.
