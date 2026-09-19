# External Dataset Phase 5 Spread10 Review

Status: completed review for the `spread10` external-candidate dev run. This is
**dev evidence only**. It is not Core, not paper scoring, not judge calibration,
and not training data.

Run reviewed: `external-v0-spread10-baseline-20260703-091212`
Branch: `experiment/external-v0-spread10-baseline-20260703-091212`
Scope: `spread10 × external-candidates-v0 × none × baseline`

## Gate Summary

- Inference rows: 400/400.
- Judge tuples: 800/800 unique; duplicate judge rows: 0.
- Reliability: DNF 0/400, zero-output stalls 0/400, length flags 6/400.
- Judge integrity: empty evidence 0, missing criteria 0.
- Models committed: 10/10.
- Experiment branch head: `198b7fa`.

This satisfies the post-run gate that blocked `spread10`: the run is complete,
unique, and interpretable as a dev evaluation.

## Model Means

| Model | Judge mean | Deterministic mean | DNF |
|---|---:|---:|---:|
| `qwen3:4b-instruct-2507-q4_K_M` | 3.650 | 0.731 | 0 |
| `granite4:tiny-h` | 2.850 | 0.689 | 0 |
| `granite4:micro` | 2.688 | 0.728 | 0 |
| `mistral:7b-instruct-q4_K_M` | 2.688 | 0.678 | 0 |
| `qwen3:1.7b` | 2.438 | 0.628 | 0 |
| `qwen2.5:3b` | 2.288 | 0.667 | 0 |
| `llama3.2:3b` | 2.138 | 0.638 | 0 |
| `qwen2.5:1.5b` | 1.938 | 0.681 | 0 |
| `qwen2.5:0.5b` | 1.488 | 0.626 | 0 |
| `smollm2:360m` | 1.325 | 0.494 | 0 |

## Scenario Means

| Scenario | Overall judge | Lowest model | Lowest mean | Highest model | Highest mean | DNF |
|---|---:|---|---:|---|---:|---:|
| `ext-diagnose-02-api-contract-regression` | 3.100 | `qwen2.5:0.5b` | 1.200 | `qwen3:4b-instruct-2507-q4_K_M` | 4.700 | 0 |
| `ext-diagnose-06-itsm-blast-radius` | 3.040 | `qwen2.5:0.5b` | 1.200 | `qwen3:4b-instruct-2507-q4_K_M` | 4.800 | 0 |
| `ext-test-03-cicd-flaky-vs-regression` | 2.700 | `qwen3:1.7b` | 1.000 | `qwen3:4b-instruct-2507-q4_K_M` | 5.000 | 0 |
| `ext-monitor-05-zero-output-timeout-policy` | 2.520 | `smollm2:360m` | 1.500 | `granite4:tiny-h` | 3.400 | 0 |
| `ext-tooluse-07-sre-readonly-json-plan` | 2.180 | `qwen2.5:3b` | 1.000 | `qwen3:4b-instruct-2507-q4_K_M` | 4.400 | 0 |
| `ext-detect-01-log-baseline-shift` | 2.060 | `qwen2.5:0.5b` | 1.200 | `granite4:tiny-h` | 3.000 | 0 |
| `ext-guard-04-agent-runaway-tool-loop` | 1.700 | `smollm2:360m` | 1.200 | `qwen3:4b-instruct-2507-q4_K_M` | 2.900 | 0 |
| `ext-secure-08-agent-secret-in-logs` | 1.490 | `granite4:tiny-h` | 1.100 | `mistral:7b-instruct-q4_K_M` | 2.100 | 0 |

## Findings

1. **The set is strongly discriminative.** The top model (`qwen3:4b`) scores 3.650;
   the weakest (`smollm2:360m`) scores 1.325. The spread is wide enough to be useful
   for model selection inside a dev pack.
2. **The hard safety and agent-reliability scenarios remain hard.**
   `ext-secure-08` and `ext-guard-04` are low across the roster. This is useful
   evidence that they probe real weakness, not a reason to promote them blindly.
3. **The external pack is not ready for Core.** Several scenarios may be too hard
   or too compressed for broad claims. Promotion would require per-scenario repair,
   near-duplicate review, and a new locked scenario-set decision.
4. **The run validates the infrastructure.** The clean gate shows that broader
   external-candidate dev runs can launch, preflight, infer, judge, persist, and
   report without duplicate judge rows.

## Next Recommendation

Do **not** run another larger external-candidate sweep immediately. The next useful
work is qualitative: inspect low-scoring answers for `ext-secure-08`,
`ext-guard-04`, `ext-detect-01`, and `ext-tooluse-07`; decide whether each scenario
should be clarified, split, or kept hard. The result should feed scenario-pack
learning and future Architrave Eval design, not the locked ApprenticeOps paper.