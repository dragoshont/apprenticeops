---
description: "ApprenticeOps academic writing voice — auto-applies to the paper, README, and docs so the tone stays consistent without being re-explained. Full guide: .github/skills/paper-voice/SKILL.md."
applyTo: "docs/**/*.md,README.md,REPRODUCE.md"
---

# ApprenticeOps paper voice (auto-applied)

Write in the project's house academic voice. Full rules + examples live in
[`paper-voice` skill](../skills/paper-voice/SKILL.md); the load-bearing rules:

- **Honesty-first.** State scope and limits up front, as plainly as the claim.
  Use the house markers: "(state up front)", "**finding, not a gap**",
  "necessary-not-sufficient", `*(Locked.)*`.
- **Earn every claim** with a number, file/field name, standard, or released
  artifact — "reproducible, **not just asserted**".
- **First-person plural, active voice** ("We present/measure/report").
- **Confident but humble:** name the probable/uncomfortable outcome up front;
  dry wit is allowed in framing only, never in methods/results.
- **Falsifiable hypotheses; pre-registered analysis/gates** marked `*(Locked.)*`.
- **Threats to validity as a `Threat | Type | Mitigation` table**; every known
  weakness gets a concrete row.
- **Anti-overclaiming:** comparative not absolute, report **CIs** not point
  estimates, **bracket-level** claims when per-model is underpowered, no
  generality from **n=1** ("single-environment case study").
- **Define-then-use:** redefine ambiguous terms early ("offline =
  locally-sovereign inference, **not** information-starvation") and keep the
  measured path separate from eval scaffolding.
- **Formatting:** **bold** the load-bearing term; `backticks` for files/tags/
  fields; `>` blockquotes for honesty notes; `$…$`/`$$…$$` math with every symbol
  defined.
- **When adding a method, adversarially review it first** and fold the surviving
  caveats into the text.

Before shipping a paragraph: is each claim falsifiable + evidenced? Is the
limitation stated as plainly as the claim? Did I separate what we *proved* from
what we *hope*?
