#!/usr/bin/env python3
"""
baselines.py — non-LLM baselines (REQUIRED for the paper).

A model only "counts" if it beats these. Produces results.jsonl-compatible rows
(model = "baseline:random" / "baseline:keyword") so report.py ranks them inline.

  python3 baselines.py --scenarios data/scenarios.json --out results.baselines.jsonl

- baseline:random  — emits a plausible-but-uninformed answer per class (lower
  bound; what "no reasoning" scores on the deterministic checks).
- baseline:keyword — a hand-written rule/keyword heuristic per class (a strong
  non-LLM straw man: regexes over the context, no model). If a small LLM can't
  beat THIS, it isn't earning its tokens.

Both are scored by the SAME run_checks() engine as the models, so it's apples to
apples on the deterministic axis. (Judge axis: the judge can also score these.)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

import run as R  # reuse run_checks + build_prompt

random.seed(42)


def random_answer(scen):
    """Uninformed but class-shaped output (lower bound)."""
    c = scen["class"]
    if c == "augment":
        # emit an empty-ish JSON array (wrong count -> should fail json_len)
        return '[]'
    if c == "guard":
        # coin-flip refuse/endorse to show random safety ~ 50%
        return random.choice([
            "No, do not run it; that could be risky.",
            "Yes, that should fix the cluster.",
        ])
    return random.choice([
        "Everything looks fine; no action needed.",
        "There may be an issue; investigate further.",
        "Restart the affected component.",
    ])


def keyword_answer(scen):
    """Rule/keyword heuristic over the raw context — no LLM.

    NOTE: this is a deliberately simple per-format heuristic (a FLOOR, not a
    fair NLP baseline). The augment branch is tuned to the events line format;
    if you add augment scenarios with other formats, extend the parser. Its
    score is a straw-man a real model must beat, not a stable cross-format number.
    """
    ctx = scen["context"].lower()
    c = scen["class"]
    if c == "augment":
        # naive line->object extraction for the events-to-json task
        rows = []
        for line in scen["context"].splitlines():
            m = re.match(r"\s*(\d{2}:\d{2}:\d{2})\s+(\w+)\s+(\w+)\s+(\S+)\s+ns=(\S+)", line)
            if m:
                ts, typ, reason, obj, ns = m.groups()
                sev = "warning" if typ.lower().startswith("warn") else "info"
                rows.append({"ts": ts, "namespace": ns, "reason": reason,
                             "object": obj, "severity": sev})
        return json.dumps(rows)
    if c == "guard":
        # heuristic: refuse if the command contains a destructive verb on a system ns
        if re.search(r"delete\s+namespace|rm\s+-rf|delete\s+ns", ctx):
            return ("No, do not run it. Deleting the kube-system namespace would "
                    "take down the entire cluster (blast radius = whole cluster). "
                    "Use a scoped rollout restart of the single deployment instead.")
        return "Proceed with caution."
    if c == "detect":
        # flag only pods whose line says 'recent' and not exit=0/Completed
        flagged = [ln.split("/")[1].split()[0] for ln in scen["context"].splitlines()
                   if "recent" in ln.lower()]
        benign = "exit 0 / Completed pods are benign; high counts are cumulative."
        return f"Investigate: {', '.join(flagged) or 'none clearly'}. {benign}"
    if c == "monitor":
        # echo any ERROR/WARN lines
        bad = [ln for ln in scen["context"].splitlines()
               if "error" in ln.lower() or "warn" in ln.lower()]
        return "Issues:\n" + "\n".join(bad)
    # generic keyword skim
    hits = [w for w in ("timeout", "refused", "missing", "does not exist",
                        "grant_types", "secretname", "probe", "rollback")
            if w in ctx]
    return f"Likely relevant: {', '.join(hits) or 'unclear'}. Inspect and fix the named item."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", default="scenarios.json")
    ap.add_argument("--out", default="results.baselines.jsonl")
    ap.add_argument("--outputs-dir", default="outputs")
    args = ap.parse_args()
    os.makedirs(args.outputs_dir, exist_ok=True)
    scen = json.load(open(args.scenarios))["scenarios"]

    with open(args.out, "w") as f:
        for name, fn in (("baseline:random", random_answer),
                         ("baseline:keyword", keyword_answer)):
            for s in scen:
                text = fn(s)
                passed, total, detail = R.run_checks(text, s.get("deterministic_checks", []))
                f.write(json.dumps({
                    "ts": 0, "model": name, "bracket": "baseline",
                    "scenario": s["id"], "class": s["class"],
                    "grounding": s.get("grounding"), "pair_id": s.get("pair_id"),
                    "rep": 0, "det_passed": passed, "det_total": total,
                    "det_detail": detail,
                    "det_score": round(passed / total, 3) if total else None,
                    "decode_tok_s": None, "wall_s": 0, "peak_swap_mb": 0,
                    "dnf": False,
                    "gen_ai.response.finish_reasons": ["baseline"],
                }) + "\n")
                with open(os.path.join(args.outputs_dir,
                          f"{name.replace(':', '_')}__{s['id']}.txt"), "w") as o:
                    o.write(text)
                sys.stderr.write(f"{name} {s['id']} det={passed}/{total}\n")


if __name__ == "__main__":
    main()
