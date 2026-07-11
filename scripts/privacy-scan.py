#!/usr/bin/env python3
"""Scan ApprenticeOps for live-looking secrets and publication disclosures."""

from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import tarfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".tmp",
    ".venv",
    "venv",
    "__pycache__",
    "downloads",
    "docs/analysis/_site",
    "docs/analysis/.quarto",
    "dashboard/frontend/node_modules",
    "data/completed-runs/.staging",
    "data/completed-runs/.state",
}

TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".out",
    ".py",
    ".qmd",
    ".sh",
    ".txt",
    ".yaml",
    ".yml",
}

ALLOW_SECRET_SUBSTRINGS = {
    "EXAMPLE_BEARER_TOKEN_DO_NOT_USE",
    "<token>",
    "<secret>",
    "REDACTED",
    "example",
}

SECRET_PATTERNS = [
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("openai-style-key", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}")),
    ("aws-access-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack-token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}")),
    ("bearer-token", re.compile(r"Authorization:\s*Bearer\s+([A-Za-z0-9._~+/=-]{16,})", re.IGNORECASE)),
]

DISCLOSURE_PATTERNS = [
    ("homelab-domain", re.compile(r"\b[A-Za-z0-9_.-]*home\.domain\b")),
    ("hont-domain", re.compile(r"\b[A-Za-z0-9_.-]*hont\.ro\b")),
    ("private-ip", re.compile(r"\b(?:10|172\.(?:1[6-9]|2[0-9]|3[0-1])|192\.168)\.[0-9]{1,3}\.[0-9]{1,3}\b")),
    ("azure-key-vault", re.compile(r"Azure Key Vault|key vault", re.IGNORECASE)),
    ("cloudflare", re.compile(r"Cloudflare", re.IGNORECASE)),
]


def is_skipped(path: Path) -> bool:
    relative = path.relative_to(REPO)
    parts = relative.parts
    if any(part in {".venv", "venv", ".tmp", "__pycache__"} for part in parts):
        return True
    for skip in SKIP_DIRS:
        skip_parts = Path(skip).parts
        if parts[: len(skip_parts)] == skip_parts:
            return True
    return False


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root, dirs, filenames in os.walk(REPO):
        root_path = Path(root)
        dirs[:] = [directory for directory in dirs if not is_skipped(root_path / directory)]
        for filename in filenames:
            path = root_path / filename
            if is_skipped(path):
                continue
            relative_parts = path.relative_to(REPO).parts
            released_evidence = (
                path.parent == REPO / "data" / "raw"
                or (
                    relative_parts[:2] == ("data", "completed-runs")
                    and not any(part.startswith(".") for part in relative_parts[2:])
                )
            )
            if path.suffix not in TEXT_SUFFIXES and not released_evidence:
                continue
            try:
                if path.stat().st_size > 2_000_000 and not released_evidence:
                    continue
            except OSError:
                continue
            files.append(path)
    return sorted(files)


def allowed_secret(match_text: str) -> bool:
    low = match_text.lower()
    return any(item.lower() in low for item in ALLOW_SECRET_SUBSTRINGS)


def iter_text_lines(path: Path):
    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                with io.TextIOWrapper(extracted, encoding="utf-8", errors="ignore") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        yield f"{member.name}:{line_number}", line
        return
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line_number, line in enumerate(handle, start=1):
            yield str(line_number), line


def scan_file(path: Path) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    try:
        lines = iter_text_lines(path)
        secrets: list[tuple[str, str, str]] = []
        disclosures: list[tuple[str, str, str]] = []
        private_key_start = None
        private_key_has_material = False
        for location, line in lines:
            if re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", line):
                private_key_start = location
                private_key_has_material = False
            elif private_key_start is not None:
                stripped = line.strip()
                if re.search(r"-----END [A-Z ]*PRIVATE KEY-----", line):
                    if private_key_has_material:
                        secrets.append(("private-key", private_key_start, "private key PEM block"))
                    private_key_start = None
                    private_key_has_material = False
                elif stripped not in {"", "...", "```"}:
                    private_key_has_material = True
            for name, pattern in SECRET_PATTERNS:
                for match in pattern.finditer(line):
                    snippet = match.group(0)[:120]
                    if not allowed_secret(snippet):
                        secrets.append((name, location, snippet))
            for name, pattern in DISCLOSURE_PATTERNS:
                if pattern.search(line):
                    disclosures.append((name, location, line.strip()[:160]))
                if private_key_start is not None and private_key_has_material:
                    secrets.append(("private-key", private_key_start, "unterminated private key PEM block"))
        return secrets, disclosures
    except (OSError, tarfile.TarError) as exc:
        return [("archive-read-error", "unreadable", type(exc).__name__)], []


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-disclosures", action="store_true", help="print disclosure findings, not just summary counts")
    args = parser.parse_args()

    secret_hits: list[tuple[Path, str, str, str]] = []
    disclosure_counts: dict[str, int] = {}
    disclosure_examples: list[tuple[Path, str, str, str]] = []
    files = iter_files()
    for path in files:
        secrets, disclosures = scan_file(path)
        for name, location, snippet in secrets:
            secret_hits.append((path, name, location, snippet))
        for name, location, snippet in disclosures:
            disclosure_counts[name] = disclosure_counts.get(name, 0) + 1
            if len(disclosure_examples) < 40:
                disclosure_examples.append((path, name, location, snippet))

    if secret_hits:
        print("privacy scan FAIL: live-looking secret patterns found")
        for path, name, location, snippet in secret_hits[:50]:
            print(f"  {path.relative_to(REPO)}:{location}: {name}: {snippet}")
        raise SystemExit(1)

    print(f"privacy scan PASS: files_scanned={len(files)} secret_hits=0")
    print(f"disclosure_counts={dict(sorted(disclosure_counts.items()))}")
    if args.show_disclosures:
        for path, name, location, snippet in disclosure_examples:
            print(f"  {path.relative_to(REPO)}:{location}: {name}: {snippet}")


if __name__ == "__main__":
    main()