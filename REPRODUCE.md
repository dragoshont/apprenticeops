# REPRODUCE — ApprenticeOps

> This is the **reproducibility contract** for the paper. Goal: a stranger with
> Ollama and a CPU can clone, run, and regenerate every number. This file is
> written to be lifted verbatim into the **standalone paper repo** (see
> `## Extracting the standalone repo`).

## 0. What you need

| Requirement | Why | Notes |
|---|---|---|
| **Ollama** ≥ 0.30 | runs the models locally | `ollama serve` on `127.0.0.1:11434` (override `OLLAMA_URL`) |
| **Python ≥ 3.10** | the harness (stdlib only for `run.py`/`baselines.py`) | no pip deps to *run* models |
| **Linux host** for full telemetry | `run.py` reads `/proc` for RAM/swap | macOS/Windows run fine but **RAM/swap series will be empty** (documented limitation) |
| **~60–120 GB free disk** | model weights (pulled then freed per model) | 95 models, q4 |
| **Time** | CPU inference | hours→days for the full R=5 × 94-model run |
| *(judge only)* a frontier judge | scoring (NOT the system-under-test) | default `copilot` backend = official Copilot CLI (`npm i -g @github/copilot`, authenticated); or `github`/`anthropic`. judge.py is stdlib-only |
| *(energy, optional)* Intel RAPL (preferred) or a metered smart plug | measured energy-per-task | **RAPL** (Intel): on-die joule counters, auto-used if present (root-only → run.py reads via passwordless sudo; tune `RAPL_DOMAIN=psys\|package-0`, disable with `RAPL_DISABLE=1`). **Plug alt:** Home Assistant `HA_URL`/`HA_TOKEN`/`HA_POWER_ENTITY`, **or** IKEA DIRIGERA `DIRIGERA_URL`/`DIRIGERA_TOKEN`/`DIRIGERA_DEVICE_ID`. LAN/SoC operator telemetry (not a model egress); RAPL wins, then HA, then DIRIGERA |
| *(stats only)* `numpy`, `scipy` | CIs, Wilcoxon, κ in the analysis | off the node, optional |

## 0a. Node topology (this homelab's setup)

Two nodes, no laptop in the loop:

| Node | Role | Runs |
|---|---|---|
| **`home-ai`** (the locked i5-8350U / 24 GB) | **experiment node** | `ollama` + `run.py` under the lock (turbo-off, RAPL `package-0`, perf on). All `env.*` / manifest checks target this node. |
| **`homelab`** (always-on server) | **control plane** | the agent/editor, `git`, the **judge** (`judge.py` → frontier API), and orchestration — it SSHes to `home-ai` to launch sweeps and pulls results back. |

A clean reproduction needs only `home-ai` + Ollama; the split just separates the
graded experiment (offline, locked) from the grading rig (online, frontier judge) —
the same offline/online boundary the paper draws. The experiment node is driven
over SSH, so nothing depends on a particular workstation.

## 1. Clone & smoke-test (5 min)

```bash
git clone <repo>  apprenticeops && cd apprenticeops
ollama --version                      # >= 0.30
python3 run.py --help                  # flags present
python3 baselines.py --out /tmp/bl.jsonl   # no model needed; sanity = random~0.26 keyword~0.73
```

## 2. Pilot run — one model, all scenarios (~5 min)

```bash
printf '# bracket: 0-1B\nqwen2.5:0.5b\n' > one.txt
python3 run.py --models one.txt          # pulls, runs 8 scenarios, writes results.jsonl + outputs/
```
You should see per-scenario `det=x/y tok/s wall finish`, and `results.jsonl` with
OTel `gen_ai.*` fields + a RAM/swap `samples` array (Linux) + `progress_trace`.

## 3. Full powered run (hours→days; the paper run)

