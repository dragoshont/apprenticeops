# CEOps Metrics and Source Analysis

Status: source-backed analysis, created 2026-07-03. This document reviews the
new AIOps/DevOps source map against current CEOps / ApprenticeOps metrics and
turns it into concrete improvement work. It is **not** a new benchmark result,
not a Core promotion, not judge calibration, and not a training/RAG plan.

## Executive Verdict

The current CEOps direction is sound: **deployment-centric evaluation** is the
right category, and the valuable contribution is measuring quality, safety,
reliability, latency, energy, and hardware fit together. The online sources do
not argue for adding more rows immediately. They argue for improving the shape of
our scenarios and reports:

1. **AIOpsLab / ITBench teach lifecycle structure.** A scenario should expose the
   operational object, task, fault, workload/evidence, permitted actions, and
   evaluator. Current scenarios often contain these implicitly; future scenario
   schemas should make them explicit.
2. **Nezha / DeepTraLog teach multimodal evidence.** Better RCA scenarios combine
   logs, metrics, traces, and labels. Current `external-candidates-v0` is mostly
   text-summary based; that is acceptable for v0, but it is the next quality gap.
3. **IBM Cloud / Google / Azure / Alibaba traces teach telemetry discipline.**
   These are not good prose-QA scenario rows. They are evidence for deployment
   profiles, anomaly windows, workload shape, hardware/energy claims, and future
   telemetry schemas.
4. **Loghub and public Q&A corpora teach surface realism, with privacy risk.**
   They are useful for adversarial fixtures and log surface forms, but row-level
   use requires a rights/privacy gate.
5. **The spread10 dev run shows the pack is discriminative but not promotion-ready.**
   `ext-secure-08`, `ext-guard-04`, `ext-detect-01`, and `ext-tooluse-07` deserve
   qualitative repair before any broader run or promotion decision.

## Source Lessons

| Source family | What it measures well | Lesson for CEOps | Safe use now |
|---|---|---|---|
| AIOpsLab | Interactive agent lifecycle: app, task, fault, workload, telemetry, evaluator; leaderboard accuracy/time. | Add lifecycle metadata to scenarios and dashboards; compare as complementary, not competing. | Related-work positioning and scenario-quality checklist. |
| ITBench | Real-world IT automation tasks across SRE/CISO/FinOps; low frontier solve rates. | Keep ApprenticeOps honest: local small models are apprentice-level, not autonomous operators. | Related-work positioning and class coverage sanity check. |
| OpsEval | Large MCQ/QA IT-ops benchmark. | Breadth alone is weak; avoid turning ApprenticeOps into generic Q&A. | Positioning warning, not a source for Core. |
| IBM Cloud telemetry | Real cloud anomaly telemetry, anomaly windows, high-dimensional intervals. | Add anomaly-window and incident-window concepts to future telemetry/result schema. | Telemetry/spec framing; no raw import. |
| Nezha / DeepTraLog | Multimodal RCA using logs, metrics, traces, and root-cause labels. | Future hard scenarios should provide multiple evidence channels, not only prose summaries. | Pattern/lifecycle design after rights review. |
| OpenStack failure dataset | Injected faults, workload, user-visible effects, correctness checks, and logs. | Strong candidate for next scenario-design source because it has fault/effect/evaluator shape. | Source-quality scan after rights/source hash gate. |
| Loghub | Realistic log surfaces, some labels, many systems. | Useful for making logs feel real and for adversarial fixtures; privacy risk is high. | Pattern-only after rights/privacy review. |
| Google/Azure/Alibaba traces | Workload, resource, power, cloud trace scale. | Supports hardware profiles, workload profiles, and deployment-centric telemetry claims. | Methods/positioning and future systems schemas. |
| UCR/Yahoo/NAB | Time-series anomaly benchmarks. | Useful baseline vocabulary for anomaly scoring; not enough for ops-answer quality. | Metric vocabulary only. |

## Metrics Verdict

| Metric / signal | Current state | Value | Verdict |
|---|---|---|---|
| `judge_score` / mean judge score | Used in paper and dev runs. | Good for open-ended answer quality when paired with evidence and cross-judge agreement. | **Keep, but gate.** Never interpret if judge duplicate/gap counts are non-zero. |
| `det_score` / deterministic checks | Used in all scenarios. | Strong for exact facts, JSON shape, and safety disqualifiers; necessary-not-sufficient. | **Keep and strengthen.** Add adversarial fixture tests for new scenarios. |
| DNF / stall / zero-output / length | Reported by `report-run-quality.py`. | Separates reliability from quality; prevents selection-by-survivorship. | **Elevate.** Show beside every quality table and dashboard result. |
| Judge duplicate tuples | Added after dryrun duplicate. | Critical integrity signal; raw judged row count can be misleading. | **Promote to mandatory gate.** Already implemented in reporter/tests. |
| Judge evidence / criteria gaps | Reported. | Catches empty or low-quality judge outputs. | **Mandatory gate.** Any non-zero count blocks interpretation. |
| TTFT, prefill/decode tok/s, wall time | Captured per row. | Core deployment UX/cost metric; aligns with AIOpsLab TIME but is more granular. | **Keep and summarize.** Add p50/p95 by model/scenario for dev packs. |
| Inter-token jitter | Captured. | Useful for product UX, less important for paper headline. | **Keep raw; summarize only when UX matters.** |
| Energy Wh/answer, tok/s-per-watt | Paper headline axis. | Differentiates deployment choice; supported by systems datasets and MLPerf-style energy thinking. | **Keep as core contribution.** |
| RAPL subdomains / DRAM power / IMC bandwidth | Captured. | Explains bottlenecks and hardware transfer; too detailed for casual dashboard. | **Keep raw; aggregate for roofline/bottleneck analysis.** |
| RSS / swap / faults / memory pressure | Captured. | Hard deployment-fit metric, especially on small hardware. | **Keep and expose as fit gate.** |
| CPU microarchitecture (`perf.core`) | Captured when available. | Valuable for diagnosing memory-bound decode; noisy and platform-specific. | **Keep raw; do not require for all submissions.** |
| Network/disk I/O | Captured. | Network near-zero supports offline claim; disk helps detect paging/caching. | **Keep as invariants.** Expose egress warnings. |
| `strategy.*`, `env.memory_context`, `prompt.*`, `effective.*` | Captured in current runs. | Essential for deployment identity; prevents memory/strategy confounding. | **Promote to deployment schema.** |
| Judge token usage | Often zero/null with current Copilot backend. | Potential cost metric, but currently incomplete. | **Keep field, do not rely on it until backend reports real usage.** |
| Full `samples[]` time series | Captured. | Research-grade telemetry; heavy. | **Keep as artifact, summarize in reports.** |

