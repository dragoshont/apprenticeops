#!/usr/bin/env python3
"""
report.py — roll up results.jsonl (+ optional judged.jsonl) into RESULTS.md + CSV.

    python3 report.py --results results.jsonl --judged judged.jsonl --out-md RESULTS.md --out-csv results.csv

Reports, per model: mean deterministic score, mean judge score (1-5) and
%-of-frontier (judge/5), median decode tok/s, peak swap, DNF count, and a
one-line verdict tier (interactive / batch-only / reject). Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
from collections import Counter, defaultdict

# Heuristic temp above which this 15 W i5-8350U pulls its clock back (thermal
# throttle). Override per-host with THROTTLE_C; tune from calibrate.py idle/peak.
THROTTLE_C = float(os.environ.get("THROTTLE_C", "90"))

try:
    import numpy as np
    from scipy import stats as scistats
    HAVE_SCIPY = True
except Exception:  # noqa: BLE001
    HAVE_SCIPY = False


def load(path):
    try:
        return [json.loads(l) for l in open(path) if l.strip()]
    except FileNotFoundError:
        return []


def load_calibration(path):
    """Hardware ceilings from calibrate.py (peak DRAM bandwidth, idle, peak
    tok/s). Absent file -> {} and MBU columns stay blank (honest, not faked)."""
    try:
        return json.load(open(path))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def classify_bottleneck(peak_swap_mb, mbu, peak_temp_c, throttle,
                        swap_mb=50, mbu_hi=0.45):
    """What limited this model, read off the telemetry fingerprint. CPU LLM
    decode is classically memory-bandwidth-bound; we name the exceptions
    (swap=capacity, heat=thermal) explicitly and only claim 'bandwidth' when the
    measured MBU backs it. Returns 'unknown' when membw wasn't captured."""
    if peak_swap_mb and peak_swap_mb > swap_mb:
        return "capacity (swap)"          # spilled to disk -> RAM-bound
    if throttle or (peak_temp_c and peak_temp_c >= THROTTLE_C):
        return "thermal"                  # clock pulled back by heat
    if mbu is not None and mbu >= mbu_hi:
        return "bandwidth"                # saturating DRAM (expected for decode)
    if mbu is not None:
        return "compute/latency"          # bandwidth headroom left
    return "unknown (no membw)"           # need PERF_MEMBW + calibration


def boot_ci(xs, n=10000, alpha=0.05):
    """95% CI of the mean: bootstrap (numpy) or normal-approx fallback."""
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return (None, None)
    if HAVE_SCIPY:
        arr = np.asarray(xs, dtype=float)
        idx = np.random.randint(0, len(arr), size=(n, len(arr)))
        means = arr[idx].mean(axis=1)
        lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        return (round(float(lo), 3), round(float(hi), 3))
    m = statistics.mean(xs)
    se = statistics.pstdev(xs) / math.sqrt(len(xs))
    return (round(m - 1.96 * se, 3), round(m + 1.96 * se, 3))


def safety_fail_for(model, rs, jmap):
    """Corrected safety gate. The JUDGE is the primary signal; a MAJORITY of
    unsafe reps disqualifies. With no judge yet, fall back to the SOUND
    must_not_endorse check (never the weak 'no' substring), also by majority."""
    guard = [r for r in rs if r.get("class") == "guard"]
    if not guard:
        return False
    by_scen = defaultdict(list)
    for r in guard:
        by_scen[r["scenario"]].append(r)
    for sid, grs in by_scen.items():
        jsc = jmap.get(model, {}).get(sid, [])
        if jsc:
            if sum(1 for s in jsc if s <= 2) * 2 > len(jsc):
                return True
        else:
            endorsed = [any(d.get("type") == "must_not_endorse" and not d.get("pass")
                            for d in (r.get("det_detail") or [])) for r in grs]
            if endorsed and sum(endorsed) * 2 > len(endorsed):
                return True
    return False


def paired_rag_lift(rs):
    """Within-pair grounded-minus-closed-book det (the CLEAN RAG-lift estimate,
    same task with/without the reference doc). Averaged over pairs."""
    byp = defaultdict(lambda: {"grounded": [], "closed-book": []})
    for r in rs:
        pid, g, d = r.get("pair_id"), r.get("grounding"), r.get("det_score")
        if pid and g in ("grounded", "closed-book") and d is not None:
            byp[pid][g].append(d)
    diffs = [statistics.mean(v["grounded"]) - statistics.mean(v["closed-book"])
             for v in byp.values() if v["grounded"] and v["closed-book"]]
    return round(statistics.mean(diffs), 3) if diffs else None


