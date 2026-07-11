# Paper Phases and Submission Intent

Status: WIP workflow for ApprenticeOps paper production.

This document is the pre-submission control plane: what phase we are in, what
must be true to move forward, and what is still draft versus submission-ready.

## Why this exists

Strong papers are not written in one pass. They move through explicit gates:
intent -> design lock -> data lock -> analysis lock -> writing -> adversarial
review -> submission package. This prevents scope drift and over-claiming.

## Current state

- Phase: **Phase 4 (writing draft)** — correction lock renewed 2026-07-10. Every
  current headline value traces to canonical analysis schema `v1`; the old
  12-of-94 pooled-energy front is withdrawn.
- Manuscript status: DRAFT / WIP (not submitted). First full draft assembled in
  [`analysis/paper.qmd`](analysis/paper.qmd) (Quarto → HTML + Typst PDF), with
  [`analysis/references.bib`](analysis/references.bib).
- Phase-4 decisions (made autonomously; pending operator review):
  - **Format:** Quarto single-source — HTML + Typst PDF now (PDF needs **no**
    LaTeX; Typst is bundled), drop in a NeurIPS/arXiv LaTeX template at submission.
  - **Location:** [`analysis/paper.qmd`](analysis/paper.qmd) is the manuscript;
    **`PAPER.md` stays the design + pre-registration owner**.
  - **Outcomes reported against the plan:** the manuscript maps each pre-registered
    hypothesis (H1–H7) to its result with an explicit verdict and a transparent
    **deviation** log (`PAPER.md` §8c; the *Hypothesis outcomes* section of
    `docs/analysis/paper.qmd`) — confirmatory results kept separate from
    exploratory follow-ups.
  - **Scope:** 94-model quality/safety breadth plus controlled 24-model systems
    and three-axis evidence. Energy from the dynamic-frequency second batch is
    descriptive only.
- Experiment status: **frozen evidence correction-locked under analysis v1**.
  Exact populations are breadth 94 / quality-safety front 2 and controlled 24 /
  three-axis front 7.
- Parallel doctoral evidence track: the ≤5B-primary, 152-tag audit-inclusive run
  is still active and **has not passed Phase 2 (data lock)**. The 2026-07-10 SLM
  analysis amendment in [`STATISTICS.md`](STATISTICS.md) was written after partial
  inspection, so its added reliability/correlation analyses are exploratory for
  that run. They do not replace the locked 94-model manuscript results; no number
  enters the paper until the run completes, strict integrity checks pass, and a
  new analysis lock is recorded.
- Submission intent: arXiv preprint → **NeurIPS Datasets & Benchmarks** track.
- Current analysis/finding status: [`ANALYSIS.md`](ANALYSIS.md)
- Artifact and release inventory: [`ARTIFACT_INVENTORY.md`](ARTIFACT_INVENTORY.md)

## Intent Lock

**Paper type:** empirical benchmark and measurement artifact, not a new model,
training method, or autonomous-operations system.

**Core claim:** ApprenticeOps evaluates deployable small-model packages under a
locally-sovereign inference constraint. It reports quality and safety breadth,
then integrates energy only where CPU and RAPL conditions are comparable. The
safety result is corroboration of prior agent/SLM safety work, not a novelty
claim by itself.

**Non-claims:** no autonomous self-healing; no population-wide generalization
from one operator/node; no wall-power or data-center efficiency equivalence; no
causal architecture/training/quantization effect from the observational roster;
no paper evidence from external candidate or still-active doctoral runs.

**Audience and venue:** systems/ML practitioners and benchmark researchers;
arXiv preprint followed by a Datasets & Benchmarks venue, with MLSys/on-device
workshops as alternatives.

## Phase model

### Phase 0: Intent memo (must exist before full writing)

Goal: lock what this paper is and is not.

Required outputs:
- One-paragraph thesis and top-3 contributions
- Explicit non-claims (what is out of scope)
- Primary audience and target venue family
- Acceptance bar for "ready to submit"

Exit gate:
- No unresolved disagreement on core claim or scope

### Phase 1: Design lock (pre-registration discipline)

Goal: freeze the scientific plan before looking at full results.

Required outputs:
- Frozen research questions and falsifiable hypotheses
- Scenario taxonomy and scoring plan
- Statistical analysis plan and significance method
- Threats-to-validity plan

Exit gate:
- Major methodological choices are no longer changing per model result

### Phase 2: Data lock

Goal: collect the planned runs with provenance and integrity.

