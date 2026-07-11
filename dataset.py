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
    identity : model, bracket, memory_context, params, quant, native_ctx, scenario, class, grounding, difficulty, rep
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

import analysis_metrics


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


def load_model_tiers(path):
    tiers = {}
    if not path:
        return tiers
    try:
        with open(path) as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    tiers[row.get("model_id")] = row.get("tier")
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return tiers


def build_dataset_rows(
    results,
    judged,
    *,
    model_tiers=None,
    allow_legacy_judge_join=False,
    evaluation_policy=None,
):
    model_tiers = model_tiers or {}
    evaluation_policy = analysis_metrics.resolve_evaluation_policy(
        judged,
        explicit=evaluation_policy,
        allow_legacy=allow_legacy_judge_join,
    )
    result_identities = {
        id(row): analysis_metrics.analysis_condition(
            row,
            evaluation_policy=evaluation_policy,
        )
        for row in results
        if "scenario" in row
    }
    condition_rows = [
        (result_identities[id(row)], row)
        for row in results
        if id(row) in result_identities
    ]
    exact_conditions, legacy_conditions = analysis_metrics.judge_condition_index(condition_rows)
    expected_judges = analysis_metrics.evaluation_policy_judges(evaluation_policy)
    per_item = defaultdict(dict)
    for row in judged:
        if row.get("score") is not None:
            condition_sha = analysis_metrics.resolve_judge_condition(
                row,
                exact_conditions=exact_conditions,
                legacy_conditions=legacy_conditions,
                allow_legacy=allow_legacy_judge_join,
            )
            if condition_sha is not None:
                item_key = (condition_sha, row.get("scenario"), row.get("rep"))
                judge = analysis_metrics.judge_identity(row)
                if expected_judges and judge not in expected_judges:
                    raise ValueError(f"undeclared judge identity: {judge[0]}:{judge[1]}")
                if judge in per_item[item_key]:
                    raise ValueError(
                        "duplicate judgement for one condition/scenario/repetition: "
                        f"{judge[0]}:{judge[1]}"
                    )
                per_item[item_key][judge] = row["score"]

    jm = {
        key: list(scores.values())
        for key, scores in per_item.items()
        if frozenset(scores) == expected_judges
    }

    out = []
    for row in results:
        if "scenario" not in row:
            continue
        identity = result_identities[id(row)]
        decode_rate = row.get("decode_tok_s")
        rss_start, rss_peak = row.get("mem.rss_start_mb"), row.get("mem.peak_rss_mb")
        swap_start, swap_peak = row.get("swap.start_mb"), row.get("peak_swap_mb")
        igpu_pct, mem_req_total = _igpu(row.get("membw.requests"))
        perf = row.get("perf.core") or {}
        finish = analysis_metrics.finish_reason(row)
        memory_context = row.get("env.memory_context") or "none"
        inference_strategy = row.get("env.inference_strategy") or "baseline"
        adapter = row.get("env.inference_runtime") or row.get("adapter") or "ollama"
        scores = jm.get((identity.sha256, row.get("scenario"), row.get("rep")))
        out.append({
            "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
            "analysis_condition_key_sha256": identity.sha256,
            "condition_identity_incomplete": int(identity.incomplete),
            "model": row.get("model"),
            "parameter_tier": model_tiers.get(row.get("model")),
            "legacy_footprint_bracket": row.get("bracket"),
            "runtime_adapter": adapter,
            "memory_context": memory_context,
            "inference_strategy": inference_strategy,
            "scenario": row.get("scenario"),
            "class": row.get("class"),
            "grounding": row.get("grounding"),
            "difficulty": row.get("difficulty"),
            "rep": row.get("rep"),
            "parameter_count": row.get("ollama.parameter_count"),
            "quantization": row.get("ollama.quantization"),
            "native_context_tokens": row.get("ollama.context_length"),
            "block_count": row.get("ollama.block_count"),
            "attention_head_count": row.get("ollama.head_count"),
            "kv_head_count": row.get("ollama.head_count_kv"),
            "expert_count": row.get("ollama.expert_count"),
            "active_expert_count": row.get("ollama.expert_used_count"),
            "is_moe": 1 if (row.get("ollama.expert_count") or 0) else 0,
            "size_vram_bytes": row.get("ollama.size_vram_bytes"),
            "cpu_pct": row.get("ollama.cpu_pct"),
            "warmup_s": row.get("warmup_s"),
            "load_s": row.get("ollama.load_duration_s"),
            "ttft_s": row.get("gen_ai.server.time_to_first_token_s"),
            "decode_tokens_per_s": decode_rate,
            "tpot_ms": round(1000 / decode_rate, 1) if decode_rate else None,
            "output_tokens": row.get("gen_ai.usage.output_tokens"),
            "output_chars": row.get("gen_ai.usage.output_chars"),
            "inter_token_p50_ms": row.get("decode.dt_p50_ms"),
            "inter_token_p95_ms": row.get("decode.dt_p95_ms"),
            "inter_token_max_ms": row.get("decode.dt_max_ms"),
            "peak_temp_c": row.get("thermal.peak_c"),
            "start_temp_c": row.get("thermal.start_c"),
            "peak_rss_mb": rss_peak,
            "rss_growth_mb": (rss_peak - rss_start) if (rss_peak is not None and rss_start is not None) else None,
            "swap_delta_mb": (swap_peak - swap_start) if (swap_peak is not None and swap_start is not None) else None,
            "min_available_mb": row.get("min_mem_avail_mb"),
            "mean_power_w": row.get("power.mean_watts"),
            "energy_wh": row.get("power.energy_wh"),
            "membw_peak_mb_s": row.get("membw.peak_mb_s"),
            "gpu_peak_mhz": row.get("gpu.peak_freq_mhz"),
            "igpu_mem_pct": igpu_pct,
            "mem_request_count": mem_req_total,
            "ipc": perf.get("ipc"),
            "cache_misses": perf.get("cache_misses"),
            "llc_load_misses": perf.get("llc_load_misses"),
            "branch_misses": perf.get("branch_misses"),
            "minor_faults": row.get("proc.minflt"),
            "context_switches": row.get("proc.ctxt_switches"),
            "det_score": row.get("det_score"),
            "judge_score": round(statistics.mean(scores), 3) if scores else None,
            "completion_outcome": analysis_metrics.completion_outcome(row),
            "dnf": 1 if row.get("dnf") else 0,
            "dnf_type": finish if (finish and str(finish).startswith("DNF")) else "",
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--judged", default="judged.jsonl")
    ap.add_argument("--out", default="dataset.csv")
    ap.add_argument("--model-lock", default="data/models.lock.jsonl")
    ap.add_argument("--allow-legacy-judge-join", action="store_true",
                    help="explicitly allow unique hashless historical judge joins")
    ap.add_argument("--evaluation-policy",
                    help="required requested ensemble id for hashless legacy judge files")
    args = ap.parse_args()

    out = build_dataset_rows(
        load(args.results),
        load(args.judged),
        model_tiers=load_model_tiers(args.model_lock),
        allow_legacy_judge_join=args.allow_legacy_judge_join,
        evaluation_policy=args.evaluation_policy,
    )

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
