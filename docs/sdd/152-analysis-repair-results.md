# 152-deployment analysis repair results

**Date:** 2026-09-09. **Status:** retained computations implemented, independently
reproduced, and accepted by final GPT/Claude review. The corpus and all candidate
results remain **provisional**; this is not a human-validity or claim lock.

> **Scope honesty.** We repaired calculations on the existing single-environment
> study. We did not validate the judging or usability instruments, establish
> independent weight lineages, collect human labels, or run another experiment.
> These are **machine-calculation-only results**, not new paper claims.

## 1. Population and identity

We used the [approved closure programme](152-analysis-closure.md) and
[statistics plan](../STATISTICS.md). The final evidence directory is
[`deep-dive/out/analysis-repair-152-20260909-r4/`](../../deep-dive/out/analysis-repair-152-20260909-r4/).
The preceding `-r2` receipts are preserved, not overwritten. Historical outputs
remain unchanged. The parent relayed a GPT core-math PASS with two required
corrections: we now reject unmapped/missing authoritative scenario classes
(including attempts to substitute `category` or a name prefix), and label A2's
third score axis **unvalidated safety-scenario judge score**. The r3 correction
left all 17 core CSV/PNG artifacts byte-identical to r2. The parent subsequently
relayed Claude's core PASS with a reduced-key compatibility caveat. R4 adds
explicit named-policy and condition-identity guards and condition columns in
`identity.csv`; the other 16 numeric CSV/PNG files remain byte-identical to r3.
Independent final acceptance remains with the parent.

The user's approval covers **all nonhuman closure computations**, not only the
initial repair slice. The [selection extension](152-selection-stability-results.md)
now computes rank, top-k and Pareto stability plus integer-tier descriptions.
These computations are complete; their independent review/reconciliation is active.

The locked grid contains **152 deployments × 20 scenarios × 5 repetitions =
15,200 cells**, with 30,400 judgments. Eligibility is the run roster intersected
with **positive integer parameters ≤5,000,000,000**, model-lock `included=true`,
and a model-lock tier in T1–T5. No safety-score complete-case table determines it.

**Reduced-key compatibility is specific to this frozen study.** The full
requested evaluation policy is
`deterministic-checks-v1|judges:copilot:claude-opus-4.6+copilot:gpt-5.4`.
The join now requires those **named judges**, not arbitrary two distinct models;
the raw-judgment reader also requires the named backend and declared policy.
We prove **one complete canonical condition hash per deployment**, 152 in total,
and verify that **all 30,400 canonical judgments carry their deployment's result
condition hash**. `identity.csv` and the core receipt preserve this proof.
The existing read-only `scripts/verify-run-conditions.py --bundle <locked-bundle>
--json` also passes **28/28 checks** for the raw run's fixed protocol/coverage.

The compact `(model, scenario, rep)` projection is therefore compatible **only
for the hash-identical snapshots of this bundle**. The snapshot hashes, complete
named-domain join and canonical condition proof must all hold before any claim
promotion; this does not waive the full `analysis_condition_key_sha256` join
required by the statistics plan for new or multi-condition evidence. No locked
raw rows were remapped, and a condition ID is not an independent weight lineage.

| Audit | Observed result | Disposition |
|---|---|---|
| Eligible primary population | **137 deployments; 13,700 cells** | Frozen in `eligibility.csv`; the other 15 are above 5B. |
| Numeric versus lock-included membership | **0 discrepancies** | The old downstream-filter risk did not actually lose deployments here; the fixture proves the repaired rule is independent of outcomes. |
| Lock tiers versus integer-derived tiers | **27 discrepancies**, all within the primary roster | Preserve both fields and use the integer-derived tiers for descriptions. For example, `codegemma:2b` has 2,506,172,416 parameters (T3), but lock tier T2. |
| Lock parameter values | 152 exact-value differences from run integers, including rounded/nominal values | Record differences, not automatic corrections to `models.lock.jsonl`. |
| Run integer snapshot | Matches canonical integers for all 152 deployments | Run integers now populate both `param_count` and `params_b`; absent counts remain missing. Curated integers remain separately auditable; names/text never fill them. |
| Artifact identity | **133 digests across 152 tags; 118 across 137 primary tags** | Digest identity is not underlying weight-lineage identity. The previous “approximately 100 weight-sets” estimate is withdrawn. |
| Model-lock digest coverage | **10 recorded, all matching the run; 142 missing** | `identity.csv` preserves both sources; a missing lock digest is not a verified lineage. |
| Verified weight grouping | None supplied by this audit | Every lineage remains `unverified`; neither equal counts nor name stems certify a pair. |
| Candidate screen | 173 candidates, 152 selected, 21 excluded | `candidate_screen.csv` preserves the selection boundary; no excluded candidate becomes a measured study row. |

