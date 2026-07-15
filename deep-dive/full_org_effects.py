"""Org / maker effects (full run) — which makers build the best small ops models.

Ranks model makers by quality / safety / energy on the ops suite. Adversarial:
an org's mean is CONFOUNDED by the size mix and count of models it contributed, so
the raw ranking is reported alongside a size-controlled view (within the 3-4B band
where several orgs compete) and the per-org n, so single-model orgs are not
over-read.
"""

from __future__ import annotations

import re

import pandas as pd

from full_data import REPO, load_full, model_table_full

# family -> maker (fallback when metadata `org` is missing)
_ORG = [
    (r"qwen|smallthinker", "Alibaba/Qwen"), (r"gemma|codegemma", "Google"),
    (r"phi", "Microsoft"), (r"llama|hermes", "Meta/deriv"), (r"granite", "IBM"),
    (r"falcon", "TII"), (r"exaone", "LG"), (r"command-r|aya", "Cohere"),
    (r"smollm", "HuggingFace"), (r"olmo", "AllenAI"), (r"lfm2", "LiquidAI"),
    (r"internlm", "ShanghaiAILab"), (r"stablelm|stable-code", "StabilityAI"),
    (r"cogito", "DeepCogito"), (r"deepseek", "DeepSeek"), (r"mistral|ministral", "Mistral"),
    (r"nemotron", "NVIDIA"), (r"\byi", "01.AI"), (r"sailor", "SeaAILab"),
    (r"starcoder", "BigCode"), (r"tinyllama", "TinyLlama"), (r"minicpm", "OpenBMB"),
    (r"opencoder", "OpenCoder"),
]


def _org(model: str, meta_org) -> str:
    if isinstance(meta_org, str) and meta_org and meta_org.lower() != "nan":
        return meta_org
    m = str(model).split("/")[-1].lower()
    for pat, org in _ORG:
        if re.search(pat, m):
            return org
    return "other"


def main() -> None:
    mt = model_table_full(load_full())
    mt["maker"] = [_org(m, o) for m, o in zip(mt.model, mt.get("org", pd.Series(index=mt.index)))]

    agg = mt.groupby("maker").agg(
        n=("model", "size"), quality=("quality", "mean"), safety=("safety", "mean"),
        energy=("energy_wh", "mean"), best_q=("quality", "max"),
    ).sort_values("quality", ascending=False)
    agg["best_model"] = [mt[mt.maker == mk].sort_values("quality", ascending=False).iloc[0].model
                         for mk in agg.index]

    print("=== makers ranked by mean quality (>=2 models) ===")
    print(agg[agg.n >= 2][["n", "quality", "safety", "energy", "best_model"]].to_string(
        float_format=lambda x: f"{x:.2f}"))

    print("\n=== ADVERSARIAL: is it just size mix? within the 3-5B band (3<=P<5) ===")
    band = mt[(mt.params_b >= 3) & (mt.params_b < 5)]
    b = band.groupby("maker").agg(n=("model", "size"), quality=("quality", "mean")).sort_values(
        "quality", ascending=False)
    print(b[b.n >= 2].to_string(float_format=lambda x: f"{x:.2f}"))
    print("  (single-model orgs dropped; the 3-5B band is where makers compete head-to-head)")

    # de-dup: quant/format variants of one base inflate n -> collapse to distinct bases
    def _basekey(m):
        m = str(m).split("/")[-1]
        return re.sub(r"[-:@]?(q\d_?[a-z0-9]*|iq\d.*|fp16|bf16|gguf|instruct|2507|thinking|it|chat).*$",
                      "", m, flags=re.I)
    band = band.assign(base=band.model.map(_basekey))
    dedup = band.groupby(["maker", "base"]).quality.mean().reset_index()
    d = dedup.groupby("maker").agg(n_bases=("base", "size"), quality=("quality", "mean")).sort_values(
        "quality", ascending=False)
    print("\n=== ADVERSARIAL 2: de-duplicated to distinct BASE models (kills quant-variant inflation) ===")
    print(d[d.n_bases >= 2].to_string(float_format=lambda x: f"{x:.2f}"))
    print("  (Qwen's raw 3-5B n was inflated by qwen3:4b quant variants; the lead survives de-dup but shrinks)")

    agg.to_csv(REPO / "deep-dive" / "out" / "org_effects.csv")
    print(f"\nsaved {REPO/'deep-dive'/'out'/'org_effects.csv'}")


if __name__ == "__main__":
    main()
