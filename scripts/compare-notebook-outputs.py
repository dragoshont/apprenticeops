#!/usr/bin/env python3
"""Compare cached notebook outputs while ignoring volatile environment metadata.

Text remains exact after narrow path/pip normalization. PNGs are decoded and
pixel-compared under a strict antialias tolerance; other binary MIME payloads
must match by SHA-256.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

BINARY_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/svg+xml",
}
MAX_IMAGE_CHANNEL_DELTA = 2
MAX_IMAGE_CHANGED_PIXEL_FRACTION = 0.0005


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def decode_png(raw: bytes) -> tuple[int, int, str, bytes]:
    with Image.open(io.BytesIO(raw)) as image:
        if image.format != "PNG":
            fail(f"binary notebook output is not a PNG: {image.format}")
        normalized = image.convert("RGBA")
        return normalized.width, normalized.height, normalized.mode, normalized.tobytes()


def binary_descriptor(mime_type: str, value) -> dict:
    encoded = "".join(value) if isinstance(value, list) else str(value)
    raw = base64.b64decode(encoded) if mime_type != "image/svg+xml" else encoded.encode()
    return {
        "__binary_mime__": mime_type,
        "payload": encoded,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _normalize_output_paths(value, roots: tuple[str, ...]):
    if isinstance(value, str):
        value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value).replace("\r\n", "\n")
        for root in roots:
            value = value.replace(root, "<REPO_ROOT>")
        for marker in ("data/site", "data/snapshots", "docs/analysis"):
            value = re.sub(
                rf"/[^\s'\"]*/{re.escape(marker)}",
                f"<REPO_ROOT>/{marker}",
                value,
            )
        value = re.sub(
            r"(?m)^(repository root:\s*).*$",
            r"\1<REPO_ROOT>",
            value,
        )
        value = re.sub(
            r"(?m)^(python\s*:\s*)(?:[^\n|]+[/\\])?python(?:\d+(?:\.\d+)*)?\s*$",
            r"\1<PYTHON>",
            value,
        )
        value = re.sub(
            r"(?m)^(root\s*:\s*)(?:[A-Za-z]:)?[/\\][^|\n]*?\S(?=\s*\|)",
            r"\1<REPO_ROOT>",
            value,
        )
        value = "".join(
            line
            for line in value.splitlines(keepends=True)
            if not re.match(
                r"^\s*\[notice\] (?:A new release of pip is available(?::|\s*$)|To update, run:)",
                line,
            )
        )
        value = value.lstrip("\n")
        return value
    if isinstance(value, list):
        return [_normalize_output_paths(item, roots) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_output_paths(item, roots) for key, item in value.items()}
    return value


def stable_output(output: dict, roots: tuple[str, ...]) -> dict:
    value = copy.deepcopy(output)
    value.pop("execution_count", None)
    value.pop("transient", None)
    data = value.get("data")
    if isinstance(data, dict):
        for mime_type in BINARY_MIME_TYPES & data.keys():
            data[mime_type] = binary_descriptor(mime_type, data[mime_type])
    return _normalize_output_paths(value, roots)


def stable_outputs(outputs: list[dict], roots: tuple[str, ...]) -> list[dict]:
    """Normalize nondeterministic Jupyter chunking of adjacent stream writes."""

    merged: list[dict] = []
    for item in outputs:
        output = copy.deepcopy(item)
        if output.get("output_type") != "stream":
            merged.append(output)
            continue
        text = output.get("text", "")
        output["text"] = "".join(text) if isinstance(text, list) else str(text)
        if (
            merged
            and merged[-1].get("output_type") == "stream"
            and merged[-1].get("name") == output.get("name")
        ):
            merged[-1]["text"] += output["text"]
        else:
            merged.append(output)

    normalized: list[dict] = []
    for output in (stable_output(item, roots) for item in merged):
        if output.get("output_type") == "stream" and not output.get("text", "").strip():
            continue
        normalized.append(output)
    return normalized


def stable_cell(cell: dict, roots: tuple[str, ...]) -> dict:
    value = {
        "cell_type": cell.get("cell_type"),
        "id": cell.get("id"),
        "source": cell.get("source", []),
    }
    if "attachments" in cell:
        value["attachments"] = cell["attachments"]
    if cell.get("cell_type") == "code":
        value["outputs"] = stable_outputs(cell.get("outputs", []), roots)
    return value


def without_binary_payloads(value):
    if isinstance(value, dict):
        if "__binary_mime__" in value:
            return {"__binary_mime__": value["__binary_mime__"]}
        return {key: without_binary_payloads(item) for key, item in value.items()}
    if isinstance(value, list):
        return [without_binary_payloads(item) for item in value]
    return value


def binary_payloads(value) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        if "__binary_mime__" in value:
            found.append(value)
        else:
            for item in value.values():
                found.extend(binary_payloads(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(binary_payloads(item))
    return found


def binary_equivalent(left: dict, right: dict) -> bool:
    if left.get("__binary_mime__") != right.get("__binary_mime__"):
        return False
    if left.get("sha256") == right.get("sha256"):
        return True
    if left["__binary_mime__"] != "image/png":
        return False
    left_raw = base64.b64decode(left["payload"])
    right_raw = base64.b64decode(right["payload"])
    left_width, left_height, left_mode, left_pixels = decode_png(left_raw)
    right_width, right_height, right_mode, right_pixels = decode_png(right_raw)
    if (left_width, left_height, left_mode) != (right_width, right_height, right_mode):
        return False
    if left_pixels == right_pixels:
        return True
    if len(left_pixels) != len(right_pixels):
        return False
    changed_pixels = 0
    max_delta = 0
    for offset in range(0, len(left_pixels), 4):
        deltas = [
            abs(left_pixels[offset + channel] - right_pixels[offset + channel])
            for channel in range(4)
        ]
        if any(deltas):
            changed_pixels += 1
            max_delta = max(max_delta, *deltas)
    total_pixels = left_width * left_height
    return (
        max_delta <= MAX_IMAGE_CHANNEL_DELTA
        and changed_pixels / total_pixels <= MAX_IMAGE_CHANGED_PIXEL_FRACTION
    )


def cells_equivalent(left: dict, right: dict) -> bool:
    if left == right:
        return True
    if without_binary_payloads(left) != without_binary_payloads(right):
        return False
    left_binary = binary_payloads(left)
    right_binary = binary_payloads(right)
    return len(left_binary) == len(right_binary) and all(
        binary_equivalent(first, second)
        for first, second in zip(left_binary, right_binary, strict=True)
    )


def load_cells(path: Path, roots: tuple[str, ...]) -> list[dict]:
    try:
        notebook = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read notebook {path}: {exc}")
    return [stable_cell(cell, roots) for cell in notebook.get("cells", [])]


def main() -> None:
    if len(sys.argv) not in {3, 4}:
        fail("usage: compare-notebook-outputs.py CACHED.ipynb EXECUTED.ipynb [EXECUTED_ROOT]")
    cached_path, executed_path = map(Path, sys.argv[1:3])
    cached_root = str(cached_path.resolve().parents[2])
    executed_roots = (
        str(Path(sys.argv[3]).resolve()),
        cached_root,
    ) if len(sys.argv) == 4 else (cached_root,)
    cached = load_cells(cached_path, (cached_root,))
    executed = load_cells(executed_path, executed_roots)
    if len(cached) != len(executed):
        fail(
            f"notebook cell count differs for {cached_path}: "
            f"cached={len(cached)} executed={len(executed)}"
        )

    changed: list[str] = []
    for index, (left, right) in enumerate(zip(cached, executed, strict=True)):
        if cells_equivalent(left, right):
            continue
        cell_id = left.get("id") or right.get("id") or "no-id"
        if left.get("source") != right.get("source"):
            reason = "source"
        elif left.get("attachments") != right.get("attachments"):
            reason = "attachments"
        else:
            reason = "outputs"
        changed.append(f"cell {index} ({cell_id}): {reason}")

    if changed:
        fail(
            f"cached notebook differs from fresh execution: {cached_path}\n  "
            + "\n  ".join(changed)
        )
    print(f"notebook outputs match: {cached_path}")


if __name__ == "__main__":
    main()
