import { LineChart, BookOpen, Cpu } from "lucide-react";

/** The three first-viewport actions from the brief (§7). */
export function PrimaryActions() {
  return (
    <div className="actions">
      <a className="btn btn--primary" href="#">
        <LineChart size={16} strokeWidth={2} aria-hidden />
        Inspect evidence
      </a>
      <a className="btn" href="#">
        <BookOpen size={16} strokeWidth={2} aria-hidden />
        Read the paper
      </a>
      <a className="btn" href="#">
        <Cpu size={16} strokeWidth={2} aria-hidden />
        Run on my hardware
      </a>
    </div>
  );
}
