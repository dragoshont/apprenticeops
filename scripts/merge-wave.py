#!/usr/bin/env python3
"""merge-wave.py — fold a new wave's raw results (+ optional 2-judge output) into
the committed snapshots so docs/analysis/wave_analysis.ipynb picks up the new
models.

Updates:
  - data/snapshots/results_snapshot.csv   (safety/det + energy + systems; FREE,
    deterministic — ready the moment a wave's run finishes), and
  - data/snapshots/judged_snapshot.csv    (the 2-judge QUALITY consensus; only
    when --judged is given).

UPSERT, keyed on (runtime_adapter, model, scenario, rep), ORDER-PRESERVING:
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
    "True"/"False"; parameter_tier comes from the model lock while the historical
    row label is retained separately as legacy_footprint_bracket;
  finish_reason = gen_ai.response.finish_reasons[0].

QUALITY (judged): judge_score = mean of the COMPLETE requested ensemble's raw
1-5 scores per canonical analysis condition, scenario, and repetition. A partial
ensemble remains unjudged. DNF reps (empty answer) get 1.0 to match judge.py's
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
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_metrics  # noqa: E402

RESULTS_CSV = "data/snapshots/results_snapshot.csv"
JUDGED_CSV = "data/snapshots/judged_snapshot.csv"
MODEL_LOCK = "data/models.lock.jsonl"
SCEN, REPS = 19, 5
EXPECT = SCEN * REPS  # 95 rows per complete model

RESULT_COLS = [
    "analysis_schema_version", "model", "runtime_adapter", "parameter_tier",
    "legacy_footprint_bracket", "collection_batch", "cpu_frequency_regime",
    "power_source", "energy_analysis_scope", "scenario", "rep", "det_score",
    "decode_tokens_per_s", "prefill_tokens_per_s", "wall_s", "membw_peak_mb_s",
    "energy_wh", "parameter_count", "parameter_size_label", "quantization",
    "artifact_size_bytes", "expert_count", "expert_used_count", "dnf", "finish_reason",
]
JUDGED_COLS = [
    "analysis_schema_version", "model", "runtime_adapter", "parameter_tier",
    "legacy_footprint_bracket", "collection_batch", "cpu_frequency_regime",
    "scenario", "rep", "judge_score",
]
LEGACY_FOOTPRINT_BRACKETS = ("0-1B", "1-2B", "2-3B", "3-4B", "4-5GB")

# snapshot column -> raw-jsonl key (only where they differ from the column name)
RAW_KEY = {
    "membw_peak_mb_s": "membw.peak_mb_s",
    "energy_wh": "power.energy_wh",
    "parameter_count": "ollama.parameter_count",
    "parameter_size_label": "ollama.parameter_size",
    "quantization": "ollama.quantization",
    "artifact_size_bytes": "ollama.size_bytes",
    "expert_count": "ollama.expert_count",
    "expert_used_count": "ollama.expert_used_count",
    "decode_tokens_per_s": "decode_tok_s",
    "prefill_tokens_per_s": "prefill_tok_s",
    "power_source": "power.source",
}

LEGACY_RESULT_COLUMNS = {
    "adapter": "runtime_adapter",
    "bracket": "legacy_footprint_bracket",
    "decode_tok_s": "decode_tokens_per_s",
    "prefill_tok_s": "prefill_tokens_per_s",
    "param_count": "parameter_count",
    "param_size": "parameter_size_label",
    "quant": "quantization",
    "size_bytes": "artifact_size_bytes",
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
    if col == "analysis_schema_version":
        return 1
    if col == "runtime_adapter":
        return r.get("adapter") or r.get("env.inference_runtime") or "ollama"
    if col == "parameter_tier":
        return r.get("_parameter_tier") or r.get("parameter_tier") or ""
    if col == "legacy_footprint_bracket":
        return r.get("legacy_footprint_bracket") or r.get("bracket") or ""
    if col == "dnf":
        return str(bool(r.get("dnf")))
    if col == "finish_reason":
        fr = r.get("gen_ai.response.finish_reasons") or [r.get("finish_reason")]
        return "" if not fr or fr[0] is None else fr[0]
    v = r.get(RAW_KEY.get(col, col))
    return "" if v is None else v


def _bool_text(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "1" if value else "0"
    rendered = str(value).strip().lower()
    if rendered in {"1", "true", "yes", "on"}:
        return "1"
    if rendered in {"0", "false", "no", "off"}:
        return "0"
    return None


def provenance_for_raw_row(
    row: dict,
    *,
    collection_batch: str | None = None,
    cpu_frequency_regime: str | None = None,
    energy_analysis_scope: str = "descriptive_only",
) -> dict[str, str]:
    """Canonical snapshot provenance for one incoming raw result row."""

    batch = row.get("collection_batch") or row.get("env.run_id") or collection_batch
    if not batch:
        raise ValueError("collection_batch is required (stamp env.run_id or pass --collection-batch)")

    regime = row.get("cpu_frequency_regime") or cpu_frequency_regime
    if not regime:
        governor = row.get("env.cpu_governor")
        no_turbo = _bool_text(row.get("env.cpu_no_turbo"))
        perf_min = row.get("env.cpu_min_perf_pct")
        perf_max = row.get("env.cpu_max_perf_pct")
        if governor and no_turbo is not None and perf_min is not None and perf_max is not None:
            turbo = "turbo_off" if no_turbo == "1" else "turbo_on"
            regime = f"{governor}_{turbo}_perf_{perf_min}_{perf_max}"
    if not regime:
        raise ValueError(
            "cpu_frequency_regime is required (stamp locked CPU fields or pass "
            "--cpu-frequency-regime)"
        )

    power_source = row.get("power_source") or row.get("power.source") or ""
    energy = row.get("energy_wh")
    if energy in (None, ""):
        energy = row.get("power.energy_wh")
    if not power_source:
        raise ValueError("power_source is required for every incoming snapshot row")

    scope = row.get("energy_analysis_scope") or energy_analysis_scope
    if scope not in {"controlled_three_axis", "descriptive_only"}:
        raise ValueError(f"invalid energy_analysis_scope: {scope!r}")
    return {
        "collection_batch": str(batch),
        "cpu_frequency_regime": str(regime),
        "power_source": str(power_source),
        "energy_analysis_scope": str(scope),
    }


def key_of(row: dict) -> tuple:
    return (
        row.get("runtime_adapter") or row.get("adapter") or "ollama",
        row["model"],
        row["scenario"],
        str(row["rep"]),
    )


def load_model_tiers(path: str) -> dict[str, str | None]:
    tiers: dict[str, str | None] = {}
    with open(path) as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                tiers[row["model_id"]] = row.get("tier")
    return tiers


def normalize_existing(row: dict, cols: list[str], tiers: dict[str, str | None]) -> dict:
    normalized = dict(row)
    for old, new in LEGACY_RESULT_COLUMNS.items():
        if old in normalized and new not in normalized:
            normalized[new] = normalized[old]
    normalized["analysis_schema_version"] = "1"
    normalized["parameter_tier"] = tiers.get(normalized.get("model")) or ""
    return {col: normalized.get(col, "") for col in cols}


def validate_snapshot_provenance(rows: list[dict], fields: tuple[str, ...], artifact: str) -> None:
    for index, row in enumerate(rows, start=2):
        missing = [field for field in fields if row.get(field) in (None, "")]
        if missing:
            raise ValueError(
                f"{artifact} row {index} lacks canonical provenance: {', '.join(missing)}; "
                "run scripts/migrate-analysis-v1.py against legacy snapshots first"
            )


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
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def dedup_results(raw_rows: list[dict]) -> dict:
    """Best raw result row per (model, scenario, rep) within this wave (highest
    det_score), dropping pull_failed stubs but KEEPING DNF rows."""
    best: dict[tuple, dict] = {}
    for r in raw_rows:
        if is_stub(r):
            continue
        k = (cell(r, "runtime_adapter"), r["model"], r["scenario"], str(r["rep"]))
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
    ap.add_argument("--model-lock", default=MODEL_LOCK)
    ap.add_argument("--collection-batch",
                    help="fallback batch id when raw rows do not stamp env.run_id")
    ap.add_argument("--cpu-frequency-regime",
                    help="fallback locked CPU regime when raw env fields are unavailable")
    ap.add_argument("--energy-analysis-scope", default="descriptive_only",
                    choices=("controlled_three_axis", "descriptive_only"),
                    help="scope for incoming energy rows; controlled requires explicit intent")
    ap.add_argument("--allow-legacy-judge-join", action="store_true",
                    help="explicitly allow unique hashless historical judge rows")
    ap.add_argument("--evaluation-policy",
                    help="required requested ensemble id for hashless legacy judge rows")
    ap.add_argument("--exclude", default="",
                    help="comma-separated model tags to DROP from this wave's merge "
                         "(overlap guard: a model kept from a prior wave, e.g. an "
                         "overlapping tag whose earlier copy has fuller telemetry). "
                         "Applies to BOTH results and judged so the kept copy is never "
                         "clobbered.")
    ap.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = ap.parse_args()

    exclude = {m.strip() for m in args.exclude.split(",") if m.strip()}

    if not os.path.exists(args.results):
        sys.exit(f"no such results file: {args.results}")
    if not os.path.exists(args.model_lock):
        sys.exit(f"no such model lock: {args.model_lock}")
    model_tiers = load_model_tiers(args.model_lock)
    raw = [json.loads(l) for l in open(args.results) if l.strip()]
    if exclude:
        before = len(raw)
        raw = [r for r in raw if r.get("model") not in exclude]
        print(f"excluded {sorted(exclude)} from this wave "
              f"({before - len(raw)} raw rows dropped; prior-wave copy kept)")
    best = dedup_results(raw)
    if not best:
        sys.exit("no result rows found (only stubs?) — nothing to merge")

    brk: dict[str, str] = {}
    for r in best.values():
        brk.setdefault(r["model"], r.get("bracket"))
    bad = sorted({b for b in brk.values() if b not in LEGACY_FOOTPRINT_BRACKETS})
    if bad:
        print(f"WARN: non-canonical legacy footprint label(s) {bad} "
              f"(expected one of {LEGACY_FOOTPRINT_BRACKETS})", file=sys.stderr)
    missing_tier_models = sorted({r["model"] for r in best.values() if r["model"] not in model_tiers})
    if missing_tier_models:
        sys.exit(f"model lock has no rows for: {', '.join(missing_tier_models)}")
    per_model = Counter(r["model"] for r in best.values())
    if any(n > EXPECT for n in per_model.values()):
        print("WARN: >%d rows for %s (scenario/rep mismatch?)"
              % (EXPECT, {m: n for m, n in per_model.items() if n > EXPECT}), file=sys.stderr)

    # ---------- results_snapshot (safety/energy/systems) ----------
    existing = [normalize_existing(row, RESULT_COLS, model_tiers)
                for row in read_csv(args.results_csv)]
    try:
        validate_snapshot_provenance(
            existing,
            ("collection_batch", "cpu_frequency_regime", "power_source", "energy_analysis_scope"),
            args.results_csv,
        )
    except ValueError as exc:
        sys.exit(str(exc))
    new_rows = []
    provenance_by_key = {}
    for key, raw_row in sorted(best.items()):
        try:
            provenance = provenance_for_raw_row(
                raw_row,
                collection_batch=args.collection_batch,
                cpu_frequency_regime=args.cpu_frequency_regime,
                energy_analysis_scope=args.energy_analysis_scope,
            )
        except ValueError as exc:
            sys.exit(f"cannot merge {raw_row.get('model')} {raw_row.get('scenario')} "
                     f"r{raw_row.get('rep')}: {exc}")
        provenance_by_key[key] = provenance
        raw_row = {
            **raw_row,
            **provenance,
            "_parameter_tier": model_tiers.get(raw_row["model"]),
        }
        new_rows.append({col: cell(raw_row, col) for col in RESULT_COLS})
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
          + ", ".join(f"{b}:{bybr.get(b, 0)}" for b in LEGACY_FOOTPRINT_BRACKETS)
          + f"  ({len(per_model)} models)")
    incomplete = {m: n for m, n in per_model.items() if n < EXPECT - 2}
    if incomplete:
        print(f"    incomplete (<{EXPECT - 2} rows): "
              + ", ".join(f"{m}({n})" for m, n in sorted(incomplete.items(), key=lambda x: x[1])))

    # ---------- judged_snapshot (quality consensus) ----------
    if args.judged:
        if not os.path.exists(args.judged):
            sys.exit(f"no such judged file: {args.judged}")
        judged_rows = [json.loads(line) for line in open(args.judged) if line.strip()]
        try:
            evaluation_policy = analysis_metrics.resolve_evaluation_policy(
                judged_rows,
                explicit=args.evaluation_policy,
                allow_legacy=args.allow_legacy_judge_join,
            )
        except ValueError as exc:
            sys.exit(f"cannot merge judged rows: {exc}")
        identities = {
            key: analysis_metrics.analysis_condition(
                row,
                evaluation_policy=evaluation_policy,
            )
            for key, row in best.items()
        }
        exact_conditions, legacy_conditions = analysis_metrics.judge_condition_index(
            (identities[key], row)
            for key, row in best.items()
        )
        try:
            expected_judges = analysis_metrics.evaluation_policy_judges(evaluation_policy)
        except ValueError as exc:
            sys.exit(f"cannot merge judged rows: {exc}")
        scores: dict[tuple, dict[tuple[str, str], float]] = defaultdict(dict)
        unmatched_judgements = 0
        for jr in judged_rows:
            if jr.get("score") is None or jr.get("scenario") is None:
                continue
            if jr["model"] in exclude:
                continue
            try:
                condition_sha = analysis_metrics.resolve_judge_condition(
                    jr,
                    exact_conditions=exact_conditions,
                    legacy_conditions=legacy_conditions,
                    allow_legacy=args.allow_legacy_judge_join,
                )
            except ValueError as exc:
                sys.exit(f"cannot merge judged row for {jr.get('model')} "
                         f"{jr.get('scenario')} r{jr.get('rep', 0)}: {exc}")
            if condition_sha is None:
                unmatched_judgements += 1
                continue
            judge_identity = analysis_metrics.judge_identity(jr)
            if expected_judges and judge_identity not in expected_judges:
                sys.exit(
                    "cannot merge judged row from undeclared judge "
                    f"{judge_identity[0]}:{judge_identity[1]}"
                )
            score_key = (condition_sha, jr["scenario"], str(jr.get("rep", 0)))
            if judge_identity in scores[score_key]:
                sys.exit(
                    "cannot merge duplicate judgement for "
                    f"{jr.get('model')} {jr.get('scenario')} r{jr.get('rep', 0)} "
                    f"from {judge_identity[0]}:{judge_identity[1]}"
                )
            scores[score_key][judge_identity] = jr["score"]
        n_judges = max((len(v) for v in scores.values()), default=0)
        jnew, need_judge = [], 0
        for k, r in sorted(best.items()):
            adapter, m, scen, _ = k
            score_key = (identities[k].sha256, scen, str(r.get("rep", 0)))
            observed_judges = frozenset(scores.get(score_key, {}))
            if score_key in scores and observed_judges == expected_judges:
                judge_scores = scores[score_key].values()
                js = sum(judge_scores) / len(scores[score_key])
            elif r.get("dnf"):
                js = 1.0  # empty answer -> judge.py scores 1
            else:
                need_judge += 1
                continue
            jnew.append({
                "analysis_schema_version": 1,
                "model": m,
                "runtime_adapter": adapter,
                "parameter_tier": model_tiers.get(m) or "",
                "legacy_footprint_bracket": brk.get(m),
                "collection_batch": provenance_by_key[k]["collection_batch"],
                "cpu_frequency_regime": provenance_by_key[k]["cpu_frequency_regime"],
                "scenario": scen,
                "rep": r.get("rep"),
                "judge_score": js,
            })
        jexisting = [normalize_existing(row, JUDGED_COLS, model_tiers)
                     for row in read_csv(args.judged_csv)]
        try:
            validate_snapshot_provenance(
                jexisting,
                ("collection_batch", "cpu_frequency_regime"),
                args.judged_csv,
            )
        except ValueError as exc:
            sys.exit(str(exc))
        jadded, jreplaced = upsert(jexisting, jnew, better=lambda nw, cur: True)  # re-judge is authoritative
        if not args.dry_run:
            write_csv(args.judged_csv, JUDGED_COLS, jexisting)
        msg = (f"judged_snapshot {'(dry-run) ' if args.dry_run else ''}: "
               f"+{jadded} new, ~{jreplaced} re-judged (up to {n_judges} judges/rep) "
               f"-> {len(jexisting)} total")
        if need_judge:
            msg += f"  — {need_judge} non-DNF reps UNJUDGED (run judge-wave3.sh, then re-merge)"
        if unmatched_judgements:
            msg += f"  — {unmatched_judgements} judged rows did not match this wave"
        print(msg)
    else:
        print("judged_snapshot : skipped (no --judged; quality axis pending judging)")

    print("\nNEXT: re-run docs/analysis/wave_analysis.ipynb headless to rebuild "
          "data/site/ + figures (scripts/build-analysis-site.sh), then commit the "
          "snapshots + site together.")


if __name__ == "__main__":
    main()
