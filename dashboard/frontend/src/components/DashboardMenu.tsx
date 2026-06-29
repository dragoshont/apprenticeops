import type { ReactNode } from "react";
import { History, Home, Images, ListChecks, Radio, Rocket, Search, X } from "lucide-react";

export function DashboardMenu({
  hasRun,
  hasRunMatrix,
  hasDoodles = false,
  runDetailLabel = "Run Detail",
  search,
  searchOpen,
  onToggleSearch,
  onSearch,
  onClearSearch,
}: {
  hasRun: boolean;
  hasRunMatrix: boolean;
  hasDoodles?: boolean;
  runDetailLabel?: string;
  search: string;
  searchOpen: boolean;
  onToggleSearch: () => void;
  onSearch: (value: string) => void;
  onClearSearch: () => void;
}) {
  const expanded = searchOpen || Boolean(search);
  return (
    <nav aria-label="Dashboard sections" className="sticky top-2 z-30 mb-4 rounded-xl border border-line bg-panel/85 p-1.5 shadow-lg shadow-bg/20 backdrop-blur-md">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-1 text-xs">
          <MenuLink href="#home" icon={<Home className="h-3.5 w-3.5" />}>Home</MenuLink>
          <MenuLink href="#start" icon={<Rocket className="h-3.5 w-3.5" />}>Start</MenuLink>
          <MenuLink href="#current-run" disabled={!hasRun} icon={<Radio className="h-3.5 w-3.5" />}>{runDetailLabel}</MenuLink>
          <MenuLink href="#library" icon={<History className="h-3.5 w-3.5" />}>Run History</MenuLink>
          <MenuLink href="#scenarios" disabled={!hasRunMatrix} icon={<ListChecks className="h-3.5 w-3.5" />}>Scenarios</MenuLink>
          <MenuLink href="#doodles" disabled={!hasDoodles} icon={<Images className="h-3.5 w-3.5" />}>Results</MenuLink>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-1.5 text-xs lg:justify-end">
          <button
            type="button"
            onClick={onToggleSearch}
            aria-label="Search run history"
            className={`inline-grid h-8 w-8 place-items-center rounded-lg border transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${expanded ? "border-accent/50 bg-accent/15 text-accent" : "border-line bg-panel2/50 text-muted hover:border-accent/50 hover:text-accent"}`}
            title="Search run history"
          >
            <Search className="h-3.5 w-3.5" />
          </button>
          {expanded && (
            <label className="relative min-w-[14rem] flex-1 lg:w-72 lg:flex-none">
              <span className="sr-only">Search sessions</span>
              <input
                id="session-search"
                value={search}
                onChange={(event) => onSearch(event.target.value)}
                placeholder="Search runs, status, model, scenario..."
                className="h-8 w-full rounded-lg border border-line bg-panel2/70 py-1.5 pl-3 pr-8 text-xs text-fg outline-none transition placeholder:text-faint focus:border-accent/60"
              />
              {search && (
                <button
                  type="button"
                  onClick={onClearSearch}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded text-faint transition hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                  aria-label="Clear session search"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </label>
          )}
        </div>
      </div>
    </nav>
  );
}

function MenuLink({
  href,
  icon,
  disabled = false,
  children,
}: {
  href: string;
  icon: ReactNode;
  disabled?: boolean;
  children: ReactNode;
}) {
  const className = `inline-flex h-8 items-center gap-1.5 rounded-lg border px-2.5 font-medium transition ${
    disabled
      ? "pointer-events-none border-line/50 bg-panel2/20 text-faint opacity-50"
      : "border-transparent text-muted hover:border-line hover:bg-panel2/70 hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
  }`;

  if (disabled) {
    return (
      <span className={className}>
        {icon}
        {children}
      </span>
    );
  }

  return (
    <a href={href} className={className}>
      {icon}
      {children}
    </a>
  );
}