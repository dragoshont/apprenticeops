---
scan_id: radar-20260713-initial
analysis_date: 2026-07-13
status: candidate-promotion-packet
canon_changed: false
---

# ApprenticeOps Paper-Impact Packet — 2026-07-13

> **Decision boundary.** This packet interprets the preserved radar against the
> current manuscript. It does not promote a citation, edit the paper, interpret
> the active timeout run, or turn a proposed experiment into a finding.

## Executive Decision

The 42-source radar does **not** show that ApprenticeOps' narrow contribution has
been published elsewhere. No reviewed source jointly measures operations quality,
destructive-action refusal, and direct energy for small, locally-sovereign,
CPU-only deployment selection under one comparable measurement regime.

It does narrow the defensible novelty to that exact intersection:

- small models and specialist deployments are established design classes;
- action safety, quantization risk, and energy are established individual axes;
- recovery-aware operations benchmarks now evaluate stronger stateful tasks;
- deployment-condition comparability is necessary scientific hygiene, not enough
  by itself as a novelty claim.

The paper should therefore lead with the **released sovereign deployment evidence
and comparability-enforced integration**, not with “small models can do ops,” a
new safety mechanism, or comparability as an abstract idea.

## What Feedback Actually Exists

No external reviewer feedback has been submitted. The public repository has two
owner-authored, closed CEOps implementation issues and no third-party review
issue. `REVIEWER.md` and `docs/analysis/reviewers.qmd` contain **anticipated
review questions**, not received reviews.

The observed feedback is internal and adversarial:

1. the former 12-of-94 energy front mixed incompatible regimes and was withdrawn;
2. one safety superlative was softened and a served failure was disclosed;
3. quality/safety breadth was separated from the controlled systems scope;
4. judge–human agreement, a second human reproduction, and archival publication
   remain open gates;
5. the paper itself asks whether integration is novel enough, whether the thin
   safety arm is over-scoped, and whether energy is a real contribution.

This packet keeps those three evidence classes separate: received feedback,
author-anticipated questions, and new literature pressure.

## Gap Diagnosis

### 1. Operations benchmark depth is the strongest novelty pressure

The recent operations cluster has moved beyond answer-only diagnosis:

- STRATUS defines an explicit state machine and Transactional No-Regression:
  `arxiv:2506.02009@arxiv-v2`.
- AgenticOpsEval separates localization, fault identification, and evidence:
  `arxiv:2606.29193@arxiv-v1`.
- R2Act reports high root-cause accuracy beside much lower recovery validity:
  `arxiv:2607.04623@arxiv-v1`.
- Cloud-OpsBench supplies deterministic state snapshots:
  `arxiv:2603.00468@arxiv-v1`.
- The RCA failure study identifies incomplete exploration and hallucinated
  telemetry as process failures: `arxiv:2602.09937@arxiv-v2`.
- PROBE separates grounded diagnosis from bounded recovery guidance:
  `arxiv:2605.08717@arxiv-v2`.

These works do not occupy ApprenticeOps' sovereign CPU and direct-energy
intersection. They do mean that a 19-scenario static response benchmark should
not imply that it measures recovery or represents the frontier of AIOps task
mechanics. Model breadth cannot repair this task-depth gap.

**Paper consequence:** add this cluster to related work and state explicitly that
the current artifact evaluates diagnosis/planning/refusal responses, not executed
recovery or restored health. Do not claim current data separately scores action
admissibility or recovery.

### 2. Comparability is strongly corroborated but is not sufficient novelty

The compression and edge-systems cluster validates the paper's correction:

- ParetoQ shows trained 2-bit or ternary models can compete under suitable QAT,
  so four bits is not a universal optimum: `arxiv:2502.02631@arxiv-v2`.
- ACBench finds compression loss differs by capability:
  `arxiv:2505.19433@arxiv-v2`.
- Direct Raspberry Pi measurements find model-specific q3/q4/q8 latency and
  energy orderings: `arxiv:2504.03360@arxiv-v1`.
