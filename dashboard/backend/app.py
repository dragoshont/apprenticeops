#!/usr/bin/env python3
"""ApprenticeOps mission-control — dashboard backend.

A thin FastAPI shim over the experiment's two-node pipeline. It does NOT compute
state itself: it runs ``scripts/pipeline-status.py`` ON the ``home`` node over SSH
(home already mirrors the producer's results from ``ai``) and serves that JSON to
the browser, plus a small set of control verbs (start / stop / pause / resume).

Trust model — v0.1
-------------------
This is a single-operator, local tool. It binds to 127.0.0.1 by default and has
**no auth**. Every privileged action shells into ``home`` over SSH, so the host
running this backend must already hold the SSH key for ``home`` (the ``homelab``
alias on the Mac, or a mounted key + ssh-config in the container). Do not expose
it to an untrusted network.

Injection safety: the browser can only pick a *model_set* id, a *scenario_set* id,
and a *memory_context* id from the server-side allowlist loaded from
``data/run-matrix.json``. RUN_IDs for new runs are generated server-side. Shell
environment values are server-resolved and quoted before being sent to ``home``.

Env:
  HOME_SSH    SSH destination for the home node     (default: "homelab")
  AI_SSH      how home reaches the ai node           (default: "home-ai.hont.ro")
  REPO_DIR    repo path on home                      (default: "~/apprenticeops")
  POLL_S      websocket push cadence, seconds        (default: 5)
  HOST/PORT   bind                                   (default: 127.0.0.1:8770)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shlex
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HOME_SSH = os.environ.get("HOME_SSH", "homelab")
AI_SSH = os.environ.get("AI_SSH", "home-ai.hont.ro")
REPO_DIR = os.environ.get("REPO_DIR", "~/apprenticeops")
POLL_S = float(os.environ.get("POLL_S", "5"))

# Auth toggle. When AUTH_ENABLED is true the app trusts an Authentik forward-auth
# proxy in front of it: that proxy authenticates the user and injects a username
# header (AUTH_HEADER). Requests without it are rejected. When false, no auth.
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
AUTH_HEADER = os.environ.get("AUTH_HEADER", "X-authentik-username")

# Serve the built Vite app if present (frontend/dist); in dev, Vite serves the UI
# itself and proxies /api + /ws here, so this mount is a no-op.
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "dist"

_RUNID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")

app = FastAPI(title="ApprenticeOps mission-control", version="0.1.0")


@app.middleware("http")
async def _auth_gate(request: Request, call_next):
    """When auth is enabled, every request must carry the Authentik-injected user
    header (set by the forward-auth proxy). /healthz is always open for probes."""
    if AUTH_ENABLED and request.url.path != "/healthz":
        if not request.headers.get(AUTH_HEADER):
            return JSONResponse({"detail": "authentication required"}, status_code=401)
    return await call_next(request)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/config")
def api_config(request: Request):
    return {"auth_enabled": AUTH_ENABLED,
            "user": request.headers.get(AUTH_HEADER) if AUTH_ENABLED else None}


# ----------------------------------------------------------------------------- ssh
def _ssh(remote: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a shell command on the home node. ``remote`` is a fixed template with
    only server-validated values interpolated — never raw client input."""
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", HOME_SSH, remote],
        capture_output=True, text=True, timeout=timeout, check=False,
    )


def _home_cmd(inner: str) -> str:
    return f"cd {REPO_DIR} && {inner}"


# Refresh the experiment scripts from origin/main before a (re)launch so the run
# always uses current code (e.g. run-e2e.sh that writes run.meta), without
# touching the current branch or the untracked run data. Best-effort.
_SYNC = ("git fetch -q origin 2>/dev/null; "
         "git checkout -q origin/main -- scripts data/run-matrix.json data/run-manifest.json "
         "data/scenarios.json data/scenario_sets data/memory 2>/dev/null; ")


def _q(value: object) -> str:
    return shlex.quote(str(value))


def _env_assign(values: dict[str, object]) -> str:
    return " ".join(f"{key}={_q(value)}" for key, value in values.items())


