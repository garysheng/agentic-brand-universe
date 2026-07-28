---
name: add-work
description: Make ONE work in a form that already exists (SPEC §4.9) — bind a brand's ids to the form's required kinds, fill its slots, generate the assets, validate against the contract, and install the outputs. Use whenever a form already exists for the kind of thing you want: a storybook, a parallax scene, a card, a deck. The routine verb — authoring a NEW form is `add-form` and is rare. Also the correct fix when you catch yourself copying a working work from another brand and editing its values, hand-writing a scene.json by hand, or reaching for `add-form` when the form you need already ships. Generic and universe-parameterized.
---

# Add Work

**Canon is the matter. A form is what shapes it. A work is canon given form.**

A form ships to a brand it has never seen. This is the verb that consumes one, and it is the common
operation: forms are authored once and worked in many times.

Authoring a new form is **`add-form`**, and you should read its "you probably do not need a new
primitive" table before going there.

## The whole idea in one line

The form says *"I need at least one style-pack."* The work says *"the style-pack is
`christofuturist-illuminated`."* Kinds on one side, ids on the other. That indirection is the only
reason the contract is portable, and honouring it is most of this skill.

## Inputs

- **The form**, pinned: `<id>@<version>`. Unpinned is a problem — a form is a versioned
  artifact and "whatever is on disk" is not a dependency.
- **The universe** — the work lands at `<universe>/works/<id>/`.
- **What this particular one is.** The work is where all the specificity — and all the AUTHORSHIP — lives. `beats`, `spine`, a scene's composition: facts present in neither the canon nor the form.

## Steps

1. **Read the form first, all of it.** `requires`, `slots` (and `schemaNotes` — that is where
   the reasons live), `invariants`, `emits`, and `placement` if it has one. The schema notes are not
   documentation; they are the accumulated failures of everyone who worked in it before you.

2. **Bind every required kind to a real id in this universe.** If a required kind has no candidate,
   stop and create it with the proper verb (`add-character`, `create-style-pack`, …). Do not bind a
   near-miss to get past validation — a wrong binding fails later, in the render, where it is much
   more expensive to diagnose.

3. **Fill the slots.** Every field in the slot schema, for every entry. A field you leave off is a
   default someone else chose, and defaults are where a scene silently reverts to the shape the
   form's author happened to be building that day.

4. **Generate the assets** using the declared `generators`. Prefer a `deterministic` capability over
   an `image` one wherever the form offers both: a computed asset is reproducible, free, and
   correct by construction, and its keep-out regions are numbers instead of hopes.

5. **Validate.** The engine resolves the pinned version, checks every filled slot is declared, every
   required kind is bound, and runs the computed invariants. Zero problems, or you are not done.

6. **Then work the JUDGED invariants yourself**, one at a time, looking at the artifact. Validation
   passing means the arithmetic holds — it says nothing about whether the thing is any good, and the
   judged invariants are usually the ones that decide that.

7. **Emit the declared proof**, composited with the SAME placement the artifact ships with. A proof
   built separately from the shipping path is a pretty picture, not evidence.

8. **Install** via the work's `install` map, and have the consumer READ the work rather than
   retyping its values.

## The failure that costs the most

**Duplicating the work's values into whatever renders it.** A component with the planes, sizes
and speeds typed in beside a work that also declares them will disagree within one round of
edits — and the moment it does, every validated invariant is validating a copy that nobody renders.
The work is the source of truth. Import it.

## The second-most

**Copying a sibling work from another brand and editing the values.** It carries that brand's
bindings, its tuning, and its exemptions, and the fields you do not notice are exactly the ones that
were tuned for something you no longer have. Start from the form's slot schema.

## Tuning against one context only

If the form has a `placement` block, its outputs are only correct *in* something. Check the
work in every context that thing actually appears in — a scene tuned at one aspect ratio does
not survive the other, and the usual symptom is not a visual glitch but the SUBJECT going missing
while the atmosphere still looks fine.

## When the form is wrong

You will find rules that are stale, missing, or false — instancing is how that gets discovered,
because the form's author only ever saw one work. Fix it **in the form**, bump its
version, and say what the failure was. A fix applied only to your work is a fix the next brand
pays for again.

If a rule is false rather than incomplete, DELETE it. A stale rule is worse than a missing one: the
next person follows it and re-ships the bug it warns about.
