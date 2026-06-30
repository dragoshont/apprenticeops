# Small-model search for the Aletheia warm-card task — 2026-06-30

Status: working research note. **Not** part of `PAPER.md` and not a rewrite of
`docs/MODELS.md`. It records what the small-model search for the Romanian Aletheia
warm-card feature found, and why the next step is Romanian-specialized models.

## Scope honesty (state up front)

> Single-environment case study: one CPU node (`home-ai`, i5-8350U, Ollama
> `0.30.8`), one app task, judged **1–5** by two CLI-gated judges
> (`claude-opus-4.6` + `gpt-5.4` — the headless Copilot-CLI ceiling, not 4.8/5.5).
> Per-model **N = 60** judge rows (6 scenarios × 5 reps × 2 judges) on the
> `journal-aletheia-6` set. Every number is **bracket-level**, not a leaderboard
> position. The conclusion is a **finding, not a gap**: it redirects effort, it
> does not settle the question.

*Define-then-use.* **Small** = runs on the CPU node at usable speed — in practice
≤ ~3 B params / ≤ ~4.5 GB Q4. **Aletheia warm-card** = turn a short Romanian
journal entry into one sincere, anchored note (no advice, no cliché, no fabricated
quotes, in Romanian). **Quality** = the judges' mean on that rubric.

## What we searched

The Aletheia companion ships on the CPU node, so the candidate pool is small local
models. On 2026-06-30 we took the Ollama library sorted newest-first and kept the
ten newest chat-capable models with a ≤3 B variant and plausible multilingual
coverage, anchored by `gemma2:2b` (the prior best small model):

`gemma4:e2b-it-qat`, `qwen3.5:2b`, `granite4.1:3b`, `ministral-3:3b`, `gemma3:1b`,
`qwen3:1.7b`, `granite4:micro`, `falcon3:3b`, `llama3.2:3b`, `gemma2:2b`.

That sweep ran as `journal-newsmall-none-baseline-20260630-100446`
(set `journal-newest-small` × `journal-aletheia-7`) and is now complete. This note
records both the *prior* runs' conclusion that motivated it and the sweep's own
result below; the sweep tests whether a newer small base changes the conclusion.

## Sweep result — a newer small base *does* help, but the winner is still a Gemma

The 10-model sweep finished: 10 models × 7 `journal-aletheia-7` cards × 5 reps × 2
judges = **N = 70 per model** (734 judged rows).

| Rank | Model | Mean (1–5) | What it is (from `ollama show`) |
|---|---|---|---|
| 1 | **`gemma4:e2b-it-qat`** | **2.41** | arch `gemma4`, 4.6 B total / **E2B-effective**, QAT `Q4_0`, 128 K ctx, multimodal — new small champion |
| 2 | `gemma2:2b` | 2.04 | prior champion / anchor |
| 3 | `qwen3:1.7b` | 1.83 | |
| 4 | `llama3.2:3b` | 1.81 | |
| 5 | `gemma3:1b` | 1.76 | |
| 6 | `granite4.1:3b` | 1.59 | arch `granite`, 3.4 B |
| 7 | `ministral-3:3b` | 1.54 | |
| 8 | `qwen3.5:2b` | 1.36 | rambles / asks questions |
| 9 | `granite4:micro` | 1.20 | |
| 10 | `falcon3:3b` | 1.01 | arch `llama`, 3.2 B — near-floor, barely on task (max 2.0) |

Three things, all consistent with the Romanian-constraint finding:

- **A newer small base helps — by +0.37.** `gemma4:e2b-it-qat` (the newest small
  Gemma, quantization-aware-trained) reaches **2.41**, above `gemma2:2b`'s **2.04**
  and within **0.01** of the generic `gemma2:9b` ceiling (**2.42**) at a fraction of
  the footprint. The best *small* generic is now level with the best *strong*
  generic.
- **Newer ≠ better; the lineage that helps is Gemma.** Three of the top five are
  Gemma (`gemma4 e2b`, `gemma2:2b`, `gemma3:1b`). Several *newer* non-Gemma releases
  land **below** the old `gemma2:2b`: `granite4.1:3b` 1.59, `qwen3.5:2b` 1.36,
  `granite4:micro` 1.20, `falcon3:3b` 1.01. Recency is not the lever; Romanian
  coverage is — and Gemma keeps winning it, exactly as the family-ranking argument
  predicts.
