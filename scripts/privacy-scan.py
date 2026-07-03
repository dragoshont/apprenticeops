#!/usr/bin/env python3
"""Scan ApprenticeOps for live-looking secrets and publication disclosures."""

from __future__ import annotations

import argparse
import os
import re
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
}

TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
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
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github-token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("openai-style-key", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
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
            if path.suffix not in TEXT_SUFFIXES:
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    continue
            except OSError:
                continue
            files.append(path)
    return sorted(files)


def allowed_secret(match_text: str) -> bool:
    low = match_text.lower()
    return any(item.lower() in low for item in ALLOW_SECRET_SUBSTRINGS)


def scan_file(path: Path) -> tuple[list[tuple[str, int, str]], list[tuple[str, int, str]]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], []
    secrets: list[tuple[str, int, str]] = []
    disclosures: list[tuple[str, int, str]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        for name, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                snippet = match.group(0)[:120]
                if not allowed_secret(snippet):
                    secrets.append((name, index, snippet))
        for name, pattern in DISCLOSURE_PATTERNS:
            if pattern.search(line):
                disclosures.append((name, index, line.strip()[:160]))
    return secrets, disclosures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show-disclosures", action="store_true", help="print disclosure findings, not just summary counts")
    args = parser.parse_args()

    secret_hits: list[tuple[Path, str, int, str]] = []
    disclosure_counts: dict[str, int] = {}
    disclosure_examples: list[tuple[Path, str, int, str]] = []
    files = iter_files()
    for path in files:
        secrets, disclosures = scan_file(path)
        for name, line_number, snippet in secrets:
            secret_hits.append((path, name, line_number, snippet))
        for name, line_number, snippet in disclosures:
            disclosure_counts[name] = disclosure_counts.get(name, 0) + 1
            if len(disclosure_examples) < 40:
                disclosure_examples.append((path, name, line_number, snippet))

    if secret_hits:
        print("privacy scan FAIL: live-looking secret patterns found")
        for path, name, line_number, snippet in secret_hits[:50]:
            print(f"  {path.relative_to(REPO)}:{line_number}: {name}: {snippet}")
        raise SystemExit(1)

    print(f"privacy scan PASS: files_scanned={len(files)} secret_hits=0")
    print(f"disclosure_counts={dict(sorted(disclosure_counts.items()))}")
    if args.show_disclosures:
        for path, name, line_number, snippet in disclosure_examples:
            print(f"  {path.relative_to(REPO)}:{line_number}: {name}: {snippet}")


if __name__ == "__main__":
    main()