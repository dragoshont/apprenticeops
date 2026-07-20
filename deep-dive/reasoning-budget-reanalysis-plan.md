# Reasoning-budget re-run — competing-risks / ITT re-analysis plan

**Date:** 2026-07-20 · **Status:** plan (pre-registered before the run finishes) ·
**Governs run:** `reasoning-budget-v1v2-nocap-20260717-112750`
(14 models × 20 scenarios × 5 reps = **1400 assigned cells**;
`max_tokens=4096`, `timeout_s=600`, config `core-current-nocap.json`)

This plan is the fix for **consensus blocker #2 / Claude C1** of
`adversarial-methodology-review.md`: the re-run's 600 s wall is *informative*
(MNAR) censoring, so any comparison on **completed** cells is survivorship-biased
**toward the study's own hypothesis**. It also encodes GPT-5.6 Sol's **two-knob
confound**. Pre-registering the estimand and the analysis *before* the data lands
prevents the "conclusion-inversion" failure the MSc reflection warns about.

It respects **`AGENTS.md` lesson 8**: this re-run is a **standalone mechanism
study**, never a patch spliced into the 152-model run. No number here is merged
into, compared cell-for-cell against, or promoted into the 152 corpus.

---

## 1. The problem this plan exists to prevent

The naïve reading of the finishing run is: *"we gave the thinking models 8× the
token budget; on the answers they produced, quality is as good as / better than
instruct → the earlier thinking-mode penalty (finding 17) was just a budget
artifact."* That reading is **invalid by construction** for three compounding
reasons:

1. **Informative (MNAR) censoring.** The 600 s wall does not fire at random. It
   fires *preferentially on the long-chain reasoning lineages the study wants to
   vindicate* (interim: qwen3:4b-thinking ≈ 57–71 % `DNF:timeout`, exaone-deep /
   smallthinker high; instruct variants ≈ 0 %). Timeout correlates with model type
   **and** with the latent verbosity/difficulty that also drives the score. The
   completed subset is therefore a **non-random, hypothesis-favouring sample** of
   the assigned cells. Conditioning on completion = survivorship bias.

2. **Two knobs moved at once (confound).** Versus the 152 baseline the re-run
   changed **both** `max_tokens` **and** `timeout_s`. Any delta is a *joint
   resource-envelope* effect and **cannot be attributed to the token budget
   alone**. Identifying the token-only effect would need a factorial or a
   token-only arm (same wall, different cap) — which this run does not have.

3. **Deterministic administrative censoring, not random dropout.** Every
   non-completion at t = 600 s is the *same* wall, so it is a competing terminal
   state, not ignorable missingness. Dropping those cells silently changes the
   estimand from *"what you get at this envelope"* to *"what the survivors score."*

**Rule:** we **never** report a completed-cell mean or an instruct-vs-thinking
delta computed on survivors as if it were the effect of budget.

---

## 2. The estimand, stated first

Every assigned cell `(model m, scenario s, rep r)` terminates in exactly one state:

```
outcome(m,s,r) ∈ { COMPLETED , DNF:timeout , DNF:error }
```

`COMPLETED` and `DNF:timeout` **compete**: a cell that hits the wall can never also
complete. The primary question is answered on **all 1400 assigned cells**, ITT:

- **PRIMARY (selection-free):** completion — *"did model m deliver a judgeable
  answer within the 600 s / 4096-token envelope?"* A binary per cell, so it is
  intention-to-treat **by construction** (no cell is dropped, nothing is imputed).
- **SECONDARY (conditional, bounded):** quality of the answer *given* completion —
  reported **only** with its completion rate and **selection bounds**, and labelled
  "conditional on completion," never "recovery" or "budget fixed it."

---

## 3. Primary analysis — completion as a competing-risks outcome

Aggregate reps → cell, cells → model, and treat the **lineage** as the inferential
unit (lesson 5: qwen3 quant/mode variants are one lineage, not independent draws).
At n = 14 models / fewer lineages this is **estimation with intervals, not NHST**.

**P1. Terminal-state rates by model and by mode.** For each model and each mode
∈ {instruct, thinking}: completion rate π̂ = COMPLETED / assigned, timeout rate,
error rate, each with a **Wilson score interval**. Report per-model and
lineage-pooled.

**P2. Cumulative incidence of completion (if per-cell latency is logged).** Using
time-to-completion over [0, 600] s with `DNF:timeout` as the competing event,
estimate the **cumulative incidence function** (Aalen–Johansen) of completion by
mode. This is the honest "competing-risks" figure: it shows *how far into the
envelope each mode actually delivers*, and that the thinking curve plateaus below 1
because the wall claims the rest. (If latency is not reliably logged, drop to the P1
multinomial only and say so.)

