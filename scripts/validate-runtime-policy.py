#!/usr/bin/env python3
"""Validate ApprenticeOps runtime policy: Ollama service, llama.cpp experiments."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
POLICY = REPO / "data" / "runtime-policy.json"
LOCK = REPO / "data" / "models.lock.jsonl"


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def main() -> None:
    policy = json.loads(POLICY.read_text())
    if policy.get("service_runtime") != "ollama":
        fail("service_runtime must remain ollama")
    if policy.get("experiment_runtime") != "llama_cpp":
        fail("experiment_runtime must be llama_cpp")
    if policy.get("legacy_snapshot_runtime") != "ollama":
        fail("legacy_snapshot_runtime must remain ollama")
    if policy.get("runner_adapter_status") not in {"planned", "implemented"}:
        fail("runner_adapter_status must be planned or implemented")
    if policy.get("runner_adapter_status") == "implemented" and policy.get("adapter_kind") != "llama_cpp_subprocess_direct_gguf":
        fail("implemented runner adapter must declare adapter_kind=llama_cpp_subprocess_direct_gguf")

    rows = [json.loads(line) for line in LOCK.read_text().splitlines() if line.strip()]
    included = [row for row in rows if row["included"]]
    direct = [row for row in included if row.get("llama_cpp_status") == "direct_gguf"]
    if not direct:
        fail("at least one included row must be direct_gguf for llama.cpp validation")
    bad_direct = [row["model_id"] for row in direct if "llama.cpp" not in row.get("runtime_options", [])]
    if bad_direct:
        fail(f"direct_gguf rows missing llama.cpp runtime option: {bad_direct[:5]}")

    print(
        "runtime policy validation passed: "
        f"service={policy['service_runtime']} experiment={policy['experiment_runtime']} "
        f"legacy={policy['legacy_snapshot_runtime']} direct_gguf={len(direct)} "
        f"adapter={policy['runner_adapter_status']} kind={policy.get('adapter_kind')}"
    )


if __name__ == "__main__":
    main()
