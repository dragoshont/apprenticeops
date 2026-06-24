#!/usr/bin/env python3
"""pipeline-status.py — emit the FULL experiment-pipeline state as one JSON blob.

Runs ON the home node (stdlib only). The dashboard backend invokes it over SSH and
serves the result; keeping the gather logic here (versioned + testable) instead of
in the web app. Best-effort: never raises on a missing file — absent data => nulls.

  python3 scripts/pipeline-status.py [RUN_ID]      # RUN_ID auto-detected if omitted
"""
from __future__ import annotations

import glob
import json
import os
import re
import shlex
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(REPO, "data", "runs")
AI = os.environ.get("AI", "dragos@home-ai.hont.ro")
AI_REPO = os.environ.get("AI_REPO", "/home/dragos/apprenticeops")
STAGES = ["lock", "reset", "infer", "emit", "collect", "judge", "persist"]


def _sh(cmd, timeout=12):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _ai(remote_cmd, timeout=12):
    """Run a command on the ai node from home (passwordless). shlex.quote keeps the
    local shell from expanding $(...)/$N before ssh forwards it to the ai shell."""
    return _sh(f"ssh -o BatchMode=yes -o ConnectTimeout=6 {AI} {shlex.quote(remote_cmd)}", timeout)


def _pgrepc(pattern):
    out = _sh(f"pgrep -fc '{pattern}'")
    try:
        return int(out)
    except ValueError:
        return 0


def _tail(path, n=40):
    try:
        with open(path, errors="ignore") as f:
            return f.readlines()[-n:]
    except OSError:
        return []


