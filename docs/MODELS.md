# Downloadable Model List — by size bracket

> Vetted June 2026 against the Ollama library (sizes = q4_K_M / default unless
> noted; **GB = on-disk**, resident is ~GB + KV cache). All are **self-hostable,
> open-weight, free, pull-with-`ollama pull`** unless flagged. Brackets are by
> **parameter count**; the **4–5 GB** bracket is by *footprint* (per your "check
> larger quant if it fits" — that's where quantized 7–8B models land).
>
> `tools` column = does the Ollama packaging declare tool-calling (`ollama show`
> → Capabilities). **Irrelevant to the reasoning eval** (tool-less by design) but
> recorded because a tool-capable winner could also replace `tiny-h`.
> `think` = native reasoning/thinking mode.

Legend: ✅ yes · ❌ no · 〜 community/unofficial packaging (provenance risk —
see [`MARKET.md`](MARKET.md))

---

## Bracket 0–1B params (the "can it even reason" floor)

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Qwen2.5 0.5B | `qwen2.5:0.5b` | 0.40 | ✅ | ❌ | Apache-2.0 | strongest sub-1B all-rounder |
| Qwen3 0.6B | `qwen3:0.6b` | 0.52 | ✅ | ✅ | Apache-2.0 | thinking at 0.6B (slow but interesting) |
| Llama 3.2 1B | `llama3.2:1b` | 1.3 | ✅ | ❌ | Llama-3.2 (permissive) | Meta, tool-tuned |
| Gemma 3 1B | `gemma3:1b` | 0.82 | ❌ | ❌ | Gemma | QAT variant `1b-it-qat` (1.0 GB) |
| Granite 4 1B-H | `granite4:1b-h` | 1.6 | ✅ | ❌ | Apache-2.0 | hybrid-mamba, IBM, tool-tuned |
| SmolLM2 360M | `smollm2:360m` | 0.73 | ✅ | ❌ | Apache-2.0 | HF, tiny + tool tag |
| SmolLM2 135M | `smollm2:135m` | 0.27 | ✅ | ❌ | Apache-2.0 | absolute floor (sanity baseline) |

**Pick 5:** qwen2.5:0.5b, qwen3:0.6b, llama3.2:1b, granite4:1b-h, smollm2:360m.

---

## Bracket 1–2B params *(bonus — you skipped it, but it's the sweet spot for tiny reasoning)*

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Qwen3 1.7B | `qwen3:1.7b` | 1.4 | ✅ | ✅ | Apache-2.0 | best tiny *thinking* candidate |
| SmolLM2 1.7B | `smollm2:1.7b` | 1.8 | ✅ | ❌ | Apache-2.0 | strong for its size |
| Qwen2.5 1.5B | `qwen2.5:1.5b` | 0.99 | ✅ | ❌ | Apache-2.0 | dense workhorse |
| DeepSeek-R1 1.5B | `deepseek-r1:1.5b` | 1.1 | ❌ | ✅ | MIT | reasoning distill (Qwen2.5-1.5B base) |
| StableLM2 1.6B | `stablelm2:1.6b` | 0.98 | ❌ | ❌ | StabilityAI (check) | diversity entry |
| Llama 3.2 1B | (also fits) | 1.3 | ✅ | ❌ | Llama-3.2 | — |

**Pick 5:** qwen3:1.7b, smollm2:1.7b, qwen2.5:1.5b, deepseek-r1:1.5b, stablelm2:1.6b.

---

## Bracket 2–3B params

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Granite 4 Micro (3B) | `granite4:micro` | 2.1 | ✅ | ❌ | Apache-2.0 | **incumbent fallback** — baseline to beat |
| Qwen2.5 3B | `qwen2.5:3b` | 1.9 | ✅ | ❌ | Qwen (research/▲) | strong; check license for sharing |
| Phi-2 2.7B | `phi:2.7b` | 1.6 | ❌ | ❌ | MIT | classic dense reasoner |
| Gemma 2 2B | `gemma2:2b` | 1.6 | ❌ | ❌ | Gemma | Google small |
| Ministral-3 3B | `ministral-3:3b` | ~2.0 | ✅ | 〜 | Mistral (check) | NEW edge family; official tag |
| Llama 3.2 3B | `llama3.2:3b` | 2.0 | ✅ | ❌ | Llama-3.2 | (also fits 3–4B) |

**Pick 5:** granite4:micro, qwen2.5:3b, phi:2.7b, gemma2:2b, ministral-3:3b.

---

## Bracket 3–4B params

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Phi-4-mini 3.8B | `phi4-mini` | 2.5 | ✅ | ❌ | MIT | reasoning+math focus, *now* has function calling |
| Qwen3 4B | `qwen3:4b` | 2.5 | ✅ | ✅ | Apache-2.0 | thinking; `4b-instruct-2507` refresh is stronger |
| Qwen3 4B Instruct 2507 | `qwen3:4b-instruct-2507-q4_K_M` | 2.5 | ✅ | ❌ | Apache-2.0 | non-thinking, improved tool/IF |
| Gemma 3 4B | `gemma3:4b` | 3.3 | ❌ | ❌ | Gemma | QAT `4b-it-qat` (4.0 GB) is the value pick |
| Llama 3.2 3B | `llama3.2:3b` | 2.0 | ✅ | ❌ | Llama-3.2 | Meta |
| DeepSeek-R1 (Qwen3-4B distill) | `deepseek-r1:4b`* | ~2.5 | ❌ | ✅ | MIT | *verify tag exists; reasoning distill |

**Pick 5:** phi4-mini, qwen3:4b-instruct-2507, gemma3:4b-it-qat, llama3.2:3b, qwen3:4b (thinking).

---

## Bracket 4–5 GB footprint *(native 4–5B is rare → quantized 7–8B models that fit)*

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Granite 4 Tiny-H (7B-a1b MoE) | `granite4:tiny-h` | 4.2 | ✅ | ❌ | Apache-2.0 | **the current agent primary** — the bar |
| Mistral 7B v0.3 | `mistral:7b-instruct-q4_K_M` | 4.4 | ✅ | ❌ | Apache-2.0 | classic 7B, q4 fits |
| Ministral-3 8B (q4) | `ministral-3:8b`〜 / `doomgrave/...q4_K_S` | ~4.7 | ✅ | 〜 | Mistral (check) | official 8B; community q4 for low-VRAM |
| Qwen2.5 7B (q4) | `qwen2.5:7b` | 4.7 | ✅ | ❌ | Qwen (check) | strong 7B reasoner |
| DeepSeek-R1 7B (q4) | `deepseek-r1:7b` | 4.7 | ❌ | ✅ | MIT | reasoning distill (Qwen base) |
| Qwen3 4B Instruct 2507 q8 | `qwen3:4b-instruct-2507-q8_0` | 4.3 | ✅ | ❌ | Apache-2.0 | higher-fidelity small model |
| Gemma 3 4B q8 | `gemma3:4b-it-q8_0` | 5.0 | ❌ | ❌ | Gemma | quality-max small (edge of bracket) |

**Pick 5:** granite4:tiny-h (incumbent), mistral:7b, qwen2.5:7b, deepseek-r1:7b, qwen3:4b-instruct-2507-q8.

> ⚠️ **Footprint vs RAM:** 4–5 GB on disk → ~5–7 GB resident with an 8 K KV cache.
> All fit the 23 GiB node with wide headroom (unlike the rejected 19–23 GB
> laguna/small-h tier — see [`../README.md`](../README.md)).

---

## Cross-bracket notes

- **Reasoning specialists to watch:** the `deepseek-r1` distills (MIT) are
  explicitly reasoning-tuned and exist at 1.5/7/8B — strong hypotheses for the
  *diagnose* tasks, at the cost of verbose `<think>` (watch the token budget +
  watchdog).
- **Thinking models need `think:true`** and a **bigger `num_predict`** or they
  burn the budget thinking and never answer (we saw this with qwen3 earlier).
  Their profile is run separately and labelled.
- **License for "sharing over the internet":** Apache-2.0 / MIT (Qwen2.5,
  Qwen3, Granite, SmolLM, Phi, Mistral-7B, DeepSeek-R1, StableLM) are clean to
  redistribute/serve. **Gemma** (Google) and some **Qwen** tags have use-policy
  terms — read before exposing a public endpoint. Flagged in the table.
- **Provenance:** prefer **official library tags** (`mistral`, `ministral-3`,
  `phi4-mini`, `granite4`, `qwen3`, `gemma3`, `smollm2`, `deepseek-r1`). The
  `user/...` community forks (〜) are supply-chain risk — only use a specific one
  if you've vetted it (see [`MARKET.md`](MARKET.md)).

## Download budget (rough)

| Bracket | 5 models ≈ | 
|---|---|
| 0–1B | ~4 GB |
| 1–2B | ~6 GB |
| 2–3B | ~9 GB |
| 3–4B | ~13 GB |
| 4–5 GB | ~23 GB |
| **Total** | **~55 GB** transient (runner frees each after its run; node has 64 GB free) |

---

# Wave 3 — the missed models (expansion roster)

> Vetted **2026-06-20** against live Ollama-library / Hugging-Face pages (each tag
> below was fetched; sizes are the `q4_K_M` on-disk footprint unless noted).
> Waves 1+2 ran **106 distinct tags** — almost all **dense transformers** in
> `q4_K_M`/`q8_0`. Wave 3 deliberately attacks the axes that coverage missed, so
> the paper can say something about *architecture* and *quantization*, not just
> *which Qwen*. Runnable manifest: [`../data/models.wave3.txt`](../data/models.wave3.txt).
>
> The four Wave-3 axes:
> 1. **Non-transformer / hybrid arch** — Mamba-2 (`granite4:*-h`), conv-hybrid
>    (Liquid LFM2), Transformer+Mamba (Falcon-H1), MatFormer (`gemma3n`), and
>    native **1.58-bit ternary** (BitNet). These are bandwidth-bound very
>    differently from dense attention on a 15 W CPU.
> 2. **Capability specialists** — dedicated **coders** (CodeGemma, StarCoder2,
>    Granite-Code, OpenCoder, Yi-Coder), **math** (Qwen2-Math, DeepScaleR), and
>    fuller **reasoning-distill** coverage (SmallThinker, DeepSeek-R1-0528-Qwen3,
>    Cogito hybrid) — vs the general models tested so far.
> 3. **Under-sampled quants** — `q5_K_M`, `q6_K`, **I-quants** (`IQ4_XS`),
>    `bf16`, and more **QAT** (`gemma3:270m-it-qat`), for an isolated
>    quant-degradation curve on the *same* weights.
> 4. **Openness / provenance** — AllenAI **OLMo-2** is the only family with open
>    data+code+weights, letting us separate "open weights" from "open everything".

Legend (unchanged): ✅ yes · ❌ no · 〜 community/unofficial · ⚠️ real model, but
confirm the exact GGUF file / runtime before pulling (see notes).

## W3 · 0–1B params

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Gemma 3 270M | `gemma3:270m` | 0.29 | ❌ | ❌ | Gemma | sub-300 MB modern floor (only `1b` was tested) |
| Gemma 3 270M QAT | `gemma3:270m-it-qat` | 0.24 | ❌ | ❌ | Gemma | **QAT** quant axis at the extreme low end |
| Granite 4 350M | `granite4:350m` | 0.71 | ✅ | ❌ | Apache-2.0 | smallest **tool-tuned** model; dense Granite-4 |
| Granite 4 350M-H | `granite4:350m-h` | 0.37 | ✅ | ❌ | Apache-2.0 | **hybrid Mamba-2** at 350M (366 MB!) |
| Granite 4 350M bf16 | `granite4:350m-bf16` | 0.71 | ✅ | ❌ | Apache-2.0 | full-precision floor (quant-vs-bf16 pair) |
| LFM2 350M | `hf.co/LiquidAI/LFM2-350M-GGUF:Q4_K_M` | 0.26 | ✅ | ❌ | LFM Open v1.0 | Liquid **conv+attention hybrid** — new family |
| LFM2 700M | `hf.co/LiquidAI/LFM2-700M-GGUF:Q4_K_M` | 0.51 | ✅ | ❌ | LFM Open v1.0 | mid-rung of the LFM2 arch ladder |
| OLMo-2 1B Instruct | `hf.co/allenai/OLMo-2-0425-1B-Instruct-GGUF:Q4_K_M` | 0.94 | ❌ | ❌ | Apache-2.0 | **fully open** (data+code+weights); full quant ladder |
| Falcon-H1 0.5B | `hf.co/tiiuae/Falcon-H1-0.5B-Instruct-GGUF:Q4_K_M` ⚠️ | ~0.4 | ✅ | ❌ | Falcon-LLM | hybrid T+Mamba; confirm GGUF file before pull |
| ERNIE-4.5 0.3B | `hf.co/baidu/ERNIE-4.5-0.3B-PT-GGUF:Q4_K_M` ⚠️ | ~0.3 | ❌ | ❌ | Apache-2.0 | Baidu family absent; HF listing bot-blocked |

## W3 · 1–2B params

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| LFM2 1.2B | `hf.co/LiquidAI/LFM2-1.2B-GGUF:Q4_K_M` | 0.80 | ✅ | ❌ | LFM Open v1.0 | top of the Liquid hybrid ladder |
| LFM2 1.2B q8 | `hf.co/LiquidAI/LFM2-1.2B-GGUF:Q8_0` | 1.25 | ✅ | ❌ | LFM Open v1.0 | q8 pair of a hybrid (quant-sensitivity) |
| Falcon-H1 1.5B-Deep | `hf.co/tiiuae/Falcon-H1-1.5B-Deep-Instruct-GGUF:Q4_K_M` | 0.94 | ✅ | ❌ | Falcon-LLM | **Transformer+Mamba**, strong math/reasoning |
| Falcon-H1 1.5B IQ4_XS | `hf.co/tiiuae/Falcon-H1-1.5B-Deep-Instruct-GGUF:IQ4_XS` | 0.86 | ✅ | ❌ | Falcon-LLM | **I-quant** axis (untested quant family) |
| OpenCoder 1.5B | `opencoder:1.5b` | 1.4 | ❌ | ❌ | OpenCoder (open) | fully-reproducible **coder** (EN/ZH) |
| Qwen2-Math 1.5B | `qwen2-math:1.5b` | 0.94 | ❌ | ❌ | Apache-2.0 | dedicated **math** specialist |
| DeepScaleR 1.5B | `deepscaler:1.5b-preview-q4_K_M` | 1.1 | ❌ | ✅ | MIT | RL-tuned reasoner (≠ the R1 distill) |
| Sailor2 1B | `sailor2:1b` | 1.1 | ❌ | ❌ | Apache-2.0 | SE-Asian **multilingual** coverage |
| Yi-Coder 1.5B | `yi-coder:1.5b` | 0.87 | ❌ | ❌ | Apache-2.0 (Yi) | 01.AI coder, 128K ctx |
| EuroLLM 1.7B | `hf.co/utter-project/EuroLLM-1.7B-Instruct-GGUF:Q4_K_M` ⚠️ | ~1.1 | ❌ | ❌ | Apache-2.0 | EU 24-language; HF listing bot-blocked |

## W3 · 2–3B params *(thinnest — see note)*

> **Honest finding:** this bracket is *thin* precisely because the strong general
> 2–3B models (Gemma2-2B, Qwen2.5-3B, Phi-2, StableLM, Granite-2B, EXAONE-2.4B,
> Falcon3-3B) are **already tested**. What remains NEW at 2–3B is almost entirely
> niche/architectural or regional-multilingual — which is itself a result.

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| CodeGemma 2B | `codegemma:2b` | 1.6 | ❌ | ❌ | Gemma | code/FIM specialist |
| CodeGemma 2B q6_K | `codegemma:2b-code-q6_K` | 2.1 | ❌ | ❌ | Gemma | **q6_K** quant axis of a 2B coder |
| Granite 4 Micro-H | `granite4:micro-h` | 1.9 | ✅ | ❌ | Apache-2.0 | **hybrid Mamba-2** twin of `micro` (== `granite4:3b-h`, same blob) |
| StarCoder2 3B | `starcoder2:3b` | 1.7 | ❌ | ❌ | BigCode OpenRAIL-M | transparent coder; **OpenRAIL** license axis |
| Gemma 3n E2B | `gemma3n:e2b` ⚠️ | 5.6 | ❌ | ❌ | Gemma | **MatFormer**; 5.6 GB on disk (eff-2B, raw ~5B) — RAM-fits, over footprint |
| Falcon-H1 3B | `hf.co/tiiuae/Falcon-H1-3B-Instruct-GGUF:Q4_K_M` ⚠️ | ~1.9 | ✅ | ❌ | Falcon-LLM | hybrid T+Mamba; confirm GGUF file |
| BitNet b1.58 2B-4T | `hf.co/microsoft/bitnet-b1.58-2B-4T-gguf` ⚠️ | ~1.2 | ❌ | ❌ | MIT | **native 1.58-bit ternary**; needs `bitnet.cpp` (stock llama.cpp lacks 1-bit kernels) |

## W3 · 3–4B params

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| Qwen3 4B Thinking-2507 | `qwen3:4b-thinking-2507-q4_K_M` | 2.5 | ✅ | ✅ | Apache-2.0 | the **thinking** 2507 refresh (only `-instruct` was tested) |
| Qwen3 4B Thinking q8 | `qwen3:4b-thinking-2507-q8_0` | 4.3 | ✅ | ✅ | Apache-2.0 | q8 pair (quant-vs-reasoning) |
| SmolLM3 3B | `hf.co/ggml-org/SmolLM3-3B-GGUF:Q4_K_M` | 1.9 | ✅ | ✅ | Apache-2.0 | **hybrid-reasoning, fully-open** 3B |
| Hermes-3 Llama-3.2 3B | `hf.co/NousResearch/Hermes-3-Llama-3.2-3B-GGUF:Q4_K_M` | 2.0 | ✅ | ❌ | Llama-3.2 | Nous function-calling lineage (agentic) |
| MiniCPM3 4B | `hf.co/openbmb/MiniCPM3-4B-GGUF:Q4_K_M` | 2.5 | ✅ | ❌ | MiniCPM GML | strong tool/code-interpreter calling |
| Cogito v1 3B | `cogito:3b` | 2.2 | ✅ | ✅ | Llama-3.2 | **hybrid reasoning toggle** + tools (deepcogito) |
| Granite-Code 3B | `granite-code:3b` | 2.0 | ❌ | ❌ | Apache-2.0 | IBM **code** model |
| SmallThinker 3B | `smallthinker:3b-preview-q4_K_M` | 2.1 | ❌ | ✅ | Apache-2.0 | Qwen2.5-3B **reasoning** distill |
| Cogito v1 3B q8 | `cogito:3b-v1-preview-llama-q8_0` | 3.8 | ✅ | ✅ | Llama-3.2 | q8 pair of `cogito:3b` (quant axis) |
| StarCoder2 3B | `starcoder2:3b` | 1.7 | ❌ | ❌ | BigCode OpenRAIL-M | (listed in 2–3B; also fits here) |

## W3+ · 3–4B quant-degradation sweep at the knee (expansion)

> 3–4B is the **quality plateau** of the whole study, so it is the most valuable
> place to measure *quantization* precisely. Net-new 3–4B families are genuinely
> scarce (the same finding as 2–3B), so this expansion goes **deep, not wide**: a
> `q4`→`q8` (+ I-quant) curve on four reputable anchors already in Wave 3. Every
> tag was fetched + size-verified; all official or reputable-quantizer.

| Anchor | Pull tag | GB | quant | prov. | note |
|---|---|---|---|---|---|
| Llama-3.2-3B | `hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q6_K` | 2.64 | Q6_K | bartowski (imatrix) | high-K point; pairs w/ tested `llama3.2:3b` q4+q8 |
| Llama-3.2-3B | `hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q5_K_M` | 2.32 | Q5_K_M | bartowski | mid-K point |
| Llama-3.2-3B | `hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:IQ4_XS` | 1.83 | IQ4_XS | bartowski | **I-quant** point (CPU-viable) |
| Llama-3.2-3B | `hf.co/bartowski/Llama-3.2-3B-Instruct-GGUF:Q3_K_L` | 1.82 | Q3_K_L | bartowski | low-bit edge (degradation tail) |
| SmolLM3-3B | `hf.co/ggml-org/SmolLM3-3B-GGUF:Q8_0` | 3.28 | Q8_0 | official (ggml-org) | q8 pair of the Wave-3 q4_K_M |
| Hermes-3-3B | `hf.co/NousResearch/Hermes-3-Llama-3.2-3B-GGUF:Q8_0` | 3.42 | Q8_0 | official (Nous) | q8 pair of the Wave-3 q4_K_M |
| Granite-Code 3B | `granite-code:3b-instruct-q6_K` | 2.9 | q6_K | official (IBM) | coder q6 point |
| Granite-Code 3B | `granite-code:3b-instruct-q8_0` | 3.7 | q8_0 | official (IBM) | coder q8 point |
| StarCoder2 3B | `starcoder2:3b-q6_K` | 2.5 | q6_K | official (BigCode) | coder q6 point |
| StarCoder2 3B | `starcoder2:3b-q8_0` | 3.2 | q8_0 | official (BigCode) | coder q8 point |

Together with the `q4` endpoints already in the roster this yields a **6-point
Llama-3.2-3B curve** (q3→IQ4→q4→q5→q6→q8), **2-point** SmolLM3 and Hermes-3
(q4↔q8), and **3-point** Granite-Code and StarCoder2 (q4→q6→q8) — a clean read
on how much quality the knee actually loses to quantization.

## W3 · 4–5 GB footprint *(only 3, per request)*

| Model | Pull tag | GB | tools | think | License | Note |
|---|---|---|---|---|---|---|
| OLMo-2 7B Instruct | `olmo2:7b` | 4.5 | ❌ | ❌ | Apache-2.0 | **fully open** 7B — the provenance/openness anchor |
| Cogito v1 8B | `cogito:8b` | 4.9 | ✅ | ✅ | Llama-3.1 | hybrid reasoning **+ tool-calling** at the top |
| DeepSeek-R1-0528-Qwen3 8B | `deepseek-r1:8b-0528-qwen3-q4_K_M` | ~5.2 | ✅ | ✅ | MIT | best small **reasoning distill** of 2025 (≠ tested `r1:7b`) |

> ⚠️ The 0528-Qwen3 distill is **~5.2 GB** (marginally over). Clean-fit
> alternates: `deepseek-r1:8b-llama-distill-q4_K_M` (4.9 GB), `granite3.3:8b`
> (4.9 GB, Apache, think+tools), `falcon3:7b-instruct-q4_K_M` (4.6 GB).
> **Excluded — non-commercial weights** that would taint the Apache-2.0 shareable
> artifact: `command-r7b`, `aya-expanse:8b`, `exaone3.5:7.8b`.

## Wave-3 coverage gaps (why these, in priority order)

1. **Hybrid SSM / Mamba & non-transformer arch — the single largest blind spot.**
   Waves 1+2 are ~all dense transformers. Wave 3 finally probes Mamba-2 hybrids
   (`granite4:*-h`, 350m→3b), Liquid LFM2 (350M→1.2B), Falcon-H1 (0.5B→3B),
   gemma3n MatFormer, and native 1.58-bit BitNet — all bandwidth-bound very
   differently on a 15 W CPU.
2. **Capability specialists were entirely absent** — no dedicated coders, no math
   models, only partial reasoning-distill coverage.
3. **Quant axes were under-sampled** — testing clustered on `q4_K_M`/`q8_0`;
   Wave 3 adds `q5_K_M`/`q6_K`, **I-quants** (`IQ4_XS`), `bf16`, and more QAT.
4. **Provenance/openness** — OLMo-2 (fully reproducible) is the only family that
   separates "open weights" from "open everything".
5. **Vendor breadth** — first coverage of AllenAI, Liquid AI, TII (Falcon-H1),
   Nous, deepcogito, BigCode, 01.AI, OpenBMB, Microsoft (BitNet), Baidu, Sea AI
   Lab (Sailor2), Agentica.

> **Verification note (2026-06-20):** ~33 of ~40 tags were fetched and confirmed
> against the live model/GGUF page (size, license, params, file list), including
> every Ollama-native entry above. The **⚠️** items are real models whose exact
> GGUF file or runtime needs a manual confirm before pulling (four HF listings
> were bot-blocked; BitNet needs `bitnet.cpp`; gemma3n is over-footprint). **No
> tag was invented** — every ⚠️ names the exact uncertainty to resolve.

## W3 · Wave-2 backfill (re-run the transient pull-failures)

> Wave 2 finished **71/80 models complete**; **9 had zero usable rows** — all
> transient pull-failures (Ollama's intermittent `hf.co` redirect bug
> [#15661](https://github.com/ollama/ollama/issues/15661) + registry blips),
> **not** missing models. `hf.co` pulls were re-verified working on the node
> (2026-06-20), so these ride along in the Wave-3 sweep to complete Wave 2.
> Brackets are their **original Wave-2** assignment (backfill, not new W3 picks).

| Bracket | Pull tag | why it was missing |
|---|---|---|
| 0–1B | `granite3.1-moe:1b` | registry blip |
| 0–1B | `granite3.1-moe:1b-instruct-q8_0` | registry blip |
| 0–1B | `hf.co/google/gemma-3-1b-it-qat-q4_0-gguf:Q4_0` | hf.co redirect bug |
| 2–3B | `exaone3.5:2.4b` | registry blip |
| 2–3B | `exaone3.5:2.4b-instruct-q4_K_M` | registry blip |
| 2–3B | `exaone3.5:2.4b-instruct-q8_0` | registry blip |
| 2–3B | `exaone-deep:2.4b` | registry blip |
| 2–3B | `stablelm-zephyr:3b` | registry blip |
| 3–4B | `hf.co/google/gemma-3-4b-it-qat-q4_0-gguf:Q4_0` | hf.co redirect bug |
