#!/usr/bin/env python3
"""Report model-lock metadata coverage without inventing missing provenance."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = REPO / "data" / "models.lock.jsonl"


def load_rows() -> list[dict]:
    return [json.loads(line) for line in LOCK.read_text().splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-license", action="store_true", default=True, help="fail if included rows have unknown license metadata")
    parser.add_argument("--strict-digest", action="store_true", help="fail if included rows lack ollama_digest or gguf_sha256")
    args = parser.parse_args()

    rows = load_rows()
    included = [row for row in rows if row["included"]]
    source_unknown = [row for row in included if row["source_url"] == "unknown"]
    license_unknown = [
        row for row in included
        if row["license"] == "unknown" or row["license_url"] == "unknown" or row["license_status"] == "unknown"
    ]
    digest_missing = [row for row in included if not row["ollama_digest"] and not row["gguf_sha256"]]
    status_counts = Counter(row["metadata_status"] for row in rows)
    license_counts = Counter(row["license"] for row in included)
    license_class_counts = Counter(row["license_class"] for row in included)
    license_status_counts = Counter(row["license_status"] for row in included)
    llama_cpp_counts = Counter(row["llama_cpp_status"] for row in included)
    print(
        "model metadata audit: "
        f"rows={len(rows)} included={len(included)} source_unknown={len(source_unknown)} "
        f"license_unknown={len(license_unknown)} digest_or_hash_missing={len(digest_missing)} "
        f"metadata_status={dict(sorted(status_counts.items()))} "
        f"llama_cpp_status={dict(sorted(llama_cpp_counts.items()))}"
    )
    print(f"license_counts={dict(sorted(license_counts.items()))}")
    print(f"license_class_counts={dict(sorted(license_class_counts.items()))}")
    print(f"license_status_counts={dict(sorted(license_status_counts.items()))}")
    if source_unknown:
        print("source_unknown_examples=" + ", ".join(row["model_id"] for row in source_unknown[:10]))
    if license_unknown:
        print("license_unknown_examples=" + ", ".join(row["model_id"] for row in license_unknown[:10]))
    if digest_missing:
        print("digest_missing_examples=" + ", ".join(row["model_id"] for row in digest_missing[:10]))
    if source_unknown:
        raise SystemExit("ERROR: included rows must have source_url")
    if args.strict_license and license_unknown:
        raise SystemExit("ERROR: included rows have unknown license")
    if args.strict_digest and digest_missing:
        raise SystemExit("ERROR: included rows lack digest/hash")


if __name__ == "__main__":
    main()