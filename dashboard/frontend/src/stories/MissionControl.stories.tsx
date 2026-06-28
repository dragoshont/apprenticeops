import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { DashboardMenu } from "../components/DashboardMenu";
import { RunControlCenter } from "../components/RunControlCenter";
import { CurrentRunSection } from "../components/CurrentRunSection";
import { RunLibrary } from "../components/RunLibrary";
import { NodeCards } from "../components/NodeCards";
import { Card } from "../components/ui";
import { runMatrix, sessions, progress, persistence, reliability, analyticsScope, selectedScope, runBatch, summary, modelProgress, modelStages, pareto, scores, nodes } from "./fixtures";

const meta = {
  title: "Mission Control/Dashboard",
  parameters: {
    layout: "fullscreen",
  },
  decorators: [
    (Story) => (
      <div className="min-h-screen bg-bg px-4 py-6 text-fg sm:px-6 lg:py-8">
        <div className="mx-auto max-w-7xl">
          <Story />
        </div>
      </div>
    ),
  ],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const TopMenu: Story = {
  render: () => {
    const [searchOpen, setSearchOpen] = useState(false);
    const [search, setSearch] = useState("granite");
    return (
      <DashboardMenu
        hasRun
        hasRunMatrix
        search={search}
        searchOpen={searchOpen}
        onToggleSearch={() => setSearchOpen((open) => !open)}
        onSearch={setSearch}
        onClearSearch={() => setSearch("")}
      />
    );
  },
};

export const StartControl: Story = {
  render: () => (
    <RunControlCenter
      runMatrix={runMatrix}
      runBatches={[]}
      activeSession={null}
      onSelectionChange={() => undefined}
      onAfter={() => undefined}
    />
  ),
};

export const CurrentRunWithBatch: Story = {
  render: () => (
    <CurrentRunSection
      title="Latest Run"
      description="The newest completed, stopped, or canceled run."
      state="done"
      live={false}
      displayBatch={runBatch}
      selectedRunId={sessions[0].run_id}
      selectedRunInBatch={runBatch.runs[0]}
      batchNotice={null}
      selectedScope={selectedScope}
      analyticsScope={analyticsScope}
      persistence={persistence}
      user="dragos"
      progress={progress}
      reliability={reliability}
      inputSelection={{ modelSet: "strategy-pilot-2", scenarioSet: "strategy-pilot-6", memoryContext: "none", inferenceStrategy: "best_of_3_detcheck" }}
      consumer={{ alive: false, status: "done", judged_rows: 120, judged_models: ["granite4:micro"], committed_models: ["granite4:micro"], ledger_tail: [], skips: [], skip_count: 0 }}
      producerAlive={false}
      models={modelStages}
      modelProgress={modelProgress}
      nodes={nodes}
      summary={summary}
      pareto={pareto}
      scores={scores}
      backToLatestRunId={null}
      onBackToLatest={() => undefined}
      onSelectRun={() => undefined}
    />
  ),
};

export const RunLibraryPage: Story = {
  render: () => {
    const [scope, setScope] = useState<"matching" | "all">("all");
    const [search, setSearch] = useState("");
    const [status, setStatus] = useState("all");
    const [date, setDate] = useState<"today" | "week" | "month" | "all">("all");
    const visible = sessions.filter((session) => {
      const text = [session.run_id, session.state, session.model_set, session.scenario_set, session.memory_context, session.inference_strategy].join(" ").toLowerCase();
      return (!search || text.includes(search.toLowerCase())) && (status === "all" || session.state === status);
    });
    return (
      <RunLibrary
        sessions={visible}
        scopedCount={sessions.length}
        matchingCount={1}
        totalCount={sessions.length}
        activeRunId={sessions[0].run_id}
        scope={scope}
        search={search}
        status={status}
        date={date}
        onScope={setScope}
        onSearch={setSearch}
        onStatus={setStatus}
        onDate={setDate}
        onSelect={() => undefined}
      />
    );
  },
};

export const HomeNoRun: Story = {
  render: () => (
    <div className="space-y-4">
      <DashboardMenu hasRun={false} hasRunMatrix search="" searchOpen={false} onToggleSearch={() => undefined} onSearch={() => undefined} onClearSearch={() => undefined} />
      <Card title="Home" right={<span className="text-xs text-faint">services from home</span>}>
        <p className="text-sm text-muted">The dashboard opens to operational context first: launch controls, run history, and the home/ai service cards stay visible even before a run is selected.</p>
      </Card>
      <NodeCards nodes={nodes} />
    </div>
  ),
};
