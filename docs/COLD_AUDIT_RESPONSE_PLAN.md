# Cold Audit Response Plan

Status: working consolidation plan, created 2026-07-03. This document converts
the external cold audit in `/Users/dragoshont/Repo/ceops-audit-cold.md` into a
repo-grounded remediation plan for ApprenticeOps / CEOps.

This is a plan, not a rewrite of the paper. It deliberately separates the locked
94-model paper-era result from the intended doctoral target: open-weight models
up to **5B parameters** on CPU-only commodity-laptop hardware.

## A. Executive Summary

Verdict against the intended doctorate: **Partially aligned**.

The repository has strong infrastructure for a serious benchmark: a large model
roster, committed result snapshots, CPU/energy telemetry, scenario validators,
external dev-scenario gates, run manifests, and an autonomous two-node pipeline.
It is not yet aligned enough to hand to a doctoral reviewer as-is, because core
public-facing language still mixes three different boundaries:

1. parameter count, such as `0.5-8B`;
2. quantized deployment footprint, such as `<= 5 GB` or `4-5GB`;
3. the new thesis target, **up to 5B parameters**.

That ambiguity is a P0 defect. A reviewer could reasonably conclude the benchmark
question is moving underneath the results.

Top five risks:

| Risk | Severity | Why it matters |
|---|---:|---|
| Thesis boundary drift: README, REVIEWER, CITATION, paper docs still say `0.5-8B`, `<=8B`, `<=5 GB`, or `4-5GB` as research framing. | P0 | The cold audit's highest-priority question fails unless the repo distinguishes old snapshot framing from the new <=5B-parameter thesis. |
| No committed model lockfile with parameter tiers, licenses, digests, inclusion/exclusion decisions, and variant handling. | P0 | `data/models.txt` has 158 tags, but the tier comments are not enough for a defensible 150+ model doctoral protocol. |
| README and reviewer docs overstate current publication readiness in places. | P0 | Claims such as preprint/NeurIPS readiness and verified numbers must be tied to the locked snapshot and caveated as pre-submission. |
| Statistical and judge/human validation story is incomplete for doctoral claims. | P1 | Cross-judge agreement is present, but human-vs-judge validation remains an open item and should not read as completed. |
| Reproducibility is strong operationally but scattered across docs. | P1 | A reviewer needs one protocol path: eligibility -> locked models -> scenarios -> run -> judge -> report -> figures. |

## B. Evidence And Assumption Register

| Claim | Classification | Evidence location | Confidence | Notes |
|---|---|---|---:|---|
| The intended thesis target is <=5B parameters, not <=5 GB footprint. | user context | Cold audit file `/Users/dragoshont/Repo/ceops-audit-cold.md` | high | This is the controlling correction for the remediation plan. |
| Current public docs still frame parts of the work as `0.5-8B` / `<=8B`. | repo evidence | `README.md`, `REVIEWER.md`, `CITATION.cff`, `docs/PAPER.md`, `docs/analysis/paper.qmd` search results | high | Must be reconciled, not blind-replaced, because the locked 94-model snapshot did include larger models. |
| Current public docs still use `<=5 GB` / `4-5GB` as a research bracket. | repo evidence | `README.md`, `docs/PAPER.md`, `docs/PAPER_INTENT.md`, `docs/MODELS.md`, `docs/TELEMETRY.md` | high | Some uses are valid footprint language; others are thesis-boundary language and must change. |
| The current model roster has 158 tags. | repo evidence | `data/models.txt` counted locally | high | This matches the 150+ target in count, but not yet in <=5B parameter eligibility. |
| The current roster includes a `4-5GB` bracket with 7B/8B models. | repo evidence | `data/models.txt`; examples include `qwen2.5:7b`, `llama3.1:8b`, `deepseek-r1:8b` | high | This is incompatible with a <=5B-parameter thesis unless marked as legacy/footprint-only/out-of-scope. |
| The locked publishable snapshot currently summarizes 94 models. | repo evidence | `data/site/summary.json` has `n_models: 94`; README says consolidated 94-model data. | high | This is a snapshot claim, not the future thesis roster. |
| Current scenario corpus has 33 scenarios; Core current has 20. | repo evidence | `data/scenarios.json`, `data/scenario_sets/core-current.json`, `scripts/validate-scenarios.py` | high | README already distinguishes old 19, current 33, and Core 20, but this should be made clearer. |
| External candidate v1 is dev-only and not paper evidence. | repo evidence | `data/run-matrix.json`, `docs/EXTERNAL_DATASET_CANDIDATE_V1_REPAIR_REVIEW.md` | high | This boundary is currently strong and should be preserved. |
| The latest v1 spread10 dev run completed cleanly on the homelab run directory. | repo evidence | `external-v1-spread10-baseline-clean-20260703-164337`, homelab strict report PASS | high | It remains dev-only scenario-pack evidence. |
| The committed v1 experiment artifacts are not yet self-contained. | repo evidence | Local `report-run-quality.py --strict` reads 450 compressed inference rows and 900 judged rows, but fails `run-meta-missing`. | high | This is now correctly exposed by the reporter and belongs in artifact inventory work. |
| A reviewer can reproduce all headline numbers from one command today. | unknown | Not fully verified in this response | medium | README claims verification; we need a paper-data audit command to prove it continuously. |
| The repo is safe from private-data leakage. | unknown | Not fully scanned in this response | low | README discloses real cluster detail in judge egress; a dedicated privacy scan remains needed. |

