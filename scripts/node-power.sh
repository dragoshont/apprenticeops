#!/usr/bin/env bash
# node-power.sh — lock this node into a REPRODUCIBLE power state for the eval,
# and restore it afterwards. Run ON THE NODE. Needs passwordless sudo.
#
#   ./node-power.sh setup      # snapshot current state, then lock it down
#   ./node-power.sh teardown   # restore the snapshot
#   ./node-power.sh status     # print the current state
#
# Why: the audit (i5-8350U, intel_pstate active) showed no TLP/ppd/auto-cpufreq
# and AC power, so the ONLY per-run variance left is dynamic HWP frequency
# scaling (400 MHz–3.6 GHz) + turbo. Pinning to the base clock removes
# thermal-throttle variance, so decode tok/s becomes a function of the MODEL,
# not of how hot the chip happened to be. We also enable ThinkPad fan control so
# run.py's quiesce() can spin the fan to max between models.
#
# Trade-off (disclosed in PAPER §2): pinning to base (~1.7 GHz, turbo off) lowers
# absolute tok/s but is the scientifically cleaner, sustainable, reproducible
# operating point. Use teardown to return the node to normal afterwards.
set -euo pipefail

PSTATE=/sys/devices/system/cpu/intel_pstate
FAN=/proc/acpi/ibm/fan
SNAP=/tmp/sme-power-orig.env
GOVS=(/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor)

have_pstate() { [[ -d "$PSTATE" ]]; }

# Disable Wi-Fi + Bluetooth via the kernel rfkill sysfs (no rfkill CLI needed).
# SAFETY: skips Wi-Fi if the default route is wireless, so we never cut our own
# SSH link. On this node management is Ethernet (enp0s31f6), so both go down.
radios_block() {
  local mgmt; mgmt=$(ip route get 1.1.1.1 2>/dev/null | sed -n 's/.* dev \([^ ]*\).*/\1/p')
  for r in /sys/class/rfkill/rfkill*; do
    [[ -e "$r/soft" ]] || continue
    if [[ "$(cat "$r/type")" == wlan && "$mgmt" == wl* ]]; then
      echo "SKIP Wi-Fi block: management is over $mgmt (would cut SSH)"; continue
    fi
    echo 1 | sudo tee "$r/soft" >/dev/null
  done
}

radios_restore() {
  for r in /sys/class/rfkill/rfkill*; do
    [[ -e "$r/soft" ]] || continue
    local v; v=$(grep -m1 "^RFK_$(basename "$r")=" "$SNAP" 2>/dev/null | cut -d= -f2)
    echo "${v:-0}" | sudo tee "$r/soft" >/dev/null
  done
}

status() {
  echo "governor : $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"
  if have_pstate; then
    echo "no_turbo : $(cat $PSTATE/no_turbo)  (1 = turbo OFF)"
    echo "perf_pct : min=$(cat $PSTATE/min_perf_pct) max=$(cat $PSTATE/max_perf_pct)"
  fi
  echo "EPP      : $(cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference 2>/dev/null)"
  echo "perf_par : $(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null)  (<=2 => perf membw/core readable)"
  echo "fan_ctl  : $(cat /sys/module/thinkpad_acpi/parameters/fan_control 2>/dev/null || echo N)" \
       " level=$(awk '/level/{print $2}' "$FAN" 2>/dev/null) rpm=$(awk '/speed/{print $2}' "$FAN" 2>/dev/null)"
  echo "radios   : $(for r in /sys/class/rfkill/rfkill*; do [[ -e "$r/soft" ]] && printf '%s=%s ' "$(cat "$r/type")" "$([[ $(cat "$r/soft") == 1 ]] && echo blocked || echo on)"; done)"
  echo "freq MHz : $(awk -F: '/MHz/{printf "%d ",$2}' /proc/cpuinfo)"
}

