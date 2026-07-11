#!/usr/bin/env python3
"""Generate Croissant 1.0 metadata from the frozen ApprenticeOps manifest."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/analysis-manifest.json"
OUTPUT = ROOT / "data/croissant.json"
MODEL_LOCK = ROOT / "data/models.lock.jsonl"
MODELS = ROOT / "data/site/models.csv"

CONTEXT = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "cr": "http://mlcommons.org/croissant/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "extract": "cr:extract",
    "field": "cr:field",
    "fileObject": "cr:fileObject",
    "fileProperty": "cr:fileProperty",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
}

RECORD_SETS = {
    "data/snapshots/results_snapshot.csv": {
        "id": "results",
        "description": "One frozen inference result per runtime, model, scenario, and repetition.",
        "key": ("runtime_adapter", "model", "scenario", "rep"),
    },
    "data/snapshots/judged_snapshot.csv": {
        "id": "judged_results",
        "description": "Two-judge consensus quality joined one-to-one to frozen inference results.",
        "key": ("runtime_adapter", "model", "scenario", "rep"),
    },
    "data/snapshots/judged_snapshot.det.csv": {
        "id": "deterministic_judged_results",
        "description": "Historical deterministic-pass judged results.",
        "key": ("runtime_adapter", "model", "scenario", "rep"),
    },
    "data/site/judge_pairs.csv": {
        "id": "judge_pairs",
        "description": "Complete Claude and GPT score pairs for the functional-model population.",
        "key": ("model", "scenario", "rep"),
    },
    "data/snapshots/judge_pair_provenance.csv": {
        "id": "judge_pair_provenance",
        "description": "Frozen provenance and evaluation-policy identity for each retained judge pair.",
        "key": ("frozen_pair_key_sha256",),
    },
}


def infer_type(values: list[str]) -> str:
    present = [value.strip() for value in values if value.strip()]
    if present and all(value.lower() in {"true", "false"} for value in present):
        return "sc:Boolean"
    if present and all(re.fullmatch(r"[+-]?\d+", value) for value in present):
        return "sc:Integer"
    try:
        if present:
            for value in present:
                float(value)
            return "sc:Float"
    except ValueError:
        pass
    return "sc:Text"


def media_type(relative: str) -> str:
    if relative.endswith(".csv"):
        return "text/csv"
    if relative.endswith(".json"):
        return "application/json"
    if relative.endswith(".jsonl"):
        return "application/x-ndjson"
    if relative.endswith((".jsonl.gz", ".tar.gz")):
        return "application/gzip"
    return "application/octet-stream"


def used_model_rights() -> list[dict]:
    with MODELS.open(newline="") as handle:
        model_ids = {row["model"] for row in csv.DictReader(handle)}
    lock = {
        row["model_id"]: row
        for row in (
            json.loads(line)
            for line in MODEL_LOCK.read_text().splitlines()
            if line.strip()
        )
    }
    if not model_ids <= set(lock):
        raise SystemExit(f"model rights ledger is missing: {sorted(model_ids - set(lock))}")
    rows = [lock[model] for model in sorted(model_ids)]
    urls = {row["license_url"] for row in rows}
    if any(not isinstance(url, str) or not url.startswith("https://") for url in urls):
        raise SystemExit("every frozen model must have an HTTPS license URL")
    return rows


def distribution(manifest: dict) -> list[dict]:
    rows = []
    for relative, digest in sorted(manifest["source_sha256"].items()):
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"missing manifest source: {relative}")
        content_url = relative.removeprefix("data/")
        rows.append({
            "@type": "cr:FileObject",
            "@id": content_url,
            "name": path.name,
            "contentSize": f"{path.stat().st_size} B",
            "contentUrl": content_url,
            "encodingFormat": media_type(relative),
            "sha256": digest,
        })
    return rows


def record_sets() -> list[dict]:
    rights = used_model_rights()
    records = [{
        "@type": "cr:RecordSet",
        "@id": "model_rights",
        "name": "model_rights",
        "description": "Per-deployment upstream model-family rights for the frozen 94-model population.",
        "dataType": "sc:Enumeration",
        "key": {"@id": "model_rights/model"},
        "field": [
            {
                "@type": "cr:Field",
                "@id": "model_rights/model",
                "name": "model",
                "dataType": "sc:Text",
            },
            {
                "@type": "cr:Field",
                "@id": "model_rights/license",
                "name": "license",
                "dataType": "sc:Text",
            },
            {
                "@type": "cr:Field",
                "@id": "model_rights/license_class",
                "name": "license_class",
                "dataType": "sc:Text",
            },
            {
                "@type": "cr:Field",
                "@id": "model_rights/license_url",
                "name": "license_url",
                "dataType": "sc:URL",
            },
        ],
        "data": [
            {
                "model_rights/model": row["model_id"],
                "model_rights/license": row["license"],
                "model_rights/license_class": row["license_class"],
                "model_rights/license_url": row["license_url"],
            }
            for row in rights
        ],
    }]
    for relative, contract in RECORD_SETS.items():
        path = ROOT / relative
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
            columns = list(rows[0]) if rows else []
        if not rows:
            raise SystemExit(f"record-set source is empty: {relative}")
        record_id = contract["id"]
        fields = []
        for column in columns:
            field = {
                "@type": "cr:Field",
                "@id": f"{record_id}/{column}",
                "name": column,
                "dataType": infer_type([row[column] for row in rows]),
                "source": {
                    "fileObject": {"@id": relative.removeprefix("data/")},
                    "extract": {"column": column},
                },
            }
            if column == "model":
                field["references"] = {"field": {"@id": "model_rights/model"}}
            fields.append(field)
        records.append({
            "@type": "cr:RecordSet",
            "@id": record_id,
            "name": record_id,
            "description": contract["description"],
            "key": [{"@id": f"{record_id}/{column}"} for column in contract["key"]],
            "field": fields,
        })
    return records


def build() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    if (
        manifest.get("analysis_schema_version") != 1
        or manifest.get("source_kind") != "frozen_snapshot"
        or manifest.get("source_id") != "paper-94-model-corrected-v1"
        or manifest.get("claim_status") != "locked"
    ):
        raise SystemExit("Croissant generation requires the locked paper analysis manifest")
    rights = used_model_rights()
    licenses = [
        "https://www.apache.org/licenses/LICENSE-2.0",
        *sorted({row["license_url"] for row in rights}),
    ]
    return {
        "@context": CONTEXT,
        "@type": "sc:Dataset",
        "name": "ApprenticeOps frozen 94-model benchmark dataset",
        "description": (
            "Frozen inference, judge, safety, and CPU telemetry evidence for 94 "
            "functional small local-language-model deployments evaluated as "
            "homelab operations assistants. Quality and safety span two batches; "
            "claim-bearing energy and speed use only the controlled first batch."
        ),
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "citeAs": (
            "@dataset{hont2026apprenticeops, author={Dragos Hont}, "
            "title={ApprenticeOps frozen 94-model benchmark dataset}, "
            "year={2026}, url={https://github.com/dragoshont/apprenticeops}}"
        ),
        "license": licenses,
        "sdLicense": "https://www.apache.org/licenses/LICENSE-2.0",
        "usageInfo": "https://github.com/dragoshont/apprenticeops/blob/main/data/DATA_RIGHTS.md",
        "conditionsOfAccess": "Public; reuse is subject to the mixed rights documented in data/DATA_RIGHTS.md.",
        "url": "https://github.com/dragoshont/apprenticeops",
        "creator": {"@type": "sc:Person", "name": "Dragos Hont"},
        "publisher": {"@type": "sc:Person", "name": "Dragos Hont"},
        "dateCreated": "2026-06-18",
        "datePublished": "2026-06-21",
        "dateModified": "2026-07-11",
        "version": "1.0.0",
        "inLanguage": "en",
        "isLiveDataset": False,
        "keywords": [
            "AIOps",
            "CPU inference",
            "energy efficiency",
            "homelab",
            "LLM safety",
            "local LLM",
            "small language models",
        ],
        "distribution": distribution(manifest),
        "recordSet": record_sets(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    encoded = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text() != encoded:
            raise SystemExit("data/croissant.json is stale; run scripts/build-croissant.py")
        print("Croissant generation check passed")
        return
    OUTPUT.write_text(encoded)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()