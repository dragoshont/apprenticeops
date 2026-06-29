import { useMemo, useState } from "react";
import { FileText, Images, ShieldCheck, Sparkles } from "lucide-react";

export type GroupBy = "scenario" | "model";

export type DoodleOutput = {
  scenario: string;
  model: string;
  rep: number;
  detScore: number;
  /** Mean LLM-judge quality on the judge's 1–5 scale (optional until judged). */
  judgeScore?: number;
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

/** A single quiet at-rest dot encoding output health without adding chrome. */
function statusDot(output: DoodleOutput, placeholder: boolean): string {
  if (placeholder) return "bg-faint/50";
  const judge = output.judgeScore ?? 0;
  if (judge >= 3 || output.detScore >= 1) return "bg-accent";
  if (output.detScore > 0 || judge >= 2) return "bg-info/80";
  return "bg-faint/60";
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

function DoodleTile({ output, crossLabel }: { output: DoodleOutput; crossLabel: string }) {
  const placeholder = isPlaceholder(output.svg);
  const label = `${prettyScenario(output.scenario)} by ${output.model}, rep ${output.rep}`;
  return (
    <div
      tabIndex={0}
      aria-label={label}
      className="group relative aspect-square overflow-hidden rounded-lg border border-line/60 bg-panel2/40 outline-none transition focus-visible:ring-2 focus-visible:ring-accent"
    >
      {placeholder ? (
        <div className="flex h-full flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-line/60 px-2 text-center">
          <FileText className="h-4 w-4 text-faint" />
          <span className="text-[10px] text-faint">prose · no SVG</span>
        </div>
      ) : (
        <SandboxedSvg svg={output.svg} title={label} />
      )}

      {/* at-rest health dot — the only chrome on a resting tile */}
      <span
        aria-hidden
        className={`pointer-events-none absolute right-1.5 top-1.5 h-2 w-2 rounded-full ring-1 ring-bg/40 ${statusDot(output, placeholder)}`}
      />

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

export function DoodleGallery({ outputs, runId, loading, defaultGroupBy = "scenario" }: DoodleGalleryProps) {
  const [groupBy, setGroupBy] = useState<GroupBy>(defaultGroupBy);

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
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
