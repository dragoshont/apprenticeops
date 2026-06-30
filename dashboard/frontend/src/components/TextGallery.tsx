import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Check, MessageSquareText, Quote, ShieldCheck, X } from "lucide-react";
import { judgeBadge, tileRing, type DoodleReview } from "./DoodleGallery";

export type TextOutput = {
  scenario: string;
  model: string;
  rep: number;
  detScore: number;
  /** Mean LLM-judge quality on the judge's 1–5 scale (optional until judged). */
  judgeScore?: number;
  /** Per-judge written verdicts (optional until judged). */
  reviews?: DoodleReview[];
  /** The model's text completion. */
  text: string;
  /** The journal entry / ask that produced it (optional). */
  prompt?: string;
  /** The gold reference answer (optional). */
  gold?: string;
};

type GroupBy = "scenario" | "model";

export type TextGalleryProps = {
  outputs: TextOutput[];
  runId?: string;
  loading?: boolean;
  defaultGroupBy?: GroupBy;
};

function prettyScenario(id: string): string {
  return id.replace(/^journal-(aletheia-|ro-)?/, "").replace(/-/g, " ");
}

function GroupToggle({ value, onChange }: { value: GroupBy; onChange: (next: GroupBy) => void }) {
  const options: GroupBy[] = ["scenario", "model"];
  return (
    <div role="group" aria-label="Group outputs by" className="inline-flex rounded-lg border border-line bg-panel2/50 p-0.5">
      {options.map((option) => {
        const active = value === option;
        return (
          <label
            key={option}
            className={`cursor-pointer rounded-md px-2.5 py-1 text-[11px] font-medium transition focus-within:ring-2 focus-within:ring-accent ${active ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
          >
            <input type="radio" name="text-group-by" value={option} checked={active} onChange={() => onChange(option)} className="sr-only" />
            By {option}
          </label>
        );
      })}
    </div>
  );
}

function JudgeChip({ score }: { score?: number }) {
  if (score == null) {
    return (
      <span className="inline-flex h-[18px] min-w-[20px] items-center justify-center rounded-md bg-faint/30 px-1 text-[10px] font-bold text-faint" title="not yet judged">
        –
      </span>
    );
  }
  return (
    <span
      className={`inline-flex h-[18px] min-w-[20px] items-center justify-center rounded-md px-1 text-[10px] font-bold tabular-nums ring-1 ring-bg/40 ${judgeBadge(score)}`}
      title={`LLM-judge mean quality ${score.toFixed(1)} of 5`}
    >
      {score.toFixed(1)}
    </span>
  );
}

function TextCard({ output, crossLabel, onOpen }: { output: TextOutput; crossLabel: string; onOpen: () => void }) {
  const label = `${prettyScenario(output.scenario)} by ${output.model}, rep ${output.rep}`;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${label} — open judge reviews`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      className={`group relative flex cursor-pointer flex-col gap-2 rounded-lg border bg-panel2/40 p-3 outline-none transition hover:bg-panel2/70 focus-visible:ring-2 focus-visible:ring-accent ${tileRing(output.judgeScore)}`}
    >
      <div className="flex items-start justify-between gap-2">
        <Quote className="h-3.5 w-3.5 shrink-0 text-faint" />
        <JudgeChip score={output.judgeScore} />
      </div>
      <p className="line-clamp-5 text-[12px] leading-snug text-fg">{output.text || "(empty)"}</p>
      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
        <span className="truncate font-mono text-[10px] text-faint" title={crossLabel}>{crossLabel}</span>
        <span className="shrink-0 text-[10px] text-faint">rep {output.rep}</span>
      </div>
    </div>
  );
}

function TextModal({ output, onClose }: { output: TextOutput; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const reviews = output.reviews ?? [];
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Judge reviews for ${prettyScenario(output.scenario)} by ${output.model}`}
      onClick={onClose}
    >
      <div className="max-h-[88vh] w-full max-w-2xl overflow-auto rounded-2xl border border-line bg-panel shadow-glow" onClick={(e) => e.stopPropagation()}>
        <header className="flex items-start justify-between gap-3 border-b border-line p-4">
          <div className="min-w-0">
            <div className="text-sm font-semibold capitalize text-fg">{prettyScenario(output.scenario)}</div>
            <div className="mt-0.5 font-mono text-[11px] text-faint">{output.model} · rep {output.rep} · {output.scenario}</div>
          </div>
          <button onClick={onClose} aria-label="Close" className="rounded-md p-1 text-muted outline-none transition hover:bg-panel2 hover:text-fg focus-visible:ring-2 focus-visible:ring-accent">
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="space-y-3 p-4">
          {output.prompt && (
            <div className="rounded-xl border border-line bg-panel2/20 p-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-faint">Prompt</div>
              <p className="whitespace-pre-wrap text-[12px] leading-snug text-muted">{output.prompt}</p>
            </div>
          )}

          <div className="rounded-xl border border-accent/30 bg-accent/5 p-3">
            <div className="mb-1 flex items-center justify-between gap-2">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-accent">Model output</div>
              <JudgeChip score={output.judgeScore} />
            </div>
            <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-fg">{output.text || "(empty)"}</p>
          </div>

          {output.gold && (
            <div className="rounded-xl border border-line bg-panel2/20 p-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-faint">Reference (gold)</div>
              <p className="text-[12px] italic leading-snug text-muted">{output.gold}</p>
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <span
              className={`pill px-1.5 py-0 text-[10px] ${output.detScore >= 1 ? "bg-good/15 text-good" : output.detScore > 0 ? "bg-info/15 text-info" : "bg-line/50 text-faint"}`}
              title="deterministic check (0–1)"
            >
              <ShieldCheck className="h-2.5 w-2.5" />
              det {output.detScore.toFixed(1)}
            </span>
            <span className="text-[10px] text-faint">{reviews.length} judge review{reviews.length === 1 ? "" : "s"}</span>
          </div>

          {reviews.map((rv, i) => (
            <div key={i} className="rounded-xl border border-line bg-panel2/30 p-3">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-muted">{rv.judge}</span>
                {rv.score != null && (
                  <span className={`inline-flex h-5 min-w-[22px] items-center justify-center rounded-md px-1 text-[11px] font-bold tabular-nums ${judgeBadge(rv.score)}`}>
                    {rv.score.toFixed(1)}
                  </span>
                )}
              </div>
              {rv.verdict && <p className="text-[12px] leading-snug text-fg">{rv.verdict}</p>}
              {(rv.met?.length || rv.missed?.length) ? (
                <div className="mt-2 space-y-1">
                  {rv.met?.map((m, j) => (
                    <div key={`m${j}`} className="flex items-start gap-1.5 text-[11px]">
                      <Check className="mt-0.5 h-3 w-3 shrink-0 text-good" />
                      <span className="text-muted">{m}</span>
                    </div>
                  ))}
                  {rv.missed?.map((m, j) => (
                    <div key={`x${j}`} className="flex items-start gap-1.5 text-[11px]">
                      <X className="mt-0.5 h-3 w-3 shrink-0 text-bad" />
                      <span className="text-muted">{m}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function TextGallery({ outputs, runId, loading, defaultGroupBy = "scenario" }: TextGalleryProps) {
  const [groupBy, setGroupBy] = useState<GroupBy>(defaultGroupBy);
  const [selected, setSelected] = useState<TextOutput | null>(null);

  const { groups, scenarioCount, modelCount } = useMemo(() => {
    const scenarios = new Set<string>();
    const models = new Set<string>();
    const map = new Map<string, TextOutput[]>();
    for (const output of outputs) {
      scenarios.add(output.scenario);
      models.add(output.model);
      const key = groupBy === "scenario" ? output.scenario : output.model;
      const arr = map.get(key) ?? [];
      arr.push(output);
      map.set(key, arr);
    }
    for (const arr of map.values()) {
      arr.sort((a, b) => {
        const ax = groupBy === "scenario" ? a.model : a.scenario;
        const bx = groupBy === "scenario" ? b.model : b.scenario;
        return ax.localeCompare(bx) || a.rep - b.rep;
      });
    }
    return {
      groups: [...map.entries()].sort((a, b) => a[0].localeCompare(b[0])),
      scenarioCount: scenarios.size,
      modelCount: models.size,
    };
  }, [outputs, groupBy]);

  return (
    <section id="doodles" className="card card-pad scroll-mt-24">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-fg">
          <MessageSquareText className="h-4 w-4 text-muted" />
          Results — Journal Outputs
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          {outputs.length > 0 && <GroupToggle value={groupBy} onChange={setGroupBy} />}
          {outputs.length > 0 && (
            <div className="flex items-center gap-1 text-[10px] text-faint" aria-label="judge score legend" title="LLM-judge mean quality (1–5)">
              <span className="mr-0.5">judge</span>
              <span className="rounded bg-bad/20 px-1 font-semibold text-bad">1</span>
              <span className="rounded bg-warn px-1 font-semibold text-slate-900">2</span>
              <span className="rounded bg-info px-1 font-semibold text-slate-900">3</span>
              <span className="rounded bg-good px-1 font-semibold text-slate-900">4–5</span>
            </div>
          )}
          <span className="text-xs text-faint">
            {runId ? <span className="font-mono">{runId}</span> : "no run selected"}
            {outputs.length > 0 && (
              <>
                {" · "}
                {outputs.length} outputs · {scenarioCount} prompts · {modelCount} models
              </>
            )}
          </span>
        </div>
      </header>

      {loading ? (
        <div className="grid place-items-center py-10 text-xs text-faint">loading outputs…</div>
      ) : groups.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line bg-panel2/20 py-10 text-center text-xs text-faint">No text outputs for this run yet.</div>
      ) : (
        <div className="space-y-4">
          {groups.map(([key, items]) => {
            const title = groupBy === "scenario" ? prettyScenario(key) : key;
            const sub = groupBy === "scenario" ? key : "model";
            return (
              <div key={key} className="rounded-xl border border-line bg-panel2/30 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-medium capitalize text-fg">{title}</span>
                    <span className="font-mono text-[11px] text-faint">{sub}</span>
                  </div>
                  <span className="pill bg-muted/15 text-muted">{items.length}</span>
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {items.map((output, index) => (
                    <TextCard
                      key={`${output.scenario}-${output.model}-${output.rep}-${index}`}
                      output={output}
                      crossLabel={groupBy === "scenario" ? output.model : prettyScenario(output.scenario)}
                      onOpen={() => setSelected(output)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selected && <TextModal output={selected} onClose={() => setSelected(null)} />}
    </section>
  );
}
