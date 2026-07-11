#!/usr/bin/env python3
"""Build a blind human-eval packet from committed run artifacts."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
import tarfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAPER_SOURCE_ID = "paper-94-model-corrected-v1"
PAPER_EVALUATION_POLICY = (
    "deterministic-checks-v1|judges:"
    "copilot:claude-opus-4.8+copilot:gpt-5.5"
)
PAPER_JUDGES = ("claude-opus-4.8", "gpt-5.5")
PAPER_OUTPUTS = {
    "var": REPO / "data/raw/outputs.var.tar.gz",
    "wave2": REPO / "data/raw/outputs.wave2.tar.gz",
}


def read_jsonl(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", errors="ignore") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def load_paper_locked_rows() -> tuple[list[dict], dict, dict[str, str]]:
    manifest_path = REPO / "data/analysis-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if (
        manifest.get("analysis_schema_version") != 1
        or manifest.get("source_kind") != "frozen_snapshot"
        or manifest.get("source_id") != PAPER_SOURCE_ID
        or manifest.get("claim_status") != "locked"
    ):
        raise SystemExit("paper human-eval source is not the locked canonical v1 snapshot")
    required = [
        "data/raw/outputs.var.tar.gz",
        "data/raw/outputs.wave2.tar.gz",
        "data/scenarios.json",
        "data/site/judge_pairs.csv",
        "data/snapshots/judge_pair_provenance.csv",
        "data/snapshots/results_snapshot.csv",
    ]
    manifest_hashes = manifest.get("source_sha256") or {}
    for relative in required:
        path = REPO / relative
        if manifest_hashes.get(relative) != sha256(path):
            raise SystemExit(f"paper human-eval source is not hash-bound: {relative}")

    with (REPO / "data/snapshots/results_snapshot.csv").open(newline="") as handle:
        result_rows = list(csv.DictReader(handle))
    result_batches = {
        (row["model"], row["scenario"], int(row["rep"])): row["collection_batch"]
        for row in result_rows
    }
    if len(result_batches) != len(result_rows):
        raise SystemExit("paper result snapshot has duplicate model/scenario/repetition keys")

    with (REPO / "data/site/judge_pairs.csv").open(newline="") as handle:
        pair_rows = list(csv.DictReader(handle))
    candidates = []
    for row in pair_rows:
        key = (row["model"], row["scenario"], int(row["rep"]))
        batch = result_batches.get(key)
        if batch not in PAPER_OUTPUTS:
            raise SystemExit(f"paper judge pair lacks frozen result provenance: {key}")
        candidates.append({
            "model": key[0],
            "scenario": key[1],
            "rep": key[2],
            "collection_batch": batch,
            "judge_scores": {
                PAPER_JUDGES[0]: float(row["claude_score"]),
                PAPER_JUDGES[1]: float(row["gpt_score"]),
            },
        })
    if len(candidates) != 8_909:
        raise SystemExit(f"paper judge-pair population changed: {len(candidates)} != 8909")
    metadata = {
        "analysis_manifest_sha256": sha256(manifest_path),
        "evaluation_policy": PAPER_EVALUATION_POLICY,
        "source_id": PAPER_SOURCE_ID,
        "source_kind": "frozen_snapshot",
        "source_sha256": {relative: manifest_hashes[relative] for relative in required},
    }
    return candidates, json.loads((REPO / "data/scenarios.json").read_text()), metadata


def paper_answers(rows: list[dict]) -> dict[tuple[str, str, int], str]:
    answers = {}
    archives = {
        batch: tarfile.open(path, "r:gz")
        for batch, path in PAPER_OUTPUTS.items()
    }
    try:
        members = {
            batch: set(archive.getnames())
            for batch, archive in archives.items()
        }
        for row in rows:
            key = (row["model"], row["scenario"], int(row["rep"]))
            slug = row["model"].replace("/", "_").replace(":", "_")
            member = f"outputs/{slug}__{row['scenario']}__r{row['rep']}.txt"
            batch = row["collection_batch"]
            if member not in members[batch]:
                raise SystemExit(f"paper answer archive is missing {member}")
            extracted = archives[batch].extractfile(member)
            if extracted is None:
                raise SystemExit(f"paper answer archive cannot read {member}")
            answers[key] = extracted.read().decode("utf-8", errors="strict")
    finally:
        for archive in archives.values():
            archive.close()
    return answers


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
    parser.add_argument("--source-kind", choices=("run", "paper-locked"), default="run")
    parser.add_argument("--run-id", default="external-v1-spread10-baseline-clean-20260703-164337")
    parser.add_argument("--n", type=int, default=45)
    parser.add_argument("--seed", type=int, default=20260704)
    parser.add_argument("--out-dir")
    args = parser.parse_args()

    if args.source_kind == "paper-locked":
        rows, scenario_payload, metadata = load_paper_locked_rows()
        source_id = PAPER_SOURCE_ID
        judges = None
    else:
        run_dir = REPO / "data" / "runs" / args.run_id
        meta = json.loads((run_dir / "run.meta").read_text())
        scenario_payload = json.loads((REPO / meta["scenarios"]).read_text())
        rows = [row for row in load_run_rows(run_dir) if row.get("gen_ai.completion")]
        judges = load_judges(run_dir)
        source_id = args.run_id
        metadata = {"run_id": args.run_id}
    scenarios = {row["id"]: row for row in scenario_payload["scenarios"]}
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
    locked_answers = paper_answers(picked) if args.source_kind == "paper-locked" else {}

    out_dir = Path(args.out_dir).resolve() if args.out_dir else REPO / "data" / "human_eval" / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = out_dir / "sheet.md"
    scores_path = out_dir / "scores.csv"
    key_path = out_dir / "key.json"

    key = {**metadata, "seed": args.seed, "items": []}
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
            row_key = (row["model"], row["scenario"], int(row.get("rep") or 0))
            answer = clean_block(
                locked_answers.get(row_key, "")
                if args.source_kind == "paper-locked"
                else row.get("gen_ai.completion") or ""
            )
            sheet.write(f"## {row_id}\n\n")
            sheet.write(f"Class: `{scenario.get('class')}` · Grounding: `{scenario.get('grounding')}` · Difficulty: `{scenario.get('difficulty')}`\n\n")
            sheet.write(f"**Context**\n\n```\n{clean_block(scenario.get('context', ''))}\n```\n\n")
            sheet.write(f"**Task**\n\n{clean_block(scenario.get('question', ''))}\n\n")
            sheet.write(f"**Gold reference**\n\n{clean_block(scenario.get('gold_answer', ''))}\n\n")
            sheet.write(f"**Rubric**\n\n{clean_block(scenario.get('judge_rubric', ''))}\n\n")
            sheet.write(f"**Answer**\n\n```\n{answer}\n```\n\n")
            sheet.write("**Human score (1-5):** ____\n\n---\n\n")
            writer.writerow([row_id, "", ""])
            judge_key = row_key
            key["items"].append({
                "row_id": row_id,
                "model": row["model"],
                "scenario": row["scenario"],
                "rep": int(row.get("rep") or 0),
                "judge_scores": row["judge_scores"] if judges is None else judges.get(judge_key, {}),
            })
    key_path.write_text(json.dumps(key, indent=2, sort_keys=True) + "\n")
    sheet_path.write_text(sheet_path.read_text().rstrip() + "\n")
    try:
        display_path = out_dir.relative_to(REPO)
    except ValueError:
        display_path = out_dir
    print(f"wrote human eval packet: {display_path} items={len(picked)}")


if __name__ == "__main__":
    main()