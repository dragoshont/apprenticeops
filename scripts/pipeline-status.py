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


# the safety/security scenario classes — a model's "security" score is its mean
# judge score on these (higher = safer refusals + correct guardrail behaviour).
SAFETY_CLASSES = {"secure", "guard"}

DEFAULT_SCEN = _scen_count()
DEFAULT_SCEN_CLASS = _scen_classes()


def load_run_meta(run_id):
    try:
        return json.load(open(os.path.join(RUNS, run_id, "run.meta")))
    except Exception:  # noqa: BLE001
        return {}


def scenario_context(meta=None):
    meta = meta or {}
    path = meta.get("scenarios") or "data/scenarios.json"
    full = path if os.path.isabs(path) else os.path.join(REPO, path)
    try:
        data = json.load(open(full))
        items = data if isinstance(data, list) else data.get("scenarios", list(data.values()))
    except Exception:  # noqa: BLE001
        items = []
    classes = {it.get("id"): it.get("class") for it in items if isinstance(it, dict)}
    count = int(meta.get("scenario_count") or len(items) or DEFAULT_SCEN)
    return {
        "count": count,
        "classes": classes or DEFAULT_SCEN_CLASS,
        "path": path,
        "set": meta.get("scenario_set") or "historical-all",
        "historical": not meta.get("scenarios"),
    }


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


def pareto(run_id, cons, scen_class):
    """Per-model quality, energy, speed, watts, and security (mean judge score on
    the safety scenarios — class `secure`/`guard`). Lower energy/watts = better;
    higher quality/security = better."""
    wd = os.path.join(RUNS, run_id)
    judged = _read_jsonl(os.path.join(wd, f"judged.{run_id}.jsonl"))
    jq, sec = {}, {}
    for r in judged:
        sc = r.get("score")
        if sc is None:
            continue
        m = r["model"]
        jq.setdefault(m, []).append(float(sc))
        if scen_class.get(r.get("scenario")) in SAFETY_CLASSES:
            sec.setdefault(m, []).append(float(sc))
    # results live in the mirror on home (or per-model slices committed)
    res = _read_jsonl(os.path.join(wd, "_mirror", f"results.{run_id}.jsonl"))
    sysd = {}
    for r in res:
        m = r.get("model")
        if not m:
            continue
        d = sysd.setdefault(m, {"toks": [], "wh": [], "watts": []})
        if r.get("decode_tok_s"):
            d["toks"].append(r["decode_tok_s"])
        if r.get("power.energy_wh"):
            d["wh"].append(r["power.energy_wh"])
        if r.get("power.mean_watts"):
            d["watts"].append(r["power.mean_watts"])
    out = []
    for m in sorted(set(jq) | set(sysd)):
        toks = sysd.get(m, {}).get("toks", [])
        wh = sysd.get(m, {}).get("wh", [])
        watts = sysd.get(m, {}).get("watts", [])
        q = jq.get(m, [])
        s = sec.get(m, [])
        out.append({
            "model": m,
            "quality": round(sum(q) / len(q), 2) if q else None,
            "security": round(sum(s) / len(s), 2) if s else None,
            "tok_s": round(sorted(toks)[len(toks) // 2], 1) if toks else None,
            "wh": round(sum(wh) / len(wh), 4) if wh else None,
            "watts": round(sum(watts) / len(watts), 1) if watts else None,
            "n": len(q),
        })
    return out


def run_summary(run_id, scen_class):
    """Roll-up metrics for the selected run's detail panel: mean power draw,
    CPU-minutes (sum of wall-clock), total energy, and overall quality/security."""
    wd = os.path.join(RUNS, run_id)
    res = _read_jsonl(os.path.join(wd, "_mirror", f"results.{run_id}.jsonl"))
    judged = _read_jsonl(os.path.join(wd, f"judged.{run_id}.jsonl"))
    watts = [r["power.mean_watts"] for r in res if r.get("power.mean_watts")]
    walls = [r["wall_s"] for r in res if r.get("wall_s")]
    wh = [r["power.energy_wh"] for r in res if r.get("power.energy_wh")]
    q = [float(r["score"]) for r in judged if r.get("score") is not None]
    sec = [float(r["score"]) for r in judged if r.get("score") is not None
           and scen_class.get(r.get("scenario")) in SAFETY_CLASSES]
    return {
        "mean_watts": round(sum(watts) / len(watts), 1) if watts else None,
        "cpu_minutes": round(sum(walls) / 60, 1) if walls else None,
        "energy_wh": round(sum(wh), 3) if wh else None,
        "quality_overall": round(sum(q) / len(q), 2) if q else None,
        "security_overall": round(sum(sec) / len(sec), 2) if sec else None,
        "n": len(q),
        "n_security": len(sec),
    }


def score_breakdown(run_id, scen_class):
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
        c = scen_class.get(r.get("scenario"))
        if c:
            cls.setdefault(c, []).append(sc)
    hist = [{"score": k, "count": buckets[k]} for k in sorted(buckets)]
    by_class = [{"class": c, "quality": round(sum(v) / len(v), 2), "n": len(v)}
                for c, v in sorted(cls.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))]
    return {"hist": hist, "by_class": by_class}


def _annotate_freq(lines):
    """Make the ai node's `freq=` line self-explanatory. When Turbo is OFF *and* the
    governor is `performance` the clock is pinned to the experiment's base regime
    (locked, ~1.7 GHz on the i5-8350U); when Turbo is ON the node is idle/unlocked and
    boosts (~3.6 GHz) — which is why a FINISHED run shows a high clock. Honest label so
    the number is not mistaken for a determinism leak (the in-run rows carry the real
    pinned freq). "locked" is claimed only when BOTH turbo and governor match the
    regime — a turbo-off-but-governor-drifted node is labelled by its turbo state."""
    turbo = next((l.split("=", 1)[1].strip() for l in lines if l.startswith("turbo=")), None)
    gov = next((l.split("=", 1)[1].strip() for l in lines if l.startswith("gov=")), None)
    out = []
    for l in lines:
        if l.startswith("freq=") and turbo in ("0", "1"):
            if turbo == "1":
                tag = "locked · turbo off" if gov == "performance" else f"turbo off · gov {gov}"
            else:
                tag = "unlocked · turbo on"
            out.append(f"{l} ({tag})")
        else:
            out.append(l)
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
        "ai": {"reachable": bool(ai), "lines": _annotate_freq([l for l in ai.splitlines() if l])},
    }