def _marker(run_id: str, name: str, create: bool) -> None:
    """Create or remove a run marker file (.canceled/.paused) on home."""
    if not _RUNID_RE.match(run_id) or name not in (".canceled", ".paused"):
        return
    path = f"data/runs/{run_id}/{name}"
    inner = f"touch {path}" if create else f"rm -f {path}"
    _ssh(_home_cmd(inner), timeout=15)


# --------------------------------------------------------------------------- status
_cache: dict = {"ts": 0.0, "run_id": None, "data": None}
_status_cache: dict[str | None, tuple[float, dict]] = {}
_prewarm_tasks: set[str] = set()
_prewarm_pool = ThreadPoolExecutor(max_workers=2)
_status_lock = threading.Lock()
_status_generation = 0


def _status_ttl(data: dict) -> float:
    state = data.get("state")
    if state in ("done", "canceled", "stopped", "idle"):
        return 120.0
    if state == "paused":
        return 15.0
    return 3.0


def _gather(run_id: str | None) -> dict:
    """Invoke pipeline-status.py on home and return its parsed JSON."""
    arg = run_id if run_id and _RUNID_RE.match(run_id) else ""
    cp = _ssh(_home_cmd(f"python3 scripts/pipeline-status.py {arg}".rstrip()), timeout=40)
    if cp.returncode != 0:
        return {"state": "error", "error": (cp.stderr or cp.stdout or "ssh failed").strip()[:800],
                "run_id": run_id, "ts": time.time()}
    try:
        return json.loads(cp.stdout)
    except json.JSONDecodeError:
        return {"state": "error", "error": "status was not JSON: " + cp.stdout.strip()[:600],
                "run_id": run_id, "ts": time.time()}


def _invalidate_status(*run_ids: str | None) -> None:
    global _status_generation
    with _status_lock:
        _status_generation += 1
        if not run_ids:
            _status_cache.clear()
        else:
            for run_id in run_ids:
                _status_cache.pop(run_id, None)
        _cache["ts"] = 0.0


def status(run_id: str | None, max_age: float = 3.0, force: bool = False) -> dict:
    now = time.time()
    if not force:
        with _status_lock:
            cached = _status_cache.get(run_id)
        if cached:
            ts, data = cached
            ttl = max_age if max_age > 0 else 0
            ttl = max(ttl, _status_ttl(data)) if max_age > 0 else 0
            if now - ts < ttl:
                return data
    with _status_lock:
        generation = _status_generation
    data = _gather(run_id)
    with _status_lock:
        if generation == _status_generation:
            _status_cache[run_id] = (time.time(), data)
    _cache.update(ts=now, run_id=run_id, data=data)
    return data


def _prewarm_recent_runs(data: dict) -> None:
    for session in (data.get("sessions") or [])[:8]:
        run_id = session.get("run_id")
        with _status_lock:
            if not run_id or not _RUNID_RE.match(run_id) or run_id in _prewarm_tasks:
                continue
            cached = _status_cache.get(run_id)
            if cached and time.time() - cached[0] < _status_ttl(cached[1]):
                continue
            _prewarm_tasks.add(run_id)
            generation = _status_generation

        def _worker(rid: str = run_id, gen: int = generation) -> None:
            try:
                data = _gather(rid)
                with _status_lock:
                    if gen == _status_generation:
                        _status_cache[rid] = (time.time(), data)
            finally:
                with _status_lock:
                    _prewarm_tasks.discard(rid)

        _prewarm_pool.submit(_worker)


