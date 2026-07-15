"""Re-run of the A/B analysis series on the 152-model full run (findings 1-14).

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
* runs ONLY the scripts that are well-defined on a single-regime run.

Routed to 152-native scripts instead of re-run here:
* a5_judge     -> full_adversarial_review.py  (152 dual-judge agreement: claude-opus-4.6 vs gpt-5.4)
* b4_roofline  -> full_moe_dense.py            (152 roofline residual; 152 has no membw axis)
* b5_regime    -> N/A                           (152 is ONE controlled regime; no var/wave2 split)
* b6_chatok    -> already the 152 chat-template analysis

Standard-library + the existing analysis modules only. Never mutates the run bundle.
"""

from __future__ import annotations

import contextlib
import io
import pathlib

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.figure

import full_data

REPO = full_data.REPO
OUT = REPO / "deep-dive" / "out" / "full_ab"
FIGOUT = REPO / "deep-dive" / "figures" / "full_ab"
OUT.mkdir(parents=True, exist_ok=True)
FIGOUT.mkdir(parents=True, exist_ok=True)


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


pd.DataFrame.to_csv = _to_csv
matplotlib.figure.Figure.savefig = _savefig


def run_one(name: str, module, model_table_based: bool, feature_override=None) -> None:
    """Patch a module's loaders to the 152 data, run its main(), tee stdout to file."""
    df = full_data.load_full()
    module.load_runs = lambda _df=df: _df.copy()
    if model_table_based:
        mt = compat_model_table(df)
        module.model_table = lambda _df=None, _mt=mt: _mt.copy()
    if feature_override is not None:
        module.FEATURES = feature_override

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            module.main()
        text = buf.getvalue()
    except Exception as exc:  # keep the batch going; surface the failure
        text = buf.getvalue() + f"\n[!! {name} raised {type(exc).__name__}: {exc}]\n"
    (OUT / f"{name}.txt").write_text(text)
    print(f"\n{'=' * 72}\n# {name}  (152-model full run)\n{'=' * 72}")
    print(text)


def main() -> None:
    import a1_ranking, a2_efficiency, a3_scaling_arch, a4_capability, a6_variance
    import b1_irt, b2_clustering, b3_mixedeffects

    # b2 feature space minus the axes the 152 run does not capture (membw)
    b2_features = ["quality", "safety", "det_score", "decode_tps", "wall_s",
                   "quality_sd", "trunc_rate", "dnf_rate", "size_gb", "params_b"]

    run_one("a1_ranking", a1_ranking, model_table_based=False)
    run_one("a2_efficiency", a2_efficiency, model_table_based=True)
    run_one("a3_scaling_arch", a3_scaling_arch, model_table_based=True)
    run_one("a4_capability", a4_capability, model_table_based=False)
    run_one("a6_variance", a6_variance, model_table_based=False)
    run_one("b1_irt", b1_irt, model_table_based=False)
    run_one("b2_clustering", b2_clustering, model_table_based=True, feature_override=b2_features)
    run_one("b3_mixedeffects", b3_mixedeffects, model_table_based=False)

    print(f"\n{'=' * 72}\nA/B series re-run on the 152 model full run complete.")
    print(f"per-script stdout captured under {OUT}")
    print("routed to 152-native scripts: a5->full_adversarial_review, b4->full_moe_dense; "
          "b5 N/A (single regime); b6 already 152.")


if __name__ == "__main__":
    main()
