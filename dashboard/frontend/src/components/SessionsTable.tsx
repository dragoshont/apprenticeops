import type { Session } from "../types";
import { Card, StatePill, Bar, fmtClock, fmtDur } from "./ui";
import { History, ChevronRight } from "lucide-react";

export function SessionsTable({
  sessions,
  activeRunId,
  onSelect,
  emptyText = "No runs yet.",
}: {
  sessions: Session[];
  activeRunId: string | null;
  onSelect: (runId: string) => void;
  emptyText?: string;
}) {
  return (
    <Card
      title="Sessions"
      icon={<History className="h-4 w-4 text-muted" />}
      right={<span className="text-xs text-faint">{sessions.length} runs</span>}
    >
      {sessions.length === 0 ? (
        <p className="py-6 text-center text-sm text-faint">{emptyText}</p>
      ) : (
        <div className="-mx-2 overflow-x-auto">
          <table className="w-full min-w-[820px] border-collapse text-sm">
            <caption className="sr-only">Runs — select a row to load its details below.</caption>
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-faint">
                <th className="px-2 py-2 font-medium">Run</th>
                <th className="px-2 py-2 font-medium">User</th>
                <th className="px-2 py-2 font-medium">Status</th>
                <th className="px-2 py-2 font-medium">Started</th>
                <th className="px-2 py-2 font-medium">Duration</th>
                <th className="px-2 py-2 font-medium">Models</th>
                <th className="px-2 py-2 font-medium">Work</th>
                <th className="px-2 py-2 font-medium">Progress</th>
                <th className="px-2 py-2 font-medium">ETA</th>
                <th className="px-2 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => {
                const active = s.run_id === activeRunId;
                return (
                  <tr
                    key={s.run_id}
                    onClick={() => onSelect(s.run_id)}
                    aria-current={active ? "true" : undefined}
                    className={`cursor-pointer border-t border-line/70 transition hover:bg-panel2/60 ${
                      active ? "bg-accent/[0.06]" : ""
                    }`}
                  >
                    <td className="px-2 py-2.5">
                      <div className="flex items-center gap-2">
                        {active && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
                        <span className="font-mono text-xs text-fg">{s.run_id}</span>
                      </div>
                      {(s.model_set || s.scenario_set) && (
                        <span className="mt-0.5 inline-block rounded bg-panel2 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                          {s.model_set || "models"} × {s.scenario_set || "scenarios"} × {s.memory_context || "none"}
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 text-xs text-muted">{s.user ?? "user"}</td>
                    <td className="px-2 py-2.5">
                      <StatePill state={s.state} size="sm" />
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 text-xs text-muted">
                      {fmtClock(s.started_at)}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 font-mono text-xs text-muted">
                      {fmtDur(s.duration_s)}
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 font-mono text-xs text-muted">
                      {s.models_done}
                      <span className="text-faint">/{s.models_total || "?"}</span>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 text-[11px] text-faint">
                      {s.scenarios}×{s.reps}
                      <span className="text-faint/70"> ·{s.njudges}j</span>
                    </td>
                    <td className="px-2 py-2.5">
                      <div className="flex items-center gap-2">
                        <Bar
                          value={s.pct}
                          max={100}
                          tone={
                            s.state === "canceled"
                              ? "bad"
                              : s.state === "done"
                                ? "good"
                                : "accent"
                          }
                          live={s.state === "running"}
                          className="w-24"
                        />
                        <span className="w-10 font-mono text-xs tabular-nums text-muted">
                          {s.pct}%
                        </span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-2 py-2.5 font-mono text-xs text-muted">
                      {s.state === "running" ? (s.eta_human ?? "—") : "—"}
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelect(s.run_id);
                        }}
                        aria-label={`Open run ${s.run_id} — ${s.state}, ${s.pct}% complete, by ${s.user ?? "user"}`}
                        className="inline-grid place-items-center rounded text-faint outline-none transition hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
