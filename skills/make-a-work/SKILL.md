---
name: make-a-work
description: Make ONE work in a form a universe already declares — a flyer, a card, a poster, a scene, whatever forms/ holds. THE GENERIC FRONT DOOR: the form supplies the method, this supplies the door, so adding a new KIND of work means adding a folder rather than writing a new skill. Use when someone says "make a flyer", "make a card for X", "make one of those", "what can this universe make", or names any form. Also the correct destination whenever you are about to write a one-off skill for a new kind of artifact. NOT for picture books (abu:make-a-book owns that chain) and NOT for a single on-brand image with no form (abu:on-brand-image).
---

# Make a work

One work, in a form the universe already declares.

**The rule this skill exists to enforce: a new KIND of work is a FOLDER, not a skill.**
If making a flyer needs a `make-a-flyer` skill, and a card needs a `make-a-card` skill,
the framework has moved the hand-rolling up one level instead of removing it. Forms are
data. This is the one door.

## What a form is

A folder at `<universe>/forms/<id>/`:

| | |
|---|---|
| `FORM.md` | **required.** What the form is, its golden works, its status, its evals. |
| `PROMPT.md` | **required.** The method. **This IS the form's composer.** |
| `evals/` | optional. Scripts the method calls at the points it names. |

Both files are required. A folder without `PROMPT.md` is a note about a form, not a form:
nothing can be made from it.

> `forms/<id>/form.json` in the SPEC §4.8 slot encoding was RETIRED in v0.17. A folder
> holding only that is reported as retired, never offered as usable.

## Procedure

1. **Discover, do not guess.** With no form named, or when the operator asks what is
   possible:

   ```bash
   python3 scripts/forms.py list <universe>
   ```

   Show the usable forms in plain language. Never invent a form that is not there, and
   never quietly pick one when several fit: ask.

2. **Resolve, and let it refuse.**

   ```bash
   python3 scripts/forms.py resolve <universe> <form-id>
   ```

   It exits on an unknown or unusable form. Do not work around that by reading the folder
   yourself; an unusable form means the method is missing, and improvising one is how a
   form silently becomes whatever the last agent felt like.

3. **Read `FORM.md` FIRST, and surface its status to the operator.** Most forms here are
   derived from one work. That is a hypothesis, not a standard, and an agent that reads
   only the method will follow it with unearned confidence. If the form says the next work
   is expected to correct it, say so out loud before starting.

4. **Read `PROMPT.md` and follow it exactly.** It is the composer. It owns the gates, the
   order, and the refusals. Where it names an eval, run that eval at that point — not at
   the end, not when convenient.

   If the method fumbles, or you find yourself working around it, that is a defect in the
   FORM, not in this work. Fix the form. This is `fix-the-generator` applied to forms.

5. **File the work where the universe says.** `universe.json` may declare `workRoot`;
   undeclared means the default, `works/<id>/`. The convention:

   ```
   works/<YYYY-MM-DD>-<slug>/
     work.json          id == the folder name, timestamp included
     <artifact>         blessed: a STABLE name, so consumers never break on a re-roll
     <artifact>.recipe.json
     candidates/        every attempt, timestamped, NEVER deleted
   ```

   A render is not reproducible, so an un-blessed candidate is the only record that
   attempt existed. Keep all of them.

6. **`status` starts at `candidate`.** Only the requester moves it to `blessed`. Looking
   at the thing is the gate, and you are not the one who gets to pass it.

## Adding a NEW kind of work

Do not write a skill. Make a folder:

```
<universe>/forms/<new-id>/
  FORM.md      what it is; its golden(s); a STATUS section saying how much evidence it rests on
  PROMPT.md    the method, step by step, with the gates named
  evals/       whatever the method calls
```

Write it from a work you have ACTUALLY MADE, and say in `FORM.md` how many. A form
written before anything exists in it is the failure this framework spent a day removing:
the retired composer had 896 lines, 91 tests and zero works.

## Gates honored

Words before art. The form's own gates, whatever they are. Candidates are never deleted.
Only the requester blesses. An unusable form refuses rather than improvising.

## Not this skill

- A picture book → `abu:make-a-book`, which owns that chain.
- One on-brand image with no form → `abu:on-brand-image`.
- Authoring a new form → make the folder (above). There is no scaffolder yet, and until a
  form exists in more than one universe there is nothing proven to scaffold.
