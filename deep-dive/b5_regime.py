"""B5 — Two-batch role structure (controlled vs breadth), not a confound.

The var/wave2 split is by design (PAPER.md §7). The frozen v1 snapshot holds two
batches with different ROLES — not a botched re-run:
* var   = the pre-registered CONTROLLED first batch: 25 tags / 24 functional; base
          clock 1700, turbo OFF, RAPL package-0 -- the ONLY energy-comparable scope;
* wave2 = a BREADTH-extension second batch: 70 tags, dynamic turbo-on -- grows
          quality/safety coverage to 94 functional but is EXCLUDED from energy/
          systems ranking by design (schema v1 records batch/regime/source and
          forbids the pooled energy front).
The two batches are disjoint model sets.
Consequences:
* quality/det are regime-invariant by construction (CPU clock does not change the
  emitted tokens at fixed temperature/seed) -> the full 94-functional *quality*
  ranking is valid; energy is confined to the 24 controlled models BY DESIGN, not
  as a limitation;
* the one thing regime CAN change is timeout/DNF (a slower regime times out more);
* an optional bridge subset (same models under both regimes) would additionally
  PRICE the power policy -- an enhancement, not a correction.

Separate cohorts, OUTSIDE this snapshot: the 152-model `full-chatok-core20-r5`
doctoral run (provisional; analysed in b6) and the ongoing 21-model timeout-
sensitivity follow-up (DNF-selected; 21x20x5 = 2100 rows).
"""

from __future__ import annotations

from ceops_data import load_runs


def main() -> None:
    df = load_runs()
    var_models = set(df[df.collection_batch == "var"]["model"])
    w2_models = set(df[df.collection_batch == "wave2"]["model"])
    print("=== two-batch role structure (controlled vs breadth), not a confound ===")
    print(f"var   = pre-registered CONTROLLED first batch (base_clock 1.7GHz, turbo-off, energy-comparable): {len(var_models)} tags")
    print(f"wave2 = BREADTH-extension second batch (dynamic turbo-on, energy descriptive-only): {len(w2_models)} tags")
    print(f"overlap: {len(var_models & w2_models)} models  ->  disjoint batches by design")
    print("energy is confined to the controlled var batch BY DESIGN; quality/det are")
    print("regime-invariant so the full 94-functional quality ranking is valid.\n")

    dnf = df.groupby("collection_batch")["dnf_bool"].mean()
    to = df[df.finish_reason.astype(str).str.contains("timeout")].groupby("collection_batch").size()
    trunc = df.groupby("collection_batch")["truncated"].mean()
    print("=== DNF / timeout by regime (the one regime-sensitive outcome) ===")
    print(f"DNF rate:       var(base)={dnf.get('var',float('nan')):.1%}  wave2(turbo)={dnf.get('wave2',float('nan')):.1%}")
    print(f"timeout events: var={int(to.get('var',0))}  wave2={int(to.get('wave2',0))}")
    print(f"truncation:     var={trunc.get('var',float('nan')):.1%}  wave2={trunc.get('wave2',float('nan')):.1%}")

    print("\n=== the 25 energy-controlled (var) models — the only ones with a comparable energy axis ===")
    print(", ".join(sorted(var_models)))

    print("\nOPTIONAL ENHANCEMENT (not a fix): run a bridge subset (~10 models) under BOTH regimes")
    print("to PRICE the CPU power-policy effect on energy/latency (ties to the homelab EPP finding).")


if __name__ == "__main__":
    main()