The 21 screen exclusions comprise 12 served failures, five empty completions,
two pull failures, and **two chat-empty/generate-nonempty warnings**:
`hf.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF:Q4_K_M` and
`deepscaler:1.5b`. The last two served visible text through `/api/generate`
(63 and 56 characters), but failed the recorded `/api/chat` selection policy.
This is a selected deployment corpus, not a representative sample of small models.

Training regime is missing for **62/152** tags; the annotated remainder comprises
82 instruct, seven code/math and one reasoning entry. Thinking capability is
separate: seven true, 83 false and 62 unknown. All 15,200 rows record
`think=false` and zero `gen_ai.thinking.chars`. This does **not** prove that their
visible answers contain no reasoning. `reasoning_name_hint` is explicitly a
heuristic; it no longer fills the training flag.

Those annotations come from `model_metadata.csv` then `models-inventory.csv`,
**not the model lock**. The lock instead records 78 unknown, 53 instruct,
15 code and six reasoning training types; its architecture is unknown for 142,
hybrid for eight and MoE for two. `metadata_audit.csv` preserves both sources.
Forty-three tags have inherited training annotations but unknown lock training;
27 have lock training but missing inherited annotations; 35 lack both.
We do not silently merge these into verified training provenance. B3's counts
below reproduce its inherited-annotation design, not a union of these sources.

## 2. Corrected metric definitions and numbers

We retain the recorded primary threshold **3.0**. An *instrument-positive attempt*
has consensus judge score ≥3. This is the operational definition behind the
existing `wh_per_usable` field, **not validated real-world usability**.

- **`pass_1`:** fraction of observed attempts that are instrument-positive.
- **All-five success:** fraction of deployment–scenario cells whose five attempts
  are all instrument-positive. Missing judgments or incomplete/duplicate
  repetition groups fail the reliability calculation.
- **Mean-good:** fraction of deployment–scenario mean scores ≥3. This is a
  descriptive thresholded-mean statistic, not `pass_1`.
- **Energy per instrument-positive answer:** all assigned CPU-package Wh divided
  by the number of instrument-positive answers. Missing energy/judgments produce
  missing cost, not zero. Zero-success deployments remain explicit with infinite
  cost. Energy is **RAPL package-0**, not wall power or DRAM-inclusive energy.

We resampled the **20 scenarios**, preserving all deployments and repetitions
and every duplicated scenario draw: seed `20260725`, 4,000 draws, percentile
95% intervals. These intervals describe task-composition sensitivity for the
fixed roster; they do not make the curated scenarios a probability sample of SRE
incidents or deployments independent training replicates.

| Primary consensus ≥3 statistic | Corrected value | 95% scenario-bootstrap interval |
|---|---:|---:|
| `pass_1` | **28.401460%** (3,891/13,700 attempts) | [20.459124%, 36.328832%] |
| All-five success | **11.459854%** (314/2,740 cells) | [7.043796%, 16.240876%] |
| `pass_1` minus all-five | **16.941606 pp** | **[13.102190, 20.708759]** |
| Mean-good | **17.992701%** (493/2,740 cells) | [11.423358%, 24.635036%] |
| Mean-good minus all-five | **6.532847 pp** | **[4.123175, 8.978102]** |
| Spearman: Wh/attempt versus Wh/instrument-positive answer | **0.116359**, finite-cost **n=135** | **[−0.006659, 0.324533]** |

The old regrouping collapsed repeated scenario draws. For the same seed and
mean-good contrast, that mechanism gives [4.548007, 8.427339] pp rather than the
corrected wider interval above. The point estimate does not change; its
interpretation and interval do.

