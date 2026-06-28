import { X } from "lucide-react";
import type { Session } from "../types";
import { SessionsTable } from "./SessionsTable";

export function RunLibrary({
  sessions,
  scopedCount,
  matchingCount,
  totalCount,
  activeRunId,
  scope,
  search,
  status,
  date,
  onScope,
  onSearch,
  onStatus,
  onDate,
  onSelect,
}: {
  sessions: Session[];
  scopedCount: number;
  matchingCount: number;
  totalCount: number;
  activeRunId: string | null;
  scope: "matching" | "all";
  search: string;
  status: string;
  date: "today" | "week" | "month" | "all";
  onScope: (scope: "matching" | "all") => void;
  onSearch: (value: string) => void;
  onStatus: (status: string) => void;
  onDate: (date: "today" | "week" | "month" | "all") => void;
  onSelect: (runId: string) => void;
}) {
  return (
    <section id="library" className="scroll-mt-24 space-y-3">
      <div className="rounded-xl border border-line bg-panel2/30 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-medium text-fg">Library</div>
            <div className="mt-0.5 text-[11px] text-faint">Completed, canceled, stopped, and historical runs. Selecting one changes the Current Run section above.</div>
          </div>
          <div className="inline-flex overflow-hidden rounded-lg border border-line bg-panel text-xs">
            <button
              type="button"
              onClick={() => onScope("matching")}
              className={`px-2.5 py-1.5 transition ${scope === "matching" ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
            >
              Matching selection · {matchingCount}
            </button>
            <button
              type="button"
              onClick={() => onScope("all")}
              className={`border-l border-line px-2.5 py-1.5 transition ${scope === "all" ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
            >
              All sessions · {totalCount}
            </button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            value={status}
            onChange={(event) => onStatus(event.target.value)}
            className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-fg outline-none transition focus:border-accent/60"
            aria-label="Filter sessions by status"
          >
            <option value="all">Any status</option>
            <option value="running">Running</option>
            <option value="done">Done</option>
            <option value="canceled">Canceled</option>
            <option value="failed">Failed</option>
            <option value="stopped">Stopped</option>
          </select>
          <div className="inline-flex overflow-hidden rounded-lg border border-line bg-panel text-xs">
            {(["today", "week", "month", "all"] as const).map((dateScope) => (
              <button
                key={dateScope}
                type="button"
                onClick={() => onDate(dateScope)}
                className={`px-2.5 py-2 capitalize transition ${date === dateScope ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`}
              >
                {dateScope === "week" ? "This week" : dateScope === "month" ? "This month" : dateScope}
              </button>
            ))}
          </div>
          {search && (
            <button
              type="button"
              onClick={() => onSearch("")}
              className="pill bg-accent/10 text-accent transition hover:bg-accent/15"
              title={`Clear search: ${search}`}
            >
              Search · {search}
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
        <div className="mt-2 text-[11px] text-faint">Showing {sessions.length} of {scopedCount} sessions in this scope.</div>
      </div>
      <SessionsTable
        sessions={sessions}
        activeRunId={activeRunId}
        onSelect={onSelect}
        title="Run Library"
        emptyText={scope === "matching" ? "No runs match the selected model, scenario, and memory context yet." : "No runs yet."}
      />
    </section>
  );
}