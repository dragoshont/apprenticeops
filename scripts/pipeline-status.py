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
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(REPO, "data", "runs")
AI = os.environ.get("AI", "dragos@home-ai.hont.ro")
AI_REPO = os.environ.get("AI_REPO", "/home/dragos/apprenticeops")
STAGES = ["lock", "reset", "infer", "emit", "collect", "judge", "persist"]

# experiment protocol — total work = models x SCEN x REPS inference units, each
# judged by NJUDGES judges. Overridable via env for non-default runs.
REPS = int(os.environ.get("REPS", "5"))
NJUDGES = int(os.environ.get("NJUDGES", "2"))


def _scen_count():
    try:
        s = json.load(open(os.path.join(REPO, "data", "scenarios.json")))
        items = s if isinstance(s, list) else s.get("scenarios", list(s.values()))
        return len(items)
    except Exception:  # noqa: BLE001
        return 24


def _scen_classes():
    """Map scenario id -> class (judged rows carry only the scenario id)."""
    try:
        s = json.load(open(os.path.join(REPO, "data", "scenarios.json")))
        items = s if isinstance(s, list) else s.get("scenarios", list(s.values()))
        return {it.get("id"): it.get("class") for it in items if isinstance(it, dict)}
    except Exception:  # noqa: BLE001
        return {}


SCEN = _scen_count()
SCEN_CLASS = _scen_classes()


def _count_lines(path):
    n = 0
    try:
        with open(path, errors="ignore") as f:
            for ln in f:
                if ln.strip():
                    n += 1
    except OSError:
        return 0
    return n


def _markers(wd):
    return {"canceled": os.path.exists(os.path.join(wd, ".canceled")),
            "paused": os.path.exists(os.path.join(wd, ".paused"))}


def _fmt_eta(seconds):
    """Seconds -> compact 'Xd Yh Zm' (or 'Zm' / 'Ys')."""
    if seconds is None or seconds < 0:
        return None
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d {h}h {m}m"
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m"
    return f"{s}s"


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


def score_breakdown(run_id):
    """Judge-score distribution + mean quality per scenario class, for the charts.
    Judged rows carry score (1-5) + scenario id; class comes from scenarios.json."""
    wd = os.path.join(RUNS, run_id)
    judged = _read_jsonl(os.path.join(wd, f"judged.{run_id}.jsonl"))
    buckets, cls = {}, {}
    for r in judged:
        sc = r.get("score")
        if sc is None:
            continue
        sc = float(sc)
        b = round(sc * 2) / 2          # nearest 0.5
        buckets[b] = buckets.get(b, 0) + 1
        c = SCEN_CLASS.get(r.get("scenario"))
        if c:
            cls.setdefault(c, []).append(sc)
    hist = [{"score": k, "count": buckets[k]} for k in sorted(buckets)]
    by_class = [{"class": c, "quality": round(sum(v) / len(v), 2), "n": len(v)}
                for c, v in sorted(cls.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))]
    return {"hist": hist, "by_class": by_class}


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


def model_progress(run_id, prod, cons):
    """Per-model inference + judge unit counts (for the horizontal progress bars).
    inf unit = (scenario, rep); judge unit = a judged row. Both fill to their total
    as the run advances; a model is complete when both bars hit 100%."""
    wd = os.path.join(RUNS, run_id)
    inf, jud = {}, {}
    for r in _read_jsonl(os.path.join(wd, "_mirror", f"results.{run_id}.jsonl")):
        m = r.get("model")
        if m and r.get("scenario") is not None and r.get("rep") is not None:
            inf.setdefault(m, set()).add((r["scenario"], r["rep"]))
    for r in _read_jsonl(os.path.join(wd, f"judged.{run_id}.jsonl")):
        m = r.get("model")
        if m:
            jud[m] = jud.get(m, 0) + 1
    committed = set(cons["committed_models"])
    done_emit = set(prod["done_models"])
    unit = SCEN * REPS
    out = []
    for m in sorted(set(inf) | set(jud) | done_emit | committed):
        idone = len(inf.get(m, ()))
        jdone = jud.get(m, 0)
        if m in committed:
            stage = "persist"
        elif jdone >= unit * NJUDGES and unit:
            stage = "judge"
        elif jdone:
            stage = "judge"
        elif m in done_emit:
            stage = "emit"
        else:
            stage = "infer"
        out.append({
            "model": m,
            "inf_done": idone, "inf_total": unit,
            "judge_done": jdone, "judge_total": unit * NJUDGES,
            "committed": m in committed, "stage": stage,
        })
    return out


def compute_progress(expect, inf_done, judge_done, started_at, active):
    """Overall run progress + ETA. Work = inference units + judge units."""
    models_total = expect or 0
    inf_total = models_total * SCEN * REPS
    judge_total = inf_total * NJUDGES
    done = inf_done + judge_done
    total = inf_total + judge_total
    pct = round(100 * done / total, 1) if total else 0.0
    now = time.time()
    elapsed = (now - started_at) if started_at else None
    eta_s = rate = None
    if active and elapsed and elapsed > 5 and 0 < done < total:
        rate = done / elapsed              # units/sec
        if rate > 0:
            eta_s = (total - done) / rate
    return {
        "inf_done": inf_done, "inf_total": inf_total,
        "judge_done": judge_done, "judge_total": judge_total,
        "units_done": done, "units_total": total,
        "pct": pct, "pct_remaining": round(100 - pct, 1),
        "elapsed_s": int(elapsed) if elapsed else None,
        "eta_s": int(eta_s) if eta_s else None,
        "eta_human": _fmt_eta(eta_s),
        "rate_per_min": round(rate * 60, 1) if rate else None,
    }


