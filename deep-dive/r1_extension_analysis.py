"""R1-extension analysis — does the frozen reasoning-distill safety finding survive
into the CPU-sovereign (152) protocol?

The frozen 94-model corpus' headline safety result was that REASONING-DISTILLED models
refuse destructive actions far less than INSTRUCT models (instruct 75.0% vs
reasoning-distill 43.9% deterministic refusal). The 152-model run could not test it: the
4 DeepSeek-R1 distills + phi:2.7b were excluded by the chat-ok roster validation, so the
94->152 bridge (full_extend_bridge.py) replicated instruct-model safety but left the
*mechanism* untested.

This consumes the R1-extension run (`results.r1ext.jsonl` + `judged.r1ext.jsonl`,
5 models x 20 scenarios x 5 reps, measured under the EXACT 152 protocol -- same locked
power/RAPL regime, same scenarios sha, same 2-judge ensemble claude-opus-4.6 + gpt-5.4)
and compares those models against the 152's own instruct and reasoning populations.

Because the protocol is identical, these rows POOL with the 152 (unlike the frozen 94,
which differs in judges, scenarios and prompt format). phi:2.7b is excluded as a
serve-failure (100% DNF, HTTP 500) per FINDINGS 26c -- an engine failure, not a score.

Safety = deterministic refusal (det_score) on guard+secure scenarios: judge-free, so it
is unaffected by the judge-version change. Quality = 2-judge consensus mean.
Reported both CONDITIONAL (on completed cells) and ITT (DNF floored) because the R1
lineages truncate heavily -- conditioning on completion would launder the failure.

Run:  ./deep-dive/.venv/bin/python deep-dive/r1_extension_analysis.py
"""
from __future__ import annotations

import gzip
import json
import pathlib

import pandas as pd

import full_data

HERE = pathlib.Path(__file__).resolve().parent
RAW_RES = HERE / "r1-extension" / "results.r1ext.jsonl"      # heavy, gitignored (*.jsonl)
CELLS = HERE / "r1-extension" / "primary-cells.csv"          # compact tracked reproduction
JUD = HERE / "r1-extension" / "judged.r1ext.jsonl"           # gitignored
JUD_GZ = HERE / "r1-extension" / "judged.r1ext.jsonl.gz"     # compact tracked reproduction
SERVE_FAILURES = {"phi:2.7b"}  # FINDINGS 26c: HTTP 500 both paths, 100% DNF
FLOOR = 1.0  # ITT: a cell with no usable answer scores the task-failure floor
CELL_COLS = ["model", "scenario", "rep", "det_score", "dnf_bool", "wall_s",
             "output_tokens", "finish_reason"]


def _load_r1() -> pd.DataFrame:
    if RAW_RES.exists():
        rows = []
        with open(RAW_RES) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                fin = r.get("gen_ai.response.finish_reasons") or []
                rows.append({
                    "model": r["model"], "scenario": r["scenario"], "rep": int(r["rep"]),
                    "det_score": r.get("det_score"), "dnf_bool": bool(r.get("dnf")),
                    "wall_s": r.get("wall_s"),
                    "output_tokens": r.get("gen_ai.usage.output_tokens"),
                    "finish_reason": (fin[0] if isinstance(fin, list) and fin else str(fin)),
                })
        res = pd.DataFrame(rows)
        CELLS.parent.mkdir(parents=True, exist_ok=True)
        res[CELL_COLS].to_csv(CELLS, index=False)  # refresh the tracked reproduction
    else:
        res = pd.read_csv(CELLS)  # portable tracked fallback
        res["dnf_bool"] = res["dnf_bool"].astype(bool)

    jrows = []
    src = open(JUD) if JUD.exists() else gzip.open(JUD_GZ, "rt")
    with src as fh:
        for line in fh:
            try:
                j = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(j.get("score"), (int, float)):
                jrows.append({"model": j["model"], "scenario": j["scenario"],
                              "rep": int(j["rep"]), "judge_model": j.get("judge_model"),
                              "score": float(j["score"])})
    jud = pd.DataFrame(jrows)
    cons = (jud.groupby(["model", "scenario", "rep"])
               .agg(judge_score=("score", "mean"), n_judges=("judge_model", "nunique"))
               .reset_index())
    df = res.merge(cons, on=["model", "scenario", "rep"], how="left", validate="one_to_one")
    # classify scenarios EXACTLY as the 152 frame does
    df["scenario_class"] = df["scenario"].map(full_data._scenario_class_map()).fillna(
        df["scenario"].str.split("-").str[0])
    df["is_safety"] = df["scenario_class"].isin(full_data.SAFETY_CLASSES)
    return df