def run_matrix():
    """Resolved run matrix for the dashboard. Mirrors backend/app.py without SSH."""
    try:
        matrix = json.load(open(os.path.join(REPO, "data", "run-matrix.json")))
    except Exception:  # noqa: BLE001
        return {"defaults": {}, "model_sets": [], "scenario_sets": [], "memory_contexts": [], "scenarios": []}

    def sha(path):
        import hashlib
        return hashlib.sha256(open(os.path.join(REPO, path), "rb").read()).hexdigest()

    def model_count(path):
        try:
            with open(os.path.join(REPO, path)) as fh:
                return sum(1 for l in fh if l.strip() and not l.lstrip().startswith("#"))
        except OSError:
            return None

    def load_scenarios(path):
        try:
            return json.load(open(os.path.join(REPO, path))).get("scenarios", [])
        except Exception:  # noqa: BLE001
            return []

    model_sets = [{**m, "model_count": model_count(m.get("path", "")), "sha256": sha(m.get("path", ""))}
                  for m in matrix.get("model_sets", [])]
    memory_contexts = []
    for item in matrix.get("memory_contexts", []):
        path = item.get("path")
        if path:
            full = os.path.join(REPO, path)
            try:
                memory_contexts.append({**item, "byte_count": os.path.getsize(full), "sha256": sha(path)})
            except OSError:
                memory_contexts.append({**item, "byte_count": None, "sha256": None})
        else:
            memory_contexts.append({**item, "path": None, "byte_count": 0, "sha256": None})
    scenario_sets = []
    scenario_rows = {}
    for sset in matrix.get("scenario_sets", []):
        items = load_scenarios(sset.get("path", ""))
        scenario_sets.append({
            **sset,
            "scenario_count": len(items),
            "class_counts": _counts(it.get("class") for it in items if isinstance(it, dict)),
            "difficulty_counts": _counts(it.get("difficulty") for it in items if isinstance(it, dict)),
            "grounding_counts": _counts(it.get("grounding") for it in items if isinstance(it, dict)),
            "scenario_ids": [it.get("id") for it in items if isinstance(it, dict) and it.get("id")],
            "sha256": sha(sset.get("path", "")),
        })
        for scenario in items:
            row = scenario_rows.setdefault(scenario.get("id"), {
                "id": scenario.get("id"),
                "class": scenario.get("class"),
                "difficulty": scenario.get("difficulty"),
                "grounding": scenario.get("grounding"),
                "brief": (scenario.get("question") or scenario.get("gold_answer") or "").split("\n", 1)[0][:180],
                "sets": [],
            })
            if sset.get("id") not in row["sets"]:
                row["sets"].append(sset.get("id"))
    return {"defaults": matrix.get("defaults", {}), "model_sets": model_sets,
            "scenario_sets": scenario_sets, "memory_contexts": memory_contexts,
            "scenarios": sorted((r for r in scenario_rows.values() if r.get("id")), key=lambda r: r["id"])}


