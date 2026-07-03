#!/usr/bin/env python3
"""Build data/models.lock.jsonl from the roster and committed snapshot metadata."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROSTER = REPO / "data" / "models.txt"
SNAPSHOT = REPO / "data" / "snapshots" / "results_snapshot.csv"
OUT = REPO / "data" / "models.lock.jsonl"

SPECIAL_PARAMS_B = {
    "phi4-mini": 3.8,
    "phi4-mini-reasoning": 3.8,
    "granite4:micro": 3.4,
    "granite4:micro-h": 3.4,
    "granite4:tiny-h": 6.9,
    "command-r7b:latest": 7.0,
}

PUBLISHER_HINTS = [
    ("qwen", "Alibaba", "Qwen"),
    ("llama", "Meta", "Llama"),
    ("granite", "IBM", "Granite"),
    ("smollm", "Hugging Face", "SmolLM"),
    ("gemma", "Google", "Gemma"),
    ("deepseek", "DeepSeek", "DeepSeek"),
    ("mistral", "Mistral AI", "Mistral"),
    ("phi", "Microsoft", "Phi"),
    ("falcon", "TII", "Falcon"),
    ("nemotron", "NVIDIA", "Nemotron"),
    ("exaone", "LG AI Research", "EXAONE"),
    ("stablelm", "Stability AI", "StableLM"),
    ("codegemma", "Google", "CodeGemma"),
    ("starcoder", "BigCode", "StarCoder"),
    ("opencoder", "OpenCoder", "OpenCoder"),
    ("lfm", "Liquid AI", "LFM"),
    ("olmo", "Allen AI", "OLMo"),
    ("internlm", "Shanghai AI Lab", "InternLM"),
    ("aya", "Cohere", "Aya"),
    ("cogito", "Deep Cogito", "Cogito"),
]


def load_roster() -> list[tuple[str | None, str]]:
    rows: list[tuple[str | None, str]] = []
    bracket: str | None = None
    for raw in ROSTER.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "bracket:" in line:
                bracket = line.split("bracket:", 1)[1].strip()
            continue
        rows.append((bracket, line))
    return rows


def load_snapshot() -> dict[str, dict]:
    measured: dict[str, dict] = {}
    if not SNAPSHOT.exists():
        return measured
    with SNAPSHOT.open(newline="") as handle:
        for row in csv.DictReader(handle):
            measured.setdefault(row["model"], row)
    return measured


def parse_float(value: str | None) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def measured_params_b(row: dict | None) -> float | None:
    if not row:
        return None
    count = parse_float(row.get("param_count"))
    if count:
        return round(count / 1_000_000_000, 3)
    label = row.get("param_size") or ""
    return infer_params_b(label)


def infer_params_b(model_id: str) -> float | None:
    if model_id in SPECIAL_PARAMS_B:
        return SPECIAL_PARAMS_B[model_id]
    text = model_id.lower()
    patterns = [
        r"(?<![a-z0-9])([0-9]+(?:\.[0-9]+)?)([bm])(?=$|[^a-z0-9])",
        r"r([0-9]+(?:\.[0-9]+)?)b(?=$|[^a-z0-9])",
    ]
    values: list[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = float(match.group(1))
            unit = match.group(2) if len(match.groups()) > 1 else "b"
            if unit == "m":
                value = value / 1000
            values.append(value)
    if not values:
        return None
    return round(max(values), 3)


def tier_for(params_b: float | None) -> str | None:
    if params_b is None or params_b <= 0:
        return None
    if params_b <= 1:
        return "T1"
    if params_b <= 2:
        return "T2"
    if params_b <= 3:
        return "T3"
    if params_b <= 4:
        return "T4"
    if params_b <= 5:
        return "T5"
    return None


def infer_quantization(model_id: str, row: dict | None) -> str:
    if row and row.get("quant"):
        return row["quant"]
    text = model_id.upper()
    for pattern in ("Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q4_0", "Q3_K_L", "IQ4_XS", "FP16", "BF16"):
        if pattern in text:
            return pattern
    return "ollama_default_or_unknown"


def infer_publisher_family(model_id: str) -> tuple[str, str]:
    text = model_id.lower()
    for needle, publisher, family in PUBLISHER_HINTS:
        if needle in text:
            return publisher, family
    if model_id.startswith("hf.co/"):
        parts = model_id.split("/")
        if len(parts) >= 3:
            return parts[1], parts[2].split(":", 1)[0]
    return "unknown", "unknown"


def infer_training_type(model_id: str) -> str:
    text = model_id.lower()
    if "coder" in text or "code" in text or "starcoder" in text or "opencoder" in text:
        return "code"
    if "reasoning" in text or "thinking" in text or "deep" in text or "deepscaler" in text:
        return "reasoning"
    if "distill" in text:
        return "distilled"
    if "instruct" in text or "it-" in text or "-it" in text or "chat" in text or "zephyr" in text:
        return "instruct"
    return "unknown"


def infer_architecture(model_id: str, row: dict | None) -> str:
    if row and parse_float(row.get("expert_count")):
        return "moe"
    text = model_id.lower()
    if "moe" in text:
        return "moe"
    if "h1" in text or "lfm" in text or "mamba" in text:
        return "hybrid"
    return "unknown"


def build_rows() -> list[dict]:
    measured = load_snapshot()
    rows: list[dict] = []
    for roster_bracket, model_id in load_roster():
        row = measured.get(model_id)
        params_b = measured_params_b(row) or infer_params_b(model_id)
        tier = tier_for(params_b)
        included = params_b is not None and 0 < params_b <= 5
        exclusion_reason = None
        if params_b is None:
            exclusion_reason = "needs_parameter_metadata"
        elif params_b > 5:
            exclusion_reason = "above_5b_parameters"
        publisher, family = infer_publisher_family(model_id)
        size_bytes = parse_float(row.get("size_bytes") if row else None)
        artifact_size_gb = round(size_bytes / 1_000_000_000, 3) if size_bytes else None
        track = ["legacy_footprint_snapshot"] if roster_bracket == "4-5GB" else []
        if included:
            track.append("thesis_5b_candidate")
        rows.append({
            "model_id": model_id,
            "publisher": publisher,
            "family": family,
            "params_b": params_b,
            "tier": tier,
            "architecture": infer_architecture(model_id, row),
            "training_type": infer_training_type(model_id),
            "quantization": infer_quantization(model_id, row),
            "runtime": "ollama",
            "artifact_size_gb": artifact_size_gb,
            "source_url": "unknown",
            "license": "unknown",
            "ollama_digest": None,
            "gguf_sha256": None,
            "context_length": None,
            "included": included,
            "track": track,
            "exclusion_reason": exclusion_reason,
            "downloaded_at": None,
            "metadata_status": "measured" if row else ("inferred" if params_b is not None else "needs_metadata"),
            "roster_bracket": roster_bracket,
            "legacy_bracket": roster_bracket if roster_bracket == "4-5GB" else None,
            "measured_snapshot": bool(row),
            "notes": "Generated from data/models.txt; measured fields imported from data/snapshots/results_snapshot.csv when available. License/source/digest are intentionally unknown until verified.",
        })
    return rows


def main() -> None:
    rows = build_rows()
    OUT.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))
    included = sum(1 for row in rows if row["included"])
    excluded = len(rows) - included
    print(f"wrote {OUT.relative_to(REPO)} rows={len(rows)} included={included} excluded={excluded}")


if __name__ == "__main__":
    main()