#!/usr/bin/env python3
"""Operator controls for CEOps runs/batches.

Runs on the home controller. It keeps pause/cancel semantics in one place:
- cancel is terminal;
- pause kills active work, trims the current incomplete model, and marks state paused;
- resume relaunches a paused memory batch against the existing batch-state file.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS = REPO / "data" / "runs"
RUN_BATCHES = REPO / "data" / "run-batches"
AI = os.environ.get("AI", "dragos@home-ai.home.domain")
AI_REPO = os.environ.get("AI_REPO", "/home/dragos/apprenticeops")
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


def fail(message: str, code: int = 2) -> None:
    print(json.dumps({"ok": False, "error": message}))
    raise SystemExit(code)


def sh(command: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(command, shell=True, cwd=REPO, capture_output=True, text=True, timeout=timeout, check=False)


def ai(command: str, timeout: int = 30) -> subprocess.CompletedProcess:
    quoted = subprocess.list2cmdline([command])
    return sh(f"ssh -o BatchMode=yes -o ConnectTimeout=8 {AI} {quoted}", timeout=timeout)


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    try:
        with path.open(errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    with tmp.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    with tmp.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def kill_processes(include_batch: bool) -> None:
    patterns = ["[r]un-from-homelab", "[j]udge-scheduler", "[j]udge.py"]
    if include_batch:
        patterns.append("[r]un-memory-batch.py")
    for sig in ("TERM", "KILL"):
        for pattern in patterns:
            sh(f"pkill -{sig} -f '{pattern}' 2>/dev/null || true", timeout=10)
        ai(f"pkill -{sig} -f '[r]un-roster' 2>/dev/null || true; pkill -{sig} -f '[r]un.py --models' 2>/dev/null || true", timeout=15)


def sync_ai_results(run_id: str) -> None:
    mirror = RUNS / run_id / "_mirror"
    mirror.mkdir(parents=True, exist_ok=True)
    for suffix in ("jsonl", "jsonl.done"):
        sh(f"rsync -az {AI}:{AI_REPO}/results.{run_id}.{suffix} {mirror}/ 2>/dev/null || true", timeout=30)


def safe_model_prefix(model: str) -> str:
    return model.replace("/", "_").replace(":", "_")


def trim_current_model(run_id: str) -> str | None:
    sync_ai_results(run_id)
    run_dir = RUNS / run_id
    mirror = run_dir / "_mirror"
    result_path = mirror / f"results.{run_id}.jsonl"
    rows = read_jsonl(result_path)
    if not rows:
        return None
    last_model = next((row.get("model") for row in reversed(rows) if row.get("model")), None)
    if not last_model:
        return None
    committed = {line.strip() for line in (run_dir / ".committed").read_text().splitlines()} if (run_dir / ".committed").exists() else set()
    done_rows = read_jsonl(mirror / f"results.{run_id}.jsonl.done")
    done = {row.get("model") for row in done_rows if row.get("model")}
    if last_model in committed or last_model in done:
        return None
    kept = [row for row in rows if row.get("model") != last_model]
    write_jsonl(result_path, kept)
    judged_path = run_dir / f"judged.{run_id}.jsonl"
    if judged_path.exists():
        judged = [row for row in read_jsonl(judged_path) if row.get("model") != last_model]
        write_jsonl(judged_path, judged)
    prefix = safe_model_prefix(last_model)
    for path in glob.glob(str(mirror / "outputs" / f"{prefix}__*")):
        try:
            os.remove(path)
        except OSError:
            pass
    sh(f"rsync -az {result_path} {AI}:{AI_REPO}/results.{run_id}.jsonl 2>/dev/null || true", timeout=30)
    ai(f"find {AI_REPO}/outputs -maxdepth 1 -type f -name '{prefix}__*' -delete 2>/dev/null || true", timeout=15)
    return last_model


def batch_for_run(run_id: str) -> tuple[Path | None, dict | None, int | None]:
    for path in RUN_BATCHES.glob("*/batch-state.json"):
        try:
            state = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            continue
        for index, run in enumerate(state.get("runs") or []):
            if run.get("run_id") == run_id:
                return path, state, index
    return None, None, None


def mark_pause(run_id: str, trimmed_model: str | None) -> dict:
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / ".paused").write_text(str(int(time.time())) + "\n")
    batch_path, state, index = batch_for_run(run_id)
    if state is not None and index is not None and batch_path is not None:
        state["status"] = "paused"
        state["updated_at"] = int(time.time())
        state["current_index"] = index
        state["runs"][index]["status"] = "paused"
        state["runs"][index]["updated_at"] = int(time.time())
        state["runs"][index]["paused_at"] = int(time.time())
        state["runs"][index]["discarded_model"] = trimmed_model
        write_json_atomic(batch_path, state)
        return {"batch_id": state.get("batch_id"), "batch_status": "paused"}
    return {}


def mark_cancel(run_id: str) -> dict:
    now = int(time.time())
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / ".canceled").write_text(str(now) + "\n")
    try:
        (run_dir / ".paused").unlink()
    except OSError:
        pass
    batch_path, state, index = batch_for_run(run_id)
    if state is not None and batch_path is not None:
        state["status"] = "canceled"
        state["updated_at"] = now
        for run in state.get("runs") or []:
            if run.get("status") != "done":
                run["status"] = "canceled"
                run["ended_at"] = now
                run["updated_at"] = now
        write_json_atomic(batch_path, state)
        return {"batch_id": state.get("batch_id"), "batch_status": "canceled"}
    return {}


def resume_batch(run_id: str) -> dict | None:
    batch_path, state, index = batch_for_run(run_id)
    if state is None or batch_path is None:
        return None
    if state.get("status") != "paused":
        fail(f"batch is not paused: status={state.get('status')!r}", code=3)
    now = int(time.time())
    state["status"] = "running"
    state["updated_at"] = now
    if index is not None:
        state["current_index"] = index
        if state["runs"][index].get("status") == "paused":
            state["runs"][index]["status"] = "pending"
            state["runs"][index]["ended_at"] = None
            state["runs"][index]["updated_at"] = now
    write_json_atomic(batch_path, state)
    run_dir = RUNS / run_id
    try:
        (run_dir / ".paused").unlink()
    except OSError:
        pass
    batch_id = state["batch_id"]
    boot = f"/tmp/ao-batch.{batch_id}.resume"
    sh(f"setsid nohup python3 scripts/run-memory-batch.py resume --batch-id {batch_id} >{boot} 2>&1 </dev/null &", timeout=10)
    return {"batch_id": batch_id, "action": "batch-resume"}


def pause(args: argparse.Namespace) -> None:
    kill_processes(include_batch=True)
    trimmed = trim_current_model(args.run_id)
    payload = {"ok": True, "action": "pause", "run_id": args.run_id, "discarded_model": trimmed}
    payload.update(mark_pause(args.run_id, trimmed))
    print(json.dumps(payload))


def cancel(args: argparse.Namespace) -> None:
    kill_processes(include_batch=True)
    payload = {"ok": True, "action": "cancel", "run_id": args.run_id}
    payload.update(mark_cancel(args.run_id))
    print(json.dumps(payload))


def resume(args: argparse.Namespace) -> None:
    batch_payload = resume_batch(args.run_id)
    if batch_payload:
        print(json.dumps({"ok": True, "run_id": args.run_id, **batch_payload}))
        return
    fail("standalone resume is handled by the dashboard backend", code=4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, func in (("pause", pause), ("cancel", cancel), ("resume", resume)):
        child = sub.add_parser(name)
        child.add_argument("--run-id", required=True)
        child.set_defaults(func=func)
    args = parser.parse_args()
    if not RUN_ID_RE.match(args.run_id):
        fail("invalid run_id")
    return args


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()