"""Retained exploratory A/B analyses on the locked <=5B 152-study roster.

The A/B scripts (a1..a6, b1..b5) were authored against the frozen 94-model
var/wave2 snapshot via ``ceops_data.load_runs`` / ``model_table``. This driver
re-runs the *same computations* against the single controlled-regime 152-model
run (``full_data``) WITHOUT editing or clobbering the 94-model scripts or their
committed outputs. It:

* feeds each script the 152 run-level frame and a ceops-schema-compatible model
  table (``energy_wh_controlled`` <- ``energy_wh`` because the 152 run is one
  controlled regime with comparable energy on 100% of rows;
  ``quality_per_wh_controlled`` <- ``quality_per_wh``;
  ``quality_per_sec`` <- quality/wall_s; ``dnf_rate`` computed from the run frame;
  ``membw_peak_mb_s`` / ``prefill_tps`` are NaN -- the 152 systems capture has no
  membw axis, so those consumers degrade or are routed to a 152-native script);
* isolates every CSV/figure the scripts emit into ``out/full_ab/`` and
  ``figures/full_ab/`` so the 94-model artifacts stay intact;
* runs only retained descriptions, with explicit exclusions for unsupported fits.

Routed to 152-native scripts instead of re-run here:
* a5_judge     -> full_adversarial_review.py  (152 dual-judge agreement: claude-opus-4.6 vs gpt-5.4)
* b4_roofline  -> full_moe_dense.py            (152 roofline residual; 152 has no membw axis)
* b5_regime    -> N/A                           (152 is ONE controlled regime; no var/wave2 split)
* b6_chatok    -> already the 152 chat-template analysis

Standard-library + the existing analysis modules only. Never mutates the run bundle.
"""

from __future__ import annotations

import contextlib
import argparse
import io
import json
import pathlib
import traceback
from unittest.mock import patch

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.figure

import full_data

REPO = full_data.REPO
OUT = REPO / "deep-dive" / "out" / "full_ab"
FIGOUT = REPO / "deep-dive" / "figures" / "full_ab"


def compat_model_table(df: pd.DataFrame) -> pd.DataFrame:
    """full_data model table + the ceops-schema alias columns the A/B scripts read."""
    mt = full_data.model_table_full(df).copy()
    mt["energy_wh_controlled"] = mt["energy_wh"]                 # comparable across all 152 (single regime)
    mt["quality_per_wh_controlled"] = mt["quality_per_wh"]
    mt["quality_per_sec"] = mt["quality"] / mt["wall_s"]
    dnf = df.groupby("model")["dnf_bool"].mean().rename("dnf_rate").reset_index()
    mt = mt.merge(dnf, on="model", how="left")
    mt["membw_peak_mb_s"] = np.nan                               # not captured on the 152 run
    mt["prefill_tps"] = np.nan
    return mt


# ---- output isolation: redirect CSV / figure writes into the full_ab/ dirs ----
_orig_to_csv = pd.DataFrame.to_csv
_orig_savefig = matplotlib.figure.Figure.savefig


def _to_csv(self, path_or_buf=None, *args, **kwargs):
    if isinstance(path_or_buf, (str, pathlib.Path)):
        path_or_buf = OUT / pathlib.Path(path_or_buf).name
    return _orig_to_csv(self, path_or_buf, *args, **kwargs)


def _savefig(self, fname, *args, **kwargs):
    if isinstance(fname, (str, pathlib.Path)):
        fname = FIGOUT / pathlib.Path(fname).name
    return _orig_savefig(self, fname, *args, **kwargs)


