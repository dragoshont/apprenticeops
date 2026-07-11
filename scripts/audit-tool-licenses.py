#!/usr/bin/env python3
"""Fail closed when locked analysis/release tools lack usable license metadata."""

from __future__ import annotations

import importlib.metadata
import json
import re
from pathlib import Path

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
PERMITTED = (
    "APACHE", "BSD", "GPL", "HPND", "ISC", "MIT", "MPL", "MOZILLA",
    "PSF", "PYTHON SOFTWARE FOUNDATION", "UNLICENSE", "ZLIB",
)
LOAD_BEARING = {
    "mlcroissant": ("APACHE",),
    "pillow": ("MIT-CMU",),
    "uv": ("APACHE", "MIT"),
}
IMMUTABLE_GITHUB_LICENSE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/blob/[0-9a-f]{40}/[^?#]+$"
)


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def locked_requirements() -> dict[str, Requirement]:
    requirements = {}
    for raw in (ROOT / "requirements-lock.txt").read_text().splitlines():
        if raw and not raw[0].isspace() and not raw.startswith("#"):
            requirement = Requirement(raw.removesuffix("\\").strip())
            name = canonicalize_name(requirement.name)
            if name in requirements:
                fail(f"duplicate package in universal lock: {name}")
            requirements[name] = requirement
    return requirements


def exact_version(requirement: Requirement) -> str:
    specifiers = list(requirement.specifier)
    if len(specifiers) != 1 or specifiers[0].operator != "==":
        fail(f"universal lock dependency is not exact: {requirement}")
    return specifiers[0].version


def license_signals(distribution) -> list[str]:
    metadata = distribution.metadata
    signals = []
    expression = metadata.get("License-Expression")
    if expression and expression.strip().upper() != "UNKNOWN":
        signals.append(expression.strip())
    signals.extend(
        value.removeprefix("License :: ").strip()
        for value in metadata.get_all("Classifier", [])
        if value.startswith("License :: ")
    )
    if not signals:
        value = metadata.get("License")
        if value and value.strip() and value.strip().upper() != "UNKNOWN":
            signals.append(value.strip())
    return signals


def require_immutable_license_source(source: object, name: str) -> None:
    if not IMMUTABLE_GITHUB_LICENSE.fullmatch(str(source or "")):
        fail(f"license source is not pinned to an immutable Git commit: {name}")


def main() -> None:
    policy = json.loads((ROOT / "data/tool-license-policy.json").read_text())
    universal = locked_requirements()
    active_names = {
        name for name, requirement in universal.items()
        if requirement.marker is None or Marker(str(requirement.marker)).evaluate()
    }
    marker_versions = {
        name: exact_version(requirement)
        for name, requirement in universal.items()
        if requirement.marker is not None
    }
    overrides = {
        canonicalize_name(name): value
        for name, value in (policy.get("metadata_overrides") or {}).items()
    }
    policy_tools = {
        canonicalize_name(name): value
        for name, value in (policy.get("load_bearing_tools") or {}).items()
    }
    if set(policy_tools) != set(LOAD_BEARING):
        fail("tool-license policy and load-bearing audit set differ")
    for name, value in policy_tools.items():
        sources = value.get("sources") or [value.get("source")]
        if not sources:
            fail(f"load-bearing tool has no license sources: {name}")
        for source in sources:
            require_immutable_license_source(source, name)
        if not value.get("license"):
            fail(f"load-bearing tool has no declared license: {name}")
    marker_policy = {
        canonicalize_name(name): value
        for name, value in (policy.get("universal_marker_dependencies") or {}).items()
    }
    if set(marker_policy) != set(marker_versions):
        fail(
            "universal marker license policy differs from lock: "
            f"{sorted(set(marker_policy) ^ set(marker_versions))}"
        )
    for name, value in marker_policy.items():
        if value.get("version") != marker_versions[name]:
            fail(f"marker-gated dependency version differs from lock: {name}")
        expected_metadata_source = (
            f"https://pypi.org/pypi/{name}/{marker_versions[name]}/json"
        )
        if value.get("metadata_source") != expected_metadata_source:
            fail(f"marker-gated dependency metadata source differs from lock: {name}")
        sources = (value.get("metadata_source"), value.get("license_source"))
        if any(not str(source or "").startswith("https://") for source in sources):
            fail(f"marker-gated dependency has incomplete license evidence: {name}")
        require_immutable_license_source(value.get("license_source"), name)
        license_name = str(value.get("license") or "")
        if not any(token in license_name.upper() for token in PERMITTED):
            fail(f"marker-gated dependency license is not permitted: {name}")
    if active_names | set(marker_policy) != set(universal):
        fail("universal lock contains packages without license coverage")
    installed = {
        canonicalize_name(distribution.metadata["Name"]): distribution
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    missing = sorted(active_names - set(installed))
    if missing:
        fail(f"locked packages are not installed: {missing}")
    summary = {}
    resolved_signals = {}
    for name in sorted(active_names):
        distribution = installed[name]
        signals = license_signals(distribution)
        if not signals and name in overrides:
            override = overrides[name]
            require_immutable_license_source(override.get("source"), name)
            signals = [str(override.get("license") or "")]
        if not signals:
            fail(f"locked package has no license metadata: {name}")
        joined = "\n".join(signals).upper()
        if not any(token in joined for token in PERMITTED):
            fail(f"locked package license is not in the permitted policy: {name}")
        resolved_signals[name] = signals
        summary[name] = {
            "license": signals[0].splitlines()[0][:160],
            "version": distribution.version,
        }
    for name, tokens in LOAD_BEARING.items():
        joined = "\n".join(resolved_signals[name]).upper()
        if not all(token in joined for token in tokens):
            fail(f"load-bearing tool license changed: {name}")
    print(
        "dependency license audit passed: "
        f"universal_packages={len(universal)} active_packages={len(summary)} "
        f"marker_policy_packages={len(marker_policy)} "
        f"load_bearing={','.join(sorted(LOAD_BEARING))}"
    )


if __name__ == "__main__":
    main()