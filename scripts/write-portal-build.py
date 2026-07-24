#!/usr/bin/env python3
"""Write machine-readable provenance for the rendered ApprenticeOps portal."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from html import escape
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
SOURCE_ID = "paper-94-model-corrected-v1"
EVIDENCE_CORRECTED_AT = "2026-07-10"
PAPER_LOCK_START = "<!-- apprenticeops-paper-evidence-lock:start -->"
PAPER_LOCK_END = "<!-- apprenticeops-paper-evidence-lock:end -->"
PAPER_DOWNLOAD_ANCHOR = (
    '<p><strong><a href="paper.pdf">Download this paper as a PDF</a></strong>'
)
NARRATIVE_ROUTES = (
    "index.html",
    "paper.html",
    "reviewers.html",
    "research-updates.html",
)
BUILD_BADGE_PATTERN = re.compile(
    r"(<a\b[^>]*\bdata-portal-build=(?:\"commit\"|'commit')[^>]*>)(.*?)(</a>)",
    re.S,
)


class PortalBuildError(ValueError):
    """Raised when portal build provenance is incomplete or inconsistent."""


def git_commit(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def validate_timestamp(value: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PortalBuildError(f"built_at must be an ISO-8601 timestamp: {value}") from exc
    return value


def build_payload(
    summary: dict,
    commit: str,
    built_at: str,
    workflow_run_url: str | None = None,
) -> dict:
    if not SHA_PATTERN.fullmatch(commit):
        raise PortalBuildError("commit must be a full 40-character lowercase Git SHA")
    if summary.get("analysis_schema_version") != 1:
        raise PortalBuildError("portal requires canonical analysis schema v1")
    if summary.get("source_id") != SOURCE_ID:
        raise PortalBuildError(f"portal requires canonical source_id {SOURCE_ID}")
    if summary.get("claim_status") != "locked":
        raise PortalBuildError("portal requires a locked analysis summary")
    if summary.get("energy_cross_batch_comparison_allowed") is not False:
        raise PortalBuildError("portal must forbid cross-batch energy comparison")

    required = {
        "breadth_model_count": 94,
        "breadth_quality_safety_pareto_count": 2,
        "controlled_model_count": 24,
        "controlled_three_axis_pareto_count": 7,
    }
    for key, expected in required.items():
        if summary.get(key) != expected:
            raise PortalBuildError(
                f"canonical summary {key}={summary.get(key)!r}; expected {expected!r}"
            )

    payload = {
        "schema": "apprenticeops.portal-build.v1",
        "analysis_schema_version": summary["analysis_schema_version"],
        "source_id": summary["source_id"],
        "claim_status": summary["claim_status"],
        "evidence_corrected_at": EVIDENCE_CORRECTED_AT,
        "breadth_model_count": summary["breadth_model_count"],
        "breadth_quality_safety_pareto_count": summary[
            "breadth_quality_safety_pareto_count"
        ],
        "controlled_model_count": summary["controlled_model_count"],
        "controlled_three_axis_pareto_count": summary[
            "controlled_three_axis_pareto_count"
        ],
        "energy_cross_batch_comparison_allowed": summary[
            "energy_cross_batch_comparison_allowed"
        ],
        "commit": commit,
        "built_at": validate_timestamp(built_at),
        "workflow_run_url": workflow_run_url,
    }
    return payload


def paper_evidence_lock(payload: dict) -> str:
    commit = escape(str(payload["commit"]))
    corrected_at = escape(str(payload["evidence_corrected_at"]))
    breadth_count = int(payload["breadth_model_count"])
    controlled_count = int(payload["controlled_model_count"])
    controlled_front = int(payload["controlled_three_axis_pareto_count"])
    breadth_front = int(payload["breadth_quality_safety_pareto_count"])
    return f"""{PAPER_LOCK_START}
