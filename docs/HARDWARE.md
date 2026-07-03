# Hardware Profile

Status: active hardware note, created 2026-07-03.

## Target Class Versus Measured Node

The doctoral target is **commodity CPU-only laptop hardware**, roughly a
T14s/T480s-class older laptop with about 24 GiB RAM and no dedicated GPU. The
current measured node is narrower:

| Role | Current value |
|---|---|
| Measured node | ThinkPad T480s / `home-ai`, hostname `ai` |
| CPU class | Intel i5-8350U class, 4C/8T, 15 W mobile CPU |
| RAM | about 24 GiB |
| Inference runtime | Ollama 0.30.8 |
| GPU use | none for graded inference |
| OS | Linux, observed kernel `7.0.0-22-generic` in committed v1 run rows |

Machine-readable profile: `data/hardware-profile.home-ai.json`.

## Locked Systems Settings

The reproducible systems pass expects:

- governor `performance`;
- turbo disabled (`cpu_no_turbo=1`);
- `min_perf_pct=max_perf_pct=100`;
- RAPL domain `package-0`;
- perf counters available (`perf_event_paranoid <= 2`);
- memory-bandwidth and core perf sampling enabled;
- sample interval 0.5 s;
- Ollama 0.30.8;
- context length 8192.

These settings are checked by `run.py --preflight-only` against
`data/run-manifest.json` for locked Linux runs.

## What Is Node-Bound

Quality and safety scores can be recomputed from committed rows on any machine.
Systems metrics are node-bound:

- RAPL energy;
- CPU frequency and thermal behavior;
- memory bandwidth and perf counters;
- RSS/swap/page-fault behavior;
- wall-time and throughput under the locked CPU state.

The paper should not generalize these systems numbers to all laptops. It should
state: single-node measurement, released harness, invite reruns.

## Known Hardware/Profile Caveat

The committed v1 dev run rows stamp `env.harness_dirty=true` even though the run
was launched from an origin-synced source checkout. This appears to reflect
generated run artifacts appearing in the worktree by row-stamp time. Treat it as
a follow-up instrumentation issue: split `source_dirty` from `artifact_dirty` in
future rows. Do not use the dirty flag alone to reject a run whose `run.meta`,
scenario hashes, model set, and strict report are otherwise clean.