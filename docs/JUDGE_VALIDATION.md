# Judge Validation

Status: active validation note, created 2026-07-03.

## Boundary

The system-under-test is the local model. The judge is eval-time scaffolding.
Judge egress must be disclosed, but it does not violate the local-inference claim.

## What Is Done

The paper-era quality axis uses a two-judge ensemble in the committed analysis
exports. `data/site/summary.json` reports:

- `quality_axis`: `5-rep x 2-judge ensemble (claude-opus-4.8 + gpt-5.5)`
- `cross_judge_kappa_quad`: `0.906`

`data/site/judge_pairs.csv` is the committed pair export used for judge-agreement
figures and checks.

The live CEOps dev path currently uses the headless Copilot CLI judge family that
is available outside the IDE, e.g. `claude-opus-4.6` and `gpt-5.4` in the v1
spread10 run. Treat judge-family/version changes as evaluation-policy metadata.

## What Is Not Done

Human-vs-judge agreement is **not complete**. The repo has `human_eval.py`, but
the doctoral paper must not imply a completed human validation set until rows,
sampling policy, adjudication instructions, and agreement metrics are committed.

## Minimum Human Validation Plan

Before thesis/paper review, define and commit:

1. a stratified sample of model/scenario/repetition answers;
2. blind human scoring instructions matching the 1-5 judge rubric;
3. at least two human raters or a documented single-rater limitation;
4. agreement metrics: human-human where possible, judge-human always;
5. a disagreement audit: where deterministic checks, judge, and human diverge.

Until then, all judge-quality claims should say **cross-judge robust, not yet
human-validated**.