- The edge-MoE study shows active parameters do not determine resident memory or
  realized edge cost: `arxiv:2606.21428@arxiv-v3`.
- Its pinned artifact demonstrates strong deployment provenance:
  `repo:github.com/Analytics-Everywhere-Lab/edge-moe@git-200040be8d54bd8ed5ad82bcd704348d4103fd34`.

**Paper consequence:** retain the invalid-join correction as evidence of rigor,
but frame the contribution as the integrated, auditable dataset and selection
result. Qualify every q4, MoE, active-parameter, and quantization statement as
lineage-, runtime-, task-, and hardware-specific.

### 3. “Training type governs safety” remains observational

The manuscript correctly says safety is corroboration, but several headline
passages still use causal-sounding language such as “training type governs
safety” or “the dominant driver.” The frozen roster did not randomize training
regime, and `docs/ANALYSIS.md` already labels this an observational contrast.

The adaptation-risk literature makes the problem more important, not more
causal:

- narrow fine-tuning can induce broad misalignment:
  `web:proceedings.mlr.press/v267/betley25a@web-sha256-b22d909675718e59e9de074877ff5706c1b9e9c3abe7410577179de9b42ccf04`;
- influence-selected benign samples can degrade safety:
  `web:proceedings.mlr.press/v267/guan25c@web-sha256-e32bdfab697b7cfdee0e2ff93e459c28a0a96e43de03eb44e8ec0c7a5910b841`;
- Safe Delta is a mitigation candidate, not an evaluation waiver:
  `web:proceedings.mlr.press/v267/lu25g@web-sha256-438a402965fd2a686b651fc47743a3fbac2fbdae2e27e9bb40473e2f0c8a6738`.

**Paper consequence:** replace causal shorthand with “training regime is the
strongest observed association in this roster” and retain the exact paired
contrast. The cluster belongs in related work or future-work motivation; it does
not prove the mechanism behind the current R1-distilled result.

### 4. Failure-inclusive timeout analysis can become a method result only after lock

LLMThinkBench reports severe accuracy degradation under constrained reasoning
budgets: `arxiv:2507.04023@arxiv-v3`. The radar found no accepted method jointly
handling timeout, token-cap length, blank output, OOM, parse failure, and
completion as distinct benchmark outcomes.

The active timeout-sensitivity study is therefore potentially valuable, but no
partial result is eligible. Its value is not another leaderboard. It is a locked
sensitivity analysis showing how timeout policy changes completion, failure
strata, conditional quality, failure-inclusive quality, and ranking.

**Paper consequence:** no change now. After 2,100 inference rows, 4,200 canonical
judgements, bundle verification, and independent review, decide whether the
result belongs in the manuscript, supplement, or a methods follow-up.

### 5. Fine-tuning, distillation, and specialist routing are a separate study

FunctionGemma, RandLoRA, K-Merge, Distillation Scaling Laws, Data Laundering, and
specialist-model releases establish a credible next research program. They do not
repair a current-paper weakness cheaply. A valid adaptation experiment needs
base/adapted lineage, incident-disjoint utility, general retention, contamination,
full safety, latency, memory, energy, and routing errors.

Adding one tuned model to the present observational roster would increase
confounding while pretending to answer a causal question. This is new-paper
scope.

## Promotion Disposition

### `add-now`

These are candidates for a later human-approved bibliography and prose pass. No
result table or figure needs to change.