<div class="evidence-lock" role="note">
<p><strong>Evidence lock:</strong> analysis schema <code>v1</code>, corrected
<strong>{corrected_at}</strong>. Public claims separate <strong>{breadth_count}-model
quality/safety breadth</strong> from <strong>{controlled_count}-model controlled
quality/safety/energy</strong>: <strong>{controlled_front} of {controlled_count}</strong>
on the controlled three-axis front and <strong>{breadth_front} of {breadth_count}</strong>
on the breadth quality-safety front. Deployed build:
<a href="build.json" data-portal-build="commit">{commit[:7]}</a>.</p>
</div>
{PAPER_LOCK_END}"""


def inject_paper_evidence_lock(site_dir: Path, payload: dict) -> Path:
    paper = site_dir / "paper.html"
    if not paper.is_file():
        raise PortalBuildError(f"rendered paper is missing: {paper}")
    html = paper.read_text()
    block = paper_evidence_lock(payload)
    if PAPER_LOCK_START in html or PAPER_LOCK_END in html:
        pattern = re.compile(
            re.escape(PAPER_LOCK_START) + r".*?" + re.escape(PAPER_LOCK_END),
            re.S,
        )
        html, replacements = pattern.subn(block, html)
        if replacements != 1:
            raise PortalBuildError(
                "rendered paper has an ambiguous evidence-lock marker sequence"
            )
    else:
        if html.count(PAPER_DOWNLOAD_ANCHOR) != 1:
            raise PortalBuildError(
                "rendered paper must contain exactly one download-link anchor"
            )
        html = html.replace(PAPER_DOWNLOAD_ANCHOR, block + "\n" + PAPER_DOWNLOAD_ANCHOR)
    temporary = paper.with_suffix(".html.tmp")
    temporary.write_text(html)
    temporary.replace(paper)
    return paper


def stamp_static_build_badges(site_dir: Path, payload: dict) -> None:
    short_commit = str(payload["commit"])[:7]
    for route in NARRATIVE_ROUTES:
        path = site_dir / route
        if not path.is_file():
            raise PortalBuildError(f"rendered narrative route is missing: {path}")
        html = path.read_text()
        html, replacements = BUILD_BADGE_PATTERN.subn(
            lambda match: match.group(1) + short_commit + match.group(3),
            html,
        )
        if replacements != 1:
            raise PortalBuildError(
                f"{route} must contain exactly one static build badge; found {replacements}"
            )
        temporary = path.with_suffix(".html.tmp")
        temporary.write_text(html)
        temporary.replace(path)


def stamp_search_build_badges(site_dir: Path, payload: dict) -> None:
    search_path = site_dir / "search.json"
    if not search_path.is_file():
        raise PortalBuildError(f"rendered search index is missing: {search_path}")
    try:
        records = json.loads(search_path.read_text())
    except json.JSONDecodeError as exc:
        raise PortalBuildError("rendered search index is not valid JSON") from exc
    if not isinstance(records, list):
        raise PortalBuildError("rendered search index must contain a list")
    short_commit = str(payload["commit"])[:7]
    for record in records:
        if isinstance(record, dict) and isinstance(record.get("text"), str):
            record["text"] = record["text"].replace("local render", short_commit)
    temporary = search_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False) + "\n")
    temporary.replace(search_path)


def write_manifest(
    repo: Path,
    site_dir: Path,
    commit: str,
    built_at: str,
    workflow_run_url: str | None,
) -> Path:
    summary = json.loads((repo / "data/site/summary.json").read_text())
    payload = build_payload(summary, commit, built_at, workflow_run_url)
    site_dir.mkdir(parents=True, exist_ok=True)
    destination = site_dir / "build.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(destination)
    inject_paper_evidence_lock(site_dir, payload)
    stamp_static_build_badges(site_dir, payload)
    stamp_search_build_badges(site_dir, payload)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", type=Path, default=REPO / "docs/analysis/_site")
    parser.add_argument("--commit", default=None)
    parser.add_argument("--built-at", default=None)
    parser.add_argument("--workflow-run-url", default=None)
    args = parser.parse_args()

    commit = args.commit or git_commit(REPO)
    built_at = args.built_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    destination = write_manifest(
        REPO,
        args.site_dir,
        commit,
        built_at,
        args.workflow_run_url,
    )
    print(f"portal build provenance written: {destination} commit={commit}")


if __name__ == "__main__":
    main()