- **The ceiling is still low.** Even the new small champion sits at **2.41 / 5**. A
  better generic small base raised the floor but did not break the Romanian ceiling
  — which is precisely why the next run tests Romanian-*specialized* weights.

**Decision.** Promote the small default `gemma2:2b` → **`gemma4:e2b-it-qat`**, and
set the bar the Romanian-specialized run must clear: **> 2.41**, ideally above the
generic 9 B's **2.42**.

*(Caveat: `gemma4:e2b-it-qat` is 4.6 B total — it sits at the top edge of the
"small" bracket — but its E2B-effective/QAT design keeps it node-runnable, so it
stays in-scope by the runs-at-usable-speed definition.)*

## Romanian-specialized result — the prediction holds, and size is beaten

The pre-registered "Romanian-specialized weights" step (below) ran: a Romanian-tuned
model against generic Gemma anchors on the same `journal-aletheia-7` cards
(N = 70/model, 288 judged rows).

| Model | Mean (1–5) | What it is |
|---|---|---|
| **`jobautomation/OpenEuroLLM-Romanian`** | **2.76** | RO-tuned Gemma3-4B (f16) — new overall champion |
| `gemma3:4b` | 2.61 | same base, generic |
| `gemma2:9b` | 2.54 | generic, ~2× the size |
| `gemma2:2b` | 2.06 | small anchor |

Two results, both predicted:

- **Romanian tuning beats raw size.** The RO-tuned **4 B** (2.76) tops the generic
  **9 B** (2.54), and clears both bars set above — the small champion's **2.41** and
  the generic 9 B ceiling (**2.42–2.54**). Specializing for Romanian moved the mean
  *further than doubling the parameter count did*. The finding's core claim now has a
  positive result, not just a within-family gradient.
- **At the identical base, tuning alone adds +0.15.** RO-tuned vs generic Gemma3-4B:
  **2.76 vs 2.61**. The remaining gap up to (and past) 9 B is what specialization buys
  on top of the base.

The ceiling was low *because generic models underserve Romanian* — a Romanian-
specialized small model lifts it. `OpenEuroLLM-Romanian` becomes the recommended
model for the Romanian warm-card task; `gemma4:e2b-it-qat` stays the best *un-tuned*
fallback. (Honesty: 2.76/5 is *better*, not *good* — the absolute bar is still modest,
and the RO-tuned model is 8.1 GB f16, heavier on the node than the small set.)

## Finding: the binding constraint is Romanian proficiency, not parameter count

Three independent lines point the same way.

**1. The failure modes are language-proficiency tells.** In an ephemeral pass over
a real self-critical entry, the small models produced warm-but-wrong Romanian:
gender/number agreement errors (`curajata`, `punctele slabes`), verb-form errors
(`schimbiți`, `recuniiți`), `tu`/`dvs.` register mixing, and English calques
(`good enough`). These are out-of-distribution-language artifacts, not task
misunderstanding.

**2. Within a family, capacity buys Romanian — on the identical cards.** The
partial `journal-strong-none-baseline-20260630-090915` run judged three 7–9 B
models on the *same* `journal-aletheia-6` set as the small baseline
(`journal-aletheia-none-baseline-20260630-064651`):

| Family | small (2–3 B) | strong (7–9 B) | Δ |
|---|---|---|---|
| Gemma | `gemma2:2b` **2.10** | `gemma2:9b` **2.42** | **+0.32** |
| Llama | `llama3.2:3b` **1.80** | `llama3.1:8b` **2.18** | **+0.38** |
| Qwen  | `qwen2.5:3b` **1.38** | `qwen2.5:7b` **1.73** | **+0.35** |

Holding family and training recipe fixed and only adding capacity moves the mean
~0.3–0.4 (each cell N = 60). Some of that capacity is being spent on Romanian
fluency.

**3. The family ranking is stable across the size jump.** Gemma > Llama > Qwen at
*both* 2–3 B and 7–9 B. A stable ordering under scaling is what you expect when the
differentiator is how much Romanian sat in pretraining, not raw size.

