#!/usr/bin/env python3
"""Run a model/scenario selection across memory contexts sequentially.

The same file-backed worker supports two modes:
- `--runner e2e`: run on home, driving the full home+ai judge/commit pipeline.
- `--runner local-roster`: run directly on an ai-node checkout for inference-only
    sweeps with the same run-roster preflight, model pulls, reset/quiesce, telemetry,
    and rm-after behavior.

State lives under data/run-batches/<BATCH_ID>/ so CEOps and the CLI can observe
the batch without keeping a terminal attached.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN_BATCHES = REPO / "data" / "run-batches"
RUNS = REPO / "data" / "runs"
LOCK_PATH = RUN_BATCHES / ".active.lock"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
PATH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,160}$")
TERMINAL_OK = {"done"}
TERMINAL_BAD = {"canceled", "error"}


def utc_now() -> int:
    return int(time.time())


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}))
    raise SystemExit(code)


def safe_path(raw: object, suffix: str) -> Path:
    if not isinstance(raw, str) or not PATH_RE.match(raw) or raw.startswith("/") or ".." in Path(raw).parts:
        fail(f"unsafe path: {raw!r}")
    path = (REPO / raw).resolve()
    if not path.is_relative_to(REPO.resolve()) or path.suffix != suffix or not path.exists():
        fail(f"missing or invalid path: {raw!r}")
    return path


def load_matrix() -> dict:
    path = REPO / "data" / "run-matrix.json"
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        fail(f"run matrix is not valid JSON: {exc}")


def by_id(items: list[dict], key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in items:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not ID_RE.match(str(item_id or "")):
            fail(f"invalid {key} id: {item_id!r}")
        if item_id in out:
            fail(f"duplicate {key} id: {item_id}")
        out[item_id] = item
    return out


def resolve_selection(model_set_id: str, scenario_set_id: str, memory_context_ids: list[str]) -> tuple[dict, dict, list[dict]]:
    if not ID_RE.match(model_set_id) or not ID_RE.match(scenario_set_id):
        fail("invalid model or scenario set id")
    matrix = load_matrix()
    model_sets = by_id(matrix.get("model_sets", []), "model_set")
    scenario_sets = by_id(matrix.get("scenario_sets", []), "scenario_set")
    memory_contexts = by_id(matrix.get("memory_contexts", []), "memory_context")
    if model_set_id not in model_sets:
        fail(f"unknown model_set: {model_set_id}")
    if scenario_set_id not in scenario_sets:
        fail(f"unknown scenario_set: {scenario_set_id}")
    selected_memories = []
    seen = set()
    for memory_id in memory_context_ids:
        if not ID_RE.match(memory_id):
            fail(f"invalid memory_context: {memory_id}")
        if memory_id in seen:
            continue
        seen.add(memory_id)
        if memory_id not in memory_contexts:
            fail(f"unknown memory_context: {memory_id}")
        selected_memories.append(memory_contexts[memory_id])
    if not selected_memories:
        fail("at least one memory context is required")
    model_set = dict(model_sets[model_set_id])
    scenario_set = dict(scenario_sets[scenario_set_id])
    model_set["_path"] = str(safe_path(model_set.get("path"), ".txt").relative_to(REPO))
    scenario_set["_path"] = str(safe_path(scenario_set.get("path"), ".json").relative_to(REPO))
    for memory in selected_memories:
        if memory.get("path"):
            memory["_path"] = str(safe_path(memory.get("path"), ".md").relative_to(REPO))
        else:
            memory["_path"] = ""
    return model_set, scenario_set, selected_memories


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    with os.fdopen(fd, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def run_ids(batch_id: str, count: int) -> list[str]:
    return [f"{batch_id}-m{index}" for index in range(1, count + 1)]


def build_state(args: argparse.Namespace, model_set: dict, scenario_set: dict, memories: list[dict]) -> dict:
    ids = run_ids(args.batch_id, len(memories))
    return {
        "schema_version": 1,
        "batch_id": args.batch_id,
        "model_set": args.model_set,
        "scenario_set": args.scenario_set,
        "memory_contexts": [memory["id"] for memory in memories],
        "status": "running",
        "runner": args.runner,
        "user": args.user,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "current_index": 0,
        "stall_timeout_s": args.stall_timeout_s,
        "log": f"data/run-batches/{args.batch_id}/batch.log",
        "runs": [
            {
                "run_id": ids[index],
                "model_set": args.model_set,
                "scenario_set": args.scenario_set,
                "memory_context": memory["id"],
                "memory_context_file": memory.get("_path") or None,
                "status": "pending",
                "started_at": None,
                "ended_at": None,
                "progress_pct": 0.0,
                "units_done": 0,
                "units_total": 0,
                "last_progress_at": None,
            }
            for index, memory in enumerate(memories)
        ],
        "paths": {
            "models": model_set["_path"],
            "scenarios": scenario_set["_path"],
        },
    }


def append_log(batch_dir: Path, message: str) -> None:
    batch_dir.mkdir(parents=True, exist_ok=True)
    with (batch_dir / "batch.log").open("a") as handle:
        handle.write(f"[{iso_now()}] {message}\n")


def sha256(path: Path | None) -> str | None:
    if not path or not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_count(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#"))


def scenario_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    items = data.get("scenarios") if isinstance(data, dict) else data
    if not isinstance(items, list):
        fail(f"scenario file {path} must contain scenarios")
    return [item for item in items if isinstance(item, dict)]


def ensure_run_meta(state: dict, run: dict) -> None:
    run_dir = RUNS / run["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    meta_path = run_dir / "run.meta"
    models_path = REPO / state["paths"]["models"]
    scenarios_path = REPO / state["paths"]["scenarios"]
    memory_path = REPO / run["memory_context_file"] if run.get("memory_context_file") else None
    scenarios = scenario_items(scenarios_path)
    payload = {
        "schema_version": 2,
        "run_id": run["run_id"],
        "model_set": run["model_set"],
        "models": state["paths"]["models"],
        "models_sha256": sha256(models_path),
        "models_count": model_count(models_path),
        "scenario_set": run["scenario_set"],
        "scenarios": state["paths"]["scenarios"],
        "scenarios_sha256": sha256(scenarios_path),
        "memory_context": run["memory_context"],
        "memory_context_file": run.get("memory_context_file"),
        "memory_context_sha256": sha256(memory_path),
        "scenario_count": len(scenarios),
        "scenario_ids": [item.get("id") for item in scenarios if item.get("id")],
        "class_counts": {},
        "difficulty_counts": {},
        "grounding_counts": {},
        "reps": int(os.environ.get("REPS", "5")),
        "judges": int(os.environ.get("NJUDGES", "2")),
        "expect": model_count(models_path),
        "user": state.get("user") or "user",
        "started_at": run.get("started_at") or utc_now(),
        "runner": state.get("runner"),
        "judge_expected": state.get("runner") != "local-roster",
    }
    for key, source in (("class_counts", "class"), ("difficulty_counts", "difficulty"), ("grounding_counts", "grounding")):
        counts: dict[str, int] = {}
        for item in scenarios:
            value = item.get(source) or "unknown"
            counts[value] = counts.get(value, 0) + 1
        payload[key] = counts
    if meta_path.exists():
        existing = json.loads(meta_path.read_text())
        keys = ("models", "models_sha256", "scenarios", "scenarios_sha256", "memory_context", "memory_context_sha256")
        mismatches = [key for key in keys if existing.get(key) != payload.get(key)]
        if mismatches:
            raise RuntimeError(f"existing run.meta for {run['run_id']} does not match this batch: {', '.join(mismatches)}")
    else:
        write_json_atomic(meta_path, payload)


def mirror_local_run(run_id: str) -> None:
    mirror_dir = RUNS / run_id / "_mirror"
    mirror_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("jsonl", "jsonl.done"):
        src = REPO / f"results.{run_id}.{suffix}"
        if src.exists():
            shutil.copy2(src, mirror_dir / src.name)
    log_src = REPO / "logs" / run_id / "driver.log"
    if log_src.exists():
        e2e_log = RUNS / run_id / "e2e.log"
        if not e2e_log.exists():
            e2e_log.write_text(f"[{iso_now()}] local-roster run {run_id}\n")


def local_roster_done(state: dict, run_id: str) -> bool:
    meta = json.loads((RUNS / run_id / "run.meta").read_text())
    expect = int(meta.get("expect") or 0)
    done_path = REPO / f"results.{run_id}.jsonl.done"
    result_path = REPO / f"results.{run_id}.jsonl"
    if not expect or not done_path.exists() or not result_path.exists():
        return False
    models_path = REPO / state["paths"]["models"]
    scenarios_path = REPO / state["paths"]["scenarios"]
    if meta.get("models_sha256") != sha256(models_path) or meta.get("scenarios_sha256") != sha256(scenarios_path):
        raise RuntimeError(f"run.meta hash mismatch for {run_id}")
    expected_memory = meta.get("memory_context")
    expected_memory_sha = meta.get("memory_context_sha256")
    expected_scenario_sha = meta.get("scenarios_sha256")
    expected_models = {
        line.strip().split()[0]
        for line in models_path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    expected_scenarios = {item.get("id") for item in scenario_items(scenarios_path) if item.get("id")}
    expected_reps = set(range(int(meta.get("reps") or 5)))
    expected_units = {(scenario_id, rep) for scenario_id in expected_scenarios for rep in expected_reps}
    seen_models = set()
    with done_path.open(errors="ignore") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            model = payload.get("model")
            if model:
                seen_models.add(model)
    rows_by_model: dict[str, set[tuple[str, int]]] = {}
    with result_path.open(errors="ignore") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (row.get("env.memory_context") or "none") != expected_memory:
                raise RuntimeError(f"result memory_context mismatch for {run_id}")
            if row.get("env.memory_context_sha") != expected_memory_sha:
                raise RuntimeError(f"result memory hash mismatch for {run_id}")
            if row.get("env.scenarios_sha") != expected_scenario_sha:
                raise RuntimeError(f"result scenario hash mismatch for {run_id}")
            model = row.get("model")
            scenario_id = row.get("scenario")
            rep = row.get("rep")
            if model and scenario_id in expected_scenarios and rep in expected_reps and row.get("det_total") is not None:
                rows_by_model.setdefault(model, set()).add((scenario_id, rep))
    return expected_models <= seen_models and all(expected_units <= rows_by_model.get(model, set()) for model in expected_models)


def load_status(run_id: str) -> dict:
    cp = subprocess.run(
        [sys.executable, "scripts/pipeline-status.py", run_id],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if cp.returncode != 0:
        return {"state": "error", "error": (cp.stderr or cp.stdout).strip()[:800]}
    try:
        return json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        return {"state": "error", "error": f"status was not JSON: {exc}"}


def launch_run(state: dict, run_index: int, batch_dir: Path, poll_s: int) -> None:
    run = state["runs"][run_index]
    env = os.environ.copy()
    env.update({
        "RUN_ID": run["run_id"],
        "MODELS": state["paths"]["models"],
        "MODEL_SET": run["model_set"],
        "SCENARIOS": state["paths"]["scenarios"],
        "SCENARIO_SET": run["scenario_set"],
        "MEMORY_CONTEXT": run["memory_context"],
        "MEMORY_CONTEXT_FILE": run.get("memory_context_file") or "",
        "RUN_USER": state.get("user") or "user",
    })
    run["status"] = "starting"
    run["started_at"] = utc_now()
    state["current_index"] = run_index
    state["updated_at"] = utc_now()
    write_json_atomic(batch_dir / "batch-state.json", state)
    append_log(batch_dir, f"launching {run['run_id']} memory_context={run['memory_context']}")
    ensure_run_meta(state, run)
    command = ["./scripts/run-e2e.sh"] if state.get("runner") == "e2e" else ["./scripts/run-roster.sh"]
    with (batch_dir / f"{run['run_id']}.boot.log").open("a") as out:
        proc = subprocess.Popen(
            command,
            cwd=REPO,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
        )

    stopped_checks = 0
    last_units_done = -1
    last_progress_at = time.time()
    while True:
        if state.get("runner") == "local-roster":
            mirror_local_run(run["run_id"])
        status = load_status(run["run_id"])
        run_state = status.get("state") or "unknown"
        proc_rc = proc.poll()
        if state.get("runner") == "local-roster" and proc_rc is None:
            run_state = "running"
        elif state.get("runner") == "local-roster" and proc_rc not in (None, 0):
            run_state = "error"
        elif state.get("runner") == "local-roster" and proc_rc == 0:
            run_state = "done" if local_roster_done(state, run["run_id"]) else "stopped"
        run["status"] = run_state
        progress = status.get("progress") or {}
        run["progress_pct"] = progress.get("pct") or 0.0
        units_done = int(progress.get("units_done") or 0)
        run["units_done"] = units_done
        run["units_total"] = int(progress.get("units_total") or 0)
        if units_done != last_units_done:
            last_units_done = units_done
            last_progress_at = time.time()
            run["last_progress_at"] = utc_now()
        run["updated_at"] = utc_now()
        state["updated_at"] = utc_now()
        write_json_atomic(batch_dir / "batch-state.json", state)
        append_log(batch_dir, f"{run['run_id']} state={run_state} pct={run['progress_pct']}")
        if run_state in TERMINAL_OK:
            if proc.poll() is None:
                proc.wait(timeout=30)
            run["ended_at"] = utc_now()
            run["progress_pct"] = 100.0
            write_json_atomic(batch_dir / "batch-state.json", state)
            append_log(batch_dir, f"completed {run['run_id']}")
            return
        if run_state in TERMINAL_BAD:
            if proc.poll() is None:
                proc.terminate()
            run["ended_at"] = utc_now()
            state["status"] = "failed"
            write_json_atomic(batch_dir / "batch-state.json", state)
            raise RuntimeError(f"{run['run_id']} ended as {run_state}")
        if run_state == "stopped":
            stopped_checks += 1
            if stopped_checks >= 10:
                run["ended_at"] = utc_now()
                state["status"] = "failed"
                write_json_atomic(batch_dir / "batch-state.json", state)
                raise RuntimeError(f"{run['run_id']} stayed stopped")
        else:
            stopped_checks = 0
        stall_timeout_s = int(state.get("stall_timeout_s") or 0)
        if run_state == "running" and stall_timeout_s > 0 and time.time() - last_progress_at > stall_timeout_s:
            run["ended_at"] = utc_now()
            state["status"] = "failed"
            state["error"] = f"{run['run_id']} made no progress for {stall_timeout_s}s"
            write_json_atomic(batch_dir / "batch-state.json", state)
            raise RuntimeError(state["error"])
        time.sleep(poll_s)


def active(_: argparse.Namespace) -> None:
    RUN_BATCHES.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"active": True, "reason": "batch lock held"}))
            return
        print(json.dumps({"active": False}))


def launch(args: argparse.Namespace) -> None:
    if not RUN_ID_RE.match(args.batch_id) or len(args.batch_id) > 70:
        fail("invalid batch_id")
    model_set, scenario_set, memories = resolve_selection(args.model_set, args.scenario_set, args.memory_context)
    ids = run_ids(args.batch_id, len(memories))
    if any(not RUN_ID_RE.match(run_id) or len(run_id) > 80 for run_id in ids):
        fail("generated run_id is invalid")
    batch_dir = RUN_BATCHES / args.batch_id
    RUN_BATCHES.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("another memory batch is already active", code=3)
        state = build_state(args, model_set, scenario_set, memories)
        write_json_atomic(batch_dir / "batch-state.json", state)
        append_log(batch_dir, f"batch started model_set={args.model_set} scenario_set={args.scenario_set} memory_contexts={','.join(state['memory_contexts'])}")
        try:
            for index in range(len(state["runs"])):
                launch_run(state, index, batch_dir, args.poll_s)
            state["status"] = "done"
            state["updated_at"] = utc_now()
            write_json_atomic(batch_dir / "batch-state.json", state)
            append_log(batch_dir, "batch completed")
        except Exception as exc:  # noqa: BLE001
            state["status"] = "failed"
            state["error"] = str(exc)
            state["updated_at"] = utc_now()
            write_json_atomic(batch_dir / "batch-state.json", state)
            append_log(batch_dir, f"batch failed: {exc}")
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    active_p = sub.add_parser("active")
    active_p.set_defaults(func=active)
    launch_p = sub.add_parser("launch")
    launch_p.add_argument("--batch-id", required=True)
    launch_p.add_argument("--model-set", required=True)
    launch_p.add_argument("--scenario-set", required=True)
    launch_p.add_argument("--memory-context", action="append", required=True)
    launch_p.add_argument("--runner", choices=("e2e", "local-roster"), default="e2e",
                          help="e2e drives the full home+ai pipeline; local-roster runs scripts/run-roster.sh on this node")
    launch_p.add_argument("--user", default="user")
    launch_p.add_argument("--poll-s", type=int, default=60)
    launch_p.add_argument("--stall-timeout-s", type=int, default=7200,
                          help="fail a running child run after this many seconds without progress; 0 disables")
    launch_p.set_defaults(func=launch)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
