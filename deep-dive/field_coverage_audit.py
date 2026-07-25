"""Per-model FIELD-POPULATION audit for the consolidated 152(+5) corpus.

Answers the question "do we truly have a 150+ model dataset with 200+ POPULATED fields
per model?" — which is NOT the same as "the schema has 245 keys". A key can be present
with a null/empty value. This streams the raw run JSONL(s) and reports, per model:

  * rows observed
  * how many of the union-schema fields are populated on >=1 row (breadth)
  * how many are populated on >=90% of rows (dependable)
  * per-telemetry-group coverage (env / power / membw / perf / ollama / gen_ai / det / prompt)
  * whether the judged file supplies judge scores for that model

and then flags the models with systematic gaps and what a re-run would have to fix.

"Populated" = key present AND value not None AND not "" / [] / {}.

Usage (on the node that holds the raw runs):
  python3 field_coverage_audit.py results.<run>.jsonl [--judged judged.<run>.jsonl] [--label 152]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

GROUPS = {
    "env": "env.",
    "power": "power.",
    "membw": "membw.",
    "perf": "perf.",
    "ollama": "ollama.",
    "gen_ai": "gen_ai.",
    "prompt": "prompt.",
    "scenario": "scenario.",
    "distill": "distill.",
    "strategy": "strategy.",
    "reset": "reset.",
    "decode/phase": ("decode.", "phase."),
    "http": ("http.", "http_"),
    "mem/proc": ("mem.", "proc.", "swap.", "disk.", "net.", "thermal."),
}
# fields that must be populated for the row to be scientifically usable
CRITICAL = [
    "model", "scenario", "rep", "det_score", "det_total", "wall_s",
    "power.energy_wh", "power.mean_watts", "env.cpu_no_turbo", "env.rapl_domain",
    "env.ollama_version", "env.scenarios_sha", "gen_ai.usage.output_tokens",
    "membw.peak_mb_s", "perf.core", "ollama.parameter_count", "ollama.quantization",
]


def populated(v) -> bool:
    return v is not None and v != "" and v != [] and v != {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--judged", default="")
    ap.add_argument("--label", default="run")
    args = ap.parse_args()

    per_model_rows: dict[str, int] = collections.Counter()
    per_model_field: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    per_model_dnf: dict[str, int] = collections.Counter()
    all_fields: set[str] = set()

    with open(args.results) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = r.get("model", "?")
            per_model_rows[m] += 1
            if r.get("dnf"):
                per_model_dnf[m] += 1
            all_fields.update(r.keys())
            pf = per_model_field[m]
            for k, v in r.items():
                if populated(v):
                    pf[k] += 1

    judged_models: collections.Counter = collections.Counter()
    if args.judged:
        try:
            with open(args.judged) as fh:
                for line in fh:
                    try:
                        j = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(j.get("score"), (int, float)):
                        judged_models[j.get("model", "?")] += 1
        except OSError:
            print(f"[warn] judged file unreadable: {args.judged}", file=sys.stderr)

    nf = len(all_fields)
    print(f"=== FIELD-POPULATION AUDIT — {args.label} ===")
    print(f"models={len(per_model_rows)}  rows={sum(per_model_rows.values())}  union schema fields={nf}")

    # ---- per-model breadth/depth ----
    rows = []
    for m, n in per_model_rows.items():
        pf = per_model_field[m]
        breadth = sum(1 for k in all_fields if pf.get(k, 0) > 0)
        dependable = sum(1 for k in all_fields if pf.get(k, 0) >= 0.9 * n)
        crit_missing = [k for k in CRITICAL if pf.get(k, 0) < 0.9 * n]
        rows.append((m, n, breadth, dependable, per_model_dnf.get(m, 0),
                     judged_models.get(m, 0), crit_missing))
    rows.sort(key=lambda r: (r[2], r[3]))

    print(f"\n{'model':52} {'rows':>5} {'anyfld':>7} {'>=90%':>6} {'dnf':>4} {'judged':>7}  critical_gaps")
    for m, n, b, d, dnf, jn, cm in rows:
        flag = "" if not cm else "  <= " + ",".join(x.replace("power.", "pw.").replace("membw.", "mb.") for x in cm[:4])
        print(f"{m[:52]:52} {n:5} {b:7} {d:6} {dnf:4} {jn:7}{flag}")

    # ---- group coverage across models ----
    print(f"\n--- telemetry-group coverage (share of rows populated, averaged over models) ---")
    for gname, pref in GROUPS.items():
        prefs = pref if isinstance(pref, tuple) else (pref,)
        gfields = [k for k in all_fields if k.startswith(prefs)]
        if not gfields:
            continue
        per = []
        for m, n in per_model_rows.items():
            pf = per_model_field[m]
            per.append(sum(pf.get(k, 0) for k in gfields) / (n * len(gfields)))
        avg = 100 * sum(per) / len(per)
        nmodels_zero = sum(1 for x in per if x == 0)
        print(f"  {gname:14} fields={len(gfields):3}  mean_row_coverage={avg:5.1f}%   models_with_ZERO={nmodels_zero}")

    # ---- fields that are never populated anywhere (dead schema) ----
    dead = []
    partial = []
    for k in sorted(all_fields):
        tot = sum(per_model_field[m].get(k, 0) for m in per_model_rows)
        allrows = sum(per_model_rows.values())
        if tot == 0:
            dead.append(k)
        elif tot < 0.5 * allrows:
            partial.append((k, 100 * tot / allrows))
    print(f"\n--- schema reality check ---")
    print(f"fields populated on >=50% of ALL rows : {nf - len(dead) - len(partial)}")
    print(f"fields populated on <50% of rows      : {len(partial)}")
    print(f"fields NEVER populated (dead)         : {len(dead)}")
    if dead:
        print("  dead: " + ", ".join(dead[:25]) + (" ..." if len(dead) > 25 else ""))
    if partial:
        print("  partial (field, %rows): " + ", ".join(f"{k}={p:.0f}%" for k, p in partial[:25])
              + (" ..." if len(partial) > 25 else ""))


if __name__ == "__main__":
    main()
