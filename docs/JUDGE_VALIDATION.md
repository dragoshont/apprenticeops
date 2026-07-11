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
figures and checks. Raw verdict rows for both batches are committed under
`data/raw/`; `scripts/export-judge-pairs.py --check` rebuilds all 8,909 complete
pairs and validates `data/snapshots/judge_pair_provenance.csv`. The sidecar keeps
batch, CPU, power, policy, and backend/model identity while explicitly marking
the historical condition identity incomplete.

The live CEOps dev path currently uses the headless Copilot CLI judge family that
is available outside the IDE, e.g. `claude-opus-4.6` and `gpt-5.4` in the v1
spread10 run. Treat judge-family/version changes as evaluation-policy metadata.
New judged rows persist the full requested ensemble as `evaluation_policy` before
calls begin. A failed family therefore leaves missing evidence, not a different
condition identity. Resume uses condition hash plus backend and model; hashless
historical rows are ignored unless the operator explicitly enables legacy resume.
Report, dataset, scheduler, run-quality, and snapshot paths retain that same
backend-plus-model identity. They do not publish a consensus score until every
requested family has produced a valid row.

## What Is Not Done

Human-vs-judge agreement is **not complete**. The correction-locked paper packet,
sampling policy, blind instructions, and agreement implementation are committed;
the human scores remain blank. The paper must not imply completed human
validation until a human fills all 50 rows and the agreement artifact passes.

## Minimum Human Validation Plan

Before thesis/paper review, define and commit:

1. a stratified sample of model/scenario/repetition answers;
2. blind human scoring instructions matching the 1-5 judge rubric;
3. at least two human raters or a documented single-rater limitation;
4. agreement metrics: human-human where possible, judge-human always;
5. a disagreement audit: where deterministic checks, judge, and human diverge.

Until then, all judge-quality claims should say **cross-judge robust, not yet
human-validated**.

## Prepared Packets

The claim-relevant frozen-paper packet is:

```text
data/human_eval/paper-94-model-corrected-v1/
```

It contains 50 deterministic, scenario-stratified items drawn only from the
8,909 complete locked judge pairs. Its key binds the `paper-94-model-corrected-v1`
manifest, `claude-opus-4.8` / `gpt-5.5` evaluation policy, scenario contract,
frozen result provenance, judge-pair export and its frozen provenance sidecar,
and both raw answer archives. The active doctoral lane uses a different
`claude-opus-4.6` / `gpt-5.4` policy and never shares this packet.

The separate development packet is:

```text
data/human_eval/external-v1-spread10-baseline-clean-20260703-164337/
```

It contains 45 items from the external-v1 run and its
`claude-opus-4.6` / `gpt-5.4` judges. It cannot close the frozen-paper gate.

Validate both packets with:

```bash
python3 scripts/validate-human-eval.py
```

To complete the single-rater paper gate, read only the paper packet's `sheet.md`,
fill every `human_score` in `scores.csv`, then run:

```bash
python3 human_eval.py score-packet \
	--packet data/human_eval/paper-94-model-corrected-v1
```

This writes `agreement.json` with fixed-scale unweighted and quadratic Cohen's
kappa, exact agreement, Spearman correlation, means, source hashes, and the
pre-registered $\kappa_{quad} \ge 0.6$ decision. The artifact records the
single-rater limitation. Do not open `key.json` before scoring.

## Optional Third Judge

The 2026-07-11 access smoke for `gemini-3.1-pro` returned "model is not
available" for the current Copilot account. No third-family rows were generated
and no evaluation policy changed. A Fleiss pass remains optional and blocked on
account model access; do not substitute another available model silently.