import { useEffect, useState } from "react";
import { Play, Pause, RotateCw, Square, ChevronDown, Loader2 } from "lucide-react";
import { control } from "../api";
import type { Batch, PipelineState } from "../types";

export function Controls({
  state,
  runId,
  batches,
  onAfter,
}: {
  state: PipelineState;
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

  return (
    <div className="flex flex-wrap items-center gap-2">
      {!active && (
        <div className="flex items-center overflow-hidden rounded-xl border border-line bg-ink-850">
          <div className="relative">
            <select
              value={batch}
              onChange={(e) => setBatch(e.target.value)}
              className="appearance-none bg-transparent py-2 pl-3 pr-8 text-sm text-slate-200 focus:outline-none"
            >
              {batches.map((b) => (
                <option key={b.id} value={b.id} className="bg-ink-850">
                  {b.label}
                  {b.count != null ? ` · ${b.count}` : ""}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          </div>
          <button
            className="btn btn-primary rounded-none border-0 border-l border-line"
            disabled={!chosen || busy != null}
            onClick={() => chosen && run("start", () => control.start(chosen.id))}
          >
            {busy === "start" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Start
          </button>
        </div>
      )}

      {running && (
        <button className="btn" disabled={busy != null} onClick={() => run("pause", control.pause)}>
          {busy === "pause" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Pause className="h-4 w-4" />}
          Pause
        </button>
      )}

      {(paused || (!active && runId)) && (
        <button
          className="btn"
          disabled={busy != null}
          onClick={() => run("resume", () => control.resume(runId))}
        >
          {busy === "resume" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCw className="h-4 w-4" />}
          {paused ? "Resume" : "Re-launch"}
        </button>
      )}

      {active && (
        <button
          className="btn btn-danger"
          disabled={busy != null}
          onClick={() => run("stop", control.stop)}
        >
          {busy === "stop" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
          Stop
        </button>
      )}

      {!active && chosen?.desc && (
        <span className="hidden max-w-[22rem] truncate text-xs text-slate-500 lg:inline">{chosen.desc}</span>
      )}
      {msg && <span className="text-xs text-bad">{msg}</span>}
    </div>
  );
}
