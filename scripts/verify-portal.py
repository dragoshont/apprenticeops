#!/usr/bin/env python3
"""Verify local or deployed ApprenticeOps portal truth and provenance."""
from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROUTE_REQUIREMENTS = {
    "index.html": [
        "7 of 24 controlled models are three-axis Pareto-optimal",
        "quality-safety front contains 2",
        "Evidence lock",
    ],
    "paper.html": [
        "7 of 24 models",
        "quality-safety front contains 2 models",
        "We withdraw an earlier 12-of-94 three-axis front",
        "Evidence lock",
        "Deployed build",
    ],
    "wave_analysis.html": [
        "controlled three-axis front contains 7 of 24 models",
        "former 12-of-94 three-axis front is withdrawn",
    ],
    "judge_comparison.html": ["8,909"],
    "reviewer.html": ["controlled sovereign selection", "7 of 24"],
    "reviewers.html": ["7 of 24", "2 of 94", "n=120", "Evidence lock"],
    "research-updates.html": [
        "Candidate evidence, not paper claims",
        "zero promotions",
        "42 immutable source versions",
    ],
}

FORBIDDEN_ACTIVE_CLAIMS = [
    "12 of 94 models are Pareto-optimal",
    "other 82 are dominated",
    "CPU-only, ≤ 5 GB",
    "CIs are nowhere near overlapping",
    "difficulty is validated empirically",
    "full 12-of-94 Pareto front all reproduced exactly",
    "n=60 safety arm",
]

SEARCHABLE_PAGES = {
    "index.html",
    "paper.html",
    "reviewers.html",
    "research-updates.html",
}
NON_SEARCHABLE_NOTEBOOKS = {
    "wave_analysis.html",
    "judge_comparison.html",
    "reviewer.html",
}
STATIC_BADGE_ROUTES = {
    "index.html",
    "paper.html",
    "reviewers.html",
    "research-updates.html",
}
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")


class PortalVerificationError(RuntimeError):
    """Raised when rendered or deployed portal truth is invalid."""


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored_depth:
            self.parts.append(data)


class BuildBadgeExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.badges: list[str] = []
        self.current: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a" and dict(attrs).get("data-portal-build") == "commit":
            if self.current is not None:
                raise PortalVerificationError("nested static build badges are invalid")
            self.current = []

    def handle_data(self, data: str) -> None:
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current is not None:
            self.badges.append(" ".join("".join(self.current).split()))
            self.current = None


def visible_text(payload: bytes) -> str:
    parser = TextExtractor()
    parser.feed(payload.decode("utf-8", errors="replace"))
    text = unescape(" ".join(parser.parts))
    return " ".join(unicodedata.normalize("NFKC", text).split())


def static_build_badges(payload: bytes) -> list[str]:
    parser = BuildBadgeExtractor()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser.badges


class LocalSource:
    def __init__(self, root: Path) -> None:
        self.root = root

    def read(self, route: str) -> bytes:
        path = self.root / route
        if not path.is_file():
            raise PortalVerificationError(f"missing portal artifact: {path}")
        return path.read_bytes()


