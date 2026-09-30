#!/usr/bin/env python3
"""Resume the local operator pilot; explicit --prepare-only creates a new packet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from human_review import main

if __name__ == "__main__":
    raise SystemExit(main())
