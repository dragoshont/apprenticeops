import { useEffect, useMemo, useState } from "react";
import { BookOpen, Boxes, Database, FileSearch, Loader2, Search, Workflow } from "lucide-react";
import { fetchInputs } from "../api";
import type { InputDetails, InputScenarioDetails } from "../types";
import { Card } from "./ui";

type Tab = "memory" | "strategy" | "scenarios" | "models";

export function InputInspector({ selection, title = "Experiment Inputs" }: { selection: { modelSet: string; scenarioSet: string; memoryContext: string; inferenceStrategy?: string }; title?: string }) {
  const [tab, setTab] = useState<Tab>("memory");
  const [query, setQuery] = useState("");
  const [details, setDetails] = useState<InputDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selection.modelSet || !selection.scenarioSet || !selection.memoryContext) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInputs(selection.modelSet, selection.scenarioSet, selection.memoryContext, selection.inferenceStrategy ?? "baseline")
      .then((data) => {
        if (!cancelled) setDetails(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selection.modelSet, selection.scenarioSet, selection.memoryContext, selection.inferenceStrategy]);

  const normalizedQuery = query.trim().toLowerCase();
  const scenarios = useMemo(() => {
    const rows = details?.scenarios ?? [];
    if (!normalizedQuery) return rows;
    return rows.filter((item) =>
      [item.id, item.class, item.difficulty, item.grounding, item.context, item.question, item.gold_answer, item.judge_rubric, item.prompt]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedQuery)),
    );
  }, [details?.scenarios, normalizedQuery]);
  const models = useMemo(() => {
    const rows = details?.model_set.models ?? [];
    if (!normalizedQuery) return rows;
    return rows.filter((item) => `${item.id} ${item.bracket ?? ""}`.toLowerCase().includes(normalizedQuery));
  }, [details?.model_set.models, normalizedQuery]);

  return (
    <Card
      title={title}
      icon={<FileSearch className="h-4 w-4 text-muted" />}
      right={loading ? <Loader2 className="h-4 w-4 animate-spin text-faint" /> : <span className="text-xs text-faint">read-only</span>}
      hint="Inspect the exact memory, scenarios, prompts, and model roster used for the selected run condition."
    >
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="inline-flex overflow-hidden rounded-lg border border-line bg-panel2 text-xs">
            <TabButton active={tab === "memory"} onClick={() => setTab("memory")} icon={<BookOpen className="h-3.5 w-3.5" />}>
              Memory
            </TabButton>
            <TabButton active={tab === "strategy"} onClick={() => setTab("strategy")} icon={<Workflow className="h-3.5 w-3.5" />}>
              Strategy
            </TabButton>
            <TabButton active={tab === "scenarios"} onClick={() => setTab("scenarios")} icon={<Database className="h-3.5 w-3.5" />}>
              Scenarios · {details?.scenarios.length ?? 0}
            </TabButton>
            <TabButton active={tab === "models"} onClick={() => setTab("models")} icon={<Boxes className="h-3.5 w-3.5" />}>
              Models · {details?.model_set.models.length ?? 0}
            </TabButton>
          </div>
          <label className="relative min-w-[14rem] flex-1 sm:max-w-xs">
            <span className="sr-only">Search inputs</span>
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search scenarios, prompts, models…"
              className="w-full rounded-lg border border-line bg-panel2 py-1.5 pl-8 pr-3 text-xs text-fg outline-none transition placeholder:text-faint focus:border-accent/60"
            />
          </label>
        </div>

        {error && <div className="rounded-lg border border-bad/30 bg-bad/10 px-3 py-2 text-xs text-bad">{error}</div>}

        {tab === "memory" && <MemoryPane details={details} />}
        {tab === "strategy" && <StrategyPane details={details} />}
        {tab === "scenarios" && <ScenarioPane scenarios={scenarios} query={normalizedQuery} />}
        {tab === "models" && <ModelPane models={models} />}
      </div>
    </Card>
  );
}

