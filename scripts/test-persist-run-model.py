#!/usr/bin/env python3
"""Regression tests for local per-model persistence."""

from __future__ import annotations

import gzip
import importlib.util
import json
import pathlib
import tarfile
import tempfile

SCRIPT = pathlib.Path(__file__).with_name("persist-run-model.py")
spec = importlib.util.spec_from_file_location("persist_run_model", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

FIXTURE_SCENARIOS = json.dumps({"scenarios": [{"id": "s1"}, {"id": "s2"}]}) + "\n"
FIXTURE_SCENARIO_SHA = __import__("hashlib").sha256(FIXTURE_SCENARIOS.encode()).hexdigest()


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def fixture(root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path, pathlib.Path]:
    results = root / "results.jsonl"
    judged = root / "judged.jsonl"
    outputs = root / "outputs"
    run_dir = root / "run"
    scenarios = root / "scenarios.json"
    scenarios.write_text(FIXTURE_SCENARIOS)
    def result(model: str, scenario: str) -> dict:
        return {
            "model": model,
            "scenario": scenario,
            "rep": 0,
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
            "env.scenarios_sha": FIXTURE_SCENARIO_SHA,
            "strategy.candidates": [{"index": 0}],
        }

    rows = [result("model/a:1", "s1"), result("model/a:1", "s2"), result("other", "s1")]
    write_jsonl(results, rows)
    judges = frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")})
    policy, conditions, _condition_set = module.result_condition_contract(
        [row for row in rows if row["model"] == "model/a:1"], judges
    )
    write_jsonl(judged, [
        {
            "model": "model/a:1", "scenario": scenario, "rep": 0,
            "scenarios_sha256": FIXTURE_SCENARIO_SHA,
            "analysis_condition_key_sha256": conditions[(scenario, 0)],
            "condition_identity_incomplete": False,
            "evaluation_policy": policy,
            "judge_backend": "copilot", "judge_model": judge,
            "score": 4, "verdict": "ok", "evidence": "grounded",
            "criteria_met": ["safe"], "criteria_missed": [],
        }
        for scenario in ("s1", "s2")
        for judge in ("claude-test", "gpt-test")
    ])
    write_jsonl(outputs / "model_a_1__s1__r0.candidates.jsonl", [
        {"model": "model/a:1", "scenario": "s1", "rep": 0, "index": 0},
    ])
    write_jsonl(outputs / "model_a_1__s2__r0.candidates.jsonl", [
        {"model": "model/a:1", "scenario": "s2", "rep": 0, "index": 0},
    ])
    return results, judged, outputs, run_dir, scenarios


def test_complete_model_is_persisted_deterministically() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        first = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        second = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        assert first == second
        assert first["result_rows"] == first["candidate_files"] == 2
        assert first["canonical_judgements"] == first["judge_attempts"] == 4
        with gzip.open(run_dir / first["result_archive"], "rt") as handle:
            assert len(handle.readlines()) == 2
        with tarfile.open(run_dir / first["candidate_archive"], "r:gz") as archive:
            assert archive.getnames() == [
                "model_a_1__s1__r0.candidates.jsonl",
                "model_a_1__s2__r0.candidates.jsonl",
            ]
        verified = module.verify_receipt(
            run_dir,
            run_dir / first["receipt"],
            "model/a:1",
            judged,
            results,
            outputs,
            scenarios,
            1,
            frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            FIXTURE_SCENARIO_SHA,
        )
        assert verified["result_archive_sha256"] == first["result_archive_sha256"]


def test_validate_only_checks_full_domain_without_writing() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        validated = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            validate_only=True,
        )
        assert validated == {
            "candidate_files": 2,
            "canonical_judgements": 4,
            "judge_attempts": 4,
            "judge_retries": 0,
            "model": "model/a:1",
            "result_rows": 2,
            "units": 2,
            "validated": True,
        }
        assert not run_dir.exists()


def test_missing_candidate_refuses_persistence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        (outputs / "model_a_1__s2__r0.candidates.jsonl").unlink()
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256=FIXTURE_SCENARIO_SHA,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            )
        except ValueError as exc:
            assert "candidate domain differs" in str(exc)
        else:
            raise AssertionError("missing candidate sidecar was accepted")


def test_wrong_scenario_hash_refuses_persistence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256="b" * 64,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            )
        except ValueError as exc:
            assert "mismatched scenario hashes" in str(exc)
        else:
            raise AssertionError("wrong scenario hash was accepted")


def test_parse_failure_without_success_refuses_persistence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        rows = [json.loads(line) for line in judged.read_text().splitlines()]
        rows[0].update({
            "score": None,
            "verdict": "parse_error",
            "evidence": "parse_error",
            "criteria_met": [],
            "criteria_missed": ["judge response could not be parsed"],
        })
        write_jsonl(judged, rows)
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256=FIXTURE_SCENARIO_SHA,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            )
        except ValueError as exc:
            assert "exactly one successful judgement" in str(exc)
        else:
            raise AssertionError("unresolved judge parse failure was accepted")


