#!/usr/bin/env python3
"""Audit citation, rights, Croissant, and archive-release metadata."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def run(command: list[str]) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        print(result.stdout)
        fail(f"command failed: {' '.join(command)}")
    print(result.stdout.strip())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    run([sys.executable, "scripts/validate-analysis-environment.py"])
    run([sys.executable, "scripts/audit-tool-licenses.py"])
    citation = (ROOT / "CITATION.cff").read_text()
    for field in (
        "cff-version:", "title:", "authors:", "license:",
        "repository-code:", "version:", "date-released:",
    ):
        if field not in citation:
            fail(f"CITATION.cff is missing {field}")
    if "PLACEHOLDER" in citation.upper():
        fail("CITATION.cff contains a placeholder")
    rights = ROOT / "data/DATA_RIGHTS.md"
    if not rights.is_file() or "mixed rights" not in rights.read_text().lower():
        fail("data rights must explicitly describe mixed rights")
    models = {
        row["model"]
        for row in csv.DictReader((ROOT / "data/site/models.csv").open(newline=""))
    }
    lock = {
        row["model_id"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "data/models.lock.jsonl").read_text().splitlines()
            if line.strip()
        )
    }
    for model in sorted(models):
        row = lock.get(model) or {}
        if row.get("license") in (None, "", "unknown"):
            fail(f"frozen model has unknown license: {model}")
        if not str(row.get("license_url") or "").startswith("https://"):
            fail(f"frozen model has no HTTPS license evidence: {model}")
    croissant = json.loads((ROOT / "data/croissant.json").read_text())
    publication_commit = subprocess.run(
        [
            "git", "show", "-s", "--format=%aI", "36fc989",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if publication_commit.returncode or not publication_commit.stdout.startswith("2026-06-21T"):
        fail("dataset publication evidence commit 36fc989 is unavailable or has changed")
    if croissant.get("datePublished") != "2026-06-21":
        fail("Croissant datePublished must match complete-dataset commit 36fc989")
    if croissant.get("identifier") or "doi.org" in json.dumps(croissant).lower():
        fail("Croissant metadata must not claim a DOI before one is reserved")
    if "type: doi" in citation.lower() or "doi.org" in citation.lower():
        fail("CITATION.cff must not claim a DOI before one is reserved")
    declared = set(croissant.get("license") or [])
    expected_model_rights = {lock[model]["license_url"] for model in models}
    if not expected_model_rights <= declared:
        fail(f"Croissant omits model rights: {sorted(expected_model_rights - declared)}")
    archive_plan = (ROOT / "docs/ARCHIVAL_RELEASE.md").read_text()
    if "Zenodo" not in archive_plan or "DOI status: not reserved" not in archive_plan:
        fail("archive provider and DOI status must be explicit")
    run([sys.executable, "scripts/build-croissant.py", "--check"])
    run([sys.executable, "scripts/validate-croissant.py"])
    run([sys.executable, "scripts/validate-human-eval.py"])
    packet = ROOT / "data/human_eval/paper-94-model-corrected-v1"
    temporary = ROOT / ".tmp/release/human-eval-regenerated"
    if temporary.exists():
        shutil.rmtree(temporary)
    run([
        sys.executable,
        "scripts/build-human-eval-sample.py",
        "--source-kind", "paper-locked",
        "--n", "50",
        "--seed", "20260711",
        "--out-dir", str(temporary),
    ])
    for filename in ("key.json", "scores.csv", "sheet.md"):
        if sha256(packet / filename) != sha256(temporary / filename):
            fail(f"paper human-eval packet is not deterministic: {filename}")
    run([sys.executable, "scripts/build-release-package.py"])
    print(f"release metadata audit passed: frozen_models={len(models)}")


if __name__ == "__main__":
    main()