## C. README Correction Plan

| Problematic README claim | Why stale/risky | Evidence | Proposed replacement | Priority |
|---|---|---|---|---:|
| `Small, locally-sovereign (<= 5 GB, CPU-only)` in the benchmark comparison table. | Treats footprint as the model eligibility boundary. | Cold audit thesis target; `data/models.txt` currently uses footprint brackets. | `Small, locally-sovereign (target thesis track: <=5B parameters; footprint and RAM reported separately)` | P0 |
| `whether a 3 GB model is meaningfully different from an 8 GB one`. | Uses GB as the research scale; the thesis target is parameters. | README opening section. | `whether a 3B-parameter model is meaningfully different from a 5B-parameter model under the same CPU-only constraints` | P0 |
| RQ5: `Best <=5 GB model reaches ...`. | The audit explicitly marks this as stale unless discussing footprint. | README RQ table; `docs/PAPER.md` has same issue. | `Best <=5B-parameter deployment reaches ...`, or for the old snapshot: `In the legacy footprint-bounded snapshot, the best <=5 GB deployment ...` | P0 |
| `0.5-8B` / `<=8B` in README, REVIEWER, CITATION. | Contradicts the intended <=5B doctoral target. | `REVIEWER.md`, `CITATION.cff`, paper docs. | `The current committed snapshot includes legacy <=8B / footprint-bounded runs; the doctoral protocol targets <=5B parameters.` | P0 |
| `Research paper / arXiv preprint -> NeurIPS Datasets & Benchmarks track`. | Can read as status rather than aspiration. | README first line; REVIEWER section. | `Research artifact in preparation; target venue: datasets/benchmarks track.` | P0 |
| `Verified (2026-06-22): every number...` | Strong claim; needs a continuously runnable audit command or exact snapshot scope. | README top matter. | `Snapshot audit (2026-06-22): paper-era 94-model numbers were re-derived from committed exports; see docs/...` plus a command. | P1 |
| Grounded/RAG language: `do I need a vector database`. | Risks implying measured RAG rather than oracle-grounded upper bound. | README grounding section. | Keep, but add inline caveat: `grounded is oracle context, not a deployed retrieval pipeline.` | P1 |
| Scenario counts across 19/33/20. | The distinctions are true but easy to misread. | README scenarios section; validators. | Add a small `Scenario corpus status` table: paper snapshot 19, current all 33, Core current 20, external v1 dev 9. | P1 |

## D. Methodology Audit

### Model Selection

Current state: partially aligned. `data/models.txt` has 158 model tags and five
bracket comments, but the fifth bracket is `4-5GB` and contains 7B/8B models.
The result snapshots contain useful metadata such as `param_count`, `param_size`,
`quant`, and `size_bytes`, but there is no first-class model lockfile defining
eligibility, tier, license, source, digest, variant policy, or exclusion reason.