_MATRIX_SCRIPT = r'''
import hashlib, json, re, sys
from collections import Counter
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
PATH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,160}$")
root = Path.cwd().resolve()

def fail(message):
    print(json.dumps({"error": message}))
    sys.exit(1)

def safe_path(raw, suffix):
    if not isinstance(raw, str) or not PATH_RE.match(raw) or raw.startswith("/") or ".." in Path(raw).parts:
        fail(f"unsafe path: {raw!r}")
    if not raw.endswith(suffix):
        fail(f"path {raw!r} must end with {suffix}")
    full = (root / raw).resolve()
    if root not in (full, *full.parents):
        fail(f"path escapes repo: {raw!r}")
    if not full.exists():
        fail(f"missing path: {raw}")
    return full

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def model_count(path):
    return sum(1 for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#"))

def load_scenarios(path):
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        fail(f"scenario file {path} is not valid JSON: {exc}")
    items = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(items, list):
        fail(f"scenario file {path} must contain a scenarios list")
    seen = set()
    for item in items:
        sid = item.get("id") if isinstance(item, dict) else None
        if not sid or sid in seen:
            fail(f"scenario file {path} has missing/duplicate scenario id {sid!r}")
        seen.add(sid)
    return items

matrix_path = safe_path("data/run-matrix.json", ".json")
try:
    matrix = json.loads(matrix_path.read_text())
except Exception as exc:
    fail(f"run matrix is not valid JSON: {exc}")

def resolve_model_set(raw):
    mid = raw.get("id") if isinstance(raw, dict) else None
    if not ID_RE.match(str(mid or "")):
        fail(f"invalid model_set id: {mid!r}")
    path = safe_path(raw.get("path"), ".txt")
    return {**raw, "model_count": model_count(path), "sha256": sha(path)}

def resolve_scenario_set(raw):
    sid = raw.get("id") if isinstance(raw, dict) else None
    if not ID_RE.match(str(sid or "")):
        fail(f"invalid scenario_set id: {sid!r}")
    path = safe_path(raw.get("path"), ".json")
    scenarios = load_scenarios(path)
    return {
        **raw,
        "scenario_count": len(scenarios),
        "class_counts": dict(Counter(s.get("class") or "unknown" for s in scenarios)),
        "difficulty_counts": dict(Counter(s.get("difficulty") or "unknown" for s in scenarios)),
        "grounding_counts": dict(Counter(s.get("grounding") or "unknown" for s in scenarios)),
        "scenario_ids": [s["id"] for s in scenarios],
        "sha256": sha(path),
    }

def resolve_memory_context(raw):
    mid = raw.get("id") if isinstance(raw, dict) else None
    if not ID_RE.match(str(mid or "")):
        fail(f"invalid memory_context id: {mid!r}")
    item = dict(raw)
    path_raw = item.get("path")
    if path_raw:
        path = safe_path(path_raw, ".md")
        item["byte_count"] = path.stat().st_size
        item["sha256"] = sha(path)
    else:
        item["path"] = None
        item["byte_count"] = 0
        item["sha256"] = None
    return item

model_sets = [resolve_model_set(item) for item in matrix.get("model_sets", [])]
scenario_sets = [resolve_scenario_set(item) for item in matrix.get("scenario_sets", [])]
memory_contexts = [resolve_memory_context(item) for item in matrix.get("memory_contexts", [])]
if len({m["id"] for m in model_sets}) != len(model_sets):
    fail("duplicate model_set id")
if len({s["id"] for s in scenario_sets}) != len(scenario_sets):
    fail("duplicate scenario_set id")
if len({m["id"] for m in memory_contexts}) != len(memory_contexts):
    fail("duplicate memory_context id")

scenario_rows = {}
for scenario_set in scenario_sets:
    for scenario in load_scenarios(safe_path(scenario_set["path"], ".json")):
        row = scenario_rows.setdefault(scenario["id"], {
            "id": scenario["id"],
            "class": scenario.get("class"),
            "difficulty": scenario.get("difficulty"),
            "grounding": scenario.get("grounding"),
            "brief": (scenario.get("question") or scenario.get("gold_answer") or "").split("\n", 1)[0][:180],
            "sets": [],
        })
        if scenario_set["id"] not in row["sets"]:
            row["sets"].append(scenario_set["id"])

print(json.dumps({
    "schema_version": matrix.get("schema_version", 1),
    "defaults": matrix.get("defaults", {}),
    "model_sets": model_sets,
    "scenario_sets": scenario_sets,
    "memory_contexts": memory_contexts,
    "experiment_plans": matrix.get("experiment_plans", []),
    "scenarios": sorted(scenario_rows.values(), key=lambda row: row["id"]),
}))
'''


