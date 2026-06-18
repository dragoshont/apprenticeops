#!/usr/bin/env python3
"""
judge_agreement.py — inter-judge agreement (Cohen's kappa) between two judge runs.

The quality numbers in the paper are graded by a single LLM judge
(`claude-opus-4.8`). A second, independent judge (`gpt-5.5`) scores the SAME
answers so we can report judge-to-judge agreement and show the ranking is not an
artifact of one grader. This script joins the two judged files on
(model, scenario, rep) and reports:

  - Cohen's kappa on the raw 1-5 scores (unweighted / linear / quadratic weights),
  - exact + within-1 agreement and Spearman rho,
  - a binarized kappa at a decision threshold (default: "good" = score >= 4),
  - the per-judge score distribution and mean (leniency check).

Stdlib only (no numpy/scipy) so it runs anywhere the harness does.

    python3 judge_agreement.py \
        --a .tmp/judge/judged.det.jsonl \
        --b .tmp/judge/judged.det.gpt55.jsonl

Interpretation (Landis & Koch): <0 poor, 0-.20 slight, .21-.40 fair,
.41-.60 moderate, .61-.80 substantial, .81-1 almost perfect. The pre-registered
bar for "the quality ranking is judge-robust" is kappa >= 0.6 (substantial).
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter


def load(path):
    """Map (model, scenario, rep) -> int score, skipping rows without a score."""
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            s = d.get("score")
            if s is None:
                continue
            try:
                s = int(round(float(s)))
            except (TypeError, ValueError):
                continue
            key = (d.get("model"), d.get("scenario"), str(d.get("rep")))
            out[key] = s
    return out


def _matrix(pairs, cats):
    """Confusion counts O[(i,j)] for rater-A score i, rater-B score j."""
    idx = {c: n for n, c in enumerate(cats)}
    k = len(cats)
    O = [[0] * k for _ in range(k)]
    for a, b in pairs:
        O[idx[a]][idx[b]] += 1
    return O, k


def cohen_kappa(pairs, cats, weight=None):
    """Cohen's kappa. weight in {None,'linear','quadratic'} (disagreement weights)."""
    O, k = _matrix(pairs, cats)
    n = sum(sum(row) for row in O)
    if n == 0:
        return None
    row_marg = [sum(O[i]) for i in range(k)]
    col_marg = [sum(O[i][j] for i in range(k)) for j in range(k)]

    def d(i, j):
        if weight is None:
            return 0.0 if i == j else 1.0
        if weight == "linear":
            return abs(i - j) / (k - 1)
        return ((i - j) ** 2) / ((k - 1) ** 2)  # quadratic

    num = sum(d(i, j) * O[i][j] for i in range(k) for j in range(k))
    den = sum(d(i, j) * row_marg[i] * col_marg[j] / n
              for i in range(k) for j in range(k))
    if den == 0:
        return 1.0  # no expected disagreement -> perfect by convention
    return 1.0 - num / den


def spearman(pairs):
    """Spearman rho via average-rank Pearson (stdlib)."""
    n = len(pairs)
    if n < 2:
        return None
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]

    def ranks(xs):
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(xs):
            j = i
            while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for t in range(i, j + 1):
                r[order[t]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    cov = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((x - mb) ** 2 for x in rb))
    return cov / (va * vb) if va and vb else None


def label(kp):
    if kp is None:
        return "n/a"
    for lo, name in [(0.81, "almost perfect"), (0.61, "substantial"),
                     (0.41, "moderate"), (0.21, "fair"), (0.0, "slight")]:
        if kp >= lo:
            return name
    return "poor"


def fleiss_kappa(ratings, cats):
    """Fleiss' kappa for >=3 raters. `ratings` is a list of per-item rating lists
    (one score per rater, every item rated by the SAME number of raters)."""
    idx = {c: n for n, c in enumerate(cats)}
    k = len(cats)
    N = len(ratings)
    if N == 0:
        return None
    n = len(ratings[0])
    if n < 2 or any(len(r) != n for r in ratings):
        return None  # Fleiss needs a fixed rater count per item
    # n_ij: count of raters assigning item i to category j
    counts = [[0] * k for _ in range(N)]
    for i, r in enumerate(ratings):
        for s in r:
            counts[i][idx[s]] += 1
    # per-item agreement P_i
    P = [(sum(c * c for c in counts[i]) - n) / (n * (n - 1)) for i in range(N)]
    Pbar = sum(P) / N
    # category marginals p_j
    pj = [sum(counts[i][j] for i in range(N)) / (N * n) for j in range(k)]
    Pe = sum(p * p for p in pj)
    if Pe >= 1.0:
        return 1.0
    return (Pbar - Pe) / (1 - Pe)


def _nick(path):
    """Short judge name from a judged-file path (…judged.det.gpt55.jsonl -> gpt55)."""
    base = os.path.basename(path).replace(".jsonl", "")
    for pre in ("judged.det.", "judged."):
        if base.startswith(pre):
            tail = base[len(pre):]
            return tail or "claude"
    return base


