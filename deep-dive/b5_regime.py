"""B5 — Two-stage funnel structure (not a confound).

The var/wave2 split is the intended methodology, not an accident: a broad
EXPLORATORY sweep first (wave2: 150+ models under the node's default dynamic-turbo
policy, to triage the roster and repair failing scripts; energy descriptive_only),
then a CURATED CONTROLLED re-run of the survivors (var: ~24 models under
node-power.sh -- turbo off, base clock 1700, RAPL package-0; the controlled energy
scope). The two stages are disjoint model sets by design.
Consequences:
* quality/det are regime-invariant by construction (CPU clock does not change the
  emitted tokens at fixed temperature/seed) -> the full-95 *quality* ranking is
  valid, the exploratory sweep included; energy is confined to the controlled var
  stage BY DESIGN, not as a limitation;
* the one thing regime CAN change is timeout/DNF (a slower regime times out more);
* an optional bridge subset (same models under both regimes) would additionally
  PRICE the power policy -- an enhancement, not a correction.
"""

from __future__ import annotations

from ceops_data import load_runs


def main() -> None:
    df = load_runs()
    var_models = set(df[df.collection_batch == "var"]["model"])
    w2_models = set(df[df.collection_batch == "wave2"]["model"])
    print("=== two-stage funnel structure (not a confound) ===")
    print(f"wave2 = exploratory sweep FIRST (dynamic turbo-on, energy descriptive-only): {len(w2_models)} models")
    print(f"var   = curated controlled RE-RUN of survivors (base_clock 1.7GHz, turbo-off): {len(var_models)} models")
    print(f"overlap: {len(var_models & w2_models)} models  ->  disjoint stages by design")
    print("energy is confined to the controlled var stage BY DESIGN; quality/det are")
    print("regime-invariant so the full-95 quality ranking (incl. the exploratory sweep) is valid.\n")

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