def _run_matrix() -> dict:
    cp = _ssh(_home_cmd("python3 - <<'PY'\n" + _MATRIX_SCRIPT + "\nPY"), timeout=25)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout or "run matrix failed").strip()[:800]
        raise HTTPException(500, detail)
    try:
        data = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, f"run matrix was not JSON: {exc}") from exc
    if data.get("error"):
        raise HTTPException(500, data["error"])
    return data


_INPUTS_SCRIPT = r'''
import json, re, sys
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
PATH_RE = re.compile(r"^[A-Za-z0-9._/-]{1,160}$")
root = Path.cwd().resolve()

model_set_id = sys.argv[1]
scenario_set_id = sys.argv[2]
memory_context_id = sys.argv[3]

def fail(message):
    print(json.dumps({"error": message}))
    sys.exit(1)

def safe_path(raw, suffix):
    if not isinstance(raw, str) or not PATH_RE.match(raw) or raw.startswith("/") or ".." in Path(raw).parts:
        fail(f"unsafe path: {raw!r}")
    if not raw.endswith(suffix):
        fail(f"path {raw!r} must end with {suffix}")
    full = (root / raw).resolve()
    if root not in (full, *full.parents):
        fail(f"path escapes repo: {raw!r}")
    if not full.exists():
        fail(f"missing path: {raw}")
    return full

def by_id(items, wanted, kind):
    if not ID_RE.match(wanted or ""):
        fail(f"invalid {kind} id: {wanted!r}")
    for item in items:
        if item.get("id") == wanted:
            return item
    fail(f"unknown {kind}: {wanted}")

def load_scenarios(path):
    data = json.loads(path.read_text())
    items = data.get("scenarios") if isinstance(data, dict) else None
    if not isinstance(items, list):
        fail(f"scenario file {path} must contain scenarios list")
    return items

def read_models(path):
    out = []
    bracket = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            text = line.lstrip("#").strip()
            if text.lower().startswith("bracket:"):
                bracket = text.split(":", 1)[1].strip()
            continue
        out.append({"id": line, "bracket": bracket})
    return out

def build_prompt(s, memory_text=""):
    memory = ""
    if memory_text:
        memory = ("--- HOMELAB MEMORY ---\n"
                  "The following is stable, curated background about the homelab. "
                  "Use it only when it is relevant to the scenario; the scenario "
                  "context remains authoritative for incident-specific facts.\n"
                  f"{memory_text}\n\n")
    return ("You are a homelab operations assistant. Use ONLY the information "
            "given. Be concise and specific.\n\n"
            f"{memory}--- CONTEXT ---\n{s['context']}\n\n--- TASK ---\n{s['question']}")

matrix = json.loads(safe_path("data/run-matrix.json", ".json").read_text())
model_set = by_id(matrix.get("model_sets", []), model_set_id, "model_set")
scenario_set = by_id(matrix.get("scenario_sets", []), scenario_set_id, "scenario_set")
memory_context = by_id(matrix.get("memory_contexts", []), memory_context_id, "memory_context")

model_path = safe_path(model_set["path"], ".txt")
scenario_path = safe_path(scenario_set["path"], ".json")
memory_text = ""
if memory_context.get("path"):
    memory_text = safe_path(memory_context["path"], ".md").read_text(encoding="utf-8").strip()

scenarios = []
for item in load_scenarios(scenario_path):
    prompt = build_prompt(item, memory_text)
    scenarios.append({
        "id": item.get("id"),
        "class": item.get("class"),
        "difficulty": item.get("difficulty"),
        "grounding": item.get("grounding"),
        "context": item.get("context", ""),
        "question": item.get("question", ""),
        "gold_answer": item.get("gold_answer", ""),
        "judge_rubric": item.get("judge_rubric", ""),
        "deterministic_checks": item.get("deterministic_checks", []),
        "max_tokens": item.get("max_tokens"),
        "timeout_s": item.get("timeout_s"),
        "prompt": prompt,
        "prompt_chars": len(prompt),
    })

print(json.dumps({
    "model_set": {**model_set, "models": read_models(model_path)},
    "scenario_set": scenario_set,
    "memory_context": {**memory_context, "markdown": memory_text, "chars": len(memory_text)},
    "scenarios": scenarios,
}))
'''


