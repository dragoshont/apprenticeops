"""A5 — Judge validity (Zheng 2023 lens).

Uses the two independent judge streams (claude-opus-4.8, gpt-5.5) on the var batch:
* inter-judge agreement (Pearson/Spearman, exact/within-1, quadratic-weighted kappa);
* WHERE the judges disagree (scenarios, models = ambiguous outputs);
* verbosity bias: does output length inflate the judge score *beyond* correctness
  (partial correlation controlling det_score, within scenario)?
* judge vs deterministic correctness per scenario.
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score

from ceops_data import REPO, load_runs

J = REPO / ".tmp" / "judge"


def load_judge(path):
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            s = r.get("score")
            if s is None:
                continue
            rows.append((r["model"], r["scenario"], r["rep"], float(s)))
    return pd.DataFrame(rows, columns=["model", "scenario", "rep", "score"])


def output_tokens(path):
    tok = {}
    try:
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                k = (r.get("model"), r.get("scenario"), r.get("rep"))
                v = r.get("gen_ai.usage.output_tokens") or r.get("output_tokens")
                if v is not None:
                    tok[k] = float(v)
    except FileNotFoundError:
        pass
    return tok


def main() -> None:
    cl = load_judge(J / "judged.var.claude.jsonl").rename(columns={"score": "claude"})
    gp = load_judge(J / "judged.var.gpt55.jsonl").rename(columns={"score": "gpt"})
    m = cl.merge(gp, on=["model", "scenario", "rep"], how="inner")
    print(f"=== dual-judge overlap: {len(m)} judged items (var batch) ===")
    r = stats.pearsonr(m.claude, m.gpt)[0]
    rho = stats.spearmanr(m.claude, m.gpt)[0]
    exact = (m.claude.round() == m.gpt.round()).mean()
    within1 = (abs(m.claude - m.gpt) <= 1).mean()
    kq = cohen_kappa_score(m.claude.round().astype(int), m.gpt.round().astype(int), weights="quadratic")
    print(f"Pearson r={r:.3f}  Spearman={rho:.3f}  exact-agree={exact:.1%}  within-1={within1:.1%}  quadratic-kappa={kq:.3f}")
    print(f"mean |claude-gpt| = {abs(m.claude-m.gpt).mean():.3f}  (claude mean {m.claude.mean():.2f}, gpt mean {m.gpt.mean():.2f})")
    bias = m.claude.mean() - m.gpt.mean()
    print(f"systematic lenience: claude - gpt = {bias:+.3f} ({'claude more generous' if bias>0 else 'gpt more generous'})")

    # where they disagree: scenarios
    m["absdiff"] = abs(m.claude - m.gpt)
    sc = m.groupby("scenario")["absdiff"].mean().sort_values(ascending=False)
    print("\nscenarios with most judge disagreement:")
    print(sc.head(5).to_string(float_format=lambda x: f"{x:.2f}"))
    print("scenarios with least disagreement:")
    print(sc.tail(3).to_string(float_format=lambda x: f"{x:.2f}"))
    md = m.groupby("model")["absdiff"].mean().sort_values(ascending=False)
    print("\nmodels the judges most disagree on (ambiguous outputs):")
    print(md.head(5).to_string(float_format=lambda x: f"{x:.2f}"))

    # verbosity bias
    df = load_runs()
    var = df[df.collection_batch.eq("var")].copy()
    tok = output_tokens(J / "results.var.jsonl")
    var["out_tok"] = [tok.get((r.model, r.scenario, r.rep)) for r in var.itertuples()]
    v = var.dropna(subset=["out_tok", "judge_score", "det_score"])
    print(f"\n=== verbosity bias ({len(v)} items with output length) ===")
    r_len_q = stats.spearmanr(v.out_tok, v.judge_score)[0]
    r_len_d = stats.spearmanr(v.out_tok, v.det_score)[0]
    print(f"Spearman(length, judge_score)={r_len_q:.3f}   Spearman(length, det_score)={r_len_d:.3f}")
    # partial: within-scenario, does length predict judge beyond det? residualize both on scenario mean, then on det
    v["jz"] = v.groupby("scenario")["judge_score"].transform(lambda x: (x - x.mean()))
    v["lz"] = v.groupby("scenario")["out_tok"].transform(lambda x: (x - x.mean()) / (x.std() + 1e-9))
    v["dz"] = v.groupby("scenario")["det_score"].transform(lambda x: (x - x.mean()))
    # regress jz on dz + lz
    import numpy as np
    X = np.column_stack([np.ones(len(v)), v.dz, v.lz])
    beta, *_ = np.linalg.lstsq(X, v.jz, rcond=None)
    print(f"within-scenario judge_score ~ det + length(z):  b_det={beta[1]:+.3f}  b_length={beta[2]:+.3f}")
    print("  -> b_length>0 means the judge rewards longer answers even after controlling for correctness (verbosity bias)")

    # judge vs deterministic per scenario
    print("\n=== judge vs det correlation per scenario (low = judge & checks diverge) ===")
    perc = var.groupby("scenario").apply(lambda g: stats.spearmanr(g.judge_score, g.det_score)[0] if g.det_score.nunique()>1 else np.nan, include_groups=False).sort_values()
    print("lowest agreement (judge & deterministic checks diverge):")
    print(perc.head(5).to_string(float_format=lambda x: f"{x:.2f}"))

    m.to_csv(REPO / "deep-dive" / "out" / "a5_judge_pairs.csv", index=False)
    print("\nsaved a5_judge_pairs.csv")


if __name__ == "__main__":
    main()