def _read_jsonl(path, limit=None):
    rows = []
    try:
        with open(path, errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows[-limit:] if limit else rows


def detect_run_id(explicit=None):
    if explicit:
        return explicit
    cands = []
    for d in glob.glob(os.path.join(RUNS, "*")):
        if not os.path.isdir(d):
            continue
        marker = os.path.join(d, "e2e.log")
        st = os.path.join(d, "judge-scheduler.status")
        mt = max((os.path.getmtime(p) for p in (marker, st) if os.path.exists(p)), default=0)
        if mt:
            cands.append((mt, os.path.basename(d)))
    cands.sort(reverse=True)
    return cands[0][1] if cands else None


def producer_state(run_id):
    """Inference side. Rows/.done come from home's local mirror (reliable); the ai
    node is asked only whether run.py is still inferring + for the driver tail."""
    wd = os.path.join(RUNS, run_id)
    mres = os.path.join(wd, "_mirror", f"results.{run_id}.jsonl")
    rows = 0
    if os.path.exists(mres):
        try:
            with open(mres, errors="ignore") as f:
                rows = sum(1 for ln in f if ln.strip())
        except OSError:
            rows = 0
    done_models = [d.get("model") for d in
                   _read_jsonl(os.path.join(wd, "_mirror", f"results.{run_id}.jsonl.done"))]
    done_models = [m for m in done_models if m]
    alive = False
    try:
        alive = int(_ai("pgrep -fc '[r]un.py --models' 2>/dev/null || echo 0") or 0) > 0
    except ValueError:
        pass
    driver = [l for l in _ai(f"tail -n 4 {AI_REPO}/logs/{run_id}/driver.log 2>/dev/null").splitlines() if l]
    return {"rows": rows, "models_emitted": len(done_models),
            "run_py_alive": alive, "done_models": done_models, "driver_tail": driver}


def consumer_state(run_id):
    """Judge + commit side, on home."""
    wd = os.path.join(RUNS, run_id)
    judged = _read_jsonl(os.path.join(wd, f"judged.{run_id}.jsonl"))
    committed = []
    try:
        committed = [m.strip() for m in open(os.path.join(wd, ".committed")) if m.strip()]
    except OSError:
        pass
    status = ""
    try:
        status = open(os.path.join(wd, "judge-scheduler.status")).read().strip()
    except OSError:
        pass
    ledger = _read_jsonl(os.path.join(wd, "pipeline-ledger.jsonl"))
    # errors / skips from the judge log
    skips = [l.strip() for l in _tail(os.path.join(wd, "judge.log"), 400) if "SKIP after" in l]
    judged_models = sorted({r.get("model") for r in judged if r.get("model")})
    return {
        "alive": bool(_pgrepc("[j]udge-scheduler")),
        "status": status,
        "judged_rows": len(judged),
        "judged_models": judged_models,
        "committed_models": committed,
        "ledger_tail": ledger[-30:],
        "skips": skips[-30:],
        "skip_count": len(skips),
    }


def per_model_stage(run_id, prod, cons):
    """Roll the ledger + markers up into one stage per model."""
    stage = {}
    for m in prod["done_models"]:
        stage[m] = "emit"
    for ev in cons["ledger_tail"]:
        m = ev.get("model")
        if m and m != "*":
            stage[m] = ev.get("stage", stage.get(m))
    for m in cons["judged_models"]:
        if stage.get(m) in (None, "emit", "collect", "judge"):
            stage[m] = "judge"
    for m in cons["committed_models"]:
        stage[m] = "persist"
    return [{"model": m, "stage": s} for m, s in sorted(stage.items())]


def pareto(run_id, cons):
    """Per-model quality x energy x speed, as data accumulates."""
    wd = os.path.join(RUNS, run_id)
    judged = _read_jsonl(os.path.join(wd, f"judged.{run_id}.jsonl"))
    jq = {}
    for r in judged:
        if r.get("score") is not None:
            jq.setdefault(r["model"], []).append(float(r["score"]))
    # results live in the mirror on home (or per-model slices committed)
    res = _read_jsonl(os.path.join(wd, "_mirror", f"results.{run_id}.jsonl"))
    sysd = {}
    for r in res:
        m = r.get("model")
        if not m:
            continue
        d = sysd.setdefault(m, {"toks": [], "wh": []})
        if r.get("decode_tok_s"):
            d["toks"].append(r["decode_tok_s"])
        if r.get("power.energy_wh"):
            d["wh"].append(r["power.energy_wh"])
    out = []
    for m in sorted(set(jq) | set(sysd)):
        toks = sysd.get(m, {}).get("toks", [])
        wh = sysd.get(m, {}).get("wh", [])
        q = jq.get(m, [])
        out.append({
            "model": m,
            "quality": round(sum(q) / len(q), 2) if q else None,
            "tok_s": round(sorted(toks)[len(toks) // 2], 1) if toks else None,
            "wh": round(sum(wh) / len(wh), 4) if wh else None,
            "n": len(q),
        })
    return out


def nodes():
    home = _sh("echo $(hostname); uptime | sed 's/.*load average/load/'; "
               "free -m | awk '/Mem:/{print $3\"/\"$2\" MB\"}'; "
               "df -h / | awk 'NR==2{print $5\" used\"}'")
    ai = _ai("echo $(hostname); ollama --version 2>/dev/null | head -1; "
             "echo turbo=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null); "
             "echo gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null); "
             "echo freq=$(awk '{s+=$1;n++}END{if(n)printf \"%d\",s/n/1000}' /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq 2>/dev/null)MHz; "
             "free -m | awk '/Mem:/{print $3\"/\"$2\" MB\"}'; df -h / | awk 'NR==2{print $5\" used\"}'")
    return {
        "home": {"reachable": True, "lines": [l for l in home.splitlines() if l]},
        "ai": {"reachable": bool(ai), "lines": [l for l in ai.splitlines() if l]},
    }


def batches():
    """The run batches the dashboard offers at Start (data/batches.json) + live counts."""
    try:
        items = json.load(open(os.path.join(REPO, "data", "batches.json"))).get("batches", [])
    except Exception:  # noqa: BLE001
        items = []
    out = []
    for b in items:
        if not isinstance(b, dict) or not b.get("id"):
            continue
        cnt = None
        try:
            with open(os.path.join(REPO, b.get("models", ""))) as fh:
                cnt = sum(1 for l in fh if l.strip() and not l.lstrip().startswith("#"))
        except OSError:
            pass
        out.append({**b, "count": cnt})
    return out


def main():
    run_id = detect_run_id(sys.argv[1] if len(sys.argv) > 1 else None)
    if not run_id:
        print(json.dumps({"run_id": None, "state": "idle", "ts": time.time(),
                          "batches": batches(), "nodes": nodes(),
                          "runs": [os.path.basename(d) for d in
                                   sorted(glob.glob(os.path.join(RUNS, "*")))]}))
        return
    prod = producer_state(run_id)
    cons = consumer_state(run_id)
    meta = {}
    try:
        meta = json.load(open(os.path.join(RUNS, run_id, "run.meta")))
    except Exception:  # noqa: BLE001
        meta = {}
    expect = meta.get("expect") or len(set(prod["done_models"]) | set(cons["committed_models"])) or 0
    running = prod["run_py_alive"] or cons["alive"]
    done = expect and len(cons["committed_models"]) >= expect
    state = "done" if done else ("running" if running else "paused")
    print(json.dumps({
        "run_id": run_id,
        "ts": time.time(),
        "state": state,
        "expect": expect,
        "meta": meta,
        "producer": prod,
        "consumer": cons,
        "stages": STAGES,
        "models": per_model_stage(run_id, prod, cons),
        "pareto": pareto(run_id, cons),
        "batches": batches(),
        "nodes": nodes(),
    }, default=str))


if __name__ == "__main__":
    main()
