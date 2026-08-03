---
name: create-form
description: Author a NEW form (a new KIND of work) for an Agentic Brand Universe, extracted from works ACTUALLY MADE, never speculated. Scaffolds forms/<id>/ (FORM.md + PROMPT.md + optional evals/) via a scaffolder that REFUSES on zero evidence, then guides the distillation (FORM.md states the evidence base, PROMPT.md is the method with gates and scripts named at the step that uses them, evals verified against the goldens they claim to reproduce) and the backfill (each evidence work gains a work.json declaration with a retrofit note; no historical record is ever rewritten). Built on three precedents: fashion-look (a newborn form), living-diorama (a growing one), and the book chain (compose-spec, compose-spread, judge-slot, book-doctor, update-book), which is the CHIEF precedent: a form at full maturity, and the trajectory every form grows along. Use when someone says "create a form", "author a new form", "extract a form from these works", "this kind of work keeps recurring", or when make-a-work has no form for a kind of work that already exists as finished pieces. NOT for making a work in an existing form (abu:make-a-work) and NOT for rendering a book (abu:make-a-book owns that chain today).
---

# Create Form

Author a new **form**: the folder at `<universe>/forms/<id>/` that teaches `make-a-work`
how to make a new KIND of work. The form is still a folder, exactly as `make-a-work`
says. What this skill owns is the METHOD of authoring that folder, extracted from what
proven forms actually do, not from speculation about forms in general.

## The three precedents, smallest to largest

- **`fashion-look`** (christofuturism, extracted 2026-08-01): a newborn form. One work,
  FORM.md + PROMPT.md, a loud STATUS hypothesis warning.
- **`living-diorama`** (gary-sheng-art, extracted 2026-08-03): a growing form. Three
  works before the form existed, a measuring eval verified against the goldens, a
  measured-returns contract, named debts.
- **The book chain** (`compose-spec`, `compose-spread`, `judge-slot`, `book-doctor`,
  `update-book`): **the chief precedent.** The picture book is the oldest and most
  complex kind of work in the framework, and it is a form in everything but
  declaration: it has a composer, a step-by-step method with gates, per-slot judging
  against goldens, a grader of the finished work, and update verbs. It stands outside
  `forms/` for historical reasons, not because books are a different category. It is
  the limit case the form model is converging toward, and the living proof of what
  each rung of maturity looks like.

## The maturity trajectory (what to build, and when)

A form is not authored at full size. It grows along a trajectory the book chain has
already walked end to end, and an author's job is to know which rung the form is on
and build exactly that rung, not to invent structure ad hoc.

