import type { ReactNode } from "react";

const NAV = [
  "Overview",
  "Evidence",
  "Method & paper",
  "Reproduce",
  "Review",
  "Research updates",
] as const;

/** Top navigation shell. CEOps is the umbrella; ApprenticeOps names the paper
 *  and first release — presented as one product, not two brands. */
export function Shell({
  current,
  children,
}: {
  current?: (typeof NAV)[number];
  children: ReactNode;
}) {
  return (
    <>
      <div className="shell shell--navonly">
        <nav className="shell__nav" aria-label="Primary">
          <div className="shell__brand">
            <span className="shell__mark">CEOps</span>
            <span className="shell__brandnote">ApprenticeOps benchmark &amp; paper</span>
          </div>
          <ul className="shell__links">
            {NAV.map((label) => (
              <li key={label}>
                <a
                  href="#"
                  aria-current={current === label ? "page" : undefined}
                >
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      {children}
    </>
  );
}