Required fix: add `data/models.lock.jsonl` and validate it. The doctoral track
should use parameter tiers:

```text
T1 <=1B
T2 >1B and <=2B
T3 >2B and <=3B
T4 >3B and <=4B
T5 >4B and <=5B
```

Legacy footprint-bounded rows can remain as historical data, but must be labelled
`legacy_footprint_snapshot` or equivalent.

### Scenario Design

Current state: strong but needs consolidation. The repo has scenario definitions,
deterministic checks, judge rubrics, Core/current splits, and external candidate
validators. The new lifecycle schema is the right direction. The gap is a single
scenario manifest that records corpus version, role, count, hash, class mix,
grounding mode, source/privacy status, and promotion status.

Required fix: add `data/scenario_manifest.json` or extend `data/run-manifest.json`
with a documented schema.

### Scoring And Judge Validity

Current state: partial. Deterministic checks and two-judge scoring exist. The
strict run-quality gate now prevents duplicate judge rows or missing judge fields
from being interpreted. However, human-vs-judge validation remains an open item
and should be stated as such everywhere.

Required fix: add `docs/JUDGE_VALIDATION.md` with what is done, what remains open,
and the minimum human evaluation plan.

### Statistics

Current state: partial. The paper docs mention CIs, kappa, Pareto, and bracket
comparisons, but the repo needs a single `docs/STATISTICS.md` that defines the
estimands, repetitions, bootstrap unit, paired comparisons, missing-row policy,
multiple-comparison stance, and Pareto robustness checks.

### Fairness

Current state: partial. Temperature, repeats, seeds, `think`, memory context, and
inference strategy are recorded. Missing or scattered: prompt-template policy,
chat-format policy, top-p/top-k handling, reasoning-output handling, code-model
handling, MoE total-vs-active parameter policy, and quantization variant policy.

Required fix: put these in `docs/PROTOCOL.md`, not only in prose fragments.

## E. Systems Audit

Current state: strong but too distributed. The runner captures RAPL, perf, memory,
swap, wall time, TTFT/prefill/decode, Ollama metadata, and environment fingerprints.
`REPRODUCE.md` explains the two-node topology and node locking. The main weakness
is hardware naming and target consistency: README says ThinkPad T480s / i5-8350U,
while the cold audit target says T14s-class or i5-8500U-class. The fix is not to
pretend they are the same; the fix is to define:

```text
measured_node = ThinkPad T480s, i5-8350U, 24 GiB RAM
target_class = commodity CPU-only laptop, T14s/T480s-like, about 24 GiB RAM
```

Required files:

- `docs/HARDWARE.md`: measured node, target class, limits, telemetry availability.
- `data/hardware-profile.home-ai.json`: machine-readable profile used by runs.

## F. Data, Privacy, And Safety Audit

Current state: partial. The repo is unusually honest about judge egress and real
cluster detail, but this is still a publication risk. A privacy scan should be a
pre-share gate.

Immediate risks to audit:

- real domains and hostnames in scenarios and outputs;
- Azure Key Vault / Cloudflare / cluster identifiers in released text;
- raw prompts/responses in result files;
- generated dashboard exports;
- external candidate source provenance and rights.

Required fix: add `scripts/privacy-scan.py` or a documented `rg`-based privacy
gate, plus `docs/PRIVACY_AND_EGRESS.md` that states what is intentionally public,
what is scrubbed, and what never leaves the local environment.

Safety methodology is directionally strong: guard scenarios, destructive-action
refusal, deterministic checks, and judge rubrics exist. The next improvement is
to separate refusal quality from helpful safe alternatives so models are not
rewarded for refusing safe diagnostics.

## G. Gap Analysis Against The Intended Doctorate

