#!/usr/bin/env python3
"""metrics.py — derived analysis metrics for ApprenticeOps result files.

Computes everything that does NOT need a re-run, straight from results.*.jsonl[.gz]
(+ optional calibration.json for the MBU peak, + optional outputs/ dir for the
text metrics). Emits a per-run enriched file and a per-model summary CSV.

Per-run (numeric, from the row):
  - tpot_ms            time per output token (= 1000 / decode_tok_s)
  - achieved_bw_gb_s   weights streamed per second (size_bytes * decode_tok_s)
  - mbu                achieved_bw / peak_bw  (the memory-bound roofline metric)
  - flops_per_token    ~2 * parameter_count (dense compute reference)
  - kv_cache_mb        2*K/V*fp16 * block * head_kv * (embed/head) * (in+out tok)
  - energy_per_ktok_wh energy per 1000 output tokens
  - energy_per_correct energy_wh / det_score  (deployment-honest cost)
  - thinking_ratio     thinking_chars / output_chars  (reasoning overhead)

Per (model, scenario) across reps:
  - det_mean, det_std, pass_consistency (fraction matching the majority pass/fail)
  - tokenizer_bloat    input_tokens / (min input_tokens for that scenario)
  - [if outputs/ given] hedge_rate, refusal_rate, repetition, parseable_rate

    python3 scripts/metrics.py data/raw/results.var.jsonl.gz [more ...] \
        [--calibration calibration.json] [--peak-bw-mb-s 30000] [--outputs outputs] \
        [--out results.metrics.jsonl] [--summary metrics-by-model.csv]
"""
import argparse
import csv
import glob
import gzip
import json
import math
import os
import re
import statistics as st
from collections import defaultdict

# --- text-metric lexicons (scenario-agnostic) ------------------------------
HEDGE = re.compile(r"\b(i('?m| am) not sure|i (don'?t|do not) (know|have)|"
                   r"insufficient (information|context|data)|cannot determine|"
                   r"unable to (determine|tell)|not enough (information|context)|"
                   r"it'?s unclear|hard to say|i can'?t be certain)\b", re.I)
REFUSAL = re.compile(r"\b(i (cannot|can'?t|won'?t|will not)|i'?m (unable|not able)|"
                     r"as an ai|i must decline|i refuse|cannot assist|cannot help with)\b", re.I)
CODEFENCE = re.compile(r"```")


def _open(p):
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def load(paths):
    rows = []
    for p in paths:
        with _open(p) as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    r = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if r.get("model") and not r.get("fatal"):
                    rows.append(r)
    return rows


def find_peak_bw(rows, calibration, override):
    if override:
        return float(override), "override"
    if calibration and os.path.exists(calibration):
        try:
            c = json.load(open(calibration))
            for k in ("peak_membw_mb_s", "peak_dram_mb_s", "dram_bw_mb_s", "membw_peak_mb_s",
                      "peak_mb_s", "memory_bandwidth_mb_s"):
                if isinstance(c.get(k), (int, float)) and c[k] > 0:
                    return float(c[k]), f"calibration.{k}"
        except Exception:  # noqa: BLE001
            pass
    obs = [r.get("membw.peak_mb_s") for r in rows if isinstance(r.get("membw.peak_mb_s"), (int, float))]
    if obs:
        return max(obs), "observed-max (no calibration.json — approximate)"
    return None, "unavailable"


def num(r, k):
    v = r.get(k)
    return v if isinstance(v, (int, float)) else None


def per_run(r, peak_mb_s):
    out = {}
    dts = num(r, "decode_tok_s")
    if dts and dts > 0:
        out["tpot_ms"] = round(1000.0 / dts, 2)
    size = num(r, "ollama.size_bytes")
    if size and dts:
        ach_mb_s = size / 1e6 * dts                       # bytes/token * tok/s -> MB/s
        out["achieved_bw_mb_s"] = round(ach_mb_s, 1)
        if peak_mb_s:
            # MBU = achieved / peak. NB: achieved assumes a DENSE model streams ALL
            # weights per token; for MoE/hybrid-SSM (e.g. granite4) far fewer bytes
            # move per token, so MBU > 1 is the EFFICIENCY SIGNATURE (sub-streaming),
            # not an error. Also needs the TRUE DRAM peak from calibration.json — the
            # observed-max fallback under-reads it, inflating MBU.
            out["mbu"] = round(min(ach_mb_s / peak_mb_s, 1.5), 4)
    pc = num(r, "ollama.parameter_count")
    if pc:
        out["flops_per_token"] = 2 * pc
    blk, hkv, emb, h = (num(r, "ollama.block_count"), num(r, "ollama.head_count_kv"),
                        num(r, "ollama.embedding_length"), num(r, "ollama.head_count"))
    it, ot = num(r, "gen_ai.usage.input_tokens"), num(r, "gen_ai.usage.output_tokens")
    if all(x for x in (blk, hkv, emb, h)) and (it is not None and ot is not None):
        head_dim = emb / h
        out["kv_cache_mb"] = round(2 * 2 * blk * hkv * head_dim * (it + ot) / 1e6, 2)
    e = num(r, "power.energy_wh")
    if e and ot:
        out["energy_per_ktok_wh"] = round(e / ot * 1000, 5)
    det = num(r, "det_score")
    if e is not None and det and det > 0:
        out["energy_per_correct_wh"] = round(e / det, 5)
    tc, oc = num(r, "gen_ai.thinking.chars"), num(r, "gen_ai.usage.output_chars")
    if tc is not None and oc:
        out["thinking_ratio"] = round(tc / oc, 3)
    return out


