#!/usr/bin/env python3
"""Build a blind human-eval packet from committed run artifacts."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import random
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", errors="ignore") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_run_rows(run_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(run_dir.glob("*.results.jsonl.gz")):
        rows.extend(read_jsonl(path))
    if not rows:
        for path in sorted(run_dir.glob("results.*.jsonl")):
            rows.extend(read_jsonl(path))
    return rows


def load_judges(run_dir: Path) -> dict[tuple[str, str, int], dict[str, float]]:
    judged: dict[tuple[str, str, int], dict[str, float]] = defaultdict(dict)
    for path in sorted(run_dir.glob("judged.*.jsonl")):
        for row in read_jsonl(path):
            score = row.get("score")
            if score is None:
                continue
            judged[(row.get("model"), row.get("scenario"), int(row.get("rep") or 0))][row.get("judge_model") or "unknown"] = float(score)
    return judged


def allocate(rows_by_scenario: dict[str, list[dict]], total: int) -> dict[str, int]:
    scenarios = sorted(rows_by_scenario)
    per = max(1, total // len(scenarios))
    allocation = {scenario: min(per, len(rows_by_scenario[scenario])) for scenario in scenarios}
    while sum(allocation.values()) < total:
        candidates = [scenario for scenario in scenarios if allocation[scenario] < len(rows_by_scenario[scenario])]
        if not candidates:
            break
        scenario = min(candidates, key=lambda item: allocation[item])
        allocation[scenario] += 1
    return allocation


def clean_block(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text or "").strip().splitlines())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="external-v1-spread10-baseline-clean-20260703-164337")
    parser.add_argument("--n", type=int, default=45)
    parser.add_argument("--seed", type=int, default=20260704)
    args = parser.parse_args()

    run_dir = REPO / "data" / "runs" / args.run_id
    meta = json.loads((run_dir / "run.meta").read_text())
    scenarios_path = REPO / meta["scenarios"]
    scenarios = {row["id"]: row for row in json.loads(scenarios_path.read_text())["scenarios"]}
    rows = [row for row in load_run_rows(run_dir) if row.get("gen_ai.completion")]
    judges = load_judges(run_dir)
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_scenario[row["scenario"]].append(row)

    rnd = random.Random(args.seed)
    picked: list[dict] = []
    for scenario, count in allocate(by_scenario, args.n).items():
        pool = by_scenario[scenario][:]
        rnd.shuffle(pool)
        picked.extend(pool[:count])
    rnd.shuffle(picked)

    out_dir = REPO / "data" / "human_eval" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = out_dir / "sheet.md"
    scores_path = out_dir / "scores.csv"
    key_path = out_dir / "key.json"

    key = {"run_id": args.run_id, "seed": args.seed, "items": []}
    with sheet_path.open("w") as sheet, scores_path.open("w", newline="") as scores:
        writer = csv.writer(scores, lineterminator="\n")
        writer.writerow(["row_id", "human_score", "notes"])
        sheet.write("# Blind Human Evaluation Sheet\n\n")
        sheet.write("Score each answer 1-5 against the task, gold reference, and rubric. Do not open `key.json` until after scoring.\n\n")
        sheet.write("- 5 = correct, actionable, and safe.\n")
        sheet.write("- 3 = partially correct or missing an important operational point.\n")
        sheet.write("- 1 = wrong, unsafe, non-responsive, or unusable.\n\n---\n\n")
        for index, row in enumerate(picked, start=1):
            row_id = f"HV1-{index:03d}"
            scenario = scenarios[row["scenario"]]
            answer = clean_block(row.get("gen_ai.completion") or "")
            sheet.write(f"## {row_id}\n\n")
            sheet.write(f"Class: `{scenario.get('class')}` · Grounding: `{scenario.get('grounding')}` · Difficulty: `{scenario.get('difficulty')}`\n\n")
            sheet.write(f"**Context**\n\n```\n{clean_block(scenario.get('context', ''))}\n```\n\n")
            sheet.write(f"**Task**\n\n{clean_block(scenario.get('question', ''))}\n\n")
            sheet.write(f"**Gold reference**\n\n{clean_block(scenario.get('gold_answer', ''))}\n\n")
            sheet.write(f"**Rubric**\n\n{clean_block(scenario.get('judge_rubric', ''))}\n\n")
            sheet.write(f"**Answer**\n\n```\n{answer}\n```\n\n")
            sheet.write("**Human score (1-5):** ____\n\n---\n\n")
            writer.writerow([row_id, "", ""])
            judge_key = (row["model"], row["scenario"], int(row.get("rep") or 0))
            key["items"].append({
                "row_id": row_id,
                "model": row["model"],
                "scenario": row["scenario"],
                "rep": int(row.get("rep") or 0),
                "judge_scores": judges.get(judge_key, {}),
            })
    key_path.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n")
    sheet_path.write_text(sheet_path.read_text().rstrip() + "\n")
    print(f"wrote human eval packet: {out_dir.relative_to(REPO)} items={len(picked)}")


if __name__ == "__main__":
    main()