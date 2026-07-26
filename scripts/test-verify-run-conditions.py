#!/usr/bin/env python3
"""Prove scripts/verify-run-conditions.py actually catches what it claims.

A verification gate that cannot fail is decoration. Each test builds a tiny but
structurally complete bundle, breaks exactly one property, and asserts the gate
reports that property - and only that property - as failed.
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

SCRIPT = REPO / "scripts" / "verify-run-conditions.py"
spec = importlib.util.spec_from_file_location("verify_run_conditions", SCRIPT)
assert spec and spec.loader
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

MODELS = ["model-a", "model-b"]
SCENARIOS = ["scenario-1", "scenario-2"]
REPS = 2

CONDITION = {
    "env.inference_runtime": "ollama",
    "env.ollama_version": "ollama version is 0.30.8",
    "adapter": "ollama",
    "env.inference_strategy": "baseline",
    "env.memory_context": "none",
    "env.scenario_set": "test-set",
    "env.scenarios_sha": "abc123",
    "prompt.template_sha256": "def456",
    "gen_ai.request.temperature": 0.7,
    "env.host": "ai",
    "env.cpu_governor": "performance",
    "env.cpu_no_turbo": "1",
    "env.cpu_max_perf_pct": "100",
    "env.cpu_min_perf_pct": "100",
    "env.rapl_domain": "package-0",
    "power.source": "rapl:package-0",
    "env.run_id": "test-run",
    "evaluation_policy": "test-policy|judges:claude-x+gpt-y",
}
JUDGES = ["claude-x", "gpt-y"]


def _result_row(model, scenario, rep, **overrides):
    row = {
        "model": model, "scenario": scenario, "rep": rep,
        "det_score": 0.5, "wall_s": 1.0, "power.energy_wh": 0.01,
        "dnf": False, "gen_ai.response.finish_reasons": ["stop"],
        "gen_ai.request.max_tokens": 500,
        "condition_identity_incomplete": False,
        **CONDITION,
    }
    row.update(overrides)
    return row


def _write_gz(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_bundle(root, *, results=None, judged=None):
    """A structurally complete bundle; callers pass mutated rows to break it."""
    bundle = pathlib.Path(root) / "bundle"
    (bundle / "contract").mkdir(parents=True, exist_ok=True)

    if results is None:
        results = [_result_row(m, s, r)
                   for m in MODELS for s in SCENARIOS for r in range(REPS)]
    if judged is None:
        judged = [{"model": m, "scenario": s, "rep": r, "judge_model": j, "score": 3}
                  for m in MODELS for s in SCENARIOS for r in range(REPS) for j in JUDGES]

    _write_gz(bundle / "canonical/results.jsonl.gz", results)
    _write_gz(bundle / "canonical/judged.jsonl.gz", judged)
    (bundle / "contract/roster.txt").write_text(
        "# generated roster\n" + "\n".join(MODELS) + "\n")
    (bundle / "contract/scenarios.json").write_text(
        json.dumps({"scenarios": [{"id": s} for s in SCENARIOS]}))

    manifest = {
        "source_id": "test-run",
        "bundle_id": "test-bundle",
        "claim_status": "provisional",
        "expected": {
            "models": len(MODELS), "scenarios": len(SCENARIOS), "reps": REPS,
            "results": len(MODELS) * len(SCENARIOS) * REPS,
            "judges": len(JUDGES),
            "canonical_judgements": len(MODELS) * len(SCENARIOS) * REPS * len(JUDGES),
        },
        "source_sha256": {
            rel: _sha256(bundle / rel) for rel in (
                "canonical/results.jsonl.gz", "canonical/judged.jsonl.gz",
                "contract/roster.txt", "contract/scenarios.json")
        },
    }
    (bundle / "bundle-manifest.json").write_text(json.dumps(manifest, indent=1))
    return bundle


def failures(bundle):
    report, _ = verifier.verify(bundle, None)
    return {name for name, ok, _ in report.checks if not ok}


def test_clean_bundle_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert failures(build_bundle(tmp)) == set()


def test_missing_cell_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    dropped = rows[:-1]
    judged = [{"model": m, "scenario": s, "rep": r, "judge_model": j, "score": 3}
              for m in MODELS for s in SCENARIOS for r in range(REPS) for j in JUDGES]
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, results=dropped, judged=judged))
    assert "every cell of the full grid is present" in bad, bad
    assert "row count == models x scenarios x reps" in bad, bad


def test_duplicated_cell_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows[0] = dict(rows[1])  # collapse two cells onto one key
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, results=rows))
    assert "no duplicated (model, scenario, rep) cell" in bad, bad


def test_condition_drift_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows[-1]["env.cpu_governor"] = "powersave"  # one row ran differently
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, results=rows))
    assert "machine fields constant across the run" in bad, bad
    assert "software fields constant across the run" not in bad, bad


def test_uneven_token_budget_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows[0]["gen_ai.request.max_tokens"] = 4096  # one model got a bigger cap
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, results=rows))
    assert "token budget identical across models within each scenario" in bad, bad


def test_partial_judging_is_caught() -> None:
    judged = [{"model": m, "scenario": s, "rep": r, "judge_model": j, "score": 3}
              for m in MODELS for s in SCENARIOS for r in range(REPS) for j in JUDGES]
    judged = judged[:-1]  # one cell loses its second judge
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, judged=judged))
    assert "every cell judged by EVERY judge" in bad, bad
    assert "judgement count == cells x judges" in bad, bad


def test_orphan_judgement_is_caught() -> None:
    judged = [{"model": m, "scenario": s, "rep": r, "judge_model": j, "score": 3}
              for m in MODELS for s in SCENARIOS for r in range(REPS) for j in JUDGES]
    judged.append({"model": "ghost", "scenario": SCENARIOS[0], "rep": 0,
                   "judge_model": JUDGES[0], "score": 5})
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, judged=judged))
    assert "no judgement without a result row" in bad, bad


def test_identity_incomplete_row_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows[2]["condition_identity_incomplete"] = True
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, results=rows))
    assert "no row flagged condition_identity_incomplete" in bad, bad


def test_null_analysis_field_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows[1]["power.energy_wh"] = None  # completed row with no energy
    with tempfile.TemporaryDirectory() as tmp:
        bad = failures(build_bundle(tmp, results=rows))
    assert "no null analysis fields on completed rows" in bad, bad


def test_dnf_row_is_reported_not_failed() -> None:
    """DNF is an outcome under the condition, never a verification failure."""
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows[0]["dnf"] = True
    rows[0]["power.energy_wh"] = None  # DNF rows may lack completion fields
    rows[3]["gen_ai.response.finish_reasons"] = ["length"]
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp, results=rows)
        report, summary = verifier.verify(bundle, None)
    assert not report.failed, [c for c in report.failed]
    assert summary["dnf"] == 1
    assert summary["truncated"] == 1


def test_tampered_bytes_are_caught() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        rows = [_result_row(m, s, r)
                for m in MODELS for s in SCENARIOS for r in range(REPS)]
        rows[0]["det_score"] = 1.0
        _write_gz(bundle / "canonical/results.jsonl.gz", rows)  # edited after locking
        bad = failures(bundle)
    assert "bundle bytes match bundle-manifest.json" in bad, bad


# --- candidate-roster screen -------------------------------------------------

EXCLUDED_BROKEN = "model-broken"
EXCLUDED_WORKING = "model-working-but-dropped"


def build_screen(root, *, ok_models=None, excluded=None, counts=None):
    """A screen record plus the two roster files it references."""
    root = pathlib.Path(root)
    ok_models = MODELS if ok_models is None else ok_models
    if excluded is None:
        excluded = [
            {"model": EXCLUDED_BROKEN, "overall_status": "fail",
             "overall_reason": "served_failure", "chat_status": "500",
             "generate_status": "500", "findings": ["server error"]},
            {"model": EXCLUDED_WORKING, "overall_status": "fail",
             "overall_reason": "empty_completion", "chat_status": "200",
             "generate_status": "200", "chat_output_chars": 0,
             "generate_output_chars": 0,
             "findings": ["both chat and generate returned empty visible text"]},
        ]
    (root / "models.txt").write_text(
        "\n".join(ok_models + [r["model"] for r in excluded]) + "\n")
    (root / "models.ok.txt").write_text("\n".join(ok_models) + "\n")
    record = {
        "validation_id": "test-validation",
        "policy": "keep only ok",
        "source_roster": "models.txt",
        "ok_roster": "models.ok.txt",
        "counts": counts or {
            "total": len(ok_models) + len(excluded), "ok": len(ok_models),
            "excluded": len(excluded),
            "fail": len(excluded), "warn": 0,
        },
        "reason_counts": {},
        "excluded_models": excluded,
    }
    path = root / "faults.json"
    path.write_text(json.dumps(record))
    return path


def screen_failures(bundle, faults):
    report, _ = verifier.verify(bundle, None, faults)
    return {name for name, ok, _ in report.checks if not ok}


def test_clean_screen_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        faults = build_screen(tmp)
        assert screen_failures(bundle, faults) == set()


def test_screen_counts_must_reconcile() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        faults = build_screen(tmp, counts={"total": 99, "ok": 2, "excluded": 2,
                                           "fail": 2, "warn": 0})
        bad = screen_failures(bundle, faults)
    assert "screen counts reconcile" in bad, bad


def test_roster_edited_after_screening_is_caught() -> None:
    """The roster that ran must be exactly the roster the screen approved."""
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        faults = build_screen(tmp, ok_models=[MODELS[0], "some-other-model"])
        bad = screen_failures(bundle, faults)
    assert "bundle roster == screened roster" in bad, bad


def test_excluded_model_leaking_into_results_is_caught() -> None:
    rows = [_result_row(m, s, r)
            for m in MODELS for s in SCENARIOS for r in range(REPS)]
    rows += [_result_row(EXCLUDED_BROKEN, s, r) for s in SCENARIOS for r in range(REPS)]
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp, results=rows)
        faults = build_screen(tmp)
        bad = screen_failures(bundle, faults)
    assert "no excluded model produced results" in bad, bad


def test_unexplained_exclusion_is_caught() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        faults = build_screen(tmp, excluded=[
            {"model": EXCLUDED_BROKEN, "overall_status": "fail",
             "overall_reason": "", "chat_status": "500"},
        ], counts={"total": 3, "ok": 2, "excluded": 1, "fail": 1, "warn": 0})
        bad = screen_failures(bundle, faults)
    assert "every excluded model has a recorded reason" in bad, bad


def test_working_but_excluded_is_disclosed_not_failed() -> None:
    """Dropping a model that served fine is legal - but it must be surfaced."""
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        faults = build_screen(tmp)
        report, summary = verifier.verify(bundle, None, faults)
    assert not report.failed, report.failed
    disclosed = [n for n in report.notes if "MUST DISCLOSE" in n]
    assert disclosed, report.notes
    dropped = summary["roster_screen"]["served_but_excluded"]
    assert [d["model"] for d in dropped] == [EXCLUDED_WORKING], dropped
    assert summary["roster_screen"]["unservable"] == [EXCLUDED_BROKEN]


def test_missing_screen_record_is_reported() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bundle = build_bundle(tmp)
        bad = screen_failures(bundle, pathlib.Path(tmp) / "absent.json")
    assert "candidate-roster screen is recorded" in bad, bad


def main() -> None:
    tests = [value for name, value in globals().items()
             if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda fn: fn.__name__):
        test()
    print(f"run-condition verifier tests passed: {len(tests)}")


if __name__ == "__main__":
    main()
