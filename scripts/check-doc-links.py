#!/usr/bin/env python3
"""Validate local links in every versioned or non-ignored Markdown/QMD source."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
SCHEMES = {"data", "file", "ftp", "http", "https", "mailto", "tel"}


def tracked_docs() -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "*.md",
            "*.qmd",
        ],
        cwd=REPO,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    sources = {Path(line) for line in result.stdout.splitlines() if line}
    return sorted(path for path in sources if (REPO / path).is_file())


def target_path(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    elif re.search(r"\s+[\"']", value):
        value = re.split(r"\s+[\"']", value, maxsplit=1)[0]
    if not value or value.startswith("#") or value.startswith("{{"):
        return None
    parsed = urlsplit(value)
    if parsed.scheme.lower() in SCHEMES or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if not path or path.startswith("/"):
        return None
    return path


def generated_source(candidate: Path) -> Path | None:
    if candidate.suffix == ".html":
        for suffix in (".qmd", ".ipynb", ".md"):
            source = candidate.with_suffix(suffix)
            if source.exists():
                return source
    if candidate.suffix == ".pdf":
        for suffix in (".qmd", ".md"):
            source = candidate.with_suffix(suffix)
            if source.exists():
                return source
    return None


def main() -> None:
    errors: list[str] = []
    checked = 0
    for relative in tracked_docs():
        source = REPO / relative
        text = source.read_text(errors="replace")
        targets = [match.group(1) for match in INLINE_LINK.finditer(text)]
        targets.extend(match.group(1) for match in REFERENCE_LINK.finditer(text))
        for raw in targets:
            path = target_path(raw)
            if path is None:
                continue
            checked += 1
            candidate = (source.parent / path).resolve()
            try:
                candidate.relative_to(REPO)
            except ValueError:
                errors.append(f"{relative}: link escapes repository: {raw}")
                continue
            if candidate.exists() or generated_source(candidate) is not None:
                continue
            errors.append(f"{relative}: missing local target: {raw}")
    if errors:
        raise SystemExit("ERROR: broken documentation links\n" + "\n".join(errors))
    print(f"documentation link audit passed: files={len(tracked_docs())} local_links={checked}")


if __name__ == "__main__":
    main()
