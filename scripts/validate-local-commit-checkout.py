#!/usr/bin/env python3
"""Create or verify the marker for an isolated local-commit checkout."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

EXPECTED = b"apprenticeops-local-commit-v1\n"


def validate_checkout(target: Path, marker_name: str) -> None:
    if Path(marker_name).name != marker_name or marker_name in {".", ".."}:
        raise ValueError("unsafe checkout marker name")
    uid = os.getuid()
    marker = target / marker_name

    if target.exists() or target.is_symlink():
        info = target.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid:
            raise ValueError("remote checkout target is not an owned regular directory")
    else:
        target.mkdir(parents=True, mode=0o700)

    entries = list(target.iterdir())
    if entries and not marker.exists() and not marker.is_symlink():
        raise ValueError("remote checkout lacks local-commit marker")

    if not marker.exists() and not marker.is_symlink():
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(marker, flags, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(EXPECTED)
            handle.flush()
            os.fsync(handle.fileno())
        directory = os.open(
            target,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    info = marker.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != uid:
        raise ValueError("remote checkout marker is not an owned regular file")
    descriptor = os.open(marker, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as handle:
        if handle.read() != EXPECTED:
            raise ValueError("remote checkout marker content is invalid")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: validate-local-commit-checkout.py TARGET MARKER")
    try:
        validate_checkout(Path(sys.argv[1]), sys.argv[2])
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
