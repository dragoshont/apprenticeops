"""B5 — Batch/regime confound structure (data integrity).

Finding: the two collection batches are DISJOINT model sets on different CPU
regimes (var/base-clock: 25 models with controlled energy; wave2/turbo: 70).
There is no model in both, so a paired regime study is impossible with this data.
Consequences:
* quality/det are regime-invariant by construction (CPU clock does not change the
  emitted tokens at fixed temperature/seed) -> the cross-batch *quality* ranking
  is valid even though energy is confined to the 25-model var set;
* the one thing regime CAN change is timeout/DNF (a slower regime times out more).
"""

from __future__ import annotations

from ceops_data import load_runs


def main() -> None:
    df = load_runs()
    var_models = set(df[df.collection_batch == "var"]["model"])
    w2_models = set(df[df.collection_batch == "wave2"]["model"])
    print("=== batch / regime structure ===")
    print(f"var  (base_clock 1.7GHz, turbo-off, energy-controlled): {len(var_models)} models")
    print(f"wave2(dynamic turbo-on, energy descriptive-only):       {len(w2_models)} models")
    print(f"overlap: {len(var_models & w2_models)} models  ->  DISJOINT")
    print("consequence: no paired regime study is possible; energy comparisons are confined")
    print("to the 25-model var set; quality/det are regime-invariant so the full-95 quality")
    print("ranking remains valid.\n")

    dnf = df.groupby("collection_batch")["dnf_bool"].mean()
    to = df[df.finish_reason.astype(str).str.contains("timeout")].groupby("collection_batch").size()
    trunc = df.groupby("collection_batch")["truncated"].mean()
    print("=== DNF / timeout by regime (the one regime-sensitive outcome) ===")
    print(f"DNF rate:       var(base)={dnf.get('var',float('nan')):.1%}  wave2(turbo)={dnf.get('wave2',float('nan')):.1%}")
    print(f"timeout events: var={int(to.get('var',0))}  wave2={int(to.get('wave2',0))}")
    print(f"truncation:     var={trunc.get('var',float('nan')):.1%}  wave2={trunc.get('wave2',float('nan')):.1%}")

    print("\n=== the 25 energy-controlled (var) models — the only ones with a comparable energy axis ===")
    print(", ".join(sorted(var_models)))

    print("\nRECOMMENDATION: run a bridge subset (~10 models) under BOTH regimes to measure the")
    print("CPU power-policy effect on energy/latency and to license cross-batch energy comparison.")


if __name__ == "__main__":
    main()