```bash
# Deterministic point estimate (det checks): temp 0, 1 rep
python3 run.py --models models.txt --temp 0 --repeats 1 --out results.det.jsonl

# Variance pass for CIs: temp 0.7, R=5 fixed seeds
python3 run.py --models models.txt --temp 0.7 --repeats 5 --seed-base 1 --out results.var.jsonl

# Thinking models get their OWN profile (separate, fair):
printf '# bracket: think\ndeepseek-r1:1.5b\ndeepseek-r1:7b\nqwen3:4b\n' > think.txt
python3 run.py --models think.txt --think --temp 0.7 --repeats 5 --out results.think.jsonl

# Non-LLM baselines (no model):
python3 baselines.py --out results.baselines.jsonl
```

## 3a. Lock the node into a reproducible power state (recommended for the systems pass)

The audit (i5-8350U, intel_pstate **active**, governor `powersave`, EPP
`performance`, **no** TLP / power-profiles-daemon / auto-cpufreq, on AC) showed the
only per-run variance is dynamic HWP frequency scaling + turbo. Lock it before the
variance run, then restore afterwards:

```bash
./node-power.sh setup      # governor=performance, turbo OFF, clock pinned to base
                           # (~1.70 GHz, sustainable), EPB perf, ThinkPad fan_control ON
./node-power.sh status     # verify
# ... variance pass with per-model quiesce (below) ...
./node-power.sh teardown   # restore the node to normal
```

**Per-model `quiesce()`** makes every model start from an identical machine state
(all steps env-gated, best-effort, need passwordless sudo):

```bash
QUIESCE=1 FAN_MAX=1 COOL_TEMP_C=55 COOL_MAX_S=180 \  # fan to max, wait until ≤55 °C
DROP_CACHES=1 RESET_SWAP=1 \                          # clear page-cache + swap each model
SAMPLE_INTERVAL=0.5 PERF_MEMBW=1 RAPL_DOMAIN=package-0 \
python3 run.py --models models.txt --shuffle --temp 0.7 --repeats 5 \
    --seed-base 1 --out results.var.jsonl
```
`--shuffle` randomizes model order (deterministic `--order-seed`) so any residual
carryover is decorrelated from model identity. `FAN_MAX` needs `node-power.sh
setup` first (it enables `fan_control`). The deterministic *quality* pass (§3) is
order-insensitive and does **not** need this; only the systems numbers do.

## 3b. Reproducibility preflight — guarantee every wave matches wave 1

`run.py` now **refuses to start** unless the node matches the frozen environment
lock in [`data/wave1-manifest.json`](data/wave1-manifest.json). This exists because
the original **wave 1** (`results.var`, Turbo **off**, RAPL `package-0`) and **wave 2**
(`results.wave2`, Turbo **on**, RAPL `psys`/`package-0` mixed) silently diverged: wave 2
was launched without `node-power.sh setup`, so the prior run's teardown trap had
restored Turbo, and `RAPL_DOMAIN` was left unpinned. None of this was recorded in the
data, so the drift stayed invisible until a post-hoc CPU-clock analysis. The guard makes
that **impossible to repeat**:

```bash
# After node-power.sh setup, verify the node is identical to wave 1 (no run yet):
RAPL_DOMAIN=package-0 PERF_MEMBW=1 PERF_CORE=1 python3 run.py --preflight-only
#   -> "PREFLIGHT: OK — node matches data/wave1-manifest.json"  (exit 0), or
#   -> "PREFLIGHT: FAIL" + the exact drift (turbo on, wrong RAPL domain, perf blocked,
#      models missing) and exit 3.
```

The preflight checks: Turbo (`intel_pstate/no_turbo=1`), governor (`performance`),
`min/max_perf_pct=100` (pinned to base), the freq ceiling (≤1750 MHz), `RAPL_DOMAIN`
(`package-0`), `perf_event_paranoid≤2` (so `membw`/`perf.core` counters are readable —
wave 2 lost them on ~14 % of runs), `num_ctx`, and — with `--no-pull` — that every model
is already present (no mid-run `pull_failed`). Any real wave run now **enforces** this
automatically (default `--manifest data/wave1-manifest.json`); a drifted node aborts with
exit 3. Use `--allow-unlocked` only for local/Mac dev runs (downgrades to a warning).

