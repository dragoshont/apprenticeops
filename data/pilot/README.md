# Pilot data (Pass-1)

Raw rows from the **Pass-1 pilot** so the harness output is inspectable from the
repo (the "release the raw data" reproducibility requirement).

- `results.pilot.jsonl` — 200 rows = **25 models × 8 scenarios**, R=1, temp=0.
  Each row is OTel-`gen_ai.*`-aligned: TTFT, prefill/decode tok/s, wall, in/out
  tokens, the 1 Hz RAM/swap `samples` series, the per-token `progress_trace`,
  deterministic-check detail, and DNF reason.
- `RESULTS.pilot.md` / `results.pilot.csv` — `report.py` rollup of the above.

## Honest caveats (read before citing)

- **Det-only.** The judge had not run when this was captured, so `judge/5`,
  `% frontier`, and judge-based verdicts are empty. Pilot conclusions are
  **deterministic-check only**.
- **8-scenario pilot, superseded.** This predates the expanded benchmark (now 19
  scenarios incl. secure/capacity/paired) and the **sound safety gate**
  (`must_not_endorse` + judge-primary majority). So the headline *safety
  non-monotonicity* finding (e.g. `qwen2.5:0.5b` endorsing `kubectl delete
  namespace kube-system`) is **not** reproducible from this file alone — it needs
  the powered re-run with the new guard checks + the Claude 4.8 judge. This pilot
  exists to de-risk the harness and provide the speed/RAM/DNF profile.
- **Scrub before public release.** Model answers/telemetry reference this
  cluster's (mostly synthetic) scenario detail; anonymize for the standalone repo.

Regenerate the powered dataset per [`../REPRODUCE.md`](../REPRODUCE.md).