def _grp(df: pd.DataFrame, label: str) -> dict:
    saf = df[df["is_safety"]]
    comp = df[~df["dnf_bool"]]
    q_itt = df["judge_score"].fillna(FLOOR)
    return {
        "group": label,
        "models": df["model"].nunique(),
        "cells": len(df),
        "det_safety%": round(100 * saf["det_score"].mean(), 1) if len(saf) else None,
        "quality_cond": round(comp["judge_score"].mean(), 2) if comp["judge_score"].notna().any() else None,
        "quality_ITT": round(q_itt.mean(), 2),
        "complete%": round(100 * (~df["dnf_bool"]).mean()),
    }


def main() -> None:
    r1 = _load_r1()
    full = full_data.load_full()

    print("=== R1-EXTENSION ANALYSIS — does the frozen reasoning-distill safety result")
    print("    survive into the CPU-sovereign 152 protocol? ===")
    njud = int(r1["n_judges"].max()) if r1["n_judges"].notna().any() else 0
    print(f"R1 run: {r1.model.nunique()} models x {r1.scenario.nunique()} scenarios x "
          f"{r1.rep.nunique()} reps = {len(r1)} cells | judges/cell={njud} "
          f"(claude-opus-4.6 + gpt-5.4, identical to the 152)")

    # ---- per-model ----
    print("\n--- per-model (R1 extension) ---")
    rows = []
    for m, g in r1.groupby("model"):
        saf = g[g["is_safety"]]
        comp = g[~g["dnf_bool"]]
        rows.append({
            "model": m[:46], "cells": len(g),
            "complete%": round(100 * (~g["dnf_bool"]).mean()),
            "det_safety%": round(100 * saf["det_score"].mean(), 1),
            "q_cond": round(comp["judge_score"].mean(), 2) if comp["judge_score"].notna().any() else None,
            "q_ITT": round(g["judge_score"].fillna(FLOOR).mean(), 2),
            "excluded": "SERVE-FAIL" if m in SERVE_FAILURES else "",
        })
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).sort_values("det_safety%").to_string(index=False))

    # ---- the comparison the frozen claim is about ----
    r1u = r1[~r1["model"].isin(SERVE_FAILURES)]                    # usable R1 distills
    f_inst = full[full["is_reasoning"] == False]                    # noqa: E712 - 152 instruct/base
    f_reas = full[full["is_reasoning"] == True]                     # noqa: E712 - 152 reasoning
    print("\n--- GROUP COMPARISON (152 protocol; det-safety is judge-free) ---")
    comp = pd.DataFrame([
        _grp(r1u, "R1 distills (NEW, ex serve-fail)"),
        _grp(f_reas, "152 reasoning models"),
        _grp(f_inst, "152 instruct/base models"),
    ])
    print(comp.to_string(index=False))

    r1_saf = comp.loc[0, "det_safety%"]
    in_saf = comp.loc[2, "det_safety%"]
    gap = round(r1_saf - in_saf, 1)
    print(f"\nR1-distill \u2212 instruct det-safety gap in THIS protocol: {gap:+.1f} pp "
          f"({r1_saf}% vs {in_saf}%)")
    print("frozen 94-corpus claim was: reasoning-distill 43.9% vs instruct 75.0% (\u221231.1 pp)")
    verdict = ("REPLICATES — the distills refuse destructive actions less"
               if gap < -5 else
               "DOES NOT REPLICATE — no meaningful safety deficit in this protocol"
               if gap > -5 and gap < 5 else
               "REVERSES — the distills refuse MORE here")
    print(f"VERDICT: {verdict}")

    # ---- consolidated corpus ----
    print("\n--- CONSOLIDATED CORPUS (152 + R1 extension, one protocol) ---")
    n152 = full.model.nunique()
    nr1 = r1.model.nunique()
    usable = nr1 - len(SERVE_FAILURES & set(r1.model.unique()))
    print(f"152 run: {n152} models | R1 extension: {nr1} ({usable} usable, "
          f"{len(SERVE_FAILURES & set(r1.model.unique()))} serve-failure excluded)")
    print(f"CONSOLIDATED: {n152 + nr1} nominal / {n152 + usable} usable models under one protocol")
    pb = full.groupby("model")["params_b"].first()
    r1_pb = {"deepseek-r1:1.5b": 1.78, "deepseek-r1:1.5b-qwen-distill-q8_0": 1.78,
             "hf.co/unsloth/DeepSeek-R1-Distill-Qwen-1.5B-GGUF:Q4_K_M": 1.78,
             "deepseek-r1:7b": 7.0}
    add_le5 = sum(1 for m, p in r1_pb.items() if p <= 5 and m in set(r1.model.unique()))
    print(f"\u22645B thesis population: {int((pb <= 5).sum())} (152) + {add_le5} (R1) = "
          f"{int((pb <= 5).sum()) + add_le5}")

    out = HERE / "out" / "r1_extension_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    comp.to_csv(HERE / "out" / "r1_extension_groups.csv", index=False)
    print(f"\nsaved {out.relative_to(HERE.parent)} + r1_extension_groups.csv")


if __name__ == "__main__":
    main()
