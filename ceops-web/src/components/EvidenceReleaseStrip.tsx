import type { ReleaseMeta } from "../lib/types";
import { StateBadge } from "./StateBadge";

function Item({ k, v }: { k: string; v: string }) {
  return (
    <span className="relstrip__item">
      <span className="relstrip__k">{k}</span>
      <span className="relstrip__v">{v}</span>
    </span>
  );
}

/** Full-width evidence-release identity: release, schema, correction, build,
 *  scope and status. Bound in production to release_id -> commit sha -> digest. */
export function EvidenceReleaseStrip({ release }: { release: ReleaseMeta }) {
  return (
    <div className="relstrip" aria-label="Evidence release">
      <Item k="Release" v={release.tag} />
      <Item k="Schema" v={release.schema} />
      <Item k="Corrected" v={release.corrected} />
      <Item k="Build" v={release.build} />
      <Item
        k="Scope"
        v={`${release.controlledScope} · ${release.breadthScope}`}
      />
      <span className="relstrip__status">
        <StateBadge state="qualified" label={release.status} />
      </span>
    </div>
  );
}
