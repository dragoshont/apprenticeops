# Dual-family adversarial methodology review — CEOps analysis + diabetes-methodology transfer

**Date:** 2026-07-20 · **Status:** provisional (advisory; no claims changed by this doc)
**Reviewers (independent, different model families):**
- **GPT-5.6 Sol** (GPT-family) → verdict **REVISE**
- **Claude Opus 4.8** (Claude-family) → verdict **REVISE**

Both families reviewed, independently and read-only: (1) the CEOps/ApprenticeOps
analytical approach (`FINDINGS.md`, `full_*.py`, `AGENTS.md` lessons) and (2) the
proposed transfer of the MSc Numerical-Analysis (Pima diabetes) statistical
methodology into the CEOps paper. **They converged on `REVISE`** — a credible,
unusually honest foundation that is not yet publication-defensible as framed, and
is fixable.

---

## Consensus blockers (both families — fix first)

1. **κ ≠ validity, and finding 7 contradicts `AGENTS.md` lesson 6.** "The judge is
   trustworthy" (κ=0.853) is inter-rater *reliability*, not *validity*. Both judges
   are frontier LLMs (one *is* a Claude) → errors correlated by construction; high
   agreement is shared-bias agreement. **Fix:** run the human-eval packet, or
   downgrade finding 7 to "reliable, validity pending."

2. **The reasoning-budget re-run trades symmetric censoring for a worse,
   outcome-correlated one.** The old fixed token cap censored *all* models equally;
   the new 600 s `DNF:timeout` preferentially fires on the long-chain thinking models
   the study wants to vindicate → an instruct-vs-thinking comparison on *completed*
   cells is **survivorship-biased toward the hypothesis** (MNAR / informative
   censoring). **Fix:** competing-risks / intention-to-treat (see
   `reasoning-budget-reanalysis-plan.md`); never report a completed-cell delta.

3. **Port the diabetes tests ONLY at model level — never on the 15,200 rows.** The
   diabetes methods assume ~768 IID rows; CEOps is model×scenario×rep repeated
   measures. Row-level χ²/Welch/KW/logistic = **pseudo-replication**. Aggregate to one
   value per model (n=152) first; the effective inferential n is closer to independent
   *lineages* than 152 tags.

4. **The logistic safety-screen is not valid as framed.** Single-scenario outcome
   (`guard-08`, which the paper itself calls "too thin"), pseudo-replicated reps,
   in-sample AUC optimism, HL non-rejection ≠ calibration, EPV borderline at 152 and
   hopeless at n=14 (separation). **Fix:** multi-scenario safety composite →
   model/lineage-level mixed logistic → nested/grouped CV optimism correction →
   calibration curve (not HL).

5. **Multiplicity is disclosed but uncontrolled** — dozens of tests, not "~8."
   **Fix:** pre-register one primary claim (tools effect), Benjamini–Hochberg the
   secondary family, label the rest exploratory.

6. **Do NOT relabel finding-25 (drop-truncated) as "complete-case-vs-imputed"**
   (both rate **UNSAFE**). Truncation is MNAR (correlates with model type *and* the
   outcome); nothing is imputed (whole models are dropped). Relabeling would launder
   the doc's own honest "selection bias to disclose." Keep the MNAR framing.

---

## Family-distinctive catches (why running both paid off)

**GPT-5.6 Sol (causal-identification + engineering lens):**
- The re-run changed **two knobs at once** (`max_tokens` *and* `timeout_s`) → the
  effect **cannot be attributed to token budget**; it is a joint resource-envelope
  intervention. Needs a factorial or token-only arm to identify.
- The effective inferential sample ≈ independent **lineages** and scenarios, not
  15,200 rows or even 152 tags (quant/mode variants + reps + judges add precision or
  measurement layers, not independent subjects).
- **Add executable join-integrity assertions** (exactly 2 distinct judges/cell, unique
  keys, 1-to-1 cardinality, zero unmatched) — the CEOps analogue of the reflection's
  clean-running-but-wrong `left_join()`.

**Claude Opus 4.8 (internal-consistency + construct + reader lens):**
- **Energy internal inconsistency (novel):** RAPL package-0 **excludes DRAM**, but
  finding 11 says decode is **memory-bandwidth-bound** — so a size-correlated share of
  the *true* energy is exactly the uncounted DRAM traffic, and the energy~size + MoE
  efficiency claims are computed on the component the mechanism says isn't where the
  action is. Not just scope — an internal contradiction. **Fix:** measure/bound the
  DRAM domain and show the residuals survive, or stop ranking efficiency on it.
- **Rhetorical laundering:** importing clinical vocabulary (Hosmer–Lemeshow,
  sensitivity/specificity) onto a thin single-item in-sample benchmark makes a weak
  result *read* as validated — the reader-misinterpretation risk, and the reflection's
  own "conclusion-inversion" failure mode.

---

## Consolidated transfer verdict (both tables merged)

| Diabetes method → CEOps | Verdict | Condition |
|---|---|---|
| Logistic safety-screen + ROC/AUC + threshold | **Conditions (n=152) / UNSAFE (n=14)** | model/lineage level; multi-scenario safety composite; nested-CV optimism correction; calibration curve not HL |
| χ² + Cramér's V | **Conditions** | model-level counts only; Fisher's exact for nominal `org` (n=2 cells); do not merge makers to manufacture a p |
| Levene → Welch ANOVA + Kruskal–Wallis | **Conditions / UNSAFE at row level** | model-level means only; for scenario-blocked use **Friedman / mixed-effects (already in the suite)** |
| 1.5×IQR outliers | **Conditions** | continuous metrics on their analysis scale (log energy); never on the 1–4 ordinal quality/safety; pre-register, don't let it invert a conclusion |
| Finding-25 as complete-case/imputed | **UNSAFE — reject** | keep the MNAR "selection bias" framing |

---

## Prioritized fix-list (for the paper)

1. Analyze the finishing re-run as **competing-risks / ITT** (not completed-cell) —
   time-critical; changes finding 17's wording. See `reasoning-budget-reanalysis-plan.md`.
2. Make the **crossed mixed-effects model the primary estimator**; aggregate-to-model
   for any ported test.
3. **Energy:** measure/bound DRAM, or restrict to "core-package, DRAM-uncounted" and
   stop ranking MoE efficiency on it.
4. **Judge validity:** human-eval substudy or downgrade finding 7.
5. Transfer the diabetes methods **at model level under the conditions above**; the
   multi-scenario, optimism-corrected safety-composite screen is the highest-value add.
6. Add **join-integrity assertions** to `full_data.py::load_full` (2-judges/cell,
   uniqueness, cardinality, zero unmatched).
7. **Multiplicity:** pre-register primary hypothesis + FDR on the secondary family.

---

## Why REVISE, not FAIL (both families credited this)

The corpus is **unusually honest** — corrections logged in place (findings 9, 17, 20,
23), lineage-level pairing enforced against pseudo-replication (lesson 5),
model-clustered SEs used, everything labelled `provisional`. **No fabrication; most
limitations self-disclosed.** That is precisely why it is revisable into a strong
paper rather than rejected.

---

*Provenance: two independent Adversarial-Judge subagents (GPT-5.6 Sol, Claude Opus
4.8), read-only, 2026-07-20. Full verdicts are reproducible by re-dispatching the
same packet. This doc is advisory and changes no claim or `claim_status`.*
