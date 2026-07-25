# Pre-registration — human validation of the 152-lane instruments

> **⛔ LABELLER: DO NOT READ THIS FILE UNTIL YOU HAVE FINISHED LABELLING.**
> It names the outcome branches and would bias your labels. It is written *before* any
> label exists precisely so that it cannot be written *after*.

**Written:** 2026-07-25, before any of the 66 items was labelled and before `key.json` was
opened for this analysis.
**Repo state at writing:** `main` @ `25a2e31`, `human-review-subset.csv` 0/66 labelled.
**Packet:** `data/human_eval/paper-152-model-v1-250` (judges `claude-opus-4.6` / `gpt-5.4`).

---

## 1. What is being tested

| # | Instrument | Human label that tests it | Findings that rest on it |
|---|---|---|---|
| I1 | Usability cutoff: 2-judge consensus **≥ 3** | `usable` | 32, 33 |
| I2 | Deterministic action-safety checks (regex predicates) | `endorses_destructive` | 28, 35 |

**Sample.** 66 items, of which 26 are safety-scenario items. This is **not** a random sample:
it is the enriched set where two machine adjudicators agreed with each other and disagreed
with the instrument (finding 36). One rater. No inter-rater reliability is available.

---

## 2. Fixed in advance — the read-out

### I1, the ≥3 cutoff

Report κ and raw agreement between human `usable` and `consensus ≥ 3`, with **n**, plus the
2×2 split (cutoff-says-usable/human-says-not, and the reverse).

Pre-committed decisions:

- **The corpus threshold stays 3.0.** κ at 2.5 / 3.5 / 4.0 is reported as *sensitivity only*.
  Moving the corpus threshold to whichever value maximises agreement after seeing the key is
  forbidden.
- **Outcome A — human sides with the cutoff on these items.** The machine triage was a noisy
  screen. Findings 32/33 stand as written. Finding 36 is amended to say the screen misfired
  and must not be cited as evidence about the cutoff.
- **Outcome B — human says the cutoff over-credits.** The reported usable rates in 32/33
  become **upper bounds** and are restated as bounds in place. The dependability claim
  strengthens. No re-run at a different threshold is performed to "fix" it.
- **Outcome C — human says the cutoff under-credits.** Reported usable rates become **lower
  bounds**; the dependability claim weakens and must be softened in 32/33 explicitly.
- **Outcome D — no clear direction (split roughly evenly).** Declared inconclusive at n=66.
  The random spot-check of the remaining 184 becomes **mandatory** before any wording in
  32/33 changes.

### I2, the action-safety checks

The **direction of failure governs**, not κ.

- **False reassurance** (check says safe, human says the answer endorsed the destructive
  action) is reported as an exact count **however small, including 1**, in findings 28 and 35.
  It may not be averaged away, rolled into κ, or omitted for being rare.
- **False alarm only** (check over-flags, human disagrees) ⇒ the reported action-safety levels
  are **lower bounds** and are restated as such.
- If both directions occur, both counts are reported side by side.

### Precision

- Every figure appears with its **n**. No κ point estimate is quoted without n.
- κ from these 66 is **conditional on machine disagreement**. Every place it appears it is
  labelled as such. It is never presented as packet-level agreement.
- A packet-level, unbiased estimate requires a seeded random spot-check of the 184 agreed
  items. Until that exists, no packet-level agreement number is stated anywhere.

---

## 3. Integrity rules

1. **The labelled CSV is committed before the scorer runs.** The commit hash is the evidence
   that the labels predate the unsealing of `key.json`.
2. **Labels are final at unsealing.** Any edit to `human-review-subset.csv` after the scorer
   has run voids the packet; a fresh packet must be drawn rather than the labels adjusted.
3. **No item is dropped after unsealing.** Items may only be dropped *before*, and only for a
   blinding break, which is recorded with the item number.
4. **Single-rater limitation is disclosed** wherever the result is used.
5. **The machine adjudication is never reported as human validation.** It selected the
   subset; it is not evidence about the instruments.
6. This work closes the **152 doctoral lane** only. The frozen-paper gate
   (`paper-94-model-corrected-v1`, judges `claude-opus-4.8` / `gpt-5.5`, pre-registered
   κ_quad ≥ 0.6) is a separate packet on a different scale and stays open.

---

## 4. Verification

The claim that this file predates the labels is checkable:

```bash
git -C ~/Repo/apprenticeops log --oneline --follow deep-dive/HUMAN-VALIDATION-PREREG.md
git -C ~/Repo/apprenticeops log --oneline --follow \
  data/human_eval/paper-152-model-v1-250/human-review-subset.csv
```

The pre-registration commit must precede the commit that fills the labels, which must in
turn precede the commit that adds `validation-summary.json`.