All **1,080.46705 Wh** assigned to the primary population enter the energy
accounting. There are **zero missing-energy cells**. At threshold 3,
`codegemma:2b` and `starcoder2:3b` have zero successes despite consuming
10.25050 and 13.84306 Wh; both remain in `energy_deployments.csv`.
The correlation necessarily conditions on finite costs. Across its bootstrap
draws, that finite population varies from **106 to 135 deployments**; all 4,000
correlation draws were finite.

| Consensus threshold | `pass_1` | All-five | Gap, pp [95% interval] | Energy ρ [95% interval]; finite n; zero-success n |
|---:|---:|---:|---|---|
| 2.5 | 37.905% | 17.482% | 20.423 [16.927, 23.686] | 0.387 [0.240, 0.504]; 136; 1 |
| **3.0** | **28.401%** | **11.460%** | **16.942 [13.102, 20.709]** | **0.116 [−0.007, 0.325]; 135; 2** |
| 3.5 | 12.387% | 3.066% | 9.321 [5.956, 12.818] | −0.067 [−0.146, 0.229]; 116; 21 |
| 4.0 | 7.153% | 1.460% | 5.693 [3.204, 8.504] | 0.063 [−0.037, 0.432]; 105; 32 |

At threshold 3, Claude-only `pass_1`/all-five are **31.898%/14.270%**,
gap **17.628 [14.146, 20.942] pp**; GPT-only values are
**34.766%/14.380%**, gap **20.387 [16.474, 24.007] pp**.
Their energy correlations are **0.128680 [0.005737, 0.333335], n=135**, and
**0.396250 [0.258922, 0.500336], n=136**, respectively.
These sensitivities do not select a new threshold or demonstrate instrument validity.

The eligible five safety-tagged scenarios contain 3,425 cells; only **2,740**
have an applicable action-safety check. All ten empty-output cells among those
2,740 pass their action checks: evidence of a vacuous-pass weakness, not safety.
We include `must_exclude`, `must_not_endorse`, and `must_exclude_action`; absence
of an applicable check remains missing. The mean action-check score among 2,730
responsive cells is **0.787179**.

## 3. Retained analyses and claim disposition

Each row below refers to the **same hash-verified study**, never the legacy94
outcomes. `receipt.json` and `ab/receipt.json` bind source/code hashes and all
26 generated evidence files. “Retain” means retain as a candidate description,
not promote into the paper.

| Candidate claim | Disposition | Population / metric / executable evidence |
|---|---|---|
| Primary eligibility | **Retain** | 137 tags; `full_data.eligibility_table`; `eligibility.csv`; boundary/missingness fixture. |
| Tier descriptions | **Correct / descriptive** | Integer counts already govern under `AGENTS.md`; the selection extension reports integer-derived groups alongside 27 conflicting frozen lock assignments. No new human choice of integer authority is required; no inferential size effect is claimed. |
| Approximately 100 independent weight-sets; quantization effects | **Withdraw / not identifiable** | 133 artifacts are not 133 independent weights. `identity.csv`; A3 excluded in `ab/disposition.json`; no name-based paired inference retained. |
| Reliability gap | **Correct** | 13,700 attempts versus 2,740 five-repeat cells; `phase4_repairs.py`, `sensitivity.csv`; duplicated-cluster and binary-success fixtures. |
| Energy “inversion” | **Exploratory; withdraw any robust universal inversion wording** | 137 assigned deployments, 135 finite at threshold 3; interval crosses zero and results depend on threshold/judge. `energy_deployments.csv`, `sensitivity.csv`. |
| Action checks measure operational safety | **Withdraw** | 137 tags; applicability and empty-response defect above; `check_summary.json`, `action_safety_primary.csv`. |
| Ranking / scaling / efficiency | **Exploratory** | A1/A2 rerun on 137; size-cost subset n=85. Integer-size/quality Spearman **0.723**. Best mean judge score: `qwen3:4b-instruct-2507-q8_0`, **3.590 [3.140, 4.010]**. No equivalence from overlapping CIs. |
| Task capability / repeat variability | **Exploratory** | A4/A6 rerun on 137 × 20 × 5; split-half rank correlation **0.979**. Composite deterministic checks are no longer labelled action-safety decisions. |
| Judge validity from agreement | **Withdraw validity interpretation; retain agreement description** | 13,700 paired judgments: exact **68.547%**, within-one **98.715%**, quadratic κ **0.846839**. `judge_agreement.json`; no human accuracy estimate. |
| IRT task-pruning conclusion | **Withdraw from retained analysis** | B1 lacks a convergence/identifiability gate and uses an unvalidated `det>=0.5` construct; explicitly excluded, not silently successful. |
| Metric clusters | **Exploratory only** | B2: 137 tags, **52 size values median-imputed**, four clusters, silhouette **0.41**; no verified model archetypes. `ab/b2_clusters.csv`. |
| B3 training/architecture partial effects | **Not identifiable; old coefficients/CIs withdrawn** | Old design: **9,000 rows / 90 deployments**, not 152 clusters. Primary complete cases: **8,700 / 87**, excluding 5,000 rows. `b3_population_*.csv`, `ab/b3_mixedeffects.txt`. |
| Roofline / regime / general hardware effects | **Not identifiable here** | No measured memory-bandwidth axis, one regime, one platform; no replacement headline. |

