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
