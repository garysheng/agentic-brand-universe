---
title: "Put one physical object into canon so it is the same object on every page"
id: HDSOP-ABU-005
version: 0.1
skill: add-prop
doc_status: drafting
tags: [authoring, canon, entity]
frequency: "a handful of times per universe, more in an object-heavy story"
est_time_per_run: "15-25 min"
automation_potential: "medium"
related_skills: [casting-sweep, shoot-references, add-motif, add-character, add-generator]
related_workflows: []
concepts: [canon, entity, invariant, register, prop]
---

# Purpose

A discrete object a character holds, wears or uses exists as a typed canon record with two
reference slots scaffolded, so it reads as THE SAME object across every render rather than as a
similar one.

This is authoring, not art. It ends at a validated `stub` entity plus ready-to-run prompts.

# When to use (Trigger)

A story names an object that will appear more than once and whose identity matters. Two
characters can share one canonical prop, so the sweep runs before the naming does.

# Inputs / Prerequisites

- The target universe, a path containing `universe.json`. Its `identity` and `assetRoot` are read
  here.
- What the object is: form, material, and who holds, wears or uses it and how.
- HOW BIG IT IS, in human terms, pinned to something a render already contains. Asked explicitly
  and never skipped, the way `add-setting` asks a room's size and `add-character` a person's.
- Its LOAD-BEARING DETAIL: the one feature that must never drift, such as an engraving, a wear
  mark, a colour, a proportion. Without it the prop reads as a similar object rather than the
  same one.

# Roles

| Role | Responsibility |
|---|---|
| **Human operator** | Names the object and its load-bearing detail, says who is allowed to touch it if that is canon, and settles an ambiguous reuse. |
| **Agent executor** | Sweeps canon first, interviews for exactly what the two slots need, scaffolds with the tested machinery, writes both prompts with the register anchor first, and stops before any image call. |

# Procedure

Steps say WHAT happens. The flowchart says who; Automation Opportunities holds the ROI.

1. Casting sweep first. Sweep `canon/entities/` and any CANON.md for an existing object that
   already covers this role. Proceed only if genuinely new.
2. Interview one question at a time: what the object is, HOW BIG it is in human terms, and its
   load-bearing detail.
3. Scaffold with `add-entity <universe> prop <id> --name`, which writes
   `structured.sheets: {"hero": null, "detail": null}` and an empty `requiredForRender`.
4. Fill `prose` with what the object means and who may touch it, and `structured.invariants` with
   the load-bearing rules the read-back will check.
4a. Fill `structured.scale.absolute` with the size, as one sentence pinned to things a render
   already contains ("about twice the height of the mug beside it"), because a measurement alone
   is unverifiable in a painting. It is the ONLY key `compose-spread` reads for a prop, and it
   emits it as the TRUE SIZE line whenever the prop is in frame. `lint-universe` warns
   `PROP-NO-SCALE` when it is absent and `PROP-SCALE-NOT-EMITTED` when the size sits under any
   other key, which is worse: the prop looks compliant and reaches no prompt.
5. Write `reference/<id>/prompts.md`: a hero shot with the object cleanly framed and its full form
   visible, and a detail crop tight on the load-bearing feature. Each prompt passes
   `identity.register.anchor` FIRST, bakes `register.rejectedPoles` as negatives, states the
   invariant, and names the output path.
6. Run `abu validate <universe>`, commit, and report the stub state with `shoot-references` as the
   next step.

# Process Flowchart

Amber = irreducibly human. Blue = agent-executed or agent-proposed.

```mermaid
flowchart TD
    A[A story names a recurring object] --> B[Sweep canon for an object in this role]
    B --> C{Genuinely new?}
    C -->|No| D[Reuse the existing id, and stop]
    C -->|Yes| E{Discrete object, or recurring pattern?}
    E -->|Pattern| F[Route to add-motif]
    E -->|Object| G[Interview: form, scale, material, user, load-bearing detail]
    G --> H[Scaffold with add-entity prop]
    H --> I[Fill prose and invariants]
    I --> I2[Fill structured.scale.absolute: the size, pinned to things a render contains]
    I2 --> J[Write prompts.md: hero plus detail crop]
    J --> K[Validate and commit at stub]
    K --> L[Hand off to shoot-references]
    classDef human fill:#fde68a,stroke:#b45309,color:#111827;
    classDef agent fill:#bfdbfe,stroke:#1e40af,color:#111827;
    class A,C,E,G human;
    class B,D,F,H,I,I2,J,K,L agent;
```

# Done / Verification

`abu validate <universe>` is green. The entity exists with both sheet slots present and null,
non-empty invariants, prose, and a non-empty `structured.scale.absolute`, so `lint-universe`
reports neither `PROP-NO-SCALE` nor `PROP-SCALE-NOT-EMITTED`. `reference/<id>/prompts.md` holds exactly two blocks, each
naming its output path and leading with the register anchor. Nothing under `reference/<id>/` is a
generated image.

# Exceptions & Troubleshooting

- **A prop with no load-bearing detail will pass every render and still drift**, because nothing
  in the record says what would count as it being the wrong object.
- **A prop is what makes a rule bind when prose loses.** A house rule written into a setting's
  `dressing` rendered four different slippers across fourteen spreads and was beaten outright by
  a character's own signature-boots invariant, because both are just text in one prompt. It held
  the moment the slippers became a locked prop with art on disk, cast into each affected spread.
  A reference image outranks any number of words.
- **A prop that appears in two states needs both sheets.** When a beat shows an object in a state
  no locked sheet depicts, generate the state rather than letting the model derive it.
- **Two characters can share one canonical prop**, which is exactly what the sweep is for.
- **An object whose correctness is a NUMBER is a generator, not a prop.** A geometric mark, a
  grid, a set of favicons: those are `add-generator`, where they are computed rather than rolled.

# Automation Opportunities

**Already automated:** the entity scaffold, and schema validation.

**Irreducibly human:** the load-bearing detail, the ownership rule, the size itself, and the reuse
call.

**Built, v0.49** (it was this map's own strongest next candidate): the interview asks the size and
step 4a fills `structured.scale.absolute`, the way `add-setting` forces `contract.scale` and
`add-character` forces `structured.scale`. The machinery and the grading both already existed; only
the authoring prompt was missing, so nothing ever put the question in front of an author, and a
supercharged laptop ranged from a notebook to a small television across one book.

**Strongest next candidate:** a refusal rather than a warning. `PROP-NO-SCALE` is advisory, so a
prop with no size still locks and still renders, and a warning in a long lint run is a thing to
scroll past. The question worth settling is whether an entity whose size is never stated should be
refused by `assert-story` the way an unlocked reference is, which is a decision about how much
existing canon it would stop rather than about how to implement it.

# Related

- [casting-sweep](../casting-sweep/SKILL.md): the reuse gate step 1 runs.
- [shoot-references](../shoot-references/SKILL.md): the art step this hands off to.
- [add-generator](../add-generator/SKILL.md): for an object whose correctness is computable.

# Revision History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-09-14 | Written from the skill file, read rather than recalled. |