def multi_rater_report(named):
    """named: list of (name, {key->score}). Prints all pairwise quadratic kappas,
    Fleiss' kappa over the common items, and median-of-N self-agreement."""
    names = [n for n, _ in named]
    common = set(named[0][1])
    for _, d in named[1:]:
        common &= set(d)
    common = sorted(common)
    print(f"\n# Multi-judge agreement  ({len(names)} judges: {', '.join(names)})")
    print(f"  items rated by ALL judges: {len(common)}\n")
    if not common:
        print("  no items shared by all judges yet.")
        return
    # pairwise quadratic-weighted kappa
    for i in range(len(named)):
        for j in range(i + 1, len(named)):
            (na, da), (nb, db) = named[i], named[j]
            pairs = [(da[k], db[k]) for k in common]
            cats = sorted(set(s for p in pairs for s in p))
            kq = cohen_kappa(pairs, cats, "quadratic")
            print(f"  {na:>8} <-> {nb:<8} kappa_quad = {kq:+.3f}  [{label(kq)}]")
    # Fleiss over all raters
    ratings = [[d[k] for _, d in named] for k in common]
    cats = sorted(set(s for r in ratings for s in r))
    fk = fleiss_kappa(ratings, cats)
    print(f"\n  Fleiss' kappa (all {len(names)} judges) = {fk:+.3f}  [{label(fk)}]")
    # how often the judges split 3 ways / agree exactly
    import statistics as _st
    exact = sum(1 for r in ratings if len(set(r)) == 1) / len(ratings)
    print(f"  all-judges-exact-agree: {exact:.0%}   "
          f"(median-of-{len(names)} is the robust combined score)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default=".tmp/judge/judged.det.jsonl",
                    help="judge A jsonl (default: claude)")
    ap.add_argument("--b", default=".tmp/judge/judged.det.gpt55.jsonl",
                    help="judge B jsonl (default: gpt-5.5)")
    ap.add_argument("--c", default="",
                    help="optional judge C jsonl (e.g. gemini) -> adds Fleiss' kappa")
    ap.add_argument("--good", type=int, default=4,
                    help="binarize threshold: score >= this counts as 'good' (default 4)")
    args = ap.parse_args()

    A, B = load(args.a), load(args.b)
    keys = sorted(set(A) & set(B))
    pairs = [(A[k], B[k]) for k in keys]
    if not pairs:
        print(f"no overlapping judged rows ( A={len(A)}  B={len(B)} ).")
        return

    cats = sorted(set(s for p in pairs for s in p))
    n = len(pairs)
    exact = sum(1 for a, b in pairs if a == b) / n
    within1 = sum(1 for a, b in pairs if abs(a - b) <= 1) / n
    mad = sum(abs(a - b) for a, b in pairs) / n
    ka = cohen_kappa(pairs, cats)
    kl = cohen_kappa(pairs, cats, "linear")
    kq = cohen_kappa(pairs, cats, "quadratic")
    rho = spearman(pairs)

    bin_pairs = [(int(a >= args.good), int(b >= args.good)) for a, b in pairs]
    kbin = cohen_kappa(bin_pairs, [0, 1])

    print(f"# Inter-judge agreement")
    print(f"  A = {args.a}   (n={len(A)})")
    print(f"  B = {args.b}   (n={len(B)})")
    print(f"  joined on (model, scenario, rep): {n} pairs "
          f"({len(A) - n} A-only, {len(B) - n} B-only)\n")
    print(f"  Cohen's kappa (unweighted) : {ka:+.3f}  [{label(ka)}]")
    print(f"  Cohen's kappa (linear wt)  : {kl:+.3f}  [{label(kl)}]")
    print(f"  Cohen's kappa (quadratic)  : {kq:+.3f}  [{label(kq)}]  <- ordinal scores")
    print(f"  kappa (binary, score>={args.good}) : {kbin:+.3f}  [{label(kbin)}]")
    print(f"  exact agreement            : {exact:6.1%}")
    print(f"  within-1 agreement         : {within1:6.1%}")
    print(f"  Spearman rho               : {rho:+.3f}" if rho is not None else "")
    print(f"  mean abs score diff        : {mad:.2f}\n")
    da = Counter(a for a, _ in pairs)
    db = Counter(b for _, b in pairs)
    mean_a = sum(a for a, _ in pairs) / n
    mean_b = sum(b for _, b in pairs) / n
    print(f"  score dist A: {{{', '.join(f'{s}:{da[s]}' for s in cats)}}}  mean={mean_a:.2f}")
    print(f"  score dist B: {{{', '.join(f'{s}:{db[s]}' for s in cats)}}}  mean={mean_b:.2f}")
    print(f"\n  verdict: quadratic-weighted kappa = {kq:+.3f} "
          f"({'>=' if kq >= 0.6 else '<'} 0.60 bar -> "
          f"{'ranking is judge-robust' if kq >= 0.6 else 'judge-sensitive; report as single-judge'}).")

    # third judge present -> full multi-rater report (pairwise + Fleiss)
    if args.c and os.path.exists(args.c):
        C = load(args.c)
        multi_rater_report([(_nick(args.a), A), (_nick(args.b), B), (_nick(args.c), C)])


if __name__ == "__main__":
    main()