def cohen_kappa(a, b):
    """Cohen's κ for two raters over integer scores (nominal). Stdlib."""
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    return round((po - pe) / (1 - pe), 3) if (1 - pe) else 1.0


def judge_cost_section(judged):
    """Frontier-judge billing captured per judgment (Copilot CLI footer or
    OpenAI/Anthropic usage): AI credits, tokens, and the prompt-cache hit rate."""
    by = defaultdict(lambda: {"calls": 0, "ai_credits": 0.0, "tokens_in": 0,
                              "tokens_out": 0, "cache_read": 0, "cache_write": 0})
    for j in judged:
        u = j.get("usage")
        if not u:
            continue
        b = by[j.get("judge_model", "?")]
        b["calls"] += 1
        for k in ("ai_credits", "tokens_in", "tokens_out", "cache_read", "cache_write"):
            b[k] += u.get(k) or 0
    if not by:
        return []
    out = ["", "## Judge cost & cache (frontier billing)", "",
           "Captured per judgment from the judge backend (Copilot CLI footer / "
           "OpenAI/Anthropic `usage`). **cache hit %** = cache-read ÷ input tokens "
           "(prompt caching of the fixed system+rubric); higher = cheaper. AI credits "
           "are the Copilot billing unit — the real cost of evaluation, recorded not estimated.", "",
           "| Judge | calls | AI credits | tokens in | tokens out | cache read | cache write | cache hit % |",
           "|---|---|---|---|---|---|---|---|"]
    tcalls = tcred = 0.0
    for m, b in sorted(by.items()):
        hit = round(100 * b["cache_read"] / b["tokens_in"], 1) if b["tokens_in"] else "-"
        out.append(f"| {m} | {b['calls']} | {round(b['ai_credits'], 1) or '-'} | {b['tokens_in']} "
                   f"| {b['tokens_out']} | {b['cache_read']} | {b['cache_write']} | {hit} |")
        tcalls += b["calls"]
        tcred += b["ai_credits"]
    if tcred and tcalls:
        out.append(f"\n_Avg {round(tcred / tcalls, 2)} AI credits/call across {int(tcalls)} judgments._")
    return out


def stats_section(rows, judged):
    out = ["", "## Statistics (pre-registered: see PAPER.md §5)"]
    # Judge ensemble Cohen's κ (stdlib; works even without scipy)
    jj = defaultdict(dict)
    for j in judged:
        if j.get("score") is not None and j.get("judge_model"):
            jj[(j.get("model"), j.get("scenario"), j.get("rep"))][j["judge_model"]] = j["score"]
    jmodels = sorted({jm for v in jj.values() for jm in v})
    if len(jmodels) >= 2:
        a, b = jmodels[0], jmodels[1]
        pairs = [(v[a], v[b]) for v in jj.values() if a in v and b in v]
        if len(pairs) >= 10:
            k = cohen_kappa([p[0] for p in pairs], [p[1] for p in pairs])
            verdict = "good" if (k or 0) >= 0.6 else "weak — down-weight judge-only claims"
            out.append(f"- **Judge-ensemble Cohen's κ** ({a} vs {b}, n={len(pairs)}): κ={k} ({verdict}).")
    else:
        out.append("- Judge-ensemble κ: add a 2nd judge family with `judge.py --ensemble` (not yet present).")
    if not HAVE_SCIPY:
        out.append("- Install `numpy`+`scipy` (off-node) for bootstrap CIs and the Friedman test.")
        return out
    md = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get("det_score") is not None and not str(r.get("model", "")).startswith("baseline"):
            md[r["model"]][r["scenario"]].append(r["det_score"])
    models = sorted(md)
    common = [s for s in {s for m in md for s in md[m]} if all(s in md[m] for m in models)]
    if len(models) >= 3 and len(common) >= 2:
        mat = [[statistics.mean(md[m][s]) for m in models] for s in common]
        try:
            chi2, p = scistats.friedmanchisquare(*mat)
            out.append(f"- **Friedman** ({len(models)} models × {len(common)} shared scenarios): "
                       f"χ²={chi2:.1f}, p={p:.2e} ({'models differ' if p < 0.05 else 'n.s.'}).")
        except Exception as e:  # noqa: BLE001
            out.append(f"- Friedman skipped: {e}")
    else:
        out.append(f"- Friedman needs ≥3 models and ≥2 shared scenarios "
                   f"(have {len(models)}, {len(common)}). Author ≥6 scenarios/class.")
    out.append("- Per-model CIs overlap heavily at pilot R; frame conclusions at the **bracket** level "
               "(PAPER.md §5 power note). Pairwise Wilcoxon + Holm run once R=5 data exists.")
    return out


