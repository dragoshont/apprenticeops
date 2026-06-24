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

Injection safety: the browser can only pick a *batch id* (validated against the
server-side allowlist loaded from ``data/batches.json``) and a *run id* (validated
against ``^[A-Za-z0-9._-]+$``). RUN_IDs for new runs are generated server-side.
Nothing the client sends is interpolated raw into a shell.

Env:
  HOME_SSH    SSH destination for the home node     (default: "homelab")
  AI_SSH      how home reaches the ai node           (default: "home-ai.hont.ro")
  REPO_DIR    repo path on home                      (default: "~/apprenticeops")
  POLL_S      websocket push cadence, seconds        (default: 5)
  HOST/PORT   bind                                   (default: 127.0.0.1:8770)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import time
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
_BATCHID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")

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
         "git checkout -q origin/main -- scripts data/batches.json data/scenarios.json 2>/dev/null; ")


def _marker(run_id: str, name: str, create: bool) -> None:
    """Create or remove a run marker file (.canceled/.paused) on home."""
    if not _RUNID_RE.match(run_id) or name not in (".canceled", ".paused"):
        return
    path = f"data/runs/{run_id}/{name}"
    inner = f"touch {path}" if create else f"rm -f {path}"
    _ssh(_home_cmd(inner), timeout=15)


# --------------------------------------------------------------------------- status
_cache: dict = {"ts": 0.0, "run_id": None, "data": None}


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


def status(run_id: str | None, max_age: float = 3.0) -> dict:
    now = time.time()
    if (_cache["data"] is not None and _cache["run_id"] == run_id
            and now - _cache["ts"] < max_age):
        return _cache["data"]
    data = _gather(run_id)
    _cache.update(ts=now, run_id=run_id, data=data)
    return data


def _batches() -> list[dict]:
    cp = _ssh(_home_cmd("cat data/batches.json"), timeout=15)
    if cp.returncode == 0:
        try:
            return json.loads(cp.stdout).get("batches", [])
        except json.JSONDecodeError:
            pass
    # fall back to whatever a status call carries
    return status(None).get("batches", [])


def _resolve_batch(batch_id: str) -> dict:
    if not _BATCHID_RE.match(batch_id or ""):
        raise HTTPException(400, "invalid batch id")
    for b in _batches():
        if b.get("id") == batch_id:
            return b
    raise HTTPException(404, f"unknown batch '{batch_id}'")


# ----------------------------------------------------------------------------- api
class StartReq(BaseModel):
    batch: str


class RunReq(BaseModel):
    run_id: str | None = None


@app.get("/api/status")
def api_status(run_id: str | None = None):
    return JSONResponse(status(run_id))


@app.get("/api/batches")
def api_batches():
    return {"batches": _batches()}


@app.post("/api/control/start")
def api_start(req: StartReq):
    b = _resolve_batch(req.batch)
    models = b.get("models", "")
    if not re.match(r"^[A-Za-z0-9._/-]{1,120}$", models):
        raise HTTPException(400, "batch points at an unsafe models path")
    # one run at a time: refuse if a run is currently active (running or paused).
    cur = status(None, max_age=0.0)
    active = (cur.get("state") in ("running", "paused")
              or (cur.get("producer") or {}).get("run_py_alive")
              or (cur.get("consumer") or {}).get("alive"))
    if active:
        raise HTTPException(409, f"a run is already active ({cur.get('run_id')}) — stop it first")
    run_id = f"{req.batch}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    inner = (_SYNC +
             f"RUN_ID='{run_id}' MODELS='{models}' BATCH='{req.batch}' "
             f"setsid nohup ./scripts/run-e2e.sh >/tmp/e2e.{run_id}.boot 2>&1 </dev/null & "
             f"echo launched {run_id}")
    cp = _ssh(_home_cmd(inner), timeout=40)
    ok = cp.returncode == 0 and "launched" in cp.stdout
    _cache["ts"] = 0.0
    return {"ok": ok, "run_id": run_id, "batch": req.batch, "models": models,
            "detail": (cp.stdout or cp.stderr).strip()[:400]}


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
    return {**_signal_all("KILL"), "action": "cancel", "run_id": req.run_id}


@app.post("/api/control/pause")
def api_pause(req: RunReq):
    """Pause = soft hold. SIGSTOP the schedulers + run.py (the process freezes with
    all state intact) and write a .paused marker. Continue resumes it exactly. The
    ollama server is separate, so an in-flight token stream stalls rather than
    checkpointing — but no rows are lost."""
    if req.run_id:
        _marker(req.run_id, ".paused", create=True)
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
    st = status(req.run_id, max_age=0.0)
    if st.get("markers", {}).get("canceled"):
        raise HTTPException(409, "run was canceled — start a new run instead")
    prod_alive = st.get("producer", {}).get("run_py_alive")
    cons_alive = st.get("consumer", {}).get("alive")
    _marker(req.run_id, ".paused", create=False)
    cont = _signal_all("CONT")
    if not (prod_alive or cons_alive):
        inner = (_SYNC +
                 f"RUN_ID='{req.run_id}' setsid nohup ./scripts/run-e2e.sh "
                 f">/tmp/e2e.{req.run_id}.boot 2>&1 </dev/null & echo relaunched {req.run_id}")
        cp = _ssh(_home_cmd(inner), timeout=40)
        _cache["ts"] = 0.0
        return {"ok": cp.returncode == 0, "action": "relaunch", "run_id": req.run_id,
                "detail": (cp.stdout or cp.stderr).strip()[:400]}
    return {**cont, "action": "continue", "run_id": req.run_id}


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