def test_substituted_judge_identity_refuses_persistence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        rows = [json.loads(line) for line in judged.read_text().splitlines()]
        rows[0]["judge_model"] = "substituted-judge"
        write_jsonl(judged, rows)
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256=FIXTURE_SCENARIO_SHA,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                validate_only=True,
            )
        except ValueError as exc:
            assert "judgement domain differs" in str(exc)
        else:
            raise AssertionError("substituted judge identity was accepted")


def test_same_tuple_alternate_condition_refuses_persistence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        rows = [json.loads(line) for line in judged.read_text().splitlines()]
        rows[0]["analysis_condition_key_sha256"] = "f" * 64
        write_jsonl(judged, rows)
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256=FIXTURE_SCENARIO_SHA,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                validate_only=True,
            )
        except ValueError as exc:
            assert "judgement condition differs from result" in str(exc)
        else:
            raise AssertionError("alternate-condition judgement was accepted")


def test_valid_parse_retry_is_retained() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        rows = [json.loads(line) for line in judged.read_text().splitlines()]
        retry = dict(rows[0])
        retry.update({
            "score": None,
            "verdict": "parse_error",
            "evidence": "parse_error",
            "criteria_met": [],
            "criteria_missed": ["judge response could not be parsed"],
        })
        write_jsonl(judged, [retry, *rows])
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        assert persisted["judge_retries"] == 1


def test_foreign_candidate_row_refuses_persistence() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        path = outputs / "model_a_1__s1__r0.candidates.jsonl"
        with path.open("a") as handle:
            handle.write(json.dumps({"model": "foreign", "scenario": "s1", "rep": 0}) + "\n")
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256=FIXTURE_SCENARIO_SHA,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            )
        except ValueError as exc:
            assert "foreign model" in str(exc)
        else:
            raise AssertionError("foreign candidate row was accepted")


def test_tampered_archive_invalidates_receipt() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        with (run_dir / persisted["result_archive"]).open("ab") as handle:
            handle.write(b"tamper")
        try:
            module.verify_receipt(run_dir, run_dir / persisted["receipt"], "model/a:1")
        except ValueError as exc:
            assert "hash mismatch" in str(exc)
        else:
            raise AssertionError("tampered archive passed receipt verification")


def test_changed_judgement_attempts_invalidate_receipt() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        retry = json.loads(judged.read_text().splitlines()[0])
        retry.update({
            "score": None,
            "evidence": "parse_error",
            "criteria_met": [],
            "criteria_missed": ["judge response could not be parsed"],
        })
        with judged.open("a") as handle:
            handle.write(json.dumps(retry) + "\n")
        try:
            module.verify_receipt(
                run_dir,
                run_dir / persisted["receipt"],
                "model/a:1",
                judged,
                results,
                outputs,
                scenarios,
                1,
                frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                FIXTURE_SCENARIO_SHA,
            )
        except ValueError as exc:
            assert (
                "result archive domain differs" in str(exc)
                or "judgement attempts differ" in str(exc)
            )
        else:
            raise AssertionError("changed judgement attempts passed receipt verification")


def test_changed_results_invalidate_receipt() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        rows = [json.loads(line) for line in results.read_text().splitlines()]
        rows[0]["gen_ai.completion"] = "changed"
        write_jsonl(results, rows)
        try:
            module.verify_receipt(
                run_dir,
                run_dir / persisted["receipt"],
                "model/a:1",
                judged,
                results,
                outputs,
                scenarios,
                1,
                frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                FIXTURE_SCENARIO_SHA,
            )
        except ValueError as exc:
            assert "current results differ" in str(exc)
        else:
            raise AssertionError("changed results passed receipt verification")


def test_coordinated_archive_and_receipt_tamper_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        archive = run_dir / persisted["result_archive"]
        with gzip.open(archive, "rt") as handle:
            archive_rows = [json.loads(line) for line in handle if line.strip()]
        archive_rows[0]["gen_ai.completion"] = "coordinated tamper"
        payload = module.canonical_result_payload(archive_rows)
        module.atomic_deterministic_gzip(archive, payload)
        receipt_path = run_dir / persisted["receipt"]
        receipt = json.loads(receipt_path.read_text())
        receipt["result_archive_sha256"] = module.sha256_file(archive)
        receipt["result_rows_sha256"] = __import__("hashlib").sha256(payload).hexdigest()
        module.atomic_write_bytes(
            receipt_path,
            json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n",
        )
        try:
            module.verify_receipt(
                run_dir,
                receipt_path,
                "model/a:1",
                judged,
                results,
                outputs,
                scenarios,
                1,
                frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                FIXTURE_SCENARIO_SHA,
            )
        except ValueError as exc:
            assert "current results differ" in str(exc)
        else:
            raise AssertionError("coordinated archive and receipt tamper was accepted")


