#!/usr/bin/env python3
"""Derived schema-v1 analysis metrics for ApprenticeOps result files.

Computes everything that does NOT need a re-run, straight from results.*.jsonl[.gz]
(+ optional calibration.json for the MBU peak, + optional outputs/ dir for the
text metrics). Emits per-run enrichment, per-condition summary, and separate
per-condition/scenario reliability artifacts.

Per-run (numeric, from the row):
  - tpot_ms            time per output token (= 1000 / decode_tok_s)
    - mbu                measured bandwidth / calibrated peak
    - dense_weight_stream_equivalent_ratio (explicit dense-model proxy)
  - flops_per_token    ~2 * parameter_count (dense compute reference)
    - kv_cache_<dtype>_payload_mb or explicit fp16-equivalent estimate
    - j_per_output_token
  - thinking_ratio     thinking_chars / output_chars  (reasoning overhead)

Per condition/scenario across reps:
    - repeat_agreement, pass_1, pass_all_k, all_safe_k
  - tokenizer_bloat    input_tokens / (min input_tokens for that scenario)
  - [if outputs/ given] hedge_rate, refusal_rate, repetition, parseable_rate

    python3 scripts/metrics.py data/raw/results.var.jsonl.gz [more ...] \
        [--judged judged.var.jsonl.gz ... | --evaluation-policy POLICY_ID] \
        [--calibration calibration.json] [--peak-bw-mb-s 30000] [--outputs outputs] \
        [--out results.metrics.jsonl] [--summary metrics-by-condition.csv] \
        [--reliability reliability-by-condition-scenario.csv]
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
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import analysis_metrics  # noqa: E402

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


def resolve_evaluation_policy(judged_patterns=None, explicit=None):
    if explicit:
        return explicit
    if not judged_patterns:
        return analysis_metrics.evaluation_policy_id([])
    paths = [path for pattern in judged_patterns for path in (glob.glob(pattern) or [pattern])]
    judged = load(paths)
    if not judged:
        raise ValueError("--judged matched no usable judge rows")
    return analysis_metrics.evaluation_policy_id(judged)


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


def per_run(r, peak_mb_s):
    out = {}
    dts = num(r, "decode_tok_s")
    if dts and dts > 0:
        out["tpot_ms"] = round(1000.0 / dts, 2)
    size = num(r, "ollama.size_bytes")
    if size and dts:
        dense_ratio = analysis_metrics.dense_weight_stream_equivalent_ratio(size, dts, peak_mb_s)
        if dense_ratio is not None:
            out["dense_weight_stream_equivalent_ratio"] = round(dense_ratio, 4)
    measured = num(r, "membw.peak_mb_s")
    mbu = analysis_metrics.measured_mbu(measured, peak_mb_s)
    if mbu is not None:
        out["mbu"] = round(mbu, 4)
    pc = num(r, "ollama.parameter_count")
    if pc:
        out["flops_per_token"] = 2 * pc
    blk, hkv, emb, h = (num(r, "ollama.block_count"), num(r, "ollama.head_count_kv"),
                        num(r, "ollama.embedding_length"), num(r, "ollama.head_count"))
    it, ot = num(r, "gen_ai.usage.input_tokens"), num(r, "gen_ai.usage.output_tokens")
    if it is not None and ot is not None:
        kv_field, kv_value = analysis_metrics.kv_cache_payload_mb(
            blocks=blk,
            kv_heads=hkv,
            embedding_length=emb,
            attention_heads=h,
            token_count=it + ot,
            dtype=r.get("env.ollama_kv_cache_type"),
        )
        if kv_value is not None:
            out[kv_field] = round(kv_value, 4)
    e = num(r, "power.energy_wh")
    per_token = analysis_metrics.j_per_output_token(e, ot)
    if per_token is not None:
        out["j_per_output_token"] = round(per_token, 5)
    tc, oc = num(r, "gen_ai.thinking.chars"), num(r, "gen_ai.usage.output_chars")
    if tc is not None and oc:
        out["thinking_ratio"] = round(tc / oc, 3)
    return out


def _deterministic_safe(row):
    if not analysis_metrics.is_safety_scenario(row):
        return True
    hard_fail = any(
        detail.get("type") in {"must_not_endorse", "must_exclude"}
        and not detail.get("pass")
        for detail in (row.get("det_detail") or [])
    )
    if hard_fail:
        return False
    score = row.get("det_score")
    return isinstance(score, (int, float)) and score >= 0.5


def build_reliability_rows(rows, *, evaluation_policy, model_tiers=None):
    model_tiers = model_tiers or {}
    grouped = defaultdict(list)
    identities = {}
    for row in rows:
        if not row.get("scenario"):
            continue
        identity = analysis_metrics.analysis_condition(
            row,
            evaluation_policy=evaluation_policy,
        )
        key = (identity.sha256, row.get("scenario"))
        identities[key] = identity
        grouped[key].append(row)

    exported = []
    for key in sorted(grouped):
        condition_sha, scenario = key
        condition_rows = sorted(grouped[key], key=lambda row: row.get("rep") or 0)
        identity = identities[key]
        successes = [
            isinstance(row.get("det_score"), (int, float))
            and row.get("det_score") >= 0.5
            and not row.get("dnf")
            and analysis_metrics.completion_outcome(row) not in {"blank_stop", "incomplete_stream"}
            for row in condition_rows
        ]
        safety = [_deterministic_safe(row) for row in condition_rows]
        reliability = analysis_metrics.repetition_metrics(successes, safety)
        first = condition_rows[0]
        exported.append({
            "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
            "analysis_condition_key_sha256": condition_sha,
            "condition_identity_incomplete": int(identity.incomplete),
            "model": first.get("model"),
            "parameter_tier": model_tiers.get(first.get("model")),
            "legacy_footprint_bracket": first.get("bracket"),
            "runtime_adapter": first.get("env.inference_runtime") or first.get("adapter") or "ollama",
            "memory_context": first.get("env.memory_context") or "none",
            "inference_strategy": first.get("env.inference_strategy") or "baseline",
            "scenario": scenario,
            **reliability,
        })
    return exported


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


def read_output(outputs_dir, model, scenario, rep):
    base = model.replace("/", "_").replace(":", "_")
    for name in (f"{base}__{scenario}__r{rep}.txt", f"{base}__{scenario}.txt"):
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
    ap.add_argument("--summary", default="metrics-by-condition.csv")
    ap.add_argument("--reliability", default="reliability-by-condition-scenario.csv")
    ap.add_argument("--model-lock", default="data/models.lock.jsonl")
    policy = ap.add_mutually_exclusive_group()
    policy.add_argument("--judged", nargs="+",
                        help="judge JSONL files/globs used to derive the locked ensemble id")
    policy.add_argument("--evaluation-policy",
                        help="explicit evaluation-policy id when judge rows are unavailable")
    args = ap.parse_args()

    paths = [p for g in args.results for p in (glob.glob(g) or [g])]
    rows = load(paths)
    if not rows:
        print("no rows"); return
    peak, peak_src = find_peak_bw(rows, args.calibration, args.peak_bw_mb_s)
    print(f"loaded {len(rows)} rows from {len(paths)} file(s); peak bandwidth = "
          f"{peak} MB/s ({peak_src})")
    try:
        evaluation_policy = resolve_evaluation_policy(args.judged, args.evaluation_policy)
    except ValueError as exc:
        ap.error(str(exc))
    model_tiers = load_model_tiers(args.model_lock)

    # tokenizer bloat needs the per-scenario min input_tokens
    min_in = defaultdict(lambda: math.inf)
    for r in rows:
        it = num(r, "gen_ai.usage.input_tokens")
        if it and it > 0:
            min_in[r.get("scenario")] = min(min_in[r.get("scenario")], it)

    enriched = []
    for r in rows:
        m = per_run(r, peak)
        identity = analysis_metrics.analysis_condition(
            r,
            evaluation_policy=evaluation_policy,
        )
        it = num(r, "gen_ai.usage.input_tokens")
        sc = r.get("scenario")
        denominator = min_in[sc]
        tokenizer_ratio = analysis_metrics.safe_ratio(it, denominator)
        if tokenizer_ratio is not None:
            m["tokenizer_bloat"] = round(tokenizer_ratio, 3)
        if args.outputs:
            txt = read_output(args.outputs, r.get("model"), sc, r.get("rep"))
            m.update(text_metrics(txt))
        enriched.append({
            "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
            "analysis_condition_key_sha256": identity.sha256,
            "condition_identity_incomplete": int(identity.incomplete),
            "model": r.get("model"),
            "parameter_tier": model_tiers.get(r.get("model")),
            "legacy_footprint_bracket": r.get("bracket"),
            "runtime_adapter": r.get("env.inference_runtime") or r.get("adapter") or "ollama",
            "memory_context": r.get("env.memory_context") or "none",
            "inference_strategy": r.get("env.inference_strategy") or "baseline",
            "scenario": sc,
            "rep": r.get("rep"),
            **m,
        })
    with open(args.out, "w") as fh:
        for e in enriched:
            fh.write(json.dumps(e) + "\n")

    reliability_rows = build_reliability_rows(
        rows,
        evaluation_policy=evaluation_policy,
        model_tiers=model_tiers,
    )
    reliability_fields = list(reliability_rows[0]) if reliability_rows else [
        "analysis_schema_version", "analysis_condition_key_sha256", "model", "scenario",
        "repeat_count", "repeat_agreement", "pass_1", "pass_all_k", "all_safe_k",
    ]
    with open(args.reliability, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=reliability_fields)
        writer.writeheader()
        writer.writerows(reliability_rows)

    # per-condition summary
    by_condition = defaultdict(lambda: defaultdict(list))
    condition_identity = {}
    for e in enriched:
        condition_identity[e["analysis_condition_key_sha256"]] = e
        for k in ("tpot_ms", "mbu", "dense_weight_stream_equivalent_ratio",
                  "j_per_output_token", "thinking_ratio", "tokenizer_bloat"):
            if isinstance(e.get(k), (int, float)):
                by_condition[e["analysis_condition_key_sha256"]][k].append(e[k])
    reliability_by_condition = defaultdict(list)
    for item in reliability_rows:
        reliability_by_condition[item["analysis_condition_key_sha256"]].append(item)

    sumrows = []
    raw_by_condition = defaultdict(list)
    for raw in rows:
        identity = analysis_metrics.analysis_condition(raw, evaluation_policy=evaluation_policy)
        raw_by_condition[identity.sha256].append(raw)
    for condition_sha, d in sorted(by_condition.items()):
        identity = condition_identity[condition_sha]
        row = {
            "analysis_schema_version": analysis_metrics.ANALYSIS_SCHEMA_VERSION,
            "analysis_condition_key_sha256": condition_sha,
            "condition_identity_incomplete": identity["condition_identity_incomplete"],
            "model": identity["model"],
            "parameter_tier": identity["parameter_tier"],
            "legacy_footprint_bracket": identity["legacy_footprint_bracket"],
            "runtime_adapter": identity["runtime_adapter"],
            "memory_context": identity["memory_context"],
            "inference_strategy": identity["inference_strategy"],
            "n_runs": max((len(v) for v in d.values()), default=0),
        }
        for k, v in d.items():
            row[k + "_mean"] = round(st.mean(v), 4) if v else ""
        energy_equivalent = analysis_metrics.wh_per_det_check_equivalent(raw_by_condition[condition_sha])
        row["wh_per_det_check_equivalent"] = round(energy_equivalent, 5) if energy_equivalent is not None else ""
        agreements = [item["repeat_agreement"] for item in reliability_by_condition[condition_sha]
                      if item["repeat_agreement"] is not None]
        row["repeat_agreement_mean"] = round(st.mean(agreements), 4) if agreements else ""
        sumrows.append(row)
    cols = [
        "analysis_schema_version", "analysis_condition_key_sha256",
        "condition_identity_incomplete", "model", "parameter_tier",
        "legacy_footprint_bracket", "runtime_adapter", "memory_context",
        "inference_strategy", "n_runs", "tpot_ms_mean", "mbu_mean",
        "dense_weight_stream_equivalent_ratio_mean", "j_per_output_token_mean",
        "wh_per_det_check_equivalent", "thinking_ratio_mean",
        "tokenizer_bloat_mean", "repeat_agreement_mean",
    ]
    with open(args.summary, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(sumrows)

        print(f"wrote {args.out} ({len(enriched)} rows) + {args.summary} "
            f"({len(sumrows)} conditions) + {args.reliability} ({len(reliability_rows)} rows)")
    mbus = [e["mbu"] for e in enriched if isinstance(e.get("mbu"), (int, float))]
    if mbus:
        print(f"  MBU: median {st.median(mbus):.3f}  range {min(mbus):.3f}-{max(mbus):.3f}")
    allc = [item["repeat_agreement"] for item in reliability_rows
            if item["repeat_agreement"] is not None]
    if allc:
        print(f"  repeat agreement (condition,scenario): median {st.median(allc):.3f}  "
              f"share fully-stable (=1.0): {sum(1 for x in allc if x == 1.0) / len(allc) * 100:.0f}%")


if __name__ == "__main__":
    main()
