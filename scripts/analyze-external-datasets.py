#!/usr/bin/env python3
"""Profile external AIOps/SRE datasets downloaded under downloads/.

This script is intentionally stdlib-only. It does not require pandas or pyarrow;
CSV archives are fully profiled, while parquet-only datasets are represented from
metadata and README cards. Outputs are written under an ignored directory so raw
external data and derived exploratory summaries do not become paper artifacts by
accident.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Any

KEY_FIELDS = {
    "domain",
    "difficulty",
    "failure_type",
    "failure_severity",
    "failure_stage",
    "root_cause",
    "resolution_action",
    "severity",
    "status",
    "error",
    "fix",
    "business_impact",
    "failure_category",
    "event_type",
    "category",
    "log_level",
}

SOURCE_REGISTRY = {
    "MCP-1st-Birthday_smoltrace-site-reliability-engineering-tasks": {
        "platform": "huggingface",
        "url": "https://huggingface.co/datasets/MCP-1st-Birthday/smoltrace-site-reliability-engineering-tasks",
        "terms_url": "https://huggingface.co/terms-of-service",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
    "expertshubham_aiops-log-monitoring-and-failure-detection-dataset": {
        "platform": "kaggle",
        "url": "https://www.kaggle.com/datasets/expertshubham/aiops-log-monitoring-and-failure-detection-dataset",
        "terms_url": "https://www.kaggle.com/terms",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
    "hamzaabbasai_ai-agent-observability-dataset": {
        "platform": "kaggle",
        "url": "https://www.kaggle.com/datasets/hamzaabbasai/ai-agent-observability-dataset",
        "terms_url": "https://www.kaggle.com/terms",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
    "mirzayasirabdullah07_api-failure-intelligence-dataset-afid": {
        "platform": "kaggle",
        "url": "https://www.kaggle.com/datasets/mirzayasirabdullah07/api-failure-intelligence-dataset-afid",
        "terms_url": "https://www.kaggle.com/terms",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
    "mirzayasirabdullah07_cicd-pipeline-failure-logs-dataset-for-aiops": {
        "platform": "kaggle",
        "url": "https://www.kaggle.com/datasets/mirzayasirabdullah07/cicd-pipeline-failure-logs-dataset-for-aiops",
        "terms_url": "https://www.kaggle.com/terms",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
    "nalisha_itsm-incident-system-relationship-dataset": {
        "platform": "kaggle",
        "url": "https://www.kaggle.com/datasets/nalisha/itsm-incident-system-relationship-dataset",
        "terms_url": "https://www.kaggle.com/terms",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
    "sunil123kumar_ai-agent-failure-benchmark-dataset": {
        "platform": "kaggle",
        "url": "https://www.kaggle.com/datasets/sunil123kumar/ai-agent-failure-benchmark-dataset",
        "terms_url": "https://www.kaggle.com/terms",
        "redistribution_status": "needs-human-review",
        "training_status": "needs-human-review",
        "derivative_scenario_status": "needs-human-review",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(errors="ignore"))
    except Exception:
        return {}


def clean_text(value: object, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def source_recommendation(name: str, title: str) -> tuple[str, str]:
    text = f"{name} {title}".lower()
    if "ai-agent-failure" in text or "failure analysis" in text:
        return "judge-calibration/dev", "Failure taxonomy and judge/guardrail calibration; do not mix into held-out scoring."
    if "api-failure" in text or "afid" in text:
        return "scenario-inspiration/dev", "API/log RCA scenario generation and remediation-label mining."
    if "cicd" in text or "pipeline" in text:
        return "scenario-inspiration/dev", "CI/CD build-test-deploy failure scenarios and rollback/flaky-test labels."
    if "log-monitoring" in text:
        return "scenario-inspiration/dev", "Detect/monitor/log-summary scenarios and anomaly labels."
    if "observability" in text:
        return "taxonomy/dev", "Agent incident taxonomy, failure category, and operational dashboard patterns."
    if "itsm" in text:
        return "scenario-inspiration-only", "Thin incident-system graph examples; insufficient for model training alone."
    if "smoltrace" in text:
        return "tool-use-dev", "Synthetic SRE tool-call/action-format tasks; useful for tool discipline, not Core scoring."
    return "needs-review", "Unknown source shape; require manual review before use."


def csv_profile_from_zip(zip_path: Path) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith(".csv"):
                continue
            with archive.open(name) as handle:
                row_count = max(0, sum(1 for _ in handle) - 1)
            with archive.open(name) as handle:
                text = (line.decode("utf-8", "replace") for line in handle)
                reader = csv.DictReader(text)
                columns = reader.fieldnames or []
                samples = []
                value_counts: dict[str, list[tuple[str, int]]] = {}
                counters = {field: collections.Counter() for field in columns if field.lower() in KEY_FIELDS}
                for index, row in enumerate(reader):
                    if index < 3:
                        samples.append({field: clean_text(row.get(field), 180) for field in columns[:10]})
                    for field, counter in counters.items():
                        counter[clean_text(row.get(field), 120)] += 1
                for field, counter in counters.items():
                    value_counts[field] = counter.most_common(20)
            profiles.append({
                "file": name,
                "rows": row_count,
                "columns": columns,
                "samples": samples,
                "value_counts": value_counts,
                "value_count_scope": "all_rows",
            })
    return profiles


def readme_extract(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(errors="ignore")
    task_match = re.search(r"(?:Tasks|Number of rows)\*{0,2}\s*:?\s*(\d+)", text, re.I)
    return {
        "first_heading": next((line.strip("# ") for line in text.splitlines() if line.startswith("# ")), None),
        "task_count_hint": int(task_match.group(1)) if task_match else None,
        "mentions": {
            "synthetic": "synthetic" in text.lower(),
            "tool": "tool" in text.lower(),
            "sre": "sre" in text.lower() or "site reliability" in text.lower(),
            "mcp": "mcp" in text.lower(),
        },
    }


def profile_source(path: Path) -> dict[str, Any]:
    metadata = load_json(path / "metadata.json")
    registry = SOURCE_REGISTRY.get(path.name, {})
    title = metadata.get("title") or metadata.get("id") or metadata.get("ref") or path.name
    license_name = metadata.get("licenseName") or (metadata.get("cardData") or {}).get("license")
    recommended_use, notes = source_recommendation(path.name, str(title))
    files = []
    for zip_path in sorted(path.glob("*.zip")):
        files.append({
            "archive": zip_path.name,
            "bytes": zip_path.stat().st_size,
            "csv_profiles": csv_profile_from_zip(zip_path),
        })
    for parquet_path in sorted(path.glob("**/*.parquet")):
        files.append({
            "file": str(parquet_path.relative_to(path)),
            "bytes": parquet_path.stat().st_size,
            "format": "parquet",
            "csv_profiles": [],
            "note": "Parquet present; row/schema profiling skipped because the analyzer is stdlib-only.",
        })
    readme = readme_extract(path / "README.md")
    return {
        "source_dir": path.name,
        "platform": registry.get("platform"),
        "source_url": registry.get("url"),
        "terms_url": registry.get("terms_url"),
        "title": title,
        "license": license_name,
        "redistribution_status": registry.get("redistribution_status", "needs-human-review"),
        "training_status": registry.get("training_status", "needs-human-review"),
        "derivative_scenario_status": registry.get("derivative_scenario_status", "needs-human-review"),
        "metadata_bytes": metadata.get("totalBytes") or metadata.get("usedStorage"),
        "downloads": metadata.get("downloadCount") or metadata.get("downloads"),
        "last_updated": metadata.get("lastUpdated") or metadata.get("lastModified"),
        "recommended_use": recommended_use,
        "recommendation_notes": notes,
        "risk_flags": risk_flags(metadata, readme),
        "readme": readme,
        "files": files,
    }


def risk_flags(metadata: dict[str, Any], readme: dict[str, Any]) -> list[str]:
    flags = []
    license_name = (metadata.get("licenseName") or (metadata.get("cardData") or {}).get("license") or "").lower()
    if not license_name:
        flags.append("missing-license")
    provenance_text = json.dumps(metadata).lower()
    if readme.get("mentions", {}).get("synthetic") or any(term in provenance_text for term in ("synthetic", "simulated", "generated", "real-world inspired")):
        flags.append("synthetic-not-real-frequency")
    else:
        flags.append("realness-unverified")
    if metadata.get("gated"):
        flags.append("gated")
    if metadata.get("private"):
        flags.append("private")
    return flags


def write_markdown(manifest: list[dict[str, Any]], out_dir: Path) -> None:
    lines = ["# External Dataset Schema Summary", "", "Generated by `scripts/analyze-external-datasets.py`.", ""]
    for item in manifest:
        lines.extend([
            f"## {item['title']}",
            "",
            f"- Source dir: `{item['source_dir']}`",
            f"- Source URL: {item.get('source_url') or 'unknown'}",
            f"- License: `{item.get('license') or 'unknown'}`",
            f"- Rights status: redistribution=`{item.get('redistribution_status')}`; training=`{item.get('training_status')}`; derivative scenarios=`{item.get('derivative_scenario_status')}`",
            f"- Recommended use: **{item['recommended_use']}**",
            f"- Risk flags: {', '.join(item['risk_flags']) if item['risk_flags'] else 'none'}",
            f"- Notes: {item['recommendation_notes']}",
            "",
        ])
        if item.get("readme"):
            lines.append(f"- README task-count hint: `{item['readme'].get('task_count_hint')}`")
            lines.append("")
        for file_info in item["files"]:
            if file_info.get("archive"):
                lines.append(f"### Archive `{file_info['archive']}`")
            else:
                lines.append(f"### File `{file_info['file']}`")
                lines.append(f"- Format: `{file_info.get('format')}`")
                lines.append(f"- Bytes: `{file_info.get('bytes')}`")
                if file_info.get("note"):
                    lines.append(f"- Note: {file_info['note']}")
                lines.append("")
                continue
            for csv_info in file_info["csv_profiles"]:
                lines.extend([
                    f"- CSV: `{csv_info['file']}`",
                    f"- Rows: `{csv_info['rows']}`",
                    f"- Columns ({len(csv_info['columns'])}): `{', '.join(csv_info['columns'])}`",
                    f"- Label counts scope: `{csv_info.get('value_count_scope')}`",
                    "",
                ])
                if csv_info["value_counts"]:
                    lines.append("Key label distributions:")
                    for field, counts in csv_info["value_counts"].items():
                        rendered = "; ".join(f"{value}={count}" for value, count in counts[:8])
                        lines.append(f"- `{field}`: {rendered}")
                    lines.append("")
        lines.append("")
    (out_dir / "schema-summary.md").write_text("\n".join(lines).rstrip() + "\n")


def write_candidate_map(manifest: list[dict[str, Any]], out_dir: Path) -> None:
    lines = ["# Candidate Use Map", "", "This is a planning artifact, not a benchmark result.", ""]
    buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for item in manifest:
        buckets[item["recommended_use"]].append(item)
    for bucket, items in sorted(buckets.items()):
        lines.append(f"## {bucket}")
        lines.append("")
        for item in items:
            lines.append(f"- **{item['title']}** (`{item['source_dir']}`): {item['recommendation_notes']}")
        lines.append("")
    lines.extend([
        "## Promotion gates",
        "",
        "Before any external-derived item becomes an ApprenticeOps scenario, record: source row/file, license status, contamination check, class/difficulty/grounding, gold answer, deterministic checks, and adversarial review verdict.",
    ])
    (out_dir / "candidate-map.md").write_text("\n".join(lines).rstrip() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="downloads/external-datasets")
    parser.add_argument("--out", default="downloads/external-datasets/analysis")
    args = parser.parse_args()
    input_dir = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = [profile_source(path) for path in sorted(input_dir.iterdir()) if path.is_dir() and path.name != "analysis"]
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_markdown(manifest, out_dir)
    write_candidate_map(manifest, out_dir)
    print(f"profiled {len(manifest)} sources -> {out_dir}")


if __name__ == "__main__":
    main()