| Rung | What the form has | The book chain's living proof |
|---|---|---|
| **Newborn** | `FORM.md` + `PROMPT.md`, maybe one eval. The method is prose an agent follows; the STATUS section says how thin the evidence is. | The early books: a method in prose (`make-a-nof-book`'s ancestors) before any of it was code. |
| **Growing** | Measuring evals verified against goldens; per-slot judging of generated pieces against locked goldens, blind, itemized, failing closed. | `judge-slot`: PASS or DEFECT per declared invariant, judge never sees the plan, against the golden never slot-to-slot. |
| **Mature** | A deterministic composer that assembles each piece from canon; a doctor that grades the FINISHED work against what it declares, with an exit code; update verbs that edit an existing work without rebuilding it. | `compose-spec` + `compose-spread` (the composer and its atomic unit), `book-doctor` (the grader), `update-book` insert/recast (the update verbs). |

Two rules about climbing:

- **A rung is earned by works, not by ambition.** The retired universal composer built
  the mature rung first, from zero works, and died of it (896 lines, 91 tests, zero
  works; SPEC §4.8). The book chain built each rung only after dozens of books had
  walked the previous one by hand.
- **When a PROMPT.md step has been executed identically across several works, that
  step is asking to become code** (a composer substep, an eval, a doctor check). Route
  it through `pave-the-path` / `evolve-abu` rather than growing a bespoke script
  beside one work.

## The evidence rule (this is a GATE, not advice)

**A form is written FROM works actually made.** Every rule in a form must be traceable
to something that happened while making a real piece, and `FORM.md` must state how many
works the form rests on and where they are.

- **Zero works REFUSES.** The scaffolder exits rather than stamping a folder. This is
  the cautionary tale kept by name: the retired universal composer had **896 lines, 91
  tests and zero works** (SPEC §4.8, retired v0.17). If the work does not exist yet,
  make it first, by hand, through the ordinary tools (`on-brand-image`,
  `shoot-references`, whatever the piece needs). Then come back and extract.
- **ONE work is the legal minimum**, and it is a hypothesis, not a standard. Both
  `fashion-look` and `event-flyer` were legally authored from one work each, and both
  carry a loud STATUS warning saying so. The scaffolder stamps that warning
  automatically whenever the evidence base is below three.
- **THREE works is the comfortable base** (the `living-diorama` precedent: three
  finished, blessed works existed before the form did). At three or more the STATUS
  section drops the hypothesis framing and states the records-win rule instead: the
  works' own READMEs, recipes and raw folders remain the ground truth, and where the
  form and a shipped work's records disagree, the records win.

## What the folder holds

```
<universe>/forms/<id>/
  FORM.md      what it is; its goldens; a STATUS section stating the evidence base
  PROMPT.md    the method, step by step, gates named, scripts named at the step that uses them
  evals/       optional; the measuring and judging instruments the method calls
```

Both files are required. `make-a-work/scripts/forms.py` discovers the form, surfaces
its STATUS warning up front, and refuses a folder missing either file.

## Procedure

1. **Gather the evidence.** Locate every finished work of this kind, on disk, with its
   own records (README, recipes, candidates/raw folders). These are the ground truth
   the form will be distilled from. If there are none, stop here and make one.

2. **Scaffold.** The scaffolder validates the id, refuses on zero evidence, refuses to
   clobber an existing form, and stamps the skeleton with the evidence base already
   counted and listed:

   ```bash
   python3 <abu>/skills/create-form/scripts/scaffold.py <universe> <form-id> \
     --work <path-to-finished-work-dir> [--work ...] \
     [--name "<Display Name>"] [--what "<one line: what the form is>"] [--evals]
   ```

   It also checks each evidence work for a `work.json` declaring this form, and prints
   backfill guidance for any that lack one (step 6).

3. **Distill `FORM.md` from the works, not from memory.** Fill the stamped skeleton:

   - **What it is**, in one paragraph a stranger could act on.
   - **Family laws / what a good one looks like**: the gate criteria a candidate is
     judged against. Write them as testable claims, each earned by a real work
     (`living-diorama` cites the golden that earned each law). These are the form's
     equivalent of an entity's declared invariants, and they should be written so a
     blind judge could check them one at a time (see step 5).
   - **Where the work goes.** The `make-a-work` default is `works/<id>/`. A form may
     override it, but only with a stated reason: `fashion-look` files entity-scoped
     because a look is a fact about a character; `living-diorama` files register-scoped
     because plates are components of one work. Say which and why.
   - **Goldens**: every evidence work, by path, with one line on what each established.
   - **Known debts, named, not hidden** (`living-diorama` precedent): anything the
     method still hand-rolls goes in a debts section and gets flagged to `evolve-abu`,
     never silently worked around.

4. **Write `PROMPT.md` as the method, step by step** (the `fashion-look` precedent,
   which is itself the prose ancestor of what `compose-spread` is in code):

   - Numbered steps in the order the work is actually made. Words before art: concept
     and copy are written down before any render, so a render can be judged against
     them (the book chain's manuscript-before-spreads law, applied to any form).
   - **Gates named at the step where they run**, not collected at the end. Every render
     goes through the provider adapter (`on-brand-image/scripts/generate.py`, which
     writes the `.recipe.json`); verification uses `render-readback/scripts/`
     (`verify_render.py`, `contact_sheet.py`, `crop_zoom.py`) before any defect is
     called.
   - **Scripts named inline at the step that uses them.** This is the CLAUDE.md
     discoverability rule applied to forms: a script named only in a reference table
     loses to whatever is in front of the agent by hour six.
   - Candidates are never deleted. The requester blesses; the method does not.
   - Every step should exist because a work needed it. `fashion-look` opens with
     "every step below is here because skipping it produced a wrong render", and that
     is the standard.

5. **Evals, when the method measures or judges anything.** The book chain's gate
   mechanics are the most battle-tested in the repo, and a form's evals follow them.
   Two kinds:

   - **Computed evals** measure numbers deterministically. **A computed eval must be
     verified against the goldens it claims to reproduce before the form lands**:
     `living-diorama`'s `measure_embers.py` was trusted only after it reproduced
     a-city-on-a-hill's recorded measurements (the lantern ember at (41.48%, 74.01%),
     the cluster counts, the 65% ceiling). An eval that has never reproduced a known
     number is a hope, not an instrument.
   - **Judged evals** follow the `judge-slot` protocol, which is a role, not a
     script: the judge gets the golden, the candidate, and the family laws as an
     itemized checklist, and NOTHING else. The judge never sees the plan; verdicts
     are per criterion, never gestalt; comparison is against the golden, never
     candidate-to-candidate (consistency is not fidelity). **Fail closed**: an
     unanswered judgement is UNJUDGED, which is a failure, not a pass
     (`event-flyer`'s `thumbnail.py` end eval fails closed exactly this way).

6. **Backfill the declarations.** When a form is extracted from existing works, each
   evidence work gains a `work.json` declaring the form:

   - `"form": "<form-id>"`, `"status"`, and a `formNote` stating the retrofit
     explicitly: the declaration was added on the day the form was extracted, the work
     predates the form, and it is one of the form's goldens (the `a-city-on-a-hill`
     wording is the model).
   - **NO historical README, recipe, or attestation is ever rewritten.** The works'
     records are what the form was distilled FROM; altering them to match the form
     inverts the evidence. Change live instructions, leave every attestation alone.

7. **Prove discovery.** Run both, and read what they print:

   ```bash
   python3 <abu>/skills/make-a-work/scripts/forms.py list <universe>
   python3 <abu>/skills/make-a-work/scripts/forms.py resolve <universe> <form-id>
   ```

   The form must show as usable and its STATUS line must surface. A form that resolves
   but whose status does not surface has a malformed STATUS heading; fix it now, since
   that warning is what keeps the next agent's confidence honest.

8. **The next work is the experiment.** Hand the form to `make-a-work` and make one.
   Whatever the method fumbles is a defect in the FORM, not in the work: fix the form
   (`fix-the-generator` applied to forms, exactly as `make-a-work` step 4 says). And
   when the same fix lands twice, look up the trajectory table: the form may be ready
   to climb a rung.

## Definition of done

- `forms/<id>/FORM.md` + `PROMPT.md` exist; `forms.py resolve` reports usable and
  surfaces the STATUS line.
- STATUS states the evidence count and lists the works; below three it carries the
  hypothesis warning.
- Every computed eval has reproduced a recorded golden measurement; every judged eval
  follows the blind, itemized, fail-closed protocol.
- Every evidence work carries its `work.json` declaration with a retrofit note, and
  `git diff` shows no historical README/recipe/attestation was touched.
- Any remaining hand-rolls are in the debts section AND flagged to `evolve-abu`.

## Not this skill

- Making a work in an existing form: `abu:make-a-work`, the one door.
- A picture book: `abu:make-a-book` owns that chain today. Books stand outside
  `forms/` for historical reasons, not category ones; the book chain is the limit
  case this form model is converging toward, and migrating it into `forms/` is a
  large architectural move with many dependents, filed as an open question on the
  `evolve-abu` shelf rather than attempted ad hoc.
- Promoting a form's method into the framework or the SPEC (a form proven portable
  across universes, a debt that recurs, a form ready to climb a maturity rung into
  code): `abu:evolve-abu`.