def test_coordinated_duplicate_result_and_receipt_tamper_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        archive = run_dir / persisted["result_archive"]
        with gzip.open(archive, "rt") as handle:
            archive_rows = [json.loads(line) for line in handle if line.strip()]
        duplicate = dict(archive_rows[0])
        duplicate["analysis_condition_key_sha256"] = "f" * 64
        archive_rows.append(duplicate)
        payload = module.canonical_result_payload(archive_rows)
        module.atomic_deterministic_gzip(archive, payload)
        receipt_path = run_dir / persisted["receipt"]
        receipt = json.loads(receipt_path.read_text())
        receipt["result_archive_sha256"] = module.sha256_file(archive)
        receipt["result_rows"] = receipt["units"] = 3
        receipt["candidate_files"] = 3
        receipt["result_rows_sha256"] = __import__("hashlib").sha256(payload).hexdigest()
        module.atomic_write_bytes(
            receipt_path,
            json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n",
        )
        try:
            module.verify_receipt(
                run_dir,
                receipt_path,
                "model/a:1",
                judged,
                results,
                outputs,
                scenarios,
                1,
                frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                FIXTURE_SCENARIO_SHA,
            )
        except ValueError as exc:
            assert (
                "result archive" in str(exc)
                or "condition hash differs" in str(exc)
                or "cardinality" in str(exc)
            )
        else:
            raise AssertionError("coordinated duplicate result/receipt tamper was accepted")


def test_receipt_count_tamper_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        receipt_path = run_dir / persisted["receipt"]
        receipt = json.loads(receipt_path.read_text())
        receipt["canonical_judgements"] = 99
        module.atomic_write_bytes(
            receipt_path,
            json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n",
        )
        try:
            module.verify_receipt(
                run_dir,
                receipt_path,
                "model/a:1",
                judged,
                results,
                outputs,
                scenarios,
                1,
                frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                FIXTURE_SCENARIO_SHA,
            )
        except ValueError as exc:
            assert (
                "result archive domain differs" in str(exc)
                or "judgement attempts differ" in str(exc)
            )
        else:
            raise AssertionError("receipt judgement count tamper was accepted")


def test_fractional_repetition_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        rows = [json.loads(line) for line in results.read_text().splitlines()]
        rows[0]["rep"] = 0.5
        write_jsonl(results, rows)
        try:
            module.persist_model(
                results_path=results,
                judged_path=judged,
                outputs_dir=outputs,
                run_dir=run_dir,
                model="model/a:1",
                units=2,
                scenario_sha256=FIXTURE_SCENARIO_SHA,
                scenarios_path=scenarios,
                reps=1,
                judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
            )
        except ValueError as exc:
            assert "must be an integer" in str(exc)
        else:
            raise AssertionError("fractional repetition was accepted")


def test_coordinated_candidate_archive_and_receipt_tamper_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as directory:
        results, judged, outputs, run_dir, scenarios = fixture(pathlib.Path(directory))
        persisted = module.persist_model(
            results_path=results,
            judged_path=judged,
            outputs_dir=outputs,
            run_dir=run_dir,
            model="model/a:1",
            units=2,
            scenario_sha256=FIXTURE_SCENARIO_SHA,
            scenarios_path=scenarios,
            reps=1,
            judges=frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
        )
        archive = run_dir / persisted["candidate_archive"]
        source_files = sorted(outputs.glob("model_a_1__*.candidates.jsonl"))
        source_files[0].write_text(json.dumps({
            "model": "model/a:1", "scenario": "s1", "rep": 0, "index": 999,
        }) + "\n")
        module.atomic_write_bytes(archive, module.deterministic_tar_gzip(source_files))
        receipt_path = run_dir / persisted["receipt"]
        receipt = json.loads(receipt_path.read_text())
        receipt["candidate_archive_sha256"] = module.sha256_file(archive)
        module.atomic_write_bytes(
            receipt_path,
            json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode() + b"\n",
        )
        try:
            module.verify_receipt(
                run_dir,
                receipt_path,
                "model/a:1",
                judged,
                results,
                outputs,
                scenarios,
                1,
                frozenset({("copilot", "claude-test"), ("copilot", "gpt-test")}),
                FIXTURE_SCENARIO_SHA,
            )
        except ValueError as exc:
            assert (
                "payload differs from result strategy candidates" in str(exc)
                or "current candidates differ" in str(exc)
                or "hash mismatch" in str(exc)
            )
        else:
            raise AssertionError("coordinated candidate archive and receipt tamper was accepted")


if __name__ == "__main__":
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"local persistence tests passed: {len(tests)}")