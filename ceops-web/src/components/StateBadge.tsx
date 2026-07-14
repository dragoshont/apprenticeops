import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  CircleSlash,
} from "lucide-react";
import type { EvidenceState } from "../lib/types";

const MAP: Record<
  EvidenceState,
  { label: string; Icon: typeof CheckCircle2; cls: string }
> = {
  verified: { label: "Verified", Icon: CheckCircle2, cls: "badge--verified" },
  qualified: { label: "Qualified", Icon: AlertTriangle, cls: "badge--qualified" },
  withdrawn: { label: "Withdrawn", Icon: XCircle, cls: "badge--withdrawn" },
  unavailable: {
    label: "Unavailable",
    Icon: CircleSlash,
    cls: "badge--unavailable",
  },
};

/** Evidence state: color plus a word, an icon and a border — never color alone. */
export function StateBadge({
  state,
  label,
}: {
  state: EvidenceState;
  label?: string;
}) {
  const { label: fallback, Icon, cls } = MAP[state];
  return (
    <span className={`badge ${cls}`}>
      <Icon size={13} strokeWidth={2.25} aria-hidden />
      {label ?? fallback}
    </span>
  );
}

/** Measurement type (Measured / Judged / Derived / Proxy) — a separate axis. */
export function MeasureBadge({ label }: { label: string }) {
  return <span className="badge badge--plain">{label}</span>;
}
