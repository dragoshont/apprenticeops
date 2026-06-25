#!/usr/bin/env python3
"""File-backed experiment-plan controller.

This is the no-UI control plane for phased experiments. The dashboard calls the
same script, so UI and CLI share one source of truth: data/run-matrix.json plus
data/experiments/<experiment_id>/phase-state.json.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MATRIX = REPO / "data" / "run-matrix.json"
EXPERIMENTS = REPO / "data" / "experiments"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}), file=sys.stderr)
    raise SystemExit(code)


def now() -> int:
    return int(time.time())


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        fail(f"cannot read JSON {path}: {exc}")


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    with os.fdopen(fd, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def append_event(exp_dir: Path, event: dict) -> None:
    exp_dir.mkdir(parents=True, exist_ok=True)
    with open(exp_dir / "phase-ledger.jsonl", "a") as handle:
        handle.write(json.dumps({"ts": now(), **event}, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def sha256(path: Path | None) -> str | None:
    if not path:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_count(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith("#"))


def load_scenarios(path: Path) -> list[dict]:
    data = load_json(path)
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list):
        fail(f"scenario file {path} must contain scenarios list")
    return scenarios


def safe_rel(raw: str, suffix: str | None = None) -> Path:
    if not raw:
        fail("empty path in run matrix")
    path = (REPO / raw).resolve()
    if not str(path).startswith(str(REPO.resolve()) + os.sep):
        fail(f"path escapes repo: {raw}")
    if suffix and path.suffix != suffix:
        fail(f"path has wrong suffix: {raw}")
    if not path.exists():
        fail(f"missing path: {raw}")
    return path


def matrix() -> dict:
    return load_json(MATRIX)


def by_id(items: list[dict], key: str) -> dict[str, dict]:
    out = {}
    for item in items:
        item_id = item.get("id")
        if not item_id or item_id in out:
            fail(f"missing/duplicate {key} id: {item_id!r}")
        out[item_id] = item
    return out


def resolve(plan_id: str, model_set: str, scenario_set: str) -> tuple[dict, dict, dict, dict]:
    m = matrix()
    plans = by_id(m.get("experiment_plans", []), "experiment_plan")
    models = by_id(m.get("model_sets", []), "model_set")
    scenarios = by_id(m.get("scenario_sets", []), "scenario_set")
    memories = by_id(m.get("memory_contexts", []), "memory_context")
    if plan_id not in plans:
        fail(f"unknown experiment plan: {plan_id}")
    if model_set not in models:
        fail(f"unknown model_set: {model_set}")
    if scenario_set not in scenarios:
        fail(f"unknown scenario_set: {scenario_set}")
    return plans[plan_id], models[model_set], scenarios[scenario_set], memories


def experiment_dir(experiment_id: str) -> Path:
    if not ID_RE.match(experiment_id or ""):
        fail(f"invalid experiment_id: {experiment_id!r}")
    return EXPERIMENTS / experiment_id


@contextlib.contextmanager
def experiment_lock(experiment_id: str):
    exp_dir = experiment_dir(experiment_id)
    exp_dir.mkdir(parents=True, exist_ok=True)
    with open(exp_dir / ".phase.lock", "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def state_path(experiment_id: str) -> Path:
    return experiment_dir(experiment_id) / "phase-state.json"


def load_state(experiment_id: str) -> dict:
    path = state_path(experiment_id)
    if not path.exists():
        fail(f"unknown experiment_id: {experiment_id}")
    return load_json(path)


def phase_index(state: dict, phase_id: str) -> int:
    for index, phase in enumerate(state.get("phases", [])):
        if phase.get("id") == phase_id:
            return index
    fail(f"unknown phase_id: {phase_id}")


def new_experiment_id(plan_id: str, model_set: str, scenario_set: str) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return f"exp-{plan_id}-{model_set}-{scenario_set}-{ts}"[:80]


def build_state(experiment_id: str, plan_id: str, model_set_id: str, scenario_set_id: str, user: str) -> dict:
    plan, model_set, scenario_set, memories = resolve(plan_id, model_set_id, scenario_set_id)
    model_path = safe_rel(model_set["path"], ".txt")
    scenario_path = safe_rel(scenario_set["path"], ".json")
    scenario_items = load_scenarios(scenario_path)
    phases = []
    for index, phase in enumerate(plan.get("phases", []), start=1):
        memory_id = phase.get("memory_context")
        if memory_id not in memories:
            fail(f"phase {phase.get('id')} references unknown memory_context {memory_id!r}")
        memory = memories[memory_id]
        memory_path = safe_rel(memory["path"], ".md") if memory.get("path") else None
        phases.append({
            "id": phase["id"],
            "label": phase.get("label") or phase["id"],
            "order": index,
            "memory_context": memory_id,
            "memory_context_file": str(memory_path.relative_to(REPO)) if memory_path else None,
            "memory_context_sha256": sha256(memory_path),
            "gate": phase.get("gate"),
            "run_id": f"{experiment_id}-p{index}",
            "status": "pending",
        })
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "plan_id": plan_id,
        "model_set": model_set_id,
        "models": model_set["path"],
        "models_sha256": sha256(model_path),
        "models_count": model_count(model_path),
        "scenario_set": scenario_set_id,
        "scenarios": scenario_set["path"],
        "scenarios_sha256": sha256(scenario_path),
        "scenario_count": len(scenario_items),
        "created_at": now(),
        "user": user or "user",
        "gate": plan.get("gate"),
        "phases": phases,
    }


def init(args: argparse.Namespace) -> dict:
    experiment_id = args.experiment_id or new_experiment_id(args.plan_id, args.model_set, args.scenario_set)
    with experiment_lock(experiment_id):
        path = state_path(experiment_id)
        if path.exists() and not args.force:
            fail(f"phase state already exists: {path}")
        state = build_state(experiment_id, args.plan_id, args.model_set, args.scenario_set, args.user)
        write_json_atomic(path, state)
        append_event(path.parent, {"event": "initialized", "experiment_id": experiment_id, "plan_id": args.plan_id})
        return {"ok": True, "experiment_id": experiment_id, "state": state}


def latest_ready(plan_id: str, model_set: str, scenario_set: str, phase_id: str) -> str | None:
    candidates = []
    for path in EXPERIMENTS.glob("*/phase-state.json"):
        try:
            state = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            continue
        if (state.get("plan_id"), state.get("model_set"), state.get("scenario_set")) != (plan_id, model_set, scenario_set):
            continue
        try:
            index = phase_index(state, phase_id)
        except SystemExit:
            continue
        prior_ok = all(phase.get("status") == "completed" for phase in state["phases"][:index])
        current_pending = state["phases"][index].get("status") == "pending"
        if prior_ok and current_pending:
            candidates.append((path.stat().st_mtime, state["experiment_id"]))
    return sorted(candidates)[-1][1] if candidates else None


def previous_phases_completed(state: dict, index: int) -> None:
    for prior in state["phases"][:index]:
        if prior.get("status") != "completed":
            fail(f"phase {prior['id']} must be completed before launching next phase")


def launch_phase(args: argparse.Namespace) -> dict:
    experiment_id = args.experiment_id
    if not experiment_id:
        plan, _, _, _ = resolve(args.plan_id, args.model_set, args.scenario_set)
        first_phase = plan.get("phases", [{}])[0].get("id")
        if args.phase_id == first_phase:
            experiment_id = new_experiment_id(args.plan_id, args.model_set, args.scenario_set)
            init(argparse.Namespace(experiment_id=experiment_id, plan_id=args.plan_id,
                                    model_set=args.model_set, scenario_set=args.scenario_set,
                                    user=args.user, force=False))
        else:
            experiment_id = latest_ready(args.plan_id, args.model_set, args.scenario_set, args.phase_id)
            if not experiment_id:
                fail("no ready experiment found for this phase; run and review the prior phase first")
    with experiment_lock(experiment_id):
        state = load_state(experiment_id)
        index = phase_index(state, args.phase_id)
        previous_phases_completed(state, index)
        phase = state["phases"][index]
        if phase.get("status") not in ("pending",):
            fail(f"phase {phase['id']} status is {phase.get('status')}, not pending")
        phase["status"] = "running"
        phase["started_at"] = now()
        state_file = state_path(state["experiment_id"])
        write_json_atomic(state_file, state)
        append_event(state_file.parent, {"event": "phase_started", "phase_id": phase["id"], "run_id": phase["run_id"]})
        launch = {"state": state, "phase": dict(phase)}
    state = launch["state"]
    phase = launch["phase"]
    if not args.dry_run:
        env = os.environ.copy()
        env.update({
            "RUN_ID": phase["run_id"],
            "MODELS": state["models"],
            "MODEL_SET": state["model_set"],
            "SCENARIOS": state["scenarios"],
            "SCENARIO_SET": state["scenario_set"],
            "MEMORY_CONTEXT": phase["memory_context"],
            "MEMORY_CONTEXT_FILE": phase.get("memory_context_file") or "",
            "RUN_USER": state.get("user") or "user",
            "EXPERIMENT_ID": state["experiment_id"],
            "EXPERIMENT_PLAN": state["plan_id"],
            "EXPERIMENT_PHASE": phase["id"],
        })
        boot = Path(f"/tmp/e2e.{phase['run_id']}.boot")
        with open(boot, "w") as out:
            subprocess.Popen(["./scripts/run-e2e.sh"], cwd=REPO, env=env,
                             stdin=subprocess.DEVNULL, stdout=out,
                             stderr=subprocess.STDOUT, start_new_session=True)
    return {"ok": True, "experiment_id": state["experiment_id"], "phase_id": phase["id"],
            "run_id": phase["run_id"], "dry_run": args.dry_run}


def line_count(path: Path) -> int:
    try:
        return sum(1 for line in path.read_text(errors="ignore").splitlines() if line.strip())
    except OSError:
        return 0


def run_markers(run_dir: Path) -> dict:
    return {"canceled": (run_dir / ".canceled").exists(), "paused": (run_dir / ".paused").exists()}


def gate_phase(args: argparse.Namespace) -> dict:
    with experiment_lock(args.experiment_id):
        state = load_state(args.experiment_id)
        index = phase_index(state, args.phase_id)
        phase = state["phases"][index]
    run_id = phase.get("run_id")
    run_dir = REPO / "data" / "runs" / run_id
    problems = []
    meta_path = run_dir / "run.meta"
    meta = load_json(meta_path) if meta_path.exists() else {}
    if not meta:
        problems.append("run.meta missing")
    checks = {
        "model_set": state["model_set"],
        "models_sha256": state["models_sha256"],
        "scenario_set": state["scenario_set"],
        "scenarios_sha256": state["scenarios_sha256"],
        "memory_context": phase["memory_context"],
        "memory_context_sha256": phase.get("memory_context_sha256"),
    }
    for key, expected in checks.items():
        if expected is not None and meta.get(key) != expected:
            problems.append(f"run.meta {key}={meta.get(key)!r} expected {expected!r}")
    markers = run_markers(run_dir)
    if markers["canceled"]:
        problems.append("run was canceled")
    if markers["paused"]:
        problems.append("run is paused")
    expect = int(meta.get("expect") or state.get("models_count") or 0)
    scenario_count = int(meta.get("scenario_count") or state.get("scenario_count") or 0)
    reps = int(meta.get("reps") or 5)
    judges = int(meta.get("judges") or 2)
    committed = line_count(run_dir / ".committed")
    judged = line_count(run_dir / f"judged.{run_id}.jsonl")
    expected_judged = expect * scenario_count * reps * judges
    if committed < expect:
        problems.append(f"committed models {committed} < expected {expect}")
    if judged < expected_judged:
        problems.append(f"judged rows {judged} < expected {expected_judged}")
    results = run_dir / "_mirror" / f"results.{run_id}.jsonl"
    if not results.exists():
        problems.append("mirrored results jsonl missing")
    elif not args.skip_audit:
        cp = subprocess.run(["python3", "scripts/audit-run.py", str(results)], cwd=REPO,
                            capture_output=True, text=True, check=False)
        if cp.returncode != 0:
            problems.append("audit-run failed: " + (cp.stdout + cp.stderr).strip()[:500])
    report = {
        "phase_id": phase["id"],
        "run_id": run_id,
        "ok": not problems,
        "checked_at": now(),
        "problems": problems,
        "counts": {"expect": expect, "scenario_count": scenario_count,
                   "reps": reps, "judges": judges, "committed": committed,
                   "judged": judged, "expected_judged": expected_judged},
    }
    gate_dir = experiment_dir(state["experiment_id"]) / "gates"
    write_json_atomic(gate_dir / f"{phase['id']}.json", report)
    with experiment_lock(args.experiment_id):
        state = load_state(args.experiment_id)
        phase = state["phases"][phase_index(state, args.phase_id)]
        phase["gate_report"] = str((gate_dir / f"{phase['id']}.json").relative_to(REPO))
        phase["status"] = "review_pending" if report["ok"] else "failed"
        phase["gate_checked_at"] = report["checked_at"]
        write_json_atomic(state_path(state["experiment_id"]), state)
        append_event(experiment_dir(state["experiment_id"]), {"event": "gate_passed" if report["ok"] else "gate_failed",
                                                               "phase_id": phase["id"], "run_id": run_id,
                                                               "problems": problems})
    return {"ok": report["ok"], "experiment_id": state["experiment_id"], "report": report}


def review_phase(args: argparse.Namespace) -> dict:
    with experiment_lock(args.experiment_id):
        state = load_state(args.experiment_id)
        index = phase_index(state, args.phase_id)
        phase = state["phases"][index]
        gate_path = phase.get("gate_report")
        if not gate_path:
            fail("gate report missing; run gate first")
        gate_report = load_json(REPO / gate_path)
        if not gate_report.get("ok"):
            fail("gate did not pass; cannot mark review pass")
        verdict = args.verdict.upper()
        if verdict not in ("PASS", "REVISE", "FAIL"):
            fail("review verdict must be PASS, REVISE, or FAIL")
        phase["review"] = {"verdict": verdict, "reviewer": args.reviewer,
                           "notes": args.notes, "reviewed_at": now()}
        phase["status"] = "completed" if verdict == "PASS" else "failed"
        write_json_atomic(state_path(state["experiment_id"]), state)
        append_event(experiment_dir(state["experiment_id"]), {"event": "review_" + verdict.lower(),
                                                               "phase_id": phase["id"], "reviewer": args.reviewer})
        return {"ok": verdict == "PASS", "experiment_id": state["experiment_id"],
                "phase_id": phase["id"], "status": phase["status"]}


def status(args: argparse.Namespace) -> dict:
    return {"ok": True, "state": load_state(args.experiment_id)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--experiment-id")
    p.add_argument("--plan-id", required=True)
    p.add_argument("--model-set", required=True)
    p.add_argument("--scenario-set", required=True)
    p.add_argument("--user", default="user")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=init)

    p = sub.add_parser("launch-phase")
    p.add_argument("--experiment-id")
    p.add_argument("--plan-id", required=True)
    p.add_argument("--phase-id", required=True)
    p.add_argument("--model-set", required=True)
    p.add_argument("--scenario-set", required=True)
    p.add_argument("--user", default="user")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=launch_phase)

    p = sub.add_parser("gate")
    p.add_argument("--experiment-id", required=True)
    p.add_argument("--phase-id", required=True)
    p.add_argument("--skip-audit", action="store_true")
    p.set_defaults(fn=gate_phase)

    p = sub.add_parser("review")
    p.add_argument("--experiment-id", required=True)
    p.add_argument("--phase-id", required=True)
    p.add_argument("--verdict", required=True)
    p.add_argument("--reviewer", default="operator")
    p.add_argument("--notes", default="")
    p.set_defaults(fn=review_phase)

    p = sub.add_parser("status")
    p.add_argument("--experiment-id", required=True)
    p.set_defaults(fn=status)

    args = parser.parse_args()
    print(json.dumps(args.fn(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()