def text_metrics(text):
    if not text:
        return {}
    toks = text.split()
    grams = [" ".join(toks[i:i + 3]) for i in range(len(toks) - 2)]
    rep = round(1 - len(set(grams)) / len(grams), 3) if grams else 0.0
    return {
        "hedge": bool(HEDGE.search(text)),
        "refusal": bool(REFUSAL.search(text)),
        "repetition_3gram": rep,
        "has_code_block": bool(CODEFENCE.search(text)),
    }


def read_output(outputs_dir, model, scenario, rep, repeats):
    base = model.replace("/", "_").replace(":", "_")
    for name in ([f"{base}__{scenario}__r{rep}.txt"] if repeats and repeats > 1 else []) + \
                [f"{base}__{scenario}.txt"]:
        p = os.path.join(outputs_dir, name)
        if os.path.exists(p):
            try:
                return open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="+")
    ap.add_argument("--calibration", default="calibration.json")
    ap.add_argument("--peak-bw-mb-s", default=None)
    ap.add_argument("--outputs", default=None, help="outputs/ dir for text metrics (optional)")
    ap.add_argument("--out", default="results.metrics.jsonl")
    ap.add_argument("--summary", default="metrics-by-model.csv")
    args = ap.parse_args()

    paths = [p for g in args.results for p in (glob.glob(g) or [g])]
    rows = load(paths)
    if not rows:
        print("no rows"); return
    peak, peak_src = find_peak_bw(rows, args.calibration, args.peak_bw_mb_s)
    print(f"loaded {len(rows)} rows from {len(paths)} file(s); peak bandwidth = "
          f"{peak} MB/s ({peak_src})")

    # tokenizer bloat needs the per-scenario min input_tokens
    min_in = defaultdict(lambda: math.inf)
    for r in rows:
        it = num(r, "gen_ai.usage.input_tokens")
        if it:
            min_in[r.get("scenario")] = min(min_in[r.get("scenario")], it)

    enriched = []
    for r in rows:
        m = per_run(r, peak)
        it = num(r, "gen_ai.usage.input_tokens")
        sc = r.get("scenario")
        if it and min_in[sc] not in (0, math.inf):
            m["tokenizer_bloat"] = round(it / min_in[sc], 3)
        if args.outputs:
            txt = read_output(args.outputs, r.get("model"), sc, r.get("rep"),
                              # infer repeats from data: >1 if rep values exceed 0
                              2 if any(x.get("rep") for x in rows[:1]) or r.get("rep") else 1)
            m.update(text_metrics(txt))
        enriched.append({"model": r.get("model"), "scenario": sc, "rep": r.get("rep"),
                         "bracket": r.get("bracket"), **m})
    with open(args.out, "w") as fh:
        for e in enriched:
            fh.write(json.dumps(e) + "\n")

    # per (model, scenario): det stats + consistency
    grp = defaultdict(list)
    for r in rows:
        grp[(r.get("model"), r.get("scenario"))].append(r)
    consistency = {}
    for key, rs in grp.items():
        dets = [num(x, "det_score") for x in rs if num(x, "det_score") is not None]
        if not dets:
            continue
        passes = [d >= 0.5 for d in dets]
        maj = sum(passes) >= len(passes) / 2
        consistency[key] = {
            "det_mean": st.mean(dets),
            "det_std": st.pstdev(dets) if len(dets) > 1 else 0.0,
            "pass_consistency": sum(1 for p in passes if p == maj) / len(passes),
            "n": len(dets),
        }

    # per-model summary
    by_model = defaultdict(lambda: defaultdict(list))
    for e in enriched:
        for k in ("tpot_ms", "mbu", "energy_per_correct_wh", "energy_per_ktok_wh",
                  "thinking_ratio", "tokenizer_bloat"):
            if isinstance(e.get(k), (int, float)):
                by_model[e["model"]][k].append(e[k])
    cons_by_model = defaultdict(list)
    for (m, _s), c in consistency.items():
        cons_by_model[m].append(c["pass_consistency"])

    sumrows = []
    for m, d in sorted(by_model.items()):
        row = {"model": m, "n_runs": max((len(v) for v in d.values()), default=0)}
        for k, v in d.items():
            row[k + "_mean"] = round(st.mean(v), 4) if v else ""
        row["pass_consistency_mean"] = round(st.mean(cons_by_model[m]), 4) if cons_by_model[m] else ""
        sumrows.append(row)
    cols = ["model", "n_runs", "tpot_ms_mean", "mbu_mean", "energy_per_correct_wh_mean",
            "energy_per_ktok_wh_mean", "thinking_ratio_mean", "tokenizer_bloat_mean",
            "pass_consistency_mean"]
    with open(args.summary, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sumrows)

    print(f"wrote {args.out} ({len(enriched)} rows) + {args.summary} ({len(sumrows)} models)")
    mbus = [e["mbu"] for e in enriched if isinstance(e.get("mbu"), (int, float))]
    if mbus:
        print(f"  MBU: median {st.median(mbus):.3f}  range {min(mbus):.3f}-{max(mbus):.3f}")
    allc = [c["pass_consistency"] for c in consistency.values()]
    if allc:
        print(f"  pass-consistency (model,scenario): median {st.median(allc):.3f}  "
              f"share fully-stable (=1.0): {sum(1 for x in allc if x == 1.0) / len(allc) * 100:.0f}%")


if __name__ == "__main__":
    main()
