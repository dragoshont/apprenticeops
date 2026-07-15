"""Task-class difficulty & discrimination (full run).

Which ops tasks are hardest (low mean quality) and which best SEPARATE models
(high between-model SD)? Psychometric view: a discriminating item has spread; a
floor item (everyone fails) or ceiling item (everyone passes) carries little
information regardless of difficulty.

Adversarial: report scenarios-per-class so single-scenario classes are not
over-read, and check whether "hard" == "discriminative" or just a floor.
"""

from __future__ import annotations

import pandas as pd
from scipy import stats

from full_data import REPO, load_full


def main() -> None:
    df = load_full()
    sm = df.groupby(["scenario", "scenario_class", "model"])["judge_score"].mean().reset_index()
    per_scen = sm.groupby(["scenario", "scenario_class"])["judge_score"].agg(["mean", "std"]).reset_index()
    per_scen.columns = ["scenario", "cls", "difficulty", "discrim"]

    per_cls = per_scen.groupby("cls").agg(
        n_scen=("scenario", "size"), difficulty=("difficulty", "mean"), discrim=("discrim", "mean"),
    ).sort_values("difficulty")

    print("=== task classes: hardest (low mean quality) first ===")
    print(per_cls.to_string(float_format=lambda x: f"{x:.2f}"))

    print("\n=== most discriminative classes (high between-model SD) ===")
    print(per_cls.sort_values("discrim", ascending=False).head(6)[["n_scen", "difficulty", "discrim"]]
          .to_string(float_format=lambda x: f"{x:.2f}"))

    r = stats.spearmanr(per_cls.difficulty, per_cls.discrim).correlation
    print(f"\n=== ADVERSARIAL: is 'hard' the same as 'discriminative'? ===")
    print(f"  Spearman(difficulty, discrimination) over classes = {r:+.2f}")
    print("  (>0 => easier tasks separate models more; hard tasks tend to floor everyone)")
    floor = per_scen[(per_scen.difficulty <= 1.5) & (per_scen.discrim <= 0.6)]
    print(f"  floor scenarios (hard + low spread = low information): {len(floor)} -> {list(floor.scenario)[:5]}")

    print("\nmost discriminative scenarios (keep):")
    print(per_scen.sort_values("discrim", ascending=False).head(5)[["scenario", "difficulty", "discrim"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nleast discriminative scenarios (near-redundant / floor):")
    print(per_scen.sort_values("discrim").head(5)[["scenario", "difficulty", "discrim"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))

    per_cls.to_csv(REPO / "deep-dive" / "out" / "task_difficulty.csv")
    print(f"\nsaved {REPO/'deep-dive'/'out'/'task_difficulty.csv'}")


if __name__ == "__main__":
    main()
