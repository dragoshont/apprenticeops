#!/usr/bin/env python3
"""Validate every Ollama roster tag with cheap pull/show/chat/generate canaries.

This is a disk-bounded roster health pass, not the scientific benchmark. It asks:

- can the tag be pulled/resolved by the local Ollama daemon?
- can Ollama show metadata for it?
- does /api/chat produce visible text for a tiny deterministic canary?
- does /api/generate produce visible text if chat fails or returns empty?
- does historical data already mark the tag as DNF/length-prone?

Rows are written as JSONL so a long validation can be resumed or audited.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = REPO / "data" / "models.txt"
DEFAULT_LOCK = REPO / "data" / "models.lock.jsonl"
DEFAULT_SNAPSHOT = REPO / "data" / "snapshots" / "results_snapshot.csv"
DEFAULT_OUT = REPO / "results.roster-validation.jsonl"

CANARY_PROMPT = "Return exactly OK and nothing else."
CANARY_MESSAGES = [
    {"role": "system", "content": "Follow the user instruction exactly."},
    {"role": "user", "content": CANARY_PROMPT},
]


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def tail_text(value: str, limit: int = 4000) -> str:
    value = value or ""
    return value[-limit:]


def load_models(path: Path) -> list[dict[str, str | None]]:
    models: list[dict[str, str | None]] = []
    bracket: str | None = None
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            if "bracket:" in line:
                bracket = line.split("bracket:", 1)[1].strip()
            continue
        models.append({"model": line, "roster_bracket": bracket})
    return models


def load_lock(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for raw in path.read_text().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        rows[str(row.get("model_id"))] = row
    return rows


def load_historical_snapshot(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            model = row.get("model")
            if model:
                buckets[model].append(row)
    out: dict[str, dict[str, Any]] = {}
    for model, rows in buckets.items():
        finish = Counter(row.get("finish_reason") or "unknown" for row in rows)
        dnf = 0
        length = 0
        for row in rows:
            reason = str(row.get("finish_reason") or "")
            is_dnf = str(row.get("dnf") or "").lower() == "true" or reason.startswith("DNF") or "error" in reason.lower()
            dnf += int(is_dnf)
            length += int("length" in reason.lower())
        total = len(rows)
        out[model] = {
            "historical.rows": total,
            "historical.dnf": dnf,
            "historical.dnf_rate": round(dnf / total, 4) if total else None,
            "historical.length": length,
            "historical.length_rate": round(length / total, 4) if total else None,
            "historical.finish_reasons": dict(finish),
        }
    return out


def completed_models(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    for raw in path.read_text(errors="ignore").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        model = row.get("model")
        if model:
            done.add(str(model))
    return done


def run_cmd(args: list[str], *, timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            args,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env={**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")},
        )
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "elapsed_s": round(time.time() - started, 3),
            "stdout_tail": tail_text(proc.stdout),
            "stderr_tail": tail_text(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "rc": None,
            "elapsed_s": round(time.time() - started, 3),
            "timeout": True,
            "stdout_tail": tail_text(exc.stdout or ""),
            "stderr_tail": tail_text(exc.stderr or ""),
        }
    except OSError as exc:
        return {
            "ok": False,
            "rc": None,
            "elapsed_s": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def post_json(base_url: str, path: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any]:
    started = time.time()
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
            parsed = json.loads(raw) if raw.strip() else {}
            return {
                "ok": 200 <= int(response.status) < 300,
                "status": response.status,
                "elapsed_s": round(time.time() - started, 3),
                "json": parsed,
                "body_tail": tail_text(raw),
            }
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return {
            "ok": False,
            "status": exc.code,
            "elapsed_s": round(time.time() - started, 3),
            "error": f"HTTPError: {exc}",
            "body_tail": tail_text(body),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": None,
            "elapsed_s": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def model_present(model: str, *, timeout: int = 30) -> bool:
    return bool(run_cmd(["ollama", "show", model], timeout=timeout).get("ok"))


def unload_model(base_url: str, model: str) -> None:
    post_json(
        base_url,
        "/api/chat",
        {"model": model, "keep_alive": 0, "messages": []},
        timeout=30,
    )


def visible_chat_text(result: dict[str, Any]) -> str:
    data = result.get("json") if isinstance(result.get("json"), dict) else {}
    message = data.get("message") if isinstance(data.get("message"), dict) else {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    return ""


def visible_generate_text(result: dict[str, Any]) -> str:
    data = result.get("json") if isinstance(result.get("json"), dict) else {}
    value = data.get("response")
    return value if isinstance(value, str) else ""


def compact_probe(result: dict[str, Any], *, text: str) -> dict[str, Any]:
    data = result.get("json") if isinstance(result.get("json"), dict) else {}
    return {
        "ok": bool(result.get("ok")),
        "status": result.get("status"),
        "elapsed_s": result.get("elapsed_s"),
        "error": result.get("error"),
        "body_tail": result.get("body_tail") if not result.get("ok") else None,
        "output_chars": len(text),
        "output_preview": text[:240],
        "done_reason": data.get("done_reason"),
        "eval_count": data.get("eval_count"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "total_duration_ns": data.get("total_duration"),
    }


def classify(row: dict[str, Any]) -> tuple[str, str, list[str]]:
    findings: list[str] = []
    if not row.get("pull.ok"):
        return "fail", "pull_failed", ["ollama pull failed"]
    if not row.get("show.ok"):
        findings.append("ollama show failed after pull")
    chat_ok = bool(row.get("chat.ok"))
    chat_chars = int(row.get("chat.output_chars") or 0)
    generate_ok = bool(row.get("generate.ok"))
    generate_chars = int(row.get("generate.output_chars") or 0)
    if chat_ok and chat_chars > 0:
        status = "ok"
        reason = "chat_nonempty"
    elif chat_ok and chat_chars == 0 and generate_ok and generate_chars > 0:
        status = "warn"
        reason = "chat_empty_generate_nonempty"
        findings.append("chat returned empty text but generate returned visible text")
    elif not chat_ok and generate_ok and generate_chars > 0:
        status = "warn"
        reason = "chat_failed_generate_nonempty"
        findings.append("chat failed but generate returned visible text")
    elif chat_ok and chat_chars == 0 and generate_ok and generate_chars == 0:
        status = "fail"
        reason = "empty_completion"
        findings.append("both chat and generate returned empty visible text")
    else:
        status = "fail"
        reason = "served_failure"
        findings.append("no canary path produced visible text")
    hist_dnf_rate = row.get("historical.dnf_rate")
    hist_length_rate = row.get("historical.length_rate")
    if isinstance(hist_dnf_rate, float) and hist_dnf_rate >= 0.5:
        findings.append(f"historical high DNF rate {hist_dnf_rate:.1%}")
    if isinstance(hist_length_rate, float) and hist_length_rate >= 0.5:
        findings.append(f"historical high length rate {hist_length_rate:.1%}")
    return status, reason, findings


def validation_row(
    model: str,
    bracket: str | None,
    lock: dict[str, Any],
    historical: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ts": utc_now(),
        "model": model,
        "roster_bracket": bracket,
        "ollama_base_url": args.ollama_url,
        "canary_prompt": CANARY_PROMPT,
        "pull_attempted": False,
        "pulled_by_validator": False,
    }
    for key in (
        "publisher",
        "family",
        "params_b",
        "tier",
        "training_type",
        "quantization",
        "runtime_options",
        "llama_cpp_status",
        "source_url",
        "included",
        "exclusion_reason",
    ):
        row[f"lock.{key}"] = lock.get(key)
    row.update(historical)

    was_present = model_present(model, timeout=args.show_timeout)
    row["pre_present"] = was_present
    pull_result = {"ok": True, "rc": 0, "elapsed_s": 0.0, "stdout_tail": "", "stderr_tail": ""}
    if not was_present and not args.no_pull:
        row["pull_attempted"] = True
        for attempt in range(1, args.pull_retries + 1):
            pull_result = run_cmd(["ollama", "pull", model], timeout=args.pull_timeout)
            if pull_result.get("ok") or model_present(model, timeout=args.show_timeout):
                pull_result["attempt"] = attempt
                row["pulled_by_validator"] = True
                break
            if attempt < args.pull_retries:
                time.sleep(args.pull_backoff_s * attempt)
        else:
            pull_result["attempt"] = args.pull_retries
    elif not was_present and args.no_pull:
        pull_result = {"ok": False, "rc": None, "elapsed_s": 0.0, "error": "model_missing_and_no_pull"}
    row.update({f"pull.{key}": value for key, value in pull_result.items()})
    if not row.get("pull.ok"):
        row["overall_status"] = "fail"
        row["overall_reason"] = "pull_failed"
        row["findings"] = ["ollama pull failed or was disabled for a missing model"]
        return row

    show_result = run_cmd(["ollama", "show", model], timeout=args.show_timeout)
    row.update({f"show.{key}": value for key, value in show_result.items()})
    chat_payload = {
        "model": model,
        "messages": CANARY_MESSAGES,
        "stream": False,
        "think": False,
        "options": {
            "num_predict": args.num_predict,
            "temperature": 0,
            "seed": args.seed,
        },
    }
    chat_result = post_json(args.ollama_url, "/api/chat", chat_payload, timeout=args.chat_timeout)
    chat_text = visible_chat_text(chat_result)
    row.update({f"chat.{key}": value for key, value in compact_probe(chat_result, text=chat_text).items()})
    generate_payload = {
        "model": model,
        "prompt": CANARY_PROMPT,
        "stream": False,
        "options": {
            "num_predict": args.num_predict,
            "temperature": 0,
            "seed": args.seed,
        },
    }
    generate_result = post_json(args.ollama_url, "/api/generate", generate_payload, timeout=args.generate_timeout)
    generate_text = visible_generate_text(generate_result)
    row.update({f"generate.{key}": value for key, value in compact_probe(generate_result, text=generate_text).items()})
    status, reason, findings = classify(row)
    row["overall_status"] = status
    row["overall_reason"] = reason
    row["findings"] = findings
    unload_model(args.ollama_url, model)
    if args.rm_after and row.get("pulled_by_validator"):
        remove_result = run_cmd(["ollama", "rm", model], timeout=args.rm_timeout)
        row.update({f"remove.{key}": value for key, value in remove_result.items()})
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=str(DEFAULT_MODELS), help="Roster file, default data/models.txt")
    parser.add_argument("--lock", default=str(DEFAULT_LOCK), help="Model lock JSONL for metadata enrichment")
    parser.add_argument("--snapshot", default=str(DEFAULT_SNAPSHOT), help="Historical results snapshot CSV")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSONL path")
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument("--no-pull", action="store_true", help="Do not pull missing models; mark them failed")
    parser.add_argument("--rm-after", action="store_true", help="Remove models pulled by this validator after probing")
    parser.add_argument("--force", action="store_true", help="Revalidate models already present in --out")
    parser.add_argument("--limit", type=int, help="Maximum number of not-yet-complete models to validate")
    parser.add_argument("--model", action="append", help="Validate only the named model; repeatable")
    parser.add_argument("--pull-retries", type=int, default=2)
    parser.add_argument("--pull-backoff-s", type=int, default=10)
    parser.add_argument("--pull-timeout", type=int, default=1800)
    parser.add_argument("--show-timeout", type=int, default=60)
    parser.add_argument("--chat-timeout", type=int, default=90)
    parser.add_argument("--generate-timeout", type=int, default=90)
    parser.add_argument("--rm-timeout", type=int, default=180)
    parser.add_argument("--num-predict", type=int, default=16)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    models_path = Path(args.models)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lock_by_model = load_lock(Path(args.lock))
    historical_by_model = load_historical_snapshot(Path(args.snapshot))
    selected = set(args.model or [])
    done = set() if args.force else completed_models(out_path)
    rows = load_models(models_path)
    pending = [row for row in rows if (not selected or row["model"] in selected) and row["model"] not in done]
    if args.limit is not None:
        pending = pending[: args.limit]
    total = len(pending)
    sys.stderr.write(f"validating {total} model(s) -> {out_path}\n")
    with out_path.open("a", encoding="utf-8") as handle:
        for index, item in enumerate(pending, start=1):
            model = str(item["model"])
            sys.stderr.write(f"[{index}/{total}] {model}\n")
            sys.stderr.flush()
            try:
                row = validation_row(
                    model,
                    item.get("roster_bracket"),
                    lock_by_model.get(model, {}),
                    historical_by_model.get(model, {}),
                    args,
                )
            except Exception as exc:  # noqa: BLE001
                row = {
                    "ts": utc_now(),
                    "model": model,
                    "roster_bracket": item.get("roster_bracket"),
                    "overall_status": "fail",
                    "overall_reason": "validator_exception",
                    "findings": [f"{type(exc).__name__}: {exc}"],
                }
            handle.write(json.dumps(row, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            sys.stderr.write(f"  -> {row.get('overall_status')} {row.get('overall_reason')}\n")
            sys.stderr.flush()


if __name__ == "__main__":
    main()