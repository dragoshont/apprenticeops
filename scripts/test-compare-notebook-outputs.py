#!/usr/bin/env python3
"""Regression tests for stable notebook-output comparison."""

from __future__ import annotations

import base64
import binascii
import importlib.util
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compare_notebook_outputs",
    ROOT / "scripts/compare-notebook-outputs.py",
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def stream(text: str) -> dict:
    return {"name": "stdout", "output_type": "stream", "text": text}


def image_output(*, changed_value: int = 0, changed_pixels: int = 1) -> dict:
    width = height = 100
    pixels = bytearray((255, 255, 255, 255) * width * height)
    if changed_value:
        for pixel in range(changed_pixels):
            pixels[pixel * 4] = 255 - changed_value
    scanlines = b"".join(
        b"\x00" + bytes(pixels[row * width * 4:(row + 1) * width * 4])
        for row in range(height)
    )

    def chunk(kind: bytes, value: bytes) -> bytes:
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", binascii.crc32(kind + value) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines))
        + chunk(b"IEND", b"")
    )
    return {
        "data": {"image/png": base64.b64encode(png).decode()},
        "metadata": {},
        "output_type": "display_data",
    }


def test_checkout_paths_are_normalized():
    left = module.stable_outputs(
        [stream("Loading /Users/person/Repo/apprenticeops/data/snapshots/results.csv\n")],
        ("/Users/person/Repo/apprenticeops",),
    )
    right = module.stable_outputs(
        [stream("Loading /private/tmp/clean-repo/data/snapshots/results.csv\n")],
        ("/private/tmp/clean-repo",),
    )
    assert left == right
    python_left = module.stable_outputs([stream("python : /tmp/a/bin/python\n")], ())
    python_right = module.stable_outputs([stream("python : /tmp/b/bin/python\n")], ())
    assert python_left == python_right
    root_left = module.stable_outputs([stream("root : /tmp/a | evidence: locked\n")], ())
    root_right = module.stable_outputs([stream("root : /tmp/b | evidence: locked\n")], ())
    assert root_left == root_right
    known_root = module.stable_outputs(
        [stream("root : /tmp/a | evidence: locked\n")],
        ("/tmp/a",),
    )
    assert known_root == root_right


def test_ansi_pip_notices_are_ignored():
    cached = module.stable_outputs(
        [stream("Note: you may need to restart the kernel to use updated packages.\n")],
        (),
    )
    fresh = module.stable_outputs(
        [stream(
            "\r\n\x1b[1m[\x1b[0m\x1b[34mnotice\x1b[0m] A new release of pip is available\r\n"
            "\x1b[1m[\x1b[0m\x1b[34mnotice\x1b[0m] To update, run: python -m pip install --upgrade pip\r\n"
            "Note: you may need to restart the kernel to use updated packages.\n"
        )],
        (),
    )
    assert cached == fresh


def test_split_trailing_newline_stream_is_merged_before_filtering():
    combined = module.stable_outputs([stream("result\n")], ())
    split = module.stable_outputs([stream("result"), stream("\n")], ())
    assert combined == split


def test_scientific_text_difference_is_not_hidden():
    left = module.stable_outputs([stream("quality=0.50\n")], ())
    right = module.stable_outputs([stream("quality=0.51\n")], ())
    assert left != right


def test_generic_notice_and_interpreter_adjacent_numbers_are_not_hidden():
    notice_left = module.stable_outputs([stream("[notice] quality=0.50\n")], ())
    notice_right = module.stable_outputs([stream("[notice] quality=0.51\n")], ())
    assert notice_left != notice_right
    python_left = module.stable_outputs([stream("python : /tmp/bin/python | quality=0.50\n")], ())
    python_right = module.stable_outputs([stream("python : /tmp/bin/python | quality=0.51\n")], ())
    assert python_left != python_right
    root_left = module.stable_outputs([stream("root : 0.50 | quality\n")], ())
    root_right = module.stable_outputs([stream("root : 0.51 | quality\n")], ())
    assert root_left != root_right


def test_tiny_antialias_image_noise_is_tolerated():
    left = module.stable_cell({"cell_type": "code", "outputs": [image_output()]}, ())
    right = module.stable_cell(
        {"cell_type": "code", "outputs": [image_output(changed_value=1)]},
        (),
    )
    assert module.cells_equivalent(left, right)


def test_scientific_image_change_is_not_hidden():
    left = module.stable_cell({"cell_type": "code", "outputs": [image_output()]}, ())
    right = module.stable_cell(
        {"cell_type": "code", "outputs": [image_output(changed_value=32)]},
        (),
    )
    assert not module.cells_equivalent(left, right)


def test_widespread_low_delta_image_change_is_not_hidden():
    left = module.stable_cell({"cell_type": "code", "outputs": [image_output()]}, ())
    right = module.stable_cell(
        {
            "cell_type": "code",
            "outputs": [image_output(changed_value=1, changed_pixels=10)],
        },
        (),
    )
    assert not module.cells_equivalent(left, right)


def test_non_png_binary_requires_exact_hash():
    def pdf(value: bytes) -> dict:
        return {
            "cell_type": "code",
            "outputs": [{
                "data": {"application/pdf": base64.b64encode(value).decode()},
                "metadata": {},
                "output_type": "display_data",
            }],
        }

    first = module.stable_cell(pdf(b"%PDF-same"), ())
    second = module.stable_cell(pdf(b"%PDF-same"), ())
    changed = module.stable_cell(pdf(b"%PDF-changed"), ())
    assert module.cells_equivalent(first, second)
    assert not module.cells_equivalent(first, changed)


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"notebook comparator tests passed: {len(tests)}")


if __name__ == "__main__":
    main()