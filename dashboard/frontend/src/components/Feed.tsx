import { Card } from "./ui";
import type { Consumer } from "../types";
import { Activity, AlertTriangle } from "lucide-react";

function ago(ts?: number) {
  if (!ts) return "";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export function ActivityFeed({ consumer }: { consumer?: Consumer }) {
  const events = [...(consumer?.ledger_tail ?? [])].reverse();
  return (
    <Card title="Activity" icon={<Activity className="h-4 w-4 text-good" />}>
      {events.length === 0 ? (
        <p className="py-6 text-center text-sm text-faint">No events yet.</p>
      ) : (
        <ul className="max-h-72 space-y-1.5 overflow-auto pr-1">
          {events.map((e, i) => {
            const ok = e.ok === 1 || e.ok === true;
            return (
              <li key={i} className="flex items-start gap-2.5 text-xs">
                <span className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${ok ? "bg-good" : "bg-bad"}`} />
                <span className="w-12 shrink-0 font-mono text-faint">{ago(e.ts)}</span>
                <span className="w-16 shrink-0 font-medium capitalize text-muted">{e.stage ?? "—"}</span>
                <span className="flex-1 truncate font-mono text-muted">
                  {e.model && e.model !== "*" ? <span className="text-fg">{e.model} </span> : null}
                  {e.detail}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export function SkipsFeed({ consumer }: { consumer?: Consumer }) {
  const skips = [...(consumer?.skips ?? [])].reverse();
  if (skips.length === 0) return null;
  return (
    <Card
      title="Skips & errors"
      icon={<AlertTriangle className="h-4 w-4 text-warn" />}
      right={<span className="text-xs text-warn">{consumer?.skip_count ?? skips.length}</span>}
    >
      <ul className="max-h-48 space-y-1 overflow-auto pr-1 font-mono text-[11px] text-muted">
        {skips.map((s, i) => (
          <li key={i} className="truncate border-l-2 border-warn/40 pl-2">
            {s}
          </li>
        ))}
      </ul>
    </Card>
  );
}