**Self-describing data:** every result row now carries an `env.*` fingerprint
(`env.cpu_no_turbo`, `env.rapl_domain`, `env.ollama_version`, `env.harness_git`,
`env.perf_event_paranoid`, …) so a wave's power/energy regime is permanently auditable —
you can always tell, from the data alone, whether Turbo was on. The volatile fields are
**re-read before every model** (not just at startup), so a multi-day sweep **aborts**
(exit 4) if the node drifts mid-run instead of silently mislabelling rows. `node-power.sh
setup` now also sets `perf_event_paranoid=1` (restored on teardown). To pin the Ollama
version, fill `expected.ollama_version` in the manifest from a known-good
`env.ollama_version`.

**Stop-and-audit (run a couple models, verify, then commit to the full sweep):**

```bash
# 1) lock + run just the first 2 models
./scripts/node-power.sh setup
RAPL_DOMAIN=package-0 PERF_MEMBW=1 PERF_CORE=1 python3 run.py --models data/models.wave3.txt \
    --temp 0.7 --repeats 5 --seed-base 1 --shuffle --order-seed 1 --limit 2 \
    --out results.wave3.jsonl
# 2) audit those rows: one regime? matches wave1? no RAPL mix / pull_failed / missing perf?
python3 scripts/audit-wave.py results.wave3.jsonl       # must print "AUDIT: PASS"
# 3) only if PASS, launch the full sweep (drop --limit; dedup handles the 2 repeats)
nohup ./scripts/run-wave3.sh >wave3.driver.out 2>&1 &
```

`--limit N` runs the first N models then stops; `audit-wave.py` exits non-zero if the
partial data shows any drift or wave2-class defect, so you spend the multi-day budget only
on a node you've **verified** matches wave 1.

## 3c. Run it from `homelab` (control) against `home-ai` (experiment)

The whole sweep is driven from the **homelab** control node — no workstation in the loop.
`homelab` SSHes to `home-ai` (its key/cert is trusted there); the node mirrors the exact
pinned commit and runs the locked roster.

```bash
# on homelab:
LIMIT=2 ./scripts/run-from-homelab.sh        # 1) audit batch: 2 models, locked, collected
python3 scripts/audit-wave.py data/collected/<RUN_ID>/results.<RUN_ID>.jsonl   # must say PASS
./scripts/run-from-homelab.sh                 # 2) full 158-model roster (detached on home-ai)
./scripts/run-from-homelab.sh status          # tail the node-side driver log
./scripts/run-from-homelab.sh collect         # pull results + logs + outputs back to homelab
```

The node-side `run-roster.sh` guarantees per run:
- **Locked + verified:** `node-power.sh setup`, then `run.py --preflight-only` must pass
  (turbo off, governor performance, RAPL `package-0`, perf readable, protocol + scenarios
  hash + models). It refuses to run otherwise.
- **Identical start per model (proven, not assumed):** between models `quiesce()` resets the
  state (fan-max cool to target °C, `drop_caches`, `swapoff/swapon`, compact), and the next
  model stamps **`reset.*`** evidence into its rows — `reset.cpu_no_turbo`, `reset.cpu_freq_mhz`,
  `reset.cpu_temp_c`, `reset.swap_used_mb`, `reset.mem_avail_mb`, `reset.load1`,
  `reset.running_procs`, `reset.top_proc`, `reset.perf_event_paranoid`, plus
  `reset.ok`/`reset.warnings`. A model that starts dirty is flagged, not silently kept.
- **Server logging:** the ollama server log (`journalctl -u ollama`, or `~/.ollama/logs/server.log`)
  is captured for the whole run, plus `ollama list` (digests) and the selected **CPU library**
  (`cpu_avx2`/`avx`/`cpu` — pin with `OLLAMA_LLM_LIBRARY` for determinism).

**Data convention** (collected to `homelab:data/collected/<RUN_ID>/`, `RUN_ID=roster-YYYYMMDD-HHMM`):

