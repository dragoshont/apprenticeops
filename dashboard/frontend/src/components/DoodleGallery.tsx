import { useEffect, useMemo, useState } from "react";
import { Check, FileText, Images, ShieldCheck, Sparkles, X } from "lucide-react";

export type GroupBy = "scenario" | "model";

/** One judge's written review of a single doodle. */
export type DoodleReview = {
  judge: string;
  score: number | null;
  verdict?: string;
  met?: string[];
  missed?: string[];
};

export type DoodleOutput = {
  scenario: string;
  model: string;
  rep: number;
  detScore: number;
  /** Mean LLM-judge quality on the judge's 1–5 scale (optional until judged). */
  judgeScore?: number;
  /** Per-judge written verdicts (optional until judged). */
  reviews?: DoodleReview[];
  svg: string;
};

export type DoodleGalleryProps = {
  outputs: DoodleOutput[];
  runId?: string;
  loading?: boolean;
  defaultGroupBy?: GroupBy;
};

const DRAWABLE = /<(path|circle|rect|line|polygon|polyline|ellipse|text|use|image)\b/i;

function isPlaceholder(svg: string): boolean {
  return !DRAWABLE.test(svg);
}

function prettyScenario(id: string): string {
  return id.replace(/^doodle-/, "").replace(/-/g, " ");
}

/** Deterministic SVG-validity check (0–1): quiet when zero. */
function detTone(det: number): string {
  if (det >= 1) return "bg-good/15 text-good";
  if (det > 0) return "bg-info/15 text-info";
  return "bg-line/50 text-faint";
}

/** LLM-judge mean on a 1–5 scale: honest + quiet for the low end. */
function judgeTone(score: number): string {
  if (score >= 4) return "bg-good/15 text-good";
  if (score >= 3) return "bg-info/15 text-info";
  if (score >= 2) return "bg-warn/15 text-warn";
  return "bg-line/50 text-faint";
}

/**
 * Always-visible judge-score badge color. Honest gradient on the 1–5 scale: a
 * judge-approved doodle (≥4) pops bold emerald; weak ones recede in soft red.
 */
function judgeBadge(score: number): string {
  if (score >= 4) return "bg-good text-slate-900";
  if (score >= 3) return "bg-info text-slate-900";
  if (score >= 2) return "bg-warn text-slate-900";
  return "bg-bad/20 text-bad";
}

/** Tile ring that makes a judge-approved doodle pop out of its prompt group. */
function tileRing(score: number | undefined): string {
  if (score == null) return "border-line/60";
  if (score >= 4) return "border-good/70 ring-2 ring-good/40";
  if (score >= 3) return "border-info/60 ring-1 ring-info/30";
  return "border-line/60";
}

