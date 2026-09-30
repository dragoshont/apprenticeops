# Completing the 152-deployment analysis

**Date:** 2026-09-08. **Status:** reviewed proposed work programme, not an analysis lock.

> **Scope honesty.** We can finish the analysis of the existing single-node
> study without collecting another 152-model sweep. We cannot turn machine
> consensus into human validation, or treat the proposed work below as completed.
> The corpus remains provisional. No experiment launch, claim promotion, or
> public-site publication is authorized by this document.

## 1. Outcome and boundaries

The target is one reproducible **artifact and measurement-validity case study**:
152 deployment tags, 20 repository-grounded scenarios, five repetitions, and
two fixed judge families. The primary doctoral population is at most 5B
parameters; larger deployments remain a separately labelled comparison.

The governing sources are the [statistics plan](../STATISTICS.md), the
[positioning decision](../PAPER_POSITIONING.md), and the
[152-run manifest](../../data/analysis-manifest.full-chatok-core20-r5-ollama-20260705-150053.json).
The existing 94-model paper, the 14-model raised-budget mechanism study, and
the R1 extension are separate evidence sets. No row-splicing or inherited
94-model pre-registration is permitted.

Two milestones are deliberately different:

1. **Analysis closure:** audited computations, reproducible outputs, explicit
   instrument limitations, and a disposition for every proposed claim.
2. **Submission/publication readiness:** human validation, independent review,
   the additional evidence required by the selected submission scope, and
   explicit human approval of the new claim lock.

