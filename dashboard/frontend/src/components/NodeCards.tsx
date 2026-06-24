import { Server, Cpu, Wifi, WifiOff } from "lucide-react";
import { Card } from "./ui";
import type { NodeInfo } from "../types";

function NodeCard({
  name,
  role,
  info,
  accent,
}: {
  name: string;
  role: string;
  info?: NodeInfo;
  accent: "ai" | "home";
}) {
  const reachable = info?.reachable ?? false;
  const Icon = accent === "ai" ? Cpu : Server;
  const ring = accent === "ai" ? "text-accent" : "text-good";
  return (
    <Card className="flex-1">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`rounded-lg bg-ink-800 p-2 ${ring}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-100">{name}</div>
            <div className="text-[11px] text-slate-500">{role}</div>
          </div>
        </div>
        <span className={`pill ${reachable ? "bg-good/15 text-good" : "bg-bad/15 text-bad"}`}>
          {reachable ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {reachable ? "online" : "offline"}
        </span>
      </div>
      <dl className="mt-3 space-y-1 font-mono text-xs text-slate-400">
        {(info?.lines ?? []).map((l, i) => (
          <div key={i} className="truncate">
            {l}
          </div>
        ))}
        {!info?.lines?.length && <div className="text-slate-600">no telemetry</div>}
      </dl>
    </Card>
  );
}

export function NodeCards({ nodes }: { nodes?: { home: NodeInfo; ai: NodeInfo } }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <NodeCard name="ai" role="i5-8350U · locked inference · ollama 0.30.8" info={nodes?.ai} accent="ai" />
      <NodeCard name="home" role="orchestrator · judge · git" info={nodes?.home} accent="home" />
    </div>
  );
}