def _counts(values):
    out = {}
    for value in values:
        key = value or "unknown"
        out[key] = out.get(key, 0) + 1
    return out


def model_progress(run_id, prod, cons, scen_count):
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
    unit = scen_count * REPS
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


def compute_progress(expect, inf_done, judge_done, started_at, active, scen_count):
    """Overall run progress + ETA. Work = inference units + judge units."""
    models_total = expect or 0
    inf_total = models_total * scen_count * REPS
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
        scen_ctx = scenario_context(meta)
        scen_count = scen_ctx["count"]
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
        inf_total = expect * scen_count * REPS
        judge_total = inf_total * NJUDGES
        total = inf_total + judge_total
        pct = round(100 * (inf_done + judge_done) / total, 1) if total else 0.0
        started = meta.get("started_at")
        # historical runs may predate run.meta — recover a start from any
        # YYYYMMDD-HHMMSS token in the id, else the oldest artefact mtime.
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
            "model_set": meta.get("model_set") or "historical",
            "scenario_set": meta.get("scenario_set") or scen_ctx["set"],
            "memory_context": meta.get("memory_context") or "none",
            "historical": scen_ctx["historical"],
            "user": meta.get("user") or "user",
            "state": state,
            "started_at": started,
            "ended_at": last,
            "duration_s": int(dur) if dur and dur > 0 else None,
            "models_total": expect,
            "models_done": committed,
            "scenarios": scen_count,
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
                          "run_matrix": run_matrix(), "nodes": nodes(), "sessions": sessions(),
                          "runs": [os.path.basename(d) for d in
                                   sorted(glob.glob(os.path.join(RUNS, "*")))]}))
        return
    prod = producer_state(run_id)
    cons = consumer_state(run_id)
    meta = load_run_meta(run_id)
    scen_ctx = scenario_context(meta)
    scen_count = scen_ctx["count"]
    scen_class = scen_ctx["classes"]
    expect = meta.get("expect") or len(set(prod["done_models"]) | set(cons["committed_models"])) or 0
    committed_n = len(cons["committed_models"])
    markers = _markers(os.path.join(RUNS, run_id))
    state = resolve_state(markers, committed_n, expect, prod["run_py_alive"], cons["alive"])
    progress = compute_progress(expect, prod["rows"], cons["judged_rows"],
                                meta.get("started_at"), state == "running", scen_count)
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
        "user": meta.get("user") or "user",
        "progress": progress,
        "summary": run_summary(run_id, scen_class),
        "producer": prod,
        "consumer": cons,
        "stages": STAGES,
        "models": per_model_stage(run_id, prod, cons),
        "model_progress": model_progress(run_id, prod, cons, scen_count),
        "pareto": pareto(run_id, cons, scen_class),
        "scores": score_breakdown(run_id, scen_class),
        "run_matrix": run_matrix(),
        "sessions": sess,
        "nodes": nodes(),
    }, default=str))


if __name__ == "__main__":
    main()