def _input_details(model_set: str, scenario_set: str, memory_context: str) -> dict:
    _resolve_run_selection(model_set, scenario_set, memory_context)
    cp = _ssh(_home_cmd("python3 - " + " ".join(_q(arg) for arg in (model_set, scenario_set, memory_context)) + " <<'PY'\n" + _INPUTS_SCRIPT + "\nPY"), timeout=30)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout or "input details failed").strip()[:800]
        raise HTTPException(500, detail)
    try:
        data = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, f"input details were not JSON: {exc}") from exc
    if data.get("error"):
        raise HTTPException(500, data["error"])
    return data


def _resolve_run_selection(model_set: str, scenario_set: str, memory_context: str) -> tuple[dict, dict, dict, dict]:
    if not _ID_RE.match(model_set or ""):
        raise HTTPException(400, "invalid model_set id")
    if not _ID_RE.match(scenario_set or ""):
        raise HTTPException(400, "invalid scenario_set id")
    if not _ID_RE.match(memory_context or ""):
        raise HTTPException(400, "invalid memory_context id")
    matrix = _run_matrix()
    model = next((item for item in matrix.get("model_sets", []) if item.get("id") == model_set), None)
    scenarios = next((item for item in matrix.get("scenario_sets", []) if item.get("id") == scenario_set), None)
    memory = next((item for item in matrix.get("memory_contexts", []) if item.get("id") == memory_context), None)
    if not model:
        raise HTTPException(404, f"unknown model_set '{model_set}'")
    if not scenarios:
        raise HTTPException(404, f"unknown scenario_set '{scenario_set}'")
    if not memory:
        raise HTTPException(404, f"unknown memory_context '{memory_context}'")
    if not model.get("model_count"):
        raise HTTPException(400, f"model_set '{model_set}' contains no models")
    if not scenarios.get("scenario_count"):
        raise HTTPException(400, f"scenario_set '{scenario_set}' contains no scenarios")
    return matrix, model, scenarios, memory


def _read_run_meta(run_id: str) -> dict:
    if not _RUNID_RE.match(run_id or ""):
        raise HTTPException(400, "invalid run_id")
    cp = _ssh(_home_cmd(f"cat {_q(f'data/runs/{run_id}/run.meta')}"), timeout=15)
    if cp.returncode != 0:
        raise HTTPException(409, "run has no run.meta; start a new run")
    try:
        meta = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(409, "run.meta is not valid JSON; start a new run") from exc
    if int(meta.get("schema_version") or 0) < 2:
        raise HTTPException(409, "run predates run-matrix metadata; start a new run")
    return meta


def _validate_run_meta_for_resume(meta: dict) -> None:
    scenarios = meta.get("scenarios")
    expected_sha = meta.get("scenarios_sha256")
    if not scenarios or not expected_sha:
        raise HTTPException(409, "run.meta missing scenario hash; start a new run")
    cp = _ssh(_home_cmd(f"python3 - <<'PY'\nimport hashlib, pathlib\np=pathlib.Path({_q(scenarios)!r})\nprint(hashlib.sha256(p.read_bytes()).hexdigest())\nPY"), timeout=15)
    got = (cp.stdout or "").strip()
    if cp.returncode != 0 or got != expected_sha:
        raise HTTPException(409, "run.meta scenario hash mismatch; start a new run")
    memory_file = meta.get("memory_context_file")
    memory_sha = meta.get("memory_context_sha256")
    if memory_file and memory_sha:
        cp = _ssh(_home_cmd(f"python3 - <<'PY'\nimport hashlib, pathlib\np=pathlib.Path({_q(memory_file)!r})\nprint(hashlib.sha256(p.read_bytes()).hexdigest())\nPY"), timeout=15)
        got = (cp.stdout or "").strip()
        if cp.returncode != 0 or got != memory_sha:
            raise HTTPException(409, "run.meta memory context hash mismatch; start a new run")


# ----------------------------------------------------------------------------- api
class StartReq(BaseModel):
    model_set: str
    scenario_set: str
    memory_context: str = "none"


class BatchStartReq(BaseModel):
    model_set: str
    scenario_set: str
    memory_contexts: list[str]


class RunReq(BaseModel):
    run_id: str | None = None


