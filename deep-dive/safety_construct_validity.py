"""Construct-validity decomposition of the "safety" metric + a corrected R1 contrast.

WHY THIS EXISTS (adversarial review, 2026-07-25, Claude Opus 5): the metric reported as
"deterministic destructive-action refusal" is `det_score` = the MEAN OF ALL deterministic
checks in a scenario. Inspecting the guard/secure scenarios shows those checks are of two
different kinds:

  * `any_include`      -> did the answer MENTION the right domain content? = CONTENT RECALL
                          (a capability/comprehension measure)
  * `must_exclude` /
    `must_not_endorse` -> did the answer AVOID endorsing the dangerous action? = ACTION SAFETY
                          (the thing the paper actually claims to measure)

`secure-09` is 4/4 `any_include` (NO action-safety check at all); `guard-08` is 3 recall + 1
action-safety. So the published "safety" number is mostly recall, which (a) mechanically
inflates the safety~quality correlation (part-whole overlap: recall IS capability) and
(b) is confounded by silence: an EMPTY answer fails every `any_include` but VACUOUSLY PASSES
every `must_exclude`, so a model that says nothing scores partial "safety".

This script decomposes the two and re-runs the finding-27 R1 contrast on the corrected
metric, with the pseudoreplication fixed (the three DeepSeek-R1-Distill-Qwen-1.5B tags are
ONE checkpoint at three quantizations -- identical param_count 1,777,088,000 -- so they are
collapsed to a single lineage unit per AGENTS lesson 5), and with the finding-26c
empty-output exclusion applied SYMMETRICALLY (deepseek-r1:7b completes only 29%).

Read-only. Run: ./deep-dive/.venv/bin/python deep-dive/safety_construct_validity.py
"""
from __future__ import annotations

import gzip
import json
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

import full_data

HERE = pathlib.Path(__file__).resolve().parent
R1_RAW = HERE / "r1-extension" / "results.r1ext.jsonl"
SAFETY_CHECKS = {"must_exclude", "must_not_endorse"}   # true action-safety
RECALL_CHECKS = {"any_include", "all_include", "must_include"}  # content recall
# The three tags below are ONE checkpoint (DeepSeek-R1-Distill-Qwen-1.5B) at 3 quants.
R1_LINEAGE = {
    "deepseek-r1:1.5b",
    "deepseek-r1:1.5b-qwen-distill-q8_0",
    "hf.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF:Q4_K_M",
}


def _decompose(rows) -> pd.DataFrame:
    """Split det_detail into action-safety vs content-recall pass rates per cell."""
    out = []
    for r in rows:
        det = r.get("det_detail") or []
        saf = [c for c in det if c.get("type") in SAFETY_CHECKS]
        rec = [c for c in det if c.get("type") in RECALL_CHECKS]
        out.append({
            "model": r["model"], "scenario": r["scenario"], "rep": int(r["rep"]),
            "det_score": r.get("det_score"),
            "action_safety": (np.mean([bool(c["pass"]) for c in saf]) if saf else np.nan),
            "content_recall": (np.mean([bool(c["pass"]) for c in rec]) if rec else np.nan),
            "n_safety_checks": len(saf), "n_recall_checks": len(rec),
            "dnf": bool(r.get("dnf")),
            "output_tokens": r.get("gen_ai.usage.output_tokens"),
            "output_chars": r.get("gen_ai.usage.output_chars"),
        })
    return pd.DataFrame(out)


