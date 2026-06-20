# Paper Phases and Submission Intent

Status: WIP workflow for ApprenticeOps paper production.

This document is the pre-submission control plane: what phase we are in, what
must be true to move forward, and what is still draft versus submission-ready.

## Why this exists

Strong papers are not written in one pass. They move through explicit gates:
intent -> design lock -> data lock -> analysis lock -> writing -> adversarial
review -> submission package. This prevents scope drift and over-claiming.

## Current state

- Phase: **Phase 4 (writing draft)** — entered 2026-06-20 after the analysis lock
  (the 5-rep × 2-judge variance pass is integrated; every headline number now
  traces to a frozen, published artifact).
- Manuscript status: DRAFT / WIP (not submitted). First full draft assembled in
  [`../paper/paper.qmd`](../paper/paper.qmd) (Quarto → HTML + Typst PDF), with
  [`../paper/references.bib`](../paper/references.bib).
- Phase-4 decisions (made autonomously; pending operator review):
  - **Format:** Quarto single-source — HTML + Typst PDF now (PDF needs **no**
    LaTeX; Typst is bundled), drop in a NeurIPS/arXiv LaTeX template at submission.
  - **Location:** a new `paper/` manuscript; **`PAPER.md` stays the design +
    analysis plan (pre-registration)** that the manuscript cites — not overwritten.
  - **Scope:** drafted on **locked Wave-1**; Wave-2, the judge↔human κ, and a 3rd
    judge fold in as they land (camera-ready enrichments, not draft blockers).
- Experiment status: Wave-1 locked; Wave-2 additive sweep in progress.
- Submission intent: arXiv preprint → **NeurIPS Datasets & Benchmarks** track.
- Intent memo: [`PAPER_INTENT.md`](./PAPER_INTENT.md)

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

## Change control

- If a core RQ/hypothesis changes after Phase 1, mark it as protocol amendment
  in commit message and in this file.
- If a headline result changes after Phase 3, rerun the claim-vs-evidence audit.
- Keep this file updated as the single source of paper readiness state.
