#!/usr/bin/env python3
"""
run.py — node-side small-model eval runner (stdlib only, runs ON home-ai).

Talks to the local Ollama (127.0.0.1:11434), so it must run on the node:
    scp -r scripts/ai-node/small-model-eval dragos@home-ai.hont.ro:/tmp/sme
    ssh dragos@home-ai.hont.ro 'cd /tmp/sme && python3 run.py --models models.txt'

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
import json
import os
import re
import glob
import hashlib
import random
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

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
# Ollama calls
# --------------------------------------------------------------------------
def _post_json(path, payload, timeout):
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return urllib.request.urlopen(req, timeout=timeout)


def model_present(model):
    try:
        with _post_json("/api/show", {"model": model}, 30) as r:
            return r.status == 200
    except Exception:
        return False


def _get_json(path, timeout=10):
    with urllib.request.urlopen(OLLAMA + path, timeout=timeout) as r:
        return json.loads(r.read())


def model_meta(model):
    """Ollama-native model metadata from /api/show (no model load): the EXACT
    parameter count, quantization, native context length and architecture. Makes
    `params` a real feature instead of a bracket guess. Best-effort {}."""
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
        "ollama.capabilities": d.get("capabilities"),
    }


def model_runtime(model):
    """Ollama /api/ps view of the loaded model: total size, VRAM bytes (0 = pure
    CPU) and the CPU/GPU split. `size_vram=0` is Ollama's OWN proof that nothing
    is offloaded to the iGPU. Best-effort {}."""
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
    try:
        _post_json("/api/chat", {"model": model, "keep_alive": 0, "messages": []}, 30).read()
    except Exception:
        pass


def remove_model(model):
    """Delete a model from disk (`ollama rm`). Best-effort. Used by --rm-after to
    bound disk during large sweeps: pull -> test -> rm, so the models dir never
    grows past ~one model at a time (the wave-2 'no space left on device' fix)."""
    try:
        subprocess.run(["ollama", "rm", model],
                       env={**os.environ, "PATH": "/usr/local/bin:" + os.environ.get("PATH", "")},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except Exception:
        pass


def warmup(model, think):
    """Cold-load the model; return load seconds (warmup phase span)."""
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
    try:
        # socket read timeout = stall window; total wall-clock checked in-loop.
        resp = _post_json("/api/chat", payload, stall_s)
        for raw in resp:
            now = time.time()
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
            msg = d.get("message") or {}
            tchunk = msg.get("thinking") or ""
            if tchunk:
                if ttft is None:
                    ttft = round(now - t_start, 3)
                think.append(tchunk); last_tok = now
            chunk = msg.get("content") or ""
            if chunk:
                if ttft is None:
                    ttft = round(now - t_start, 3)
                if think and think_s is None:
                    think_s = round(now - t_start, 3)  # answer began -> think phase ended
                out.append(chunk)
                last_tok = now
                tok_times.append(now)
                progress.append([round(now - t_start, 2), sum(len(c) for c in out)])
            if d.get("done"):
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
    except socket.timeout:
        finish = "DNF:stall"
    except Exception as e:  # noqa: BLE001
        finish = f"DNF:error:{type(e).__name__}"

    text = "".join(out)
    wall = round(time.time() - t_start, 2)
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
        "progress_trace": progress,   # token-arrival curve (behaviour-over-time)
        "phase.think_s": think_s,
        "gen_ai.thinking.chars": sum(len(c) for c in think),
        "decode.dt_p50_ms": _pct(50),
        "decode.dt_p95_ms": _pct(95),
        "decode.dt_max_ms": round(max(dts), 1) if dts else None,
        "ollama.total_duration_s": round(total_dur / 1e9, 3) if total_dur else None,
        "ollama.load_duration_s": round(load_dur / 1e9, 3) if load_dur else None,
        "_text": text,
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
        results.append({"desc": c.get("desc", t), "type": t, "pass": bool(ok)})
    passed = sum(1 for r in results if r["pass"])
    return passed, len(results), results


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
# invisible until a post-hoc clock analysis. See data/wave1-manifest.json.
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
    return {
        "env.host": socket.gethostname(),
        "env.kernel": kernel,
        "env.ollama_version": _sh_out(["ollama", "--version"]),
        "env.harness_git": _sh_out(
            ["git", "-C", os.path.dirname(os.path.abspath(__file__)), "rev-parse", "--short", "HEAD"]),
        "env.num_ctx": NUM_CTX,
        "env.sample_interval_s": SAMPLE_INTERVAL_S,
        "env.perf_membw": PERF_MEMBW,
        "env.perf_core": PERF_CORE,
    }


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

    wantver = man.get("expected", {}).get("ollama_version")
    if wantver and wantver != fp["env.ollama_version"]:
        problems.append(f"ollama version: manifest wants {wantver!r}, node has {fp['env.ollama_version']!r}")

    # protocol args (temperature/repeats/seed/think) — a stray --temp or --think
    # would otherwise pass the env preflight and silently produce non-wave1 data.
    prot = man.get("protocol", {})
    if protocol:
        for key in ("temperature", "repeats", "seed_base", "think"):
            want = prot.get(key, False if key == "think" else None)
            got = protocol.get(key)
            if want is not None and want != got:
                problems.append(f"protocol {key}: manifest wants {want!r}, run uses {got!r}")
    want_sha = prot.get("scenarios_sha256")
    if want_sha and scenarios_path and os.path.exists(scenarios_path):
        got_sha = hashlib.sha256(open(scenarios_path, "rb").read()).hexdigest()
        if got_sha != want_sha:
            problems.append(f"scenarios.json changed: sha256 {got_sha[:12]}\u2026 != manifest {want_sha[:12]}\u2026")

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
    ap.add_argument("--manifest", default="data/wave1-manifest.json",
                    help="frozen env-lock manifest; run.py refuses to start if the node has drifted "
                         "from it (turbo/governor/RAPL-domain/perf/models). The wave1<->wave2 guard.")
    ap.add_argument("--allow-unlocked", action="store_true",
                    help="downgrade preflight failures to warnings (local/dev or Mac runs; "
                         "NEVER for a canonical wave).")
    ap.add_argument("--preflight-only", action="store_true",
                    help="run the env/model preflight, print the fingerprint + result, and exit "
                         "(no models run).")
    ap.add_argument("--limit", type=int, default=0,
                    help="run only the first N models then stop (stop-and-audit: run a couple, audit "
                         "env.* with scripts/audit-wave.py, then launch the full sweep).")
    args = ap.parse_args()

    os.makedirs(args.outputs_dir, exist_ok=True)
    scen = json.load(open(args.scenarios))["scenarios"]
    models = load_models(args.models, args.bracket)
    if args.shuffle:
        random.Random(args.order_seed).shuffle(models)

    # --- reproducibility preflight: refuse to run on a drifted node ---------
    env_fp = env_fingerprint()
    _protocol = {"temperature": args.temp, "repeats": args.repeats,
                 "seed_base": args.seed_base, "think": args.think}
    problems = preflight(models, env_fp, args.manifest, require_models_present=args.no_pull,
                         protocol=_protocol, scenarios_path=args.scenarios)
    if args.preflight_only:
        if problems:
            sys.stderr.write("PREFLIGHT: FAIL\n" + "\n".join(f"  - {p}" for p in problems) + "\n")
            sys.exit(3)
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
                     f"(shuffle={args.shuffle}, sample={SAMPLE_INTERVAL_S}s, "
                     f"cool_temp={COOL_TEMP_C}, fan_max={FAN_MAX and _fan_control_on()}, "
                     f"drop_caches={DROP_CACHES}, reset_swap={RESET_SWAP}) ==\n")
    idle_w = measure_idle_watts()
    if idle_w is not None:
        sys.stderr.write(f"== idle power baseline: {idle_w} W ==\n")

    with open(args.out, "a") as fout:
        for _mi, (model, bracket) in enumerate(models):
            if args.limit and _mi >= args.limit:
                sys.stderr.write(f"== --limit {args.limit} reached; stopping for audit "
                                 f"(scripts/audit-wave.py {args.out}) ==\n")
                break
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
                row = {"model": model, "bracket": bracket, "fatal": "pull_failed",
                       "ts": time.time(), **env_fp}
                fout.write(json.dumps(row) + "\n"); fout.flush()
                continue
            if args.no_pull and not model_present(model):
                continue
            warm_s, warm_err = warmup(model, args.think)
            meta = {**model_meta(model), **model_runtime(model)}
            sys.stderr.write(f"[{bracket}] {model}  warmup={warm_s}s  "
                             f"params={meta.get('ollama.parameter_count')} "
                             f"vram={meta.get('ollama.size_vram_bytes')}  "
                             f"(R={args.repeats}, temp={args.temp})\n"); sys.stderr.flush()
            for s in scen:
                for rep in range(args.repeats):
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
                    tel = run_chat(
                        model, "", build_prompt(s),
                        max_tokens=s.get("max_tokens", DEFAULT_MAX_TOKENS),
                        timeout_s=s.get("timeout_s", DEFAULT_TIMEOUT_S),
                        stall_s=DEFAULT_STALL_S, think=args.think, sampler=sampler,
                        temperature=args.temp, seed=seed)
                    sampler.stop(); sampler.join(timeout=2)
                    rapl1 = _rapl_uj()
                    if perf:
                        perf.stop(); perf.join(timeout=2)
                    if pcore:
                        pcore.stop(); pcore.join(timeout=2)
                    text = tel.pop("_text")
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
                    row = {
                        "ts": time.time(), "model": model, "bracket": bracket,
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
                        "samples": sampler.samples,
                        **env_fp,
                        **meta,
                        **tel,
                    }
                    fout.write(json.dumps(row) + "\n"); fout.flush()
                    suffix = f"__r{rep}" if args.repeats > 1 else ""
                    with open(os.path.join(args.outputs_dir,
                              f"{model.replace('/', '_').replace(':', '_')}__{s['id']}{suffix}.txt"), "w") as o:
                        o.write(text)
                    flag = tel["gen_ai.response.finish_reasons"][0]
                    sys.stderr.write(f"    {s['id']:28} r{rep} det={passed}/{total} "
                                     f"{tel['decode_tok_s']}tok/s {tel['wall_s']}s {flag}\n")
                    sys.stderr.flush()
            unload(model)
            quiesce()
            # bound disk: drop a model we pulled for this run (keep pre-existing ones)
            if args.rm_after and not was_present:
                remove_model(model)
    sys.stderr.write("== done ==\n")


def build_prompt(s):
    return (f"You are a homelab operations assistant. Use ONLY the information "
            f"given. Be concise and specific.\n\n"
            f"--- CONTEXT ---\n{s['context']}\n\n--- TASK ---\n{s['question']}")


if __name__ == "__main__":
    main()
