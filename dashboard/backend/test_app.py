#!/usr/bin/env python3
"""Focused regressions for Mission Control status collection."""

from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("app.py")


def load_app():
    spec = importlib.util.spec_from_file_location("mission_control_app", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StatusGatherTests(unittest.TestCase):
    def test_timeout_returns_structured_error(self) -> None:
        module = load_app()
        timeout = subprocess.TimeoutExpired(["ssh", "home"], 40)
        with patch.object(module, "_ssh", side_effect=timeout):
            result = module._gather(None)

        self.assertEqual(result["state"], "error")
        self.assertEqual(result["run_id"], None)
        self.assertIn("timed out after 40 seconds", result["error"])
        self.assertIsInstance(result["ts"], float)


if __name__ == "__main__":
    unittest.main()