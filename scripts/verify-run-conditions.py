#!/usr/bin/env python3
"""Prove a completed run is one condition with nothing missing.

Everything a claim of the form "we evaluated N models under identical conditions
and evaluation" depends on is checked here, mechanically, from the locked bundle
- and, when present, cross-checked against the derived analysis lane.

The checks are deliberately paranoid about SILENT loss, because that is the
failure mode that survives review: a model that quietly ran 19 scenarios instead
of 20, a cell judged by one judge instead of two, a duplicate row inflating a
mean, an environment field that drifted for part of the run, or a lane that
dropped rows on the way out of the bundle.

DNF and truncation are reported, never failed on: they are outcomes measured
under the identical condition, not evidence against it.

Usage:
  scripts/verify-run-conditions.py --bundle <path> [--lane <dir>]
  scripts/verify-run-conditions.py --bundle <path> --json
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Fields that MUST hold one value across every row for the run to be one
# condition. Split by what they govern so a failure report is diagnostic.
CONDITION_FIELDS = {
    "software": ["env.inference_runtime", "env.ollama_version", "adapter"],
    "protocol": ["env.inference_strategy", "env.memory_context", "env.scenario_set",
                 "env.scenarios_sha", "prompt.template_sha256",
                 "gen_ai.request.temperature"],
    "machine": ["env.host", "env.cpu_governor", "env.cpu_no_turbo",
                "env.cpu_max_perf_pct", "env.cpu_min_perf_pct",
                "env.rapl_domain", "power.source"],
    "identity": ["env.run_id", "evaluation_policy"],
}

# Analysis-critical fields that must never be null on a non-DNF row.
REQUIRED_NUMERIC = ["det_score", "wall_s", "power.energy_wh"]

# Default record of the candidate-roster screen that produced the run roster.
DEFAULT_FAULTS = REPO / "data/models.ollama-chat-faults.json"


def read_model_list(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def _resolve_screen_path(relative: str, faults_path: Path) -> Path:
    """Roster paths in the screen record are repo-relative, but a screen shipped
    beside its rosters should also resolve."""
    for base in (REPO, faults_path.parent):
        candidate = base / relative
        if candidate.exists():
            return candidate
    return REPO / relative


def verify_roster_screen(report: "Report", bundle_roster: list[str],
                         models_in_results: set[str], faults_path: Path) -> dict:
    """Check the candidate-roster screen that decided who got to run at all.

    A run can be internally perfect and still mislead if the roster it ran was
    filtered on something correlated with the outcome. This does not fail such a
    screen - excluding a model that will not serve is correct - but it proves the
    screen is consistent with the roster that actually ran, and it surfaces every
    model that was dropped DESPITE working, which is the class that needs
    disclosing in prose.
    """
    if not faults_path.exists():
        report.check("candidate-roster screen is recorded", False,
                     f"{faults_path} not found - roster provenance unverified")
        return {}

    screen = json.loads(faults_path.read_text())
    counts = screen.get("counts", {})
    excluded = screen.get("excluded_models", [])

    total, ok = counts.get("total"), counts.get("ok")
    n_excluded = counts.get("excluded")
    report.check("screen counts reconcile",
                 total == (ok or 0) + (n_excluded or 0)
                 and n_excluded == len(excluded)
                 and (counts.get("fail", 0) + counts.get("warn", 0)) == n_excluded,
                 f"total={total} = ok={ok} + excluded={n_excluded} "
                 f"(fail={counts.get('fail')} warn={counts.get('warn')})")

    source_path = _resolve_screen_path(screen["source_roster"], faults_path)
    ok_path = _resolve_screen_path(screen["ok_roster"], faults_path)
    candidates = read_model_list(source_path) if source_path.exists() else []
    screened_ok = read_model_list(ok_path) if ok_path.exists() else []

    report.check("candidate roster file matches the screen's total",
                 len(candidates) == total,
                 f"{screen['source_roster']}={len(candidates)} total={total}")
    report.check("screened roster file matches the screen's ok count",
                 len(screened_ok) == ok,
                 f"{screen['ok_roster']}={len(screened_ok)} ok={ok}")

    # The roster that ran must be exactly the roster the screen approved.
    report.check("bundle roster == screened roster",
                 set(bundle_roster) == set(screened_ok),
                 f"{len(set(bundle_roster) ^ set(screened_ok))} models differ")

    excluded_ids = {str(row.get("model")) for row in excluded}
    leaked = excluded_ids & models_in_results
    report.check("no excluded model produced results", not leaked,
                 f"leaked: {sorted(leaked)}" if leaked else "none")
    report.check("every excluded model has a recorded reason",
                 all(row.get("overall_reason") for row in excluded),
                 f"{sum(1 for r in excluded if not r.get('overall_reason'))} unexplained")

    # Split the exclusions by whether the model actually worked.
    unservable, served_but_excluded = [], []
    for row in excluded:
        chat = str(row.get("chat_status"))
        (served_but_excluded if chat == "200" else unservable).append(row)

    report.note(f"candidate-roster screen: {total} candidates -> {ok} ran "
                f"({n_excluded} excluded); policy: {screen.get('policy', '')[:70]}")
    report.note(f"exclusions that could not be served at all: {len(unservable)} "
                "(HTTP 500 or pull failure) - uncontroversial")

    if served_but_excluded:
        report.note(
            f"MUST DISCLOSE - {len(served_but_excluded)} models served fine "
            "(HTTP 200 on chat and generate) and were still excluded:")
        for row in served_but_excluded:
            findings = "; ".join(row.get("findings") or [])
            report.note(f"    {row['model']} - {row.get('overall_reason')}"
                        + (f" [{findings}]" if findings else ""))
        report.note("    A screen that removes working models on an output-shape "
                    "criterion can be correlated with the outcome under study; "
                    "state it as a limitation rather than reporting the roster as "
                    "an arbitrary sample.")

    return {
        "validation_id": screen.get("validation_id"),
        "policy": screen.get("policy"),
        "candidates": total,
        "ran": ok,
        "excluded": n_excluded,
        "reason_counts": screen.get("reason_counts"),
        "unservable": [r["model"] for r in unservable],
        "served_but_excluded": [
            {"model": r["model"], "reason": r.get("overall_reason"),
             "findings": r.get("findings"),
             "chat_output_chars": r.get("chat_output_chars"),
             "generate_output_chars": r.get("generate_output_chars")}
            for r in served_but_excluded
        ],
    }


class Report:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []
        self.notes: list[str] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append((name, ok, detail))
        return ok

    def note(self, text: str) -> None:
        self.notes.append(text)

    @property
    def failed(self) -> list[tuple[str, bool, str]]:
        return [c for c in self.checks if not c[1]]

    def render(self) -> str:
        width = max(len(name) for name, _, _ in self.checks) + 2
        lines = []
        for name, ok, detail in self.checks:
            mark = "PASS" if ok else "FAIL"
            lines.append(f"  [{mark}] {name.ljust(width)} {detail}")
        return "\n".join(lines)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl_gz(path: Path):
    with gzip.open(path, "rt") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_roster(bundle: Path) -> list[str]:
    text = (bundle / "contract" / "roster.txt").read_text()
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def load_scenarios(bundle: Path) -> list[str]:
    data = json.loads((bundle / "contract" / "scenarios.json").read_text())
    return [s["id"] for s in data["scenarios"]]


def verify(bundle: Path, lane: Path | None, faults: Path | None = None) -> tuple[Report, dict]:
    report = Report()
    manifest = json.loads((bundle / "bundle-manifest.json").read_text())
    expected = manifest["expected"]
    # The bundle manifest says "reps"; the run summary says "repetitions".
    reps_expected = expected.get("reps", expected.get("repetitions"))
    if reps_expected is None:
        raise SystemExit("ERROR: bundle manifest declares no repetition count")

    # ---- integrity: the bytes we are about to trust ------------------------
    bad_hashes = []
    for relative in ("canonical/results.jsonl.gz", "canonical/judged.jsonl.gz",
                     "contract/roster.txt", "contract/scenarios.json"):
        want = (manifest.get("source_sha256") or {}).get(relative)
        path = bundle / relative
        if not want:
            bad_hashes.append(f"{relative}: unbound")
        elif not path.exists():
            bad_hashes.append(f"{relative}: missing")
        elif sha256(path) != want:
            bad_hashes.append(f"{relative}: mismatch")
    report.check("bundle bytes match bundle-manifest.json", not bad_hashes,
                 "; ".join(bad_hashes) or "4 files verified")

    roster = load_roster(bundle)
    scenarios = load_scenarios(bundle)
    report.check("roster size == expected models",
                 len(roster) == expected["models"],
                 f"roster={len(roster)} expected={expected['models']}")
    report.check("scenario count == expected",
                 len(scenarios) == expected["scenarios"],
                 f"scenarios={len(scenarios)} expected={expected['scenarios']}")

    # ---- read the run ------------------------------------------------------
    cells: Counter[tuple[str, str, int]] = Counter()
    per_model_scenarios: dict[str, set[str]] = defaultdict(set)
    per_model_reps: dict[str, set[int]] = defaultdict(set)
    condition: dict[str, set[str]] = defaultdict(set)
    max_tokens_by_scenario: dict[str, set[str]] = defaultdict(set)
    identity_incomplete = 0
    null_required: Counter[str] = Counter()
    dnf = 0
    truncated = 0
    rows = 0

    all_condition_fields = [f for group in CONDITION_FIELDS.values() for f in group]

    for row in read_jsonl_gz(bundle / "canonical/results.jsonl.gz"):
        rows += 1
        model, scenario = str(row.get("model")), str(row.get("scenario"))
        rep = int(row.get("rep", -1))
        cells[(model, scenario, rep)] += 1
        per_model_scenarios[model].add(scenario)
        per_model_reps[model].add(rep)
        for field in all_condition_fields:
            condition[field].add(repr(row.get(field)))
        max_tokens_by_scenario[scenario].add(repr(row.get("gen_ai.request.max_tokens")))
        if row.get("condition_identity_incomplete"):
            identity_incomplete += 1
        is_dnf = bool(row.get("dnf"))
        if is_dnf:
            dnf += 1
        finish = (row.get("gen_ai.response.finish_reasons") or [None])[0]
        if finish == "length":
            truncated += 1
        for field in REQUIRED_NUMERIC:
            if not is_dnf and row.get(field) is None:
                null_required[field] += 1

    # ---- completeness: nothing missing, nothing duplicated -----------------
    report.check("row count == models x scenarios x reps",
                 rows == expected["results"],
                 f"rows={rows} expected={expected['results']}")

    duplicates = [cell for cell, count in cells.items() if count > 1]
    report.check("no duplicated (model, scenario, rep) cell", not duplicates,
                 f"{len(duplicates)} duplicated" if duplicates else "15,200 unique"
                 if rows == 15200 else f"{len(cells)} unique")

    expected_grid = {(m, s, r) for m in roster for s in scenarios
                     for r in range(reps_expected)}
    missing = expected_grid - set(cells)
    extra = set(cells) - expected_grid
    report.check("every cell of the full grid is present", not missing,
                 f"{len(missing)} missing" if missing else
                 f"{len(expected_grid)} cells complete")
    report.check("no rows outside the declared grid", not extra,
                 f"{len(extra)} unexpected" if extra else "none")

    incomplete_models = {m: sorted(set(scenarios) - per_model_scenarios[m])
                         for m in roster if set(scenarios) - per_model_scenarios[m]}
    report.check("every model ran every scenario", not incomplete_models,
                 f"{len(incomplete_models)} models short" if incomplete_models
                 else f"{len(roster)} models x {len(scenarios)} scenarios")

    want_reps = set(range(reps_expected))
    wrong_reps = {m: sorted(per_model_reps[m]) for m in roster
                  if per_model_reps.get(m, set()) != want_reps}
    report.check("every model has every repetition", not wrong_reps,
                 f"{len(wrong_reps)} models differ" if wrong_reps
                 else f"reps {sorted(want_reps)}")

    # ---- identical conditions ---------------------------------------------
    report.check("no row flagged condition_identity_incomplete",
                 identity_incomplete == 0, f"{identity_incomplete} flagged")

    for group, fields in CONDITION_FIELDS.items():
        drifted = {f: len(condition[f]) for f in fields if len(condition[f]) != 1}
        report.check(f"{group} fields constant across the run", not drifted,
                     f"drifted: {drifted}" if drifted else f"{len(fields)} fields")

    # max_tokens is a per-scenario budget: it may differ BETWEEN scenarios but
    # must be identical across models within one, or models faced unequal caps.
    uneven = {s: len(v) for s, v in max_tokens_by_scenario.items() if len(v) != 1}
    report.check("token budget identical across models within each scenario",
                 not uneven, f"uneven: {uneven}" if uneven else
                 f"{len(max_tokens_by_scenario)} scenario budgets")

    report.check("no null analysis fields on completed rows", not null_required,
                 f"nulls: {dict(null_required)}" if null_required else
                 ", ".join(REQUIRED_NUMERIC))

    # ---- evaluation completeness ------------------------------------------
    judged: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    judge_rows = 0
    null_scores = 0
    for row in read_jsonl_gz(bundle / "canonical/judged.jsonl.gz"):
        judge_rows += 1
        key = (str(row.get("model")), str(row.get("scenario")), int(row.get("rep", -1)))
        judged[key].add(str(row.get("judge_model")))
        if row.get("score") is None:
            null_scores += 1

    judges = sorted({j for v in judged.values() for j in v})
    report.check("judgement count == cells x judges",
                 judge_rows == expected["canonical_judgements"],
                 f"rows={judge_rows} expected={expected['canonical_judgements']}")
    report.check("judge count == expected", len(judges) == expected["judges"],
                 ", ".join(judges))

    unjudged = set(cells) - set(judged)
    partial = {k for k, v in judged.items() if len(v) != len(judges)}
    orphan = set(judged) - set(cells)
    report.check("every result cell was judged", not unjudged,
                 f"{len(unjudged)} unjudged" if unjudged else f"{len(cells)} cells")
    report.check("every cell judged by EVERY judge", not partial,
                 f"{len(partial)} partially judged" if partial else
                 f"all by {len(judges)} judges")
    report.check("no judgement without a result row", not orphan,
                 f"{len(orphan)} orphaned" if orphan else "none")
    report.check("no null judge score", null_scores == 0, f"{null_scores} null")

    # ---- derived lane must not lose anything -------------------------------
    lane_summary = {}
    if lane is not None:
        lane_meta = json.loads((lane / "lane.json").read_text())
        for name, digest in (lane_meta.get("artifact_sha256") or {}).items():
            path = lane / name
            ok = path.exists() and sha256(path) == digest
            report.check(f"lane artifact unmodified: {name}", ok,
                         "sha256 matches lane.json" if ok else "MODIFIED since build")

        with (lane / "results_snapshot.csv").open(newline="") as handle:
            lane_rows = list(csv.DictReader(handle))
        lane_cells = {(r["model"], r["scenario"], int(r["rep"])) for r in lane_rows}
        report.check("lane carries every bundle row",
                     len(lane_rows) == rows and lane_cells == set(cells),
                     f"lane={len(lane_rows)} bundle={rows}, "
                     f"{len(set(cells) - lane_cells)} cells dropped")

        with (lane / "judged_snapshot.csv").open(newline="") as handle:
            lane_judged = list(csv.DictReader(handle))
        report.check("lane judged covers every cell",
                     len(lane_judged) == len(cells),
                     f"lane={len(lane_judged)} cells={len(cells)}")
        lane_summary = {
            "lane_id": lane_meta.get("run_id"),
            "results": len(lane_rows),
            "judged": len(lane_judged),
        }

    # ---- outcomes, reported not judged -------------------------------------
    report.note(f"DNF rows: {dnf} ({100*dnf/max(rows,1):.2f}%) - outcomes under the "
                "identical condition, not condition drift")
    report.note(f"finish_reason=length rows: {truncated} "
                f"({100*truncated/max(rows,1):.2f}%) - output-budget censoring")
    report.note(f"judges: {', '.join(judges)}")

    screen_summary = {}
    if faults is not None:
        screen_summary = verify_roster_screen(
            report, roster, {m for m, _, _ in cells}, faults)

    summary = {
        "run_id": manifest.get("source_id"),
        "bundle_id": manifest.get("bundle_id"),
        "claim_status": manifest.get("claim_status"),
        "models": len(roster),
        "scenarios": len(scenarios),
        "repetitions": reps_expected,
        "results": rows,
        "judgements": judge_rows,
        "judges": judges,
        "dnf": dnf,
        "truncated": truncated,
        "condition": {f: sorted(condition[f])[0].strip("'")
                      for f in all_condition_fields if len(condition[f]) == 1},
        "lane": lane_summary,
        "roster_screen": screen_summary,
        "checks_run": len(report.checks),
        "checks_failed": len(report.failed),
    }
    return report, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--lane", default="")
    parser.add_argument("--faults", default=str(DEFAULT_FAULTS),
                        help="candidate-roster screen record (empty string to skip)")
    parser.add_argument("--json", action="store_true", help="emit the summary as JSON")
    args = parser.parse_args()

    bundle = Path(args.bundle)
    if not bundle.is_absolute():
        bundle = REPO / bundle
    if not (bundle / "bundle-manifest.json").exists():
        raise SystemExit(f"ERROR: not a locked bundle: {bundle}")

    lane = None
    if args.lane:
        lane = Path(args.lane)
        if not lane.is_absolute():
            lane = REPO / lane
        if not (lane / "lane.json").exists():
            raise SystemExit(f"ERROR: not an analysis lane: {lane}")

    faults = None
    if args.faults:
        faults = Path(args.faults)
        if not faults.is_absolute():
            faults = REPO / faults

    report, summary = verify(bundle, lane, faults)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"RUN CONDITION VERIFICATION - {summary['run_id']}")
        print(f"{summary['models']} models x {summary['scenarios']} scenarios x "
              f"{summary['repetitions']} reps = {summary['results']} rows, "
              f"{summary['judgements']} judgements\n")
        print(report.render())
        print("\nreported, not failed:")
        for note in report.notes:
            print(f"  - {note}")

    failed = report.failed
    print()
    if failed:
        print(f"VERDICT: FAIL - {len(failed)} of {len(report.checks)} checks failed")
        for name, _, detail in failed:
            print(f"  {name}: {detail}")
        sys.exit(1)
    print(f"VERDICT: PASS - {len(report.checks)}/{len(report.checks)} checks. "
          "Every declared cell is present exactly once, every cell was judged by "
          "every judge, and every condition field holds a single value.")


if __name__ == "__main__":
    main()
