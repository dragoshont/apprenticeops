import { Card, Bar } from "./ui";
import type { Producer, Consumer } from "../types";
import { Upload, Scale } from "lucide-react";

export function ProgressCards({
  producer,
  consumer,
  expect,
}: {
  producer?: Producer;
  consumer?: Consumer;
  expect: number;
}) {
  const emitted = producer?.models_emitted ?? 0;
  const committed = consumer?.committed_models.length ?? 0;
  const judged = consumer?.judged_models.length ?? 0;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Card title="Producer · ai" icon={<Upload className="h-4 w-4 text-accent" />}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="label">Result rows</div>
            <div className="stat mt-1">{(producer?.rows ?? 0).toLocaleString()}</div>
          </div>
          <div>
            <div className="label">Models emitted</div>
            <div className="stat mt-1">
              {emitted}
              {expect > 0 && <span className="text-base text-slate-500"> / {expect}</span>}
            </div>
          </div>
        </div>
        <div className="mt-3">
          <Bar value={emitted} max={expect || emitted || 1} tone="accent" />
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className={`h-2 w-2 rounded-full ${producer?.run_py_alive ? "bg-good animate-pulse" : "bg-slate-600"}`} />
          <span className="text-slate-500">{producer?.run_py_alive ? "inferring" : "idle"}</span>
        </div>
      </Card>

      <Card title="Consumer · home" icon={<Scale className="h-4 w-4 text-good" />}>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="label">Judge rows</div>
            <div className="stat mt-1">{(consumer?.judged_rows ?? 0).toLocaleString()}</div>
          </div>
          <div>
            <div className="label">Judged</div>
            <div className="stat mt-1">{judged}</div>
          </div>
          <div>
            <div className="label">Committed</div>
            <div className="stat mt-1">
              {committed}
              {expect > 0 && <span className="text-base text-slate-500"> / {expect}</span>}
            </div>
          </div>
        </div>
        <div className="mt-3">
          <Bar value={committed} max={expect || committed || 1} tone="good" />
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs">
          <span className={`h-2 w-2 rounded-full ${consumer?.alive ? "bg-good animate-pulse" : "bg-slate-600"}`} />
          <span className="truncate text-slate-500">
            {consumer?.alive ? "judging" : "idle"}
            {consumer?.skip_count ? ` · ${consumer.skip_count} skips` : ""}
          </span>
        </div>
      </Card>
    </div>
  );
}