## CEOps Improvement Backlog

### 1. Scenario lifecycle schema

Add optional metadata fields to future scenario/candidate files:

```text
operational_object   # app/service/component under evaluation
task_lifecycle       # detect | localize | analyze | mitigate | verify
fault_model          # misconfig | dependency | capacity | security | agent-failure | etc.
workload_evidence    # logs | metrics | traces | events | config | user-impact | synthetic summary
action_surface       # prose-only | json-tool-plan | kubectl | gitops-plan | destructive-risk
evaluator_shape      # deterministic checks | judge rubric | runtime validator | human review
promotion_status     # candidate | dev | locked-core | retired
source_trace         # source families and row/hash status
```

This is the most direct lesson from AIOpsLab and OpenStack failure data. It does
not require changing existing paper scenarios immediately; add it first to future
candidate sets or a v1 schema.

### 2. Scenario-level error review as a standard artifact

`docs/EXTERNAL_DATASET_PHASE5_SPREAD10_REVIEW.md` should become a template:

- gate summary;
- model means;
- scenario means;
- low-score themes;
- promotion verdict;
- next repair actions.

Do this for every dev scenario pack before a broader run. It is cheaper than
blindly adding models.

### 3. Run-quality report hardening

Already done: judge duplicate tuples are now reported and tested. Next useful
additions:

- optional non-zero exit when `--strict` and any structural gate fails;
- per-scenario reliability table;
- per-scenario judge mean and deterministic mean table;
- `report-run-quality.py --markdown` for review docs;
- explicit `interpretation_ok` boolean in JSON output.

### 4. Dashboard / mission-control improvements

The dashboard should eventually surface:

- scenario set `kind` (`default`, `pilot`, `dev`, `app`) as a visible badge;
- run-quality gate status: inference rows, judge tuples, duplicate judge rows,
  DNF, zero-output, length, evidence/criteria gaps, push-pending;
- per-scenario heatmap for dev packs;
- a “not paper scoring” warning for `kind=dev` scenario sets;
- link to the review doc for completed dev runs.

This is product/ops clarity, not paper-critical.

### 5. Metrics extraction for Architrave Eval

When extracting Architrave Eval / CEOps, define the deployment object explicitly:

```text
deployment = model + runtime + hardware_profile + quantization + prompt_policy
           + memory_context + inference_strategy + evaluation_policy
```

Minimum schemas should cover:

- `deployment.schema.json`
- `scenario-pack.schema.json`
- `hardware-profile.schema.json`
- `result-row.schema.json`
- `run-quality-report.schema.json`
- `evaluation-policy.schema.json`

Do not build a large SDK before these schemas are stable.

## Source-Driven Scenario Repair Priorities

| Current scenario | Spread10 signal | Source lesson | Recommended action |
|---|---|---|---|
| `ext-secure-08-agent-secret-in-logs` | Lowest overall, max only 2.1. | Loghub/security logs show real log surfaces are messy; secret hygiene needs output-storage safety. | Split into two: incident summary with redaction, and logging-policy remediation. Add stronger deterministic ban on partial sentinel/header echoes. |
| `ext-guard-04-agent-runaway-tool-loop` | Low overall, but discriminative. | AIOpsLab agent lifecycle and Owner-Harm-style deployer harm imply agent-run failure is a first-class ops incident. | Keep hard; clarify classification vs remediation; add contrast case where repeated tool calls are justified by new evidence. |
| `ext-detect-01-log-baseline-shift` | Low-mid; many models miss root cause/action. | IBM/UCR anomaly data emphasize baseline/window reasoning. | Add explicit baseline-window language and require provider/dependency action; consider a paired variant with a false-positive baseline shift. |
| `ext-tooluse-07-sre-readonly-json-plan` | Strong for top model, low for several. | AIOpsLab evaluator/action interface requires executable actions, not just prose. | Keep as structured action gate; add validator-friendly alternate allowed tail values/order if needed. |
| `ext-monitor-05-zero-output-timeout-policy` | Moderate but harness-internal. | CEOps reliability is a genuine deployment metric, but not ordinary AIOps. | Keep in CEOps/Architrave Eval pack; do not promote to generic ops Core without reframing. |

## Near-Term Recommendation

Do **not** start another external-candidate model run now. The best next work is:

1. Add `--strict` and `--markdown` modes to `report-run-quality.py`.
2. Draft a v1 scenario lifecycle schema for future candidate packs.
3. Repair or split the four low-scoring scenarios listed above.
4. Only then consider a new dev run or a candidate-v1 scenario set.

This sequence converts the online-source research into better evaluation quality
instead of just a larger table.