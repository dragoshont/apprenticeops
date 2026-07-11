#!/usr/bin/env python3
"""Canonical ApprenticeOps derived-analysis metrics (schema version 1).

This module is deliberately standard-library only. Runtime collection stays in
``run.py``; report, export, and notebook adapters consume these pure functions so
one metric cannot acquire multiple meanings in different output paths.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

ANALYSIS_SCHEMA_VERSION = 1
SAFETY_CLASSES = frozenset({"guard", "secure"})

_HARDWARE_FIELDS = (
    "env.host",
    "env.kernel",
    "env.cpu_no_turbo",
    "env.cpu_governor",
    "env.cpu_min_perf_pct",
    "env.cpu_max_perf_pct",
    "env.rapl_domain",
    "env.num_ctx",
    "env.ollama_version",
)

_REQUEST_SAMPLER_FIELDS = (
    "gen_ai.request.temperature",
    "gen_ai.request.top_k",
    "gen_ai.request.top_p",
    "gen_ai.request.min_p",
    "gen_ai.request.repeat_penalty",
    "gen_ai.request.frequency_penalty",
    "gen_ai.request.presence_penalty",
)

_KV_BYTES_PER_ELEMENT = {
    "f32": 4.0,
    "float32": 4.0,
    "f16": 2.0,
    "float16": 2.0,
    "bf16": 2.0,
    # GGML block storage includes the per-block scale.
    "q8_0": 34.0 / 32.0,
    "q4_0": 18.0 / 32.0,
}


def _present(value: Any) -> bool:
    return value is not None and value != ""


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _first(row: Mapping[str, Any], *fields: str, default: Any = None) -> Any:
    for field in fields:
        value = row.get(field)
        if _present(value):
            return value
    return default


def _hardware_condition(row: Mapping[str, Any]) -> tuple[str | None, list[str]]:
    values = {field: row.get(field) for field in _HARDWARE_FIELDS}
    missing = [field for field, value in values.items() if not _present(value)]
    if missing:
        return None, missing
    return _canonical_hash(values), []


def _sampler_policy(row: Mapping[str, Any]) -> tuple[str | None, list[str]]:
    values = {
        field: row.get(field)
        for field in _REQUEST_SAMPLER_FIELDS
        if _present(row.get(field))
    }
    if "gen_ai.request.temperature" not in values and _present(row.get("temp")):
        values["gen_ai.request.temperature"] = row.get("temp")
    values["think"] = bool(row.get("think", False))
    if _present(row.get("ollama.parameters")):
        values["ollama.parameters"] = row.get("ollama.parameters")
    if _present(row.get("analysis.sampler_policy")):
        values["analysis.sampler_policy"] = row.get("analysis.sampler_policy")
    llama_sampler = {
        key: value
        for key, value in row.items()
        if key.startswith("llama_cpp.sampler.") and _present(value)
    }
    values.update(llama_sampler)
    has_effective_policy = (
        "ollama.parameters" in values
        or "analysis.sampler_policy" in values
        or bool(llama_sampler)
        or any(field in values for field in _REQUEST_SAMPLER_FIELDS[1:])
    )
    if not has_effective_policy:
        return None, ["effective_sampler_policy"]
    return _canonical_hash(values), []


def normalize_condition_provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    """Add explicit derived identity markers without changing raw evidence."""

    normalized = dict(row)
    if not _first(
        normalized,
        "ollama.digest",
        "llama_cpp.artifact.sha256",
        "gguf_sha256",
        "analysis.artifact_identity",
    ):
        model = str(normalized.get("model") or "")
        loaded = (normalized.get("ollama.ps.before") or {}).get("models") or []
        candidates = [
            item for item in loaded
            if isinstance(item, Mapping)
            and item.get("name") in {model, f"{model}:latest"}
            and isinstance(item.get("digest"), str)
            and len(item["digest"]) == 64
        ]
        if len(candidates) == 1:
            normalized["analysis.artifact_identity"] = (
                "ollama-ps-sha256:" + candidates[0]["digest"]
            )
            normalized["analysis.artifact_identity_source"] = "ollama.ps.before"

    _policy, sampler_missing = _sampler_policy(normalized)
    if sampler_missing:
        runtime = str(
            normalized.get("env.inference_runtime")
            or normalized.get("adapter")
            or "unknown"
        )
        runtime_version = (
            normalized.get("env.ollama_version")
            or normalized.get("llama_cpp.version")
        )
        temperature = normalized.get("gen_ai.request.temperature")
        if temperature in (None, ""):
            temperature = normalized.get("temp")
        if temperature not in (None, "") and runtime_version not in (None, ""):
            normalized["analysis.sampler_policy"] = {
                "kind": "runtime_defaults",
                "runtime_adapter": runtime,
                "runtime_version": runtime_version,
                "temperature": temperature,
                "think": bool(normalized.get("think", False)),
            }
    return normalized


@dataclass(frozen=True)
class AnalysisCondition:
    """Stable, hashable identity for one measured deployment condition."""

    key: tuple[tuple[str, Any], ...]
    sha256: str
    incomplete: bool
    missing_fields: tuple[str, ...]


def analysis_condition(
    row: Mapping[str, Any],
    *,
    evaluation_policy: str | None,
) -> AnalysisCondition:
    """Build the canonical analysis-condition key and fail closed on omissions.

    Incomplete rows may be summarized within their source artifact, but callers
    must not use them for cross-run joins or paired deployment comparisons.
    """

    artifact_identity = _first(
        row,
        "ollama.digest",
        "llama_cpp.artifact.sha256",
        "gguf_sha256",
        "analysis.artifact_identity",
    )
    runtime_adapter = _first(row, "env.inference_runtime", "adapter", "inference_runtime")
    quantization = _first(row, "ollama.quantization", "quantization", "quant")
    hardware_condition, hardware_missing = _hardware_condition(row)
    sampler_policy, sampler_missing = _sampler_policy(row)
    memory_context = _first(row, "env.memory_context", "memory_context", default="none")
    memory_sha = _first(row, "env.memory_context_sha", "memory_context_sha")
    strategy = _first(row, "env.inference_strategy", "inference_strategy", default="baseline")
    strategy_sha = _first(row, "env.strategy_prompt_sha", "strategy_prompt_sha")
    scenario_set = _first(row, "env.scenario_set", "scenario_set")
    scenarios_sha = _first(row, "env.scenarios_sha", "scenarios_sha256", "scenarios_sha")

    values = {
        "model": row.get("model"),
        "runtime_adapter": runtime_adapter,
        "artifact_identity": artifact_identity,
        "quantization": quantization,
        "hardware_condition": hardware_condition,
        "prompt_template_sha256": row.get("prompt.template_sha256"),
        "memory_context": memory_context,
        "memory_context_sha": memory_sha,
        "inference_strategy": strategy,
        "strategy_prompt_sha": strategy_sha,
        "sampling_policy": sampler_policy,
        "scenario_set": scenario_set,
        "scenarios_sha256": scenarios_sha,
        "evaluation_policy": evaluation_policy,
    }

    required = (
        "model",
        "runtime_adapter",
        "artifact_identity",
        "quantization",
        "hardware_condition",
        "prompt_template_sha256",
        "memory_context",
        "inference_strategy",
        "sampling_policy",
        "scenario_set",
        "scenarios_sha256",
        "evaluation_policy",
    )
    missing = [field for field in required if not _present(values.get(field))]
    if memory_context != "none" and not _present(memory_sha):
        missing.append("memory_context_sha")
    if strategy != "baseline" and not _present(strategy_sha):
        missing.append("strategy_prompt_sha")
    missing.extend(hardware_missing)
    missing.extend(sampler_missing)
    missing = sorted(set(missing))
    key = tuple((field, values[field]) for field in values)
    return AnalysisCondition(
        key=key,
        sha256=_canonical_hash(key),
        incomplete=bool(missing),
        missing_fields=tuple(missing),
    )


def evaluation_policy_id(judged_rows: Iterable[Mapping[str, Any]]) -> str:
    rows = list(judged_rows)
    declared = sorted({
        str(row.get("evaluation_policy"))
        for row in rows
        if _present(row.get("evaluation_policy"))
    })
    if len(declared) > 1:
        raise ValueError(
            "conflicting evaluation_policy values in judged rows: "
            + ", ".join(declared)
        )
    if declared:
        return declared[0]
    judges = sorted({
        f"{row.get('judge_backend') or 'unknown'}:{row.get('judge_model')}"
        for row in rows
        if row.get("judge_model")
    })
    return "deterministic-checks-v1|judges:" + ("+".join(judges) if judges else "none")


def resolve_evaluation_policy(
    judged_rows: Iterable[Mapping[str, Any]],
    *,
    explicit: str | None = None,
    allow_legacy: bool = False,
) -> str:
    rows = list(judged_rows)
    declared = {
        str(row.get("evaluation_policy"))
        for row in rows
        if _present(row.get("evaluation_policy"))
    }
    if explicit is not None:
        if declared and declared != {explicit}:
            raise ValueError(
                "explicit evaluation_policy conflicts with judged rows: "
                + ", ".join(sorted(declared))
            )
        return explicit
    if allow_legacy and any(not _present(row.get("analysis_condition_key_sha256")) for row in rows):
        if not declared:
            raise ValueError(
                "legacy judge compatibility requires an explicit evaluation_policy; "
                "observed surviving judges cannot define the requested ensemble"
            )
    return evaluation_policy_id(rows)


def judge_identity(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        str(row.get("judge_backend") or "unknown"),
        str(row.get("judge_model") or "unknown"),
    )


def judge_identity_label(row: Mapping[str, Any]) -> str:
    backend, model = judge_identity(row)
    return model if backend == "unknown" else f"{backend}:{model}"


def evaluation_policy_judges(evaluation_policy: str) -> frozenset[tuple[str, str]]:
    marker = "|judges:"
    if marker not in evaluation_policy:
        return frozenset()
    rendered = evaluation_policy.split(marker, 1)[1]
    if rendered in {"", "none"}:
        return frozenset()
    judges = set()
    for item in rendered.split("+"):
        backend, separator, model = item.partition(":")
        if not separator or not backend or not model:
            raise ValueError(f"invalid judge identity in evaluation_policy: {item!r}")
        judges.add((backend, model))
    return frozenset(judges)


def legacy_judge_join_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    """Fields available in historical judged rows before condition hashes."""

    return (
        row.get("model"),
        row.get("scenario"),
        row.get("rep"),
        _first(row, "env.memory_context", "memory_context", default="none"),
        _first(row, "env.inference_strategy", "inference_strategy", default="baseline"),
        _first(row, "env.inference_runtime", "adapter", "inference_runtime", default="ollama"),
    )


def judge_condition_index(
    condition_rows: Iterable[tuple[AnalysisCondition, Mapping[str, Any]]],
) -> tuple[frozenset[str], dict[tuple[Any, ...], frozenset[str]]]:
    """Index exact condition hashes and historical coarse keys.

    A coarse key may intentionally map to multiple canonical conditions. Callers
    must reject legacy judged rows for such a key instead of choosing one.
    """

    exact: set[str] = set()
    legacy: defaultdict[tuple[Any, ...], set[str]] = defaultdict(set)
    for identity, row in condition_rows:
        if identity.incomplete:
            continue
        exact.add(identity.sha256)
        legacy[legacy_judge_join_key(row)].add(identity.sha256)
    return frozenset(exact), {
        key: frozenset(values)
        for key, values in legacy.items()
    }


def resolve_judge_condition(
    judged_row: Mapping[str, Any],
    *,
    exact_conditions: frozenset[str],
    legacy_conditions: Mapping[tuple[Any, ...], frozenset[str]],
    allow_legacy: bool = False,
) -> str | None:
    """Resolve a judged row to one canonical condition, failing on ambiguity."""

    exact = judged_row.get("analysis_condition_key_sha256")
    if _present(exact):
        return str(exact) if exact in exact_conditions else None
    candidates = legacy_conditions.get(legacy_judge_join_key(judged_row), frozenset())
    if candidates and not allow_legacy:
        raise ValueError(
            "hashless legacy judge join requires explicit opt-in; rejudge with "
            "canonical condition hashes or enable the legacy compatibility mode"
        )
    if len(candidates) > 1:
        rendered = ", ".join(sorted(candidates))
        raise ValueError(
            "ambiguous legacy judge join: one judged-row key matches multiple "
            f"analysis conditions ({rendered}); rejudge with canonical condition hashes"
        )
    return next(iter(candidates), None)


def load_analysis_schema(path: str) -> dict[str, Any]:
    with open(path) as handle:
        schema = json.load(handle)
    if schema.get("schema_version") != ANALYSIS_SCHEMA_VERSION:
        raise ValueError(
            f"analysis schema version must be {ANALYSIS_SCHEMA_VERSION}, "
            f"got {schema.get('schema_version')!r}"
        )
    return schema


def validate_artifact_columns(
    schema: Mapping[str, Any],
    artifact_name: str,
    columns: Iterable[str],
) -> list[str]:
    artifacts = schema.get("artifacts") or {}
    contract = artifacts.get(artifact_name)
    if not isinstance(contract, Mapping):
        return [f"unknown analysis artifact contract: {artifact_name}"]
    observed = set(columns)
    required = set(contract.get("required_columns") or contract.get("required_keys") or [])
    forbidden = set(schema.get("global_forbidden_columns") or [])
    forbidden.update(contract.get("forbidden_columns") or [])
    errors = [f"missing required column/key: {name}" for name in sorted(required - observed)]
    errors.extend(f"forbidden column/key: {name}" for name in sorted(forbidden & observed))
    return errors


def validate_analysis_manifest(
    manifest: Mapping[str, Any],
    *,
    claim_bearing: bool,
) -> list[str]:
    errors = []
    if manifest.get("analysis_schema_version") != ANALYSIS_SCHEMA_VERSION:
        errors.append(f"analysis_schema_version must be {ANALYSIS_SCHEMA_VERSION}")
    if manifest.get("source_kind") not in {"frozen_snapshot", "completed_run"}:
        errors.append("source_kind must be frozen_snapshot or completed_run")
    if not _present(manifest.get("source_id")):
        errors.append("source_id is required")
    hashes = manifest.get("source_sha256")
    if not isinstance(hashes, Mapping) or not hashes:
        errors.append("source_sha256 must be a non-empty object")
    else:
        for name, digest in hashes.items():
            if not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64:
                errors.append("source_sha256 values must be named 64-character SHA256 strings")
                break
    if manifest.get("claim_status") not in {"locked", "provisional"}:
        errors.append("claim_status must be locked or provisional")
    if claim_bearing and manifest.get("claim_status") != "locked":
        errors.append("claim-bearing surfaces require claim_status=locked")
    return errors


def finish_reason(row: Mapping[str, Any]) -> str | None:
    reasons = row.get("gen_ai.response.finish_reasons")
    if isinstance(reasons, list):
        return str(reasons[0]) if reasons else None
    if _present(reasons):
        return str(reasons)
    fallback = row.get("finish_reason")
    return str(fallback) if _present(fallback) else None


def completion_outcome(row: Mapping[str, Any]) -> str:
    reason = finish_reason(row) or "unknown"
    lowered = reason.lower()
    if "after_done_missing" in lowered:
        return "incomplete_stream"
    if lowered.startswith("dnf:timeout"):
        return "dnf_timeout"
    if lowered.startswith("dnf:") or row.get("dnf"):
        suffix = lowered.split(":", 1)[1] if ":" in lowered else "other"
        return f"dnf_{suffix}"
    if lowered == "length":
        return "length"
    completion = row.get("gen_ai.completion")
    if completion is None:
        output = row.get("distill.output_message")
        completion = output.get("content") if isinstance(output, dict) else ""
    if not str(completion or "").strip():
        return "blank_stop" if lowered in {"stop", "unknown"} else "blank_other"
    return "stop" if lowered == "stop" else lowered


def safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if not isinstance(numerator, (int, float)) or not isinstance(denominator, (int, float)):
        return None
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def measured_mbu(measured_mb_s: float | int | None, peak_mb_s: float | int | None) -> float | None:
    return safe_ratio(measured_mb_s, peak_mb_s)


def dense_weight_stream_equivalent_ratio(
    artifact_size_bytes: float | int | None,
    decode_tokens_per_second: float | int | None,
    peak_mb_s: float | int | None,
) -> float | None:
    if not isinstance(artifact_size_bytes, (int, float)) or artifact_size_bytes <= 0:
        return None
    if not isinstance(decode_tokens_per_second, (int, float)) or decode_tokens_per_second <= 0:
        return None
    equivalent_mb_s = float(artifact_size_bytes) / 1e6 * float(decode_tokens_per_second)
    return measured_mbu(equivalent_mb_s, peak_mb_s)


def mean_energy_wh_per_answer(rows: Iterable[Mapping[str, Any]]) -> float | None:
    energies = [
        float(row["power.energy_wh"])
        for row in rows
        if isinstance(row.get("power.energy_wh"), (int, float))
    ]
    return statistics.mean(energies) if energies else None


def wh_per_det_check_equivalent(rows: Iterable[Mapping[str, Any]]) -> float | None:
    energy = 0.0
    credit = 0.0
    seen = False
    for row in rows:
        value = row.get("power.energy_wh")
        score = row.get("det_score")
        if not isinstance(value, (int, float)) or not isinstance(score, (int, float)):
            continue
        seen = True
        energy += float(value)
        credit += float(score)
    if not seen or credit <= 0:
        return None
    return energy / credit


def j_per_output_token(energy_wh: float | int | None, output_tokens: float | int | None) -> float | None:
    ratio = safe_ratio(energy_wh, output_tokens)
    return ratio * 3600.0 if ratio is not None else None


def kv_cache_payload_mb(
    *,
    blocks: float | int | None,
    kv_heads: float | int | None,
    embedding_length: float | int | None,
    attention_heads: float | int | None,
    token_count: float | int | None,
    dtype: str | None,
) -> tuple[str, float | None]:
    normalized = str(dtype).lower() if _present(dtype) else None
    if normalized in _KV_BYTES_PER_ELEMENT:
        field = f"kv_cache_{normalized}_payload_mb"
        bytes_per_element = _KV_BYTES_PER_ELEMENT[normalized]
    else:
        field = "kv_cache_fp16_equivalent_mb"
        bytes_per_element = 2.0
    values = (blocks, kv_heads, embedding_length, attention_heads, token_count)
    if any(not isinstance(value, (int, float)) or value <= 0 for value in values):
        return field, None
    head_dim = float(embedding_length) / float(attention_heads)
    payload = 2.0 * float(blocks) * float(kv_heads) * head_dim * float(token_count) * bytes_per_element
    return field, payload / 1e6


def repetition_metrics(
    successes: Sequence[bool],
    safe_outcomes: Sequence[bool] | None = None,
) -> dict[str, float | int | None]:
    if not successes:
        return {
            "repeat_count": 0,
            "repeat_agreement": None,
            "pass_1": None,
            "pass_all_k": None,
            "all_safe_k": None,
        }
    success_values = [bool(value) for value in successes]
    counts = Counter(success_values)
    safety = [bool(value) for value in safe_outcomes] if safe_outcomes is not None else None
    if safety is not None and len(safety) != len(success_values):
        raise ValueError("safe_outcomes must have the same length as successes")
    return {
        "repeat_count": len(success_values),
        "repeat_agreement": max(counts.values()) / len(success_values),
        "pass_1": sum(success_values) / len(success_values),
        "pass_all_k": int(all(success_values)),
        "all_safe_k": int(all(safety)) if safety is not None else None,
    }


def is_safety_scenario(row: Mapping[str, Any]) -> bool:
    if str(row.get("class") or "").lower() in SAFETY_CLASSES:
        return True
    risk = row.get("scenario.lifecycle.action.destructive_risk")
    if isinstance(risk, bool):
        return risk
    if isinstance(risk, (int, float)):
        return risk > 0
    return str(risk or "").strip().lower() not in {"", "0", "false", "no", "none", "low"}


def friedman_samples(
    rows: Iterable[Mapping[str, Any]],
    *,
    condition: Callable[[Mapping[str, Any]], Any],
    scenario_field: str = "scenario",
    value_field: str = "det_score",
) -> tuple[list[Any], list[str], list[list[float]]]:
    grouped: dict[Any, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        scenario = row.get(scenario_field)
        value = row.get(value_field)
        if not _present(scenario) or not isinstance(value, (int, float)):
            continue
        grouped[condition(row)][str(scenario)].append(float(value))
    labels = sorted(grouped, key=str)
    if not labels:
        return [], [], []
    common = sorted(set.intersection(*(set(grouped[label]) for label in labels)))
    samples = [
        [statistics.mean(grouped[label][scenario]) for scenario in common]
        for label in labels
    ]
    return labels, common, samples


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires values")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def scenario_cluster_mean_ci(
    rows: Iterable[Mapping[str, Any]],
    *,
    value_field: str,
    scenario_field: str = "scenario",
    samples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, float | None]:
    clusters: dict[str, list[float]] = defaultdict(list)
    observed: list[float] = []
    for row in rows:
        scenario = row.get(scenario_field)
        value = row.get(value_field)
        if not _present(scenario) or not isinstance(value, (int, float)):
            continue
        numeric = float(value)
        clusters[str(scenario)].append(numeric)
        observed.append(numeric)
    if not observed:
        return None, None, None
    point = statistics.mean(observed)
    labels = sorted(clusters)
    if len(labels) < 2 or samples <= 0:
        return point, None, None
    rng = random.Random(seed)
    means = []
    for _ in range(samples):
        selected = [rng.choice(labels) for _ in labels]
        sample_values = [value for label in selected for value in clusters[label]]
        means.append(statistics.mean(sample_values))
    return point, _quantile(means, alpha / 2), _quantile(means, 1 - alpha / 2)


def scenario_cluster_contrast_ci(
    rows: Iterable[Mapping[str, Any]],
    *,
    group_field: str,
    left_group: Any,
    right_group: Any,
    value_field: str,
    scenario_field: str = "scenario",
    samples: int = 10_000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, float | None]:
    """Estimate a left-minus-right contrast by resampling paired scenarios."""

    grouped: dict[Any, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        group = row.get(group_field)
        scenario = row.get(scenario_field)
        value = row.get(value_field)
        if group not in {left_group, right_group}:
            continue
        if not _present(scenario) or not isinstance(value, (int, float)):
            continue
        grouped[group][str(scenario)].append(float(value))
    common = sorted(set(grouped[left_group]) & set(grouped[right_group]))
    if not common:
        return None, None, None
    differences = {
        scenario: (
            statistics.mean(grouped[left_group][scenario])
            - statistics.mean(grouped[right_group][scenario])
        )
        for scenario in common
    }
    point = statistics.mean(differences.values())
    if len(common) < 2 or samples <= 0:
        return point, None, None
    rng = random.Random(seed)
    means = [
        statistics.mean(differences[rng.choice(common)] for _ in common)
        for _ in range(samples)
    ]
    return point, _quantile(means, alpha / 2), _quantile(means, 1 - alpha / 2)
