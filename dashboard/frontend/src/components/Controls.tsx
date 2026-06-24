import { useEffect, useState } from "react";
import { Play, Pause, RotateCw, Square, ChevronDown, Loader2 } from "lucide-react";
import { control } from "../api";
import type { Batch } from "../types";

export function Controls({
  state,
  runId,
  batches,
  onAfter,
}: {
  state: string;
  runId: string | null;
  batches: Batch[];
  onAfter: (runId?: string | null) => void;
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
    busy === k ? <Loader2 className="h-4 w-4 animate-spin" /> : icon;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {!active && (
        <div className="flex items-center overflow-hidden rounded-xl border border-line bg-panel2">
          <div className="relative">
            <select
              value={batch}
              onChange={(e) => setBatch(e.target.value)}
              className="appearance-none bg-transparent py-2 pl-3 pr-8 text-sm text-fg focus:outline-none"
            >
              {batches.map((b) => (
                <option key={b.id} value={b.id} className="bg-panel text-fg">
                  {b.label}
                  {b.count != null ? ` · ${b.count}` : ""}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
          </div>
          <button
            className="btn btn-primary rounded-none border-0 border-l border-line"
            disabled={!chosen || busy != null}
            onClick={() => chosen && run("start", () => control.start(chosen.id))}
          >
            {spin("start", <Play className="h-4 w-4" />)}
            Start
          </button>
        </div>
      )}

      {running && (
        <button className="btn" disabled={busy != null} onClick={() => run("pause", () => control.pause(runId))}>
          {spin("pause", <Pause className="h-4 w-4" />)}
          Pause
        </button>
      )}

      {(paused || stopped) && (
        <button
          className="btn btn-primary"
          disabled={busy != null}
          onClick={() => run("resume", () => control.resume(runId))}
        >
          {spin("resume", <RotateCw className="h-4 w-4" />)}
          {paused ? "Resume" : "Continue"}
        </button>
      )}

      {active && (
        <button
          className="btn btn-danger"
          disabled={busy != null}
          onClick={() => run("stop", () => control.stop(runId))}
        >
          {spin("stop", <Square className="h-4 w-4" />)}
          Stop
        </button>
      )}

      {!active && chosen?.desc && (
        <span className="hidden max-w-[20rem] truncate text-xs text-faint xl:inline">{chosen.desc}</span>
      )}
      {msg && <span className="max-w-[16rem] truncate text-xs text-bad" title={msg}>{msg}</span>}
    </div>
  );
}
