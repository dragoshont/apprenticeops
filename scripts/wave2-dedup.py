#!/usr/bin/env python3
"""Wave-2 dedup + clean — run this the moment the node sweep wraps, BEFORE any
snapshot refresh.

The Wave-2 resume appends to /tmp/sme-var/results.wave2.jsonl on the node, mixing
three kinds of row:
  1. real result rows         {model, scenario, rep, det_score, energy_wh, ...}
  2. fatal stubs              {model, bracket, fatal: "pull_failed", ts}   <- drop
  3. DNF rows                 det=0/N, finish_reason ~ dnf/error           <- drop
plus occasional duplicate (model, scenario, rep) across resume restarts.

This script keeps only clean result rows, dedups by (model, scenario, rep)
keeping the best det_score, and prints a per-model completeness report so you can
see which models are usable before refreshing data/snapshots and re-judging the
NEW models for the quality axis.

Fetch first, then run:
    scp dragos@home-ai.hont.ro:/tmp/sme-var/results.wave2.jsonl .tmp/
    python3 scripts/wave2-dedup.py .tmp/results.wave2.jsonl
"""
import json
import sys
from collections import defaultdict

INP = sys.argv[1] if len(sys.argv) > 1 else ".tmp/results.wave2.jsonl"
OUT = sys.argv[2] if len(sys.argv) > 2 else INP.replace(".jsonl", ".clean.jsonl")
SCEN_PER_MODEL = 19      # Wave-1 scenario count; complete model = 19 x 5 reps
REPS = 5


def is_pull_failed(r):
    return bool(r.get("fatal"))


def is_dnf(r):
    fr = r.get("finish_reason")
    return bool(r.get("dnf")) or (
        isinstance(fr, str) and ("dnf" in fr.lower() or "error" in fr.lower())
    )


def is_result(r):
    return r.get("scenario") is not None and r.get("rep") is not None


def main():
    rows = []
    for line in open(INP):
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    total = len(rows)

    pull_failed = [r for r in rows if is_pull_failed(r)]
    rest = [r for r in rows if not is_pull_failed(r)]
    dnf = [r for r in rest if is_dnf(r)]
    good = [r for r in rest if not is_dnf(r) and is_result(r)]

    # dedup (model, scenario, rep) keeping the best det_score
    best = {}
    for r in good:
        k = (r["model"], r["scenario"], str(r["rep"]))
        cur = best.get(k)
        if cur is None or (r.get("det_score") or 0) > (cur.get("det_score") or 0):
            best[k] = r
    clean = list(best.values())

    # per-model completeness
    per_model = defaultdict(int)
    for r in clean:
        per_model[r["model"]] += 1
    expected = SCEN_PER_MODEL * REPS
    complete = {m for m, n in per_model.items() if n >= expected - 2}  # tolerate a couple DNF
    partial = {m: n for m, n in per_model.items() if m not in complete}

    pf_models = sorted({r["model"] for r in pull_failed})

    print(f"input rows           : {total}")
    print(f"  pull_failed stubs  : {len(pull_failed)}  -> dropped  ({len(pf_models)} models)")
    print(f"  DNF / error rows   : {len(dnf)}  -> dropped")
    print(f"  dup rows collapsed : {len(good) - len(clean)}")
    print(f"clean result rows    : {len(clean)}")
    print(f"distinct clean models: {len(per_model)}  |  complete (>= {expected - 2} rows): {len(complete)}")
    if pf_models:
        print("\npull-failed models (likely the hf.co host-bug — exclude or re-pull via huggingface.co):")
        for m in pf_models:
            print(f"  - {m}")
    if partial:
        print("\npartial models (usable but incomplete; check before including):")
        for m, n in sorted(partial.items(), key=lambda x: x[1]):
            print(f"  {n:4d}/{expected}  {m}")

    with open(OUT, "w") as f:
        for r in clean:
            f.write(json.dumps(r) + "\n")
    print(f"\nwrote {OUT} ({len(clean)} clean rows)")
    print("\nNEXT (refresh): convert -> data/snapshots/results_snapshot.csv (safety+energy),")
    print("then JUDGE the NEW models (2-judge x 5-rep) for the quality axis before")
    print("rebuilding judged_snapshot.csv + data/site/ via wave_analysis.ipynb.")


if __name__ == "__main__":
    main()
