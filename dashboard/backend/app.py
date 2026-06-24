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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HOME_SSH = os.environ.get("HOME_SSH", "homelab")
AI_SSH = os.environ.get("AI_SSH", "home-ai.hont.ro")
REPO_DIR = os.environ.get("REPO_DIR", "~/apprenticeops")
POLL_S = float(os.environ.get("POLL_S", "5"))
# Serve the built Vite app if present (frontend/dist); in dev, Vite serves the UI
# itself and proxies /api + /ws here, so this mount is a no-op.
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "dist"

_RUNID_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
_BATCHID_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")

app = FastAPI(title="ApprenticeOps mission-control", version="0.1.0")


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
    run_id = f"{req.batch}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}"
    inner = (f"RUN_ID='{run_id}' MODELS='{models}' BATCH='{req.batch}' "
             f"setsid nohup ./scripts/run-e2e.sh >/tmp/e2e.{run_id}.boot 2>&1 </dev/null & "
             f"echo launched {run_id}")
    cp = _ssh(_home_cmd(inner), timeout=30)
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
def api_stop():
    return _signal_all("KILL")


@app.post("/api/control/pause")
def api_pause():
    """Best-effort pause: SIGSTOP the schedulers + run.py. The ollama server is a
    separate persistent process, so an in-flight token stream stalls rather than
    cleanly checkpointing — this is a soft hold, not a transactional pause."""
    return _signal_all("STOP")


@app.post("/api/control/resume")
def api_resume(req: RunReq):
    """Continue a paused run (SIGCONT). If nothing is stopped and a run_id is
    given, re-launch the same RUN_ID — the pipeline is model-level resumable, so
    relaunching continues where it left off."""
    cont = _signal_all("CONT")
    if req.run_id:
        if not _RUNID_RE.match(req.run_id):
            raise HTTPException(400, "invalid run_id")
        st = status(req.run_id, max_age=0.0)
        prod_alive = st.get("producer", {}).get("run_py_alive")
        cons_alive = st.get("consumer", {}).get("alive")
        if not (prod_alive or cons_alive):
            inner = (f"RUN_ID='{req.run_id}' setsid nohup ./scripts/run-e2e.sh "
                     f">/tmp/e2e.{req.run_id}.boot 2>&1 </dev/null & echo relaunched {req.run_id}")
            cp = _ssh(_home_cmd(inner), timeout=30)
            _cache["ts"] = 0.0
            return {"ok": cp.returncode == 0, "action": "relaunch", "run_id": req.run_id,
                    "detail": (cp.stdout or cp.stderr).strip()[:400]}
    return {**cont, "action": "continue"}


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