**P3. Completion contrast.** Difference in completion rate (instruct − thinking)
with a lineage-clustered / cluster-bootstrap CI. This is the run's real headline
and it is **immune to survivorship** because it counts the timeouts as the failures
they are.

---

## 4. Secondary analysis — conditional quality, with selection bounds

Only after P1–P3, and always beside them:

**S1. Conditional mean quality.** E[Q | COMPLETED, model] on the 1–4 ordinal scale,
per model + lineage, judged by the **same two-judge protocol**
(claude-opus-4.6 + gpt-5.4). Reported *with* π̂ from P1 so the reader always sees how
much of the assignment it conditions on.

**S2. ITT quality (ordinal, floor-scored).** Re-compute mean quality over **all
assigned cells** with `DNF:*` scored at the task-failure floor (Q = 1 — the operator
got nothing usable within the envelope). This is the ITT analogue of S1 and will
move opposite to S1 for the thinking lineages. Report both; the gap between S1 and
S2 *is* the size of the selection problem.

**S3. Selection bounds on the survivor delta (the anti-laundering step).** Bound
what the conditional instruct-vs-thinking quality delta *could* be once the
unobserved timed-out cells are accounted for:
- **Manski worst-/best-case bounds** (no assumptions): set the missing thinking
  scores to the min / max of the scale.
- **Lee bounds** (monotone-selection): trim the more-completing group to the
  completion rate of the less-completing group.
If the "thinking ≥ instruct on completed cells" claim **does not survive** the lower
bound (it will not, given 57–71 % missing), it is a survivorship artifact and is
reported as such.

**S4. Latency liability.** Median time-to-completion (completed cells) and the
fraction of assigned cells that hit the 600 s wall, per model/mode — the practical
"how long you wait, and how often you wait for nothing" cost.

---

## 5. Framing constraints (what the paper may and may not say)

- **Joint resource-envelope, not token effect.** Every claim is stated as *"at
  envelope E₂ = (4096 tok, 600 s) …"* — never *"raising the token budget caused …"*
  (blocker #2b). If the token-only effect is asserted, it must be flagged
  **unidentified** here.
- **Standalone (lesson 8).** No merge, no cell-for-cell diff, no promotion into the
  152 run. The re-run stands on its own regime.
- **No row-level tests, no logistic.** n = 14 models → EPV is hopeless (separation);
  the diabetes logistic/Welch/KW transfer is **UNSAFE** on this run (review transfer
  table). Descriptive estimation with clustered intervals only; if any test,
  Friedman / mixed-effects at model level.
- **`provisional` stays `provisional`** until a human promotes it; this plan changes
  no `claim_status`.

---

## 6. Deliverables to compute when the run finishes

A single script `deep-dive/reasoning_budget_reanalysis.py` (to be written against
the completed run) emitting one table + (optionally) one figure:

| Output | Method (§) | Purpose |
|---|---|---|
| Per-model / per-lineage completion, timeout, error rates + Wilson CI | P1 | primary, selection-free |
| Completion CIF by mode over [0,600] s (if latency logged) | P2 | competing-risks figure |
| Completion contrast instruct − thinking + clustered CI | P3 | the honest headline |
| Conditional E[Q\|completed] + π̂ | S1 | survivor quality, in context |
| ITT mean-Q (DNF = 1) | S2 | selection-robust quality |
| Manski + Lee bounds on the survivor delta | S3 | does the "recovery" survive? |
| Median latency + wall-hit fraction | S4 | practical liability |

Each row carries its own n (assigned, completed) so completeness is never implicit.

---

## 7. The honest claim this analysis is expected to support

> **Even at an 8× token budget with a 600 s wall, the verbose reasoning lineages
> fail to *complete* a large share of assigned cells (interim: qwen3-thinking
> ≈ 57–71 % timeout; instruct ≈ 0 %). The primary, selection-robust completion
> outcome therefore stays worse for thinking modes, and any apparent quality parity
> on *completed* cells (a) is conditional on survival and (b) does not survive its
> Manski/Lee lower bound. The re-run demonstrates a completion / latency liability of
> long-chain reasoning at CPU-bound envelopes — not a demonstrated quality-ceiling
> recovery.**

This **sharpens finding 17** (the thinking-mode penalty is not merely "fit to a
small budget"; a generous budget does not rescue completion) and it does so without
the survivorship trap the naïve reading would have fallen into.

---

*Pre-registered 2026-07-20 from the dual-family REVISE review
(`adversarial-methodology-review.md`). No `claim_status` changed. Run untouched.*