function GroupToggle({ value, onChange }: { value: GroupBy; onChange: (next: GroupBy) => void }) {
  const options: GroupBy[] = ["scenario", "model"];
  return (
    <div role="group" aria-label="Group doodles by" className="inline-flex rounded-lg border border-line bg-panel2/50 p-0.5">
      {options.map((option) => {
        const active = value === option;
        return (
          <label
            key={option}
            className={`cursor-pointer rounded-md px-2.5 py-1 text-[11px] font-medium transition focus-within:ring-2 focus-within:ring-accent ${active ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
          >
            <input
              type="radio"
              name="doodle-group-by"
              value={option}
              checked={active}
              onChange={() => onChange(option)}
              className="sr-only"
            />
            By {option}
          </label>
        );
      })}
    </div>
  );
}

/**
 * Renders an UNTRUSTED model-generated SVG safely.
 *
 * The SVG never touches the dashboard DOM. It is wrapped in a minimal HTML
 * document and handed to an `<iframe sandbox="">` — the empty sandbox token
 * disables scripts, same-origin access, forms, popups and top navigation, so
 * an embedded `<script>` or `onload=` payload cannot execute or reach the
 * parent page. SMIL `<animate>` is declarative (not script) and still plays.
 */
function SandboxedSvg({ svg, title }: { svg: string; title: string }) {
  const srcDoc = useMemo(
    () =>
      "<!doctype html><html><head><meta charset=\"utf-8\"><style>" +
      "html,body{margin:0;height:100%;display:flex;align-items:center;justify-content:center;background:transparent;overflow:hidden}" +
      "svg{max-width:100%;max-height:100%;height:auto;width:auto}" +
      "</style></head><body>" +
      svg +
      "</body></html>",
    [svg],
  );
  return (
    <iframe
      title={title}
      sandbox=""
      loading="lazy"
      srcDoc={srcDoc}
      className="h-full w-full border-0 bg-transparent"
    />
  );
}

function DoodleTile({ output, crossLabel, onOpen }: { output: DoodleOutput; crossLabel: string; onOpen: () => void }) {
  const placeholder = isPlaceholder(output.svg);
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
      className={`group relative aspect-square cursor-pointer overflow-hidden rounded-lg border bg-panel2/40 outline-none transition focus-visible:ring-2 focus-visible:ring-accent ${tileRing(output.judgeScore)}`}
    >
      {placeholder ? (
        <div className="flex h-full flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-line/60 px-2 text-center">
          <FileText className="h-4 w-4 text-faint" />
          <span className="text-[10px] text-faint">prose · no SVG</span>
        </div>
      ) : (
        <SandboxedSvg svg={output.svg} title={label} />
      )}

      {/* always-visible judge-score badge — the per-image headline signal */}
      {output.judgeScore != null ? (
        <span
          className={`pointer-events-none absolute right-1 top-1 inline-flex h-[18px] min-w-[20px] items-center justify-center rounded-md px-1 text-[11px] font-bold leading-none tabular-nums shadow-sm ring-1 ring-bg/40 ${judgeBadge(output.judgeScore)}`}
          title={`LLM-judge mean quality ${output.judgeScore.toFixed(1)} of 5`}
        >
          {output.judgeScore.toFixed(1)}
        </span>
      ) : (
        <span
          aria-hidden
          className="pointer-events-none absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-faint/50 ring-1 ring-bg/40"
          title="not yet judged"
        />
      )}

      {/* hover / keyboard-focus reveal */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-1 bg-gradient-to-t from-bg/95 via-bg/70 to-transparent p-2 opacity-0 transition duration-150 group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:translate-y-0 group-focus-within:opacity-100">
        <div className="truncate font-mono text-[11px] font-medium text-fg" title={crossLabel}>
          {crossLabel}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-1">
          <span className="pill bg-line/50 px-1.5 py-0 text-[10px] text-muted">rep {output.rep}</span>
          <span className={`pill px-1.5 py-0 text-[10px] ${detTone(output.detScore)}`} title="deterministic SVG-validity check (0–1)">
            <ShieldCheck className="h-2.5 w-2.5" />
            {output.detScore.toFixed(1)}
          </span>
          {output.judgeScore != null && (
            <span className={`pill px-1.5 py-0 text-[10px] ${judgeTone(output.judgeScore)}`} title="LLM-judge mean quality (1–5)">
              <Sparkles className="h-2.5 w-2.5" />
              {output.judgeScore.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function DoodleModal({ output, onClose }: { output: DoodleOutput; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const placeholder = isPlaceholder(output.svg);
  const reviews = output.reviews ?? [];
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Judge reviews for ${prettyScenario(output.scenario)} by ${output.model}`}
      onClick={onClose}
    >
      <div
        className="max-h-[88vh] w-full max-w-2xl overflow-auto rounded-2xl border border-line bg-panel shadow-glow"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-3 border-b border-line p-4">
          <div className="min-w-0">
            <div className="text-sm font-semibold capitalize text-fg">{prettyScenario(output.scenario)}</div>
            <div className="mt-0.5 font-mono text-[11px] text-faint">
              {output.model} · rep {output.rep} · {output.scenario}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-md p-1 text-muted outline-none transition hover:bg-panel2 hover:text-fg focus-visible:ring-2 focus-visible:ring-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="grid gap-4 p-4 sm:grid-cols-[180px_1fr]">
          <div className="space-y-2">
            <div className="aspect-square overflow-hidden rounded-xl border border-line bg-panel2/40">
              {placeholder ? (
                <div className="flex h-full items-center justify-center px-2 text-center text-[11px] text-faint">
                  prose · no SVG
                </div>
              ) : (
                <SandboxedSvg svg={output.svg} title={`${output.scenario} by ${output.model}`} />
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1">
              <span className={`pill px-1.5 py-0 text-[10px] ${detTone(output.detScore)}`} title="deterministic SVG-validity (0–1)">
                <ShieldCheck className="h-2.5 w-2.5" />
                det {output.detScore.toFixed(1)}
              </span>
              {output.judgeScore != null && (
                <span className={`pill px-1.5 py-0 text-[10px] font-semibold ${judgeBadge(output.judgeScore)}`} title="mean judge score (1–5)">
                  <Sparkles className="h-2.5 w-2.5" />
                  judge {output.judgeScore.toFixed(1)}
                </span>
              )}
            </div>
          </div>

          <div className="space-y-3">
            {reviews.length === 0 ? (
              <div className="rounded-xl border border-dashed border-line bg-panel2/20 p-3 text-center text-xs text-faint">
                No judge reviews recorded for this output.
              </div>
            ) : (
              reviews.map((rv, i) => (
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
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DoodleGallery({ outputs, runId, loading, defaultGroupBy = "scenario" }: DoodleGalleryProps) {
  const [groupBy, setGroupBy] = useState<GroupBy>(defaultGroupBy);
  const [selected, setSelected] = useState<DoodleOutput | null>(null);

  const { groups, scenarioCount, modelCount } = useMemo(() => {
    const scenarios = new Set<string>();
    const models = new Set<string>();
    const map = new Map<string, DoodleOutput[]>();
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

  const groupLabel = (key: string) =>
    groupBy === "scenario"
      ? { title: prettyScenario(key), sub: key }
      : { title: key, sub: "model" };

  return (
    <section id="doodles" className="card card-pad scroll-mt-24">
      <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-fg">
          <Images className="h-4 w-4 text-muted" />
          Results — Doodle Gallery
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
                {outputs.length} renders · {scenarioCount} scenarios · {modelCount} models
              </>
            )}
          </span>
        </div>
      </header>

      {loading ? (
        <div className="grid place-items-center py-10 text-xs text-faint">loading doodles…</div>
      ) : groups.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line bg-panel2/20 py-10 text-center text-xs text-faint">
          No SVG outputs for this run yet.
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map(([key, items]) => {
            const heading = groupLabel(key);
            return (
              <div key={key} className="rounded-xl border border-line bg-panel2/30 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-sm font-medium capitalize text-fg">{heading.title}</span>
                    <span className="font-mono text-[11px] text-faint">{heading.sub}</span>
                  </div>
                  <span className="pill bg-muted/15 text-muted">{items.length}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
                  {items.map((output, index) => (
                    <DoodleTile
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

      {selected && <DoodleModal output={selected} onClose={() => setSelected(null)} />}
    </section>
  );
}