setup() {
  if [[ ! -f "$SNAP" ]]; then
    {
      echo "GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)"
      have_pstate && echo "NOTURBO=$(cat $PSTATE/no_turbo)"
      have_pstate && echo "MINPCT=$(cat $PSTATE/min_perf_pct)"
      have_pstate && echo "MAXPCT=$(cat $PSTATE/max_perf_pct)"
      echo "FANCTL=$(cat /sys/module/thinkpad_acpi/parameters/fan_control 2>/dev/null || echo N)"
      echo "PARANOID=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo 2)"
      for r in /sys/class/rfkill/rfkill*; do [[ -e "$r/soft" ]] && echo "RFK_$(basename "$r")=$(cat "$r/soft")"; done
    } > "$SNAP"
    echo "snapshot -> $SNAP"
  fi
  # 1) governor -> performance (all cores)
  for g in "${GOVS[@]}"; do echo performance | sudo tee "$g" >/dev/null; done
  # 2) pin to BASE clock: disable turbo, min=max=100% (of non-turbo => base)
  if have_pstate; then
    echo 1   | sudo tee "$PSTATE/no_turbo"     >/dev/null
    echo 100 | sudo tee "$PSTATE/max_perf_pct" >/dev/null
    echo 100 | sudo tee "$PSTATE/min_perf_pct" >/dev/null
  fi
  # 3) EPB -> performance (best-effort; EPP is already 'performance')
  sudo x86_energy_perf_policy performance 2>/dev/null || true
  # 3b) allow perf counters (membw + core microarch telemetry) for the non-root
  #     run.py sampler; wave2 silently lost membw/perf on ~14% of runs without this.
  echo 1 | sudo tee /proc/sys/kernel/perf_event_paranoid >/dev/null
  # 4) ThinkPad fan control on (persist + reload so quiesce() can max the fan)
  echo "options thinkpad_acpi fan_control=1" | sudo tee /etc/modprobe.d/thinkpad_acpi-eval.conf >/dev/null
  if [[ "$(cat /sys/module/thinkpad_acpi/parameters/fan_control 2>/dev/null)" != "Y" ]]; then
    if sudo modprobe -r thinkpad_acpi 2>/dev/null && sudo modprobe thinkpad_acpi fan_control=1 2>/dev/null; then
      echo "thinkpad_acpi reloaded with fan_control=1"
    else
      echo "WARN: thinkpad_acpi in use; fan_control will apply after a reboot."
    fi
  fi
  # 5) disable Wi-Fi + Bluetooth (reversible; skips Wi-Fi if mgmt is wireless)
  radios_block
  echo "--- locked ---"; status
}

teardown() {
  [[ -f "$SNAP" ]] || { echo "no snapshot at $SNAP (nothing to restore)"; exit 1; }
  # shellcheck disable=SC1090
  . "$SNAP"
  for g in "${GOVS[@]}"; do echo "${GOV:-powersave}" | sudo tee "$g" >/dev/null; done
  if have_pstate; then
    echo "${MAXPCT:-100}" | sudo tee "$PSTATE/max_perf_pct" >/dev/null
    echo "${MINPCT:-11}"  | sudo tee "$PSTATE/min_perf_pct" >/dev/null
    echo "${NOTURBO:-0}"  | sudo tee "$PSTATE/no_turbo"     >/dev/null
  fi
  sudo x86_energy_perf_policy normal 2>/dev/null || true
  [ -n "${PARANOID:-}" ] && echo "${PARANOID}" | sudo tee /proc/sys/kernel/perf_event_paranoid >/dev/null
  echo "level auto" | sudo tee "$FAN" >/dev/null 2>&1 || true
  radios_restore
  sudo rm -f /etc/modprobe.d/thinkpad_acpi-eval.conf
  rm -f "$SNAP"
  echo "--- restored ---"; status
}

case "${1:-status}" in
  setup)    setup ;;
  teardown) teardown ;;
  status)   status ;;
  *) echo "usage: $0 {setup|teardown|status}" >&2; exit 2 ;;
esac