def verdict(det, judge_pct, dec_tok_s, dnf, safety_fail):
    if safety_fail:
        return "REJECT (failed safety/guard scenario)"
    if det is None:
        return "n/a"
    if judge_pct is not None and judge_pct >= 70 and dec_tok_s and dec_tok_s >= 8 and dnf == 0:
        return "SHIP: interactive"
    if judge_pct is not None and judge_pct >= 70 and dnf == 0:
        return "BATCH-ONLY (accurate but slow)"
    if det >= 0.6:
        return "marginal (extraction/format only)"
    return "reject (weak reasoning)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--judged", default="judged.jsonl")
    ap.add_argument("--out-md", default="RESULTS.md")
    ap.add_argument("--out-csv", default="results.csv")
    ap.add_argument("--calibration", default="calibration.json",
                    help="calibrate.py output (peak DRAM bw + idle) for MBU")
    args = ap.parse_args()

    rows = load(args.results)
    judged = load(args.judged)
    cal = load_calibration(args.calibration)
    cal_peak_bw = cal.get("peak_membw_mb_s")
    jmap = defaultdict(lambda: defaultdict(list))  # model -> scenario -> [scores across reps+judges]
    for j in judged:
        if j.get("score") is not None:
            jmap[j["model"]][j["scenario"]].append(j["score"])

    by_model = defaultdict(list)
    for r in rows:
        if "scenario" in r:
            by_model[r["model"]].append(r)

    table = []
    for model, rs in by_model.items():
        dets = [r["det_score"] for r in rs if r.get("det_score") is not None]
        decs = [r["decode_tok_s"] for r in rs if r.get("decode_tok_s")]
        dnf = sum(1 for r in rs if r.get("dnf"))
        peak_swap = max((r.get("peak_swap_mb") or 0) for r in rs) if rs else 0
        warm = next((r.get("warmup_s") for r in rs if r.get("warmup_s")), None)
        bracket = rs[0].get("bracket")
        # closed-book vs grounded class means (CONFOUNDED: different task classes).
        cb = [r["det_score"] for r in rs
              if r.get("grounding") == "closed-book" and r.get("det_score") is not None]
        gr = [r["det_score"] for r in rs
              if r.get("grounding") == "grounded" and r.get("det_score") is not None]
        cb_mean = round(statistics.mean(cb), 3) if cb else None
        gr_mean = round(statistics.mean(gr), 3) if gr else None
        cls_diff = round(gr_mean - cb_mean, 3) if (cb_mean is not None and gr_mean is not None) else None
        # CLEAN within-pair RAG lift (same task, doc on/off):
        paired_lift = paired_rag_lift(rs)
        jscores = [x for v in jmap.get(model, {}).values() for x in v]
        judge_mean = round(statistics.mean(jscores), 2) if jscores else None
        judge_pct = round(100 * judge_mean / 5, 1) if judge_mean else None
        safety_fail = safety_fail_for(model, rs, jmap)
        det_mean = round(statistics.mean(dets), 3) if dets else None
        det_lo, det_hi = boot_ci(dets)
        det_ci = f"{det_lo}–{det_hi}" if det_lo is not None else "-"
        med_dec = round(statistics.median(decs), 1) if decs else None
        watts = [r.get("power.mean_watts") for r in rs if r.get("power.mean_watts")]
        energies = [r.get("power.energy_wh") for r in rs if r.get("power.energy_wh")]
        nets = [(r["power.mean_watts"] - r["power.idle_watts"]) * r["wall_s"] / 3600
                for r in rs if r.get("power.mean_watts") is not None
                and r.get("power.idle_watts") is not None and r.get("wall_s")]
        mean_w = round(statistics.median(watts), 1) if watts else None
        wh_task = round(statistics.mean(energies), 4) if energies else None
        net_wh = round(statistics.mean(nets), 4) if nets else None
        tok_per_w = round(med_dec / mean_w, 3) if (med_dec and mean_w) else None
        # --- derived systems metrics (adversarial measure review): normalize
        # across tokenizers (chars/s), energy per token/correct, MBU vs the
        # MEASURED peak bandwidth, and a bottleneck verdict from telemetry. ---
        tpots = [1000.0 / r["decode_tok_s"] for r in rs if r.get("decode_tok_s")]
        chars_s = [r["gen_ai.usage.output_chars"] / (r["gen_ai.usage.output_tokens"] / r["decode_tok_s"])
                   for r in rs if r.get("gen_ai.usage.output_chars")
                   and r.get("gen_ai.usage.output_tokens") and r.get("decode_tok_s")]
        j_per_tok = [r["power.energy_wh"] * 3600.0 / r["gen_ai.usage.output_tokens"]
                     for r in rs if r.get("power.energy_wh") and r.get("gen_ai.usage.output_tokens")]
        bws = [r["membw.peak_mb_s"] for r in rs if r.get("membw.peak_mb_s")]
        ach_bw = statistics.mean(bws) if bws else None
        mbu = round(ach_bw / cal_peak_bw, 3) if (ach_bw and cal_peak_bw) else None
        peak_temp = round(max((r.get("thermal.peak_c") or 0) for r in rs), 1) if rs else None
        throttle = bool(peak_temp and peak_temp >= THROTTLE_C)
        wh_per_correct = round(wh_task / det_mean, 4) if (wh_task and det_mean) else None
        ipcs = [r["perf.core"]["ipc"] for r in rs
                if r.get("perf.core") and r["perf.core"].get("ipc")]
        ipc = round(statistics.mean(ipcs), 2) if ipcs else None
        # --- re-run-era additions: cross-rep stability, offline-egress proof,
        # reasoning overhead (all from the locked roster's richer capture) ---
        _byscen = defaultdict(list)
        for r in rs:
            if r.get("det_score") is not None:
                _byscen[r.get("scenario")].append(r["det_score"])
        _cons = []
        for _ds in _byscen.values():
            _p = [d >= 0.5 for d in _ds]
            _maj = sum(_p) >= len(_p) / 2
            _cons.append(sum(1 for x in _p if x == _maj) / len(_p))
        pass_consistency = round(statistics.mean(_cons), 3) if _cons else None
        _eg = [r.get("net.total_kb") for r in rs if isinstance(r.get("net.total_kb"), (int, float))]
        net_egress_kb = round(statistics.mean(_eg), 2) if _eg else None  # ~0 proves offline
        _thr = [r["gen_ai.thinking.chars"] / r["gen_ai.usage.output_chars"]
                for r in rs if r.get("gen_ai.thinking.chars") and r.get("gen_ai.usage.output_chars")]
        thinking_ratio = round(statistics.mean(_thr), 3) if _thr else None
        table.append({
            "model": model, "bracket": bracket,
            "det_mean": det_mean, "det_ci": det_ci,
            "judge_mean": judge_mean, "judge_pct": judge_pct,
            "det_closedbook": cb_mean, "det_grounded": gr_mean,
            "paired_lift": paired_lift, "cls_diff": cls_diff,
            "median_tok_s": med_dec, "mean_w": mean_w, "wh_task": wh_task,
            "net_wh": net_wh, "tok_per_w": tok_per_w, "warmup_s": warm,
            "peak_swap_mb": peak_swap, "dnf": dnf,
            "tpot_ms": round(statistics.median(tpots), 1) if tpots else None,
            "chars_s": round(statistics.median(chars_s), 1) if chars_s else None,
            "j_per_tok": round(statistics.mean(j_per_tok), 2) if j_per_tok else None,
            "wh_per_correct": wh_per_correct, "mbu": mbu,
            "ipc": ipc,
            "pass_consistency": pass_consistency,
            "net_egress_kb": net_egress_kb,
            "thinking_ratio": thinking_ratio,
            "peak_temp_c": peak_temp, "throttle": throttle,
            "bottleneck": classify_bottleneck(peak_swap, mbu, peak_temp, throttle),
            "verdict": verdict(det_mean, judge_pct, med_dec, dnf, safety_fail),
        })

    # sort: by judge_pct desc (None last), then det
    table.sort(key=lambda t: (t["judge_pct"] is None, -(t["judge_pct"] or 0),
                              -(t["det_mean"] or 0)))

    with open(args.out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()) if table else
                           ["model", "bracket", "det_mean", "judge_mean", "judge_pct",
                            "median_tok_s", "warmup_s", "peak_swap_mb", "dnf", "verdict"])
        w.writeheader(); w.writerows(table)

    lines = ["# Small-Model Reasoning Eval — Results", "",
             f"_{len(by_model)} models × {len({r['scenario'] for r in rows if 'scenario' in r})} scenarios. "
             "Ranked by % of frontier (judge/5). See PLAN.md for method._", "",
             "| Model | Bracket | det | det 95%CI | judge/5 | % frontier | closed-book | grounded | paired RAG lift | tok/s | mean W | Wh/task | net Wh/task | tok/s/W | warmup | peak swap MB | DNF | Verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in table:
        lines.append("| {model} | {bracket} | {det_mean} | {det_ci} | {judge_mean} | "
                     "{judge_pct} | {det_closedbook} | {det_grounded} | {paired_lift} | "
                     "{median_tok_s} | {mean_w} | {wh_task} | {net_wh} | {tok_per_w} | {warmup_s} | "
                     "{peak_swap_mb} | {dnf} | {verdict} |".format(**t))
    lines += ["", "## Notes", "",
              "- **det** = mean deterministic-check pass rate (0-1). For the "
              "`capacity`/`foresee` classes the det checks measure answer **shape** "
              "(mentions a rate/timeframe/proactive action), not numeric correctness — "
              "the judge carries correctness there.",
              "- **det 95%CI** = bootstrap CI of the mean (normal-approx if numpy absent).",
              "- **% frontier** = judge score / 5 (frontier reference = the configured judge; "
              "default `copilot:claude-opus-4.8` — see `judge.py --backend`).",
              "- **paired RAG lift** = within-pair grounded−closed-book det on the SAME task "
              "(doc on/off); the clean RAG estimate. The bare closed-book/grounded columns are "
              "whole-class means and are **confounded** by task difficulty — do not read them as a "
              "retrieval effect.",
              "- **DNF** = timeout/stall/oom/loop count (breakglass watchdog).",
              "- **mean W / Wh/task / net Wh/task / tok/s/W** = MEASURED energy per task. "
              "Primary source is Intel RAPL on-die joule counters (`psys` SoC energy); a smart "
              "plug (Home Assistant / IKEA DIRIGERA) is an optional wall-power alternative. "
              "`power.source` in results.jsonl records which. `Wh/task` is gross; `net Wh/task` "
              "subtracts the measured idle baseline; `tok/s/W` is the real efficiency frontier "
              "(replaces the old tok×acc watt-proxy). RAPL `psys` excludes display/PSU — compute "
              "energy, not facility power.",
              "- The `guard` safety gate is **judge-primary** (majority of unsafe reps → REJECT); "
              "the `must_not_endorse` check is the sound fallback when the judge hasn't run.",
              "- Telemetry per request (TTFT, prefill/decode tok/s, RAM/swap series, progress "
              "trace) is in results.jsonl, OTel gen_ai.* **schema-aligned** (local JSONL; no "
              "exporter wired)."]

    # ---- Per-taxonomy breakdown: model x class matrix (det mean) ----------
    classes = sorted({r["class"] for r in rows if r.get("class")})
    lines += ["", "## Per-task-taxonomy scores (det mean, by class)", "",
              "Each cell = mean deterministic score for that model on that task class. "
              "Read columns to see which *task types* small models handle vs fail.", "",
              "| Model | Bracket | " + " | ".join(classes) + " |",
              "|---|---|" + "|".join(["---"] * len(classes)) + "|"]
    for t in table:
        rs = by_model[t["model"]]
        cells = []
        for c in classes:
            cd = [r["det_score"] for r in rs
                  if r.get("class") == c and r.get("det_score") is not None]
            cells.append(str(round(statistics.mean(cd), 2)) if cd else "-")
        lines.append(f"| {t['model']} | {t['bracket']} | " + " | ".join(cells) + " |")

    # ---- Per-class summary across ALL models (which task types are hard?) --
    lines += ["", "### Task-class difficulty (mean det across all real models, baselines excluded)", "",
              "| Class | aiopslab_task | mean det | n models | hardest? |",
              "|---|---|---|---|---|"]
    task_map = {r["class"]: r.get("aiopslab_task", "") for r in rows if r.get("class")}
    class_means = []
    for c in classes:
        cd = [r["det_score"] for r in rows
              if r.get("class") == c and r.get("det_score") is not None
              and not str(r.get("model", "")).startswith("baseline")]
        if cd:
            class_means.append((c, round(statistics.mean(cd), 3), len({r["model"] for r in rows if r.get("class") == c})))
    worst = min((m for _, m, _ in class_means), default=None)
    for c, m, n in sorted(class_means, key=lambda x: x[1]):
        flag = "  <-- hardest" if m == worst else ""
        lines.append(f"| {c} | {task_map.get(c,'')} | {m} | {n} | {flag} |")

    # ---- Paired RAG lift (clean within-pair estimate) ---------------------
    pairs = sorted({r.get("pair_id") for r in rows if r.get("pair_id")})
    if pairs:
        lines += ["", "### Paired RAG lift (within-pair grounded − closed-book det)", "",
                  "Same task with the reference doc present vs withheld — isolates retrieval "
                  "(unlike the confounded whole-class columns above).", "",
                  "| Model | " + " | ".join(pairs) + " | mean lift |", "|---|" + "|".join(["---"] * (len(pairs) + 1)) + "|"]
        for t in table:
            rs = by_model[t["model"]]
            cells = []
            for pid in pairs:
                gr = [r["det_score"] for r in rs if r.get("pair_id") == pid
                      and r.get("grounding") == "grounded" and r.get("det_score") is not None]
                cb = [r["det_score"] for r in rs if r.get("pair_id") == pid
                      and r.get("grounding") == "closed-book" and r.get("det_score") is not None]
                cells.append(str(round(statistics.mean(gr) - statistics.mean(cb), 2))
                             if gr and cb else "-")
            lines.append(f"| {t['model']} | " + " | ".join(cells) + f" | {t['paired_lift']} |")

    # ---- Systems & efficiency (derived) -----------------------------------
    lines += ["", "## Systems & efficiency (derived)", "",
              "Per-token latency and energy, normalized so cross-tokenizer comparison stays "
              "honest: **chars/s** sits next to tok/s because tok/s is **not** comparable across "
              "tokenizers (~20% spread, PAPER §4). **TPOT** = inter-token latency (ms/token). "
              "**J/token** and **Wh/correct** are the energy frontier. **MBU** = mean achieved ÷ "
              "measured-peak DRAM bandwidth (`calibrate.py`); **IPC** = instructions/cycle (low + "
              "high LLC-miss = stalled, memory-bound); **bottleneck** is the telemetry "
              "fingerprint verdict (capacity/thermal/bandwidth/compute).", "",
              "| Model | tok/s | TPOT ms | chars/s | J/token | Wh/correct | MBU | IPC | peak °C | throttle | bottleneck |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in table:
        lines.append("| {model} | {median_tok_s} | {tpot_ms} | {chars_s} | {j_per_tok} | "
                     "{wh_per_correct} | {mbu} | {ipc} | {peak_temp_c} | {throttle} | {bottleneck} |".format(**t))
    if not cal_peak_bw:
        lines.append("")
        lines.append("> **MBU/bottleneck are blank until `calibrate.py` has run on a quiet node** "
                     "(`--calibration calibration.json`) and `PERF_MEMBW=1` captured per-task "
                     "bandwidth. Roofline needs the *measured* peak, not the datasheet.")

    # ---- Accuracy by difficulty -------------------------------------------
    diff_order = ["easy", "medium", "hard"]
    present = [d for d in diff_order if any(r.get("difficulty") == d for r in rows)]
    if present:
        lines += ["", "## Accuracy by difficulty (det mean)", "",
                  "Difficulty is author-assigned per scenario (scenarios.json). A model that holds "
                  "up on `hard` is reasoning, not pattern-matching the easy tail.", "",
                  "| Model | Bracket | " + " | ".join(present) + " |",
                  "|---|---|" + "|".join(["---"] * len(present)) + "|"]
        for t in table:
            rs = by_model[t["model"]]
            cells = []
            for d in present:
                dd = [r["det_score"] for r in rs if r.get("difficulty") == d
                      and r.get("det_score") is not None]
                cells.append(str(round(statistics.mean(dd), 2)) if dd else "-")
            lines.append(f"| {t['model']} | {t['bracket']} | " + " | ".join(cells) + " |")
        srow = []
        for d in present:
            dd = [r["det_score"] for r in rows if r.get("difficulty") == d
                  and r.get("det_score") is not None
                  and not str(r.get("model", "")).startswith("baseline")]
            srow.append(str(round(statistics.mean(dd), 3)) if dd else "-")
        lines += ["", "Mean across all real models (baselines excluded): "
                  + "  ·  ".join(f"**{d}** {v}" for d, v in zip(present, srow)) + "."]

    # ---- Model architecture (static, from Ollama /api/show) ----
    arch = {}
    for r in rows:
        m = r.get("model")
        if m and m not in arch and r.get("ollama.parameter_count"):
            arch[m] = r
    if arch:
        lines += ["", "## Model architecture (Ollama /api/show)", "",
                  "Exact params, **MoE sparsity** (active/total experts = how many 'nodes' fire "
                  "per token), GQA heads (query/KV = KV-cache compression), and depth. A MoE like "
                  "`granite4:tiny-h` (6/64) computes like a ~1B dense model but needs the full "
                  "footprint in RAM — decoupling size from speed.", "",
                  "| Model | params | quant | experts active/total | heads q/kv | layers |",
                  "|---|---|---|---|---|---|"]
        for m in sorted(arch):
            r = arch[m]
            ec, eu = r.get("ollama.expert_count") or 0, r.get("ollama.expert_used_count") or 0
            moe = f"{eu}/{ec}" if ec else "dense"
            hc, hk = r.get("ollama.head_count"), r.get("ollama.head_count_kv")
            gqa = f"{hc}/{hk}" if (hc and hk) else (str(hc) if hc else "-")
            lines.append(f"| {m} | {r.get('ollama.parameter_size') or r.get('ollama.parameter_count')} "
                         f"| {r.get('ollama.quantization')} | {moe} | {gqa} | {r.get('ollama.block_count')} |")

    # ---- Memory dynamics & iGPU (RAM/swap variation; CPU-only confirmation) ----
    if any(r.get("mem.rss_start_mb") is not None or r.get("gpu.peak_freq_mhz") for r in rows):
        def _meanf(rs, key):
            vs = [r[key] for r in rs if r.get(key) is not None]
            return round(statistics.mean(vs)) if vs else None
        lines += ["", "## Memory dynamics & iGPU", "",
                  "RSS/swap **start→peak** show how each model's footprint grows under load "
                  "(weights load `--no-mmap`, so RSS ≈ real model memory). **iGPU MHz** near the "
                  "~300 MHz idle floor and **iGPU mem %** (GT share of memory requests) near 0 "
                  "confirm inference is **CPU-only** (no GPU offload). Dual- vs single-channel "
                  "flex-region attribution is not OS-exposed (PAPER §6).", "",
                  "| Model | RSS start→peak MB | swap start→peak MB | avail min MB | iGPU MHz peak | iGPU mem % |",
                  "|---|---|---|---|---|---|"]
        for t in table:
            rs = by_model[t["model"]]
            rss0, rss1 = _meanf(rs, "mem.rss_start_mb"), _meanf(rs, "mem.peak_rss_mb")
            sw0, sw1 = _meanf(rs, "swap.start_mb"), _meanf(rs, "peak_swap_mb")
            availmin = min([r["min_mem_avail_mb"] for r in rs if r.get("min_mem_avail_mb") is not None], default=None)
            gpu = max([r["gpu.peak_freq_mhz"] for r in rs if r.get("gpu.peak_freq_mhz")], default=None)
            req = [r["membw.requests"] for r in rs if r.get("membw.requests")]
            ia = sum(x.get("ia_requests", 0) for x in req)
            gt = sum(x.get("gt_requests", 0) for x in req)
            io = sum(x.get("io_requests", 0) for x in req)
            gtpct = round(100 * gt / (ia + gt + io), 2) if (ia + gt + io) else None
            lines.append(f"| {t['model']} | {rss0}→{rss1} | {sw0}→{sw1} | {availmin} | {gpu} | {gtpct} |")

    lines += stats_section(rows, judged)
    lines += judge_cost_section(judged)

    open(args.out_md, "w").write("\n".join(lines) + "\n")
    print(f"wrote {args.out_md} and {args.out_csv} ({len(table)} models)")


if __name__ == "__main__":
    main()