def resolve_state(markers, committed, expect, prod_alive, cons_alive):
    """canceled > done > running > paused > stopped/idle."""
    if markers["canceled"]:
        return "canceled"
    if expect and committed >= expect:
        return "done"
    if prod_alive or cons_alive:
        return "running"
    if markers["paused"]:
        return "paused"
    if committed or prod_alive is not None:
        return "stopped"
    return "idle"


def sessions():
    """Lightweight scan of every run dir for the sessions table. Uses line counts
    (one row == one unit) so it stays fast even for full runs. The active run's
    'running' status is set by the caller (it owns the live process check)."""
    out = []
    for d in sorted(glob.glob(os.path.join(RUNS, "*")), reverse=True):
        if not os.path.isdir(d):
            continue
        rid = os.path.basename(d)
        meta = {}
        try:
            meta = json.load(open(os.path.join(d, "run.meta")))
        except Exception:  # noqa: BLE001
            meta = {}
        mk = _markers(d)
        expect = int(meta.get("expect") or 0)
        inf_done = sum(_count_lines(p) for p in
                       glob.glob(os.path.join(d, "_mirror", "results.*.jsonl")))
        judge_done = sum(_count_lines(p) for p in glob.glob(os.path.join(d, "judged.*.jsonl")))
        committed = _count_lines(os.path.join(d, ".committed"))
        if not expect:
            # historical runs predate run.meta — recover a total from the markers
            done_markers = sum(_count_lines(p) for p in
                               glob.glob(os.path.join(d, "_mirror", "results.*.jsonl.done")))
            expect = max(committed, done_markers)
        inf_total = expect * SCEN * REPS
        judge_total = inf_total * NJUDGES
        total = inf_total + judge_total
        pct = round(100 * (inf_done + judge_done) / total, 1) if total else 0.0
        started = meta.get("started_at")
        # legacy runs predate run.meta — recover a start: the run-id timestamp
        # (<batch>-YYYYMMDD-HHMMSS) if present, else the oldest artefact mtime.
        if not started:
            tm = re.search(r"(\d{8})-(\d{6})", rid)
            if tm:
                try:
                    started = datetime.strptime(tm.group(1) + tm.group(2),
                                                "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).timestamp()
                except ValueError:
                    started = None
        if not started:
            arts = [os.path.getmtime(p) for p in glob.glob(os.path.join(d, "*")) if os.path.isfile(p)]
            arts += [os.path.getmtime(p) for p in glob.glob(os.path.join(d, "_mirror", "*"))]
            started = min(arts) if arts else None
        # last activity = newest mtime among the live artefacts
        act = [os.path.getmtime(p) for p in (
            os.path.join(d, ".committed"),
            os.path.join(d, "judge-scheduler.status"),
            os.path.join(d, f"judged.{rid}.jsonl"),
            os.path.join(d, ".canceled"),
        ) if os.path.exists(p)]
        last = max(act) if act else (os.path.getmtime(d) if os.path.isdir(d) else None)
        state = ("canceled" if mk["canceled"]
                 else "done" if expect and committed >= expect
                 else "paused" if mk["paused"]
                 else "stopped")
        dur = (last - started) if (started and last) else None
        out.append({
            "run_id": rid,
            "batch": meta.get("batch") or "",
            "state": state,
            "started_at": started,
            "ended_at": last,
            "duration_s": int(dur) if dur and dur > 0 else None,
            "models_total": expect,
            "models_done": committed,
            "scenarios": SCEN,
            "reps": REPS,
            "njudges": NJUDGES,
            "inf_done": inf_done, "inf_total": inf_total,
            "judge_done": judge_done, "judge_total": judge_total,
            "pct": pct,
        })
    return out


def main():
    run_id = detect_run_id(sys.argv[1] if len(sys.argv) > 1 else None)
    if not run_id:
        print(json.dumps({"run_id": None, "state": "idle", "ts": time.time(),
                          "batches": batches(), "nodes": nodes(), "sessions": sessions(),
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
    committed_n = len(cons["committed_models"])
    markers = _markers(os.path.join(RUNS, run_id))
    state = resolve_state(markers, committed_n, expect, prod["run_py_alive"], cons["alive"])
    progress = compute_progress(expect, prod["rows"], cons["judged_rows"],
                                meta.get("started_at"), state == "running")
    # the sessions list comes from a cheap scan; correct the active run's live state
    sess = sessions()
    for s in sess:
        if s["run_id"] == run_id:
            s["state"] = state
            if state == "running" and progress.get("eta_s"):
                s["eta_s"] = progress["eta_s"]
                s["eta_human"] = progress["eta_human"]
    print(json.dumps({
        "run_id": run_id,
        "ts": time.time(),
        "state": state,
        "markers": markers,
        "expect": expect,
        "meta": meta,
        "progress": progress,
        "producer": prod,
        "consumer": cons,
        "stages": STAGES,
        "models": per_model_stage(run_id, prod, cons),
        "model_progress": model_progress(run_id, prod, cons),
        "pareto": pareto(run_id, cons),
        "scores": score_breakdown(run_id),
        "batches": batches(),
        "sessions": sess,
        "nodes": nodes(),
    }, default=str))


if __name__ == "__main__":
    main()