class RemoteSource:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/") + "/"

    def read(self, route: str) -> bytes:
        request = Request(
            urljoin(self.base_url, route),
            headers={"User-Agent": "ApprenticeOps-Portal-Verification/1"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise PortalVerificationError(
                        f"{route}: unexpected HTTP status {response.status}"
                    )
                return response.read()
        except (HTTPError, URLError) as exc:
            raise PortalVerificationError(f"{route}: request failed: {exc}") from exc


def verify_build(payload: bytes, expected_commit: str) -> None:
    try:
        build = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PortalVerificationError("build.json is not valid JSON") from exc
    expected = {
        "schema": "apprenticeops.portal-build.v1",
        "analysis_schema_version": 1,
        "source_id": "paper-94-model-corrected-v1",
        "claim_status": "locked",
        "evidence_corrected_at": "2026-07-10",
        "breadth_model_count": 94,
        "breadth_quality_safety_pareto_count": 2,
        "controlled_model_count": 24,
        "controlled_three_axis_pareto_count": 7,
        "energy_cross_batch_comparison_allowed": False,
        "commit": expected_commit,
    }
    for key, value in expected.items():
        if build.get(key) != value:
            raise PortalVerificationError(
                f"build.json {key}={build.get(key)!r}; expected {value!r}"
            )


def verify_search(payload: bytes, expected_commit: str) -> None:
    try:
        records = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PortalVerificationError("search.json is not valid JSON") from exc
    if not isinstance(records, list):
        raise PortalVerificationError("search.json must contain a list")
    pages = {str(record.get("href", "")).split("#", 1)[0] for record in records}
    missing = SEARCHABLE_PAGES - pages
    leaked = NON_SEARCHABLE_NOTEBOOKS & pages
    if missing:
        raise PortalVerificationError(
            f"search index omits narrative pages: {sorted(missing)}"
        )
    if leaked:
        raise PortalVerificationError(
            f"search index contains code-heavy notebooks: {sorted(leaked)}"
        )
    if any("local render" in str(record.get("text", "")) for record in records):
        raise PortalVerificationError("search index contains a stale local-render badge")
    expected_badge = expected_commit[:7]
    index_text = " ".join(
        str(record.get("text", ""))
        for record in records
        if str(record.get("href", "")).split("#", 1)[0] == "index.html"
    )
    if expected_badge not in index_text:
        raise PortalVerificationError(
            f"search index omits stamped build identity {expected_badge}"
        )


def verify_once(source: LocalSource | RemoteSource, expected_commit: str) -> None:
    if not SHA_PATTERN.fullmatch(expected_commit):
        raise PortalVerificationError("expected commit must be a full Git SHA")

    combined: list[str] = []
    for route, requirements in ROUTE_REQUIREMENTS.items():
        payload = source.read(route)
        text = visible_text(payload)
        combined.append(text)
        for phrase in requirements:
            normalized = " ".join(unicodedata.normalize("NFKC", phrase).split())
            if normalized.casefold() not in text.casefold():
                raise PortalVerificationError(
                    f"{route}: missing required portal truth: {phrase}"
                )
        if route in STATIC_BADGE_ROUTES:
            badges = static_build_badges(payload)
            expected_badge = expected_commit[:7]
            if badges != [expected_badge]:
                raise PortalVerificationError(
                    f"{route}: static build badge {badges!r}; expected {[expected_badge]!r}"
                )

    all_text = " ".join(combined)
    for forbidden in FORBIDDEN_ACTIVE_CLAIMS:
        normalized = " ".join(unicodedata.normalize("NFKC", forbidden).split())
        if normalized.casefold() in all_text.casefold():
            raise PortalVerificationError(
                f"portal contains withdrawn active claim: {forbidden}"
            )

    pdf = source.read("paper.pdf")
    if not pdf.startswith(b"%PDF"):
        raise PortalVerificationError("paper.pdf is missing or not a PDF")
    verify_build(source.read("build.json"), expected_commit)
    verify_search(source.read("search.json"), expected_commit)


def verify_with_retries(
    source: LocalSource | RemoteSource,
    expected_commit: str,
    attempts: int,
    delay_seconds: float,
) -> None:
    if attempts < 1:
        raise PortalVerificationError("attempts must be at least 1")
    last_error: PortalVerificationError | None = None
    for attempt in range(1, attempts + 1):
        try:
            verify_once(source, expected_commit)
            return
        except PortalVerificationError as exc:
            last_error = exc
            if attempt == attempts:
                break
            print(f"portal verification attempt {attempt}/{attempts} failed: {exc}")
            time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def main() -> None:
    parser = argparse.ArgumentParser()
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument("--site-dir", type=Path)
    location.add_argument("--base-url")
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.0)
    args = parser.parse_args()

    source: LocalSource | RemoteSource
    if args.site_dir:
        source = LocalSource(args.site_dir)
    else:
        source = RemoteSource(args.base_url)
    verify_with_retries(source, args.expected_commit, args.attempts, args.delay)
    print(
        "portal verification passed: "
        f"routes={len(ROUTE_REQUIREMENTS)} commit={args.expected_commit}"
    )


if __name__ == "__main__":
    main()
