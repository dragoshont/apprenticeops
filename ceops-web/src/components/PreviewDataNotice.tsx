import { FlaskConical } from "lucide-react";

/** Site-wide honesty banner. The workbench must never read as real evidence. */
export function PreviewDataNotice() {
  return (
    <div className="notice" role="note">
      <FlaskConical size={15} strokeWidth={2} aria-hidden />
      <span>
        <strong>Illustrative preview data</strong> — this is a design workbench for
        the CEOps site. Model family names are real; every measurement shown is
        invented to exercise the layout and must not be cited as published
        evidence.
      </span>
    </div>
  );
}
