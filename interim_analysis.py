import csv, json, math, statistics
from collections import defaultdict, Counter
from pathlib import Path

SRC = Path("results.var.jsonl")
OUT_JSON = Path("analysis_snapshot.json")

rows = []
with SRC.open() as f:
    for ln in f:
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            pass


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return (sum(xs) / len(xs)) if xs else None

def median(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return statistics.median(xs) if xs else None

def p90(xs):
    xs = sorted([x for x in xs if isinstance(x, (int, float))])
    if not xs:
        return None
    i = int(0.9 * (len(xs)-1))
    return xs[i]

def pearson(pairs):
    pairs = [(a,b) for (a,b) in pairs if isinstance(a,(int,float)) and isinstance(b,(int,float))]
    n = len(pairs)
    if n < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = sum(xs)/n
    my = sum(ys)/n
    vx = sum((x-mx)**2 for x in xs)
    vy = sum((y-my)**2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    cov = sum((x-mx)*(y-my) for x,y in pairs)
    return cov / math.sqrt(vx * vy)

models = sorted({r.get("model") for r in rows if r.get("model")})
scenarios = sorted({r.get("scenario") for r in rows if r.get("scenario")})

model_groups = defaultdict(list)
for r in rows:
    m = r.get("model")
    if m:
        model_groups[m].append(r)

model_summary = []
for m, rs in sorted(model_groups.items(), key=lambda kv: len(kv[1]), reverse=True):
    d = [r.get("det_score") for r in rs]
    tok = [r.get("decode_tok_s") for r in rs]
    wh = [r.get("wh_per_correct") for r in rs]
    ipc = [r.get("ipc") for r in rs]
    swap = [r.get("peak_swap_mb") for r in rs]
    moe_hits = sum(1 for r in rs if (r.get("ollama.expert_count") or 0) > 0)
    model_summary.append({
        "model": m,
        "rows": len(rs),
        "det_mean": mean(d),
        "det_p90": p90(d),
        "tok_s_median": median(tok),
        "tok_s_mean": mean(tok),
        "wh_per_correct_mean": mean(wh),
        "ipc_mean": mean(ipc),
        "peak_swap_mb_max": max([x for x in swap if isinstance(x,(int,float))], default=0),
        "moe_rows": moe_hits,
    })

difficulty_groups = defaultdict(list)
for r in rows:
    d = r.get("difficulty")
    if d:
        difficulty_groups[d].append(r)

difficulty_summary = []
for d in ("easy", "medium", "hard"):
    rs = difficulty_groups.get(d, [])
    difficulty_summary.append({
        "difficulty": d,
        "rows": len(rs),
        "det_mean": mean([r.get("det_score") for r in rs]),
        "tok_s_mean": mean([r.get("decode_tok_s") for r in rs]),
        "temp_mean": mean([r.get("thermal.peak_c") for r in rs]),
    })

scenario_groups = defaultdict(list)
for r in rows:
    s = r.get("scenario")
    if s:
        scenario_groups[s].append(r)

scenario_hardest = []
for s, rs in scenario_groups.items():
    scenario_hardest.append({
        "scenario": s,
        "rows": len(rs),
        "difficulty": rs[0].get("difficulty"),
        "det_mean": mean([r.get("det_score") for r in rs]),
        "tok_s_mean": mean([r.get("decode_tok_s") for r in rs]),
        "peak_swap_mb_max": max([r.get("peak_swap_mb") for r in rs if isinstance(r.get("peak_swap_mb"),(int,float))], default=0),
    })
scenario_hardest.sort(key=lambda x: (x["det_mean"] if x["det_mean"] is not None else 1e9))

corr_summary = [
    {
        "metric_x": "decode_tok_s",
        "metric_y": "ipc",
        "pearson_r": pearson([(r.get("decode_tok_s"), r.get("ipc")) for r in rows]),
    },
    {
        "metric_x": "decode_tok_s",
        "metric_y": "thermal.peak_c",
        "pearson_r": pearson([(r.get("decode_tok_s"), r.get("thermal.peak_c")) for r in rows]),
    },
    {
        "metric_x": "det_score",
        "metric_y": "decode_tok_s",
        "pearson_r": pearson([(r.get("det_score"), r.get("decode_tok_s")) for r in rows]),
    },
    {
        "metric_x": "llc_miss_rate",
        "metric_y": "decode_tok_s",
        "pearson_r": pearson([(r.get("llc_miss_rate"), r.get("decode_tok_s")) for r in rows]),
    },
]

bottle = Counter()
for r in rows:
    b = r.get("bottleneck")
    if b:
        bottle[b] += 1
bottleneck_summary = [{"bottleneck": k, "rows": v} for k, v in bottle.most_common()]

snapshot = {
    "rows": len(rows),
    "models_seen": len(models),
    "scenarios_seen": len(scenarios),
    "model_summary": model_summary,
    "difficulty_summary": difficulty_summary,
    "scenario_hardest_top10": scenario_hardest[:10],
    "corr_summary": corr_summary,
    "bottleneck_summary": bottleneck_summary,
}

OUT_JSON.write_text(json.dumps(snapshot, indent=2))


def write_csv(path, records):
    if not records:
        path.write_text("")
        return
    keys = list(records[0].keys())
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in records:
            w.writerow(r)

write_csv(Path("model_summary.csv"), model_summary)
write_csv(Path("difficulty_summary.csv"), difficulty_summary)
write_csv(Path("scenario_hardest.csv"), scenario_hardest)
write_csv(Path("corr_summary.csv"), corr_summary)
write_csv(Path("bottleneck_summary.csv"), bottleneck_summary)

print("rows", len(rows))
print("models_seen", len(models), "scenarios_seen", len(scenarios))
print("wrote", "analysis_snapshot.json model_summary.csv difficulty_summary.csv scenario_hardest.csv corr_summary.csv bottleneck_summary.csv")
