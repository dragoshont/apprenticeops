#!/usr/bin/env python3
"""Regression checks for generated Croissant metadata."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_croissant", ROOT / "scripts/build-croissant.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_distribution_matches_manifest():
    metadata = module.build()
    manifest = json.loads((ROOT / "data/analysis-manifest.json").read_text())
    observed = {
        f"data/{row['contentUrl']}": row["sha256"]
        for row in metadata["distribution"]
    }
    assert observed == manifest["source_sha256"]


def test_mixed_rights_are_explicit():
    metadata = module.build()
    assert metadata["sdLicense"] == "https://www.apache.org/licenses/LICENSE-2.0"
    assert "https://ai.google.dev/gemma/terms" in metadata["license"]
    assert "https://huggingface.co/stabilityai" in metadata["license"]
    assert metadata["isLiveDataset"] is False


def test_every_frozen_model_has_embedded_rights():
    metadata = module.build()
    rights = next(row for row in metadata["recordSet"] if row["@id"] == "model_rights")
    declared = {
        row["model_rights/model"]: (
            row["model_rights/license"],
            row["model_rights/license_class"],
            row["model_rights/license_url"],
        )
        for row in rights["data"]
    }
    assert len(declared) == 94
    assert all(values[0] and values[1] and values[2].startswith("https://") for values in declared.values())
    for record_set in metadata["recordSet"]:
        if record_set["@id"] == "model_rights":
            continue
        model_fields = [field for field in record_set.get("field", []) if field.get("name") == "model"]
        for field in model_fields:
            assert field["references"] == {"field": {"@id": "model_rights/model"}}


def test_record_sets_have_unique_fields_and_sources():
    metadata = module.build()
    ids = []
    for record_set in metadata["recordSet"]:
        for field in record_set["field"]:
            ids.append(field["@id"])
            if record_set["@id"] != "model_rights":
                assert field["source"]["fileObject"]["@id"]
                assert field["source"]["extract"]["column"]
    assert len(ids) == len(set(ids))


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in sorted(tests, key=lambda item: item.__name__):
        test()
    print(f"Croissant tests passed: {len(tests)}")


if __name__ == "__main__":
    main()