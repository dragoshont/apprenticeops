#!/usr/bin/env python3
"""Regression tests for completed-run promotion into analysis schema v1."""
from __future__ import annotations

import importlib.util
import gzip
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "lock-completed-run.py"
SPEC = importlib.util.spec_from_file_location("lock_completed_run", SCRIPT)
assert SPEC and SPEC.loader
promotion = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = promotion
SPEC.loader.exec_module(promotion)


JUDGES = ("copilot:claude-test", "copilot:gpt-test")


def write_jsonl(path: pathlib.Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def add_sidecars(run: pathlib.Path) -> None:
    for model in ("model-a", "model-b"):
        result_bytes = (json.dumps({"model": model, "sidecar": True}) + "\n").encode()
        (run / f"{model}.results.jsonl.gz").write_bytes(gzip.compress(result_bytes, mtime=0))
        candidate_bytes = (json.dumps({"model": model, "candidate": 0}) + "\n").encode()
        archive_path = run / f"{model}.candidates.tar.gz"
        with tarfile.open(archive_path, "w:gz") as archive:
            member = tarfile.TarInfo(f"{model}.candidates.jsonl")
            member.size = len(candidate_bytes)
            archive.addfile(member, io.BytesIO(candidate_bytes))
    (run / "judge.log").write_text("fixture judge log\n")


def complete_result(model: str, scenario: str, rep: int, scenario_sha: str) -> dict:
    return {
        "model": model,
        "scenario": scenario,
        "rep": rep,
        "adapter": "ollama",
        "env.inference_runtime": "ollama",
        "ollama.digest": f"sha256:{model}",
        "ollama.quantization": "Q4_K_M",
        "env.host": "fixture-ai",
        "env.kernel": "linux",
        "env.cpu_no_turbo": "1",
        "env.cpu_governor": "performance",
        "env.cpu_min_perf_pct": "100",
        "env.cpu_max_perf_pct": "100",
        "env.rapl_domain": "package-0",
        "env.num_ctx": 8192,
        "env.ollama_version": "0.30.8",
        "prompt.template_sha256": "prompt-sha",
        "env.memory_context": "none",
        "env.inference_strategy": "baseline",
        "temp": 0.7,
        "think": False,
        "ollama.parameters": "top_k 40\ntop_p 0.9",
        "env.scenario_set": "fixture-core",
        "env.scenarios_sha": scenario_sha,
        "det_score": 1.0,
        "dnf": False,
        "gen_ai.response.finish_reasons": ["stop"],
        "gen_ai.completion": "fixture answer",
    }


def judgement(
    model: str,
    scenario: str,
    rep: int,
    backend: str,
    judge_model: str,
    *,
    score=4,
    parse_error=False,
) -> dict:
    row = {
        "model": model,
        "scenario": scenario,
        "rep": rep,
        "adapter": "ollama",
        "memory_context": "none",
        "inference_strategy": "baseline",
        "judge_backend": backend,
        "judge_model": judge_model,
        "score": score,
        "verdict": "fixture verdict",
        "evidence": "fixture evidence",
        "criteria_met": [],
        "criteria_missed": [],
    }
    if parse_error:
        row.update({
            "score": None,
            "verdict": "unparseable",
            "evidence": "parse_error",
            "criteria_missed": ["judge response could not be parsed"],
        })
    return row


def fixture(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    repo = root / "repo"
    run = repo / "data" / "runs" / "fixture-run"
    output = repo / "data" / "completed-runs"
    roster_path = repo / "data" / "models.fixture.txt"
    scenario_path = repo / "data" / "scenarios.fixture.json"
    roster_path.parent.mkdir(parents=True)
    roster_path.write_text("# bracket: fixture\nmodel-a\nmodel-b\n")
    scenarios = {"scenarios": [{"id": "s1"}, {"id": "s2"}]}
    scenario_path.write_text(json.dumps(scenarios) + "\n")
    run.mkdir(parents=True)
    meta = {
        "schema_version": 2,
        "run_id": "fixture-run",
        "model_set": "fixture",
        "models": "data/models.fixture.txt",
        "models_sha256": promotion.sha256_file(roster_path),
        "models_count": 2,
        "scenario_set": "fixture-core",
        "scenarios": "data/scenarios.fixture.json",
        "scenarios_sha256": promotion.sha256_file(scenario_path),
        "scenario_count": 2,
        "scenario_ids": ["s1", "s2"],
        "reps": 2,
        "judges": 2,
        "judge_identities": [
            {"judge_backend": "copilot", "judge_model": "claude-test"},
            {"judge_backend": "copilot", "judge_model": "gpt-test"},
        ],
        "expect": 2,
        "memory_context": "none",
        "inference_strategy": "baseline",
        "inference_runtime": "ollama",
    }
    (run / "run.meta").write_text(json.dumps(meta) + "\n")
    results = [
        complete_result(model, scenario, rep, meta["scenarios_sha256"])
        for model in ("model-a", "model-b")
        for scenario in ("s1", "s2")
        for rep in range(2)
    ]
    write_jsonl(run / "_mirror" / "results.fixture-run.jsonl", results)
    write_jsonl(run / "_mirror" / "results.fixture-run.jsonl.done", [
        {"model": "model-a", "units": 4},
        {"model": "model-b", "units": 4},
    ])
    judged = []
    for model in ("model-a", "model-b"):
        for scenario in ("s1", "s2"):
            for rep in range(2):
                if (model, scenario, rep) == ("model-a", "s1", 0):
                    judged.append(judgement(
                        model,
                        scenario,
                        rep,
                        "copilot",
                        "gpt-test",
                        score=None,
                        parse_error=True,
                    ))
                judged.extend([
                    judgement(model, scenario, rep, "copilot", "claude-test"),
                    judgement(model, scenario, rep, "copilot", "gpt-test"),
                ])
    write_jsonl(run / "judged.fixture-run.jsonl", judged)
    write_jsonl(run / "pipeline-ledger.jsonl", [
        {"model": model, "stage": "persist", "ok": 1}
        for model in ("model-a", "model-b")
    ])
    (run / ".committed").write_text("model-a\nmodel-b\n")
    (run / ".push-pending").write_text("")
    return repo, run, output


def full_shape_fixture(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    repo = root / "repo"
    run = repo / "data" / "runs" / "full-shape-run"
    output = repo / "data" / "completed-runs"
    roster_path = repo / "data" / "models.full-shape.txt"
    scenario_path = repo / "data" / "scenarios.full-shape.json"
    models = tuple(f"model-{index:03d}" for index in range(152))
    scenarios = tuple(f"s{index:02d}" for index in range(20))
    roster_path.parent.mkdir(parents=True)
    roster_path.write_text("# bracket: full-shape\n" + "\n".join(models) + "\n")
    scenario_path.write_text(json.dumps({
        "scenarios": [{"id": scenario} for scenario in scenarios],
    }) + "\n")
    run.mkdir(parents=True)
    meta = {
        "schema_version": 2,
        "run_id": "full-shape-run",
        "model_set": "full-shape",
        "models": "data/models.full-shape.txt",
        "models_sha256": promotion.sha256_file(roster_path),
        "models_count": len(models),
        "scenario_set": "full-shape-core",
        "scenarios": "data/scenarios.full-shape.json",
        "scenarios_sha256": promotion.sha256_file(scenario_path),
        "scenario_count": len(scenarios),
        "scenario_ids": list(scenarios),
        "reps": 5,
        "judges": len(JUDGES),
        "judge_identities": [
            {"judge_backend": backend, "judge_model": model}
            for backend, model in (value.split(":", 1) for value in JUDGES)
        ],
        "expect": len(models),
        "memory_context": "none",
        "inference_strategy": "baseline",
        "inference_runtime": "ollama",
    }
    (run / "run.meta").write_text(json.dumps(meta) + "\n")
    write_jsonl(
        run / "_mirror" / "results.full-shape-run.jsonl",
        (
            complete_result(model, scenario, rep, meta["scenarios_sha256"])
            for model in models
            for scenario in scenarios
            for rep in range(5)
        ),
    )
    write_jsonl(
        run / "_mirror" / "results.full-shape-run.jsonl.done",
        ({"model": model, "units": 100} for model in models),
    )
    write_jsonl(
        run / "judged.full-shape-run.jsonl",
        (
            judgement(model, scenario, rep, *judge.split(":", 1))
            for model in models
            for scenario in scenarios
            for rep in range(5)
            for judge in JUDGES
        ),
    )
    write_jsonl(
        run / "pipeline-ledger.jsonl",
        ({"model": model, "stage": "persist", "ok": 1} for model in models),
    )
    (run / ".committed").write_text("\n".join(models) + "\n")
    (run / ".push-pending").write_text("")
    return repo, run, output


def context(repo: pathlib.Path, run: pathlib.Path, output: pathlib.Path):
    return promotion.build_context(
        repo_root=repo,
        run_dir=run,
        output_root=output,
        judge_values=JUDGES,
    )


def expect_failure(callable_, gate: str) -> promotion.PromotionError:
    try:
        callable_()
    except promotion.PromotionError as exc:
        assert exc.gate == gate, (exc.gate, str(exc))
        return exc
    raise AssertionError(f"expected PromotionError at {gate}")


def test_complete_fixture_promotes_verifies_and_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        ctx = context(repo, run, output)
        stale_stage = output / ".staging" / "fixture-run.999999.tmp"
        stale_stage.mkdir(parents=True)
        (stale_stage / "partial").write_text("abandoned\n")
        with promotion.promotion_lock(ctx):
            bundle, manifest = promotion.promote(ctx)
        assert not stale_stage.exists()
        assert manifest["source_kind"] == "completed_run"
        assert manifest["claim_status"] == "provisional"
        assert manifest["observed"]["results"] == 8
        assert manifest["observed"]["canonical_judgements"] == 16
        assert manifest["observed"]["judge_retries"] == 1
        assert (
            manifest["observed"]["canonical_judgements"]
            + manifest["observed"]["judge_retries"]
            == manifest["observed"]["raw_judge_attempts"]
        )
        assert (bundle / "contract" / "roster.txt").read_bytes() == ctx.inputs.roster.read_bytes()
        assert (bundle / "contract" / "scenarios.json").read_bytes() == ctx.inputs.scenarios.read_bytes()
        assert (bundle / "raw" / "push-pending.txt").read_bytes() == ctx.inputs.push_pending.read_bytes()
        assert promotion.verify_bundle(bundle)["bundle_id"] == manifest["bundle_id"]
        with promotion.promotion_lock(ctx):
            second_bundle, second_manifest = promotion.promote(ctx)
        assert second_bundle == bundle
        assert second_manifest["bundle_id"] == manifest["bundle_id"]
        status = promotion.latest_status(output, "fixture-run")
        assert status["bundles"] == [bundle.name]
        assert status["last_event"]["stage"] == "promotion_eligible"


def test_full_shape_fixture_promotes_verifies_and_is_idempotent() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = full_shape_fixture(pathlib.Path(directory))
        ctx = context(repo, run, output)
        with promotion.promotion_lock(ctx):
            bundle, manifest = promotion.promote(ctx)
        assert manifest["observed"]["results"] == 15_200
        assert manifest["observed"]["canonical_judgements"] == 30_400
        assert manifest["observed"]["raw_judge_attempts"] == 30_400
        assert manifest["observed"]["judge_retries"] == 0
        assert promotion.verify_bundle(bundle)["bundle_id"] == manifest["bundle_id"]
        with promotion.promotion_lock(ctx):
            second_bundle, second_manifest = promotion.promote(ctx)
        assert second_bundle == bundle
        assert second_manifest["bundle_id"] == manifest["bundle_id"]
        ledger = [
            json.loads(line)
            for line in (output / ".state" / "full-shape-run" / "promotion-ledger.jsonl").read_text().splitlines()
        ]
        started = [row for row in ledger if row["stage"] == "promotion_started"]
        assert len(started) == 2
        assert all(row["input_sha256"] for row in started)


def test_malformed_result_reports_exact_missing_fields() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results_path = run / "_mirror" / "results.fixture-run.jsonl"
        rows = [json.loads(line) for line in results_path.read_text().splitlines()]
        rows[0].pop("rep")
        write_jsonl(results_path, rows)
        failure = expect_failure(lambda: promotion.build_stage(context(repo, run, output)), "P3")
        assert failure.details["malformed_results"] == [{
            "fatal": False,
            "line": 1,
            "missing_fields": ["rep"],
            "model": "model-a",
            "scenario": "s1",
            "rep": None,
        }]


def test_sidecars_are_hash_bound_and_copied_byte_exactly() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        add_sidecars(run)
        ctx = context(repo, run, output)
        source_sidecars = {
            relative: source.read_bytes()
            for relative, source in ctx.inputs.sidecar_sources().items()
        }
        bundle, manifest = promotion.promote(ctx)
        assert manifest["observed"]["candidate_archives"] == 2
        assert manifest["observed"]["result_archives"] == 2
        assert manifest["observed"]["log_files"] == 1
        for relative, source_bytes in source_sidecars.items():
            assert (bundle / relative).read_bytes() == source_bytes
            assert relative in manifest["source_sha256"]
        assert promotion.verify_bundle(bundle)["bundle_id"] == manifest["bundle_id"]


def test_sidecar_inventory_drift_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        add_sidecars(run)
        ctx = context(repo, run, output)
        (run / "late.log").write_text("created after intake\n")
        error = expect_failure(lambda: promotion.promote(ctx), "P7")
        assert error.details["pattern"] == "*.log"
        assert not list(output.glob("fixture-run-*"))


def test_partial_fixture_refuses_without_visible_bundle() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        lines = results.read_text().splitlines()
        results.write_text("\n".join(lines[:-1]) + "\n")
        ctx = context(repo, run, output)
        expect_failure(lambda: promotion.build_stage(ctx), "P3")
        assert not list(output.glob("fixture-run-*"))


def test_multiple_successful_judgements_refuse() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        judged = run / "judged.fixture-run.jsonl"
        with judged.open("a") as handle:
            handle.write(json.dumps(judgement(
                "model-a", "s1", 0, "copilot", "gpt-test", score=5,
            )) + "\n")
        ctx = context(repo, run, output)
        expect_failure(lambda: promotion.build_stage(ctx), "P4")
        assert not list(output.glob("fixture-run-*"))


def test_wrong_roster_hash_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        (repo / "data" / "models.fixture.txt").write_text(
            "# changed after launch\nmodel-a\nmodel-b\n"
        )
        ctx = context(repo, run, output)
        expect_failure(lambda: promotion.build_stage(ctx), "P2")


def test_wrong_scenario_hash_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        scenario_path = repo / "data" / "scenarios.fixture.json"
        scenarios = json.loads(scenario_path.read_text())
        scenarios["changed_after_launch"] = True
        scenario_path.write_text(json.dumps(scenarios) + "\n")
        ctx = context(repo, run, output)
        error = expect_failure(lambda: promotion.build_stage(ctx), "P2")
        assert error.details["actual"] != error.details["expected"]


def test_duplicate_result_tuple_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        first = results.read_text().splitlines()[0]
        with results.open("a") as handle:
            handle.write(first + "\n")
        ctx = context(repo, run, output)
        expect_failure(lambda: promotion.build_stage(ctx), "P3")


def test_extra_result_tuple_refuses_with_exact_gap() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        extra = complete_result("model-a", "s1", 2, json.loads((run / "run.meta").read_text())["scenarios_sha256"])
        with results.open("a") as handle:
            handle.write(json.dumps(extra) + "\n")
        ctx = context(repo, run, output)
        error = expect_failure(lambda: promotion.build_stage(ctx), "P3")
        assert error.details["extra_results"] == [
            {"model": "model-a", "scenario": "s1", "rep": 2}
        ]


def test_missing_judge_family_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        judged = run / "judged.fixture-run.jsonl"
        rows = [json.loads(line) for line in judged.read_text().splitlines()]
        rows = [
            row for row in rows
            if not (
                row["model"] == "model-b"
                and row["scenario"] == "s2"
                and row["rep"] == 1
                and row["judge_model"] == "gpt-test"
            )
        ]
        write_jsonl(judged, rows)
        ctx = context(repo, run, output)
        error = expect_failure(lambda: promotion.build_stage(ctx), "P4")
        assert error.details["missing_attempts"]
        assert error.details["missing_successes"]


def test_missing_judgement_rep_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        judged = run / "judged.fixture-run.jsonl"
        rows = [json.loads(line) for line in judged.read_text().splitlines()]
        rows[0].pop("rep")
        write_jsonl(judged, rows)
        ctx = context(repo, run, output)
        error = expect_failure(lambda: promotion.build_stage(ctx), "P4")
        assert error.details["invalid_repetitions"][0]["value"] is None


def test_incomplete_condition_identity_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        rows = [json.loads(line) for line in results.read_text().splitlines()]
        rows[0].pop("ollama.digest")
        write_jsonl(results, rows)
        ctx = context(repo, run, output)
        error = expect_failure(lambda: promotion.build_stage(ctx), "P3")
        assert "artifact_identity" in error.details["incomplete_results"][0]["missing_fields"]


def test_runtime_default_sampler_is_derived_without_changing_raw_source() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        rows = [json.loads(line) for line in results.read_text().splitlines()]
        for row in rows:
            row.pop("ollama.parameters")
        write_jsonl(results, rows)
        source_hash = promotion.sha256_file(results)
        ctx = context(repo, run, output)
        bundle, _manifest = promotion.promote(ctx)
        assert promotion.sha256_file(results) == source_hash
        with gzip.open(bundle / "canonical" / "results.jsonl.gz", "rt") as handle:
            normalized = json.loads(next(handle))
        assert normalized["analysis.sampler_policy"]["kind"] == "runtime_defaults"


def test_process_snapshot_artifact_digest_is_derived_without_changing_raw_source() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        rows = [json.loads(line) for line in results.read_text().splitlines()]
        for row in rows:
            row.pop("ollama.digest")
            row["ollama.ps.before"] = {
                "models": [{"name": row["model"] + ":latest", "digest": "b" * 64}],
            }
        write_jsonl(results, rows)
        source_hash = promotion.sha256_file(results)
        ctx = context(repo, run, output)
        bundle, _manifest = promotion.promote(ctx)
        assert promotion.sha256_file(results) == source_hash
        with gzip.open(bundle / "canonical" / "results.jsonl.gz", "rt") as handle:
            normalized = json.loads(next(handle))
        assert normalized["analysis.artifact_identity"] == "ollama-ps-sha256:" + "b" * 64


def test_pending_push_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        (run / ".push-pending").write_text("model-b\n")
        ctx = context(repo, run, output)
        expect_failure(lambda: promotion.build_stage(ctx), "P1")


def test_pause_and_cancel_markers_refuse() -> None:
    for marker in (".paused", ".canceled"):
        with tempfile.TemporaryDirectory() as directory:
            repo, run, output = fixture(pathlib.Path(directory))
            (run / marker).write_text("blocked\n")
            ctx = context(repo, run, output)
            expect_failure(lambda: promotion.build_stage(ctx), "P1")


def test_symlinked_mirror_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        mirror = run / "_mirror"
        moved = run / "actual-mirror"
        mirror.rename(moved)
        mirror.symlink_to(moved, target_is_directory=True)
        error = expect_failure(lambda: context(repo, run, output), "P0")
        assert "symlinked run evidence" in str(error)


def test_source_mutation_between_normalize_and_lock_refuses() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        ctx = context(repo, run, output)
        promotion.build_stage(ctx)
        gate_report = promotion.validate_stage(ctx)
        with (run / "pipeline-ledger.jsonl").open("a") as handle:
            handle.write(json.dumps({"stage": "late-write", "ok": 1}) + "\n")
        expect_failure(lambda: promotion.lock_stage(ctx, gate_report), "P7")
        assert not list(output.glob("fixture-run-*"))


def test_verify_detects_bundle_tampering() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        ctx = context(repo, run, output)
        bundle, _manifest = promotion.promote(ctx)
        with (bundle / "gate-report.json").open("a") as handle:
            handle.write(" ")
        expect_failure(lambda: promotion.verify_bundle(bundle), "P7")


def test_metadata_rejects_same_count_judge_substitution() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        substituted = promotion.build_context(
            repo_root=repo,
            run_dir=run,
            output_root=output,
            judge_values=("copilot:wrong-claude", "copilot:wrong-gpt"),
        )
        roster = promotion.parse_roster(substituted.inputs.roster)
        scenarios = promotion.parse_scenarios(substituted.inputs.scenarios)
        expect_failure(
            lambda: promotion.validate_metadata(substituted, roster, scenarios),
            "P2",
        )


def test_metadata_rejects_malformed_modern_judge_identities() -> None:
    malformed_values = (
        None,
        "copilot:claude-test",
        [],
        [{}],
        [{"judge_backend": "", "judge_model": "claude-test"}],
        [
            {"judge_backend": "copilot", "judge_model": "claude-test"},
            {"judge_backend": "copilot", "judge_model": "claude-test"},
        ],
        [{"judge_backend": "copilot", "judge_model": "claude-test"}],
    )
    for malformed in malformed_values:
        with tempfile.TemporaryDirectory() as directory:
            repo, run, output = fixture(pathlib.Path(directory))
            meta_path = run / "run.meta"
            meta = json.loads(meta_path.read_text())
            meta["judge_identities"] = malformed
            meta_path.write_text(json.dumps(meta) + "\n")
            ctx = context(repo, run, output)
            roster = promotion.parse_roster(ctx.inputs.roster)
            scenarios = promotion.parse_scenarios(ctx.inputs.scenarios)
            expect_failure(
                lambda: promotion.validate_metadata(ctx, roster, scenarios),
                "P2",
            )


def test_metadata_requires_strict_positive_integer_judge_count() -> None:
    invalid_counts = (2.5, "2", "two", {}, [], True, False, 0, -1, None)
    for invalid in invalid_counts:
        with tempfile.TemporaryDirectory() as directory:
            repo, run, output = fixture(pathlib.Path(directory))
            meta_path = run / "run.meta"
            meta = json.loads(meta_path.read_text())
            meta["judges"] = invalid
            meta_path.write_text(json.dumps(meta) + "\n")
            ctx = context(repo, run, output)
            roster = promotion.parse_roster(ctx.inputs.roster)
            scenarios = promotion.parse_scenarios(ctx.inputs.scenarios)
            expect_failure(
                lambda: promotion.validate_metadata(ctx, roster, scenarios),
                "P2",
            )

    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        meta_path = run / "run.meta"
        meta = json.loads(meta_path.read_text())
        del meta["judges"]
        meta_path.write_text(json.dumps(meta) + "\n")
        ctx = context(repo, run, output)
        roster = promotion.parse_roster(ctx.inputs.roster)
        scenarios = promotion.parse_scenarios(ctx.inputs.scenarios)
        expect_failure(
            lambda: promotion.validate_metadata(ctx, roster, scenarios),
            "P2",
        )

    assert promotion.analysis_metrics.metadata_judge_count({"judges": 2}) == 2


def test_verify_rejects_unlisted_bundle_file() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        ctx = context(repo, run, output)
        bundle, _manifest = promotion.promote(ctx)
        (bundle / "unlisted.txt").write_text("not part of evidence\n")
        expect_failure(lambda: promotion.verify_bundle(bundle), "P7")


def test_payload_hashes_rejects_symlinked_directory() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        stage = root / "stage"
        target = root / "outside"
        stage.mkdir()
        target.mkdir()
        (stage / "linked-directory").symlink_to(target, target_is_directory=True)
        expect_failure(lambda: promotion.payload_hashes(stage), "P0")


def test_verify_rejects_symlinked_directory() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        bundle, _manifest = promotion.promote(context(repo, run, output))
        target = pathlib.Path(directory) / "outside"
        target.mkdir()
        (bundle / "linked-directory").symlink_to(target, target_is_directory=True)
        expect_failure(lambda: promotion.verify_bundle(bundle), "P0")


def test_cli_promote_and_verify_end_to_end() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        command = [
            sys.executable,
            str(SCRIPT),
            "promote",
            "--repo-root", str(repo),
            "--run-dir", str(run),
            "--output-root", str(output),
        ]
        for judge in JUDGES:
            command.extend(["--judge", judge])
        promoted = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(promoted.stdout)
        assert payload["ok"] is True
        bundle = pathlib.Path(payload["bundle"])
        assert bundle.name.endswith(payload["manifest"]["bundle_id"])
        verified = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", "--bundle", str(bundle)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(verified.stdout)["ok"] is True
        ledger = [
            json.loads(line)
            for line in (output / ".state" / "fixture-run" / "promotion-ledger.jsonl").read_text().splitlines()
        ]
        assert sum(row["stage"] == "validate_passed" for row in ledger) == 1
        completed = next(row for row in ledger if row["stage"] == "lock_passed")
        assert completed["input_sha256"]
        assert completed["output_sha256"] == payload["manifest"]["bundle_id"]


def test_cli_failure_reports_exact_gaps_and_stage() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repo, run, output = fixture(pathlib.Path(directory))
        results = run / "_mirror" / "results.fixture-run.jsonl"
        results.write_text("\n".join(results.read_text().splitlines()[:-1]) + "\n")
        command = [
            sys.executable,
            str(SCRIPT),
            "promote",
            "--repo-root", str(repo),
            "--run-dir", str(run),
            "--output-root", str(output),
        ]
        for judge in JUDGES:
            command.extend(["--judge", judge])
        failed = subprocess.run(command, capture_output=True, text=True)
        assert failed.returncode == promotion.EXIT_INCOMPLETE
        payload = json.loads(failed.stderr)
        assert payload["stage"] == "normalize"
        assert payload["gate"] == "P3"
        assert payload["details"]["missing_results"] == [
            {"model": "model-b", "scenario": "s2", "rep": 1}
        ]
        ledger = [
            json.loads(line)
            for line in (output / ".state" / "fixture-run" / "promotion-ledger.jsonl").read_text().splitlines()
        ]
        assert ledger[-1]["stage"] == "normalize_failed"
        assert ledger[-1]["input_sha256"]
        assert ledger[-1]["detail"]["details"]["missing_results"]


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"completed-run promotion tests passed: {len(tests)}")


if __name__ == "__main__":
    main()