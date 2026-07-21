# ApprenticeOps / CEOps — shareable brief

> **Status: provisional.** Numbers below are from a single controlled run and are
> under active methodology hardening (see §4). Do not quote as final. Not published.
> Canonical detail lives in the `docs/` files linked in §6.
> **Date:** 2026-07-21.

---

## 1. What it is (one paragraph)

ApprenticeOps ("CEOps") benchmarks **small, locally-sovereign language models as
homelab/SRE ops assistants** — offline (no external model API), **CPU-only**, and for
the current protocol **≤5B parameters**, i.e. the *last line* with no frontier to
escalate to and no human reviewer downstream. The thesis (positioning ADR,
[`docs/PAPER_POSITIONING.md`](docs/PAPER_POSITIONING.md)): the proxies a practitioner
reaches for — parameter count, benchmark score, a "reasoning" badge, perplexity —
**each mislead, on *different* axes**. So we profile **quality × safety × energy in one
reproducible harness on commodity offline hardware**, so model selection is made on
measured behaviour, not a proxy. That *integration* — not any single axis — is the
contribution. (Safety is a corroborating axis, not a novelty claim; the literature
already establishes reasoning/quant/small-model safety degradation.)

## 2. Method (what was actually run)

- **Roster:** 152 models × 20 ops scenarios × 5 reps = **15,200 rows**; run
  `full-chatok-core20-r5-ollama-20260705-150053`.
- **Scoring:** deterministic checks **plus** a 2-judge consensus (`claude-opus-4.6` +
  `gpt-5.4`), 30,400 judgements.
- **Regime (fixed on every row):** CPU, `no_turbo=1`, governor=performance,
  RAPL package-0 energy, `num_ctx=8192`, temp 0.7, fixed seeds. Energy is comparable
  across all 152 because the regime is constant.
- **Claim status:** `provisional` by design until a human promotes it.

## 3. Headline results (provisional)

- **Quality:** ~4B is the efficiency knee; bigger helps *on average*
  (Spearman(params, quality) ≈ 0.73), but the single best model is a **4B**
  (`qwen3:4b-instruct`) at a fraction of the energy — proxies mislead.
- **Safety:** safety and quality are ~collinear (r ≈ 0.97) for these small models, yet
  **~44% fail the destructive-action guard** (take/allow a destructive action); worst
  are reasoning-distills and tiny models. The real multi-objective tension is
  **capability vs energy/speed/size**, not safety vs quality.
- **Energy:** the reliably-tagged MoE models decode **faster than their footprint
  predicts**; energy/answer (Wh) is a first-class selection axis.
- **Judges:** highly *reliable* (quadratic κ ≈ 0.92, within-1 99.9%, verbosity-bias
  resistant) — but **reliability ≠ validity** (both raters are frontier LLMs; validity
  pending a human-eval substudy). See [`docs/JUDGE_VALIDATION.md`](docs/JUDGE_VALIDATION.md).
- **A concept blind-spot:** cumulative-vs-active restart triage is a **size-invariant**
  failure (small models 1.4/5, barely improving with size, while passing the mechanical
  checks) — a named ops misconception, not a capacity problem.

## 4. Rigor status — honest (read before quoting numbers)

The analysis passed a **dual-family adversarial review** (independent GPT-5.6 and
Claude Opus 4.8 judges); both returned **REVISE** — a credible, unusually honest
foundation that is *fixable*, not publication-final as framed. See
[`deep-dive/adversarial-methodology-review.md`](deep-dive/adversarial-methodology-review.md).

- **Landed:** join-integrity guard on the results↔judged merge; finding-7 downgraded to
  reliable-not-validated; a pre-registered competing-risks / ITT plan for the
  reasoning-budget re-run
  ([`deep-dive/reasoning-budget-reanalysis-plan.md`](deep-dive/reasoning-budget-reanalysis-plan.md)).