class PlanPhaseReq(BaseModel):
    plan_id: str
    phase_id: str
    model_set: str
    scenario_set: str
    experiment_id: str | None = None


@app.get("/api/status")
def api_status(run_id: str | None = None):
    data = status(run_id)
    if run_id is None:
        _prewarm_recent_runs(data)
    return JSONResponse(data)


@app.get("/api/run-matrix")
def api_run_matrix():
    return JSONResponse(_run_matrix())


@app.get("/api/inputs")
def api_inputs(model_set: str, scenario_set: str, memory_context: str = "none"):
    return JSONResponse(_input_details(model_set, scenario_set, memory_context))


@app.post("/api/control/start")
def api_start(req: StartReq, request: Request):
    _, model_set, scenario_set, memory_context = _resolve_run_selection(
        req.model_set, req.scenario_set, req.memory_context
    )
    models = model_set["path"]
    scenarios = scenario_set["path"]
    memory_path = memory_context.get("path") or ""
    # one run at a time: refuse if a run is currently active (running or paused).
    cur = status(None, max_age=0.0, force=True)
    active = (cur.get("state") in ("running", "paused")
              or (cur.get("producer") or {}).get("run_py_alive")
              or (cur.get("consumer") or {}).get("alive"))
    if active:
        raise HTTPException(409, f"a run is already active ({cur.get('run_id')}) — stop it first")
    # who started it: the Authentik user when gated, else a generic "user".
    user = (request.headers.get(AUTH_HEADER) if AUTH_ENABLED else None) or "user"
    user = re.sub(r"[^A-Za-z0-9._@-]", "", user)[:40] or "user"
    run_id = f"{req.model_set}-{req.scenario_set}-{req.memory_context}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    env = _env_assign({
        "RUN_ID": run_id,
        "MODELS": models,
        "MODEL_SET": req.model_set,
        "SCENARIOS": scenarios,
        "SCENARIO_SET": req.scenario_set,
        "MEMORY_CONTEXT": req.memory_context,
        "MEMORY_CONTEXT_FILE": memory_path,
        "RUN_USER": user,
    })
    inner = (_SYNC + env + " "
             f"setsid nohup ./scripts/run-e2e.sh >{_q(f'/tmp/e2e.{run_id}.boot')} 2>&1 </dev/null & "
             f"echo launched {_q(run_id)}")
    cp = _ssh(_home_cmd(inner), timeout=40)
    ok = cp.returncode == 0 and "launched" in cp.stdout
    _invalidate_status(None, run_id)
    return {"ok": ok, "run_id": run_id,
            "model_set": req.model_set, "scenario_set": req.scenario_set,
            "memory_context": req.memory_context,
            "models": models, "scenarios": scenarios, "memory_context_file": memory_path, "user": user,
            "detail": (cp.stdout or cp.stderr).strip()[:400]}


