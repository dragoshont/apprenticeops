#!/usr/bin/env python3
"""Validate ApprenticeOps research-radar provenance and promotion boundaries."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

TOPICS = {
    "small-models", "peft-finetuning", "distillation", "specialization",
    "quantization-compression", "efficient-reasoning", "on-device-systems",
    "agent-safety", "evaluation-statistics", "ops-domain-eval",
}
ORGANIZATIONS = {
    "Microsoft", "Apple", "Anthropic", "Google-DeepMind", "Meta", "IBM",
    "NVIDIA", "Hugging-Face", "Mistral",
}
SOURCE_FAMILIES = {
    "primary-index", "company-research", "model-code",
    "independent-reproduction", "social-lead",
}
SOURCE_TIERS = {
    "primary-paper", "company-report", "model-card", "code-artifact",
    "independent-reproduction", "social",
}
VERIFICATION = {
    "lead", "metadata-verified", "abstract-verified", "fulltext-verified",
    "reproduced",
}
REPORT_HEADINGS = (
    "Scope", "Coverage", "What Was Already Covered",
    "New, Updated, and Contradictory Evidence", "Trends and Disagreements",
    "Gaps ApprenticeOps Can Fill", "Candidate Experiments",
    "Analysis Implications", "Social / Practitioner Leads", "Negative Results",
    "Promotion Candidates", "Limitations", "Sources",
)
CANONICAL_PATHS = (
    "docs/analysis/literature-catalog.md",
    "docs/analysis/references.bib",
    "docs/PAPER.md",
    "docs/analysis/paper.qmd",
)
RADAR_FILES = {
    "queries": "queries.jsonl",
    "sources": "sources.jsonl",
    "claims": "claims.jsonl",
    "scans": "scans.jsonl",
    "promotions": "promotions.jsonl",
}
SCHEMAS = {
    "queries": "apprenticeops.radar-query.v1",
    "sources": "apprenticeops.radar-source.v1",
    "claims": "apprenticeops.radar-claim.v1",
    "scans": "apprenticeops.radar-scan.v1",
    "promotions": "apprenticeops.radar-promotion.v1",
}
REQUIRED_FIELDS = {
    "queries": {
        "schema", "scan_id", "query_id", "observed_at", "source_family",
        "organization", "topic", "query", "window_start", "window_end",
        "result_count", "selected_version_ids", "notes",
    },
    "sources": {
        "schema", "scan_id", "work_id", "version_id", "prior_version_id",
        "canonical_url", "variants", "title", "authors_or_orgs",
        "first_published", "observed_at", "revision_id", "revision_date",
        "revision_hash", "source_tier", "verification", "topics",
        "organizations", "delta_status", "update_kind",
        "changed_claim_version_ids", "relevance", "limitations", "decision",
        "promotion_state", "promoted_to",
    },
    "claims": {
        "schema", "scan_id", "claim_id", "claim_version_id", "work_id",
        "version_id", "claim_text", "evidence_scope", "status",
        "supersedes_claim_version_id", "changed_from_claim_version_id",
        "corroborating_version_ids", "contradicting_version_ids", "last_verified_at",
    },
    "scans": {
        "schema", "scan_id", "scan_date", "window_start", "window_end",
        "status", "report_path", "query_ids", "selected_version_ids",
        "claim_version_ids", "canonical_hashes", "notes",
    },
    "promotions": {
        "schema", "promotion_id", "scan_id", "version_id", "approved_by",
        "approved_at", "targets",
    },
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@#-]{0,511}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TOKEN_KEYS = re.compile(r"(?i)(token|key|secret|password|passwd|auth|cookie|session)")


class RadarError(ValueError):
    pass


def fail(message: str) -> None:
    raise RadarError(message)


def parse_date(value: object, label: str) -> dt.date:
    if not isinstance(value, str):
        fail(f"{label} must be an ISO date")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise RadarError(f"{label} must be an ISO date") from exc


def parse_timestamp(value: object, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        fail(f"{label} must be a UTC timestamp ending in Z")
    try:
        return dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RadarError(f"{label} must be a UTC timestamp ending in Z") from exc


def string_list(value: object, label: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        fail(f"{label} must be a list of non-empty strings")
    if nonempty and not value:
        fail(f"{label} must not be empty")
    if len(value) != len(set(value)):
        fail(f"{label} contains duplicates")
    return value


def identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        fail(f"{label} is not a safe identifier")
    return value


def safe_url(value: object, label: str) -> str:
    if not isinstance(value, str):
        fail(f"{label} must be an HTTPS URL")
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        fail(f"{label} must be a public HTTPS URL without credentials")
    if (
        host in {"localhost", "127.0.0.1", "::1"}
        or host.endswith((".local", ".internal", ".home", ".hont.ro"))
        or re.fullmatch(r"10\..*|192\.168\..*|172\.(1[6-9]|2\d|3[01])\..*", host)
    ):
        fail(f"{label} contains a private host")
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if TOKEN_KEYS.search(key):
            fail(f"{label} contains a credential-like query parameter")
    return value


def read_jsonl(path: Path, kind: str) -> list[dict]:
    if not path.is_file():
        fail(f"missing radar ledger: {path}")
    rows: list[dict] = []
    for line_number, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw.strip():
            fail(f"{path}:{line_number}: blank JSONL line")
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RadarError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            fail(f"{path}:{line_number}: row must be an object")
        if set(row) != REQUIRED_FIELDS[kind]:
            fail(
                f"{path}:{line_number}: fields differ: "
                f"missing={sorted(REQUIRED_FIELDS[kind] - set(row))} "
                f"extra={sorted(set(row) - REQUIRED_FIELDS[kind])}"
            )
        if row["schema"] != SCHEMAS[kind]:
            fail(f"{path}:{line_number}: unexpected schema {row['schema']!r}")
        rows.append(row)
    return rows


def unique(rows: list[dict], field: str, kind: str) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        value = identifier(row[field], f"{kind}.{field}")
        if value in indexed:
            fail(f"duplicate {kind} {field}: {value}")
        indexed[value] = row
    return indexed


def validate_query(row: dict) -> None:
    identifier(row["scan_id"], "query.scan_id")
    identifier(row["query_id"], "query.query_id")
    parse_timestamp(row["observed_at"], "query.observed_at")
    if row["source_family"] not in SOURCE_FAMILIES:
        fail(f"query source_family is invalid: {row['source_family']!r}")
    if row["organization"] not in ORGANIZATIONS | {"cross-lab", "smaller-lab"}:
        fail(f"query organization is invalid: {row['organization']!r}")
    if row["topic"] not in TOPICS:
        fail(f"query topic is invalid: {row['topic']!r}")
    if not isinstance(row["query"], str) or not row["query"].strip():
        fail("query text must not be empty")
    if any(token in row["query"].lower() for token in (".hont.ro", "192.168.", "api_key", "token=")):
        fail("query text contains private or credential-like material")
    start = parse_date(row["window_start"], "query.window_start")
    end = parse_date(row["window_end"], "query.window_end")
    if start > end:
        fail("query window_start is after window_end")
    if isinstance(row["result_count"], bool) or not isinstance(row["result_count"], int) or row["result_count"] < 0:
        fail("query result_count must be a non-negative integer")
    selected = string_list(row["selected_version_ids"], "query.selected_version_ids")
    if len(selected) > row["result_count"]:
        fail("query selected versions exceed its result count")
    if row["result_count"] == 0 and selected:
        fail("zero-result query cannot select a source version")
    if not isinstance(row["notes"], str):
        fail("query notes must be a string")
    if re.search(r"(?i)\bselect(?:ed|ion|ions)?\b", row["notes"]):
        fail("query notes must not duplicate the authoritative selected-version count")


def validate_source(row: dict) -> None:
    identifier(row["scan_id"], "source.scan_id")
    work_id = identifier(row["work_id"], "source.work_id")
    version_id = identifier(row["version_id"], "source.version_id")
    if not version_id.startswith(work_id + "@"):
        fail(f"source version_id must be versioned from work_id: {version_id}")
    if row["prior_version_id"] is not None:
        identifier(row["prior_version_id"], "source.prior_version_id")
    safe_url(row["canonical_url"], "source.canonical_url")
    for index, value in enumerate(string_list(row["variants"], "source.variants")):
        safe_url(value, f"source.variants[{index}]")
    string_list(row["authors_or_orgs"], "source.authors_or_orgs", nonempty=True)
    parse_date(row["first_published"], "source.first_published")
    parse_timestamp(row["observed_at"], "source.observed_at")
    if not isinstance(row["revision_id"], str) or not row["revision_id"]:
        fail("source revision_id must not be empty")
    parse_date(row["revision_date"], "source.revision_date")
    if row["revision_hash"] is not None and (
        not isinstance(row["revision_hash"], str) or not SHA256_PATTERN.fullmatch(row["revision_hash"])
    ):
        fail("source revision_hash must be null or SHA-256")
    version_suffix = version_id[len(work_id) + 1 :]
    if version_suffix.startswith("web-sha256-"):
        expected_hash = version_suffix.removeprefix("web-sha256-")
        if row["revision_id"] != version_suffix or row["revision_hash"] != expected_hash:
            fail("web source version, revision_id, and revision_hash must agree")
    elif version_suffix.startswith("git-"):
        if row["revision_id"] != version_suffix or row["revision_hash"] is not None:
            fail("Git source version must use its full commit as revision_id and no padded revision_hash")
    elif version_suffix.startswith("arxiv-") and row["revision_id"] != version_suffix:
        fail("arXiv source version and revision_id must agree")
    elif version_suffix.startswith("model-revision-") and row["revision_id"] != version_suffix:
        fail("model source version and revision_id must agree")
    if row["source_tier"] not in SOURCE_TIERS:
        fail(f"source tier is invalid: {row['source_tier']!r}")
    if row["verification"] not in VERIFICATION:
        fail(f"source verification is invalid: {row['verification']!r}")
    topics = set(string_list(row["topics"], "source.topics", nonempty=True))
    if not topics <= TOPICS:
        fail(f"source topics are invalid: {sorted(topics - TOPICS)}")
    string_list(row["organizations"], "source.organizations", nonempty=True)
    if row["delta_status"] not in {"already-covered", "new", "updated", "contradictory"}:
        fail(f"source delta_status is invalid: {row['delta_status']!r}")
    if row["update_kind"] not in {"none", "revision", "venue-upgrade", "retraction", "claim-change"}:
        fail(f"source update_kind is invalid: {row['update_kind']!r}")
    changed = string_list(row["changed_claim_version_ids"], "source.changed_claim_version_ids")
    if row["delta_status"] in {"updated", "contradictory"} and not changed:
        fail("updated/contradictory source must name changed claims")
    for field in ("relevance", "limitations"):
        if not isinstance(row[field], str) or not row[field].strip():
            fail(f"source {field} must not be empty")
    if row["decision"] not in {"monitor", "promote-candidate", "reject", "already-covered"}:
        fail(f"source decision is invalid: {row['decision']!r}")
    if row["promotion_state"] not in {"candidate", "approved", "promoted", "rejected"}:
        fail(f"source promotion_state is invalid: {row['promotion_state']!r}")
    if row["promoted_to"] is not None:
        string_list(row["promoted_to"], "source.promoted_to", nonempty=True)
    if row["source_tier"] == "social" and (
        row["verification"] != "lead" or row["decision"] != "monitor" or row["promotion_state"] != "candidate"
    ):
        fail("social source must remain lead/monitor/candidate")


def validate_claim(row: dict) -> None:
    identifier(row["scan_id"], "claim.scan_id")
    work_id = identifier(row["work_id"], "claim.work_id")
    version_id = identifier(row["version_id"], "claim.version_id")
    claim_id = identifier(row["claim_id"], "claim.claim_id")
    claim_version_id = identifier(row["claim_version_id"], "claim.claim_version_id")
    if not version_id.startswith(work_id + "@") or not claim_id.startswith(work_id + "#"):
        fail("claim identity does not belong to work")
    if claim_version_id != f"{claim_id}@{version_id}":
        fail("claim_version_id must be claim_id@version_id")
    for field in ("claim_text", "evidence_scope"):
        if not isinstance(row[field], str) or not row[field].strip():
            fail(f"claim {field} must not be empty")
    if row["status"] not in {"active", "superseded", "retracted", "contradicted"}:
        fail(f"claim status is invalid: {row['status']!r}")
    for field in ("supersedes_claim_version_id", "changed_from_claim_version_id"):
        if row[field] is not None:
            identifier(row[field], f"claim.{field}")
            if row[field] == claim_version_id:
                fail(f"claim {field} cannot self-reference")
    string_list(row["corroborating_version_ids"], "claim.corroborating_version_ids")
    string_list(row["contradicting_version_ids"], "claim.contradicting_version_ids")
    parse_timestamp(row["last_verified_at"], "claim.last_verified_at")


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## (.+?)\s*$", text, re.MULTILINE))
    return {
        match.group(1).strip(): text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        for index, match in enumerate(matches)
    }


def report_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines()
    if len(lines) < 3 or lines[0] != "---":
        fail(f"report lacks frontmatter: {path}")
    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise RadarError(f"report frontmatter is unterminated: {path}") from exc
    values: dict[str, str] = {}
    for raw in lines[1:end]:
        key, separator, value = raw.partition(":")
        if not separator or not key.strip() or not value.strip():
            fail(f"report frontmatter line is invalid: {raw!r}")
        values[key.strip()] = value.strip()
    return values


def canonical_clean(root: Path) -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *CANONICAL_PATHS], cwd=root
    )
    if result.returncode != 0:
        fail("radar-only validation refuses canonical literature or paper changes")


def validate_customizations(root: Path) -> None:
    skill = root / ".github/skills/literature-radar/SKILL.md"
    agent = root / ".github/agents/research-radar.agent.md"
    if not skill.is_file():
        fail("missing literature-radar skill")
    if not agent.is_file():
        fail("missing Research Radar agent")
    skill_values = report_frontmatter(skill)
    agent_values = report_frontmatter(agent)
    if skill_values.get("name") != "literature-radar":
        fail("literature-radar skill name must match its directory")
    if not skill_values.get("description"):
        fail("literature-radar skill requires a description")
    if agent_values.get("name") != '"Research Radar"':
        fail("Research Radar agent name is invalid")
    if not agent_values.get("description"):
        fail("Research Radar agent requires a description")
    if agent_values.get("user-invocable") != "true":
        fail("Research Radar agent must be user-invocable")


def detect_cycle(claims: dict[str, dict]) -> None:
    for start in claims:
        seen: set[str] = set()
        current: str | None = start
        while current is not None:
            if current in seen:
                fail(f"claim lineage cycle detected at {current}")
            seen.add(current)
            row = claims.get(current)
            if row is None:
                fail(f"claim lineage references unknown claim: {current}")
            current = row["changed_from_claim_version_id"] or row["supersedes_claim_version_id"]


def validate(root: Path, mode: str, scan_id: str | None, *, check_canon: bool = True) -> dict[str, int]:
    radar = root / "docs/analysis/research-radar"
    if not (radar / "schema.json").is_file():
        fail("missing formal research-radar schema")
    schema = json.loads((radar / "schema.json").read_text())
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("research-radar schema must use JSON Schema 2020-12")
    rows = {kind: read_jsonl(radar / filename, kind) for kind, filename in RADAR_FILES.items()}
    for row in rows["queries"]:
        validate_query(row)
    for row in rows["sources"]:
        validate_source(row)
    for row in rows["claims"]:
        validate_claim(row)

    queries = unique(rows["queries"], "query_id", "query")
    sources = unique(rows["sources"], "version_id", "source")
    claims = unique(rows["claims"], "claim_version_id", "claim")
    scans = unique(rows["scans"], "scan_id", "scan")
    promotions = unique(rows["promotions"], "promotion_id", "promotion")
    detect_cycle(claims)

    for row in rows["queries"]:
        missing = set(row["selected_version_ids"]) - set(sources)
        if missing:
            fail(f"query {row['query_id']} selects unknown source versions: {sorted(missing)}")
    for row in rows["sources"]:
        if row["prior_version_id"] is not None and row["prior_version_id"] not in sources:
            fail(f"source prior_version_id is unknown: {row['prior_version_id']}")
        missing = set(row["changed_claim_version_ids"]) - set(claims)
        if missing:
            fail(f"source changed claims are unknown: {sorted(missing)}")
    for row in rows["claims"]:
        if row["version_id"] not in sources:
            fail(f"claim source version is unknown: {row['version_id']}")
        for field in ("corroborating_version_ids", "contradicting_version_ids"):
            missing = set(row[field]) - set(sources)
            if missing:
                fail(f"claim {field} references unknown versions: {sorted(missing)}")

    for row in rows["scans"]:
        identifier(row["scan_id"], "scan.scan_id")
        scan_date = parse_date(row["scan_date"], "scan.scan_date")
        start = parse_date(row["window_start"], "scan.window_start")
        end = parse_date(row["window_end"], "scan.window_end")
        if start > end or scan_date < end:
            fail("scan dates are inconsistent")
        if row["status"] not in {"incomplete", "complete"}:
            fail("scan status is invalid")
        string_list(row["query_ids"], "scan.query_ids", nonempty=True)
        string_list(row["selected_version_ids"], "scan.selected_version_ids")
        string_list(row["claim_version_ids"], "scan.claim_version_ids")
        if not isinstance(row["canonical_hashes"], dict) or set(row["canonical_hashes"]) != set(CANONICAL_PATHS):
            fail("scan canonical_hashes must cover exact canonical paths")
        if any(not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value) for value in row["canonical_hashes"].values()):
            fail("scan canonical_hashes values must be SHA-256")
        if row["status"] == "incomplete" and row["report_path"] is not None:
            fail("incomplete scan must not publish a report")
        if row["status"] == "complete" and not isinstance(row["report_path"], str):
            fail("complete scan must name a report")

    target_ids = [scan_id] if scan_id else sorted(scans)
    if not target_ids:
        fail("no scans recorded")
    for target in target_ids:
        if target not in scans:
            fail(f"unknown scan_id: {target}")
        scan = scans[target]
        scan_queries = {key: row for key, row in queries.items() if row["scan_id"] == target}
        scan_sources = {key: row for key, row in sources.items() if row["scan_id"] == target}
        scan_claims = {key: row for key, row in claims.items() if row["scan_id"] == target}
        if set(scan["query_ids"]) != set(scan_queries):
            fail(f"scan {target} query inventory differs from ledger")
        if set(scan["selected_version_ids"]) != set(scan_sources):
            fail(f"scan {target} source inventory differs from ledger")
        if set(scan["claim_version_ids"]) != set(scan_claims):
            fail(f"scan {target} claim inventory differs from ledger")
        selected_by_queries = {
            version_id
            for query in scan_queries.values()
            for version_id in query["selected_version_ids"]
        }
        if selected_by_queries != set(scan_sources):
            fail(f"scan {target} query-selected source inventory differs from ledger")
        topics = {row["topic"] for row in scan_queries.values()}
        organizations = {row["organization"] for row in scan_queries.values()}
        families = {row["source_family"] for row in scan_queries.values()}
        if topics != TOPICS:
            fail(f"scan {target} topic coverage differs: missing={sorted(TOPICS - topics)}")
        if not ORGANIZATIONS <= organizations:
            fail(f"scan {target} organization coverage missing={sorted(ORGANIZATIONS - organizations)}")
        if families != SOURCE_FAMILIES:
            fail(f"scan {target} source-family coverage missing={sorted(SOURCE_FAMILIES - families)}")
        if mode == "scan" and scan["status"] == "incomplete":
            continue
        if scan["status"] != "complete":
            fail(f"scan {target} is not complete")
        report = root / scan["report_path"]
        if not report.is_file():
            fail(f"scan report is missing: {scan['report_path']}")
        frontmatter = report_frontmatter(report)
        if frontmatter.get("scan_id") != target:
            fail("report scan_id differs from ledger")
        if frontmatter.get("window_start") != scan["window_start"] or frontmatter.get("window_end") != scan["window_end"]:
            fail("report window differs from ledger")
        text = report.read_text()
        sections = markdown_sections(text)
        missing_headings = [heading for heading in REPORT_HEADINGS if heading not in sections]
        if missing_headings:
            fail(f"report missing headings: {missing_headings}")
        for version_id in scan_sources:
            if f"`{version_id}`" not in sections["Sources"]:
                fail(f"report Sources omits version_id: {version_id}")
        social_versions = {key for key, row in scan_sources.items() if row["source_tier"] == "social"}
        non_social = set(scan_sources) - social_versions
        for claim in scan_claims.values():
            if claim["version_id"] not in social_versions:
                continue
            if set(claim["corroborating_version_ids"]) & non_social:
                continue
            for heading, body in sections.items():
                if heading != "Social / Practitioner Leads" and f"`{claim['claim_version_id']}`" in body:
                    fail("uncorroborated social claim appears outside Social / Practitioner Leads")

    if mode in {"scan", "complete"} and check_canon:
        canonical_clean(root)
        scan_targets = [scans[target] for target in target_ids]
        for scan in scan_targets:
            for relative in CANONICAL_PATHS:
                actual = hashlib.sha256((root / relative).read_bytes()).hexdigest()
                if scan["canonical_hashes"][relative] != actual:
                    fail(f"scan {scan['scan_id']} canonical hash changed: {relative}")
    if mode == "complete":
        validate_customizations(root)
    if mode == "promotion":
        if not promotions:
            fail("promotion mode requires a human-approved promotion record")
        for source in sources.values():
            if source["promotion_state"] in {"approved", "promoted"} and not source["promoted_to"]:
                fail("approved/promoted source lacks promoted_to mapping")
    elif promotions:
        fail("radar-only validation refuses promotion records")

    return {
        "queries": len(queries), "sources": len(sources), "claims": len(claims),
        "scans": len(scans), "promotions": len(promotions),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("scan", "complete", "promotion"), nargs="?", default="scan")
    parser.add_argument("--scan-id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        counts = validate(args.root.resolve(), args.mode, args.scan_id)
    except RadarError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    print("research radar validation passed: " + " ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()