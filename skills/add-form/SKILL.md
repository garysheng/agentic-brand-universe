---
name: add-form
description: Add ONE form to the framework, and one work made in it (SPEC §4.8/§4.9) — the typed contract for a KIND of work, plus the specific one you are making. Use whenever you catch yourself building a NEW kind of artifact by hand: a scene, a card, a deck, a poster series, a title sequence, anything where the same shape will recur on another brand. Scaffolds forms/<id>/form.json (surface, requires-by-kind, slots, generators, computed + judged invariants, emits) and works/<id>/work.json (bind, slots, install). Also the correct fix when you find yourself inventing a new top-level folder with a "kind" field, adding a primitive to SPEC, or copying a working artifact to a second brand by editing its values. Authoring a form is rare; making a work in an existing one is `add-work`. Generic and universe-parameterized.
---

# Add Form

**Canon is the matter. A form is what shapes it. A work is canon given form.**

A **Form** (§4.8) is the contract for a kind of work; a **Work** (§4.9) is one made in it. Splitting
those two is the entire point: the form ships to a brand it has never seen, and the work is the only
thing you rewrite.

Authoring a form is RARE. Making a work in a form that already exists is the routine operation and
has its own verb: **`add-work`**. Come here only when nothing that ships fits.

## Read this first: you probably do not need a new primitive

The failure this skill exists to prevent, in the order it actually happens:

1. You build a new kind of artifact by hand, in a new folder, with a `"kind"` field.
2. Someone asks whether it conforms to the spec. It does not — it is a folder wearing the
   framework's clothes.
3. You promote it into SPEC as a **new primitive**, with a new engine class and new validation.
4. Someone asks *"isn't this just a form?"* and it is.

Step 3 is the expensive mistake, and it is the one that feels most like diligence. Before adding a
primitive, check whether what you think is novel is actually one of these:

| you think you have | it is already |
|---|---|
| "the ORDER of these assets is the content" | a **crossSlot invariant** (§4.8) |
| "these N things are generated the same way" | a **slot** with `repeat` |
| "it needs a style pack / a character / a setting" | `requires`, by KIND |
| "this particular one binds these ids" | a **Work** (§4.9) |
| "it produces these files" | `emits` |

A new primitive is warranted only when the thing cannot be expressed as *a contract with slots that
emits files*. That is a much higher bar than it feels like at 2am.

## Name the TREATMENT, not the medium

The most likely naming error, and it hides for a long time. If your form's `id` equals its
`surface.medium`, you have taken the name of a whole category for one specific way of working in it:

```jsonc
"id": "parallax-scene",
"surface": { "medium": "parallax-scene", ... }   // <- the tell
```

There are many kinds of parallax scene — mouse-driven, horizontal, dolly, fixed-camera — and a
contract that hardcodes vertical scroll, edge-pinned bands and sink-behind occlusion is ONE of them.
Owning the category's name leaves every sibling with nowhere to live, and the error is invisible
until someone asks "what about the other kind?"

Name what the contract actually commits to: `scrolling-diorama`, not `parallax-scene`;
`read-aloud-storybook`, not `picture-book`. Then check the id against `surface.medium` before you
ship. They should never match.

**Three levels, and only two are primitives.** The MEDIUM (the surface projected onto) is a string
in `surface`, not a first-class thing. Leave it that way until a SECOND contract targets the same
medium and the two need to agree on something — that is when a level earns its existence. Promoting
it earlier is the same mistake as adding a primitive: inventing a layer for imagined siblings.

**Subtypes are `extends`, not a new level.** A sibling treatment forks with
`"extends": "<id>@<version>"`. If a shared base belongs underneath several of them, EXTRACT it once
two exist. A base extracted from one example is a guess about what the second one will need.

## Inputs

- **The kind of deliverable**, in a sentence. "A scene separated into depth planes that move as the
  page scrolls."