function TabButton({ active, onClick, icon, children }: { active: boolean; onClick: () => void; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 transition ${active ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
    >
      {icon}
      {children}
    </button>
  );
}

function StrategyPane({ details }: { details: InputDetails | null }) {
  const strategy = details?.inference_strategy;
  if (!details) return <p className="py-5 text-center text-sm text-faint">Loading selected inputs…</p>;
  if (!strategy) return <p className="rounded-xl border border-line bg-panel2/30 p-4 text-sm text-muted">No inference strategy metadata is available.</p>;
  return (
    <div className="rounded-xl border border-line bg-panel2/30 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-medium text-fg">{strategy.label}</div>
          <div className="text-xs text-faint">
            {strategy.id} · {strategy.candidate_count ?? 1} candidate{strategy.candidate_count === 1 ? "" : "s"} · {strategy.selection_method ?? "single_call"}
          </div>
        </div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">inference_strategy={strategy.id}</span>
      </div>
      {strategy.markdown ? (
        <div className="max-h-96 overflow-auto pr-2">
          <MarkdownView text={strategy.markdown} />
        </div>
      ) : (
        <p className="text-sm text-muted">No extra strategy prompt is injected. The runner uses the strategy implementation itself.</p>
      )}
    </div>
  );
}

function MemoryPane({ details }: { details: InputDetails | null }) {
  const memory = details?.memory_context;
  if (!details) return <p className="py-5 text-center text-sm text-faint">Loading selected inputs…</p>;
  if (!memory?.markdown) {
    return <p className="rounded-xl border border-line bg-panel2/30 p-4 text-sm text-muted">No memory context is injected for this selection.</p>;
  }
  return (
    <div className="rounded-xl border border-line bg-panel2/30 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-medium text-fg">{memory.label}</div>
          <div className="text-xs text-faint">{memory.path} · {memory.chars.toLocaleString()} chars</div>
        </div>
        <span className="rounded bg-panel px-2 py-1 font-mono text-[10px] text-faint">{memory.id}</span>
      </div>
      <div className="max-h-96 overflow-auto pr-2">
        <MarkdownView text={memory.markdown} />
      </div>
    </div>
  );
}

function ScenarioPane({ scenarios, query }: { scenarios: InputScenarioDetails[]; query: string }) {
  if (!scenarios.length) {
    return <p className="py-5 text-center text-sm text-faint">No scenarios match {query ? `“${query}”` : "this selection"}.</p>;
  }
  return (
    <div className="space-y-2">
      {scenarios.map((scenario) => (
        <details key={scenario.id} className="rounded-xl border border-line bg-panel2/30 p-3">
          <summary className="cursor-pointer list-none">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-mono text-xs text-fg">{scenario.id}</span>
              {scenario.class && <Badge>{scenario.class}</Badge>}
              {scenario.difficulty && <Badge>{scenario.difficulty}</Badge>}
              {scenario.grounding && <Badge>{scenario.grounding}</Badge>}
              <span className="ml-auto text-[11px] text-faint">{scenario.prompt_chars.toLocaleString()} prompt chars</span>
            </div>
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">{scenario.question}</p>
          </summary>
          <div className="mt-3 space-y-3 border-t border-line/60 pt-3">
            <TextBlock title="Context" text={scenario.context} />
            <TextBlock title="Task" text={scenario.question} />
            <TextBlock title="Full model input" text={scenario.prompt} mono />
            <TextBlock title="Gold answer" text={scenario.gold_answer} />
            <TextBlock title="Judge rubric" text={scenario.judge_rubric} />
            <div>
              <div className="label mb-1">Deterministic checks</div>
              <pre className="max-h-56 overflow-auto rounded-lg border border-line bg-panel p-3 text-[11px] leading-relaxed text-muted">
                {JSON.stringify(scenario.deterministic_checks, null, 2)}
              </pre>
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}

function ModelPane({ models }: { models: { id: string; bracket?: string | null }[] }) {
  if (!models.length) return <p className="py-5 text-center text-sm text-faint">No models match this search.</p>;
  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {models.map((model) => (
        <div key={model.id} className="rounded-lg border border-line bg-panel2/30 px-3 py-2">
          <div className="break-all font-mono text-xs text-fg">{model.id}</div>
          {model.bracket && <div className="mt-1 text-[11px] text-faint">{model.bracket}</div>}
        </div>
      ))}
    </div>
  );
}

function TextBlock({ title, text, mono = false }: { title: string; text: string; mono?: boolean }) {
  if (!text) return null;
  return (
    <div>
      <div className="label mb-1">{title}</div>
      <pre className={`max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-panel p-3 text-xs leading-relaxed text-muted ${mono ? "font-mono" : "font-sans"}`}>
        {text}
      </pre>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded bg-panel px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-faint">{children}</span>;
}

function MarkdownView({ text }: { text: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed text-muted">
      {text.split("\n").map((line, index) => {
        const key = `${index}-${line.slice(0, 12)}`;
        if (!line.trim()) return <div key={key} className="h-1" />;
        if (line.startsWith("# ")) return <h3 key={key} className="mt-3 text-base font-semibold text-fg">{line.slice(2)}</h3>;
        if (line.startsWith("## ")) return <h4 key={key} className="mt-3 text-sm font-semibold text-fg">{line.slice(3)}</h4>;
        if (line.startsWith("---")) return <hr key={key} className="border-line" />;
        if (line.startsWith("- ")) return <div key={key} className="pl-3"><span className="text-faint">• </span>{line.slice(2)}</div>;
        if (/^\s/.test(line)) return <pre key={key} className="whitespace-pre-wrap rounded bg-panel px-2 py-1 font-mono text-xs text-faint">{line}</pre>;
        return <p key={key}>{line}</p>;
      })}
    </div>
  );
}