B3's primary complete cases contain **86 dense and one MoE** deployment, and
**79 instruct, seven code/math, one reasoning** entry. Unknown flags/quantization
remain missing. The old mixed-model specification nested scenario effects within
deployment and supplied no model intercept for its `cov_re` access; it was not
the claimed crossed cross-check. We remove that fit and report **zero newly fitted
rows**, rather than relabel it as validated crossed inference.

The retained A/B audit also repaired the transposed Friedman input
(models are treatments, scenarios blocks) and strict Pareto dominance at equal
cost. The corrected Friedman statistic is **1682.2**, Kendall's W **0.618**;
neither establishes generality beyond this corpus. The batch now records an
exception and exits nonzero; it cannot print completion or write a success
receipt after a failed retained script. Loader/output patches are call-scoped.

## 4. Reproduction and verification

Interpreters were pre-existing: root `.venv` **Python 3.14.7** for repository
gates; `deep-dive/.venv` **Python 3.14.5**, NumPy 2.5.1, pandas 3.0.3,
SciPy 1.18.0 for analysis. No package was installed. Exact commands:

```bash
deep-dive/.venv/bin/python deep-dive/test_analysis_repairs.py
deep-dive/.venv/bin/python deep-dive/test_join_integrity.py
deep-dive/.venv/bin/python deep-dive/phase4_repairs.py \
  --out deep-dive/out/analysis-repair-152-20260909-r4 --bootstrap 4000
deep-dive/.venv/bin/python deep-dive/full_ab.py \
  --out deep-dive/out/analysis-repair-152-20260909-r4/ab
PATH="$PWD/.venv/bin:$PATH" env -u GIT_CONFIG_COUNT \
  -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 \
  -u GIT_CONFIG_KEY_1 -u GIT_CONFIG_VALUE_1 bash gates/checks.sh
```

Both analysis commands require an **unused output directory**; substitute a new
name to reproduce without overwriting receipts. The canonical raw bundle must
be locally available for the identity/check audit. Hash verification precedes
analysis; no `.tmp`/legacy94 fallback is allowed in these entry points.

| Evidence | SHA-256 |
|---|---|
| Canonical results archive | `660058c452ca197ad9fd0df3a63e5ccddc9377cb348f3d52ee40bd0fd881b1d8` |
| Canonical judged archive | `5b3591b03e3c8e394b50ef0030d5c15c462b6ae7ed0118736ccb0bd313d42d09` |
| Model lock | `c4a96fed7354bc6bc762a93bc0ce0b4bd25d3f4ebc5bd0dfcb64dcd6f203fcb8` |
| Final metric receipt | `22fac59e27ec3df40406d00c5b31cd39ae55596140c0d16f817abc1af185371a` |
| Final `sensitivity.csv` | `cbb8011360452c7e5e1b0910b2fcf5933330c8f1483a84c9e54ec4f83af4f4a1` |
| Final A/B receipt | `269e6a5c334850bcc866222dc184defbb34f46daaaaf6a47dcf6b76dd62df108` |

Source revision: base `15c3a364cac1ec76464b414119c62a781c8fc67b` plus the
uncommitted analysis files individually hashed in those receipts. We independently
rechecked all source hashes and **26 output hashes**. A further final-code rerun
into temporary new directories produced **17 byte-identical CSV/PNG outputs**.
`verification.json` records the deterministic gates separately from the
computation receipts.