- **The universe** — a path, for the work.
- **What it needs from a brand**, as KINDS: style-pack, character, setting. Never ids.
- **The one you are making now** — the work is not optional. A form with no work has
  never been tested against reality and is a guess.

## The rules that carry the weight

**`requires` names kinds; the work binds ids.** This is the whole mechanism. The moment a
projection names `warm-oil-curdles-cold` instead of `style-pack`, it is welded to one universe and
it has stopped being distributable. The engine rejects this.

**Every computed invariant needs a machine-evaluable `rule`, not just an id.** A generic engine
cannot run a check it knows only by NAME. Express the check as data:

```jsonc
{ "id": "depth-order", "check": "computed",
  "assert": "speed increases strictly with z, or the illusion inverts",
  "rule": { "op": "monotonic", "over": "plane", "by": "z", "field": "speed",
            "direction": "increasing", "strict": true } }
```

Three ops cover the cases so far, and each is about a RELATIONSHIP between slot entries, which is
exactly what a crossSlot invariant is:

- `monotonic` — a field is ordered by another field (`by`, `field`, `direction`, `strict`)
- `count` — how many entries match a predicate (`where`, `max`, `min`)
- `extreme` — a matching entry sits at an end (`where`, `by`, `at`)

An invariant marked `computed` with no `rule` is reported as a problem, not silently passed. If your
check needs an op that does not exist, add the op to the evaluator — do not downgrade it to
`judged` to make the warning go away.

**Judged vs computed is about the CHECK, not about difficulty.** Mark it `judged` when a human or a
model has to look. Mark it `computed` when arithmetic settles it. Be honest in the other direction
too: if a form's own flagship work legitimately violates a rule you were about to compute, that rule is
judged with a stated exemption. A computed rule your flagship work fails is a lie with a green
checkmark.

**Write the invariants from failures you have actually shipped, not from principles.** A form
whose rules were written before anything was built is a wish list. Every rule worth having came from
a screenshot. When one turns out to be wrong, DELETE it — a stale rule is worse than no rule,
because the next brand follows it and re-ships the bug it warns about.

**Surface geometry is a range, not the count your first work happened to use.** `"planes": 3`
because today's scene has three is a number that will be wrong next week.

## Steps

1. **Check the table above.** If a form already fits, stop — you want `add-work`, not this.
2. **Write `forms/<id>/form.json`** — `id`, semantic `version`, `author`, `surface`,
   `requires` (by kind), `slots`, `generators` (capability, not provider), `invariants`, `emits`.
3. **Write `works/<id>/work.json`** in the universe — `form: "<id>@<version>"` pinned,
   `bind`, `slots`, `install`.
4. **Validate.** The engine resolves the pinned version, checks that every filled slot is declared,
   that every required kind is bound, and runs the computed rules.
5. **Break it on purpose.** Invert the ordering, bind nothing, fill an undeclared slot. A rule you
   have not seen fail is a rule you do not know is wired up.
6. **Emit the proof** the form declares, composited with the SAME placement the artifact ships
   with — otherwise the proof is a pretty picture made separately, not evidence about what shipped.

## When the artifact has a placement contract

A form normally stops at the artifact. When its output is only correct *in* something else —
a page, a print jig, a feed — add a `placement` block and put the rules there. They are part of the
contract; a consumer that renders the files correctly and places them wrongly has not conformed.

Keep placement rules honest against the implementation. This is where staleness is most dangerous,
because placement rules read like principles and get copied without testing.

## Anti-patterns

- **A form with no work.** Untested guess.
- **`requires` naming an id.** Not distributable; the engine rejects it.
- **A computed invariant with no rule.** Documentation cosplaying as enforcement.
- **Duplicating the work's values into the consumer** (a component, a template). They disagree
  within one round of edits, and the moment they do, the validated invariant is validating a copy
  nobody renders. Read the work.
- **Adding a SPEC primitive.** Nearly always the wrong layer. See the table.
