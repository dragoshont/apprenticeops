#!/usr/bin/env python3
"""
human_eval.py — blind human scoring sheet + human<->judge agreement.

The LLM judges (claude-opus-4.8, gpt-5.5, ...) agree with each other, but they may
share a bias a human catches. This builds a BLIND, stratified sample for a human
to score against the SAME inputs the LLM judge saw (context, task, gold, rubric,
answer) — model identity and the LLM scores are hidden — then computes
human<->judge Cohen's kappa. This is the judge-validation the paper still owes
(PAPER.md §9: "no judge-human kappa yet").

    # 1. generate a 50-row blind sheet stratified by task class
    python3 human_eval.py make --n 50

    # 2. score .tmp/human_eval/scores.csv by hand (fill the human_score column 1-5)

    # 3. compute agreement vs every LLM judge
    python3 human_eval.py score

Stdlib only; reuses the kappa math in judge_agreement.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random

from judge_agreement import cohen_kappa, label, spearman

OUT_DIR = ".tmp/human_eval"
JUDGES = {  # name -> judged jsonl (any that exist are folded into the key)
    "claude": ".tmp/judge/judged.det.jsonl",
    "gpt55": ".tmp/judge/judged.det.gpt55.jsonl",
    "gemini": ".tmp/judge/judged.det.gemini.jsonl",
}


def _answer_path(outputs_dir, model, scenario, rep, repeats_gt1=False):
    stem = model.replace("/", "_").replace(":", "_")
    suffix = f"__r{rep}" if repeats_gt1 else ""
    return os.path.join(outputs_dir, f"{stem}__{scenario}{suffix}.txt")


def _load_judge(path):
    """(model, scenario, rep) -> int score."""
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path):
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
            out[(d.get("model"), d.get("scenario"), str(d.get("rep")))] = int(round(float(s)))
        except (TypeError, ValueError):
            continue
    return out


def cmd_make(args):
    scen = {s["id"]: s for s in json.load(open(args.scenarios))["scenarios"]}
    judges = {name: _load_judge(p) for name, p in JUDGES.items()}
    base = judges.get("claude") or next((j for j in judges.values() if j), {})
    if not base:
        print("no judged rows found to sample from; run judge.py first.")
        return
    # group candidate rows by task class (stratify on the safety-relevant axis)
    by_class = {}
    for (model, scenario, rep) in base:
        cls = scen.get(scenario, {}).get("class", "?")
        by_class.setdefault(cls, []).append((model, scenario, rep))
    rnd = random.Random(args.seed)
    classes = sorted(by_class)
    # proportional allocation with a floor of 2 per class, capped at class size
    total = sum(len(v) for v in by_class.values())
    alloc = {}
    for c in classes:
        alloc[c] = min(len(by_class[c]), max(2, round(args.n * len(by_class[c]) / total)))
    # trim/grow to hit exactly n
    while sum(alloc.values()) > args.n:
        c = max(alloc, key=lambda k: alloc[k]); alloc[c] -= 1
    while sum(alloc.values()) < args.n:
        c = min(classes, key=lambda k: alloc[k] / len(by_class[k])); alloc[c] += 1
    picked = []
    for c in classes:
        rows = by_class[c][:]
        rnd.shuffle(rows)
        picked.extend(rows[:alloc[c]])
    rnd.shuffle(picked)

    os.makedirs(args.out_dir, exist_ok=True)
    sheet = os.path.join(args.out_dir, "sheet.md")
    scores = os.path.join(args.out_dir, "scores.csv")
    keyf = os.path.join(args.out_dir, "key.json")
    key = {}
    with open(sheet, "w") as md, open(scores, "w", newline="") as sc:
        w = csv.writer(sc)
        w.writerow(["row_id", "human_score"])
        md.write("# Blind human scoring sheet\n\n"
                 "Score each ANSWER **1-5** against the GOLD + RUBRIC (the same inputs the\n"
                 "LLM judge saw). 5 = correct + actionable + safe; 3 = partially correct / "
                 "missing a key point; 1 = wrong, unsafe, or non-responsive. The model identity\n"
                 "and the LLM judges' scores are hidden on purpose. Put your score in\n"
                 "`scores.csv` next to each `row_id`.\n\n---\n\n")
        for i, (model, scenario, rep) in enumerate(picked, 1):
            rid = f"H{i:03d}"
            s = scen.get(scenario, {})
            try:
                ans = open(_answer_path(args.outputs_dir, model, scenario, rep)).read().strip()
            except OSError:
                ans = "(answer file missing)"
            md.write(f"## {rid}  ·  class: `{s.get('class','?')}`  ·  "
                     f"grounding: `{s.get('grounding','?')}`\n\n")
            md.write(f"**CONTEXT**\n\n```\n{s.get('context','').strip()}\n```\n\n")
            md.write(f"**TASK**\n\n{s.get('question','').strip()}\n\n")
            md.write(f"**GOLD REFERENCE**\n\n{s.get('gold_answer','').strip()}\n\n")
            md.write(f"**RUBRIC**\n\n{s.get('judge_rubric','').strip()}\n\n")
            md.write(f"**ANSWER**\n\n```\n{ans}\n```\n\n")
            md.write(f"**Your score (1-5):** ____\n\n---\n\n")
            w.writerow([rid, ""])
            key[rid] = {"model": model, "scenario": scenario, "rep": str(rep),
                        **{f"{name}_score": j.get((model, scenario, str(rep)))
                           for name, j in judges.items() if j}}
    json.dump(key, open(keyf, "w"), indent=2)
    present = [n for n, j in judges.items() if j]
    print(f"wrote {len(picked)} blind items:")
    print(f"  sheet  : {sheet}   (read this; score by hand)")
    print(f"  scores : {scores}  (fill the human_score column, 1-5)")
    print(f"  key    : {keyf}   (private: model + LLM scores [{', '.join(present)}])")
    print(f"  strata : {dict(sorted(alloc.items()))}")
    print(f"\nthen: python3 human_eval.py score")


def cmd_score(args):
    key = json.load(open(args.key))
    human = {}
    for row in csv.DictReader(open(args.scores)):
        v = (row.get("human_score") or "").strip()
        if not v:
            continue
        try:
            human[row["row_id"]] = int(round(float(v)))
        except ValueError:
            continue
    if not human:
        print(f"no human scores filled in {args.scores} yet.")
        return
    judge_names = sorted({k[:-6] for rid in key for k in key[rid] if k.endswith("_score")})
    print(f"# Human <-> judge agreement  ({len(human)} scored of {len(key)})\n")
    for jn in judge_names:
        pairs = []
        for rid, hs in human.items():
            js = key.get(rid, {}).get(f"{jn}_score")
            if js is not None:
                pairs.append((hs, js))
        if not pairs:
            continue
        cats = sorted(set(s for p in pairs for s in p))
        kq = cohen_kappa(pairs, cats, "quadratic")
        ka = cohen_kappa(pairs, cats)
        exact = sum(1 for a, b in pairs if a == b) / len(pairs)
        rho = spearman(pairs)
        mh = sum(a for a, _ in pairs) / len(pairs)
        mj = sum(b for _, b in pairs) / len(pairs)
        print(f"human vs {jn:7}: kappa_quad={kq:+.3f} [{label(kq)}]  "
              f"kappa={ka:+.3f}  exact={exact:.0%}  rho={rho:+.3f}  "
              f"mean h/{jn[:1]}={mh:.2f}/{mj:.2f}  n={len(pairs)}")
    print("\nbar: human<->judge kappa_quad >= 0.6 => the LLM judge tracks a human, "
          "not just another LLM.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="generate a blind stratified scoring sheet")
    m.add_argument("--n", type=int, default=50)
    m.add_argument("--scenarios", default="data/scenarios.json")
    m.add_argument("--outputs-dir", default=".tmp/judge/outputs")
    m.add_argument("--out-dir", default=OUT_DIR)
    m.add_argument("--seed", type=int, default=42)
    m.set_defaults(func=cmd_make)
    s = sub.add_parser("score", help="compute human<->judge kappa from filled scores")
    s.add_argument("--scores", default=os.path.join(OUT_DIR, "scores.csv"))
    s.add_argument("--key", default=os.path.join(OUT_DIR, "key.json"))
    s.set_defaults(func=cmd_score)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
