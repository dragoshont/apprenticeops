#!/usr/bin/env python3
"""Build a deterministic Zenodo-ready archive from the frozen paper manifest."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "paper-94-model-corrected-v1"
OUTPUT_ROOT = ROOT / ".tmp/release"
EXTRA_FILES = (
    ".python-version",
    "CITATION.cff",
    "LICENSE",
    "REPRODUCE.md",
    "data/DATA_RIGHTS.md",
    "data/analysis-manifest.json",
    "data/analysis.schema.json",
    "data/croissant.json",
    "data/tool-license-policy.json",
    "data/human_eval/paper-94-model-corrected-v1/scores.csv",
    "data/human_eval/paper-94-model-corrected-v1/sheet.md",
    "docs/ARTIFACT_INVENTORY.md",
    "docs/PRIVACY_AND_EGRESS.md",
    "requirements-lock.in",
    "requirements-lock.txt",
    "requirements-release.txt",
    "requirements.txt",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_files() -> list[Path]:
    manifest = json.loads((ROOT / "data/analysis-manifest.json").read_text())
    if (
        manifest.get("source_id") != SOURCE_ID
        or manifest.get("source_kind") != "frozen_snapshot"
        or manifest.get("claim_status") != "locked"
    ):
        raise SystemExit("release packaging requires the locked paper manifest")
    relative_paths = sorted(set(manifest["source_sha256"]) | set(EXTRA_FILES))
    files = []
    for relative in relative_paths:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"release source is missing: {relative}")
        files.append(path)
    return files


def tar_info(path: Path, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(path.relative_to(ROOT).as_posix())
    info.size = size
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def build(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in source_files():
                    value = path.read_bytes()
                    archive.addfile(tar_info(path, len(value)), io.BytesIO(value))
    temporary.replace(output)


def verify(output: Path) -> None:
    expected = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in source_files()
    }
    with tarfile.open(output, "r:gz") as archive:
        members = [member for member in archive if member.isfile()]
        observed = {}
        for member in members:
            extracted = archive.extractfile(member)
            if extracted is None:
                raise SystemExit(f"release archive cannot read {member.name}")
            observed[member.name] = hashlib.sha256(extracted.read()).hexdigest()
            if (
                member.mtime != 0
                or member.uid != 0
                or member.gid != 0
                or member.mode != 0o644
                or member.uname
                or member.gname
            ):
                raise SystemExit(f"release archive metadata is not deterministic: {member.name}")
    if observed != expected:
        raise SystemExit("release archive does not exactly match its declared sources")
    try:
        display_path = output.relative_to(ROOT)
    except ValueError:
        display_path = output
    print(
        f"release package verified: files={len(expected)} "
        f"sha256={sha256(output)} path={display_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_ROOT / f"apprenticeops-{SOURCE_ID}.tar.gz",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    build(output)
    verify(output)


if __name__ == "__main__":
    main()