| Priority | Cluster | Exact source versions | Manuscript effect |
|---:|---|---|---|
| 1 | Recovery-aware operations | `arxiv:2607.04623@arxiv-v1`; `arxiv:2506.02009@arxiv-v2`; `arxiv:2606.29193@arxiv-v1`; `arxiv:2603.00468@arxiv-v1`; `arxiv:2602.09937@arxiv-v2`; `arxiv:2605.08717@arxiv-v2` | Update AIOps related work; narrow current task claim; add executed recovery as future work. |
| 2 | Compression and deployment identity | `arxiv:2502.02631@arxiv-v2`; `arxiv:2505.19433@arxiv-v2`; `arxiv:2504.03360@arxiv-v1`; `arxiv:2606.21428@arxiv-v3` | Qualify q4/quantization/MoE language; strengthen comparability rationale. |
| 3 | Adaptation risk | `web:proceedings.mlr.press/v267/betley25a@web-sha256-b22d909675718e59e9de074877ff5706c1b9e9c3abe7410577179de9b42ccf04`; `web:proceedings.mlr.press/v267/guan25c@web-sha256-e32bdfab697b7cfdee0e2ff93e459c28a0a96e43de03eb44e8ec0c7a5910b841`; `web:proceedings.mlr.press/v267/lu25g@web-sha256-438a402965fd2a686b651fc47743a3fbac2fbdae2e27e9bb40473e2f0c8a6738` | Qualify causal training language and motivate a separate preregistered adaptation study. |

### `add-after-current-run`

| Candidate | Required gate | Possible paper role |
|---|---|---|
| Timeout and failure-stratum sensitivity, grounded by `arxiv:2507.04023@arxiv-v3` | Complete and lock all 2,100 rows and 4,200 judgements; preserve every failure; independent review | Sensitivity subsection or supplement; never a partial headline. |
| Answer-stability risk coverage, grounded by `arxiv:2605.25394@arxiv-v1` | Out-of-fold threshold selection on development incidents and evaluation on held-out incidents | Exploratory uncertainty result only if selective risk improves honestly. |

### `related-work-only`

- Distillation Scaling Laws: `arxiv:2502.08606@arxiv-v2`.
- Data Laundering: `doi:10.18653/v1/2025.acl-long.407@doi-version-2025-07-01`.
- RandLoRA: `arxiv:2502.00987@arxiv-v2`.
- K-Merge: `doi:10.18653/v1/2026.acl-long.137@doi-version-2026-07-01`.
- RAG × training-type system-log study: `arxiv:2601.07790@arxiv-v1`.

Use these only where the manuscript explains why adaptation, distillation, or
causal RAG effects are not claimed by the current design.

### `future-work`

1. A recovery-aware sovereign benchmark with typed evidence, diagnosis,
   operation, target, parameters, preconditions, expected postcondition,
   execution receipt, and observed terminal health.
2. A preregistered adaptation study: base, paired RAG, target LoRA,
   replay-anchored LoRA, and safety-defended LoRA.
3. A matched q3/q4/q8/QAT or ternary study on at least two hardware points.
4. Specialist routing and fallback using the pinned FunctionGemma revision:
   `model:huggingface.co/google/functiongemma-270m-it@model-revision-39eccb091651513a5dfb56892d3714c1b5b8276c`.
5. A second hardware point. For this paper's external-validity threat, this is
   likely more valuable than another large tag sweep on the same ThinkPad.

### `monitor`

The following are model/runtime watch candidates, not paper findings:

- BitNet report and runtime: `arxiv:2504.12285@arxiv-v2` and
  `repo:github.com/microsoft/BitNet@git-01eb415772c342d9f20dc42772f1583ae1e5b102`;
- Apple 3B: `arxiv:2507.13575@arxiv-v3`;
- MobileLLM-R1: `arxiv:2509.24945@arxiv-v3`;
- Granite H-Micro:
  `model:huggingface.co/ibm-granite/granite-4.0-h-micro@model-revision-d5f01a3ea75f088947be3aae039f4ad52837dfde`;
- SmolLM3:
  `model:huggingface.co/HuggingFaceTB/SmolLM3-3B@model-revision-a07cc9a04f16550a088caea529712d1d335b0ac1`;
- Ministral 3: `arxiv:2601.08584@arxiv-v1`.

These first-party releases establish availability and publisher claims, not
independent ops utility or CPU-energy performance.