Deterministic results: **24 repair fixtures PASS**, including the reproduced
class-fallback, A2-label, wrong named/backend policy and collapsed-condition
failures; real 152×20×5 join and five
corruption cases PASS; lane **8**, summary **13**, condition **18**, metric **27**
tests PASS. Configured `gates/checks.sh` **PASS** with only the stated
terminal-injected Git overrides removed. UI reconciliation is not applicable.
The repository privacy scanner reported **zero secret findings and zero
disclosure findings** on the scoped analysis sources and outputs; the final
scope count is recorded in `verification.json`. This does not override the
separately recorded whole-tree dependency-file scanner caveat.
The focused fixtures first failed on the reproduced mechanisms, not only on
the corrected implementation.

## 5. Completed computations versus remaining gates

| Phase | Name | Status | Scope | Gate | Result |
|---|---|---|---|---|---|
| 1 | Approved P1/P2 analysis repair slice | complete | Population, fixtures, repairs, isolated recomputation | Deterministic evidence plus independent GPT/Claude post-review | Computation, parent tests/hash verification, and final independent reviews PASS. |
| 2 | Approved nonhuman closure extension | complete for retained machine calculations | Selection/rank/Pareto stability, integer-tier descriptions, completion-proxy and energy-metric sensitivity; served-failure effects not identifiable | Deterministic evidence plus independent review | Final bounded sensitivity report closes the retained computational requirements; no validity or publication approval. |

**Implemented in this response:** the analysis files named in the two receipts,
the regression runner, this report and isolated outputs. Changes are integrated
in the shared working tree; no patch application is needed. We preserved the
parent's dirty files and did not edit review UI/assets, human-evaluation data,
claim manifests, paper/bibliography, or the public analysis site. No inference,
rejudging, hardware run, remote mutation, commit, push or claim promotion occurred.

**Additional work implemented:** scenario-resampled rank/top-k/Pareto stability
and integer-tier descriptions are documented in the selection extension, not
merely deferred. Independent lineage verification, human instrument validation,
second-hardware work, publication integration and claim promotion remain
**not completed**. Nonhuman computational work is authorized; new experiments,
validity evidence and publication decisions retain their separate requirements.

The [final sensitivity report](152-selection-sensitivity-results.md) covers the
remaining statistics-plan dimensions and records their non-identifiability
where measurements do not exist. The parent reran all 61 scientific fixtures
and reproduced all 17 final extension computation files byte-for-byte.
Final GPT and Claude reviews accept P2 only at this machine-calculation level.

**Next evidence gate:** independent human instrument validation. The operator
pilot is useful review input, not a substitute for that evidence. Lineage,
hardware, claim-lock and publication requirements remain explicitly open.

Audit run: `.architrave/runs/analysis-repairs-20260909`. Creation succeeded.
The external `task-add` CLI failed with `unsupported command: None`, then
`TypeError` for a list-valued command; the supported native `RunStore.add_task`
API registered the pending parent-review task without changing kit code or
manually editing signed state. Native verification correctly remains incomplete.
The installed legacy `harness/validate-run.sh` rejects the generated v2 summary
schema; we report that failure rather than downgrade or hand-edit the run.
The earlier parent run's reported `ARTIFACT_TAMPERED` candidate-patch resume
failure remains unresolved and was not bypassed.

| Threat | Type | Mitigation |
|---|---|---|
| Unvalidated machine threshold/checks | Construct validity | Keep metric definitions explicit; restrict interpretations pending human evidence. |
| Unknown lineage and sparse annotations | Statistical | Retain tag descriptions; exclude weight-level, quantization and B3 inferential headlines. |
| Twenty curated scenarios, one platform, screened roster | External validity | Report fixed-corpus/task-composition sensitivity; no random-model or general-SRE claim. |
| Variable finite-cost population | Selection | Preserve zero-success rows and disclose point/replicate denominators. |
| Median-imputed size in B2 | Measurement | Disclose 52 imputations; clusters remain exploratory. |
| External audit-tool incompatibility | Reproduction/process | Preserve canonical v2 receipts, record failures, leave final gate with the parent. |

Candidate lesson for parent review, **not promoted**: cluster identity must
distinguish source identity from bootstrap draw identity, and every reported
denominator must be taken from the observed/fitted population. The fixtures and
the earlier corrections in `AGENTS.md` provide recurrence evidence.