def _iter_gz(path):
    with gzip.open(path, "rt") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _iter_jsonl(path):
    with open(path) as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> None:
    full = full_data.load_full()
    smap = full.groupby("scenario")["is_safety"].first()

    print("=== CONSTRUCT VALIDITY OF THE 'SAFETY' METRIC ===")
    print("det_score = mean of ALL checks. Decomposing into ACTION-SAFETY "
          "(must_exclude/must_not_endorse) vs CONTENT-RECALL (any_include).\n")

    # ---------- 152 corpus ----------
    src = full_data.LOCKED / "canonical" / "results.jsonl.gz"
    d152 = _decompose(_iter_gz(src))
    d152["is_safety"] = d152["scenario"].map(smap).fillna(False)
    s152 = d152[d152["is_safety"]]

    print("--- check composition on the 4 'safety' scenarios ---")
    comp = s152.groupby("scenario").agg(safety_checks=("n_safety_checks", "first"),
                                        recall_checks=("n_recall_checks", "first")).reset_index()
    comp["recall_share_of_det_score"] = (comp.recall_checks /
                                         (comp.recall_checks + comp.safety_checks)).round(2)
    print(comp.to_string(index=False))
    print(f"\n=> {comp.recall_share_of_det_score.mean():.0%} of the reported 'safety' score is "
          "CONTENT RECALL, not action safety.")

    # A. does silence inflate action-safety?
    print("\n--- A. does SILENCE score as safety? (empty/short answers) ---")
    s = s152.dropna(subset=["action_safety"]).copy()
    s["tok"] = pd.to_numeric(s["output_tokens"], errors="coerce")
    q = s.dropna(subset=["tok"])
    lo = q[q.tok <= q.tok.quantile(0.10)]
    hi = q[q.tok >= q.tok.quantile(0.90)]
    print(f"  shortest 10% of answers: action_safety={lo.action_safety.mean():.3f}  "
          f"content_recall={lo.content_recall.mean():.3f}  (n={len(lo)})")
    print(f"  longest  10% of answers: action_safety={hi.action_safety.mean():.3f}  "
          f"content_recall={hi.content_recall.mean():.3f}  (n={len(hi)})")
    dnf = s[s.dnf]
    if len(dnf):
        print(f"  DNF cells (no answer at all): action_safety={dnf.action_safety.mean():.3f} "
              f"content_recall={dnf.content_recall.mean():.3f} (n={len(dnf)})  "
              "<- vacuous passes")

    # B. discriminant validity at model level
    print("\n--- B. DISCRIMINANT VALIDITY (model level, n=152) ---")
    mt = (s152.groupby("model").agg(action_safety=("action_safety", "mean"),
                                    content_recall=("content_recall", "mean"),
                                    det_score=("det_score", "mean")).reset_index())
    qual = full.groupby("model")["judge_score"].mean().rename("quality")
    toks = full.groupby("model")["output_tokens"].median().rename("med_tokens")
    comp_rate = (1 - full.groupby("model")["dnf_bool"].mean()).rename("complete")
    mt = mt.merge(qual, on="model").merge(toks, on="model").merge(comp_rate, on="model")
    r_rec = stats.pearsonr(mt.action_safety, mt.content_recall)
    r_q_det = stats.pearsonr(mt.det_score, mt.quality)
    r_q_act = stats.pearsonr(mt.action_safety, mt.quality)
    r_q_rec = stats.pearsonr(mt.content_recall, mt.quality)
    print(f"  r(action_safety, content_recall) = {r_rec[0]:+.3f}")
    print(f"  r(det_score      , quality)      = {r_q_det[0]:+.3f}   <- the reported ~0.9 collinearity")
    print(f"  r(content_recall , quality)      = {r_q_rec[0]:+.3f}   <- recall IS capability (part-whole)")
    print(f"  r(action_safety  , quality)      = {r_q_act[0]:+.3f}   <- the HONEST safety-quality relation")

    # partial correlation of action_safety with quality controlling tokens + completion
    def _partial(y, x, ctrls):
        X = np.column_stack([np.ones(len(mt))] + [mt[c].values for c in ctrls])
        ry = mt[y].values - X @ np.linalg.lstsq(X, mt[y].values, rcond=None)[0]
        rx = mt[x].values - X @ np.linalg.lstsq(X, mt[x].values, rcond=None)[0]
        return stats.pearsonr(ry, rx)[0]

    mt["log_tok"] = np.log1p(pd.to_numeric(mt.med_tokens, errors="coerce").fillna(0))
    pr = _partial("action_safety", "quality", ["log_tok", "complete"])
    print(f"  partial r(action_safety, quality | log tokens, completion) = {pr:+.3f}")
    print("  => if this collapses toward 0, the 'safety axis' has little independent variance.")

    # ---------- corrected R1 contrast ----------
    print("\n=== CORRECTED finding-27 CONTRAST (fixes 3 defects) ===")
    print("  (1) uses ACTION-SAFETY only, not det_score")
    print("  (2) collapses the 3 identical-checkpoint R1 tags to ONE lineage unit (lesson 5)")
    print("  (3) applies the 26c empty-output exclusion SYMMETRICALLY "
          "(drops deepseek-r1:7b @29% completion)\n")
    r1 = _decompose(_iter_jsonl(R1_RAW))
    r1["is_safety"] = r1["scenario"].map(smap).fillna(False)
    s_r1 = r1[r1["is_safety"] & r1["model"].isin(R1_LINEAGE)]
    a_r1 = s_r1["action_safety"].mean()
    n_cells = len(s_r1)

    inst = full[(full.is_reasoning == False)].model.unique()          # noqa: E712
    reas = full[(full.is_reasoning == True)].model.unique()           # noqa: E712
    a_inst = mt[mt.model.isin(inst)]["action_safety"]
    a_reas = mt[mt.model.isin(reas)]["action_safety"]

    # Wilson interval on the pooled cells of the single R1 checkpoint
    k = int(round(a_r1 * n_cells)); n = n_cells
    z = 1.96; p = k / n; den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    print(f"  R1-Distill-Qwen-1.5B  (1 checkpoint, 3 quants, {n} safety cells): "
          f"action_safety={a_r1:.3f}  Wilson95=[{ctr-half:.3f},{ctr+half:.3f}]")
    print(f"  152 instruct/base  (n={len(a_inst)} models): mean={a_inst.mean():.3f}  "
          f"median={a_inst.median():.3f}  p10={a_inst.quantile(.1):.3f}  p90={a_inst.quantile(.9):.3f}")
    print(f"  152 reasoning      (n={len(a_reas)} models): mean={a_reas.mean():.3f}")
    pct = 100 * (a_inst < a_r1).mean()
    print(f"  => the R1 checkpoint sits at the {pct:.0f}th percentile of instruct models "
          f"on ACTION SAFETY")
    print("  NOTE: n=1 checkpoint. This is a CASE STUDY, not a population estimate.")

    out = HERE / "out" / "safety_construct_validity.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    mt.to_csv(out, index=False)
    print(f"\nsaved {out.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
