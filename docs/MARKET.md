# Adversarial Market Analysis — small-model reasoning

> The job of this doc is to make us *distrust* the model marketing before we
> spend hours testing, so the eval is designed to catch the lies. Pairs with
> [`PLAN.md`](PLAN.md) (which bakes these defenses in) and [`MODELS.md`](MODELS.md).

## 1. The central hype pattern: "our 3B beats GPT-4"

Every small-model release ships a benchmark table where it "matches" or "beats" a
model 50× its size. This is almost always true **on the cited benchmark** and
almost always false **in your use**. Three mechanisms:

1. **Benchmark contamination.** The test sets (GSM8K, MMLU, HumanEval) are in the
   training data. A small model can memorize answers it cannot *reason* to. This
   is why the Open LLM Leaderboard moved to **v2** (MMLU-**Pro**, harder/cleaner
   GPQA gated, MuSR algorithmically generated) — and why **our Axis-B homelab
   suite uses YOUR cluster's incidents**, which are in nobody's training set.
2. **Narrow tuning.** A model tuned to ace IFEval/format can still be a poor
   diagnostician. Format-following ≠ reasoning.
3. **Cherry-picked quant.** Headline numbers are the **fp16/q8** model; the q4
   you'll actually run is weaker, and the q2/q3 they *don't* benchmark is much
   weaker (§4).

**Defense:** decision is **Axis B only** (homelab suite, frontier-judged, % of
Opus 4.8). Academic scores are a *contamination sanity check*, never the verdict.

## 2. What each bracket can realistically do (honest priors)

Before testing, my expectation — to be confirmed/refuted by data:

| Bracket | Likely *can* | Likely *cannot* | Watch for |
|---|---|---|---|
| **0–1B** | Classify/extract, format JSON, 1-step "is X broken?" | Multi-step root-cause, safe-fix reasoning | confident nonsense (no calibration) |
| **1–2B** | Short summaries, simple diagnosis, follow format | 3-hop reasoning, novel fixes | drops facts under longer context |
| **2–3B** | Decent monitor/summary, single-fault diagnosis | Multi-fault correlation, upgrade planning | the incumbent `granite4:micro` lives here — the bar |
| **3–4B** | Real diagnosis, structured plans, most ops prose | Deep correlation, subtle safety calls | **best value tier — likely the winners** |
| **4–5 GB** | Strongest reasoning that fits; closest to frontier-lite | Still not frontier; slow on CPU (~4–8 tok/s) | speed/RAM trade vs the 3–4B tier |

**Prediction (falsifiable):** the **3–4B tier (phi4-mini, qwen3:4b, llama3.2:3b)**
is the sweet spot — enough reasoning to be useful, small enough to be fast. The
4–5 GB tier wins accuracy but may not be worth the tok/s on this CPU. The
sub-2B tier is for *extraction/format* scheduled tasks, not *diagnosis*. We test
to confirm, not to assume.

## 3. Provenance & supply-chain risk (you're sharing these over the internet)

This is the part the benchmark tables never mention and that matters most for a
shared endpoint.

- **Prefer official library publishers.** `qwen3`, `granite4`, `gemma3`,
  `phi4-mini`, `mistral`, `ministral-3`, `smollm2`, `deepseek-r1` are first-party
  or Ollama-curated. Pull those.
- **Community forks (`user/model`) are unvetted.** The Ministral search alone
  surfaced `peacedude/ministral-3-3b-merged`, `doomgrave/...q4`,
  `aratan/Ministral-3-14B-Reasoning`, `pstdio/microcoder` — random merges/quants
  of unknown calibration and **unknown weight integrity**. A poisoned/merged GGUF
  can carry biased or jailbroken behaviour you'd then serve to others. Treat them
  like the `Cowork-Local-LLM` / `hermes-agent-desktop` repos we already flagged:
  **don't ship what you didn't vet.**
- **Weights are opaque.** Unlike code you can read, a `.gguf` is a black box. Pin
  the **digest** (`ollama show` ID), record it, and re-pull only by digest. A tag
  can be re-pushed; a digest can't.
- **License ≠ permission to serve.** Gemma's and some Qwen tags' use policies
  restrict redistribution / certain uses. For a public endpoint, stick to
  **Apache-2.0 / MIT** (Qwen2.5/3, Granite, SmolLM, Phi, Mistral-7B, DeepSeek-R1).

## 4. The quant honesty problem

Quantization is sold as free; it isn't, and the cheap quants are where small
models die:

- **q8 → q4** is usually a fair trade (and on this bandwidth-bound box, q4 is
  *faster*). **q4 → q3/q2** often **collapses** small models — a 1–3B model has
  little redundancy to spare, so q2 can turn a working reasoner into a babbler.
- **QAT (quant-aware-trained)** beats post-hoc q4 at the same size (we proved this
  with gemma — `it-qat` was faster *and* better than default q4). Prefer QAT tags
  where they exist (`gemma3:*-it-qat`).
- **Defense:** test the **specific quant you'll deploy**, never extrapolate from
  the headline fp16 number. The harness records the exact digest.

## 5. The "reasoning model" trap

`deepseek-r1` distills and `qwen3`/`thinking` models advertise reasoning — and
they can genuinely diagnose better. But:

- They emit long `<think>` chains → **burn the token budget and the wall-clock**
  (directly hits the §6 watchdog). A thinking model that's right but takes 240 s
  is a *batch* tool, not interactive.
- On a CPU node, "think more" = "wait more" linearly. The decode-tok/s is the
  same; they just emit 5× the tokens.
- **Defense:** thinking models run on their **own profile** (`think:true`, larger
  `num_predict`, longer timeout) and are scored on a separate
  *accuracy-vs-latency* curve, not lumped with instant models.

## 6. The LLM-as-judge is itself a bias risk

Using Opus 4.8 to grade introduces known biases: **self-preference** (favours
answers in its own style), **verbosity bias** (longer = better), **position
bias** (first answer scored higher). The eval mitigates (randomize order, blind
the model identity, require evidence citations, hand-validate 15 %), but the
**honest caveat** stands: the judge is a strong proxy, not ground truth. That's
exactly why every scenario also has **deterministic checks** — the parts where
truth is unambiguous (right component? valid JSON? non-destructive?) don't go
through the judge at all.

## 7. The uncomfortable likely conclusion

We should name the probable outcome up front so we're not disappointed:

> **A ≤5 GB model will not match the frontier at homelab diagnosis.** The realistic
> win is finding the model that hits **"good enough for scheduled/pipeline ops"**
> — detect, summarize, extract, draft — at a speed/RAM that fits. The *agentic*
> "fix it live" work stays with `tiny-h` + tools or a frontier escalation; this
> eval is about the **tool-less reasoning floor for unattended jobs**, and that's
> a real, useful thing to pin down — just not a frontier replacement.

If the data surprises us (a 4B genuinely nails diagnosis), great — but the plan is
built to **earn** that claim against your own cluster's incidents, not to inherit
it from a marketing table.

## 8. What would make me change the recommendation

- A 1–3B model scoring ≥ 80 % of frontier on Axis B → promote to interactive.
- A thinking model winning accuracy *and* staying under ~90 s → worth the batch tier.
- Any model failing the **safety** scenario class (suggests destructive actions)
  → **disqualified for a shared endpoint** regardless of other scores.