### `reject`

- Do not use the xLAM issue
  `web:github.com/SalesforceAIResearch/xLAM/issues/37@web-sha256-c5f9ab09fb21404b972ab0082634546c0a964a6eb976fd163c835ada340a1af5`,
  Needle pull request
  `web:github.com/jason-easyazz/zoe-ai-assistant/pull/1276@web-sha256-e656d35b6720ca9b462f4d70cc2b40ee641e00d7a7b86603ab5aebbea18cb8b5`,
  or Selora HN thread
  `web:news.ycombinator.com/item/48576208@web-sha256-ae46d76d0c3cb9781e5070502a679508731effdf57bd7e440848ad3fca854cc0`
  as paper evidence. They remain practitioner leads.
- Do not add arbitrary public-LoRA merging as an experiment; the preserved
  negative result `arxiv:2602.12323@arxiv-v2` argues for a target-task adapter or
  a preregistered adapter-bank treatment instead.
- Do not bolt one specialist or tuned model onto the frozen roster and call it an
  adaptation result.
- Do not add partial timeout-run values.

## What Is Worth Adding to This Paper

The smallest defensible paper update is prose and bibliography only:

1. **Related work:** add the recovery-aware operations cluster and explain that
   ApprenticeOps is a deployment-selection benchmark, not a recovery benchmark.
2. **Claim qualification:** change causal-sounding training language to an
   observational-roster statement.
3. **Systems positioning:** add the compression/deployment cluster and state
   explicitly that q4 is a local prior, not a universal optimum; total/resident
   parameters and runtime are part of condition identity.
4. **Limitations/future work:** name executed recovery and a second hardware point
   as the two highest-value extensions.

Do **not** add a fine-tuning section, specialist result, recovery result, or
failure-sensitivity number without new locked evidence.

## Novelty and Venue Implications

### Novelty that survives

- one harness joining quality, deterministic refusal, and direct energy under a
  controlled sovereign CPU regime;
- an executable comparability boundary that prevented and exposed an invalid
  cross-regime energy join;
- real-incident deployment-selection evidence and a reusable failure-inclusive
  schema.

### Novelty to stop claiming or implying

- small models are useful for specialist/agent tasks;
- action safety differs from text safety;
- quantization, training, or model size alone predicts deployment readiness;
- realistic incidents or deterministic checks are unique to ApprenticeOps;
- comparability by itself is novel.

### Venue read

The Datasets & Benchmarks case remains defensible but is now more demanding. A
reviewer can reasonably call the scenario set small and static beside newer
stateful recovery benchmarks. The response is not to imitate them inside the
current paper. It is to present ApprenticeOps as a **sovereign deployment
measurement artifact**, make the 94/24 comparability boundary central, and keep
recovery as the next benchmark generation.

MLSys or an on-device/efficient-ML venue becomes more attractive if reviewers see
the systems condition identity, direct energy, and invalid-join prevention as the
strongest contribution. A safety venue remains a poor fit because the safety
result is corroborating and thin by independent-scenario count.

## Recommended Sequence

1. Preserve this packet beside the radar with `canon_changed=false`.
2. Wait for explicit human approval before creating promotion records or editing
   `references.bib`, `literature-catalog.md`, or `paper.qmd`.
3. If approved, promote the operations and compression clusters first; update
   observational wording in the same claim-audit pass.
4. Run the paper claim audit and regenerate HTML/PDF after that prose-only pass.
5. Revisit timeout sensitivity only after its independent lock and review.
6. Keep adaptation, recovery execution, and specialist routing as separately
   preregistered studies.

## Evidence Limits

- This packet uses the 42 preserved source versions; it reproduces none of their
  experiments.
- Several 2026 items are preprints and may change.
- First-party reports and model cards are not independent validation.
- No external reviewer feedback was available; anticipated questions are not
  presented as received reviews.
- The active timeout experiment was treated as unavailable.
