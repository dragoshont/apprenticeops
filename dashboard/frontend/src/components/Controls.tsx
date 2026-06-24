import { useEffect, useState } from "react";
import { Play, Pause, RotateCw, Square, ChevronDown, Loader2 } from "lucide-react";
import { control } from "../api";
import type { Batch } from "../types";

export function Controls({
  state,
  runId,
  batches,
  onAfter,
  liveElsewhere = false,
}: {
  state: string;
  runId: string | null;
  batches: Batch[];
  onAfter: (runId?: string | null) => void;
  liveElsewhere?: boolean;
}) {
  const [batch, setBatch] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  // Batches load on the first status poll (after mount), so default the selection
  // once they arrive and keep it pointed at a batch that actually exists.
  useEffect(() => {
    if (batches.length && !batches.some((b) => b.id === batch)) {
      setBatch(batches[0].id);
    }
  }, [batches, batch]);

  const running = state === "running";
  const paused = state === "paused";
  const stopped = state === "stopped";
  const active = running || paused;
  const chosen = batches.find((b) => b.id === batch) ?? batches[0];

  async function run(action: string, fn: () => Promise<{ run_id?: string }>) {
    setBusy(action);
    setMsg(null);
    try {
      const r = await fn();
      setMsg(null);
      onAfter(r?.run_id ?? undefined);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const spin = (k: string, icon: React.ReactNode) =>
    busy === k ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : icon;

  const cbtn =
    "inline-flex items-center gap-1 rounded-lg border border-line bg-panel2/50 px-2.5 py-1.5 text-xs font-medium text-fg transition hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {!active && (
        <div className="flex items-center overflow-hidden rounded-lg border border-line bg-panel2 text-xs">
          <div className="relative">
            <select
              value={batch}
              onChange={(e) => setBatch(e.target.value)}
              className="appearance-none bg-transparent py-1.5 pl-2.5 pr-7 text-xs text-fg focus:outline-none"
            >
              {batches.map((b) => (
                <option key={b.id} value={b.id} className="bg-panel text-fg">
                  {b.label}
                  {b.count != null ? ` · ${b.count}` : ""}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
          </div>
          <button
            className="inline-flex items-center gap-1 border-l border-line bg-accent/15 px-2.5 py-1.5 font-medium text-accent transition hover:bg-accent/25 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!chosen || busy != null || liveElsewhere}
            title={liveElsewhere ? "A run is already running or paused — only one run can use the ai node. Follow it to control it." : undefined}
            onClick={() => chosen && run("start", () => control.start(chosen.id))}
          >
            {spin("start", <Play className="h-3.5 w-3.5" />)}
            Start
          </button>
        </div>
      )}

      {running && (
        <button className={cbtn} disabled={busy != null} onClick={() => run("pause", () => control.pause(runId))}>
          {spin("pause", <Pause className="h-3.5 w-3.5" />)}
          Pause
        </button>
      )}

      {(paused || stopped) && (
        <button
          className={`${cbtn} border-accent/50 bg-accent/15 text-accent`}
          disabled={busy != null}
          onClick={() => run("resume", () => control.resume(runId))}
        >
          {spin("resume", <RotateCw className="h-3.5 w-3.5" />)}
          {paused ? "Resume" : "Continue"}
        </button>
      )}

      {active && (
        <button
          className={`${cbtn} hover:border-bad/60 hover:bg-bad/10 hover:text-bad`}
          disabled={busy != null}
          onClick={() => run("stop", () => control.stop(runId))}
        >
          {spin("stop", <Square className="h-3.5 w-3.5" />)}
          Cancel
        </button>
      )}

      {msg && <span className="max-w-[16rem] truncate text-xs text-bad" title={msg}>{msg}</span>}
    </div>
  );
}