| Requirement | Current evidence | Status | Gap | Priority |
|---|---|---|---|---:|
| 150+ models | `data/models.txt` has 158 tags. | Partial | Need <=5B eligibility lockfile, not just tags. | P0 |
| Five parameter tiers up to 5B | Current roster has 0-1B..3-4B plus `4-5GB`; fifth bracket contains 7B/8B models. | Contradictory | Replace footprint tiering with parameter tiering for thesis track. | P0 |
| CPU-only commodity laptop | `REPRODUCE.md` and README document i5-8350U / 24 GiB node. | Partial | Need target-vs-measured hardware distinction. | P1 |
| Fair benchmark protocol | Run manifests, validators, seeds, repeats exist. | Partial | Need one protocol doc and model/scenario lock schemas. | P0 |
| Reproducible paper artifact | Snapshots and site exports exist; README claims clean audit. | Partial | Need one paper-data audit command and artifact inventory. | P1 |
| Dashboard/results | `data/site/*`, GitHub Pages workflow, dashboard exist. | Partial | Dashboard must badge `legacy`, `dev`, `paper`, and `<=5B thesis` tracks. | P2 |
| Judge validation | Cross-judge agreement reported. | Partial | Human-vs-judge validation not complete. | P1 |
| Safety | Guard/safety scenarios and deterministic refusal exist. | Partial | Need refusal-vs-safe-helpfulness analysis. | P1 |
| Privacy | Disclosure exists. | Unclear | Need explicit privacy scan and publication allowlist. | P0 |

## H. Prioritized Implementation Backlog

### P0 - Must Fix Before Serious Sharing

1. **Thesis-boundary reconciliation.**
   - Type: documentation + data.
   - Files: `README.md`, `REVIEWER.md`, `CITATION.cff`, `docs/PAPER.md`, `docs/analysis/paper.qmd`, `docs/PAPER_INTENT.md`, `docs/MODELS.md`, `AGENTS.md`.
   - Acceptance: every public claim distinguishes `<=5B parameters` thesis target from legacy `<=8B` / `<=5 GB footprint` snapshots.
   - Status: first public-surface pass completed. Remaining `5 GB` / `8B` references in the main public docs are legacy snapshot or footprint language.

2. **Model lockfile and schema.**
   - Type: data + code.
   - Files: `data/models.lock.jsonl`, `data/model.schema.json`, `scripts/validate-model-lock.py`.
   - Acceptance: every model has `params_b`, tier, architecture, training type, quantization, artifact size, license/source/digest, included flag, and exclusion reason.
   - Status: implemented as a first lockfile. It validates all 158 roster tags, excludes 18 >5B rows, and currently leaves 140 included <=5B candidates, so the 150+ thesis universe is **not yet met**.

3. **README correction plan and rewrite.**
   - Type: documentation.
   - Files: `docs/README_UPDATE_PLAN.md`, `README.md`.
   - Acceptance: README opens with the corrected project definition and marks paper-era results as the current committed snapshot, not the final thesis protocol.

4. **Privacy/egress gate.**
   - Type: mixed.
   - Files: `docs/PRIVACY_AND_EGRESS.md`, `scripts/privacy-scan.py`.
   - Acceptance: a pre-share command reports known public hostnames/domains, blocks token patterns, and documents intentional disclosures.
   - Status: implemented as `scripts/privacy-scan.py` and `docs/PRIVACY_AND_EGRESS.md`.

### P1 - Must Fix Before Thesis/Paper Review

5. **Protocol document.**
   - Type: documentation.
   - Files: `docs/PROTOCOL.md`.
   - Acceptance: a reviewer can determine model eligibility, scenario version, prompt settings, repetitions, judging, missing-run policy, and statistics from one file.
   - Status: implemented as `docs/PROTOCOL.md`.

6. **Artifact inventory and audit command.**
   - Type: mixed.
   - Files: `docs/ARTIFACT_INVENTORY.md`, `scripts/audit-paper-data.py`, experiment commit policy.
   - Acceptance: one command validates snapshot files, summary numbers, scenario/model counts, generated site exports, and whether committed run artifacts include their `run.meta` contract.
   - Status: implemented as `docs/ARTIFACT_INVENTORY.md` and `scripts/audit-paper-data.py`.