```
results.<RUN_ID>.jsonl                    one row per (model,scenario,rep); env.* + reset.* stamped
outputs/<model>__<scenario>__rN.txt       the raw answers
logs/<RUN_ID>/{driver,run,preflight}.log  ollama-server.log  ollama-list.txt
              ollama.meta  ollama-cpu-library.txt  node-power-status.txt  calibration.json
```

**Trust:** set up `homelab -> home-ai` SSH first — homelab's public key (or a CA-signed SSH
certificate `home-ai` trusts) so the orchestrator runs in BatchMode with no prompts. The
experiment node mirrors `origin/main` exactly (tracked files only; gitignored artifacts kept).

## 4. Judge (on the control node `homelab`, off the experiment node; frontier reference + scoring)

```bash
# Default backend = copilot (the official GitHub Copilot CLI). Find the Claude id:
JUDGE_BACKEND=copilot python3 judge.py --list-models      # -> claude-opus-4.8
export JUDGE_BACKEND=copilot JUDGE_MODEL=claude-opus-4.8   # Claude 4.8 Max
python3 judge.py --reference --out reference.jsonl                       # gold ceiling
python3 judge.py --judge --ensemble copilot:gpt-5.5 \
    --results results.det.jsonl --out judged.jsonl        # 2-family ensemble
```
> Backends: `copilot` (default, Copilot CLI — needs `npm i -g @github/copilot`
> once-authenticated; consumes AI Credits), `github` (GitHub Models, OpenAI-compat
> — NO Claude there), `anthropic` (`ANTHROPIC_API_KEY`). The judge/reference is
> **eval scaffolding** — the system-under-test (the small local model) never calls
> it. "Offline" describes the *deployed system*, not the grading rig.

## 5. Report

