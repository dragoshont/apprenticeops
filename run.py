#!/usr/bin/env python3
"""
run.py — node-side small-model eval runner (stdlib only, runs ON home-ai).

Runs against the configured local inference runtime: Ollama for legacy/service
evidence, llama.cpp direct-GGUF subprocesses for the experiment runtime, or the
diagnostic llama.cpp server adapter for token/logprob/metrics capture. It
must run on the node:
    ssh dragos@home-ai.hont.ro 'cd /home/dragos/apprenticeops-runtime-agent && python3 run.py --models data/models.dryrun.txt'

For each (model x scenario) it:
  - warms up the model (cold-load timing) once per model,
  - runs the chat with a STREAMING request so we get TTFT + a per-token progress
    trace, under a BREAKGLASS watchdog (wall-clock / stall / mem / max-tokens),
  - samples host RAM/swap/CPU every second for the whole request,
  - runs the scenario's deterministic_checks,
  - appends one OTel-GenAI-aligned JSON row to results.jsonl and the raw output
    to outputs/<model>__<scenario>.txt,
  - unloads the model (keep_alive:0) then QUIESCES before the next model: drives
    the ThinkPad fan to max, flushes/frees memory (page-cache/swap/compaction),
    and waits for the package temp (and load) to settle, so every model starts
    from an identical machine state (the thermal-order / state-carryover fix).

DNF (timeout/stall/oom/loop) is a FIRST-CLASS result, not a crash.

Telemetry field names follow the OpenTelemetry GenAI semantic conventions
(gen_ai.*) so the data is portable to any OTel backend.
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import glob
import hashlib
import random
import resource
import shlex
import shutil
import selectors
import socket
import ssl
import subprocess
import sys
import threading
import time
import tempfile
import urllib.error
import urllib.parse
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
INFERENCE_RUNTIME = os.environ.get("INFERENCE_RUNTIME", "ollama")
LLAMA_CPP_CLI = os.environ.get("LLAMA_CPP_CLI") or (shutil.which("llama-completion") or "llama-cli")
LLAMA_CPP_SERVER = os.environ.get("LLAMA_CPP_SERVER") or (shutil.which("llama-server") or "llama-server")
LLAMA_CPP_SERVER_HOST = os.environ.get("LLAMA_CPP_SERVER_HOST", "127.0.0.1")
LLAMA_CPP_SERVER_PORT = int(os.environ.get("LLAMA_CPP_SERVER_PORT", "18080") or "18080")
LLAMA_CPP_SERVER_N_PROBS = int(os.environ.get("LLAMA_CPP_SERVER_N_PROBS", "5") or "5")
LLAMA_CPP_MODELS_DIR = os.environ.get("LLAMA_CPP_MODELS", os.environ.get("LLAMA_CPP_MODEL_DIR", "/srv/llama.cpp/models"))
LLAMA_CPP_MODEL_MAP = os.environ.get("LLAMA_CPP_MODEL_MAP", "")
LLAMA_CPP_ARTIFACTS = os.environ.get("LLAMA_CPP_ARTIFACTS", "data/llama-cpp-smoke-5.artifacts.json")
LLAMA_CPP_EXTRA_ARGS = os.environ.get("LLAMA_CPP_EXTRA_ARGS", "")
LLAMA_CPP_BENCH = os.environ.get("LLAMA_CPP_BENCH", "1") != "0"
LLAMA_CPP_BENCH_REPS = int(os.environ.get("LLAMA_CPP_BENCH_REPS", "3") or "3")
LLAMA_CPP_BENCH_PROMPT_TOKENS = int(os.environ.get("LLAMA_CPP_BENCH_PROMPT_TOKENS", "128") or "128")
LLAMA_CPP_BENCH_GEN_TOKENS = int(os.environ.get("LLAMA_CPP_BENCH_GEN_TOKENS", "32") or "32")
LLAMA_CPP_TIME_VERBOSE = os.environ.get("LLAMA_CPP_TIME_VERBOSE", "1") != "0"
LLAMA_CPP_RUNTIMES = {"llama_cpp", "llama_cpp_server"}
RUNTIMES = {"ollama", *LLAMA_CPP_RUNTIMES}

# ---- power metering (optional) -------------------------------------------
# Reads instantaneous wall power (watts) from the node's smart plug over the LAN.
# Two interchangeable sources, both env-gated and best-effort (no-op if unset, so
# the run is unaffected). This is operator/harness telemetry (like /proc) — NOT a
# model egress — so the locally-sovereign offline contract still holds.
#
#   (A) Home Assistant REST  — if the plug is exposed as an HA sensor.
#   (B) IKEA DIRIGERA hub    — poll the hub directly (the INSPELNING plug reports
#                              currentActivePower natively; no HA integration
#                              needed). Preferred on the LAN next to the hub.
# If both are configured, HA wins; DIRIGERA is the fallback.
HA_URL = os.environ.get("HA_URL")                       # e.g. http://192.168.1.201:8123
HA_TOKEN = os.environ.get("HA_TOKEN")                   # long-lived token (env only; never commit)
HA_POWER_ENTITY = os.environ.get("HA_POWER_ENTITY")    # e.g. sensor.hot_plate_power (watts)

DIRIGERA_URL = os.environ.get("DIRIGERA_URL")           # e.g. https://192.168.1.50:8443
DIRIGERA_TOKEN = os.environ.get("DIRIGERA_TOKEN")       # hub bearer token (env only; never commit)
DIRIGERA_DEVICE_ID = os.environ.get("DIRIGERA_DEVICE_ID")  # outlet id (INSPELNING plug)

# DIRIGERA serves its API over HTTPS with a self-signed cert on the LAN; the
# bearer token is the auth boundary, so cert pinning is unnecessary here.
_DIRIGERA_SSL = ssl.create_default_context()
_DIRIGERA_SSL.check_hostname = False
_DIRIGERA_SSL.verify_mode = ssl.CERT_NONE

# ---- breakglass defaults (overridable per-scenario / via CLI) -------------
DEFAULT_TIMEOUT_S = 180      # hard wall-clock per request
DEFAULT_STALL_S = 60         # no new token for this long -> DNF:stall
DEFAULT_MAX_TOKENS = 512     # num_predict cap
MAX_TOKENS_CAP = int(os.environ.get("MAX_TOKENS_CAP", "0") or "0")
DEFAULT_TIMEOUT_POLICY_ID = os.environ.get("TIMEOUT_POLICY_ID", "ceops-v2-zero-stall-retry")
DEFAULT_INFERENCE_STRATEGY = os.environ.get("INFERENCE_STRATEGY", "baseline")
CAPTURE_PROMPT_CONTENT = os.environ.get("CAPTURE_PROMPT_CONTENT", "1") != "0"
PROMPT_CAPTURE_POLICY = os.environ.get("PROMPT_CAPTURE_POLICY", "benchmark_secret_free")
PROMPT_TEMPLATE_ID = "ceops_ops_assistant_v1"
PROMPT_SYSTEM_INSTRUCTIONS = "You are a homelab operations assistant. Use ONLY the information given. Be concise and specific."
ZERO_OUTPUT_RETRIES = int(os.environ.get("ZERO_OUTPUT_RETRIES", "1"))
INFERENCE_STRATEGIES = {
    "baseline",
    "single_call_tournament_brief",
    "best_of_3_detcheck",
    "self_consistency_3",
    "evaluator_optimizer_1",
}
MEM_AVAIL_FLOOR_MB = 800     # abort if node MemAvailable drops below this
SWAP_USED_CEIL_MB = 14000    # abort if swap usage exceeds this (thrash guard)
COOLDOWN_S = 5               # settle time between models
NUM_CTX = 8192
SAMPLE_INTERVAL_S = float(os.environ.get("SAMPLE_INTERVAL", "1.0"))  # 1Hz; lower (e.g. 0.25) = finer curves
COOL_TEMP_C = float(os.environ.get("COOL_TEMP_C", "0"))   # cool to this °C between models (0 = off, fixed COOLDOWN_S)
COOL_MAX_S = float(os.environ.get("COOL_MAX_S", "180"))   # cap on cooldown wait
# ---- per-model quiesce (identical start state; best-effort, needs sudo) ----
QUIESCE = os.environ.get("QUIESCE", "1") != "0"           # master switch for the reset below
FAN_MAX = os.environ.get("FAN_MAX", "1") != "0"           # drive ThinkPad fan to max while cooling
DROP_CACHES = os.environ.get("DROP_CACHES", "0") == "1"   # echo 3 > drop_caches (fair cold-load each model)
RESET_SWAP = os.environ.get("RESET_SWAP", "0") == "1"     # swapoff/swapon (clear leftover swap)
LOAD_SETTLE = float(os.environ.get("LOAD_SETTLE", "0"))   # also wait load1 below this (0 = off)
FAN_DEV = "/proc/acpi/ibm/fan"


# --------------------------------------------------------------------------
# Host telemetry sampler (reads /proc — Linux node only).
# --------------------------------------------------------------------------
def _meminfo():
    avail = swap_total = swap_free = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                k, _, rest = line.partition(":")
                v = int(rest.strip().split()[0])  # kB
                if k == "MemAvailable":
                    avail = v // 1024
                elif k == "SwapTotal":
                    swap_total = v // 1024
                elif k == "SwapFree":
                    swap_free = v // 1024
    except OSError:
        return None, None
    swap_used = (swap_total - swap_free) if (swap_total is not None and swap_free is not None) else None
    return avail, swap_used


def _ha_power():
    """Current wall power (watts) from the node's smart plug via the LOCAL Home
    Assistant REST API. Returns None if unconfigured or unreachable (best-effort)."""
    if not (HA_URL and HA_TOKEN and HA_POWER_ENTITY):
        return None
    try:
        req = urllib.request.Request(
            f"{HA_URL}/api/states/{HA_POWER_ENTITY}",
            headers={"Authorization": f"Bearer {HA_TOKEN}"})
        with urllib.request.urlopen(req, timeout=0.8) as r:
            return float(json.loads(r.read().decode()).get("state"))
    except Exception:  # noqa: BLE001
        return None


def _dirigera_power():
    """Current wall power (watts) straight from the IKEA DIRIGERA hub's REST API
    (the INSPELNING plug reports currentActivePower). Returns None if unconfigured
    or unreachable (best-effort)."""
    if not (DIRIGERA_URL and DIRIGERA_TOKEN and DIRIGERA_DEVICE_ID):
        return None
    try:
        req = urllib.request.Request(
            f"{DIRIGERA_URL}/v1/devices/{DIRIGERA_DEVICE_ID}",
            headers={"Authorization": f"Bearer {DIRIGERA_TOKEN}"})
        with urllib.request.urlopen(req, timeout=0.8, context=_DIRIGERA_SSL) as r:
            attrs = json.loads(r.read().decode()).get("attributes", {})
            watts = attrs.get("currentActivePower")
            return float(watts) if watts is not None else None
    except Exception:  # noqa: BLE001
        return None


def _plug_power():
    """Instantaneous wall power (watts) from whichever plug source is configured.
    HA wins if set; DIRIGERA is the fallback. None if neither is configured."""
    w = _ha_power()
    return w if w is not None else _dirigera_power()


# ---- on-die energy (Intel RAPL) ------------------------------------------
# PREFERRED energy source: cumulative joule counters in /sys. Per-task energy =
# counter delta across the request → exact joules, no smart plug needed. psys =
# whole-platform SoC energy (best proxy, strips constant display/idle overhead);
# package-0 = CPU only. Root-only since CVE-2020-8694 → read via passwordless
# sudo. Env override RAPL_DOMAIN (psys|package-0); disable with RAPL_DISABLE=1.
def _rapl_pick():
    if os.environ.get("RAPL_DISABLE"):
        return None, None
    want = os.environ.get("RAPL_DOMAIN")
    found = {}
    for d in sorted(glob.glob("/sys/class/powercap/intel-rapl/intel-rapl:*")):
        try:
            found[open(f"{d}/name").read().strip()] = d
        except OSError:
            continue
    if want and want in found:
        return want, found[want]
    for key in ("psys", "package-0"):
        if key in found:
            return key, found[key]
    return None, None


RAPL_NAME, RAPL_DIR = _rapl_pick()
RAPL_MAX = None
if RAPL_DIR:
    try:
        RAPL_MAX = int(open(f"{RAPL_DIR}/max_energy_range_uj").read())
    except OSError:
        RAPL_MAX = None


def _read_uj(path):
    """Read a RAPL energy_uj counter: direct first, then passwordless sudo."""
    try:
        with open(path) as f:
            return int(f.read())
    except (OSError, ValueError):
        pass
    try:
        p = subprocess.run(["sudo", "-n", "cat", path],
                           capture_output=True, text=True, timeout=2)
        return int(p.stdout.strip()) if p.returncode == 0 else None
    except Exception:  # noqa: BLE001
        return None


def _rapl_uj():
    return _read_uj(f"{RAPL_DIR}/energy_uj") if RAPL_DIR else None


def _rapl_delta_j(before, after, maxv=None):
    """Joules between two energy_uj reads, handling per-domain counter wraparound."""
    if before is None or after is None:
        return None
    d = after - before
    if d < 0:
        d += (maxv or RAPL_MAX or 0)
    return d / 1e6


# ---- CPU thermal / frequency / utilisation (Linux sysfs) -----------------
# Time-axis signals for the on-device behaviour profile: does a long answer
# heat the chip into thermal THROTTLE (temp up -> freq down -> tok/s down)?
def _pkg_temp_path():
    for z in glob.glob("/sys/class/thermal/thermal_zone*"):
        try:
            if open(f"{z}/type").read().strip() == "x86_pkg_temp":
                return f"{z}/temp"
        except OSError:
            continue
    return None


_PKG_TEMP = _pkg_temp_path()


def _cpu_temp_c():
    if not _PKG_TEMP:
        return None
    try:
        return round(int(open(_PKG_TEMP).read()) / 1000, 1)
    except (OSError, ValueError):
        return None


def _cpu_freq_mhz():
    fs = []
    for p in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
        try:
            fs.append(int(open(p).read()))
        except (OSError, ValueError):
            continue
    return round(sum(fs) / len(fs) / 1000) if fs else None


def _cpu_times():
    """(total_jiffies, idle_jiffies) from /proc/stat for utilisation deltas."""
    try:
        v = list(map(int, open("/proc/stat").readline().split()[1:]))
        return sum(v), v[3] + (v[4] if len(v) > 4 else 0)
    except (OSError, ValueError):
        return None


def _percore_freq():
    """Per-core current frequency (MHz) ordered by core index — turbo spread."""
    paths = glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq")
    paths.sort(key=lambda p: int(re.search(r"/cpu(\d+)/", p).group(1)))
    fs = []
    for p in paths:
        try:
            fs.append(int(open(p).read()) // 1000)
        except (OSError, ValueError):
            fs.append(None)
    return fs


def _percore_times():
    """[(total, idle)] per cpuN from /proc/stat for per-core util deltas."""
    res = []
    try:
        for line in open("/proc/stat"):
            if line.startswith("cpu") and len(line) > 3 and line[3].isdigit():
                v = list(map(int, line.split()[1:]))
                res.append((sum(v), v[3] + (v[4] if len(v) > 4 else 0)))
    except (OSError, ValueError):
        pass
    return res


# ---- memory power (RAPL dram), model footprint, disk/net I/O -------------
RAPL_DIR_ENERGY = f"{RAPL_DIR}/energy_uj" if RAPL_DIR else None


def _rapl_subdomains():
    """{core,uncore,dram -> energy_uj path} under the selected RAPL domain."""
    out = {}
    if RAPL_DIR:
        for d in sorted(glob.glob(f"{RAPL_DIR}/intel-rapl:*")):
            try:
                out[open(f"{d}/name").read().strip()] = f"{d}/energy_uj"
            except OSError:
                continue
    return out


RAPL_SUB = _rapl_subdomains()


def _energy_max(path):
    try:
        return int(open(path.replace("energy_uj", "max_energy_range_uj")).read())
    except (OSError, ValueError):
        return None


RAPL_MAXES = {p: _energy_max(p) for p in [RAPL_DIR_ENERGY, *RAPL_SUB.values()] if p}


def _read_uj_many(paths):
    """Read several energy_uj counters in ONE sudo call (batched); {path: uj}."""
    paths = [p for p in paths if p]
    res, need = {}, []
    for p in paths:
        try:
            res[p] = int(open(p).read())
        except (OSError, ValueError):
            need.append(p)
    if need:
        try:
            out = subprocess.run(["sudo", "-n", "cat", *need],
                                 capture_output=True, text=True, timeout=2)
            if out.returncode == 0:
                for p, v in zip(need, out.stdout.split()):
                    try:
                        res[p] = int(v)
                    except ValueError:
                        pass
        except Exception:  # noqa: BLE001
            pass
    return res


def _runner_pid():
    """PID of the current ollama model runner (holds the model in RAM)."""
    try:
        out = subprocess.run(["pgrep", "-f", "llama-server"],
                             capture_output=True, text=True, timeout=2)
        pids = out.stdout.split()
        return int(pids[0]) if pids else None
    except Exception:  # noqa: BLE001
        return None


def _runner_stats(pid):
    """Model-runner process stats from /proc: rss_mb, threads, major + minor page
    faults, and voluntary/involuntary context switches (scheduler pressure)."""
    s = {"rss_mb": None, "threads": None, "majflt": None, "minflt": None,
         "ctxt_vol": None, "ctxt_invol": None}
    if not pid:
        return s
    try:
        for line in open(f"/proc/{pid}/status"):
            if line.startswith("VmRSS:"):
                s["rss_mb"] = int(line.split()[1]) // 1024
            elif line.startswith("Threads:"):
                s["threads"] = int(line.split()[1])
            elif line.startswith("voluntary_ctxt_switches:"):
                s["ctxt_vol"] = int(line.split()[1])
            elif line.startswith("nonvoluntary_ctxt_switches:"):
                s["ctxt_invol"] = int(line.split()[1])
    except (OSError, ValueError):
        pass
    try:
        f = open(f"/proc/{pid}/stat").read().split()
        s["minflt"], s["majflt"] = int(f[9]), int(f[11])
    except (OSError, IndexError, ValueError):
        pass
    return s


def _disk_sectors():
    """Total sectors (512B) read+written on the physical disk (for I/O rate)."""
    try:
        tot = 0
        for line in open("/proc/diskstats"):
            f = line.split()
            if len(f) >= 10 and f[2] in ("nvme0n1", "sda", "vda"):
                tot += int(f[5]) + int(f[9])
        return tot
    except (OSError, ValueError):
        return None


def _net_bytes():
    """Total non-loopback bytes (rx+tx) — for the egress-proof net rate."""
    try:
        tot = 0
        for line in open("/proc/net/dev"):
            if ":" not in line:
                continue
            name, _, rest = line.partition(":")
            if name.strip() == "lo":
                continue
            f = rest.split()
            if len(f) >= 9:
                tot += int(f[0]) + int(f[8])
        return tot
    except (OSError, ValueError):
        return None


def measure_idle_watts(seconds=4):
    """Idle power baseline for net-over-idle energy. RAPL preferred (energy delta
    over `seconds`); else a few smart-plug readings. None if neither available."""
    if RAPL_DIR:
        e0 = _rapl_uj()
        if e0 is not None:
            time.sleep(seconds)
            j = _rapl_delta_j(e0, _rapl_uj())
            if j is not None:
                return round(j / seconds, 1)
    vals = []
    for _ in range(5):
        w = _plug_power()
        if w is not None:
            vals.append(w)
        time.sleep(0.6)
    return round(sum(vals) / len(vals), 1) if vals else None


def cooldown():
    """Back-compat alias."""
    quiesce()


def _sudo_write(path, val):
    """Best-effort `echo val | sudo -n tee path`. Returns True on success. Uses
    passwordless sudo (already required for RAPL); silently skips if unavailable."""
    try:
        p = subprocess.run(["sudo", "-n", "tee", path], input=f"{val}\n".encode(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        return p.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _fan_control_on():
    try:
        return open("/sys/module/thinkpad_acpi/parameters/fan_control").read().strip() == "Y"
    except OSError:
        return False


def _fan_set(level):
    """Set the ThinkPad fan ('disengaged'=max RPM, 'auto', or 0-7). No-op unless
    thinkpad_acpi was loaded with fan_control=1 (see node-power.sh)."""
    if not _fan_control_on():
        return False
    return _sudo_write(FAN_DEV, f"level {level}")


def _free_memory():
    """Flush dirty pages then (gated) drop caches / reset swap / compact, so each
    model loads from the same clean memory state."""
    try:
        subprocess.run(["sync"], timeout=30)
    except Exception:  # noqa: BLE001
        pass
    if DROP_CACHES:
        _sudo_write("/proc/sys/vm/drop_caches", "3")
    if RESET_SWAP:
        try:
            subprocess.run(["sudo", "-n", "swapoff", "-a"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=120)
            subprocess.run(["sudo", "-n", "swapon", "-a"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=60)
        except Exception:  # noqa: BLE001
            pass
    if DROP_CACHES or RESET_SWAP:
        _sudo_write("/proc/sys/vm/compact_memory", "1")


def quiesce():
    """Per-model reset so every model starts from an identical machine state (the
    C1 thermal-order fix, generalized). Every step is best-effort and env-gated;
    a step that can't run (no sudo, not a ThinkPad) is skipped, never fatal.
    Disclosed as part of the method in PAPER.md §2.

    Sequence: fan -> max RPM, flush & free memory, wait for the package temp
    (and optionally load1) to settle under COOL_TEMP_C/LOAD_SETTLE (capped at
    COOL_MAX_S), then ALWAYS restore the fan to auto. The model was already
    unloaded (keep_alive:0) before this call."""
    if not QUIESCE:
        time.sleep(COOLDOWN_S)
        return
    fan = FAN_MAX and _fan_set("disengaged")   # spin to max so the chip cools fast
    try:
        _free_memory()
        t0 = time.time()
        if COOL_TEMP_C or LOAD_SETTLE:
            while time.time() - t0 < COOL_MAX_S:
                t = _cpu_temp_c()
                hot = bool(COOL_TEMP_C) and (t is not None and t > COOL_TEMP_C)
                try:
                    busy = bool(LOAD_SETTLE) and \
                        float(open("/proc/loadavg").read().split()[0]) > LOAD_SETTLE
                except OSError:
                    busy = False
                if not hot and not busy:
                    break
                time.sleep(2)
        else:
            time.sleep(COOLDOWN_S)
    finally:
        if fan:
            _fan_set("auto")   # restore the firmware fan governor no matter what


_GPU_FREQ_PATHS = glob.glob("/sys/class/drm/card*/gt_act_freq_mhz")


def _gpu_freq_mhz():
    """Intel iGPU actual GT frequency (MHz). ~300 = the idle floor -> direct
    evidence the iGPU does no inference work (Ollama runs CPU-only, no -ngl).
    None if there is no i915 GPU."""
    for p in _GPU_FREQ_PATHS:
        try:
            return int(open(p).read().strip())
        except (OSError, ValueError):
            continue
    return None


PERF_MEMBW = os.environ.get("PERF_MEMBW") == "1"
_PERF_RE = re.compile(r"([\d.]+)\s+([\d,.]+)\s+(?:(?!uncore_imc)\S+\s+)?uncore_imc/(\w+)/")


class PerfBandwidth(threading.Thread):
    """Optional memory-bandwidth(t) via perf uncore IMC counters (needs sudo).
    Parses `perf stat -I 1000` -> per-second read/write MiB/s, and accumulates the
    memory-request split by REQUESTOR (ia=CPU cores, gt=iGPU, io=devices) so a
    gt-share ~ 0 is direct proof the integrated GPU isn't used. Enable PERF_MEMBW=1."""

    _EVENTS = ("data_reads", "data_writes", "ia_requests", "gt_requests", "io_requests")

    def __init__(self):
        super().__init__(daemon=True)
        self.series = []
        self.peak_mb_s = 0.0
        self.req = {"ia_requests": 0.0, "gt_requests": 0.0, "io_requests": 0.0}
        self._proc = None

    def run(self):
        try:
            self._proc = subprocess.Popen(
                ["sudo", "-n", "perf", "stat", "-a", "-e",
                 ",".join(f"uncore_imc/{e}/" for e in self._EVENTS), "-I", "1000"],
                stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        except Exception:  # noqa: BLE001
            return
        cur = {}
        for line in self._proc.stderr:
            m = _PERF_RE.search(line)
            if not m:
                continue
            t, name, val = float(m.group(1)), m.group(3), float(m.group(2).replace(",", ""))
            if cur and abs(t - cur.get("t", t)) > 1e-6:
                self._flush(cur)
                cur = {}
            cur["t"] = t
            cur[name] = val
        if cur:
            self._flush(cur)

    def _flush(self, cur):
        reads, writes = cur.get("data_reads"), cur.get("data_writes")
        if reads is not None and writes is not None:
            tot = reads + writes
            self.peak_mb_s = max(self.peak_mb_s, tot)
            self.series.append({"t": round(cur["t"], 2),
                                "read_mb_s": round(reads, 1),
                                "write_mb_s": round(writes, 1)})
        for r in self.req:
            if cur.get(r) is not None:
                self.req[r] += cur[r]

    def stop(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:  # noqa: BLE001
                pass


PERF_CORE = os.environ.get("PERF_CORE") == "1"
_PERFCORE_RE = re.compile(r"([\d,]+)\s+(instructions|cycles|cache-misses|LLC-load-misses|branch-misses)\b")


class PerfCore(threading.Thread):
    """Optional CPU microarchitecture counters via perf (needs sudo): total
    instructions + cycles (-> IPC), cache-misses, LLC-load-misses, branch-misses
    over the request. These are the contention signals Alibaba's AMTrace uses;
    a low IPC / high LLC-miss rate is the fingerprint of a memory-bound decode.
    Env-gated PERF_CORE=1 (off by default -- extra observer overhead)."""

    _EVENTS = ("instructions", "cycles", "cache-misses", "LLC-load-misses", "branch-misses")

    def __init__(self):
        super().__init__(daemon=True)
        self.counts = {e: 0.0 for e in self._EVENTS}
        self._proc = None

    def run(self):
        try:
            self._proc = subprocess.Popen(
                ["sudo", "-n", "perf", "stat", "-a", "-e", ",".join(self._EVENTS), "-I", "1000"],
                stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        except Exception:  # noqa: BLE001
            return
        for line in self._proc.stderr:
            m = _PERFCORE_RE.search(line)
            if m:
                try:
                    self.counts[m.group(2)] += float(m.group(1).replace(",", ""))
                except (ValueError, KeyError):
                    pass

    def stop(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:  # noqa: BLE001
                pass

    @property
    def derived(self):
        ins, cyc = self.counts.get("instructions", 0), self.counts.get("cycles", 0)
        out = {
            "instructions": int(ins) or None,
            "cycles": int(cyc) or None,
            "ipc": round(ins / cyc, 3) if cyc else None,
            "cache_misses": int(self.counts.get("cache-misses", 0)) or None,
            "llc_load_misses": int(self.counts.get("LLC-load-misses", 0)) or None,
            "branch_misses": int(self.counts.get("branch-misses", 0)) or None,
        }
        return out if any(v for v in out.values()) else None


class Sampler(threading.Thread):
    """Samples RAM/swap every `interval`s; raises an abort flag on mem pressure."""

    def __init__(self, interval=None):
        super().__init__(daemon=True)
        self.interval = interval if interval is not None else SAMPLE_INTERVAL_S
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self.abort_reason: str | None = None
        self.peak_swap_mb = 0
        self.min_avail_mb = 10**9
        self.watts: list[float] = []
        self.peak_watts = 0.0
        self._last_t = None
        self._last_sub = {}     # last RAPL subdomain energies (power(t) breakdown)
        self._last_cpu = None   # last /proc/stat (total, idle) for util(t)
        self._last_disk = None  # last disk sectors (for MB/s)
        self._last_net = None   # last net bytes (for KB/s egress proof)
        self._last_percore = None  # last per-core (total, idle) for per-core util
        self.runner_pid = None
        self.peak_temp_c = 0.0
        self.peak_rss_mb = 0
        self.peak_dram_w = 0.0
        self.peak_gpu_freq = 0

    def set_runner_pid(self, pid):
        """Attach sampling to a runtime child process after it is spawned.

        Ollama keeps a persistent llama-server process that can be discovered at
        sampler start. The direct llama.cpp adapter creates a short-lived child
        after sampling has already begun, so the adapter sets that PID here.
        """
        self.runner_pid = pid

    def run(self):
        t0 = time.time()
        self.runner_pid = _runner_pid()
        while not self._stop.is_set():
            now = time.time()
            dt = (now - self._last_t) if self._last_t else None
            avail, swap = _meminfo()
            if avail is not None:
                self.min_avail_mb = min(self.min_avail_mb, avail)
                if avail < MEM_AVAIL_FLOOR_MB:
                    self.abort_reason = f"oom:mem_avail={avail}MB"
            if swap is not None:
                self.peak_swap_mb = max(self.peak_swap_mb, swap)
                if swap > SWAP_USED_CEIL_MB:
                    self.abort_reason = f"oom:swap={swap}MB"
            watts = _plug_power()
            if watts is not None:
                self.watts.append(watts)
                self.peak_watts = max(self.peak_watts, watts)
            # --- RAPL: domain power(t) + core/uncore/dram breakdown (1 sudo call) ---
            subs = _read_uj_many([RAPL_DIR_ENERGY, RAPL_SUB.get("core"),
                                  RAPL_SUB.get("uncore"), RAPL_SUB.get("dram")])

            def _pw(path):
                cur, prev = subs.get(path), self._last_sub.get(path)
                if cur is not None and prev is not None and dt and dt > 0:
                    j = _rapl_delta_j(prev, cur, RAPL_MAXES.get(path))
                    return round(j / dt, 1) if j is not None else None
                return None
            rapl_w = _pw(RAPL_DIR_ENERGY)
            dram_w, core_w, uncore_w = (_pw(RAPL_SUB.get("dram")),
                                        _pw(RAPL_SUB.get("core")),
                                        _pw(RAPL_SUB.get("uncore")))
            self._last_sub = subs
            if rapl_w is not None:
                self.watts.append(rapl_w)
                self.peak_watts = max(self.peak_watts, rapl_w)
            if dram_w is not None:
                self.peak_dram_w = max(self.peak_dram_w, dram_w)
            # --- thermal / freq / util ---
            temp_c = _cpu_temp_c()
            if temp_c is not None:
                self.peak_temp_c = max(self.peak_temp_c, temp_c)
            freq_mhz = _cpu_freq_mhz()
            gpu_freq = _gpu_freq_mhz()
            if gpu_freq:
                self.peak_gpu_freq = max(self.peak_gpu_freq, gpu_freq)
            util = None
            ctimes = _cpu_times()
            if ctimes and self._last_cpu:
                d_tot = ctimes[0] - self._last_cpu[0]
                d_idle = ctimes[1] - self._last_cpu[1]
                if d_tot > 0:
                    util = round(100 * (1 - d_idle / d_tot), 1)
            self._last_cpu = ctimes
            # per-core util + freq (spatial: which cores, turbo spread)
            core_freq = _percore_freq()
            core_util = None
            pcore = _percore_times()
            if pcore and self._last_percore and len(pcore) == len(self._last_percore):
                core_util = []
                for (tot, idle), (pt, pi) in zip(pcore, self._last_percore):
                    dd = tot - pt
                    core_util.append(round(100 * (1 - (idle - pi) / dd), 1) if dd > 0 else None)
            self._last_percore = pcore
            # --- model runner: RSS / threads / major-faults (thrash) ---
            st = _runner_stats(self.runner_pid)
            rss = st["rss_mb"]
            if rss:
                self.peak_rss_mb = max(self.peak_rss_mb, rss)
            # --- disk + net rates (net ~0 = egress proof of the offline claim) ---
            disk_mb_s = net_kb_s = None
            ds, nb = _disk_sectors(), _net_bytes()
            if ds is not None and self._last_disk is not None and dt and dt > 0:
                disk_mb_s = round((ds - self._last_disk) * 512 / 1e6 / dt, 2)
            if nb is not None and self._last_net is not None and dt and dt > 0:
                net_kb_s = round((nb - self._last_net) / 1024 / dt, 2)
            self._last_disk, self._last_net = ds, nb
            try:
                load1 = float(open("/proc/loadavg").read().split()[0])
            except OSError:
                load1 = None
            self._last_t = now
            self.samples.append({
                "t": round(now - t0, 2),
                "mem_avail_mb": avail, "swap_used_mb": swap, "rss_mb": rss,
                "watts": watts, "rapl_watts": rapl_w,
                "dram_w": dram_w, "core_w": core_w, "uncore_w": uncore_w,
                "cpu_temp_c": temp_c, "cpu_freq_mhz": freq_mhz, "cpu_util_pct": util,
                "gpu_freq_mhz": gpu_freq,
                "threads": st["threads"], "majflt": st["majflt"], "minflt": st["minflt"],
                "ctxt_vol": st["ctxt_vol"], "ctxt_invol": st["ctxt_invol"],
                "core_util": core_util, "core_freq": core_freq,
                "disk_mb_s": disk_mb_s, "net_kb_s": net_kb_s, "load1": load1,
            })
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()


# --------------------------------------------------------------------------
# Runtime calls (Ollama + llama.cpp)
# --------------------------------------------------------------------------
def _load_model_lock() -> dict[str, dict]:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "models.lock.jsonl")
    rows = {}
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    rows[row["model_id"]] = row
    except OSError:
        pass
    return rows


MODEL_LOCK = _load_model_lock()


def _load_llama_cpp_artifacts() -> tuple[dict, dict[str, dict]]:
    if not LLAMA_CPP_ARTIFACTS:
        return {}, {}
    path = LLAMA_CPP_ARTIFACTS
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}, {}
    artifacts = payload.get("artifacts") or []
    return payload, {item.get("model_id"): item for item in artifacts if item.get("model_id")}


LLAMA_CPP_ARTIFACTS_PAYLOAD, LLAMA_CPP_ARTIFACTS_BY_MODEL = _load_llama_cpp_artifacts()


def llama_cpp_artifact_fields(model: str) -> dict:
    item = LLAMA_CPP_ARTIFACTS_BY_MODEL.get(model) or {}
    if not item:
        return {}
    return {
        "llama_cpp.artifact.sample_id": LLAMA_CPP_ARTIFACTS_PAYLOAD.get("sample_id"),
        "llama_cpp.artifact.node": LLAMA_CPP_ARTIFACTS_PAYLOAD.get("node"),
        "llama_cpp.artifact.models_dir": LLAMA_CPP_ARTIFACTS_PAYLOAD.get("models_dir"),
        "llama_cpp.artifact.model_id": item.get("model_id"),
        "llama_cpp.artifact.repo": item.get("repo"),
        "llama_cpp.artifact.filename": item.get("filename"),
        "llama_cpp.artifact.path": item.get("path"),
        "llama_cpp.artifact.size_bytes": item.get("size_bytes"),
        "llama_cpp.artifact.sha256": item.get("sha256"),
        "llama_cpp.artifact.params_b": item.get("params_b"),
        "llama_cpp.artifact.license": item.get("license"),
        "llama_cpp.artifact.license_class": item.get("license_class"),
        "llama_cpp.artifact.license_status": item.get("license_status"),
    }


def _post_json(path, payload, timeout):
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def _server_attrs_from_url(url: str) -> dict:
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:  # noqa: BLE001
        return {}
    return {
        "server.address": parsed.hostname,
        "server.port": parsed.port,
    }


def model_present(model):
    if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
        return resolve_llama_cpp_model_path(model)[0] is not None
    try:
        with _post_json("/api/show", {"model": model}, 30) as r:
            return r.status == 200
    except Exception:
        return False


def _safe_env_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", model).upper()


def _load_llama_cpp_model_map() -> dict[str, str]:
    if not LLAMA_CPP_MODEL_MAP:
        return {}
    try:
        with open(LLAMA_CPP_MODEL_MAP, encoding="utf-8") as handle:
            return json.load(handle)
    except OSError:
        return {}


def _candidate_gguf_paths(model: str) -> list[str]:
    paths = []
    row = MODEL_LOCK.get(model) or {}
    quant = (row.get("quantization") or "").lower()
    needles = []
    if model.startswith("hf.co/"):
        body = model.removeprefix("hf.co/").split(":", 1)[0]
        repo = body.split("/")[-1]
        needles.extend([repo.lower(), repo.lower().replace("-gguf", "")])
    else:
        needles.append(model.lower().replace(":", "-"))
    root = LLAMA_CPP_MODELS_DIR
    try:
        for current, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.lower().endswith(".gguf"):
                    continue
                low = filename.lower()
                if quant and quant.lower() not in low:
                    continue
                if any(needle and needle in low for needle in needles):
                    paths.append(os.path.join(current, filename))
    except OSError:
        pass
    return sorted(paths)


def resolve_llama_cpp_model_path(model: str) -> tuple[str | None, str | None]:
    if os.path.exists(model):
        return model, None
    env_path = os.environ.get(f"LLAMA_CPP_MODEL_{_safe_env_name(model)}")
    if env_path:
        return (env_path, None) if os.path.exists(env_path) else (None, f"mapped path missing: {env_path}")
    model_map = _load_llama_cpp_model_map()
    if model in model_map:
        path = model_map[model]
        return (path, None) if os.path.exists(path) else (None, f"mapped path missing: {path}")
    row = MODEL_LOCK.get(model) or {}
    if row.get("llama_cpp_status") != "direct_gguf":
        return None, f"model is {row.get('llama_cpp_status') or 'not_in_model_lock'}, not direct_gguf"
    candidates = _candidate_gguf_paths(model)
    if len(candidates) == 1:
        return candidates[0], None
    if len(candidates) > 1:
        return None, f"multiple GGUF candidates found under {LLAMA_CPP_MODELS_DIR}: {candidates[:5]}"
    return None, f"no GGUF file found under {LLAMA_CPP_MODELS_DIR}; set LLAMA_CPP_MODEL_MAP or LLAMA_CPP_MODEL_{_safe_env_name(model)}"


def _get_json(path, timeout=10):
    with urllib.request.urlopen(OLLAMA + path, timeout=timeout) as r:
        return json.loads(r.read())


def ollama_ps_snapshot():
    """Compact /api/ps snapshot for stall forensics.

    Full Ollama process payloads can be large and version-specific. The harness
    only needs the evidence that helps classify a zero-token stall: which model
    was resident, how much memory it claimed, and whether the daemon thought it
    was scheduled.
    """
    try:
        data = _get_json("/api/ps", timeout=2)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}:{str(exc)[:120]}"}
    out = []
    for item in data.get("models", []) if isinstance(data, dict) else []:
        out.append({
            "name": item.get("name") or item.get("model"),
            "digest": item.get("digest"),
            "size_vram": item.get("size_vram"),
            "expires_at": item.get("expires_at"),
        })
    return {"models": out}


def runtime_ps_snapshot():
    if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
        return {"runtime": INFERENCE_RUNTIME}
    return ollama_ps_snapshot()


def classify_stall_phase(*, http_connected_at, first_byte_at, first_json_at,
                         first_content_at, done_at, finish):
    if not finish or not str(finish).startswith("DNF"):
        return None
    if http_connected_at is None:
        return "before_response_headers"
    if first_byte_at is None:
        return "before_first_byte"
    if first_json_at is None:
        return "before_first_json"
    if first_content_at is None:
        return "before_first_token"
    if done_at is None:
        return "during_decode"
    return "after_done_missing"


def model_meta(model):
    """Ollama-native model metadata from /api/show (no model load): the EXACT
    parameter count, quantization, native context length and architecture. Makes
    `params` a real feature instead of a bracket guess. Best-effort {}."""
    if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
        row = MODEL_LOCK.get(model) or {}
        return {
            "llama_cpp.status": row.get("llama_cpp_status"),
            "llama_cpp.runtime_options": row.get("runtime_options"),
            "model_lock.params_b": row.get("params_b"),
            "model_lock.tier": row.get("tier"),
            "model_lock.license": row.get("license"),
            "model_lock.license_class": row.get("license_class"),
        }
    try:
        with _post_json("/api/show", {"model": model}, 30) as r:
            d = json.loads(r.read())
    except Exception:  # noqa: BLE001
        return {}
    det, mi = d.get("details") or {}, d.get("model_info") or {}

    def _mi(suffix):
        return next((v for k, v in mi.items() if k.endswith(suffix)), None)
    return {
        "ollama.parameter_count": mi.get("general.parameter_count"),
        "ollama.parameter_size": det.get("parameter_size"),
        "ollama.quantization": det.get("quantization_level"),
        "ollama.family": det.get("family"),
        "ollama.context_length": _mi(".context_length"),
        "ollama.block_count": _mi(".block_count"),
        "ollama.embedding_length": _mi(".embedding_length"),
        "ollama.feed_forward_length": _mi(".feed_forward_length"),
        # GQA: head_count query heads vs head_count_kv KV heads (KV-cache compression)
        "ollama.head_count": _mi(".attention.head_count"),
        "ollama.head_count_kv": _mi(".attention.head_count_kv"),
        # MoE sparsity: experts used per token = the "nodes activated" (0/None = dense)
        "ollama.expert_count": _mi(".expert_count"),
        "ollama.expert_used_count": _mi(".expert_used_count"),
        "ollama.expert_shared_count": _mi(".expert_shared_count"),
        # extra covariates (cheap, can't backfill after the run): quant scheme
        # version, tokenizer + vocab (tokenizer efficiency), RoPE (context scaling).
        "ollama.quantization_version": mi.get("general.quantization_version"),
        "ollama.vocab_size": _mi(".vocab_size"),
        "ollama.rope_freq_base": _mi(".rope.freq_base"),
        "ollama.rope_dimension_count": _mi(".rope.dimension_count"),
        "ollama.tokenizer_model": mi.get("tokenizer.ggml.model"),
        # the model's OWN Modelfile sampler defaults (top_p/top_k/repeat_penalty/stop):
        # run.py pins only temperature+seed+num_predict+num_ctx, so the rest fall back to
        # THESE per-model defaults — captured so the decoding variation is auditable.
        "ollama.parameters": d.get("parameters"),
        "ollama.capabilities": d.get("capabilities"),
    }


def model_runtime(model):
    """Ollama /api/ps view of the loaded model: total size, VRAM bytes (0 = pure
    CPU) and the CPU/GPU split. `size_vram=0` is Ollama's OWN proof that nothing
    is offloaded to the iGPU. Best-effort {}."""
    if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
        path, error = resolve_llama_cpp_model_path(model)
        size = os.path.getsize(path) if path and os.path.exists(path) else None
        return {
            "llama_cpp.model_path": path,
            "llama_cpp.model_error": error,
            "llama_cpp.size_bytes": size,
            "llama_cpp.cli": shutil.which(LLAMA_CPP_CLI) or LLAMA_CPP_CLI,
            "llama_cpp.version": _sh_out([LLAMA_CPP_CLI, "--version"]),
        }
    try:
        d = _get_json("/api/ps", 10)
    except Exception:  # noqa: BLE001
        return {}
    for m in d.get("models", []):
        if model in (m.get("name"), m.get("model")):
            size, vram = m.get("size") or 0, m.get("size_vram") or 0
            return {
                "ollama.size_bytes": size or None,
                "ollama.size_vram_bytes": vram,
                "ollama.cpu_pct": round(100 * (size - vram) / size, 1) if size else None,
                "ollama.gpu_pct": round(100 * vram / size, 1) if size else None,
                # exact model blob identity (sha256) — pins WHICH weights ran, so a
                # re-pulled tag with updated weights is detectable across waves.
                "ollama.digest": m.get("digest"),
            }
    return {}


def ensure_pulled(model, retries=4, backoff_s=10):
    """Pull a model, retrying transient failures. `ollama pull` against the
    registry (esp. hf.co GGUF repos) intermittently drops the connection
    ("Error: EOF"); a single attempt then marks the model pull_failed and skips
    it. Retry with linear backoff so a flaky network doesn't DNF a model that is
    actually available (the wave-2 'Error: EOF' fix)."""
    if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
        path, error = resolve_llama_cpp_model_path(model)
        if path:
            return True
        sys.stderr.write(f"  llama.cpp model unavailable for {model}: {error}\n")
        sys.stderr.flush()
        return False
    if model_present(model):
        return True
    env = {**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")}
    for attempt in range(1, retries + 1):
        sys.stderr.write(f"  pulling {model} (attempt {attempt}/{retries}) …\n")
        sys.stderr.flush()
        rc = subprocess.run(["ollama", "pull", model], env=env)
        if rc.returncode == 0 or model_present(model):
            return True
        if attempt < retries:
            time.sleep(backoff_s * attempt)  # 10s, 20s, 30s — let the registry settle
    sys.stderr.write(f"  pull FAILED after {retries} attempts: {model}\n")
    sys.stderr.flush()
    return False


def unload(model):
    if INFERENCE_RUNTIME == "llama_cpp_server":
        llama_cpp_server_stop()
        return
    if INFERENCE_RUNTIME == "llama_cpp":
        return
    try:
        _post_json("/api/chat", {"model": model, "keep_alive": 0, "messages": []}, 30).read()
    except Exception:
        pass


def remove_model(model):
    """Delete a model from disk (`ollama rm`). Best-effort. Used by --rm-after to
    bound disk during large sweeps: pull -> test -> rm, so the models dir never
    grows past ~one model at a time (the wave-2 'no space left on device' fix)."""
    if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
        return
    try:
        subprocess.run(["ollama", "rm", model],
                       env={**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except Exception:
        pass


def warmup(model, think):
    """Cold-load the model; return load seconds (warmup phase span)."""
    if INFERENCE_RUNTIME == "llama_cpp_server":
        return llama_cpp_server_warmup(model)
    if INFERENCE_RUNTIME == "llama_cpp":
        return llama_cpp_warmup(model)
    t0 = time.time()
    try:
        with _post_json("/api/chat", {
            "model": model, "stream": False, "think": think,
            "messages": [{"role": "user", "content": "ok"}],
            "options": {"num_predict": 1, "num_ctx": NUM_CTX},
        }, 300) as r:
            r.read()
        return round(time.time() - t0, 2), None
    except Exception as e:  # noqa: BLE001
        return round(time.time() - t0, 2), f"warmup_error:{e}"


def run_chat(model, system, user, *, max_tokens, timeout_s, stall_s, think,
             sampler, temperature=0, seed=None):
    """
    Streaming chat under the watchdog. Returns a telemetry dict aligned to
    OTel gen_ai.* plus our phase timings and the raw text.
    """
    if INFERENCE_RUNTIME == "llama_cpp_server":
        return run_llama_cpp_server(model, system, user, max_tokens=max_tokens, timeout_s=timeout_s,
                                    stall_s=stall_s, sampler=sampler, temperature=temperature, seed=seed)
    if INFERENCE_RUNTIME == "llama_cpp":
        return run_llama_cpp(model, system, user, max_tokens=max_tokens, timeout_s=timeout_s,
                             stall_s=stall_s, sampler=sampler, temperature=temperature, seed=seed)
    opts = {"num_predict": max_tokens, "num_ctx": NUM_CTX, "temperature": temperature}
    if seed is not None:
        opts["seed"] = seed  # reproducibility: fixed seed per repetition
    payload = {
        "model": model, "stream": True, "think": think,
        "messages": ([{"role": "system", "content": system}] if system else [])
                    + [{"role": "user", "content": user}],
        "options": opts,
    }
    out, think, ttft, finish = [], [], None, None
    in_tok = out_tok = 0
    total_dur = load_dur = 0
    prefill_s = decode_s = think_s = None
    progress = []   # [t_since_start, cumulative_output_chars]
    tok_times = []  # per-answer-chunk wall timestamps -> inter-token jitter
    t_start = time.time()
    last_tok = t_start
    http_connected_at = first_byte_at = first_json_at = first_content_at = done_at = None
    http_exception = None
    ps_before = runtime_ps_snapshot()
    ps_after = None
    try:
        # socket read timeout = stall window; total wall-clock checked in-loop.
        resp = _post_json("/api/chat", payload, stall_s)
        http_connected_at = round(time.time() - t_start, 3)
        for raw in resp:
            now = time.time()
            if first_byte_at is None:
                first_byte_at = round(now - t_start, 3)
            if now - t_start > timeout_s:
                finish = "DNF:timeout"; break
            if sampler.abort_reason:
                finish = "DNF:" + sampler.abort_reason; break
            line = raw.decode().strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if first_json_at is None:
                first_json_at = round(now - t_start, 3)
            msg = d.get("message") or {}
            tchunk = msg.get("thinking") or ""
            if tchunk:
                if ttft is None:
                    ttft = round(now - t_start, 3)
                if first_content_at is None:
                    first_content_at = round(now - t_start, 3)
                think.append(tchunk); last_tok = now
            chunk = msg.get("content") or ""
            if chunk:
                if ttft is None:
                    ttft = round(now - t_start, 3)
                if first_content_at is None:
                    first_content_at = round(now - t_start, 3)
                if think and think_s is None:
                    think_s = round(now - t_start, 3)  # answer began -> think phase ended
                out.append(chunk)
                last_tok = now
                tok_times.append(now)
                progress.append([round(now - t_start, 2), sum(len(c) for c in out)])
            if d.get("done"):
                done_at = round(now - t_start, 3)
                finish = finish or d.get("done_reason") or "stop"
                in_tok = d.get("prompt_eval_count", 0) or 0
                out_tok = d.get("eval_count", 0) or 0
                ped = d.get("prompt_eval_duration") or 0
                ed = d.get("eval_duration") or 0
                prefill_s = round(ped / 1e9, 3) if ped else None
                decode_s = round(ed / 1e9, 3) if ed else None
                total_dur = d.get("total_duration") or 0
                load_dur = d.get("load_duration") or 0
                break
    except socket.timeout as e:
        finish = "DNF:stall"
        http_exception = f"{type(e).__name__}:{str(e)[:160]}"
    except urllib.error.URLError as e:
        finish = "DNF:stall" if isinstance(getattr(e, "reason", None), socket.timeout) else f"DNF:error:{type(e).__name__}"
        http_exception = f"{type(e).__name__}:{str(e)[:160]}"
    except Exception as e:  # noqa: BLE001
        finish = f"DNF:error:{type(e).__name__}"
        http_exception = f"{type(e).__name__}:{str(e)[:160]}"

    if finish is None:
        finish = "DNF:after_done_missing"
    text = "".join(out)
    wall = round(time.time() - t_start, 2)
    if finish and str(finish).startswith("DNF"):
        ps_after = runtime_ps_snapshot()
    stall_phase = classify_stall_phase(
        http_connected_at=http_connected_at,
        first_byte_at=first_byte_at,
        first_json_at=first_json_at,
        first_content_at=first_content_at,
        done_at=done_at,
        finish=finish,
    )
    # If we broke early without 'done', estimate out_tok by ~chars/4.
    if out_tok == 0 and text:
        out_tok = max(1, len(text) // 4)
    dts = [(tok_times[i] - tok_times[i - 1]) * 1000 for i in range(1, len(tok_times))]
    _dts = sorted(dts)

    def _pct(p):
        if not _dts:
            return None
        k = max(0, min(len(_dts) - 1, int(round(p / 100 * (len(_dts) - 1)))))
        return round(_dts[k], 1)
    return {
        "gen_ai.request.model": model,
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "ollama",
        "gen_ai.output.type": "text",
        "gen_ai.request.stream": True,
        "gen_ai.response.model": model,
        "gen_ai.request.max_tokens": max_tokens,
        "gen_ai.request.temperature": temperature,
        "gen_ai.request.seed": seed,
        "gen_ai.usage.input_tokens": in_tok,
        "gen_ai.usage.output_tokens": out_tok,
        "gen_ai.usage.output_chars": len(text),
        "gen_ai.response.finish_reasons": [finish],
        "gen_ai.server.time_to_first_token_s": ttft,
        "phase.prefill_s": prefill_s,
        "phase.decode_s": decode_s,
        "prefill_tok_s": round(in_tok / prefill_s, 2) if (prefill_s and in_tok) else None,
        "decode_tok_s": round(out_tok / decode_s, 2) if (decode_s and out_tok) else None,
        "wall_s": wall,
        "dnf": finish.startswith("DNF") if finish else False,
        "stall.phase": stall_phase,
        "stall_phase": stall_phase,
        "http.connected_at_s": http_connected_at,
        "http.first_byte_at_s": first_byte_at,
        "http.first_json_at_s": first_json_at,
        "http.first_content_at_s": first_content_at,
        "http.done_at_s": done_at,
        "http_connected_at": http_connected_at,
        "first_byte_at": first_byte_at,
        "first_json_at": first_json_at,
        "first_content_at": first_content_at,
        "done_at": done_at,
        "http.exception": http_exception,
        "socket_exception": http_exception,
        "ollama.ps.before": ps_before,
        "ollama.ps.after": ps_after,
        "progress_trace": progress,   # token-arrival curve (behaviour-over-time)
        "phase.think_s": think_s,
        "gen_ai.thinking.chars": sum(len(c) for c in think),
        "decode.dt_p50_ms": _pct(50),
        "decode.dt_p95_ms": _pct(95),
        "decode.dt_max_ms": round(max(dts), 1) if dts else None,
        "ollama.total_duration_s": round(total_dur / 1e9, 3) if total_dur else None,
        "ollama.load_duration_s": round(load_dur / 1e9, 3) if load_dur else None,
        **_server_attrs_from_url(OLLAMA),
        "_text": text,
        "_think": "".join(think),
    }


def _llama_cpp_prompt(system: str, user: str) -> str:
    parts = []
    if system:
        parts.append(f"System:\n{system.strip()}")
    parts.append(f"User:\n{user.strip()}\n\nAssistant:\n")
    return "\n\n".join(parts)


def _llama_cpp_cmd(model_path: str, prompt: str, *, max_tokens: int, temperature: float, seed: int | None) -> list[str]:
    cmd = [
        LLAMA_CPP_CLI,
        "-m", model_path,
        "-p", prompt,
        "-n", str(max_tokens),
        "-c", str(NUM_CTX),
        "--temp", str(temperature),
        "--no-display-prompt",
        "-no-cnv",
        "--simple-io",
        "--perf",
    ]
    if seed is not None:
        cmd.extend(["--seed", str(seed)])
    if LLAMA_CPP_EXTRA_ARGS:
        cmd.extend(shlex.split(LLAMA_CPP_EXTRA_ARGS))
    return cmd


def _duration_seconds(value: str, unit: str | None) -> float:
    v = float(value)
    u = (unit or "ms").lower()
    if u.startswith("us") or u.startswith("µs"):
        return v / 1_000_000
    if u.startswith("ms"):
        return v / 1_000
    return v


def _parse_llama_cpp_timings(stderr_text: str | None) -> dict:
    """Parse best-effort libllama timing lines from stderr.

    llama.cpp versions vary their prefixes, but the stable load-bearing phrases
    are `load time`, `prompt eval time`, `eval time`, and `total time`.
    """
    text = stderr_text or ""
    out = {}
    patterns = {
        "load": r"load time\s*=\s*([0-9.]+)\s*([a-zµ]+)",
        "prompt_eval": r"prompt eval time\s*=\s*([0-9.]+)\s*([a-zµ]+)\s*/\s*([0-9]+)\s+tokens?",
        "eval": r"(?<!prompt )eval time\s*=\s*([0-9.]+)\s*([a-zµ]+)\s*/\s*([0-9]+)\s+(?:runs?|tokens?)",
        "total": r"total time\s*=\s*([0-9.]+)\s*([a-zµ]+)",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        seconds = _duration_seconds(match.group(1), match.group(2))
        out[f"llama_cpp.timing.{name}_s"] = round(seconds, 6)
        if name in ("prompt_eval", "eval") and len(match.groups()) >= 3:
            count = int(match.group(3))
            out[f"llama_cpp.timing.{name}_tokens"] = count
            out[f"llama_cpp.timing.{name}_tok_s"] = round(count / seconds, 2) if seconds > 0 else None
    return out


def _parse_llama_cpp_sampler_params(stderr_text: str | None) -> dict:
    text = stderr_text or ""
    fields = {
        "repeat_penalty": "gen_ai.request.repeat_penalty",
        "frequency_penalty": "gen_ai.request.frequency_penalty",
        "presence_penalty": "gen_ai.request.presence_penalty",
        "top_k": "gen_ai.request.top_k",
        "top_p": "gen_ai.request.top_p",
        "min_p": "llama_cpp.sampler.min_p",
        "temperature": "llama_cpp.sampler.temperature",
    }
    out = {}
    for name, key in fields.items():
        match = re.search(rf"\b{name}\s*=\s*([-+0-9.]+)", text)
        if match:
            raw = match.group(1)
            out[key] = int(raw) if raw.lstrip("+-").isdigit() else float(raw)
    return out


def _parse_time_verbose(stderr_text: str | None) -> dict:
    """Parse GNU /usr/bin/time -v resource usage from stderr."""
    text = stderr_text or ""
    mapping = {
        "Maximum resident set size (kbytes)": "llama_cpp.proc.max_rss_kb",
        "Major (requiring I/O) page faults": "llama_cpp.proc.majflt",
        "Minor (reclaiming a frame) page faults": "llama_cpp.proc.minflt",
        "Voluntary context switches": "llama_cpp.proc.ctxt_vol",
        "Involuntary context switches": "llama_cpp.proc.ctxt_invol",
    }
    out = {}
    for label, key in mapping.items():
        match = re.search(rf"{re.escape(label)}:\s*([0-9]+)", text)
        if match:
            out[key] = int(match.group(1))
    cpu_match = re.search(r"Percent of CPU this job got:\s*([0-9.]+)%", text)
    if cpu_match:
        out["llama_cpp.proc.cpu_pct"] = float(cpu_match.group(1))
    if "llama_cpp.proc.max_rss_kb" in out:
        out["mem.peak_rss_mb"] = round(out["llama_cpp.proc.max_rss_kb"] / 1024, 1)
    if "llama_cpp.proc.minflt" in out:
        out["proc.minflt"] = out["llama_cpp.proc.minflt"]
    if "llama_cpp.proc.majflt" in out:
        out["proc.majflt"] = out["llama_cpp.proc.majflt"]
    if "llama_cpp.proc.ctxt_vol" in out or "llama_cpp.proc.ctxt_invol" in out:
        out["proc.ctxt_switches"] = out.get("llama_cpp.proc.ctxt_vol", 0) + out.get("llama_cpp.proc.ctxt_invol", 0)
    return out


def _rusage_fields(usage) -> dict:
    if usage is None:
        return {}
    out = {
        "llama_cpp.proc.max_rss_kb": int(getattr(usage, "ru_maxrss", 0) or 0) or None,
        "llama_cpp.proc.minflt": int(getattr(usage, "ru_minflt", 0) or 0),
        "llama_cpp.proc.majflt": int(getattr(usage, "ru_majflt", 0) or 0),
        "llama_cpp.proc.ctxt_vol": int(getattr(usage, "ru_nvcsw", 0) or 0),
        "llama_cpp.proc.ctxt_invol": int(getattr(usage, "ru_nivcsw", 0) or 0),
        "llama_cpp.proc.user_s": round(float(getattr(usage, "ru_utime", 0.0) or 0.0), 6),
        "llama_cpp.proc.system_s": round(float(getattr(usage, "ru_stime", 0.0) or 0.0), 6),
    }
    if out["llama_cpp.proc.max_rss_kb"]:
        out["mem.peak_rss_mb"] = round(out["llama_cpp.proc.max_rss_kb"] / 1024, 1)
    out["proc.minflt"] = out["llama_cpp.proc.minflt"]
    out["proc.majflt"] = out["llama_cpp.proc.majflt"]
    out["proc.ctxt_switches"] = out["llama_cpp.proc.ctxt_vol"] + out["llama_cpp.proc.ctxt_invol"]
    return out


def _safe_model_slug(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model).strip("_") or "model"


def _sha256_file(path: str) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _llama_cpp_thread_arg() -> str | None:
    args = shlex.split(LLAMA_CPP_EXTRA_ARGS) if LLAMA_CPP_EXTRA_ARGS else []
    for i, item in enumerate(args):
        if item in ("-t", "--threads") and i + 1 < len(args):
            return args[i + 1]
    return None


LLAMA_CPP_BENCH_COMMON_FIELDS = (
    "build_commit", "build_number", "cpu_info", "gpu_info", "backends",
    "model_filename", "model_type", "model_size", "model_n_params",
    "n_batch", "n_ubatch", "n_threads", "cpu_mask", "cpu_strict", "poll",
    "type_k", "type_v", "n_gpu_layers", "n_cpu_moe", "split_mode",
    "main_gpu", "no_kv_offload", "flash_attn", "devices", "tensor_split",
    "tensor_buft_overrides", "use_mmap", "use_direct_io", "embeddings",
    "no_op_offload", "no_host", "fit_target", "fit_min_ctx",
)

LLAMA_CPP_BENCH_TEST_FIELDS = (
    "n_prompt", "n_gen", "n_depth", "test_time", "avg_ns", "stddev_ns",
    "avg_ts", "stddev_ts", "samples_ns", "samples_ts",
)


def _load_jsonl(path: str) -> list[dict]:
    rows = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
    except OSError:
        pass
    return rows


def _llama_cpp_bench_kind(row: dict) -> str:
    n_prompt = int(row.get("n_prompt") or 0)
    n_gen = int(row.get("n_gen") or 0)
    if n_prompt > 0 and n_gen == 0:
        return "pp"
    if n_prompt == 0 and n_gen > 0:
        return "tg"
    if n_prompt > 0 and n_gen > 0:
        return "pg"
    return "unknown"


def summarize_llama_cpp_bench(bench_path: str) -> dict:
    rows = _load_jsonl(bench_path)
    if not rows:
        return {}
    summary = {
        "llama_cpp.bench.test_summaries": [
            {"kind": _llama_cpp_bench_kind(row), **{k: row.get(k) for k in LLAMA_CPP_BENCH_TEST_FIELDS if k in row}}
            for row in rows
        ]
    }
    first = rows[0]
    for field in LLAMA_CPP_BENCH_COMMON_FIELDS:
        if field in first:
            summary[f"llama_cpp.bench.{field}"] = first.get(field)
    seen_kinds = set()
    for row in rows:
        kind = _llama_cpp_bench_kind(row)
        if kind in seen_kinds:
            continue
        seen_kinds.add(kind)
        for field in LLAMA_CPP_BENCH_TEST_FIELDS:
            if field in row:
                summary[f"llama_cpp.bench.{kind}.{field}"] = row.get(field)
    return summary


def llama_cpp_bench(model: str, outputs_dir: str) -> dict:
    if INFERENCE_RUNTIME != "llama_cpp" or not LLAMA_CPP_BENCH:
        return {}
    if not shutil.which("llama-bench"):
        return {"llama_cpp.bench.error": "llama-bench-not-found"}
    path, error = resolve_llama_cpp_model_path(model)
    if not path:
        return {"llama_cpp.bench.error": f"model-unavailable:{error}"}
    os.makedirs(outputs_dir, exist_ok=True)
    slug = _safe_model_slug(model)
    bench_path = os.path.join(outputs_dir, f"{slug}.llama-bench.jsonl")
    err_path = os.path.join(outputs_dir, f"{slug}.llama-bench.stderr.txt")
    if not os.path.exists(bench_path):
        cmd = [
            "llama-bench", "-m", path,
            "-p", str(LLAMA_CPP_BENCH_PROMPT_TOKENS),
            "-n", str(LLAMA_CPP_BENCH_GEN_TOKENS),
            "-r", str(LLAMA_CPP_BENCH_REPS),
            "-o", "jsonl",
        ]
        thread_arg = _llama_cpp_thread_arg()
        if thread_arg:
            cmd.extend(["-t", thread_arg])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
            with open(bench_path, "w", encoding="utf-8") as handle:
                handle.write(proc.stdout or "")
            if proc.stderr:
                with open(err_path, "w", encoding="utf-8") as handle:
                    handle.write(proc.stderr)
            rc = proc.returncode
        except Exception as exc:  # noqa: BLE001
            with open(err_path, "w", encoding="utf-8") as handle:
                handle.write(f"{type(exc).__name__}:{exc}\n")
            rc = -1
    else:
        rc = 0
    try:
        rows = sum(1 for line in open(bench_path, encoding="utf-8") if line.strip())
    except OSError:
        rows = 0
    stderr_tail = None
    if os.path.exists(err_path):
        try:
            stderr_tail = "\n".join(open(err_path, encoding="utf-8").read().splitlines()[-20:]) or None
        except OSError:
            stderr_tail = None
    return {
        "llama_cpp.bench.path": bench_path,
        "llama_cpp.bench.sha256": _sha256_file(bench_path),
        "llama_cpp.bench.rows": rows,
        "llama_cpp.bench.repetitions": LLAMA_CPP_BENCH_REPS,
        "llama_cpp.bench.n_prompt": LLAMA_CPP_BENCH_PROMPT_TOKENS,
        "llama_cpp.bench.n_gen": LLAMA_CPP_BENCH_GEN_TOKENS,
        "llama_cpp.bench.returncode": rc,
        "llama_cpp.bench.stderr_tail": stderr_tail,
        **summarize_llama_cpp_bench(bench_path),
    }


def _run_llama_cpp_process(cmd: list[str], *, timeout_s: int, stall_s: int, sampler) -> dict:
    t_start = time.time()
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    chunk_times: list[float] = []
    progress: list[list[float | int]] = []
    ttft = None
    finish = None
    time_bin = "/usr/bin/time" if LLAMA_CPP_TIME_VERBOSE and os.path.exists("/usr/bin/time") else None
    exec_cmd = [time_bin, "-v", *cmd] if time_bin else cmd
    proc = subprocess.Popen(
        exec_cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    if sampler is not None and hasattr(sampler, "set_runner_pid"):
        sampler.set_runner_pid(proc.pid)
    sel = selectors.DefaultSelector()
    if proc.stdout:
        os.set_blocking(proc.stdout.fileno(), False)
        sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
    if proc.stderr:
        os.set_blocking(proc.stderr.fileno(), False)
        sel.register(proc.stderr, selectors.EVENT_READ, "stderr")
    last_output = t_start
    open_streams = len(sel.get_map())
    while open_streams:
        now = time.time()
        if now - t_start > timeout_s:
            finish = "DNF:timeout"
            proc.kill()
        elif sampler is not None and getattr(sampler, "abort_reason", None):
            finish = "DNF:" + sampler.abort_reason
            proc.kill()
        elif now - last_output > stall_s:
            finish = "DNF:stall"
            proc.kill()
        events = sel.select(timeout=0.1)
        if not events and proc.poll() is not None:
            # The process can exit just before /usr/bin/time writes its final
            # resource report. Keep draining registered pipes to EOF instead of
            # breaking on the first empty select after process exit.
            events = [(key, selectors.EVENT_READ) for key in list(sel.get_map().values())]
        for key, _ in events:
            stream = key.fileobj
            name = key.data
            try:
                data = os.read(stream.fileno(), 4096)
            except BlockingIOError:
                continue
            if not data:
                try:
                    sel.unregister(stream)
                except Exception:  # noqa: BLE001
                    pass
                open_streams = len(sel.get_map())
                continue
            if name == "stdout":
                text = decoder.decode(data)
                if text:
                    if ttft is None:
                        ttft = round(time.time() - t_start, 3)
                    stdout_chunks.append(text)
                    last_output = time.time()
                    chunk_times.append(last_output)
                    progress.append([round(last_output - t_start, 2), sum(len(c) for c in stdout_chunks)])
            else:
                stderr_chunks.append(data.decode("utf-8", "replace"))
    usage = None
    try:
        pid, status, usage = os.wait4(proc.pid, 0)
        proc.returncode = os.waitstatus_to_exitcode(status)
    except ChildProcessError:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            pid, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
        except Exception:  # noqa: BLE001
            proc.wait(timeout=5)
    tail = decoder.decode(b"", final=True)
    if tail:
        stdout_chunks.append(tail)
    wall = round(time.time() - t_start, 2)
    if finish is None:
        finish = "stop" if proc.returncode == 0 else f"DNF:error:llama_cpp_rc_{proc.returncode}"
    stdout = "".join(stdout_chunks).strip()
    stderr = "".join(stderr_chunks)
    dts = [(chunk_times[i] - chunk_times[i - 1]) * 1000 for i in range(1, len(chunk_times))]
    dts_sorted = sorted(dts)

    def pct(p):
        if not dts_sorted:
            return None
        idx = max(0, min(len(dts_sorted) - 1, int(round(p / 100 * (len(dts_sorted) - 1)))))
        return round(dts_sorted[idx], 1)

    return {
        "stdout": stdout,
        "stderr": stderr,
        "finish": finish,
        "wall_s": wall,
        "ttft_s": ttft,
        "progress_trace": progress,
        "decode_dt_p50_ms": pct(50),
        "decode_dt_p95_ms": pct(95),
        "decode_dt_max_ms": round(max(dts), 1) if dts else None,
        "resource": _rusage_fields(usage),
    }


def llama_cpp_warmup(model: str) -> tuple[float, str | None]:
    path, error = resolve_llama_cpp_model_path(model)
    if not path:
        return 0.0, f"llama_cpp_model_unavailable:{error}"
    t0 = time.time()
    try:
        subprocess.run(
            _llama_cpp_cmd(path, "ok", max_tokens=1, temperature=0, seed=1),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=300,
            check=False,
        )
        return round(time.time() - t0, 2), None
    except Exception as exc:  # noqa: BLE001
        return round(time.time() - t0, 2), f"warmup_error:{type(exc).__name__}:{str(exc)[:160]}"


def run_llama_cpp(model: str, system: str, user: str, *, max_tokens: int,
                  timeout_s: int, stall_s: int, sampler, temperature: float, seed: int | None) -> dict:
    path, error = resolve_llama_cpp_model_path(model)
    prompt = _llama_cpp_prompt(system, user)
    t_start = time.time()
    if not path:
        return {
            "gen_ai.request.model": model,
            "gen_ai.operation.name": "completion",
            "gen_ai.provider.name": "llama_cpp",
            "gen_ai.output.type": "text",
            "gen_ai.request.stream": True,
            "gen_ai.response.model": model,
            "gen_ai.request.max_tokens": max_tokens,
            "gen_ai.request.temperature": temperature,
            "gen_ai.request.seed": seed,
            "gen_ai.usage.input_tokens": max(1, len(prompt) // 4),
            "gen_ai.usage.output_tokens": 0,
            "gen_ai.usage.output_chars": 0,
            "gen_ai.response.finish_reasons": ["DNF:runtime_unsupported"],
            "gen_ai.server.time_to_first_token_s": None,
            "phase.prefill_s": None,
            "phase.decode_s": None,
            "prefill_tok_s": None,
            "decode_tok_s": None,
            "wall_s": 0.0,
            "dnf": True,
            "stall.phase": "before_runtime",
            "stall_phase": "before_runtime",
            "http.exception": None,
            "socket_exception": None,
            "ollama.ps.before": {"runtime": "llama_cpp"},
            "ollama.ps.after": {"runtime": "llama_cpp", "error": error},
            "llama_cpp.model_error": error,
            "progress_trace": [],
            "phase.think_s": None,
            "gen_ai.thinking.chars": 0,
            "decode.dt_p50_ms": None,
            "decode.dt_p95_ms": None,
            "decode.dt_max_ms": None,
            "_text": "",
            "_think": "",
        }
    cmd = _llama_cpp_cmd(path, prompt, max_tokens=max_tokens, temperature=temperature, seed=seed)
    proc = _run_llama_cpp_process(cmd, timeout_s=timeout_s, stall_s=stall_s, sampler=sampler)
    wall = proc["wall_s"]
    text = proc["stdout"]
    finish = proc["finish"]
    stderr_text = proc["stderr"]
    stderr_tail = "\n".join((stderr_text or "").splitlines()[-20:]) or None
    timing = _parse_llama_cpp_timings(stderr_text)
    sampler_params = _parse_llama_cpp_sampler_params(stderr_text)
    proc_resource = {**proc.get("resource", {}), **_parse_time_verbose(stderr_text)}
    parsed_in = timing.get("llama_cpp.timing.prompt_eval_tokens")
    parsed_out = timing.get("llama_cpp.timing.eval_tokens")
    out_tok = parsed_out if parsed_out is not None else (max(1, len(text) // 4) if text else 0)
    in_tok = parsed_in if parsed_in is not None else max(1, len(prompt) // 4)
    prefill_s = timing.get("llama_cpp.timing.prompt_eval_s")
    decode_s = timing.get("llama_cpp.timing.eval_s") or (wall if out_tok else None)
    token_source = "llama_cpp_timing" if parsed_in is not None or parsed_out is not None else "char_estimate"
    return {
        "gen_ai.request.model": model,
        "gen_ai.operation.name": "completion",
        "gen_ai.provider.name": "llama_cpp",
        "gen_ai.output.type": "text",
        "gen_ai.request.stream": True,
        "gen_ai.response.model": model,
        "gen_ai.request.max_tokens": max_tokens,
        "gen_ai.request.temperature": temperature,
        "gen_ai.request.seed": seed,
        "gen_ai.usage.input_tokens": in_tok,
        "gen_ai.usage.output_tokens": out_tok,
        "gen_ai.usage.token_source": token_source,
        "gen_ai.usage.output_chars": len(text),
        "gen_ai.response.finish_reasons": [finish],
        "gen_ai.server.time_to_first_token_s": proc["ttft_s"],
        "phase.prefill_s": prefill_s,
        "phase.decode_s": decode_s,
        "prefill_tok_s": round(in_tok / prefill_s, 2) if (prefill_s and in_tok) else timing.get("llama_cpp.timing.prompt_eval_tok_s"),
        "decode_tok_s": round(out_tok / decode_s, 2) if decode_s and out_tok else None,
        "wall_s": wall,
        "dnf": finish.startswith("DNF"),
        "stall.phase": "subprocess_timeout" if finish == "DNF:timeout" else None,
        "stall_phase": "subprocess_timeout" if finish == "DNF:timeout" else None,
        "http.exception": None,
        "socket_exception": None,
        "ollama.ps.before": {"runtime": "llama_cpp"},
        "ollama.ps.after": {"runtime": "llama_cpp"},
        "llama_cpp.model_path": path,
        "llama_cpp.cli": shutil.which(LLAMA_CPP_CLI) or LLAMA_CPP_CLI,
        "llama_cpp.command_args": [arg for arg in cmd if arg != prompt],
        "llama_cpp.stderr_tail": stderr_tail,
        **timing,
        **sampler_params,
        **proc_resource,
        "progress_trace": proc["progress_trace"],
        "phase.think_s": None,
        "gen_ai.thinking.chars": 0,
        "decode.dt_p50_ms": proc["decode_dt_p50_ms"],
        "decode.dt_p95_ms": proc["decode_dt_p95_ms"],
        "decode.dt_max_ms": proc["decode_dt_max_ms"],
        "_text": text,
        "_think": "",
    }


LLAMA_CPP_SERVER_PROC: subprocess.Popen | None = None
LLAMA_CPP_SERVER_MODEL: str | None = None
LLAMA_CPP_SERVER_BASE = f"http://{LLAMA_CPP_SERVER_HOST}:{LLAMA_CPP_SERVER_PORT}"


def _server_json(path: str, payload: dict | None = None, timeout: int = 10):
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(LLAMA_CPP_SERVER_BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return json.loads(body.decode())
        return body.decode(errors="replace")


def _metrics_map(text: str | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in (text or "").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            continue
        try:
            out[parts[0]] = float(parts[1])
        except ValueError:
            continue
    return out


def _metric_delta(before: dict[str, float], after: dict[str, float], key: str) -> float | None:
    if key not in before and key not in after:
        return None
    return round(float(after.get(key, 0.0) - before.get(key, 0.0)), 6)


def _slots_summary(slots) -> dict:
    if not isinstance(slots, list):
        return {"count": None, "processing": None}
    return {
        "count": len(slots),
        "processing": sum(1 for slot in slots if slot.get("is_processing")),
        "n_ctx": sorted({slot.get("n_ctx") for slot in slots if slot.get("n_ctx") is not None}),
    }


def _probability_summary(probabilities) -> dict:
    probs = probabilities if isinstance(probabilities, list) else []
    logprobs = [item.get("logprob") for item in probs if isinstance(item.get("logprob"), (int, float))]
    margins = []
    for item in probs:
        top = item.get("top_logprobs") if isinstance(item, dict) else None
        if isinstance(top, list) and len(top) >= 2:
            first = top[0].get("logprob")
            second = top[1].get("logprob")
            if isinstance(first, (int, float)) and isinstance(second, (int, float)):
                margins.append(float(first) - float(second))
    top_ns = [len(item.get("top_logprobs") or []) for item in probs if isinstance(item, dict)]
    return {
        "count": len(probs),
        "mean_logprob": round(sum(logprobs) / len(logprobs), 6) if logprobs else None,
        "min_logprob": round(min(logprobs), 6) if logprobs else None,
        "mean_top1_margin": round(sum(margins) / len(margins), 6) if margins else None,
        "top_logprobs_n": max(top_ns) if top_ns else None,
        "token_ids": [item.get("id") for item in probs if isinstance(item, dict) and item.get("id") is not None],
    }


def llama_cpp_server_stop() -> None:
    global LLAMA_CPP_SERVER_PROC, LLAMA_CPP_SERVER_MODEL
    proc = LLAMA_CPP_SERVER_PROC
    LLAMA_CPP_SERVER_PROC = None
    LLAMA_CPP_SERVER_MODEL = None
    if not proc:
        return
    try:
        proc.terminate()
        proc.wait(timeout=15)
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass


def llama_cpp_server_start(model: str) -> tuple[float, str | None]:
    global LLAMA_CPP_SERVER_PROC, LLAMA_CPP_SERVER_MODEL
    if LLAMA_CPP_SERVER_PROC and LLAMA_CPP_SERVER_PROC.poll() is None and LLAMA_CPP_SERVER_MODEL == model:
        return 0.0, None
    llama_cpp_server_stop()
    path, error = resolve_llama_cpp_model_path(model)
    if not path:
        return 0.0, f"llama_cpp_model_unavailable:{error}"
    cmd = [
        LLAMA_CPP_SERVER,
        "-m", path,
        "--host", LLAMA_CPP_SERVER_HOST,
        "--port", str(LLAMA_CPP_SERVER_PORT),
        "--metrics",
        "--props",
        "--slots",
        "--no-webui",
    ]
    if LLAMA_CPP_EXTRA_ARGS:
        cmd.extend(shlex.split(LLAMA_CPP_EXTRA_ARGS))
    t0 = time.time()
    try:
        LLAMA_CPP_SERVER_PROC = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        LLAMA_CPP_SERVER_MODEL = model
        deadline = time.time() + 90
        last_error = None
        while time.time() < deadline:
            if LLAMA_CPP_SERVER_PROC.poll() is not None:
                return round(time.time() - t0, 2), f"llama_server_exited:{LLAMA_CPP_SERVER_PROC.returncode}"
            try:
                _server_json("/health", timeout=1)
                return round(time.time() - t0, 2), None
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.25)
        return round(time.time() - t0, 2), f"llama_server_not_ready:{type(last_error).__name__}:{str(last_error)[:120]}"
    except Exception as exc:  # noqa: BLE001
        LLAMA_CPP_SERVER_PROC = None
        LLAMA_CPP_SERVER_MODEL = None
        return round(time.time() - t0, 2), f"llama_server_start_error:{type(exc).__name__}:{str(exc)[:160]}"


def llama_cpp_server_warmup(model: str) -> tuple[float, str | None]:
    warm_s, err = llama_cpp_server_start(model)
    if err:
        return warm_s, err
    try:
        _server_json("/completion", {"prompt": "ok", "n_predict": 1, "temperature": 0, "cache_prompt": False}, timeout=60)
    except Exception as exc:  # noqa: BLE001
        return warm_s, f"warmup_error:{type(exc).__name__}:{str(exc)[:160]}"
    return warm_s, None


def run_llama_cpp_server(model: str, system: str, user: str, *, max_tokens: int,
                         timeout_s: int, stall_s: int, sampler, temperature: float, seed: int | None) -> dict:
    path, error = resolve_llama_cpp_model_path(model)
    prompt = _llama_cpp_prompt(system, user)
    if not path:
        return {
            "gen_ai.request.model": model,
            "gen_ai.operation.name": "completion",
            "gen_ai.provider.name": "llama_cpp_server",
            "gen_ai.response.finish_reasons": ["DNF:runtime_unsupported"],
            "dnf": True,
            "wall_s": 0.0,
            "decode_tok_s": None,
            "llama_cpp.model_error": error,
            "progress_trace": [],
            "_text": "",
            "_think": "",
        }
    warm_s, start_error = llama_cpp_server_start(model)
    if start_error:
        return {
            "gen_ai.request.model": model,
            "gen_ai.operation.name": "completion",
            "gen_ai.provider.name": "llama_cpp_server",
            "gen_ai.response.finish_reasons": ["DNF:runtime_start_failed"],
            "dnf": True,
            "wall_s": warm_s,
            "decode_tok_s": None,
            "llama_cpp.model_path": path,
            "llama_cpp.server.error": start_error,
            "progress_trace": [],
            "_text": "",
            "_think": "",
        }
    t0 = time.time()
    exception = None
    props = slots_before = slots_after = metrics_before_text = metrics_after_text = None
    prompt_tokens = []
    response = {}
    try:
        props = _server_json("/props", timeout=5)
        slots_before = _server_json("/slots", timeout=5)
        metrics_before_text = _server_json("/metrics", timeout=5)
        try:
            tokenized = _server_json("/tokenize", {"content": prompt}, timeout=10)
            prompt_tokens = tokenized.get("tokens") if isinstance(tokenized, dict) else []
        except Exception:  # noqa: BLE001
            prompt_tokens = []
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": temperature,
            "n_probs": LLAMA_CPP_SERVER_N_PROBS,
            "cache_prompt": False,
        }
        if seed is not None:
            payload["seed"] = seed
        response = _server_json("/completion", payload, timeout=timeout_s)
        metrics_after_text = _server_json("/metrics", timeout=5)
        slots_after = _server_json("/slots", timeout=5)
    except Exception as exc:  # noqa: BLE001
        exception = exc
        try:
            metrics_after_text = _server_json("/metrics", timeout=2)
        except Exception:
            pass
        try:
            slots_after = _server_json("/slots", timeout=2)
        except Exception:
            pass
    wall = round(time.time() - t0, 2)
    if exception is not None:
        finish = "DNF:timeout" if isinstance(exception, TimeoutError) else f"DNF:server_error:{type(exception).__name__}"
        return {
            "gen_ai.request.model": model,
            "gen_ai.operation.name": "completion",
            "gen_ai.provider.name": "llama_cpp_server",
            "gen_ai.output.type": "text",
            "gen_ai.request.stream": False,
            "gen_ai.response.model": model,
            "gen_ai.request.max_tokens": max_tokens,
            "gen_ai.request.temperature": temperature,
            "gen_ai.request.seed": seed,
            "gen_ai.response.finish_reasons": [finish],
            "dnf": True,
            "wall_s": wall,
            "decode_tok_s": None,
            "llama_cpp.model_path": path,
            "llama_cpp.server.base_url": LLAMA_CPP_SERVER_BASE,
            "llama_cpp.server.exception": f"{type(exception).__name__}:{str(exception)[:240]}",
            "llama_cpp.server.metrics_before": metrics_before_text,
            "llama_cpp.server.metrics_after": metrics_after_text,
            "llama_cpp.server.slots_before": slots_before,
            "llama_cpp.server.slots_after": slots_after,
            "progress_trace": [],
            "_text": "",
            "_think": "",
        }
    text = response.get("content") or ""
    timings = response.get("timings") or {}
    probabilities = response.get("completion_probabilities") or []
    prob_summary = _probability_summary(probabilities)
    metrics_before = _metrics_map(metrics_before_text if isinstance(metrics_before_text, str) else "")
    metrics_after = _metrics_map(metrics_after_text if isinstance(metrics_after_text, str) else "")
    stop_type = response.get("stop_type")
    finish = "length" if stop_type == "limit" else "stop"
    out_tok = int(response.get("tokens_predicted") or len(prob_summary.get("token_ids") or []) or max(1, len(text) // 4) if text else 0)
    in_tok = int(response.get("tokens_evaluated") or len(prompt_tokens) or max(1, len(prompt) // 4))
    prompt_s = (timings.get("prompt_ms") / 1000) if isinstance(timings.get("prompt_ms"), (int, float)) else None
    decode_s = (timings.get("predicted_ms") / 1000) if isinstance(timings.get("predicted_ms"), (int, float)) else None
    return {
        "gen_ai.request.model": model,
        "gen_ai.operation.name": "completion",
        "gen_ai.provider.name": "llama_cpp_server",
        "gen_ai.output.type": "text",
        "gen_ai.request.stream": False,
        "gen_ai.response.model": model,
        "gen_ai.request.max_tokens": max_tokens,
        "gen_ai.request.temperature": temperature,
        "gen_ai.request.seed": seed,
        "gen_ai.usage.input_tokens": in_tok,
        "gen_ai.usage.output_tokens": out_tok,
        "gen_ai.usage.output_chars": len(text),
        "gen_ai.usage.token_source": "llama_server",
        "gen_ai.response.finish_reasons": [finish],
        "gen_ai.server.time_to_first_token_s": None,
        "phase.prefill_s": prompt_s,
        "phase.decode_s": decode_s,
        "prefill_tok_s": round(in_tok / prompt_s, 2) if prompt_s and in_tok else timings.get("prompt_per_second"),
        "decode_tok_s": round(out_tok / decode_s, 2) if decode_s and out_tok else timings.get("predicted_per_second"),
        "wall_s": wall,
        "dnf": False,
        "stall.phase": None,
        "stall_phase": None,
        "http.exception": None,
        "socket_exception": None,
        "ollama.ps.before": {"runtime": "llama_cpp_server"},
        "ollama.ps.after": {"runtime": "llama_cpp_server"},
        "llama_cpp.model_path": path,
        "llama_cpp.server.binary": shutil.which(LLAMA_CPP_SERVER) or LLAMA_CPP_SERVER,
        "llama_cpp.server.base_url": LLAMA_CPP_SERVER_BASE,
        "llama_cpp.server.endpoint": "/completion",
        "llama_cpp.server.props.build_info": (props or {}).get("build_info") if isinstance(props, dict) else None,
        "llama_cpp.server.props.total_slots": (props or {}).get("total_slots") if isinstance(props, dict) else None,
        "llama_cpp.server.props.chat_template_sha256": _sha256_text((props or {}).get("chat_template")) if isinstance(props, dict) else None,
        "llama_cpp.server.slots_before": _slots_summary(slots_before),
        "llama_cpp.server.slots_after": _slots_summary(slots_after),
        "llama_cpp.server.metrics.prompt_tokens_delta": _metric_delta(metrics_before, metrics_after, "llamacpp:prompt_tokens_total"),
        "llama_cpp.server.metrics.predicted_tokens_delta": _metric_delta(metrics_before, metrics_after, "llamacpp:tokens_predicted_total"),
        "llama_cpp.server.metrics.prompt_seconds_delta": _metric_delta(metrics_before, metrics_after, "llamacpp:prompt_seconds_total"),
        "llama_cpp.server.metrics.predicted_seconds_delta": _metric_delta(metrics_before, metrics_after, "llamacpp:tokens_predicted_seconds_total"),
        "llama_cpp.server.metrics.decode_calls_delta": _metric_delta(metrics_before, metrics_after, "llamacpp:n_decode_total"),
        "llama_cpp.server.prompt_token_ids": prompt_tokens,
        "llama_cpp.server.prompt_token_count": len(prompt_tokens),
        "llama_cpp.server.output_token_ids": prob_summary["token_ids"],
        "llama_cpp.server.completion_probabilities_count": prob_summary["count"],
        "llama_cpp.server.logprob.mean": prob_summary["mean_logprob"],
        "llama_cpp.server.logprob.min": prob_summary["min_logprob"],
        "llama_cpp.server.logprob.mean_top1_margin": prob_summary["mean_top1_margin"],
        "llama_cpp.server.top_logprobs_n": prob_summary["top_logprobs_n"],
        "llama_cpp.server.stop_type": stop_type,
        "progress_trace": [],
        "phase.think_s": None,
        "gen_ai.thinking.chars": 0,
        "decode.dt_p50_ms": None,
        "decode.dt_p95_ms": None,
        "decode.dt_max_ms": None,
        "_server_capture": {
            "request": {"n_predict": max_tokens, "temperature": temperature, "seed": seed, "n_probs": LLAMA_CPP_SERVER_N_PROBS},
            "props": props,
            "slots_before": slots_before,
            "slots_after": slots_after,
            "metrics_before": metrics_before_text,
            "metrics_after": metrics_after_text,
            "prompt_token_ids": prompt_tokens,
            "completion_response": response,
        },
        "_text": text,
        "_think": "",
    }


# --------------------------------------------------------------------------
# Deterministic checks
# --------------------------------------------------------------------------
def _find_json(text):
    """Pull the first JSON array/object out of text (tolerates code fences)."""
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    candidate = m.group(1) if m else text
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = candidate.find(opener), candidate.rfind(closer)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(candidate[i:j + 1])
            except json.JSONDecodeError:
                continue
    return None


_NEG_RE = re.compile(r"(?:not|no|never|avoid|without|n't|do ?n'?t|instead of)\W*$", re.I)


def _hit_unnegated(pattern, text):
    """True if `pattern` matches at least once NOT immediately preceded by a
    negation — so 'do not delete' is not counted as a 'delete' violation, while
    'delete the namespace' is. Fixes both false-pass and false-fail of naive
    substring excludes (per the option-C gold review)."""
    try:
        matches = re.finditer(pattern, text, re.I)
    except re.error:
        matches = re.finditer(re.escape(pattern), text, re.I)
    for m in matches:
        if not _NEG_RE.search(text[max(0, m.start() - 18):m.start()]):
            return True
    return False


def _json_eq(got, exp):
    """Order-insensitive deep equality of two JSON arrays of objects (compares
    actual values, not just shape — closes the all-same-severity loophole)."""
    try:
        norm = lambda a: sorted(json.dumps(x, sort_keys=True) for x in a)
        return isinstance(got, list) and norm(got) == norm(exp)
    except (TypeError, ValueError):
        return False


def _single_fenced_command_block(text):
    match = re.fullmatch(r"\s*```(?:[A-Za-z0-9_+.-]+)?\s*\n(?P<body>.*?)\n```\s*", text, re.S)
    return bool(match and match.group("body").strip() and "```" not in match.group("body"))


def run_checks(text, checks):
    low = text.lower()
    results = []
    for c in checks:
        t = c["type"]
        ok = False
        if t in ("must_include",):
            ok = all(re.search(p.lower(), low) for p in c["patterns"])
        elif t == "any_include":
            ok = any(re.search(p.lower(), low) for p in c["patterns"])
        elif t in ("must_exclude", "must_exclude_action"):
            ok = not any(_hit_unnegated(p.lower(), low) for p in c["patterns"])
        elif t == "must_not_endorse":
            # SAFETY: pass = no affirmative-run/endorsement phrase present
            # (negation-aware: 'don't go ahead' is not an endorsement). The judge
            # is primary; this is the sound secondary signal for the guard class.
            ok = not any(_hit_unnegated(p.lower(), low) for p in c["patterns"])
        elif t == "valid_json_array":
            j = _find_json(text); ok = isinstance(j, list)
        elif t == "json_len":
            j = _find_json(text); ok = isinstance(j, list) and len(j) == c["value"]
        elif t == "json_equals":
            ok = _json_eq(_find_json(text), c["value"])
        elif t == "json_keys":
            j = _find_json(text)
            ok = isinstance(j, list) and all(
                isinstance(it, dict) and set(it.keys()) == set(c["value"]) for it in j)
        elif t == "json_field_values":
            j = _find_json(text)
            ok = isinstance(j, list) and all(
                isinstance(it, dict) and it.get(c["field"]) in c["allowed"] for it in j)
        elif t == "regex":
            ok = bool(re.search(c["pattern"], text, re.I | re.S))
        elif t == "single_fenced_command_block":
            ok = _single_fenced_command_block(text)
        results.append({"desc": c.get("desc", t), "type": t, "pass": bool(ok)})
    passed = sum(1 for r in results if r["pass"])
    return passed, len(results), results


def _sha256_text(text: str | None) -> str | None:
    return hashlib.sha256((text or "").encode()).hexdigest() if text is not None else None


def _json_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _prompt_user_content(s, memory_context=""):
    memory = ""
    if memory_context:
        memory = ("--- HOMELAB MEMORY ---\n"
                  "The following is stable, curated background about the homelab. "
                  "Use it only when it is relevant to the scenario; the scenario "
                  "context remains authoritative for incident-specific facts.\n"
                  f"{memory_context}\n\n")
    return f"{memory}--- CONTEXT ---\n{s['context']}\n\n--- TASK ---\n{s['question']}"


def _otel_text_part(content: str) -> dict:
    return {"type": "text", "content": content}


def _chat_message(role: str, content: str) -> dict:
    return {"role": role, "parts": [_otel_text_part(content)]}


def prompt_capture_fields(s, memory_context, prompt):
    user_content = _prompt_user_content(s, memory_context)
    checks = s.get("deterministic_checks") or []
    gold = s.get("gold_answer")
    rubric = s.get("judge_rubric")
    lifecycle = s.get("lifecycle") or {}
    fields = {
        "prompt.capture.enabled": CAPTURE_PROMPT_CONTENT,
        "prompt.capture.policy": PROMPT_CAPTURE_POLICY,
        "prompt.template_id": PROMPT_TEMPLATE_ID,
        "prompt.template_sha256": _sha256_text(PROMPT_SYSTEM_INSTRUCTIONS),
        "prompt.sha256": _sha256_text(prompt),
        "prompt.user_content_sha256": _sha256_text(user_content),
        "scenario.context_sha256": _sha256_text(s.get("context") or ""),
        "scenario.question_sha256": _sha256_text(s.get("question") or ""),
        "scenario.gold_answer_sha256": _sha256_text(gold) if gold is not None else None,
        "scenario.judge_rubric_sha256": _sha256_text(rubric) if rubric is not None else None,
        "scenario.deterministic_checks_sha256": _json_sha256(checks),
        "scenario.lifecycle_sha256": _json_sha256(lifecycle) if lifecycle else None,
        "distill.example_schema": "chat_sft_v1",
        "distill.input_sha256": _sha256_text(prompt),
        "distill.reference_answer_sha256": _sha256_text(gold) if gold is not None else None,
        "distill.reference_answer_source": "scenario.gold_answer" if gold is not None else None,
        "distill.judge_rubric_sha256": _sha256_text(rubric) if rubric is not None else None,
    }
    if lifecycle:
        operational_object = lifecycle.get("operational_object") or {}
        fault_model = lifecycle.get("fault_model") or {}
        workload_evidence = lifecycle.get("workload_evidence") or {}
        action_surface = lifecycle.get("action_surface") or {}
        evaluator_shape = lifecycle.get("evaluator_shape") or {}
        source_trace = lifecycle.get("source_trace") or {}
        fields.update({
            "scenario.lifecycle.schema_version": lifecycle.get("schema_version"),
            "scenario.lifecycle.operational_object.kind": operational_object.get("kind"),
            "scenario.lifecycle.operational_object.name": operational_object.get("name"),
            "scenario.lifecycle.operational_object.boundary": operational_object.get("boundary"),
            "scenario.lifecycle.task_lifecycle": lifecycle.get("task_lifecycle"),
            "scenario.lifecycle.fault.category": fault_model.get("category"),
            "scenario.lifecycle.fault.manifestation": fault_model.get("manifestation"),
            "scenario.lifecycle.evidence.channels": workload_evidence.get("channels"),
            "scenario.lifecycle.evidence.source_quality": workload_evidence.get("source_quality"),
            "scenario.lifecycle.action.mode": action_surface.get("mode"),
            "scenario.lifecycle.action.destructive_risk": action_surface.get("destructive_risk"),
            "scenario.lifecycle.action.permitted_actions": action_surface.get("permitted_actions"),
            "scenario.lifecycle.action.forbidden_actions": action_surface.get("forbidden_actions"),
            "scenario.lifecycle.evaluator.deterministic_checks": evaluator_shape.get("deterministic_checks"),
            "scenario.lifecycle.evaluator.judge_rubric": evaluator_shape.get("judge_rubric"),
            "scenario.lifecycle.evaluator.runtime_validator": evaluator_shape.get("runtime_validator"),
            "scenario.lifecycle.evaluator.human_review": evaluator_shape.get("human_review"),
            "scenario.lifecycle.evaluator.adversarial_fixtures": evaluator_shape.get("adversarial_fixtures"),
            "scenario.lifecycle.promotion_status": lifecycle.get("promotion_status"),
            "scenario.lifecycle.source.use": source_trace.get("use"),
            "scenario.lifecycle.source.row_status": source_trace.get("row_status"),
            "scenario.lifecycle.source.source_families": source_trace.get("source_families"),
            "scenario.lifecycle.source.rights_gate": source_trace.get("rights_gate"),
        })
    if CAPTURE_PROMPT_CONTENT:
        fields.update({
            "prompt.full": prompt,
            "prompt.user_content": user_content,
            "gen_ai.system_instructions": [_otel_text_part(PROMPT_SYSTEM_INSTRUCTIONS)],
            "gen_ai.input.messages": [_chat_message("user", user_content)],
            "distill.input_messages": [
                {"role": "system", "content": PROMPT_SYSTEM_INSTRUCTIONS},
                {"role": "user", "content": user_content},
            ],
            "distill.reference_answer": gold,
            "distill.judge_rubric": rubric,
        })
    return fields


def output_capture_fields(text: str, finish: str | None):
    fields = {
        "gen_ai.output.sha256": _sha256_text(text or ""),
        "distill.output_sha256": _sha256_text(text or ""),
    }
    if CAPTURE_PROMPT_CONTENT:
        fields.update({
            "gen_ai.output.messages": [_chat_message("assistant", text or "")],
            "distill.output_message": {"role": "assistant", "content": text or "", "finish_reason": finish},
        })
    return fields


def prompt_diagnostics(s, memory_context, prompt):
    context = s.get("context") or ""
    task = s.get("question") or ""
    return {
        "prompt.char_count": len(prompt),
        "prompt.memory_char_count": len(memory_context or ""),
        "prompt.scenario_context_char_count": len(context),
        "prompt.task_char_count": len(task),
        "prompt.estimated_tokens": max(1, len(prompt) // 4),
    }


def resolve_policy(s, *, model, memory_context_id, strategy_id):
    """Effective per-call policy stamped into every row.

    This deliberately changes behaviour under a named policy id so old and new
    regimes never get mixed accidentally in analysis. Scenario caps remain the
    base; memory and known-slow models receive bounded extra prompt-eval budget.
    """
    timeout_s = int(s.get("timeout_s") or DEFAULT_TIMEOUT_S)
    stall_s = int(s.get("stall_s") or DEFAULT_STALL_S)
    max_tokens = int(s.get("max_tokens") or DEFAULT_MAX_TOKENS)
    if MAX_TOKENS_CAP > 0:
        max_tokens = min(max_tokens, MAX_TOKENS_CAP)
    reasons = ["scenario_or_default"]
    model_low = model.lower()
    if memory_context_id != "none":
        timeout_s = int(round(timeout_s * 1.35))
        stall_s = int(round(stall_s * 1.25))
        reasons.append("memory_context")
    if "mistral" in model_low or "qwen3:4b" in model_low:
        timeout_s = int(round(timeout_s * 1.35))
        stall_s = int(round(stall_s * 1.25))
        reasons.append("known_slow_model")
    if strategy_id in ("best_of_3_detcheck", "self_consistency_3"):
        timeout_s = int(round(timeout_s * 1.15))
        reasons.append("multi_candidate_strategy")
    if strategy_id == "evaluator_optimizer_1":
        timeout_s = int(round(timeout_s * 1.25))
        reasons.append("critique_revise_strategy")
    return {
        "timeout_s": min(timeout_s, 600),
        "stall_s": min(stall_s, 120),
        "max_tokens": max_tokens,
        "max_tokens_cap": MAX_TOKENS_CAP or None,
        "timeout_policy_id": DEFAULT_TIMEOUT_POLICY_ID,
        "policy_reasons": reasons,
    }


def with_zero_output_retry(model, system, user, *, max_tokens, timeout_s, stall_s,
                           think, sampler, temperature, seed):
    attempts = []
    for attempt in range(ZERO_OUTPUT_RETRIES + 1):
        # A zero-output stall is usually slow PREFILL, not a hang: a hard scenario on
        # a slow CPU model can need longer than stall_s just to emit the FIRST token.
        # Keep the tight stall_s on the first try (fast-fail a genuine hang), but grant
        # each retry the scenario's full timeout_s as the first-byte budget before
        # recording DNF. Decode-stall protection is unchanged on the first try.
        attempt_stall_s = stall_s if attempt == 0 else timeout_s
        tel = run_chat(
            model, system, user,
            max_tokens=max_tokens, timeout_s=timeout_s, stall_s=attempt_stall_s,
            think=think, sampler=sampler, temperature=temperature, seed=seed,
        )
        attempts.append(tel)
        finish = (tel.get("gen_ai.response.finish_reasons") or [None])[0]
        zero_stall = (
            finish == "DNF:stall"
            and not tel.get("gen_ai.usage.output_tokens")
            and not tel.get("progress_trace")
        )
        if not zero_stall or attempt >= ZERO_OUTPUT_RETRIES:
            tel["effective.retry_count"] = attempt
            tel["effective.retry_reason"] = "zero_output_stall" if attempt else None
            tel["effective.retry_attempts"] = [summarize_candidate(i, item) for i, item in enumerate(attempts)]
            return tel
        unload(model)
        time.sleep(3)
    return attempts[-1]


def summarize_candidate(index, tel, *, selected=False, det=None, selection_reason=None):
    finish = (tel.get("gen_ai.response.finish_reasons") or [None])[0]
    text = tel.get("_text") or ""
    out = {
        "candidate_index": index,
        "selected": selected,
        "finish": finish,
        "dnf": bool(tel.get("dnf")),
        "wall_s": tel.get("wall_s"),
        "input_tokens": tel.get("gen_ai.usage.input_tokens"),
        "output_tokens": tel.get("gen_ai.usage.output_tokens"),
        "output_chars": len(text),
        "completion_sha256": hashlib.sha256(text.encode()).hexdigest() if text else None,
        "completion": text,
        "thinking": tel.get("_think") or None,
        "det_passed": det[0] if det else None,
        "det_total": det[1] if det else None,
        "det_score": round(det[0] / det[1], 3) if det and det[1] else None,
        "stall_phase": tel.get("stall.phase"),
        "retry_count": tel.get("effective.retry_count", 0),
        "selection_reason": selection_reason,
    }
    return out


def _strategy_prompt(strategy_id, strategy_prompt):
    if strategy_id == "single_call_tournament_brief" and strategy_prompt:
        return strategy_prompt.strip()
    return ""


def _revise_prompt(original, critique):
    return (
        "Revise the answer below using the critique. Keep the final answer concise, "
        "specific, and safe. Do not mention the critique process.\n\n"
        "--- ORIGINAL ANSWER ---\n"
        f"{original}\n\n--- CRITIQUE ---\n{critique}\n\n--- REVISED ANSWER ---"
    )


def run_strategy(model, scenario, prompt, *, memory_context, memory_context_id,
                 strategy_id, strategy_prompt, policy, think, sampler,
                 temperature, seed):
    """Run the selected inference strategy and return the final telemetry.

    The durable result row remains one final answer per (model, scenario, rep),
    while strategy candidates are returned as audit metadata and written to a
    sidecar JSONL by the caller. This keeps old analysis shape intact without
    hiding the extra inference calls.
    """
    candidates = []
    strategy_id = strategy_id or "baseline"
    strategy_version = "1"

    def call(candidate_index, user_prompt, call_seed):
        tel = with_zero_output_retry(
            model, "", user_prompt,
            max_tokens=policy["max_tokens"], timeout_s=policy["timeout_s"],
            stall_s=policy["stall_s"], think=think, sampler=sampler,
            temperature=temperature, seed=call_seed,
        )
        text = tel.get("_text") or ""
        det = run_checks(text, scenario.get("deterministic_checks", []))
        candidates.append({"index": candidate_index, "tel": tel, "det": det})
        return tel

    if strategy_id == "baseline":
        selected = call(0, prompt, seed)
        method = "single_call"
        reason = "baseline single generation"
    elif strategy_id == "single_call_tournament_brief":
        brief = _strategy_prompt(strategy_id, strategy_prompt)
        user_prompt = prompt if not brief else f"--- RESPONSE STRATEGY ---\n{brief}\n\n{prompt}"
        selected = call(0, user_prompt, seed)
        method = "single_call_strategy_prompt"
        reason = "strategy prompt injected as inference strategy"
    elif strategy_id == "evaluator_optimizer_1":
        strategy_version = "2"
        first = call(0, prompt, seed)
        critique_prompt = (
            "Critique the answer for factual grounding, safety, missing actions, and overclaiming. "
            "Return a concise critique only.\n\n--- ANSWER ---\n"
            f"{first.get('_text') or ''}"
        )
        critique = call(1, f"{prompt}\n\n{critique_prompt}", seed + 1000)
        revised = call(2, f"{prompt}\n\n{_revise_prompt(first.get('_text') or '', critique.get('_text') or '')}", seed + 2000)
        method = "generate_critique_revise_with_draft_fallback"
        if revised.get("dnf") and not first.get("dnf"):
            selected = first
            reason = "revision DNF; selected original draft fallback"
        else:
            selected = revised
            reason = "selected revised answer after one critique pass"
    elif strategy_id in ("best_of_3_detcheck", "self_consistency_3"):
        for index in range(3):
            call(index, prompt, seed + (index * 1000))
        if strategy_id == "best_of_3_detcheck":
            ranked = sorted(
                candidates,
                key=lambda item: (
                    item["det"][0] / item["det"][1] if item["det"][1] else -1,
                    not item["tel"].get("dnf"),
                    item["tel"].get("gen_ai.usage.output_chars") or 0,
                ),
                reverse=True,
            )
            method = "max_det_score_then_non_dnf"
            reason = "highest deterministic-check score; ties prefer non-DNF and fuller answer"
        else:
            buckets = {}
            for item in candidates:
                key = round(item["det"][0] / item["det"][1], 3) if item["det"][1] else -1
                buckets.setdefault(key, []).append(item)
            best_bucket = max(buckets.items(), key=lambda kv: (len(kv[1]), kv[0]))[1]
            ranked = sorted(best_bucket, key=lambda item: (not item["tel"].get("dnf"), item["tel"].get("gen_ai.usage.output_chars") or 0), reverse=True)
            method = "majority_det_score_bucket"
            reason = "most common deterministic-score bucket; ties prefer non-DNF and fuller answer"
        selected = ranked[0]["tel"]
    else:
        raise ValueError(f"unknown inference_strategy: {strategy_id}")

    selected_index = next(item["index"] for item in candidates if item["tel"] is selected)
    total_wall = round(sum(float(item["tel"].get("wall_s") or 0) for item in candidates), 2)
    total_in = sum(int(item["tel"].get("gen_ai.usage.input_tokens") or 0) for item in candidates)
    total_out = sum(int(item["tel"].get("gen_ai.usage.output_tokens") or 0) for item in candidates)
    retry_total = sum(int(item["tel"].get("effective.retry_count") or 0) for item in candidates)
    candidate_summary = []
    for item in candidates:
        candidate_summary.append(summarize_candidate(
            item["index"], item["tel"], selected=item["index"] == selected_index,
            det=item["det"], selection_reason=reason if item["index"] == selected_index else None,
        ))
    selected["strategy.id"] = strategy_id
    selected["strategy.version"] = strategy_version
    selected["strategy.sample_index"] = 0
    selected["strategy.candidate_count"] = len(candidates)
    selected["strategy.selection_method"] = method
    selected["strategy.selected_candidate"] = selected_index
    selected["strategy.extra_calls"] = max(0, len(candidates) - 1)
    selected["strategy.total_wall_s"] = total_wall
    selected["strategy.total_input_tokens"] = total_in
    selected["strategy.total_output_tokens"] = total_out
    selected["strategy.total_retry_count"] = retry_total
    selected["strategy.failure_mode"] = None if not selected.get("dnf") else (selected.get("gen_ai.response.finish_reasons") or [None])[0]
    selected["strategy.candidates"] = candidate_summary
    selected["strategy.prompt_sha256"] = hashlib.sha256(strategy_prompt.encode()).hexdigest() if strategy_prompt else None
    selected["wall_s"] = total_wall or selected.get("wall_s")
    return selected, candidate_summary


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def load_models(path, only_bracket=None):
    models, bracket = [], None
    for line in open(path):
        s = line.strip()
        if s.startswith("# bracket:"):
            bracket = s.split(":", 1)[1].strip(); continue
        if not s or s.startswith("#"):
            continue
        if only_bracket and bracket != only_bracket:
            continue
        models.append((s, bracket))
    return models


# --------------------------------------------------------------------------
# Reproducibility guard: fingerprint the node's power/turbo/energy/version
# state and refuse to run if it drifts from the frozen manifest. This exists
# because wave1 (Turbo OFF, RAPL package-0) and wave2 (Turbo ON, RAPL psys/
# package-0) silently diverged — the env was never recorded, so the drift was
# invisible until a post-hoc clock analysis. See data/run-manifest.json.
# --------------------------------------------------------------------------
def _read_first(path):
    try:
        return open(path).read().strip()
    except OSError:
        return None


def _sh_out(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        return out or None
    except Exception:  # noqa: BLE001
        return None


def env_fingerprint():
    """Full node fingerprint (static + volatile) for the startup preflight + the
    self-describing env.* stamp on every record."""
    return {**_env_static(), **_env_volatile()}


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _running_procs():
    """Contention check: (# running-state procs, the top non-harness CPU hog).
    Proves nothing heavy is competing with inference at this model's start."""
    try:
        out = subprocess.run(["ps", "-eo", "stat,pcpu,comm", "--sort=-pcpu", "--no-headers"],
                             capture_output=True, text=True, timeout=5).stdout.splitlines()
    except Exception:  # noqa: BLE001
        return None, None
    running = sum(1 for ln in out if ln.strip()[:1] == "R")
    top = None
    for ln in out:
        p = ln.split(None, 2)
        if len(p) == 3 and p[2] not in ("ps", "ollama", "run.py", "python3", "python") and _f(p[1]) > 5:
            top = f"{p[2]}:{p[1]}%"; break
    return running, top


def reset_state_snapshot():
    """Per-model evidence (captured AFTER quiesce, BEFORE the model loads) that the
    node is in the identical reset state: turbo/governor/freq/temp/swap/RAM/load/
    procs. Stamped into every row of the model so 'identical setup' is PROVEN, not
    assumed. reset.ok=False flags a model whose start state drifted (filter it)."""
    avail, swap = _meminfo()
    try:
        load1 = float(open("/proc/loadavg").read().split()[0])
    except OSError:
        load1 = None
    nproc, topproc = _running_procs()
    temp = _cpu_temp_c()
    s = {
        "reset.cpu_no_turbo": _read_first("/sys/devices/system/cpu/intel_pstate/no_turbo"),
        "reset.cpu_governor": _read_first("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "reset.cpu_freq_mhz": _cpu_freq_mhz(),
        "reset.cpu_temp_c": temp,
        "reset.mem_avail_mb": avail,
        "reset.swap_used_mb": swap,
        "reset.load1": load1,
        "reset.running_procs": nproc,
        "reset.top_proc": topproc,
        "reset.perf_event_paranoid": _read_first("/proc/sys/kernel/perf_event_paranoid"),
    }
    warn = []
    if COOL_TEMP_C and temp is not None and temp > COOL_TEMP_C + 8:
        warn.append(f"hot:{temp}C")
    if RESET_SWAP and isinstance(swap, (int, float)) and swap > 200:
        warn.append(f"swap:{swap}MB")
    if isinstance(avail, (int, float)) and avail < MEM_AVAIL_FLOOR_MB:
        warn.append(f"low_mem:{avail}MB")
    if topproc:
        warn.append(f"busy:{topproc}")
    s["reset.ok"] = not warn
    s["reset.warnings"] = ";".join(warn) or None
    return s


def _env_static():
    """Slow-changing node identity (read once per run)."""
    try:
        kernel = os.uname().release
    except Exception:  # noqa: BLE001
        kernel = None
    repo = os.path.dirname(os.path.abspath(__file__))
    git_status = _sh_out(["git", "-C", repo, "status", "--short", "--untracked-files=all"])
    source_dirty, artifact_dirty = _classify_git_status(git_status)
    return {
        "env.host": socket.gethostname(),
        "env.kernel": kernel,
        "env.ollama_version": _sh_out(["ollama", "--version"]),
        "env.ollama_kv_cache_type": os.environ.get("OLLAMA_KV_CACHE_TYPE"),
        "env.ollama_flash_attention": os.environ.get("OLLAMA_FLASH_ATTENTION"),
        "env.inference_runtime": INFERENCE_RUNTIME,
        "env.llama_cpp_cli": shutil.which(LLAMA_CPP_CLI) or LLAMA_CPP_CLI,
        "env.llama_cpp_server": shutil.which(LLAMA_CPP_SERVER) or LLAMA_CPP_SERVER if INFERENCE_RUNTIME == "llama_cpp_server" else None,
        "env.llama_cpp_artifacts": LLAMA_CPP_ARTIFACTS if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES else None,
        "env.llama_cpp_artifacts_sha256": hashlib.sha256(open(LLAMA_CPP_ARTIFACTS, "rb").read()).hexdigest() if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES and LLAMA_CPP_ARTIFACTS and os.path.exists(LLAMA_CPP_ARTIFACTS) else None,
        "env.llama_cpp_version": _sh_out([LLAMA_CPP_CLI, "--version"]) if INFERENCE_RUNTIME == "llama_cpp" else (_sh_out([LLAMA_CPP_SERVER, "--version"]) if INFERENCE_RUNTIME == "llama_cpp_server" else None),
        "env.llama_cpp_git_commit": os.environ.get("LLAMA_CPP_GIT_COMMIT"),
        "env.llama_cpp_git_describe": os.environ.get("LLAMA_CPP_GIT_DESCRIBE"),
        "env.harness_git": _sh_out(["git", "-C", repo, "rev-parse", "--short", "HEAD"]),
        "env.harness_dirty": source_dirty or artifact_dirty,
        "env.harness_source_dirty": source_dirty,
        "env.harness_artifact_dirty": artifact_dirty,
        "env.num_ctx": NUM_CTX,
        "env.sample_interval_s": SAMPLE_INTERVAL_S,
        "env.perf_membw": PERF_MEMBW,
        "env.perf_core": PERF_CORE,
        "env.run_id": os.environ.get("RUN_ID"),
    }


ARTIFACT_STATUS_PREFIXES = (
    "calibration.json",
    "logs/",
    "outputs/",
    "results.",
    "data/runs/",
    "data/run-batches/",
    "data/experiments/",
)


def _classify_git_status(status_text: str | None) -> tuple[bool, bool]:
    """Return (source_dirty, artifact_dirty) for porcelain git status text."""
    source_dirty = False
    artifact_dirty = False
    for raw in (status_text or "").splitlines():
        if not raw.strip():
            continue
        path = raw[3:].strip() if len(raw) > 3 else raw.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path.startswith(ARTIFACT_STATUS_PREFIXES):
            artifact_dirty = True
        else:
            source_dirty = True
    return source_dirty, artifact_dirty


def _env_volatile():
    """Drift-prone power/energy state — cheap sysfs reads, re-read PER MODEL so a
    row's regime is accurate even if the node drifts mid-sweep (turbo/governor can
    be flipped by thermald/cron during a multi-day run; a one-shot startup snapshot
    would silently lie)."""
    return {
        "env.cpu_no_turbo": _read_first("/sys/devices/system/cpu/intel_pstate/no_turbo"),
        "env.cpu_governor": _read_first("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "env.cpu_min_perf_pct": _read_first("/sys/devices/system/cpu/intel_pstate/min_perf_pct"),
        "env.cpu_max_perf_pct": _read_first("/sys/devices/system/cpu/intel_pstate/max_perf_pct"),
        "env.rapl_domain": RAPL_NAME,
        "env.perf_event_paranoid": _read_first("/proc/sys/kernel/perf_event_paranoid"),
    }


def preflight(models, fp, manifest_path, require_models_present=False, protocol=None, scenarios_path=None):
    """Compare the live node fingerprint + protocol args + model presence against the
    frozen manifest. Returns a list of human-readable problems ([] = clean). Model
    presence is only enforced when require_models_present (i.e. --no-pull), so the
    disk-bounded streaming pull+rm sweep (--rm-after) is not blocked."""
    problems = []
    if not (manifest_path and os.path.exists(manifest_path)):
        return [f"manifest not found: {manifest_path!r} (pass --manifest or --allow-unlocked)"]
    try:
        man = json.load(open(manifest_path))
    except Exception as e:  # noqa: BLE001
        return [f"manifest unreadable: {e}"]

    enforce_plat = man.get("enforce_on_platform")
    if enforce_plat and sys.platform.startswith("darwin") and enforce_plat == "linux":
        problems.append(f"node is macOS but manifest targets {enforce_plat!r}; "
                        "this is a dev box, not the experiment node (use --allow-unlocked for local runs)")

    cpu = man.get("cpu", {})
    checks = [
        ("cpu turbo (no_turbo)", cpu.get("intel_pstate.no_turbo"), fp["env.cpu_no_turbo"]),
        ("cpu governor", cpu.get("scaling_governor"), fp["env.cpu_governor"]),
        ("cpu min_perf_pct", cpu.get("min_perf_pct"), fp["env.cpu_min_perf_pct"]),
        ("cpu max_perf_pct", cpu.get("max_perf_pct"), fp["env.cpu_max_perf_pct"]),
        ("rapl_domain", man.get("energy", {}).get("rapl_domain"), fp["env.rapl_domain"]),
        ("num_ctx", man.get("model_runtime", {}).get("num_ctx"), fp["env.num_ctx"]),
    ]
    for name, want, got in checks:
        if want is not None and str(want) != str(got):
            problems.append(f"{name}: manifest wants {want!r}, node has {got!r}")

    tel = man.get("telemetry", {})
    pmax = tel.get("perf_event_paranoid_max")
    pv = fp["env.perf_event_paranoid"]
    if pmax is not None and pv is not None:
        try:
            if int(pv) > int(pmax):
                problems.append(f"perf_event_paranoid={pv} > {pmax}: perf counters (membw/core) may be blocked")
        except ValueError:
            pass
    if tel.get("require_perf_membw") and not fp["env.perf_membw"]:
        problems.append("PERF_MEMBW is off: set PERF_MEMBW=1 (manifest requires membw telemetry)")
    if tel.get("require_perf_core") and not fp["env.perf_core"]:
        problems.append("PERF_CORE is off: set PERF_CORE=1 (manifest requires core telemetry)")

    ceil = cpu.get("freq_ceiling_mhz")
    if ceil:
        cur = []
        for p in glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"):
            v = _read_first(p)
            if v:
                cur.append(int(v) // 1000)
        if cur and max(cur) > ceil:
            problems.append(f"cpu freq {max(cur)} MHz > ceiling {ceil} MHz "
                            "(Turbo appears ON — run scripts/node-power.sh setup)")

    runtime = (protocol or {}).get("inference_runtime") or INFERENCE_RUNTIME
    wantver = man.get("expected", {}).get("ollama_version")
    if wantver and runtime == "ollama":
        got_raw = fp.get("env.ollama_version") or ""
        _gm = re.search(r"\d+\.\d+\.\d+", got_raw)
        _wm = re.search(r"\d+\.\d+\.\d+", str(wantver))
        got_v = _gm.group(0) if _gm else got_raw.strip()
        want_v = _wm.group(0) if _wm else str(wantver).strip()
        if got_v != want_v:
            problems.append(f"ollama version: manifest wants {want_v!r}, node has {got_v!r} "
                            f"(full: {got_raw.strip()!r})")

    # protocol args (temperature/repeats/seed/think) — a stray --temp or --think
    # would otherwise pass the env preflight and silently produce non-wave1 data.
    prot = man.get("protocol", {})
    if protocol:
        for key in ("temperature", "repeats", "seed_base", "think"):
            want = prot.get(key, False if key == "think" else None)
            got = protocol.get(key)
            if want is not None and want != got:
                problems.append(f"protocol {key}: manifest wants {want!r}, run uses {got!r}")
    if scenarios_path and os.path.exists(scenarios_path):
        got_sha = hashlib.sha256(open(scenarios_path, "rb").read()).hexdigest()
        approved = set()
        want_sha = prot.get("scenarios_sha256")
        if want_sha:
            approved.add(want_sha)
        for item in (prot.get("scenario_sets") or {}).values():
            if isinstance(item, dict) and item.get("sha256"):
                approved.add(item["sha256"])
        if approved and got_sha not in approved:
            shown = ", ".join(sorted(s[:12] + "…" for s in approved))
            problems.append(f"scenario set hash {got_sha[:12]}… is not approved by manifest ({shown})")

    if require_models_present and man.get("models_pinned", {}).get("require_all_present"):
        missing = [m for m, _ in models if not model_present(m)]
        if missing:
            shown = ", ".join(missing[:6]) + ("…" if len(missing) > 6 else "")
            problems.append(f"{len(missing)} model(s) not present locally — pre-pull to avoid mid-run "
                            f"pull_failed rows: {shown}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="data/models.txt")
    ap.add_argument("--scenarios", default="data/scenarios.json")
    ap.add_argument("--memory-context", default=None,
                    help="run-level memory/context condition id; defaults to MEMORY_CONTEXT env or none")
    ap.add_argument("--memory-context-file", default="",
                    help="optional markdown memory/context file prepended to every scenario prompt; "
                         "used for memory-conditioned runs")
    ap.add_argument("--inference-strategy", default=None,
                    help="run-level inference strategy id; defaults to INFERENCE_STRATEGY env or baseline")
    ap.add_argument("--strategy-prompt-file", default="",
                    help="optional markdown strategy prompt used by prompt-only strategy variants")
    ap.add_argument("--bracket", help="only run this bracket label (e.g. 0-1B)")
    ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--outputs-dir", default="outputs")
    ap.add_argument("--think", action="store_true", help="enable thinking mode for these models")
    ap.add_argument("--no-pull", action="store_true", help="skip auto-pull; only run present models")
    ap.add_argument("--repeats", type=int, default=1,
                    help="samples per (model x scenario). R>=5 + --temp 0.7 for the powered study; "
                         "default 1 (pilot, deterministic).")
    ap.add_argument("--temp", type=float, default=0.0,
                    help="sampling temperature. 0 = deterministic point estimate (det checks); "
                         "0.7 = variance/CI pass.")
    ap.add_argument("--seed-base", type=int, default=1,
                    help="first seed; repetition r uses seed-base + r (fixed -> reproducible).")
    ap.add_argument("--shuffle", action="store_true",
                    help="randomize model order (anti thermal-carryover / run-order confound)")
    ap.add_argument("--order-seed", type=int, default=0, help="deterministic seed for --shuffle")
    ap.add_argument("--rm-after", action="store_true",
                    help="`ollama rm` each model THIS run pulled, after its scenarios finish, "
                         "to bound disk during large sweeps. Models already present before the "
                         "run are KEPT (conservative; never deletes pre-existing models).")
    ap.add_argument("--manifest", default="data/run-manifest.json",
                    help="frozen env-lock manifest; run.py refuses to start if the node has drifted "
                         "from it (turbo/governor/RAPL-domain/perf/models). The run-drift guard.")
    ap.add_argument("--allow-unlocked", action="store_true",
                    help="downgrade preflight failures to warnings (local/dev or Mac runs; "
                         "NEVER for a canonical wave).")
    ap.add_argument("--preflight-only", action="store_true",
                    help="run the env/model preflight, print the fingerprint + result, and exit "
                         "(no models run).")
    ap.add_argument("--limit", type=int, default=0,
                    help="run only the first N models then stop (stop-and-audit: run a couple, audit "
                         "env.* with scripts/audit-run.py, then launch the full sweep).")
    args = ap.parse_args()

    if INFERENCE_RUNTIME not in RUNTIMES:
        sys.exit(f"unknown INFERENCE_RUNTIME={INFERENCE_RUNTIME!r}; expected one of {sorted(RUNTIMES)}")

    os.makedirs(args.outputs_dir, exist_ok=True)
    scen = json.load(open(args.scenarios))["scenarios"]
    memory_context_id = args.memory_context or os.environ.get("MEMORY_CONTEXT") or "none"
    inference_strategy_id = args.inference_strategy or os.environ.get("INFERENCE_STRATEGY") or DEFAULT_INFERENCE_STRATEGY
    if inference_strategy_id not in INFERENCE_STRATEGIES:
        sys.exit(f"unknown inference_strategy={inference_strategy_id!r}; expected one of {sorted(INFERENCE_STRATEGIES)}")
    strategy_prompt = ""
    strategy_prompt_sha = None
    if args.strategy_prompt_file:
        with open(args.strategy_prompt_file, encoding="utf-8") as fh:
            strategy_prompt = fh.read().strip()
        strategy_prompt_sha = hashlib.sha256(open(args.strategy_prompt_file, "rb").read()).hexdigest()
    if inference_strategy_id == "single_call_tournament_brief" and not strategy_prompt:
        sys.exit("single_call_tournament_brief requires --strategy-prompt-file (or STRATEGY_PROMPT_FILE)")
    if args.memory_context_file and memory_context_id == "none":
        sys.exit("--memory-context-file requires --memory-context (or MEMORY_CONTEXT) != none")
    if not args.memory_context_file and memory_context_id != "none":
        sys.exit("--memory-context without --memory-context-file would label an unconditioned run; pass both or use none")
    memory_context = ""
    memory_sha = None
    if args.memory_context_file:
        with open(args.memory_context_file, encoding="utf-8") as fh:
            memory_context = fh.read().strip()
        memory_sha = hashlib.sha256(open(args.memory_context_file, "rb").read()).hexdigest()
    models = load_models(args.models, args.bracket)
    if args.shuffle:
        random.Random(args.order_seed).shuffle(models)

    # --- reproducibility preflight: refuse to run on a drifted node ---------
    env_fp = env_fingerprint()
    _protocol = {"temperature": args.temp, "repeats": args.repeats,
                 "seed_base": args.seed_base, "think": args.think,
                 "inference_strategy": inference_strategy_id,
                 "inference_runtime": INFERENCE_RUNTIME}
    problems = preflight(models, env_fp, args.manifest, require_models_present=args.no_pull,
                         protocol=_protocol, scenarios_path=args.scenarios)
    if args.preflight_only:
        if problems:
            tag = "WARN (unlocked)" if args.allow_unlocked else "FAIL"
            sys.stderr.write(f"PREFLIGHT: {tag}\n" + "\n".join(f"  - {p}" for p in problems) + "\n")
            sys.exit(0 if args.allow_unlocked else 3)
        sys.stderr.write(f"PREFLIGHT: OK \u2014 node matches {args.manifest}\n"
                         + json.dumps(env_fp, indent=2) + "\n")
        sys.exit(0)
    if problems:
        tag = "WARN (unlocked)" if args.allow_unlocked else "FATAL"
        sys.stderr.write(f"PREFLIGHT {tag}: node does not match {args.manifest}\n"
                         + "\n".join(f"  - {p}" for p in problems) + "\n")
        if not args.allow_unlocked:
            sys.stderr.write("Refusing to run a wave on a drifted node. Fix it (scripts/node-power.sh "
                             "setup; RAPL_DOMAIN=package-0; PERF_MEMBW=1 PERF_CORE=1; pre-pull models) "
                             "or pass --allow-unlocked for a non-canonical run.\n")
            sys.exit(3)

    # Per-model drift guard: the startup env_fp is a snapshot; re-read the volatile
    # state before EACH model so a multi-day sweep aborts if the node moves (turbo
    # re-enabled by thermald/cron) instead of silently mislabelling rows.
    env_static = _env_static()
    scenario_sha = hashlib.sha256(open(args.scenarios, "rb").read()).hexdigest()
    env_static["env.scenarios_sha"] = scenario_sha
    env_static["env.scenarios_path"] = args.scenarios
    env_static["env.scenario_set"] = os.environ.get("SCENARIO_SET")
    env_static["env.memory_context"] = memory_context_id
    env_static["env.memory_context_file"] = args.memory_context_file or None
    env_static["env.memory_context_sha"] = memory_sha
    env_static["env.inference_strategy"] = inference_strategy_id
    env_static["env.strategy_prompt_file"] = args.strategy_prompt_file or None
    env_static["env.strategy_prompt_sha"] = strategy_prompt_sha
    _man = {}
    if args.manifest and os.path.exists(args.manifest):
        try:
            _man = json.load(open(args.manifest))
        except Exception:  # noqa: BLE001
            _man = {}
    expected_vol = {
        "env.cpu_no_turbo": _man.get("cpu", {}).get("intel_pstate.no_turbo"),
        "env.cpu_governor": _man.get("cpu", {}).get("scaling_governor"),
        "env.cpu_min_perf_pct": _man.get("cpu", {}).get("min_perf_pct"),
        "env.cpu_max_perf_pct": _man.get("cpu", {}).get("max_perf_pct"),
        "env.rapl_domain": _man.get("energy", {}).get("rapl_domain"),
    }

    sys.stderr.write(f"== {len(models)} models x {len(scen)} scenarios "
                     f"(shuffle={args.shuffle}, sample={SAMPLE_INTERVAL_S}s, runtime={INFERENCE_RUNTIME}, "
                     f"cool_temp={COOL_TEMP_C}, fan_max={FAN_MAX and _fan_control_on()}, "
                     f"drop_caches={DROP_CACHES}, reset_swap={RESET_SWAP}) ==\n")
    idle_w = measure_idle_watts()
    if idle_w is not None:
        sys.stderr.write(f"== idle power baseline: {idle_w} W ==\n")

    # --- model-level resume: skip models already complete in --out (idempotent) ---
    # A model is "complete" when it has a row for every (scenario, rep) unit. A
    # half-finished model (crash mid-model) is re-run from scratch; the duplicate
    # partial rows are harmless and collapse in dedup. This makes the roster
    # recoverable + resumable at MODEL granularity: a re-launch continues where it
    # stopped instead of repeating days of compute.
    expected_pairs = {(s["id"], rep) for s in scen for rep in range(args.repeats)}
    expected_units = len(expected_pairs)
    done_models = set()
    _seen = {}
    current_memory_context = env_static.get("env.memory_context")
    current_memory_sha = env_static.get("env.memory_context_sha")
    current_strategy = env_static.get("env.inference_strategy")
    current_strategy_sha = env_static.get("env.strategy_prompt_sha")
    if os.path.exists(args.out):
        with open(args.out) as _f:
            for _ln in _f:
                _ln = _ln.strip()
                if not _ln:
                    continue
                try:
                    _r = json.loads(_ln)
                except Exception:  # noqa: BLE001
                    continue
                _m = _r.get("model")
                pair = (_r.get("scenario"), _r.get("rep"))
                row_sha = _r.get("env.scenarios_sha")
                if (_m and pair in expected_pairs and _r.get("det_total") is not None
                    and row_sha == scenario_sha
                    and (_r.get("env.memory_context") or "none") == current_memory_context
                    and _r.get("env.memory_context_sha") == current_memory_sha
                    and (_r.get("env.inference_strategy") or "baseline") == current_strategy
                    and _r.get("env.strategy_prompt_sha") == current_strategy_sha):
                    _seen.setdefault(_m, set()).add(pair)
            done_models = {m for m, u in _seen.items() if expected_pairs <= u}
        if done_models:
            sys.stderr.write(f"== resume: {len(done_models)} model(s) already complete in "
                             f"{args.out}; skipping them ==\n")

    with open(args.out, "a") as fout:
        ran = 0
        for (model, bracket) in models:
            if model in done_models:
                continue                      # model-level resume: already complete
            if args.limit and ran >= args.limit:
                sys.stderr.write(f"== --limit {args.limit} reached; stopping for audit "
                                 f"(scripts/audit-run.py {args.out}) ==\n")
                break
            ran += 1
            # re-read the drift-prone state for THIS model; abort if the node moved.
            env_fp = {**env_static, **_env_volatile()}
            _drift = [f"{k}={env_fp.get(k)!r}!={v!r}"
                      for k, v in expected_vol.items()
                      if v is not None and str(env_fp.get(k)) != str(v)]
            if _drift and not args.allow_unlocked:
                sys.stderr.write(f"FATAL: node drifted mid-run before {model}: "
                                 + "; ".join(_drift) + "\nRe-lock (scripts/node-power.sh setup) "
                                 "and resume; rows already written are fine.\n")
                sys.exit(4)
            # per-model identical-state EVIDENCE (turbo/temp/swap/ram/procs), captured
            # after the previous model's quiesce -> proves each model starts clean.
            env_fp = {**env_fp, **reset_state_snapshot()}
            if not env_fp.get("reset.ok"):
                sys.stderr.write(f"  reset-state WARN for {model}: {env_fp.get('reset.warnings')}\n")
            # was the model on disk before this run? (decides --rm-after cleanup)
            was_present = model_present(model)
            if not args.no_pull and not ensure_pulled(model):
                fatal = "runtime_model_unavailable" if INFERENCE_RUNTIME == "llama_cpp" else "pull_failed"
                row = {"model": model, "bracket": bracket, "fatal": fatal,
                       "ts": time.time(), **env_fp}
                fout.write(json.dumps(row) + "\n"); fout.flush()
                continue
            if args.no_pull and not model_present(model):
                continue
            warm_s, warm_err = warmup(model, args.think)
            meta = {**model_meta(model), **model_runtime(model)}
            if INFERENCE_RUNTIME in LLAMA_CPP_RUNTIMES:
                meta.update(llama_cpp_artifact_fields(model))
            if INFERENCE_RUNTIME == "llama_cpp":
                meta.update(llama_cpp_bench(model, args.outputs_dir))
            sys.stderr.write(f"[{bracket}] {model}  warmup={warm_s}s  "
                             f"params={meta.get('ollama.parameter_count')} "
                             f"vram={meta.get('ollama.size_vram_bytes')}  "
                             f"(R={args.repeats}, temp={args.temp})\n"); sys.stderr.flush()
            # scenario-level resume: skip (scenario, rep) units already recorded for
            # this model (a re-launch after pause/stop continues where it left off,
            # not from the model's first scenario). Resumed units carry their own
            # reset/env evidence, so the analysis can still tell them apart.
            seen_for_model = _seen.get(model, set())
            for s in scen:
                for rep in range(args.repeats):
                    if (s["id"], rep) in seen_for_model:
                        continue
                    seed = args.seed_base + rep
                    perf = PerfBandwidth() if PERF_MEMBW else None
                    pcore = PerfCore() if PERF_CORE else None
                    if perf:
                        perf.start()
                    if pcore:
                        pcore.start()
                    start_temp = _cpu_temp_c()
                    rapl0 = _rapl_uj()
                    sampler = Sampler(); sampler.start()
                    prompt = build_prompt(s, memory_context)
                    policy = resolve_policy(
                        s,
                        model=model,
                        memory_context_id=memory_context_id,
                        strategy_id=inference_strategy_id,
                    )
                    tel, candidates = run_strategy(
                        model, s, prompt,
                        memory_context=memory_context,
                        memory_context_id=memory_context_id,
                        strategy_id=inference_strategy_id,
                        strategy_prompt=strategy_prompt,
                        policy=policy,
                        think=args.think,
                        sampler=sampler,
                        temperature=args.temp,
                        seed=seed,
                    )
                    sampler.stop(); sampler.join(timeout=2)
                    rapl1 = _rapl_uj()
                    if perf:
                        perf.stop(); perf.join(timeout=2)
                    if pcore:
                        pcore.stop(); pcore.join(timeout=2)
                    text = tel.pop("_text")
                    think_text = tel.pop("_think", "")
                    server_capture = tel.pop("_server_capture", None)
                    suffix = f"__r{rep}" if args.repeats > 1 else ""
                    _osafe = model.replace('/', '_').replace(':', '_')
                    if server_capture:
                        server_sidecar = os.path.join(args.outputs_dir, f"{_osafe}__{s['id']}{suffix}.llama-server.json")
                        with open(server_sidecar, "w", encoding="utf-8") as sidecar:
                            json.dump(server_capture, sidecar, sort_keys=True)
                            sidecar.write("\n")
                        tel["llama_cpp.server.sidecar_path"] = server_sidecar
                        tel["llama_cpp.server.sidecar_sha256"] = _sha256_file(server_sidecar)
                        try:
                            tel["llama_cpp.server.sidecar_bytes"] = os.path.getsize(server_sidecar)
                        except OSError:
                            tel["llama_cpp.server.sidecar_bytes"] = None
                    passed, total, detail = run_checks(text, s.get("deterministic_checks", []))
                    # energy: prefer RAPL on-die joules; else smart-plug watts.
                    ej = _rapl_delta_j(rapl0, rapl1)
                    if ej is not None and tel["wall_s"]:
                        power_src = f"rapl:{RAPL_NAME}"
                        mean_w = round(ej / tel["wall_s"], 1)
                        energy_wh = round(ej / 3600, 5)
                    elif sampler.watts:
                        power_src = "plug"
                        mean_w = round(sum(sampler.watts) / len(sampler.watts), 1)
                        energy_wh = round(mean_w * tel["wall_s"] / 3600, 4)
                    else:
                        power_src, mean_w, energy_wh = None, None, None

                    def _sdelta(key):
                        vs = [s[key] for s in sampler.samples if s.get(key) is not None]
                        return (vs[-1] - vs[0]) if len(vs) >= 2 else None
                    _cv = [s for s in sampler.samples if s.get("ctxt_vol") is not None]
                    ctxt_sw = ((_cv[-1]["ctxt_vol"] - _cv[0]["ctxt_vol"]
                                + (_cv[-1].get("ctxt_invol") or 0) - (_cv[0].get("ctxt_invol") or 0))
                               if len(_cv) >= 2 else None)
                    _net = [s.get("net_kb_s") for s in sampler.samples if isinstance(s.get("net_kb_s"), (int, float))]
                    _disk = [s.get("disk_mb_s") for s in sampler.samples if isinstance(s.get("disk_mb_s"), (int, float))]
                    row = {
                        "ts": time.time(), "model": model, "bracket": bracket,
                        "adapter": INFERENCE_RUNTIME,
                        "scenario": s["id"], "class": s["class"],
                        "aiopslab_task": s.get("aiopslab_task"),
                        "grounding": s.get("grounding"),
                        "difficulty": s.get("difficulty"),
                        "pair_id": s.get("pair_id"),
                        "rep": rep, "seed": seed, "temp": args.temp,
                        "think": args.think,
                        "warmup_s": warm_s, "warmup_err": warm_err,
                        "det_passed": passed, "det_total": total, "det_detail": detail,
                        "det_score": round(passed / total, 3) if total else None,
                        "peak_swap_mb": sampler.peak_swap_mb,
                        "min_mem_avail_mb": sampler.min_avail_mb,
                        "power.source": power_src,
                        "power.mean_watts": mean_w,
                        "power.peak_watts": round(sampler.peak_watts, 1) or None,
                        "power.energy_wh": energy_wh,
                        "power.idle_watts": idle_w,
                        "thermal.peak_c": round(sampler.peak_temp_c, 1) or None,
                        "thermal.start_c": start_temp,
                        "mem.peak_rss_mb": sampler.peak_rss_mb or None,
                        "power.peak_dram_w": round(sampler.peak_dram_w, 1) or None,
                        "membw.peak_mb_s": round(perf.peak_mb_s, 1) if perf else None,
                        "membw.series": perf.series if perf else None,
                        "membw.requests": perf.req if perf else None,
                        "mem.rss_start_mb": (sampler.samples[0]["rss_mb"] if sampler.samples else None),
                        "mem.avail_start_mb": (sampler.samples[0]["mem_avail_mb"] if sampler.samples else None),
                        "swap.start_mb": (sampler.samples[0]["swap_used_mb"] if sampler.samples else None),
                        "gpu.peak_freq_mhz": sampler.peak_gpu_freq or None,
                        "perf.core": pcore.derived if pcore else None,
                        "proc.minflt": _sdelta("minflt"),
                        "proc.majflt": _sdelta("majflt"),
                        "proc.ctxt_switches": ctxt_sw,
                        "net.peak_kb_s": round(max(_net), 2) if _net else None,
                        "net.total_kb": round(sum(_net) * SAMPLE_INTERVAL_S, 1) if _net else None,
                        "disk.read_mb": round(sum(_disk) * SAMPLE_INTERVAL_S, 1) if _disk else None,
                        "samples": sampler.samples,
                        "effective.timeout_s": policy["timeout_s"],
                        "effective.stall_s": policy["stall_s"],
                        "effective.max_tokens": policy["max_tokens"],
                        "effective.timeout_policy_id": policy["timeout_policy_id"],
                        "effective.policy_reasons": policy["policy_reasons"],
                        **prompt_diagnostics(s, memory_context, prompt),
                        **prompt_capture_fields(s, memory_context, prompt),
                        **env_fp,
                        **meta,
                        **tel,
                    }
                    # Verbatim model answer (+ thinking trace) retained in the durable
                    # row so a run can be re-judged, shown as a transcript, or a judge
                    # call audited against the actual output. Assigned AFTER the spreads
                    # so a future gen_ai.* telemetry key can never silently clobber the
                    # answer. The judge still reads outputs/<...>.txt; this is the
                    # committed copy.
                    row["gen_ai.completion"] = text
                    finish_reason = (row.get("gen_ai.response.finish_reasons") or [None])[0]
                    row.update(output_capture_fields(text, finish_reason))
                    if CAPTURE_PROMPT_CONTENT and "distill.input_messages" in row:
                        row["distill.messages"] = [*row["distill.input_messages"], row["distill.output_message"]]
                    row["gen_ai.thinking"] = think_text or None
                    fout.write(json.dumps(row) + "\n"); fout.flush()
                    with open(os.path.join(args.outputs_dir, f"{_osafe}__{s['id']}{suffix}.txt"), "w") as o:
                        o.write(text)
                    if think_text:
                        with open(os.path.join(args.outputs_dir, f"{_osafe}__{s['id']}{suffix}.think.txt"), "w") as o:
                            o.write(think_text)
                    if candidates:
                        with open(os.path.join(args.outputs_dir, f"{_osafe}__{s['id']}{suffix}.candidates.jsonl"), "w") as o:
                            for candidate in candidates:
                                o.write(json.dumps({
                                    "model": model,
                                    "scenario": s["id"],
                                    "rep": rep,
                                    "memory_context": memory_context_id,
                                    "inference_strategy": inference_strategy_id,
                                    **candidate,
                                }) + "\n")
                    flag = tel["gen_ai.response.finish_reasons"][0]
                    sys.stderr.write(f"    {s['id']:28} r{rep} det={passed}/{total} "
                                     f"{tel['decode_tok_s']}tok/s {tel['wall_s']}s {flag}\n")
                    sys.stderr.flush()
            # model fully produced all (scenario x rep) rows -> signal the consumer
            # (the judge/commit scheduler) that this model is ready to evaluate.
            with open(args.out + ".done", "a") as _df:
                _df.write(json.dumps({"model": model, "bracket": bracket,
                                      "ts": time.time(), "units": expected_units}) + "\n")
                _df.flush()
                os.fsync(_df.fileno())
            unload(model)
            quiesce()
            # bound disk: drop a model we pulled for this run (keep pre-existing ones)
            if args.rm_after and not was_present:
                remove_model(model)
    sys.stderr.write("== done ==\n")


def build_prompt(s, memory_context=""):
    return f"{PROMPT_SYSTEM_INSTRUCTIONS}\n\n{_prompt_user_content(s, memory_context)}"


if __name__ == "__main__":
    main()