7. **Judge validation plan.**
   - Type: documentation + data.
   - Files: `docs/JUDGE_VALIDATION.md`, `data/human_eval/*` or equivalent.
   - Acceptance: cross-judge agreement and human-vs-judge status are unambiguous; no human validation is implied before it exists.

8. **Statistics spec.**
   - Type: documentation + code later.
   - Files: `docs/STATISTICS.md`.
   - Acceptance: CIs, bootstrap units, effect sizes, paired comparisons, and Pareto robustness are specified.
   - Status: implemented as `docs/STATISTICS.md`; hardware and judge validation companion docs were also added.

### P2 - Should Improve

9. **Dashboard track badges.**
   - Type: UI/backend.
   - Files: `dashboard/*`, `data/run-matrix.json`.
   - Acceptance: runs are visibly `paper`, `dev`, `app`, `legacy`, or `thesis-target`.

10. **Scenario manifest.**
    - Type: data + validation.
    - Files: `data/scenario_manifest.json`, `scripts/validate-scenarios.py`.
    - Acceptance: scenario set count/hash/class mix/source/privacy status is machine-readable.

11. **Hardware profile artifact.**
    - Type: data + docs.
    - Files: `data/hardware-profile.home-ai.json`, `docs/HARDWARE.md`.
    - Acceptance: measured node and target class are no longer conflated.

### P3 - Polish

12. **Contributor model submission template.**
    - Type: docs.
    - Files: `CONTRIBUTING.md`, `.github/ISSUE_TEMPLATE/*`.
    - Acceptance: contributors submit model metadata in lockfile-compatible form.

## I. Recommended Repository Changes

Add or modify these files in order:

1. `docs/README_UPDATE_PLAN.md`
2. `data/model.schema.json`
3. `data/models.lock.jsonl`
4. `scripts/validate-model-lock.py`
5. `docs/PROTOCOL.md`
6. `docs/PRIVACY_AND_EGRESS.md`
7. `scripts/privacy-scan.py`
8. `docs/ARTIFACT_INVENTORY.md`
9. `scripts/audit-paper-data.py`
10. `docs/HARDWARE.md`
11. `data/hardware-profile.home-ai.json`
12. `docs/JUDGE_VALIDATION.md`
13. `docs/STATISTICS.md`

## J. Suggested Corrected README Structure

1. Project definition: <=5B-parameter local ops-model benchmark under CPU-only constraints.
2. Status: current committed snapshot versus doctoral target.
3. Research question.
4. What `<=5B` means; what GB means separately.
5. Hardware constraint and measured node.
6. Benchmark tracks: paper snapshot, thesis target, dev external candidates, app tasks.
7. Model tiers and eligibility.
8. Scenario corpus and scenario-set status.
9. Metrics: quality, safety, latency, memory, energy.
10. Reproducibility path.
11. Current results with snapshot scope.
12. Known limitations and open validation items.
13. Smoke test.
14. Full reproduction.
15. Citation and roadmap.

## K. Final Verdict

What is already strong: the harness, telemetry depth, run manifests, external dev
scenario gates, strict run-quality reporting, and the current two-node pipeline.

What is weak: the public research boundary, model eligibility metadata, privacy
gate, single-path protocol, and human validation status.

What to fix first: **do not run more broad experiments until the model universe is
re-locked around <=5B parameters.** The v1 external dev run is useful scenario-pack
learning, but it does not solve the doctoral-alignment problem.

Current suitability:

| Artifact role | Current status |
|---|---|
| Engineering prototype | Strong |
| Benchmark artifact | Promising but needs model lock/protocol |
| Paper artifact | Partial; snapshot-backed but public framing needs repair |
| Doctoral artifact | Not yet; P0 alignment work required |
| Public open-source tool | Useful to advanced users, but README claims need correction first |

## L. Immediate Next Phase

Start with `docs/README_UPDATE_PLAN.md` plus the model lock schema. The first
implementation phase should not rewrite every document at once. It should define
the canonical replacement language and make one validator fail if the thesis track
contains a model above 5B parameters.

Only after that gate exists should README, REVIEWER, CITATION, PAPER, and dashboard
copy be rewritten.