#!/usr/bin/env python3
"""merge-wave.py — fold a new wave's raw results (+ optional 2-judge output) into
the committed snapshots so docs/analysis/wave_analysis.ipynb picks up the new
models.

Updates:
  - data/snapshots/results_snapshot.csv   (safety/det + energy + systems; FREE,
    deterministic — ready the moment a wave's run finishes), and
  - data/snapshots/judged_snapshot.csv    (the 2-judge QUALITY consensus; only
    when --judged is given).

UPSERT, keyed on (model, scenario, rep), ORDER-PRESERVING:
  - a NEW key is appended;
  - a COLLIDING key is replaced only by a STRICTLY BETTER row — for results, a
    higher det_score (so a Wave-3 success upgrades a Wave-2 DNF on a re-run /
    backfill, but a DNF never clobbers a good row); for judged, the newer score
    (a re-judge is authoritative).
  - re-running with the same data is a no-op (idempotent).
This is why the merge reads the RAW jsonl, not wave2-dedup's DNF-stripped .clean
file: wave-1 keeps its 178 DNF rows (every model has the full 19x5 = 95), and a
served-failure model (all-DNF, like phi:2.7b) is a real data point that a later
wave can upgrade.

Field handling matches the committed wave-1 snapshot (verified 2026-06-21):
  drop pull_failed stubs; null -> "" (membw/expert_count on non-MoE); dnf bool ->
  "True"/"False"; bracket taken verbatim from each row (run.py writes the label);
  finish_reason = gen_ai.response.finish_reasons[0].

QUALITY (judged): judge_score = mean of the ensemble judges' raw 1-5 scores per
(model, scenario, rep). DNF reps (empty answer) get 1.0 to match judge.py's
empty->1 rule. A NON-DNF rep with no judge row is left out and reported (it still
needs judging — run judge-wave3.sh, then re-merge).

    # safety + energy now (free; quality pending judging):
    python3 scripts/merge-wave.py --results .tmp/results.wave2.jsonl
    # after judge-wave3.sh, add the quality axis (and the rest of the wave):
    python3 scripts/merge-wave.py --results .tmp/results.wave3.jsonl \
        --judged .tmp/judge/judged.wave3.jsonl
    # preview without writing:
    python3 scripts/merge-wave.py --results .tmp/results.wave2.jsonl --dry-run

Then re-run docs/analysis/wave_analysis.ipynb headless to rebuild data/site/ +
figures (scripts/build-analysis-site.sh), and commit the snapshots + site together.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict

RESULTS_CSV = "data/snapshots/results_snapshot.csv"
JUDGED_CSV = "data/snapshots/judged_snapshot.csv"
SCEN, REPS = 19, 5
EXPECT = SCEN * REPS  # 95 rows per complete model

RESULT_COLS = [
    "model", "bracket", "scenario", "rep", "det_score", "decode_tok_s",
    "prefill_tok_s", "wall_s", "membw_peak_mb_s", "energy_wh", "param_count",
    "param_size", "quant", "size_bytes", "expert_count", "expert_used_count",
    "dnf", "finish_reason",
]
JUDGED_COLS = ["model", "bracket", "scenario", "rep", "judge_score"]
CANON_BRACKETS = ("0-1B", "1-2B", "2-3B", "3-4B", "4-5GB")

# snapshot column -> raw-jsonl key (only where they differ from the column name)
RAW_KEY = {
    "membw_peak_mb_s": "membw.peak_mb_s",
    "energy_wh": "power.energy_wh",
    "param_count": "ollama.parameter_count",
    "param_size": "ollama.parameter_size",
    "quant": "ollama.quantization",
    "size_bytes": "ollama.size_bytes",
    "expert_count": "ollama.expert_count",
    "expert_used_count": "ollama.expert_used_count",
}


def is_stub(r: dict) -> bool:
    """A pull_failed stub or any non-result row (no scenario/rep)."""
    return bool(r.get("fatal")) or r.get("scenario") is None or r.get("rep") is None


def num(x) -> float:
    """det_score as a float for comparison ('' / None -> 0.0)."""
    if x is None or x == "":
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def cell(r: dict, col: str):
    """Render one results cell from a raw row (null -> '', bool -> 'True'/'False')."""
    if col == "dnf":
        return str(bool(r.get("dnf")))
    if col == "finish_reason":
        fr = r.get("gen_ai.response.finish_reasons") or [r.get("finish_reason")]
        return "" if not fr or fr[0] is None else fr[0]
    v = r.get(RAW_KEY.get(col, col))
    return "" if v is None else v


def key_of(row: dict) -> tuple:
    return (row["model"], row["scenario"], str(row["rep"]))


def read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, cols: list[str], rows: list[dict]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def dedup_results(raw_rows: list[dict]) -> dict:
    """Best raw result row per (model, scenario, rep) within this wave (highest
    det_score), dropping pull_failed stubs but KEEPING DNF rows."""
    best: dict[tuple, dict] = {}
    for r in raw_rows:
        if is_stub(r):
            continue
        k = (r["model"], r["scenario"], str(r["rep"]))
        cur = best.get(k)
        if cur is None or num(r.get("det_score")) > num(cur.get("det_score")):
            best[k] = r
    return best


def upsert(existing: list[dict], new_rows: list[dict], *, better) -> tuple[int, int]:
    """In-place, order-preserving upsert. `better(new, cur)` -> bool decides a
    replace. Returns (added, replaced)."""
    idx = {key_of(r): i for i, r in enumerate(existing)}
    added = replaced = 0
    for row in new_rows:
        k = key_of(row)
        if k in idx:
            cur = existing[idx[k]]
            if better(row, cur):
                existing[idx[k]] = row
                replaced += 1
        else:
            existing.append(row)
            idx[k] = len(existing) - 1
            added += 1
    return added, replaced


def main() -> None:
    ap = argparse.ArgumentParser(description="Merge a wave's results (+judge) into the snapshots.")
    ap.add_argument("--results", required=True,
                    help="RAW wave results.jsonl (NOT the wave2-dedup .clean file)")
    ap.add_argument("--judged", help="2-judge judged.jsonl (adds the quality axis)")
    ap.add_argument("--results-csv", default=RESULTS_CSV)
    ap.add_argument("--judged-csv", default=JUDGED_CSV)
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    if not os.path.exists(args.results):
        sys.exit(f"no such results file: {args.results}")
    raw = [json.loads(l) for l in open(args.results) if l.strip()]
    best = dedup_results(raw)
    if not best:
        sys.exit("no result rows found (only stubs?) — nothing to merge")

    brk: dict[str, str] = {}
    for r in best.values():
        brk.setdefault(r["model"], r.get("bracket"))
    bad = sorted({b for b in brk.values() if b not in CANON_BRACKETS})
    if bad:
        print(f"WARN: non-canonical bracket label(s) {bad} — would mis-group in the "
              f"analysis (expected one of {CANON_BRACKETS})", file=sys.stderr)
    per_model = Counter(r["model"] for r in best.values())
    if any(n > EXPECT for n in per_model.values()):
        print("WARN: >%d rows for %s (scenario/rep mismatch?)"
              % (EXPECT, {m: n for m, n in per_model.items() if n > EXPECT}), file=sys.stderr)

    # ---------- results_snapshot (safety/energy/systems) ----------
    existing = read_csv(args.results_csv)
    new_rows = [{c: cell(r, c) for c in RESULT_COLS} for _, r in sorted(best.items())]
    added, replaced = upsert(existing, new_rows,
                             better=lambda nw, cur: num(nw["det_score"]) > num(cur["det_score"]))
    dnf_n = sum(1 for r in new_rows if r["dnf"] == "True")
    if not args.dry_run:
        write_csv(args.results_csv, RESULT_COLS, existing)
    print(f"results_snapshot {'(dry-run) ' if args.dry_run else ''}: "
          f"+{added} new, ~{replaced} upgraded ({dnf_n} of this wave's rows are DNF) "
          f"-> {len(existing)} total")
    bybr = Counter(brk[m] for m in per_model)
    print("    models this wave: "
          + ", ".join(f"{b}:{bybr.get(b, 0)}" for b in CANON_BRACKETS)
          + f"  ({len(per_model)} models)")
    incomplete = {m: n for m, n in per_model.items() if n < EXPECT - 2}
    if incomplete:
        print(f"    incomplete (<{EXPECT - 2} rows): "
              + ", ".join(f"{m}({n})" for m, n in sorted(incomplete.items(), key=lambda x: x[1])))

    # ---------- judged_snapshot (quality consensus) ----------
    if args.judged:
        if not os.path.exists(args.judged):
            sys.exit(f"no such judged file: {args.judged}")
        scores: dict[tuple, list] = defaultdict(list)
        for jr in (json.loads(l) for l in open(args.judged) if l.strip()):
            if jr.get("score") is None or jr.get("scenario") is None:
                continue
            scores[(jr["model"], jr["scenario"], str(jr.get("rep", 0)))].append(jr["score"])
        n_judges = max((len(v) for v in scores.values()), default=0)
        jnew, need_judge = [], 0
        for k, r in sorted(best.items()):
            m, scen, _ = k
            if k in scores:
                js = sum(scores[k]) / len(scores[k])
            elif r.get("dnf"):
                js = 1.0  # empty answer -> judge.py scores 1
            else:
                need_judge += 1
                continue
            jnew.append({"model": m, "bracket": brk.get(m), "scenario": scen,
                         "rep": r.get("rep"), "judge_score": js})
        jexisting = read_csv(args.judged_csv)
        jadded, jreplaced = upsert(jexisting, jnew, better=lambda nw, cur: True)  # re-judge is authoritative
        if not args.dry_run:
            write_csv(args.judged_csv, JUDGED_COLS, jexisting)
        msg = (f"judged_snapshot {'(dry-run) ' if args.dry_run else ''}: "
               f"+{jadded} new, ~{jreplaced} re-judged (up to {n_judges} judges/rep) "
               f"-> {len(jexisting)} total")
        if need_judge:
            msg += f"  — {need_judge} non-DNF reps UNJUDGED (run judge-wave3.sh, then re-merge)"
        print(msg)
    else:
        print("judged_snapshot : skipped (no --judged; quality axis pending judging)")

    print("\nNEXT: re-run docs/analysis/wave_analysis.ipynb headless to rebuild "
          "data/site/ + figures (scripts/build-analysis-site.sh), then commit the "
          "snapshots + site together.")


if __name__ == "__main__":
    main()