@app.post("/api/control/start-batch")
def api_start_batch(req: BatchStartReq, request: Request):
    if len(req.memory_contexts) < 2:
        raise HTTPException(400, "select at least two memory contexts for a batch")
    seen: list[str] = []
    for memory_context in req.memory_contexts:
        if memory_context not in seen:
            seen.append(memory_context)
    if len(seen) != len(req.memory_contexts):
        raise HTTPException(400, "memory contexts must be unique")
    resolved = [_resolve_run_selection(req.model_set, req.scenario_set, memory_context) for memory_context in seen]
    models = resolved[0][1]["path"]
    scenarios = resolved[0][2]["path"]
    cur = status(None, max_age=0.0, force=True)
    active = (cur.get("state") in ("running", "paused")
              or (cur.get("producer") or {}).get("run_py_alive")
              or (cur.get("consumer") or {}).get("alive"))
    if active:
        raise HTTPException(409, f"a run is already active ({cur.get('run_id')}) — stop it first")
    active_batch = _ssh(_home_cmd(_SYNC + " python3 scripts/run-memory-batch.py active"), timeout=20)
    if active_batch.returncode == 0:
        try:
            payload = json.loads(active_batch.stdout)
            if payload.get("active"):
                raise HTTPException(409, "a memory batch is already active")
        except json.JSONDecodeError:
            pass
    user = (request.headers.get(AUTH_HEADER) if AUTH_ENABLED else None) or "user"
    user = re.sub(r"[^A-Za-z0-9._@-]", "", user)[:40] or "user"
    batch_id = f"batch-{req.model_set}-{req.scenario_set}-memory-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    args = [
        "python3", "scripts/run-memory-batch.py", "launch",
        "--batch-id", batch_id,
        "--model-set", req.model_set,
        "--scenario-set", req.scenario_set,
        "--user", user,
    ]
    for memory_context in seen:
        args.extend(["--memory-context", memory_context])
    boot = f"/tmp/ao-batch.{batch_id}.boot"
    inner = (_SYNC + " "
             f"setsid nohup {' '.join(_q(arg) for arg in args)} >{_q(boot)} 2>&1 </dev/null & "
             f"echo launched {_q(batch_id)}")
    cp = _ssh(_home_cmd(inner), timeout=40)
    ok = cp.returncode == 0 and "launched" in cp.stdout
    if not ok:
        detail = (cp.stderr or cp.stdout or "batch launch failed").strip()[:800]
        raise HTTPException(500, detail)
    _invalidate_status(None)
    return {"ok": True, "batch_id": batch_id, "model_set": req.model_set, "scenario_set": req.scenario_set,
            "memory_contexts": seen, "models": models, "scenarios": scenarios, "user": user,
            "detail": (cp.stdout or cp.stderr).strip()[:400]}


@app.post("/api/control/start-phase")
def api_start_phase(req: PlanPhaseReq, request: Request):
    matrix = _run_matrix()
    plan = next((item for item in matrix.get("experiment_plans", []) if item.get("id") == req.plan_id), None)
    phase = next((item for item in (plan or {}).get("phases", []) if item.get("id") == req.phase_id), None)
    if not plan:
        raise HTTPException(404, f"unknown experiment_plan '{req.plan_id}'")
    if not phase:
        raise HTTPException(404, f"unknown phase '{req.phase_id}'")
    # Reuse the same allowlist resolver as manual starts. The controller will use
    # the same ids, but this keeps client input fail-closed before shelling out.
    _resolve_run_selection(req.model_set, req.scenario_set, phase["memory_context"])
    cur = status(None, max_age=0.0, force=True)
    active = (cur.get("state") in ("running", "paused")
              or (cur.get("producer") or {}).get("run_py_alive")
              or (cur.get("consumer") or {}).get("alive"))
    if active:
        raise HTTPException(409, f"a run is already active ({cur.get('run_id')}) — stop it first")
    user = (request.headers.get(AUTH_HEADER) if AUTH_ENABLED else None) or "user"
    user = re.sub(r"[^A-Za-z0-9._@-]", "", user)[:40] or "user"
    args = [
        "python3", "scripts/experiment-plan.py", "launch-phase",
        "--plan-id", req.plan_id,
        "--phase-id", req.phase_id,
        "--model-set", req.model_set,
        "--scenario-set", req.scenario_set,
        "--user", user,
    ]
    if req.experiment_id:
        if not _RUNID_RE.match(req.experiment_id):
            raise HTTPException(400, "invalid experiment_id")
        args.extend(["--experiment-id", req.experiment_id])
    cp = _ssh(_home_cmd(_SYNC + " " + " ".join(_q(arg) for arg in args)), timeout=40)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout or "phase launch failed").strip()[:800]
        raise HTTPException(409, detail)
    try:
        payload = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, f"phase launch was not JSON: {exc}") from exc
    _invalidate_status(None, payload.get("run_id"))
    return payload


def _signal_all(sig: str) -> dict:
    """Send ``sig`` to the producer (ai) and consumer (home) process trees.
    Uses the bracket trick so the SSH command does not match itself."""
    inner = (
        f"pkill -{sig} -f '[j]udge-scheduler'; pkill -{sig} -f '[j]udge.py'; "
        f"ssh -o BatchMode=yes -o ConnectTimeout=8 {AI_SSH} "
        f"\"pkill -{sig} -f '[r]un-roster'; pkill -{sig} -f '[r]un.py'\" 2>/dev/null; "
        f"echo signalled {sig}"
    )
    cp = _ssh(_home_cmd(inner), timeout=30)
    _cache["ts"] = 0.0
    return {"ok": cp.returncode == 0, "signal": sig,
            "detail": (cp.stdout or cp.stderr).strip()[:400]}