```bash
cat results.*.jsonl results.baselines.jsonl > all.jsonl
python3 report.py --results all.jsonl --judged judged.jsonl --out-md RESULTS.md --out-csv results.csv
# ML-ready table (one row per task: features + labels) for sklearn/Kaggle modelling:
python3 dataset.py --results all.jsonl --judged judged.jsonl --out dataset.csv
```
`RESULTS.md` includes: the headline table (det + 95% CI, % frontier, tok/s, swap,
DNF), the **per-task-taxonomy matrix** (model × class), the **task-class
difficulty** table, the **paired RAG lift** table (within-pair, the clean
estimate), and a **Statistics** section (bootstrap CIs + Friedman with
numpy/scipy; judge-ensemble Cohen's κ). The bare closed-book/grounded columns are
confounded class means — read the paired table for the retrieval effect.

## 5a. Notebook dependencies + setup (captured for reproducibility)

Notebook dependencies are versioned in:

- `requirements-notebook.txt`

Create a local notebook environment (from repo root):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r scripts/ai-node/small-model-eval/requirements-notebook.txt
python -m ipykernel install --user --name apprenticeops --display-name "ApprenticeOps (.venv)"
```

Open and run:

- `docs/analysis/interim_variance_analysis.ipynb`

The notebook expects interim files under `.tmp/interim/` at repo root
(`analysis_snapshot.json`, `model_summary.csv`, `difficulty_summary.csv`,
`scenario_hardest.csv`, `corr_summary.csv`, `bottleneck_summary.csv`).

## 6. Exact pinning (for byte-reproducibility in the paper)

Record into `ENVIRONMENT.md` at run time:
```bash
{
  echo "## env $(date -u +%FT%TZ)"
  uname -a
  ollama --version
  python3 --version
  echo "### model digests"; ollama list           # the ID column = the digest you pin
  echo "### cpu"; grep -m1 'model name' /proc/cpuinfo; nproc
  echo "### cpu freq policy"; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor; \
    echo "no_turbo=$(cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null)" \
         "perf_pct=$(cat /sys/devices/system/cpu/intel_pstate/min_perf_pct 2>/dev/null)-$(cat /sys/devices/system/cpu/intel_pstate/max_perf_pct 2>/dev/null)"; \
    lscpu | grep -E 'CPU (max|min) MHz'
  echo "### mem"; free -h | awk '/Mem|Swap/'
  echo "### dram speed/channels"; sudo dmidecode -t memory 2>/dev/null | \
    grep -E 'Locator:|Size:|Type:|Configured Memory Speed:' | grep -vE 'No Module|Unknown'
  echo "### disk"; lsblk -d -o NAME,MODEL,SIZE,TRAN | grep -v loop; \
    for d in /sys/class/nvme/nvme*/device; do sudo lspci -vv -s "$(basename "$(readlink -f "$d")")" 2>/dev/null | grep -m1 LnkSta:; done
  echo "### swap"; cat /proc/swaps      # zram (compressed RAM, used first) + disk swapfile (overflow)
  echo "### radios"; for r in /sys/class/rfkill/rfkill*; do echo "$(cat "$r/type")=soft$(cat "$r/soft")"; done 2>/dev/null
} > ENVIRONMENT.md
```
The prompts are **byte-frozen** in `MODEL-PROMPTS.md`; seeds are fixed
(`--seed-base`); temps are explicit. Same model digest + same seed + same prompt =
same input. (CPU-nondeterminism in float reductions may still vary tokens slightly;
that's why we report CIs, not point claims.)

## Reproducibility caveats (state in the paper)

- **Telemetry needs Linux** (`/proc`). On other OSes, quality scores still
  reproduce; the RAM/swap series won't.
- **Energy is optional**: the **preferred** source is Intel RAPL (`psys` =
  on-die SoC energy, excludes display/PSU — clean compute energy, not facility
  power); a smart plug measures wall draw instead. Either way capture the idle
  baseline and report net-over-idle. No RAPL and unset `HA_*`/`DIRIGERA_*` →
  power columns are blank and everything else reproduces. `power.source` in
  results.jsonl records which source was used.
- **CPU nondeterminism**: identical seed can still differ token-for-token across
  CPUs/threads → we publish CIs and bracket-level claims, not exact per-model ranks.
- **Ollama packaging changes**: a re-pushed tag can change weights; **pin the
  digest** from `ollama list`, not the tag.
- **Judge drift**: frontier models update; record `JUDGE_MODEL` + date. Release
  the judge prompts + a human-rated κ subset so others can re-judge.
- **Judge egress / opsec**: the off-node judge (GitHub Models → a cloud frontier
  model) **receives the full scenario text**, which in this study contains real
  cluster detail (namespaces, Azure Key Vault, Cloudflare, `*.hont.ro`,
  restic/NAS). The *system-under-test* stays sovereign, but **grading sends real
  ops data to a third party**. Scrub/anonymize scenarios before public release,
  and disclose this egress in the paper. Self-hosting the judge removes it.

## Extracting the standalone repo (for the paper)

This folder is self-contained and meant to become its own public repo. To lift it:

```
apprenticeops/                     # new public repo (Apache-2.0)
├── README.md                      # <- README.md (this folder)
├── PAPER.md  PLAN.md  MARKET.md   # design + method + adversarial  (docs/)
├── MODELS.md  models.txt          # model manifest  (docs/ and data/)
├── scenarios.json                 # the benchmark (frozen real incidents)  (data/)
├── MODEL-PROMPTS.md               # byte-frozen prompts  (data/)
├── run.py  baselines.py  judge.py  report.py
├── REPRODUCE.md                   # <- this file
├── LICENSE                        # Apache-2.0 (add on extraction)
└── results/                       # released run data + RESULTS.md + ENVIRONMENT.md
```
Nothing in the harness hardwires `home.hont.ro` — the scenarios are **frozen
text** (anyone runs them as-is); `OLLAMA_URL` is the only host knob. The only
homelab-specific content is the *incident text itself*, which is the point (real,
uncontaminated tasks). Add a top-level `LICENSE` and a `results/` snapshot on
extraction and it's a clean clone-and-run artifact.
