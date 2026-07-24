#!/usr/bin/env python3
"""Adversarial tests for ApprenticeOps portal provenance and truth gates."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


writer = load_module("write_portal_build", "write-portal-build.py")
verifier = load_module("verify_portal", "verify-portal.py")


def canonical_summary() -> dict:
    return {
        "analysis_schema_version": 1,
        "source_id": "paper-94-model-corrected-v1",
        "claim_status": "locked",
        "breadth_model_count": 94,
        "breadth_quality_safety_pareto_count": 2,
        "controlled_model_count": 24,
        "controlled_three_axis_pareto_count": 7,
        "energy_cross_batch_comparison_allowed": False,
    }


def build_fixture(root: Path) -> None:
    for route, phrases in verifier.ROUTE_REQUIREMENTS.items():
        body = " ".join(phrases)
        if route in verifier.STATIC_BADGE_ROUTES:
            body += (
                ' <a href="build.json" data-portal-build="commit">'
                + COMMIT[:7]
                + "</a>"
            )
        (root / route).write_text(f"<html><body>{body}</body></html>")
    (root / "paper.pdf").write_bytes(b"%PDF-1.7\nfixture")
    build = writer.build_payload(
        canonical_summary(), COMMIT, "2026-07-14T00:00:00Z", None
    )
    (root / "build.json").write_text(json.dumps(build))
    search = [
        {
            "href": page,
            "title": page,
            "text": "narrative evidence " + (COMMIT[:7] if page == "index.html" else ""),
        }
        for page in sorted(verifier.SEARCHABLE_PAGES)
    ]
    (root / "search.json").write_text(json.dumps(search))


def rendered_paper_fixture(root: Path) -> None:
    (root / "paper.html").write_text(
        "<html><body><div class=\"callout-note\">Draft</div>"
        + writer.PAPER_DOWNLOAD_ANCHOR
        + " — read it.</p></body></html>"
    )


def expect_rejected(root: Path, message: str) -> None:
    try:
        verifier.verify_once(verifier.LocalSource(root), COMMIT)
    except verifier.PortalVerificationError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"portal attack unexpectedly passed: {message}")


def main() -> None:
    payload = writer.build_payload(
        canonical_summary(), COMMIT, "2026-07-14T00:00:00Z", None
    )
    assert payload["controlled_three_axis_pareto_count"] == 7
    assert payload["breadth_quality_safety_pareto_count"] == 2

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rendered_paper_fixture(root)
        writer.inject_paper_evidence_lock(root, payload)
        paper = (root / "paper.html").read_text()
        assert paper.count(writer.PAPER_LOCK_START) == 1
        assert "Evidence lock:" in paper and COMMIT[:7] in paper
        writer.inject_paper_evidence_lock(root, {**payload, "commit": "c" * 40})
        paper = (root / "paper.html").read_text()
        assert paper.count(writer.PAPER_LOCK_START) == 1
        assert ("c" * 7) in paper and COMMIT[:7] not in paper

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for route in writer.NARRATIVE_ROUTES:
            (root / route).write_text(
                '<a href="build.json" data-portal-build="commit">local render</a>'
            )
        writer.stamp_static_build_badges(root, payload)
        for route in writer.NARRATIVE_ROUTES:
            assert COMMIT[:7] in (root / route).read_text()

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "search.json").write_text(
            json.dumps([{"href": "index.html", "text": "Deployed build: local render"}])
        )
        writer.stamp_search_build_badges(root, payload)
        assert COMMIT[:7] in (root / "search.json").read_text()
        assert "local render" not in (root / "search.json").read_text()

    try:
        writer.build_payload(
            {**canonical_summary(), "energy_cross_batch_comparison_allowed": True},
            COMMIT,
            "2026-07-14T00:00:00Z",
            None,
        )
    except writer.PortalBuildError as exc:
        assert "forbid cross-batch" in str(exc)
    else:
        raise AssertionError("cross-batch energy manifest unexpectedly passed")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        build_fixture(root)
        verifier.verify_once(verifier.LocalSource(root), COMMIT)

        index = root / "index.html"
        original = index.read_text()
        index.write_text(original + " 12 of 94 models are Pareto-optimal")
        expect_rejected(root, "withdrawn active claim")
        index.write_text(original)

        search = json.loads((root / "search.json").read_text())
        search.append({"href": "reviewer.html#q1", "title": "code", "text": "import pandas"})
        (root / "search.json").write_text(json.dumps(search))
        expect_rejected(root, "code-heavy notebooks")
        build_fixture(root)

        build = json.loads((root / "build.json").read_text())
        build["commit"] = "b" * 40
        (root / "build.json").write_text(json.dumps(build))
        expect_rejected(root, "build.json commit")

        build_fixture(root)
        build = json.loads((root / "build.json").read_text())
        build["source_id"] = "stale-source"
        (root / "build.json").write_text(json.dumps(build))
        expect_rejected(root, "build.json source_id")

        build_fixture(root)
        paper = root / "paper.html"
        paper.write_text(paper.read_text().replace("Evidence lock", "Evidence status"))
        expect_rejected(root, "missing required portal truth: Evidence lock")

        build_fixture(root)
        index = root / "index.html"
        index.write_text(index.read_text().replace(COMMIT[:7], "d" * 7, 1))
        expect_rejected(root, "static build badge")

        build_fixture(root)
        search = json.loads((root / "search.json").read_text())
        search[0]["text"] = "Deployed build: local render"
        (root / "search.json").write_text(json.dumps(search))
        expect_rejected(root, "stale local-render badge")

    print("portal tests passed: 11")


if __name__ == "__main__":
    main()
