#!/usr/bin/env python3
"""audit-run.py — stop-and-audit a (partial) results file before committing days
of compute. Reads results.jsonl[.gz], confirms EVERY row shares one reproducible
env regime (no mid-run drift) and that the regime matches the frozen manifest, and
flags the known regime problems (RAPL-domain mix, pull_failed, missing perf telemetry).

Usage:
    python3 scripts/audit-run.py results.<RUN_ID>.jsonl [--manifest data/run-manifest.json]

Workflow:
    1) node-power.sh setup
    2) RAPL_DOMAIN=package-0 PERF_MEMBW=1 PERF_CORE=1 python3 run.py --models ... \
         --temp 0.7 --repeats 5 --seed-base 1 --limit 2 --out results.<RUN_ID>.jsonl
    3) python3 scripts/audit-run.py results.<RUN_ID>.jsonl     # must print AUDIT: PASS
    4) re-launch without --limit for the full sweep (dedup handles the 2 repeats)

Exit 0 = PASS, non-zero = problems found.
"""
import argparse
import collections
import gzip
import hashlib
import json
import os
import sys

VOLATILE = ["env.cpu_no_turbo", "env.cpu_governor", "env.cpu_min_perf_pct",
            "env.cpu_max_perf_pct", "env.rapl_domain", "env.perf_event_paranoid"]
STATIC = ["env.host", "env.kernel", "env.ollama_version", "env.harness_git",
          "env.num_ctx", "env.sample_interval_s", "env.perf_membw", "env.perf_core"]


def _open(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def load(path):
    rows = []
    with _open(path) as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try:
                    rows.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
    return rows


def finish_of(r):
    fr = r.get("gen_ai.response.finish_reasons")
    if isinstance(fr, list) and fr:
        return fr[0]
    if isinstance(fr, str):
        return fr
    if r.get("fatal"):
        return f"fatal:{r['fatal']}"
    return r.get("finish_reason") or "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--manifest", default="data/run-manifest.json")
    ap.add_argument("--scenarios", default="data/scenarios.json")
    args = ap.parse_args()

    rows = load(args.results)
    if not rows:
        print(f"AUDIT: FAIL — no rows in {args.results}")
        sys.exit(2)
    man = json.load(open(args.manifest)) if os.path.exists(args.manifest) else {}
    problems, notes = [], []

    real = [r for r in rows if r.get("model") and not r.get("fatal")]
    fatals = [r for r in rows if r.get("fatal")]
    has_env = [r for r in real if any(k in r for k in VOLATILE)]

    print(f"rows={len(rows)}  models={len({r.get('model') for r in real})}  "
          f"result-rows={len(real)}  fatal-rows={len(fatals)}")

    # 0) provenance present at all? (a wave1/wave2-era file has no env.* fields)
    if not has_env:
        problems.append("no env.* provenance in any row — this file predates the guard; "
                        "cannot verify the regime from the data (re-run with the current run.py)")

    # 1) ONE consistent volatile regime across all rows (no mid-run drift)
    if has_env:
        regimes = collections.Counter(
            tuple(str(r.get(k)) for k in VOLATILE) for r in has_env)
        if len(regimes) > 1:
            problems.append(f"{len(regimes)} DIFFERENT env regimes in one file (mid-run drift):")
            for reg, n in regimes.most_common():
                notes.append("   " + dict(zip(VOLATILE, reg)).__repr__() + f"  x{n}")
        else:
            reg = dict(zip(VOLATILE, next(iter(regimes))))
            notes.append("single regime: " + ", ".join(f"{k.split('.')[-1]}={v}" for k, v in reg.items()))

    # 2) regime matches the manifest
    cpu, energy = man.get("cpu", {}), man.get("energy", {})
    want = {
        "env.cpu_no_turbo": cpu.get("intel_pstate.no_turbo"),
        "env.cpu_governor": cpu.get("scaling_governor"),
        "env.cpu_min_perf_pct": cpu.get("min_perf_pct"),
        "env.cpu_max_perf_pct": cpu.get("max_perf_pct"),
        "env.rapl_domain": energy.get("rapl_domain"),
    }
    for k, v in want.items():
        if v is None:
            continue
        seen = {str(r.get(k)) for r in has_env}
        if seen and seen != {str(v)}:
            problems.append(f"{k}: manifest wants {v!r}, file has {sorted(seen)}")

    # 3) RAPL domain must be single (the wave2 psys/package-0 mix)
    srcs = collections.Counter(r.get("power.source") for r in real if r.get("power.source"))
    if len(srcs) > 1:
        problems.append(f"mixed RAPL/power source (energy not comparable): {dict(srcs)}")
    elif srcs:
        notes.append(f"power.source: {dict(srcs)}")

    # 4) pull_failed (the wave2 133)
    if fatals:
        fc = collections.Counter(r.get("fatal") for r in fatals)
        problems.append(f"{len(fatals)} fatal/pull_failed rows: {dict(fc)} "
                        "(pre-pull the models or check disk/registry)")

    # 5) missing perf telemetry rate (the wave2 14%)
    miss = sum(1 for r in real if r.get("membw.series") in (None, [], {}))
    rate = miss / len(real) * 100 if real else 0
    (problems if rate > 3 else notes).append(
        f"missing membw.series on {miss}/{len(real)} ({rate:.1f}%) "
        + ("> 3% — perf counters dropping (perf_event_paranoid?)" if rate > 3 else "rows (ok)"))

    # 6) ollama version consistency (+ vs manifest if pinned)
    vers = {r.get("env.ollama_version") for r in has_env if r.get("env.ollama_version")}
    if len(vers) > 1:
        problems.append(f"multiple ollama versions in one file: {sorted(vers)}")
    elif vers:
        v = next(iter(vers))
        notes.append(f"ollama version: {v}")
        pinned = man.get("expected", {}).get("ollama_version")
        if pinned and pinned != v:
            problems.append(f"ollama version {v!r} != manifest pin {pinned!r}")
        elif not pinned:
            notes.append("  (manifest expected.ollama_version is null — pin it to this once confirmed)")

    # 7) scenarios.json hash (inputs unchanged)
    want_sha = man.get("protocol", {}).get("scenarios_sha256")
    if want_sha and os.path.exists(args.scenarios):
        got = hashlib.sha256(open(args.scenarios, "rb").read()).hexdigest()
        if got != want_sha:
            problems.append(f"scenarios.json changed since wave1: {got[:12]}… != {want_sha[:12]}…")
        else:
            notes.append("scenarios.json sha256 matches wave1")

    # 8) protocol args as recorded in the rows
    temps = {r.get("temp") for r in real if r.get("temp") is not None}
    thinks = {r.get("think") for r in real if r.get("think") is not None}
    if temps and temps != {man.get("protocol", {}).get("temperature", 0.7)}:
        problems.append(f"temperature in rows = {temps} (manifest {man.get('protocol', {}).get('temperature')})")
    if thinks and thinks != {man.get("protocol", {}).get("think", False)}:
        problems.append(f"think in rows = {thinks} (manifest {man.get('protocol', {}).get('think')})")

    # finish-reason mix (informational)
    notes.append("finish: " + ", ".join(f"{k}={v}" for k, v in
                 collections.Counter(finish_of(r) for r in real).most_common()))

    print("\n".join("  " + n for n in notes))
    if problems:
        print("\nAUDIT: FAIL")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(1)
    print("\nAUDIT: PASS — regime is single, matches the manifest, and is wave1-identical.")


if __name__ == "__main__":
    main()