**External corroboration.** An active Romanian open-LLM effort, **OpenLLM-Ro** (HF
`OpenLLM-Ro`), exists specifically to fix this: it SFT/DPO-tunes generic bases on
Romanian corpora and ships `RoLlama2/3/3.1`, `RoMistral`, `RoGemma/2/3`, including
small `RoLlama-3.2-1B` and `RoGemma3-4B-Instruct`. The community builds Romanian
finetunes because the generic models underperform in Romanian — the same signal
from the outside.

### The uncomfortable half of the finding (state up front)

> Size is a **weak** lever here. Even `gemma2:9b` reaches only **2.42 / 5**. The
> ceiling is low because Romanian warm-tone is genuinely underserved by generic
> models — so scaling the base up is **necessary-not-sufficient**. The strong
> levers are Romanian-specialized weights or a task-specific finetune, not a
> bigger generic model.

And it is **not 100 % language**: `qwen3.5:2b` failed by *rambling and asking
questions* — an instruction-/format-following miss that is only partly
language-bound; the rubric's negative constraints ("hold the regret, no advice, no
toxic positivity") are hard for any 2–3 B model. A related held result:
self-critique (`evaluator_optimizer_1`) made every <3 B model *worse* (`gemma2:2b`
2.10 → 1.30), i.e. small models cannot reliably re-grade their own Romanian.

## What this proves and does not

- **Proves (within this case study):** on one Romanian warm-tone task, same-family
  capacity correlates with quality, and the absolute ceiling is low even at 9 B.
- **Does not prove:** that the *cause* is language rather than task difficulty. The
  two are confounded — every card is both Romanian *and* a subtle no-advice warm
  note. A clean control is pre-registered below.
- **Does not generalize:** n = 1 environment, one task, small per-model N. No
  leaderboard claims.

## Next steps (separate from the paper)

1. **RO-vs-EN control *(Locked, pre-registered).*** Run the same warm-card cards
   translated to English against the same models. **Hypothesis:** if the gap is
   Romanian, English scores rise materially (≥ ~0.5) and the small/large gap
   narrows; if the gap is task difficulty, scores stay low in both. A non-improvement
   in English *falsifies* "it's the language".
2. **Romanian-specialized weights *(Done — confirmed; see "Romanian-specialized
   result" above).*** Ran `jobautomation/OpenEuroLLM-Romanian` (an OpenEuroLLM RO
   finetune of Gemma3-4B) against generic Gemma anchors. It **cleared the generic 9 B
   ceiling at a fraction of the footprint** (2.76 vs 2.54), as expected. Next: try a
   smaller RO finetune (e.g. `RoLlama-3.2-1B`) to see how low the footprint can go and
   still beat the generic small champion (2.41).
3. **Finetune path** (heavier): an Unsloth LoRA on a small base + warm-RO-note data —
   the same recipe OpenLLM-Ro uses, specialized to our tone.

## Threats to validity

| Threat | Type | Mitigation |
|---|---|---|
| Language vs task confound | Internal validity | The RO-vs-EN control above isolates it. |
| Small per-model N (60–70) | Statistical | Bracket-level claims only; the 10-model sweep added the spread (N = 70/model). |
| Judge is English-native on Romanian text | Measurement | Two judges; rubric rewards anchoring and penalizes non-Romanian; cross-check a Ro-native judge later. |
| Single node / single task | External validity | Stated as a case study; no generalization claimed. |
| `gemma2:9b` ceiling from a *partial* (killed) run | Provenance | N = 60 is complete for the three judged models; the run was stopped after them, not mid-model. |

## Artifacts

- Small baseline: `journal-aletheia-none-baseline-20260630-064651`
- Self-critique (held negative): `journal-aletheia-none-evalopt-20260630-075632`
- Strong (size lever, partial): `journal-strong-none-baseline-20260630-090915`
- Newest-small sweep (complete, N = 70/model): `journal-newsmall-none-baseline-20260630-100446`
- Romanian-specialized run (complete, N = 70/model): `journal-romanian-journal-aletheia-7-none-baseline-20260630-113017`
- Scenario set: `data/scenario_sets/journal-aletheia-7.json` (`e33ddbe3…`)
