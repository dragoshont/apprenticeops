#!/usr/bin/env python3
"""
calibrate.py — measure the hardware CEILINGS + telemetry overhead so MBU and
saturation % are real, not guessed (addresses the adversarial measure review:
roofline needs the *measured* peak, not the datasheet; C3 observer-effect).

Writes calibration.json that report.py reads to compute **Model Bandwidth
Utilization** (MBU = achieved ÷ peak) and a bottleneck verdict:
  - peak_membw_mb_s : a STREAM-style multi-thread memcpy peak (achievable, not spec)
  - peak_tok_s      : decode tok/s of the tiniest model (a practical speed ceiling)
  - idle_watts/temp : the net-over-idle baseline
  - telemetry_overhead_pct : tok/s lost to the sampler+perf (the observer effect)

  python3 calibrate.py --probe-model qwen2.5:0.5b --out calibration.json
  # run on the node, with RAPL/perf env as for the real run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
import time

import run  # reuse PerfBandwidth, Sampler, run_chat, measure_idle_watts


def stream_peak_mb_s(seconds=6, threads=None):
    """Multi-thread memcpy to saturate DRAM; perf reports the achieved peak MB/s.
    Closer to the *achievable* bandwidth ceiling than the datasheet figure."""
    threads = threads or max(1, (os.cpu_count() or 4) // 2)
    perf = run.PerfBandwidth()
    perf.start()
    stop = time.time() + seconds

    def worker():
        a = bytearray(128 * 1024 * 1024)
        b = bytearray(128 * 1024 * 1024)
        while time.time() < stop:
            b[:] = a  # 128 MB memcpy -> ~256 MB DRAM traffic

    ts = [threading.Thread(target=worker, daemon=True) for _ in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    perf.stop()
    perf.join(timeout=2)
    return round(perf.peak_mb_s, 1), threads


class _NullSampler:
    """No-op sampler so run_chat can run WITHOUT telemetry (overhead baseline)."""
    abort_reason = None

    def start(self):
        pass

    def stop(self):
        pass

    def join(self, timeout=None):
        pass


def _tok_s(model, prompt, reps=3, with_telemetry=True):
    vals = []
    for _ in range(reps):
        if with_telemetry:
            perf = run.PerfBandwidth() if run.PERF_MEMBW else None
            if perf:
                perf.start()
            s = run.Sampler()
            s.start()
        else:
            perf, s = None, _NullSampler()
        tel = run.run_chat(model, "", prompt, max_tokens=128, timeout_s=120,
                           stall_s=60, think=False, sampler=s, temperature=0, seed=1)
        if with_telemetry:
            s.stop()
            s.join(timeout=2)
            if perf:
                perf.stop()
                perf.join(timeout=2)
        if tel.get("decode_tok_s"):
            vals.append(tel["decode_tok_s"])
    return round(sum(vals) / len(vals), 2) if vals else None


def disk_seq_read_mb_s(mb=1024):
    """Cold sequential read MB/s of the NVMe: write a temp file, drop caches, time
    the read. Best-effort; needs sudo for the cache drop (else it reads warm)."""
    path = "/tmp/sme_disktest.bin"
    try:
        subprocess.run(["dd", "if=/dev/zero", f"of={path}", "bs=1M", f"count={mb}"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        subprocess.run(["sync"], timeout=30)
        run._sudo_write("/proc/sys/vm/drop_caches", "3")  # force a cold read
        t0 = time.time()
        with open(path, "rb", buffering=0) as f:
            while f.read(8 << 20):
                pass
        dt = time.time() - t0
        return round(mb / dt, 1) if dt > 0 else None
    except Exception:  # noqa: BLE001
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-model", default="qwen2.5:0.5b")
    ap.add_argument("--out", default="calibration.json")
    args = ap.parse_args()
    prompt = "List three reasons to monitor a Kubernetes cluster. Be brief."

    run.warmup(args.probe_model, False)
    peak_bw, bw_threads = stream_peak_mb_s()
    clean_tok = _tok_s(args.probe_model, prompt, with_telemetry=False)
    instr_tok = _tok_s(args.probe_model, prompt, with_telemetry=True)
    cal = {
        "ts": time.time(),
        "probe_model": args.probe_model,
        "rapl_domain": run.RAPL_NAME,
        "idle_watts": run.measure_idle_watts(),
        "idle_temp_c": run._cpu_temp_c(),
        "peak_membw_mb_s": peak_bw,
        "membw_stress_threads": bw_threads,
        "disk_seq_read_mb_s": disk_seq_read_mb_s(),
        "peak_tok_s": clean_tok,
        "telemetry_overhead_pct": (round(100 * (clean_tok - instr_tok) / clean_tok, 1)
                                   if (clean_tok and instr_tok) else None),
        "perf_membw_enabled": run.PERF_MEMBW,
    }
    json.dump(cal, open(args.out, "w"), indent=2)
    print(json.dumps(cal, indent=2))


if __name__ == "__main__":
    main()