def run_one(name: str, module, model_table_based: bool, feature_override=None, df=None) -> None:
    """Bound loader/output redirection to this call; record failure and re-raise."""
    if df is None:
        df = full_data.load_full()
    buf = io.StringIO()
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(module, "load_runs", lambda: df.copy(), create=True))
            if model_table_based:
                mt = compat_model_table(df)
                stack.enter_context(patch.object(module, "model_table", lambda _df=None: mt.copy()))
            if feature_override is not None:
                stack.enter_context(patch.object(module, "FEATURES", feature_override))
            if hasattr(module, "FIG"):
                stack.enter_context(patch.object(module, "FIG", FIGOUT))
            stack.enter_context(patch.object(pd.DataFrame, "to_csv", _to_csv))
            stack.enter_context(patch.object(matplotlib.figure.Figure, "savefig", _savefig))
            stack.enter_context(contextlib.redirect_stdout(buf))
            stack.enter_context(contextlib.redirect_stderr(buf))
            module.main()
        text = buf.getvalue()
    except Exception:
        (OUT / f"{name}.txt").write_text(buf.getvalue() + "\nFAILED\n" + traceback.format_exc())
        raise
    (OUT / f"{name}.txt").write_text(text)
    print(f"\n{'=' * 72}\n# {name}: {df.model.nunique()} deployments, {len(df)} rows\n{'=' * 72}")
    print(text)


def main() -> None:
    global OUT, FIGOUT
    parser = argparse.ArgumentParser(description="Retained exploratory A/B, primary <=5B locked roster only")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    from phase4_repairs import verify_inputs, sha256
    source_hashes = verify_inputs()
    OUT = args.out
    FIGOUT = OUT / "figures"
    OUT.mkdir(parents=True, exist_ok=False)
    FIGOUT.mkdir()
    import a1_ranking, a2_efficiency, a4_capability, a6_variance
    import b2_clustering, b3_mixedeffects
    full = full_data.load_full()
    df = full_data.primary_frame(full)
    full_data.eligibility_table(full).to_csv(OUT / "eligibility.csv", index=False)

    # b2 feature space minus the axes the 152 run does not capture (membw)
    b2_features = ["quality", "safety", "det_score", "decode_tps", "wall_s",
                   "quality_sd", "trunc_rate", "dnf_rate", "size_gb", "params_b"]

    modules = [(a1_ranking, False), (a2_efficiency, True), (a4_capability, False),
               (a6_variance, False), (b2_clustering, True), (b3_mixedeffects, False)]
    for module, based in modules:
        run_one(module.__name__, module, based,
                feature_override=b2_features if module is b2_clustering else None, df=df)
    exclusions = {
        "a3_scaling_arch": "NOT IDENTIFIABLE: heuristic lineage and independent-tag resampling cannot support quantization/training inference.",
        "b1_irt": "EXCLUDED: unvalidated det>=0.5 construct; no convergence/identifiability gate for joint 2PL fit. No task-pruning claim retained.",
        "b3_mixedeffects": "Population audit only; old coefficient/CIs and nested-as-crossed cross-check withdrawn.",
        "b4_roofline": "EXCLUDED: no measured memory-bandwidth axis; no new hardware evidence.",
        "b5_regime": "NOT IDENTIFIABLE: single regime.",
        "b6_chatok": "Candidate screen is a separate selection process, not random sampling of models."}
    (OUT / "disposition.json").write_text(json.dumps(exclusions, indent=2)+"\n")
    for module, _ in modules:
        p = pathlib.Path(module.__file__)
        source_hashes[str(p.relative_to(REPO))] = sha256(p)
    for name in ["full_ab.py", "full_data.py", "phase4_repairs.py"]:
        source_hashes["deep-dive/"+name] = sha256(REPO/"deep-dive"/name)
    (OUT / "receipt.json").write_text(json.dumps({
        "status": "completed", "claim_status": "provisional", "study": full_data.RUN_ID,
        "models": int(df.model.nunique()), "rows": len(df),
        "scripts": [m.__name__ for m, _ in modules], "source_sha256": source_hashes,
        "output_sha256": {str(p.relative_to(OUT)): sha256(p) for p in sorted(OUT.rglob("*")) if p.is_file()},
        "interpretation": "Exploratory fixed-corpus descriptions, not paper claim approval; see disposition.json"
    }, indent=2)+"\n")

    print(f"\n{'=' * 72}\nRetained A/B primary-roster computation complete.")
    print(f"per-script stdout captured under {OUT}")
    print("Excluded or audit-only analyses: disposition.json. No scientific validation implied.")


if __name__ == "__main__":
    main()
