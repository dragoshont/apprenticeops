#!/usr/bin/env python3
"""build-model-inventory.py — full inventory of every model across all 3 waves.

Joins the three manifests (wave membership + bracket) with the verified metadata
(data/model_metadata.csv) and the raw results (which tags actually produced data),
and parses the tag for the rest. Emits data/models-inventory.csv — one row per
unique tag in the roster, so you can see at a glance: which wave(s) it's in, its
bracket, family/org/arch/license/quant, size, and whether it has data yet.

    python3 scripts/build-model-inventory.py
"""
import csv
import glob
import gzip
import json
import os
import re
from collections import defaultdict

LISTS = [("w1", "data/models.txt"), ("w2", "data/models.wave2.txt"), ("w3", "data/models.wave3.txt")]
META = "data/model_metadata.csv"
RAW = sorted(glob.glob("data/raw/results.*.jsonl.gz"))
OUT = "data/models-inventory.csv"

COLS = ["model", "waves", "bracket", "has_data", "family", "org", "arch_class", "quant",
        "param_size", "size_gb", "is_moe", "native_ctx", "license", "training_regime",
        "thinking_capable", "tools_capable", "provenance", "source_file_count"]


def parse_lists():
    info = defaultdict(lambda: {"waves": [], "brackets": []})
    for wave, path in LISTS:
        if not os.path.exists(path):
            continue
        bracket = None
        for line in open(path):
            s = line.strip()
            if s.startswith("# bracket:"):
                bracket = s.split(":", 1)[1].strip(); continue
            if not s or s.startswith("#"):
                continue
            d = info[s]
            if wave not in d["waves"]:
                d["waves"].append(wave)
            if bracket and bracket not in d["brackets"]:
                d["brackets"].append(bracket)
    return info


def load_meta():
    if not os.path.exists(META):
        return {}
    with open(META) as fh:
        return {r["model"]: r for r in csv.DictReader(fh)}


def ran_in():
    """tag -> set of data files it appears in (has real result rows)."""
    seen = defaultdict(set)
    for path in RAW:
        tag_present = set()
        with gzip.open(path, "rt") as fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    r = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                m = r.get("model")
                if m and not r.get("fatal"):
                    tag_present.add(m)
        wave = os.path.basename(path).replace("results.", "").replace(".jsonl.gz", "")
        for m in tag_present:
            seen[m].add(wave)
    return seen


def provenance(tag):
    if tag.startswith("hf.co/"):
        owner = tag.split("/", 2)[1] if "/" in tag[6:] else "hf"
        return f"hf:{owner}"
    return "ollama-library"


def parse_quant(tag, meta):
    if meta.get("quant"):
        return meta["quant"]
    m = re.search(r"(q\d[_a-zA-Z0-9]*|fp16|bf16|f16|IQ\d[_a-zA-Z0-9]*)", tag)
    return m.group(1) if m else ""


def parse_family(tag, meta):
    if meta.get("family"):
        return meta["family"]
    base = tag.split("/")[-1].split(":")[0]
    return re.split(r"[-.\d]", base)[0] or base


def main():
    info = parse_lists()
    meta = load_meta()
    ran = ran_in()
    rows = []
    for tag, d in info.items():
        m = meta.get(tag, {})
        data_files = ran.get(tag, set())
        rows.append({
            "model": tag,
            "waves": ";".join(d["waves"]),
            "bracket": d["brackets"][0] if d["brackets"] else (m.get("bracket") or ""),
            "has_data": ";".join(sorted(data_files)) if data_files else "no",
            "family": parse_family(tag, m),
            "org": m.get("org", ""),
            "arch_class": m.get("arch_class", ""),
            "quant": parse_quant(tag, m),
            "param_size": m.get("param_size", ""),
            "size_gb": m.get("size_gb", ""),
            "is_moe": m.get("is_moe", ""),
            "native_ctx": m.get("native_ctx", ""),
            "license": m.get("license", ""),
            "training_regime": m.get("training_regime", ""),
            "thinking_capable": m.get("thinking_capable", ""),
            "tools_capable": m.get("tools_capable", ""),
            "provenance": provenance(tag),
            "source_file_count": len(d["waves"]),
        })
    order = {b: i for i, b in enumerate(["0-1B", "1-2B", "2-3B", "3-4B", "4-5GB"])}
    rows.sort(key=lambda r: (order.get(r["bracket"], 9), r["model"]))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    # summary
    n = len(rows)
    with_meta = sum(1 for r in rows if r["org"])
    with_data = sum(1 for r in rows if r["has_data"] != "no")
    print(f"wrote {OUT}: {n} unique tags")
    print(f"  with verified metadata: {with_meta}   with result data: {with_data}   "
          f"NEW (no data yet): {n - with_data}")
    bybr = defaultdict(int)
    for r in rows:
        bybr[r["bracket"]] += 1
    print("  by bracket: " + "  ".join(f"{b}={bybr[b]}" for b in ["0-1B", "1-2B", "2-3B", "3-4B", "4-5GB"]))
    byw = defaultdict(int)
    for r in rows:
        byw[r["waves"]] += 1
    print("  by wave membership: " + "  ".join(f"{k}={v}" for k, v in sorted(byw.items())))


if __name__ == "__main__":
    main()