- **Pending (blockers):** informative-censoring (MNAR) re-analysis of the re-run;
  multiplicity control; the judge-validity human-eval substudy; the energy DRAM-domain
  bound; a model/lineage-level (not row-level) safety-composite screen.

**Implication for an internal submission:** cite the *method and integration* freely;
treat the *point numbers* as provisional until the pending blockers close.

## 5. Reproducibility & data

- Portable tracked snapshots (`data/snapshots/*.csv`) reproduce every 152-run number
  with no heavy download; the deep-dive suite (`deep-dive/full_*.py`) recomputes from
  them. Gates: `python3 scripts/*` test suite + `deep-dive/.venv` analysis.
- The full raw bundle (~433 MB, hash-bound) is archived in Azure Blob (private) for
  citation; see [`docs/ARCHIVAL_RELEASE.md`](docs/ARCHIVAL_RELEASE.md).

## 6. Canonical docs (share these for depth)

| Topic | File |
|---|---|
| Positioning / thesis ADR | [`docs/PAPER_POSITIONING.md`](docs/PAPER_POSITIONING.md) |
| Manuscript | [`docs/PAPER.md`](docs/PAPER.md), [`docs/PAPER-fullrun-section.draft.md`](docs/PAPER-fullrun-section.draft.md) |
| Findings register | [`deep-dive/FINDINGS.md`](deep-dive/FINDINGS.md) |
| Methodology review (REVISE) | [`deep-dive/adversarial-methodology-review.md`](deep-dive/adversarial-methodology-review.md) |
| Submission checklist | [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) |
| Reviewer notes | [`REVIEWER.md`](REVIEWER.md) |
| Judge validation | [`docs/JUDGE_VALIDATION.md`](docs/JUDGE_VALIDATION.md) |

## 7. For an internal / Microsoft-domain submission — suggestions

The academic CEOps paper and a Microsoft-internal paper are **two different
submissions**; keep them separate. CEOps' transferable *engine* is the reusable part:
a **CPU-only, energy-aware, dual-judge benchmark harness** for small/offline models on
a real operational task, with honest provisional claiming.

- **Reuse the engine, re-target the task.** The strongest internal angle mirrors CEOps'
  novelty (the *integration gap*): pick one Microsoft-domain ops/dev task (e.g. .NET
  framework-upgrade agents, mutation-test generation, or CVE triage/remediation) and
  measure **quality × cost/energy × safety** for small/on-device models where no prior
  work measures all three together for the *selection* decision.
- **Don't re-discover the safety axis.** Carve novelty against the 2026 scan already in
  [`docs/PAPER_POSITIONING.md`](docs/PAPER_POSITIONING.md) (GAP, Owner-Harm, AgentHarm,
  Beyond-the-Tip, Q-resafe, Self-Jailbreaking). Your novelty must be the *task +
  integration*, not "small models are unsafe."
- **Related-work search terms** to seed the internal lit review:
  - Modernization: *LLM code migration*, *automated framework upgrade*, *agentic code
    modernization benchmark*, *legacy .NET LLM refactoring*.
  - Testing: *LLM mutation testing*, *neural mutation score*, *LLM test generation
    benchmark*.
  - Security: *LLM vulnerability detection benchmark*, *agent CVE remediation*,
    *small-model security triage*.
  - Cross-cutting: *small language model agent benchmark*, *on-device / edge LLM
    evaluation*, *energy-aware LLM inference*, *LLM-as-judge reliability vs validity*.
- **Sequence:** close the pending rigor blockers (§4) *before* any submission quotes the
  152 numbers; until then, submit the *method* and *provisional* framing, not final
  point estimates. A starter for the Microsoft-domain subjects already exists outside
  this repo (`ceops-dotnet-paper-starter/paper-starter.md`).

---

*Provisional research brief. Nothing here is peer-reviewed or published; numbers are a
single-run snapshot under active hardening. Reproduce from `data/snapshots/` +
`deep-dive/`.*