The [positioning decision](../PAPER_POSITIONING.md#blocking-before-submission)
currently requires a second hardware point before submission. It does not
prevent analysing the existing node. Omitting that experiment would require a
human-approved scope amendment and renewed review, not silent removal of a gate.

### Recommended sequence, not an implementation authorization

| Option | Work/cost | Scientific reach | Risk | Recommendation |
|---|---|---|---|---|
| A: computation audit and closure first | Lowest new-data cost; P1/P2 plus P3 design | Finishes the fixed-corpus analysis; instruments may remain unvalidated | Cannot be sold as submission-ready | **Start here once approved.** Human recruitment can proceed in parallel. |
| B: retain the existing submission scope | Adds independent human ratings and a second-node panel | Tests instruments and bounded platform sensitivity | Rater/hardware availability; panel may still be inconclusive | Continue after A if resources are available. |
| C: narrower single-node release | Avoids second-node collection; does not remove the human-validity issue | Explicitly limited case study | Requires a human-approved positioning amendment and fresh review | Fallback if B is not feasible, not an automatic gate waiver. |

This is a qualitative planning comparison, not a prediction of venue acceptance.
The minimal-change ladder is: skip a new sweep; reuse locked evidence and
existing analysis helpers; repair demonstrated defects with focused tests;
avoid new frameworks, training pipelines, or runtime migrations.

## 2. What is already available

| Item | Verified state on this checkout |
|---|---|
| Inference and judging | 15,200 cells; 30,400 canonical judgments. Existing join-integrity test passes on the real 152 x 20 x 5 grid. |
| Durable evidence | Locked raw bundle available locally; tracked compact and canonical-schema snapshots exist. Claim status remains `provisional`. |
| Analysis infrastructure | On 2026-09-08, direct existing-script runs passed: lane 8 tests, summary 13, condition verifier 18; join-integrity positives and five corruption cases also passed. These are infrastructure checks, not a scientific all-clear. |
| Analysis outputs | A/B reruns, sensitivity analyses, metric/identity corrections, and a separately analysed raised-budget study are recorded. These are candidate outputs, not a final clean-room analysis pass. |
| Human review | The 66-item human slot is blank. Earlier reconciled labels are explicitly machine-panel evidence. |
| Public integration | The public claim holder is still the locked 94-model lane; notebook migration is incomplete. |

The last recorded repair pass reports 137 primary tags and approximately 100
weight-sets across all 152 tags. Neither count should be copied without
reconciling the frozen inclusion rule and the final identity map.

## 3. Proposed phase ledger

P0 is complete. The user approved nonhuman implementation on 2026-09-09.
P1 has a recorded population/identity contract with unresolved provenance
explicitly excluded from inference. **P2 is complete for the retained
machine-calculation scope**: repairs, selection stability, completion-proxy and
energy-metric sensitivities have passed deterministic checks, independent replay,
and final GPT/Claude review. Effects of unmeasured screened-out models are
explicitly not identifiable. No implementation phase is active. P3-P6 remain
not-started; the local operator pilot does not constitute independent human
validation, and computational review does not promote provisional claims.

| Phase | State | Scope and deliverable | Explicitly out of scope | Exit gate |
|---|---|---|---|---|
| P0: closure plan and research delta | complete | Reconciled current evidence, identified methodological gaps, checked recent primary and practitioner sources. | Changing paper claims or rerunning inference. | Source-backed plan and reviewed research report; gaps disclosed. |
| P1: freeze the analysis contract | complete for retained descriptive analyses | Manifest-bound population and source reconciliation; 137 eligible deployments, unknown lineage held, lock-tier discrepancies preserved; metric and failure definitions recorded. | New models, unverifiable lineage effects, or retrospective pre-registration. | Counts/joins/hashes verified; excluded inferential uses explicitly listed in the repair report. |
| P2: recompute and reconcile | complete for retained machine calculations | Core repairs; rank/top-k/Pareto stability; integer-tier descriptions; completion-proxy and energy-cost sensitivity; unmeasured exclusions dispositioned. | Human usability/safety validity, unverified lineage inference, or universal selection claims. | 61 scientific fixtures, source/output hashes and byte-identical replay PASS; independent GPT and Claude final PASS. |
| P3: human instrument validation | not-started; design after P1, can overlap P2 | Approved blinded sampling protocol, qualified raters, immutable labels, read-out with uncertainty. | Machine-filled human labels or tuning the cutoff on validation labels. | Scope-appropriate validation or an explicit restriction/withdrawal of unsupported claims. |
| P4: hardware sensitivity | not-started; separately approved | Bounded second-node study if retaining the existing submission scope. | Replacing the primary run or pretending a runtime change isolates hardware. | Predeclared within-study contrasts and independently checked artifacts, or reviewed scope amendment. |
| P5: independent review and claim lock | not-started; after P2/P3 and scope-required P4 | Fresh GPT-family and Claude-family reviews; resolve contradictions; human paper-final decision. | Automatic promotion from `provisional`. | Both reviews PASS for retained claims and explicit human lock approval. |
| P6: publication integration | not-started; after P5 | Complete notebook/schema/figure/site migration and clean-checkout reproduction. | Publishing provisional 152 outputs. | Claim, privacy, link, notebook, portal, and reproduction gates pass before one authorized publication. |

Current computation receipts and remaining limitations:
[core repair results](152-analysis-repair-results.md),
[selection stability](152-selection-stability-results.md), and
[final sensitivity closure](152-selection-sensitivity-results.md).
The review portal has been implemented separately with full text and durable
pilot labels. Neither its completion nor its instruction-only portal page
authorizes publication of provisional research findings.

## 4. P1/P2: work that needs no new human labels or inference

### 4.1 Identity and population

- Reconcile run-reported integer `param_count`, the model lock's inclusion flag,
  and parameter tiers. Publish a row-level inclusion/exclusion table.
- Define eligibility from the frozen, reconciled model-lock inclusion rule
  intersected with the run roster, never from a downstream safety-complete-case
  table. The current repair script derives `le5_models` from such a table.
  Assert equality to the intended eligible roster and report any differences;
  this code path is a risk, not proof that models were actually lost.
- Separate **deployment tag**, **artifact digest**, and **underlying weight
  lineage**. Different quantizations have different digests but are not
  independent training replicates. Name-stem matching is a heuristic, not a
  verified identity contract.
- Audit the candidate-roster screen and disclose models excluded despite serving.
  Freeze training type, thinking capability, and actual reasoning mode as
  distinct fields. The old deep-dive and new summary do not yet share one
  definition of a reasoning arm.
- Keep unknown metadata unknown; document complete-case populations separately
  from the 152-tag deployment population.

### 4.2 Measurement definitions

- Separate judged quality, content recall, action-safety checks, completion, and
  usability. Do not relabel the composite deterministic score as safety.
- Include all relevant action-check types; a scenario with no applicable check
  is not evidence of a safe answer. Separate empty output, substantive partial
  output, token cap, timeout, and stream-finalization failure.
- Report both assigned-cell outcomes and explicitly conditional outcomes. Missing
  judgments are evaluation missingness, not automatic model failures.
- Define observed per-attempt success separately from "mean judge score exceeds
  a threshold." The existing mean-good versus all-five-good comparison is not
  interchangeable with `pass_1` versus `pass^5`.
- Energy per usable answer is total in-scope measured energy divided by usable
  answers. Zero-success deployments are unbounded/undefined, not silently
  removed from selection tables. Report which records have missing energy.
  Energy remains RAPL CPU-package energy, not wall power or DRAM-inclusive energy.
- The threshold of 3.0 remains the recorded primary analysis threshold unless
  a separately versioned future study changes it. Sensitivities are not a
  procedure for choosing the most favourable cutoff.

### 4.3 Statistical and executable checks

- Re-run ranking, efficiency, scaling, task capability, judge agreement,
  variance, and retained IRT/clustering/association analyses on the final table.
  Each optional analysis must either pass its stated gate or be explicitly
  excluded from paper claims; a script printing output is not sufficient.
- Audit resampling multiplicity: duplicated sampled scenarios must remain
  separate bootstrap draws even when a statistic regroups by model/scenario.
  The [current clustered helper](../../deep-dive/phase4_repairs.py) concatenates
  sampled scenarios while some statistics regroup on the original scenario ID.
  Test this interaction before accepting its published intervals.
- The [B3 output](../../deep-dive/out/full_ab/b3_mixedeffects.txt) reports 9,000
  fitted rows, labels 152 clusters, and records an `IndexError` in the mixed-model
  cross-check. Reconcile the actual fitting population and model specification;
  do not treat that output as a completed validation gate.
- Verify that the [A/B driver](../../deep-dive/full_ab.py) cannot count a caught
  exception as successful completion. Add the smallest regression tests for
  repaired behaviour when implementation begins.
- Match uncertainty to the estimand: scenario clusters for a fixed roster's
  task sensitivity; paired lineage comparisons for quantization; appropriately
  crossed model/scenario uncertainty for broader claims. Twenty curated
  scenarios do not become a random population of all SRE incidents.
- Report effect sizes and intervals, predeclared analysis families, multiplicity
  adjustments, per-judge sensitivity, and Pareto inclusion stability. No causal
  training/architecture claim from this observational roster.
- Generate a claim table: **retain / correct / withdraw / exploratory / not
  identifiable**, each linked to data hash, script revision, population, metric
  definition, and verification output.
- The energy-per-usable-answer and reliability-gap claims specifically remain
  **instrument-defined, unvalidated** unless P3 supports their interpretation.
  Recomputing a number does not validate its threshold.

## 5. P3: what human validation actually requires

**Do not simply ask the operator to fill the old 66 rows and declare victory.**
The [provenance record](../../data/human_eval/paper-152-model-v1-250/AI-REVIEW-PROVENANCE.md)
states that the operator reviewed machine labels and later parked human
labelling. Blinding cannot be recovered by clearing the CSV.

The existing subset is useful for **diagnostic error analysis**, not a
representative estimate of instrument accuracy. Even the original 250 items
were deliberately enriched for difficult cases. Neither raw agreement nor
error direction on that subset establishes corpus-wide bounds.

There is also an instrument mismatch to repair in a **new versioned packet**:
the [packet generator](../../deep-dive/human_validation_packet.py) displays only
1,800 context characters and 2,500 answer characters. A human evaluating that
prefix may miss a later correction or harmful recommendation. Validate against
the actual text/context seen by the instrument under test, with differences
recorded, rather than introducing a new display cap.

Proposed design, subject to review before labels are collected:

1. Preserve the old packet, preregistration, and machine labels unchanged.
   Record an amendment before collecting new labels; acknowledge that the
   original corpus has already been explored.
2. Recruit one independent ops-competent primary rater not exposed to the
   machine labels; preferably two raters. The operator can contribute domain
   adjudication but should not be described as an unexposed blind rater.
3. Use a fresh probability sample from the final primary population, plus a
   separately reported safety/error-enriched diagnostic sample. Freeze the
   sampling frame, selection probabilities, seed, precision target, and
   stopping rule. Do not convert machine disagreement sampling into
   representative human validation.
   The primary target is instrument agreement/error rates on the **fixed
   eligible answer-cell corpus**, with `(deployment, scenario, repetition)` as
   the sampling unit. Use design-based estimates and uncertainty matched to
   the actual probability-sampling design, including any finite-population
   correction and unequal weights. Broader task/model claims require a
   separate crossed-cluster analysis; shared scenarios, lineages and judges
   are not independent replications.
4. Budget provisionally for **200-300 full-answer primary ratings**, with an
   independently double-scored subset (initial planning range **50-100**),
   selected by a known sampling design. Calibrate the actual count and effort
   from a small excluded practice packet; these ranges are planning estimates,
   not a powered design or a promise of safety precision.
   This means **250-400 rating decisions** before extra diagnostic items,
   practice, or adjudication. Independent overlap requires two eligible raters.
   With only one, explicitly omit inter-rater reliability claims and retain the
   single-rater validity limitation; do not silently drop the second rating.
5. Report per-stratum uncertainty and sampling-weighted summaries where
   appropriate, false reassurance and false alarms separately, inter-rater
   disagreement before adjudication, and the treatment of unresolved labels.
   Rare-harm claims require their own precision assessment; zero observed
   failures does not establish zero risk.
6. Freeze labels with provenance before unsealing/scoring. Do not adjust labels
   or the primary threshold to improve agreement. A poorly validated
   instrument leads to narrower wording or withdrawal, not an automatic
   "upper/lower bound" on the whole corpus.

If no human time or budget is available, we can still complete a reproducible
**LLM-judged benchmark with unvalidated usability/safety instruments**. That is a
restricted analysis milestone, not closure of the current submission gate or
permission to claim operational safety.

## 6. P4: bounded additional experiment, not another sweep

For the existing submission scope, propose a separately locked panel on a
second CPU: roughly **6-8 deployments x 20 scenarios x 5 repetitions** as an
initial feasibility budget. Select by prespecified size, quantization and
completion strata, not whichever models make the best headline. Include weak
and unreliable deployments as well as strong ones.

Hold weights/digests, runtime version, prompt/template, sampler, budgets, and
judge policy fixed wherever technically possible. Otherwise label the result
**platform-stack sensitivity**, not a hardware-only effect. Record the new
machine profile and energy domain; do not compare unlike energy scopes as if
they were the same measurement.

Lock the panel and contrasts before seeing its outcomes. Use a short preflight
pilot to estimate wall time, disk, judge credits, and attainable precision
before approval of a full panel. The proposed panel is not automatically
sufficient for cross-hardware generalization.

New models, LoRA/SFT, distillation, memory, retrieval, inference strategies, or
llama.cpp migration can follow as separately locked studies. They are not
dependencies for closing the original analysis.

## 7. Research needed, and a stopping rule

The current delta scan is limited to **2026-07-06 through 2026-09-08**, overlapping
the prior complete scan by seven days. Older methods can be newly relevant
without being new releases. Primary source verification, immutable revisions,
negative searches, and access limitations belong in the radar ledger.

Priority order:

1. Human/LLM evaluation validity, enriched-sample bias, rater reliability, and
   justified uncertainty for repeated/crossed benchmark data.
2. Non-completion and budget censoring; energy per successful task and the
   limits of per-token or per-attempt efficiency comparisons.
3. CPU deployment identity: templates, parsers, quantization, reasoning mode,
   runtime and memory effects, with actual CPU evidence separated from GPU claims.
4. Operations benchmark realism and diagnosis-versus-executed-recovery scope.
5. PEFT, specialization, distillation and new small releases as **follow-on
   opportunities**, not reasons to keep replacing the frozen roster.

The [completed bounded delta](../analysis/research-radar/2026-09-08.md) records
112 queries/reads, 22 candidate source versions, explicit negative searches and
access failures. The [ten-source shortlist](../analysis/research-radar/2026-09-08-shortlist.md)
is the working reading set: human-evaluation design, human-corrected evaluation,
omission blindness, resampling/reliability definitions, censoring, deployment
identity, energy boundaries and updated ops-benchmark context. Five are older
methods, explicitly not new 2026 releases. No source was promoted into canon.

This is enough literature grounding to begin the proposed computation audit
after approval. Further research should resolve a named methodological or
counter-evidence question, not extend the roster indefinitely.

Social/practitioner material is a lead for investigation. It cannot validate a
scientific claim or establish a trend without non-social corroboration. An
unretrievable thread is an access failure, not evidence that no concern exists.

**Stop researching for closure** once the retained claim/method rows have
verified primary citations, important counter-evidence is handled, and missing
reproduction is explicitly named. Keep later releases in the radar. Do not
delay closure to chase an indefinitely moving model leaderboard.

## 8. Inputs needed from the operator

| Input | Why it is needed | Work that can proceed without it |
|---|---|---|
| Scope decision: existing stronger submission path, or explicitly narrowed single-node release | Determines whether P4 remains a submission blocker; narrowing needs a reviewed amendment. | P1/P2 and candidate research. |
| A qualified independent human rater, or budget to recruit one; ideally a second rater for overlap | Machine consensus cannot validate itself. The operator need not personally label everything. | Packet/protocol design and all computation audits. |
| If P4 is retained: second-node specifications, available exclusive time, and a compute/judging budget | Prevents uncontrolled hardware/runtime confounds and unauthorized launches. | Feasibility plan, no remote mutation. |
| Later: explicit claim-lock and publication approval | Only a human can promote provisional claims; pushing `main` can publish the site. | Private isolated computation and proposed migration changes. |

No credentials need to be pasted into chat. Access and launch permissions, if
needed later, should be provisioned through the existing authenticated workflow.

## 9. Threats and release gates

| Threat | Type | Mitigation |
|---|---|---|
| Old corrections survive in some scripts, prose, or site cells | Measurement | One claim-to-script inventory; independent recomputation and retired-claim checks. |
| Machine-selected or exposed human labels | Construct validity | Fresh probability sample, unexposed raters, immutable provenance, diagnostic subset kept separate. |
| Display truncation changes the rated answer | Measurement | Versioned full-text packet matched to the instrument input. |
| Tags treated as independent models | Statistical | Verified lineage map; deployment and weight-level estimands distinguished. |
| Budget-related missingness | Internal validity | Assigned-cell denominators; finish states reported separately; no automatic censoring correction without assumptions. |
| One CPU and a curated scenario set | External validity | State limits; second platform study if required by scope; no universal ops-autonomy claim. |
| Provisional results reach the public site | Release integrity | Human claim lock first; isolated outputs; explicit publication approval and portal verification. |

The existing validation entry points are
[lane tests](../../scripts/test-analysis-lane.py),
[summary tests](../../scripts/test-analysis-summary.py),
[condition tests](../../scripts/test-verify-run-conditions.py),
[join-integrity tests](../../deep-dive/test_join_integrity.py),
[statistics/metric tests](../../scripts/test-analysis-metrics.py),
and the [site build/verification script](../../scripts/build-analysis-site.sh).
Passing today's baseline proves infrastructure behaviour, not the correctness
of every scientific analysis. P2 needs the focused tests for each actual repair.

| Gate | Existing entry point / focused repair test | Expected invariant |
|---|---|---|
| Snapshot and condition integrity | `scripts/verify-run-conditions.py --bundle <locked-bundle> --lane <canonical-lane>`; `deep-dive/test_join_integrity.py` | Exact roster/scenario/repetition coverage, both judges, one frozen protocol, no duplicate or orphan joins. |
| Population and identities | Model-lock validation plus a new focused membership fixture during P1 | Eligible roster independent of metric missingness; uncertain lineage cannot create a verified pair. |
| Metrics and failure states | `scripts/test-analysis-metrics.py` plus retained-claim fixtures during P2 | Different finish states and different success definitions cannot collapse into one metric; zero-success cost preserved. |
| Resampling | New minimal duplicated-cluster fixture during P2 | Sampling the same scenario twice contributes twice, without splitting its repetitions/judges. |
| Batch/model fitting | Focused failure-exit and fitted-population fixtures during P2 | Analysis failure fails the gate; model count matches actual fitted rows; random-effects structure is as stated. |
| Reproduction and publication | `scripts/build-analysis-site.sh --verify`, paper/claim/privacy/link/portal checks after human lock | No 94/152 cross-wiring, no provisional public outputs, fresh-checkout output agreement. |
