---
name: paper-voice
description: "Use whenever writing or editing the ApprenticeOps paper, README, or docs (PAPER.md, README.md, REPRODUCE.md, PLAN.md, MARKET.md, TAXONOMY.md, TELEMETRY.md, MODELS.md, PAPER_INTENT.md, PAPER_PHASES.md). The house academic voice: rigorous, honesty-first, anti-overclaiming, practitioner-readable, dry-witty in framing only. Apply it without being asked. Trigger phrases: 'write the paper', 'edit PAPER.md', 'paper voice', 'academic tone', 'add a section', 'reword this', 'document this finding'."
argument-hint: "What part of the paper/docs are you writing or editing?"
---

# ApprenticeOps paper voice

The academic voice for this project, distilled from the manuscript and its review
history. Apply it by default to all paper/README/docs prose. The goal: a reviewer
trusts it AND a homelab operator can read it.

## Core stance (non-negotiable)

1. **Honesty-first.** State scope and limits *up front*, as plainly as the claim
   itself. A limitation you name beats one a reviewer finds. Use the literal
   markers we use: "(state up front)", "Scope honesty", "**finding, not a gap**",
   "necessary-not-sufficient".
2. **Earn every claim with evidence** — numbers, file/field names, a standard, or
   a released artifact. "Released so reproducible, **not just asserted**."
3. **Rigor with readability.** Falsifiable hypotheses, pre-registration, threats
   tables — but written so a practitioner follows it. Define jargon on first use.
4. **Anti-overclaiming is the heart of the voice.** Separate what we *proved* from
   what we *hope*; the maturity ladder is motivation, the bottom rungs are the
   result.

## Tone

- **First-person plural, active voice:** "We present", "we measure", "we report".
- **Confident but humble:** name the probable/uncomfortable outcome up front, e.g.
  "A ≤5 GB model will not match the frontier at homelab diagnosis — the realistic
  win is …". Pre-empting the let-down *is* the credibility.
- **Dry wit only in the intro/framing**, never in methods/results. One wry, true
  line is allowed (e.g. "the 2018 ThinkPad is not a weakness; it is the
  *measurement point*"). Never jokey, never sloppy, never a pun in a results table.
- **Precise > flowery.** Short declarative for the claim; an em-dash or parenthetical
  for the caveat riding behind it.

## Structure & discipline

- Numbered sections. Every research question gets a **falsifiable** hypothesis.
- **Pre-registration:** write the analysis plan and any decision gates *before*
  looking at the data, and mark them **\*(Locked.)\***.
- **Threats to validity is a table:** `Threat | Type | Mitigation`. Every known
  weakness earns a row; the mitigation is concrete (a file, a method, a number).
- **Positioning tables** vs prior work that *sharpen* the contribution — show the
  overlap honestly, then the one column that is new.
- **Adversarial review before shipping:** when you add a method, attack it, then
  enumerate the surviving caveats in-text ("this method was attacked before
  shipping"). A held/negative result is a contribution, not a hole.

## Formatting idioms (match these exactly)

- **Bold** the load-bearing term, decision, or verdict in a sentence.
- *Italics* for defined terms and emphasis inside a caveat.
- `backticks` for files, model tags, fields, commands, identifiers.
- `>` blockquotes for "state up front" honesty notes and caveats.
- Math: inline `$...$`, display `$$...$$`; **define every symbol** right after.
- Markers in active use: `*(Locked.)*`, "(REQUIRED)", "necessary-not-sufficient",
  "finding, not a gap", "DONE"/"⏳ not yet run" for build status.
- File references in backticks with a relative link when pointing at a repo file.

## Define-then-use (a signature move)

Redefine ambiguous terms precisely and early, and keep the distinction visible:

- "**offline = locally-sovereign inference** (no external *model* API), **not**
  information-starvation."
- Separate the **measured path** from **scaffolding** (the judge is eval-time, the
  system-under-test never calls it).

## Anti-overclaiming rules (apply to every quantitative claim)

1. **Comparative, not absolute**, where it matters; report **CIs**, not point
   estimates; make **bracket-level** claims when per-model is underpowered (say so).
2. **No unearned generality from n=1** — "single-environment case study", invite
   re-runs.
3. **Name the mechanism and the file**, never passive hand-waving.
4. **Distinguish achieved vs roadmap** explicitly in the same breath.

## Don'ts (these read as slop here)

- No hype: "revolutionary", "state-of-the-art" without a number, "beats GPT-4".
- No marketing adjectives in methods/results.
- No vague "it is well known that …"; cite or measure.
- No buried limitation; if it's load-bearing, it goes near the claim, not in a
  footnote.

## Litmus test before shipping a paragraph

1. Is each claim **falsifiable** and **evidenced**?
2. Is the **limitation stated as plainly** as the claim?
3. Could a reviewer find a gap I didn't name? (If yes, name it.)
4. Did I separate **what we proved** from **what we hope**?

## Pairs with

- [`adversarial-review`](../../skills/adversarial-review/SKILL.md) — attack a new
  section/method before shipping; fold the surviving caveats into the prose.
- Diátaxis for docs that mix tutorial/how-to/reference/explanation audiences.
