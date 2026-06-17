#!/usr/bin/env python3
"""
dataset.py — flatten results.jsonl (+ judged.jsonl) into an ML-READY table
(one row per model×scenario×rep) of FEATURES + LABELS, so the rich telemetry can
feed sklearn / Kaggle-style modelling. See PAPER.md §4b for the task framing and
the comparison to public hardware datasets (Backblaze SMART, Google Borg power,
Alibaba AMTrace, MLPerf Power) — none of which pair systems telemetry with a
task-quality label, which is what makes *quality-from-behaviour* possible here.

    python3 dataset.py --results results.jsonl --judged judged.jsonl --out dataset.csv

Columns:
  identity : model, bracket, params, quant, native_ctx, scenario, class, grounding, difficulty, rep
  features : warmup_s, load_s, ttft_s, decode_tok_s, tpot_ms, output_tokens/chars,
             jitter p50/p95/max, peak_temp_c, start_temp_c, peak_rss_mb,
             rss_growth_mb, swap_delta_mb, min_avail_mb, mean_w, energy_wh,
             membw_peak_mb_s, gpu_peak_mhz, igpu_mem_pct, cpu_pct, mem_req_total
  labels   : det_score, judge_score, dnf (0/1), dnf_type

Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict


def load(p):
    try:
        return [json.loads(line) for line in open(p) if line.strip()]
    except FileNotFoundError:
        return []


def _igpu(req):
    """(GT share of memory requests %, total requests) from the requestor split."""
    if not req:
        return (None, None)
    ia, gt, io = req.get("ia_requests", 0), req.get("gt_requests", 0), req.get("io_requests", 0)
    tot = ia + gt + io
    return (round(100 * gt / tot, 3) if tot else None, tot or None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--judged", default="judged.jsonl")
    ap.add_argument("--out", default="dataset.csv")
    args = ap.parse_args()

    jm = defaultdict(list)  # (model, scenario, rep) -> [judge scores]
    for j in load(args.judged):
        if j.get("score") is not None:
            jm[(j.get("model"), j.get("scenario"), j.get("rep"))].append(j["score"])

    out = []
    for r in load(args.results):
        if "scenario" not in r:
            continue
        dec = r.get("decode_tok_s")
        rss0, rss1 = r.get("mem.rss_start_mb"), r.get("mem.peak_rss_mb")
        sw0, sw1 = r.get("swap.start_mb"), r.get("peak_swap_mb")
        igpu_pct, mem_req_total = _igpu(r.get("membw.requests"))
        pc = r.get("perf.core") or {}
        finish = (r.get("gen_ai.response.finish_reasons") or [None])[0]
        js = jm.get((r.get("model"), r.get("scenario"), r.get("rep")))
        out.append({
            "model": r.get("model"), "bracket": r.get("bracket"),
            "scenario": r.get("scenario"), "class": r.get("class"),
            "grounding": r.get("grounding"), "difficulty": r.get("difficulty"),
            "rep": r.get("rep"),
            # --- model metadata (Ollama /api/show, /api/ps) ---
            "params": r.get("ollama.parameter_count"),
            "quant": r.get("ollama.quantization"),
            "native_ctx": r.get("ollama.context_length"),
            "layers": r.get("ollama.block_count"),
            "heads": r.get("ollama.head_count"),
            "kv_heads": r.get("ollama.head_count_kv"),
            "experts": r.get("ollama.expert_count"),
            "active_experts": r.get("ollama.expert_used_count"),
            "is_moe": 1 if (r.get("ollama.expert_count") or 0) else 0,
            "size_vram_bytes": r.get("ollama.size_vram_bytes"),
            "cpu_pct": r.get("ollama.cpu_pct"),
            # --- behavioural features ---
            "warmup_s": r.get("warmup_s"),
            "load_s": r.get("ollama.load_duration_s"),
            "ttft_s": r.get("gen_ai.server.time_to_first_token_s"),
            "decode_tok_s": dec,
            "tpot_ms": round(1000 / dec, 1) if dec else None,
            "output_tokens": r.get("gen_ai.usage.output_tokens"),
            "output_chars": r.get("gen_ai.usage.output_chars"),
            "dt_p50_ms": r.get("decode.dt_p50_ms"),
            "dt_p95_ms": r.get("decode.dt_p95_ms"),
            "dt_max_ms": r.get("decode.dt_max_ms"),
            "peak_temp_c": r.get("thermal.peak_c"),
            "start_temp_c": r.get("thermal.start_c"),
            "peak_rss_mb": rss1,
            "rss_growth_mb": (rss1 - rss0) if (rss1 is not None and rss0 is not None) else None,
            "swap_delta_mb": (sw1 - sw0) if (sw1 is not None and sw0 is not None) else None,
            "min_avail_mb": r.get("min_mem_avail_mb"),
            "mean_w": r.get("power.mean_watts"),
            "energy_wh": r.get("power.energy_wh"),
            "membw_peak_mb_s": r.get("membw.peak_mb_s"),
            "gpu_peak_mhz": r.get("gpu.peak_freq_mhz"),
            "igpu_mem_pct": igpu_pct,
            "mem_req_total": mem_req_total,
            "ipc": pc.get("ipc"),
            "cache_misses": pc.get("cache_misses"),
            "llc_load_misses": pc.get("llc_load_misses"),
            "branch_misses": pc.get("branch_misses"),
            "minflt": r.get("proc.minflt"),
            "ctxt_switches": r.get("proc.ctxt_switches"),
            # --- labels ---
            "det_score": r.get("det_score"),
            "judge_score": round(statistics.mean(js), 3) if js else None,
            "dnf": 1 if r.get("dnf") else 0,
            "dnf_type": finish if (finish and str(finish).startswith("DNF")) else "",
        })

    cols = list(out[0].keys()) if out else []
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"wrote {args.out}: {len(out)} task-rows x {len(cols)} cols "
          f"({sum(o['dnf'] for o in out)} DNF, "
          f"{sum(1 for o in out if o['judge_score'] is not None)} judged)")


if __name__ == "__main__":
    main()
