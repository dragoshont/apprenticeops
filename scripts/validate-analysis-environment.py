#!/usr/bin/env python3
"""Validate the exact Python and hash-locked analysis/release environment."""

from __future__ import annotations

import importlib.metadata
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-lock.txt"
DIRECT = (ROOT / "requirements.txt", ROOT / "requirements-release.txt")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def direct_requirements() -> dict[str, str]:
    found = {}
    for path in DIRECT:
        for raw in path.read_text().splitlines():
            value = raw.split("#", 1)[0].strip()
            if not value:
                continue
            requirement = Requirement(value)
            specifiers = list(requirement.specifier)
            if len(specifiers) != 1 or specifiers[0].operator != "==":
                fail(f"direct dependency must use one exact pin: {path.name}: {value}")
            found[canonicalize_name(requirement.name)] = specifiers[0].version
    return found


def lock_sections(path: Path):
    sections = []
    current = None
    lines: list[str] = []
    for raw in path.read_text().splitlines():
        if raw and not raw[0].isspace() and not raw.startswith("#"):
            if current is not None:
                sections.append((current, lines))
            current = Requirement(raw.removesuffix("\\").strip())
            lines = [raw]
        elif current is not None:
            lines.append(raw)
    if current is not None:
        sections.append((current, lines))
    return sections


def lock_requirements() -> tuple[dict[str, str], list[str]]:
    active = {}
    missing_hashes = []
    for requirement, lines in lock_sections(LOCK):
        name = canonicalize_name(requirement.name)
        if requirement.marker is None or Marker(str(requirement.marker)).evaluate():
            specifiers = list(requirement.specifier)
            if len(specifiers) != 1 or specifiers[0].operator != "==":
                fail(f"lock dependency is not exact: {requirement}")
            active[name] = specifiers[0].version
        if not any("--hash=sha256:" in line for line in lines):
            missing_hashes.append(name)
    return active, missing_hashes


def lock_semantics(path: Path) -> dict[tuple[str, str], tuple[str, tuple[str, ...]]]:
    semantics = {}
    for requirement, lines in lock_sections(path):
        specifiers = list(requirement.specifier)
        if len(specifiers) != 1 or specifiers[0].operator != "==":
            fail(f"lock dependency is not exact: {requirement}")
        key = (
            canonicalize_name(requirement.name),
            str(requirement.marker) if requirement.marker is not None else "",
        )
        hashes = tuple(sorted(
            match.group(1)
            for line in lines
            if (match := re.search(r"--hash=sha256:([0-9a-f]{64})", line))
        ))
        if not hashes:
            fail(f"lock dependency has no SHA-256: {requirement}")
        semantics[key] = (specifiers[0].version, hashes)
    return semantics


def check_lock_regeneration() -> None:
    uv = Path(sys.executable).with_name("uv")
    if not uv.is_file():
        fail("uv is not installed in the locked environment")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "requirements-lock.txt"
        result = subprocess.run(
            [
                str(uv), "pip", "compile", "requirements-lock.in",
                "--constraint", "requirements-lock.txt",
                "--python", (ROOT / ".python-version").read_text().strip(),
                "--generate-hashes", "--universal", "--output-file", str(output),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode:
            print(result.stdout)
            fail("uv could not regenerate the dependency lock")
        if lock_semantics(LOCK) != lock_semantics(output):
            fail("requirements-lock.txt is stale; regenerate it with uv pip compile")


def main() -> None:
    expected_python = (ROOT / ".python-version").read_text().strip()
    actual_python = ".".join(map(str, sys.version_info[:3]))
    if actual_python != expected_python:
        fail(f"Python {actual_python} != locked {expected_python}")
    direct = direct_requirements()
    locked, missing_hashes = lock_requirements()
    if missing_hashes:
        fail(f"lock entries are missing hashes: {missing_hashes}")
    for name, version in direct.items():
        if locked.get(name) != version:
            fail(f"direct dependency differs from lock: {name} {version} != {locked.get(name)}")
    installed = {
        canonicalize_name(distribution.metadata["Name"]): distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    mismatches = {
        name: {"expected": version, "actual": installed.get(name)}
        for name, version in locked.items()
        if installed.get(name) != version
    }
    if mismatches:
        fail(f"installed environment differs from lock: {mismatches}")
    extras = sorted(set(installed) - set(locked))
    if extras:
        fail(f"installed environment contains unlocked packages: {extras}")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        print(result.stdout)
        fail("pip check failed")
    check_lock_regeneration()
    print(
        f"analysis environment passed: python={actual_python} "
        f"active_packages={len(locked)} hashes=complete lock=self-consistent"
    )


if __name__ == "__main__":
    main()