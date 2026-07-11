#!/usr/bin/env python3
"""Validate ApprenticeOps Croissant metadata against frozen local evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data/croissant.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_validate() -> None:
    metadata = json.loads(METADATA.read_text())
    required = {
        "@context", "@type", "conformsTo", "creator", "datePublished",
        "description", "distribution", "license", "name", "url",
    }
    missing = sorted(required - set(metadata))
    if missing:
        raise SystemExit(f"Croissant metadata is missing required fields: {missing}")
    if metadata["@type"] != "sc:Dataset":
        raise SystemExit("Croissant @type must be sc:Dataset")
    if metadata["conformsTo"] != "http://mlcommons.org/croissant/1.0":
        raise SystemExit("Croissant metadata must conform to version 1.0")
    if metadata.get("isLiveDataset") is not False:
        raise SystemExit("frozen paper metadata must not be marked live")
    manifest = json.loads((ROOT / "data/analysis-manifest.json").read_text())
    expected = manifest.get("source_sha256") or {}
    observed = {}
    identifiers = set()
    for item in metadata["distribution"]:
        identifier = item.get("@id")
        if not identifier or identifier in identifiers:
            raise SystemExit(f"duplicate or empty Croissant distribution id: {identifier!r}")
        identifiers.add(identifier)
        relative = f"data/{item['contentUrl']}"
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"Croissant distribution is missing: {relative}")
        if item.get("sha256") != sha256(path):
            raise SystemExit(f"Croissant SHA-256 mismatch: {relative}")
        if item.get("contentSize") != f"{path.stat().st_size} B":
            raise SystemExit(f"Croissant size mismatch: {relative}")
        observed[relative] = item["sha256"]
    if observed != expected:
        raise SystemExit("Croissant distributions must exactly match the frozen manifest")
    if "https://www.apache.org/licenses/LICENSE-2.0" not in metadata["license"]:
        raise SystemExit("Croissant metadata omits the repository license")
    if len(metadata["license"]) < 2:
        raise SystemExit("Croissant metadata must disclose mixed model rights")
    print(
        f"Croissant local validation passed: files={len(observed)} "
        f"record_sets={len(metadata.get('recordSet') or [])}"
    )


def official_validate() -> None:
    try:
        import mlcroissant as mlc
    except ImportError as exc:
        raise SystemExit(
            "mlcroissant is required for --official; install requirements-release.txt"
        ) from exc
    dataset = mlc.Dataset(str(METADATA))
    serialized = dataset.metadata.to_json()
    if serialized.get("name") != "ApprenticeOps frozen 94-model benchmark dataset":
        raise SystemExit("official Croissant parser changed the dataset identity")
    first = next(iter(dataset.records(record_set="results")), None)
    if not first or not {"results/model", "results/scenario", "results/rep"} <= set(first):
        raise SystemExit("official Croissant loader could not read the results record set")
    print("official mlcroissant validation passed: results record loaded")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", action="store_true")
    args = parser.parse_args()
    local_validate()
    if args.official:
        official_validate()


if __name__ == "__main__":
    main()