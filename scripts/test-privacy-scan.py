#!/usr/bin/env python3
"""Regression tests for privacy-scan secret-token boundaries."""

from __future__ import annotations

import importlib.util
import gzip
import tarfile
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("privacy_scan", REPO / "scripts" / "privacy-scan.py")
assert SPEC and SPEC.loader
privacy_scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(privacy_scan)


def scan(text: str) -> list[tuple[str, int, str]]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture.md"
        path.write_text(text)
        secrets, _ = privacy_scan.scan_file(path)
        return secrets


assert scan("run: timeout-risk-clean-20260704-210054\n") == []
assert scan("historical: prefixsk-abcdefghijklmnopqrstuvwxyz123456\n") == []

fake_key = "sk" + "-" + "abcdefghijklmnopqrstuvwxyz123456"
hits = scan(f"token: {fake_key}\n")
assert len(hits) == 1
assert hits[0][0] == "openai-style-key"

assert scan("Authorization: Bearer cloudflare_api_token\n") == []
assert scan("Authorization: Bearer EXAMPLE_BEARER_TOKEN_DO_NOT_USE.\n") == []
fake_bearer = "abcdefghijklmnop" + "qrstuvwxyz123456"
bearer_hits = scan(f"Authorization: Bearer {fake_bearer}\n")
assert bearer_hits and bearer_hits[0][0] == "bearer-token"
for embedded in ("example", "REDACTED", "cloudflare_api_token"):
    hostile_bearer = "abcdefghijklmnop" + embedded + "qrstuvwxyz123456"
    embedded_hits = scan(f"Authorization: Bearer {hostile_bearer}\n")
    assert embedded_hits and embedded_hits[0][0] == "bearer-token"

for embedded in ("example", "REDACTED"):
    hostile_openai = "sk" + "-" + "abcdefghijklmnop" + embedded + "qrstuvwxyz123456"
    embedded_hits = scan(f"token: {hostile_openai}\n")
    assert embedded_hits and embedded_hits[0][0] == "openai-style-key"

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "judged.fixture.jsonl.gz"
    with gzip.open(path, "wt") as handle:
        handle.write(f"token: {fake_key}\n")
    secrets, _ = privacy_scan.scan_file(path)
assert secrets and secrets[0][0] == "openai-style-key"

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    member = root / "answer.txt"
    member.write_text(f"token: {fake_key}\n")
    path = root / "outputs.fixture.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        archive.add(member, arcname="outputs/answer.txt")
    secrets, _ = privacy_scan.scan_file(path)
assert secrets and secrets[0][0] == "openai-style-key"
assert secrets[0][1] == "outputs/answer.txt:1"

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "corrupt.tar.gz"
    path.write_bytes(b"not a gzip-compressed tar archive")
    secrets, _ = privacy_scan.scan_file(path)
assert secrets == [("archive-read-error", "unreadable", "ReadError")]

private_key_begin = "-----BEGIN " + "PRIVATE KEY-----"
private_key_end = "-----END " + "PRIVATE KEY-----"
ssh_private_key_begin = "-----BEGIN SSH " + "PRIVATE KEY-----"
ssh_private_key_end = "-----END SSH " + "PRIVATE KEY-----"
assert scan(f"{private_key_begin}\n...\n{private_key_end}\n") == []
assert scan(f"{private_key_begin}{private_key_end}\n") == []
same_line_key_hits = scan(f"{private_key_begin}MIIEvQIBADANBgkqhkiG9w0BAQEFAASC{private_key_end}\n")
assert same_line_key_hits and same_line_key_hits[0][0] == "private-key"
assert scan(
    f'{{"completion":"{ssh_private_key_begin}\\n\\n{ssh_private_key_end}"}}\n'
    '{"next":"ordinary evidence must not become key material"}\n'
) == []
escaped_key_hits = scan(
    f'{{"completion":"{ssh_private_key_begin}\\n'
    'MIIEvQIBADANBgkqhkiG9w0BAQEFAASC\\n'
    f'{ssh_private_key_end}"}}\n'
)
assert escaped_key_hits and escaped_key_hits[0][0] == "private-key"
private_key_hits = scan(
    f"{private_key_begin}\n"
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n"
    f"{private_key_end}\n"
)
assert private_key_hits and private_key_hits[0][0] == "private-key"

with tempfile.TemporaryDirectory() as directory:
    original_repo = privacy_scan.REPO
    try:
        privacy_scan.REPO = Path(directory)
        evidence = privacy_scan.REPO / "data" / "completed-runs" / "run-bundle" / "raw" / "results.jsonl.gz"
        evidence.parent.mkdir(parents=True)
        with gzip.open(evidence, "wt") as handle:
            handle.write('{"completion":"fixture"}\n')
        assert evidence in privacy_scan.iter_files()
    finally:
        privacy_scan.REPO = original_repo

print("privacy scan tests passed")