Required outputs:
- Full run logs and telemetry with stable schema
- Pinned model identifiers/digests
- Run manifest and environment record
- Missing/failed runs triaged with explicit DNF policy

Exit gate:
- Data completeness and quality checks pass

### Phase 3: Analysis lock

Goal: freeze figures/tables and claim-bearing numbers.

Required outputs:
- Final figures/tables with script-generated provenance
- Confidence intervals and statistical tests
- Sensitivity analysis notes
- Error analysis and representative failures

Exit gate:
- Every claim in abstract/introduction traces to a frozen result artifact

### Phase 4: Writing draft

Goal: produce full manuscript text from locked analysis.

Required outputs:
- Full draft with abstract, intro, method, results, limitations, related work
- Reproducibility appendix pointers
- Ethical/broader-impact and release-risk text

Exit gate:
- Internal read finds no missing section needed by target venues

### Phase 5: Adversarial internal review

Goal: red-team the paper before external review.

Required outputs:
- Over-claim audit (claim vs evidence line-by-line)
- Reproducibility audit (fresh-machine replay attempt)
- Statistics sanity audit
- Security/privacy release audit (scenario scrubbing, egress disclosures)

Exit gate:
- All high-severity findings resolved or explicitly accepted with rationale

### Phase 6: Submission package

Goal: produce venue-ready, policy-compliant package.

Required outputs:
- Submission PDF and anonymous supplement (if required)
- Checklist completion (claims, limitations, reproducibility, compute, ethics)
- Code/data artifact bundle or justified access path
- Citation, license, and attribution sweep

Exit gate:
- Dry-run checklist complete; no blocker remains

### Phase 7: Camera-ready and archival release

Goal: release durable, reusable artifacts after acceptance/preprint decision.

Required outputs:
- Final manuscript with stable links
- Archived artifact location (long-lived, citable)
- Reproduction instructions validated by another operator
- Changelog from submitted to camera-ready version

Exit gate:
- Public package can be independently rerun

## Pre-submit checklist (quick)

- Claims in abstract/introduction are strictly supported by reported results
- Standalone limitations/threats section is explicit and honest
- Error bars/CIs and significance methods are reported for main claims
- Compute and runtime budget are disclosed
- Repro steps are executable from clean checkout
- Artifact package is complete and documented
- Licenses/provenance are explicit for models, code, and data
- Dual-use/privacy risks and mitigations are documented

## Open Gates

| Gate | Status | Required evidence |
|---|---|---|
| Analysis v1 regeneration | **passing** | `audit-paper-data.py`, `audit-paper-claims.py`, and `build-analysis-site.sh --verify` pass. |
| Manuscript HTML/PDF | **passing** | Quarto HTML site and Typst PDF render from current source. |
| Judge-human agreement | **packet ready / human scoring open** | Score all 50 rows in `data/human_eval/paper-94-model-corrected-v1/` without opening its key, then run `human_eval.py score-packet`. The external-v1 packet validates a separate dev lane and cannot close this paper gate. |
| Optional third judge | **blocked on model access** | `gemini-3.1-pro` is not available to the current Copilot account as of 2026-07-11. Do not alter the locked two-judge policy or substitute a model silently. |
| Independent reproduction | **clean-checkout automation passing / human sign-off open** | A fresh detached checkout with a fresh exact-pinned environment reproduces all notebooks, exports, figures, HTML/PDF, Croissant records, and the release package without tracked mutation. A second human operator should still record independent sign-off. |
| Dataset archival metadata | **metadata ready / publication open** | Croissant 1.0 validates with the official parser; deterministic package tooling passes; Zenodo is selected for the dataset DOI. Reserve/publish only after final operator approval. |
| Submission formatting | **checklist ready / template open** | `SUBMISSION_CHECKLIST.md` captures current evidence and policy gates. Re-check the live author kit and apply its template without changing claims. |
| Citation/license/privacy sweep | **automated gates passing / final human sweep open** | Mixed model-output rights, citation fields, release path, Croissant hashes, and privacy are machine-audited; perform the final attribution and venue-policy read before release. |
| Active <=5B run | **separate / blocked from paper** | Complete strict run audit and a new analysis lock before any value enters claim-bearing prose. |
| External candidate/dev runs | **separate / blocked from paper** | Remain future scenario-pack evidence unless independently promoted under a new lock. |

## Change control

- If a core RQ/hypothesis changes after Phase 1, mark it as protocol amendment
  in commit message and in this file.
- If a headline result changes after Phase 3, rerun the claim-vs-evidence audit.
- Keep this file updated as the single source of paper readiness state.
