---
title: "Write one story over canon, with its spine declared and every beat sourced"
id: HDSOP-ABU-008
version: 0.1
skill: add-story
doc_status: drafting
tags: [authoring, canon, story, provenance]
frequency: "once per property, which is every book"
est_time_per_run: "2-6 hours for a full beat sheet, 10 min for a stub"
automation_potential: "low"
related_skills: [casting-sweep, add-character, add-setting, render-book, compose-spec, make-a-book]
related_workflows: []
concepts: [canon, spine, universe, provenance, register, entity]
---

# Purpose

A property exists as a typed, medium-neutral StorySpec: a logline, a declared spine, a refrain,
and an ordered beat sheet where every beat cites a real source. The renderer projects it into a
medium later, so the same story can become a picture book without the words being written for a
picture book.

The outcome is a validated record, not a manuscript and not art.

# When to use (Trigger)

A new property is being composed out of existing or new canon: a book, a chapter, or any other
unit. Also when a planned property should appear on the roster before it is fully built, which
registers as a `stub`.

# Inputs / Prerequisites

- The target universe, with `identity` and existing `canon/entities/` and `stories/` readable.
- The source material: a testimony, a design brief, a braindump. Read BEFORE anything is asked.
- Whether it is ready to be beaten out or only worth registering as a placeholder.
- The author, available for four decisions that change the work materially and cannot be derived.

# Roles

| Role | Responsibility |
|---|---|
| **Author** | Owns the spine object and title, the beat-count target, how much of the book lives in a declared future, and how far forward that future goes. These are story-shaping decisions and they are theirs. |
| **Agent executor** | Does the reading first, counts the movements, batches the four decisions into ONE `AskUserQuestion` call with previews and a marked recommendation, runs the casting sweep over the beats, writes the StorySpec directly, and validates. |

# Procedure

Steps say WHAT happens. The flowchart says who; Automation Opportunities holds the ROI.

1. Do the reading FIRST: the source material, a canon sweep, and a count of the movements, before
   anything is asked.
2. Interview with `AskUserQuestion`, batching the four recurring decisions into one call, each
   with a `preview` showing the concrete artifact, and a recommendation first and marked. Do not
   ask what can be decided: register defaults to the universe's, so state the default and move on.
3. Capture the logline, the spine drawn from an open set, the refrain, any per-story register
   override, and the features plus ordered beats with per-beat provenance.
4. Decide `status`: `stub` for logline plus spine only, `full` when features, beats and provenance
   are filled.
5. Run the casting sweep over every entity named in `features` or a beat's `characters` and
   `location`. Reuse what exists; hand anything missing to the matching sibling `add-*` skill
   BEFORE finalizing.
6. Write `stories/<id>.json` directly. A story is a StorySpec, not an `add-entity` kind.
7. Validate and commit the story plus any entities the sweep created. Report the status and that
   rendering still requires `assert-story` separately.

# Process Flowchart

Amber = irreducibly human. Blue = agent-executed or agent-proposed.

```mermaid
flowchart TD
    A[A new property is being composed] --> B[Read the source, sweep canon, count the movements]
    B --> C{Four decisions, batched into one board}
    C --> D[Spine object and title, from the source's own words]
    C --> E[Beat-count target, drawn as a movement budget]
    C --> F[How much lives in the declared future]
    C --> G[How far forward the future goes]
    D --> H{Ready to beat out, or a placeholder?}
    E --> H
    F --> H
    G --> H
    H -->|Placeholder| I[Register as stub: logline and spine only]
    H -->|Ready| J[Write beats, each with its provenance]
    J --> K[Casting sweep over every named entity]
    K --> L{Anything not in canon?}
    L -->|Yes| M[Hand off to the matching add skill first]
    M --> K
    L -->|No| N[Write the StorySpec as full]
    I --> O[Validate and commit]
    N --> O
    classDef human fill:#fde68a,stroke:#b45309,color:#111827;
    classDef agent fill:#bfdbfe,stroke:#1e40af,color:#111827;
    class A,C,D,E,F,G,H human;
    class B,I,J,K,L,M,N,O agent;
```

# Done / Verification

`abu validate <universe>` is green. A `stub` is exempt from the features and beats requirements; a
`full` story must have non-empty `features` and `beats`, every beat's `provenance` non-empty, and
every featured id known to canon. Count the beats spent diagnosing against the beats spent on the
answer, and the beats living in the declared future, and confirm both ratios match what the author
chose rather than what drafting fatigue produced.

# Exceptions & Troubleshooting

- **There is no default length, and inventing a small one silently is the commonest authoring
  failure here.** A beat sheet written without a declared target lands around fifteen to twenty
  beats because that is where drafting fatigue sits, not because the argument ended. Shipped books
  range from about thirteen to well over thirty.
- **Cheap to add a beat now, expensive after the art exists.** Every later beat renumbers the
  render-spec, the manuscript, the platform manifest, the staged assets and the narration.
- **Proportion is a way of hedging that obeys every word of an anti-hedging rule.** Thirty beats
  on the problem and one on the promise has hedged, whatever the wording says. A quarter to a
  third of the beats is a normal share for a declared future, and more is fine when the future IS
  the subject.
- **Never assume hero-journey.** An explainer is a `primer`; a property built around one object's
  argued states is a `thesis`. Ask which shape this actually is.
- **An unsourced vivid detail does not go in a beat.** Provenance is per beat and it is validated.
- **A beat that only asserts needs a beat that shows.** A claim about a character's gift, wound or
  capacity that is stated and never depicted is a missing beat rather than economical writing.
- **The manuscript-to-story converter is DECLINED, deliberately.** The mechanical half is about
  ten lines; the valuable half, the cast and the provenance, is authored content that varies per
  book and per source. Promoting it would invent a manuscript-format contract the framework does
  not own, so the next book would be writing its manuscript to please a parser.

# Automation Opportunities

**Already automated:** schema validation of the stub-versus-full contract, the unresolved-feature
error, and the per-beat provenance requirement.

**Irreducibly human:** all four interview decisions, the spine, and every beat's text. This is the
skill in the framework with the least automatable core, and that is correct: it is where the work
is authored rather than assembled.

**Strongest next candidate:** a static proportion check reporting the diagnosis-to-answer ratio
and the declared-future share off a `full` story's own beats. Both rules are already written as
numbers, both are checked today by an agent remembering to count, and `render-book` names the same
check again at render time, which is the last cheap moment rather than the first.

# Related

- [casting-sweep](../casting-sweep/SKILL.md): the reuse gate step 5 runs.
- [compose-spec](../compose-spec/SKILL.md): turns this record into a render-spec, and carries a
  beat's `when` onto the spread for the era gate.
- [render-book](../render-book/SKILL.md): resolves the declared spine and genre against
  `list-craft` and stops when either does not exist.

# Revision History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-09-14 | Written from the skill file, read rather than recalled. |
