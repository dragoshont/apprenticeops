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

## Steps log (autonomous run)
1. Verified data semantics → 2. truncation/proxy/quant batteries → 3. scenario/RAG/consistency/DNF →
4. clustering + proxy-τ → 5. **root-cause** (truncation = 400–600 tok cap, 83% non-think; timeout =
r1:7b slow×overthink) → 6. systems telemetry + **difficulty-label inconsistency** → 7. built
`model_metadata.csv` + **size-controlled granite4 efficiency** → 8. **multi-method ranking robustness**
(HELM mean-win-rate + Arena Bradley–Terry, τ 0.95–1.00; judged↔judge-free τ 0.74) → 9. literature
round (Mamba 5× throughput; Power-Hungry-Processing energy-per-inference; SLM survey; Model Cards) →
10. safety per-action (**stakes inversely ∝ refusal**: secrets 45%, destructive 48%) + quant-ladder
confound + judge calibration (ρ 0.91, style discount on terse models). Artifacts: `model_metadata.csv`,
this draft. Remaining: promote vetted findings to PAPER.md (with caveats); add covariate + multi-method
figures; optionally a per-bracket champion table.

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