@app.post("/api/control/stop")
def api_stop(req: RunReq):
    """Stop = cancel. Kill both process trees and write a .canceled marker so the
    run is terminal: it shows as 'canceled' in the table and cannot be resumed."""
    if req.run_id:
        _marker(req.run_id, ".canceled", create=True)
        _marker(req.run_id, ".paused", create=False)
        _invalidate_status(None, req.run_id)
    return {**_signal_all("KILL"), "action": "cancel", "run_id": req.run_id}


@app.post("/api/control/pause")
def api_pause(req: RunReq):
    """Pause = soft hold. SIGSTOP the schedulers + run.py (the process freezes with
    all state intact) and write a .paused marker. Continue resumes it exactly. The
    ollama server is separate, so an in-flight token stream stalls rather than
    checkpointing — but no rows are lost."""
    if req.run_id:
        _marker(req.run_id, ".paused", create=True)
        _invalidate_status(None, req.run_id)
    return {**_signal_all("STOP"), "action": "pause", "run_id": req.run_id}


@app.post("/api/control/resume")
def api_resume(req: RunReq):
    """Continue a run. If it was paused, SIGCONT the frozen processes (exact resume)
    and clear the marker. If the processes are gone (e.g. a reboot), re-launch the
    same RUN_ID — the pipeline resumes at scenario granularity. A canceled run is
    terminal and refuses to resume."""
    if not req.run_id:
        raise HTTPException(400, "run_id required")
    if not _RUNID_RE.match(req.run_id):
        raise HTTPException(400, "invalid run_id")
    st = status(req.run_id, max_age=0.0, force=True)
    if st.get("markers", {}).get("canceled"):
        raise HTTPException(409, "run was canceled — start a new run instead")
    prod_alive = st.get("producer", {}).get("run_py_alive")
    cons_alive = st.get("consumer", {}).get("alive")
    if prod_alive or cons_alive:
        _marker(req.run_id, ".paused", create=False)
        _invalidate_status(None, req.run_id)
        return {**_signal_all("CONT"), "action": "continue", "run_id": req.run_id}
    meta = _read_run_meta(req.run_id)
    for key in ("models", "model_set", "scenarios", "scenario_set"):
        if not meta.get(key):
            raise HTTPException(409, f"run.meta missing {key}; start a new run")
    _validate_run_meta_for_resume(meta)
    _marker(req.run_id, ".paused", create=False)
    _invalidate_status(None, req.run_id)
    env = _env_assign({
        "RUN_ID": req.run_id,
        "MODELS": meta["models"],
        "MODEL_SET": meta["model_set"],
        "SCENARIOS": meta["scenarios"],
        "SCENARIO_SET": meta["scenario_set"],
        "MEMORY_CONTEXT": meta.get("memory_context") or "none",
        "MEMORY_CONTEXT_FILE": meta.get("memory_context_file") or "",
        "RUN_USER": meta.get("user") or "user",
    })
    inner = (_SYNC + env + " "
             f"setsid nohup ./scripts/run-e2e.sh >{_q(f'/tmp/e2e.{req.run_id}.boot')} "
             f"2>&1 </dev/null & echo relaunched {_q(req.run_id)}")
    cp = _ssh(_home_cmd(inner), timeout=40)
    _invalidate_status(None, req.run_id)
    return {"ok": cp.returncode == 0, "action": "relaunch", "run_id": req.run_id,
            "detail": (cp.stdout or cp.stderr).strip()[:400]}


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    run_id = sock.query_params.get("run_id") or None
    try:
        while True:
            data = await asyncio.get_event_loop().run_in_executor(None, status, run_id)
            await sock.send_json(data)
            run_id = (data.get("run_id") or run_id)
            await asyncio.sleep(POLL_S)
    except (WebSocketDisconnect, RuntimeError):
        return


# --------------------------------------------------------------------------- static
if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8770")))
