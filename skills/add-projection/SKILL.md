---
name: add-projection
description: Add ONE projection to the framework, and one instance of it in a universe (SPEC §4.8/§4.9) — the typed contract for a KIND of deliverable, plus the specific one you are making. Use whenever you catch yourself building a NEW kind of artifact by hand: a scene, a card, a deck, a poster series, a title sequence, anything where the same shape will recur on another brand. Scaffolds projections/<id>/projection.json (surface, requires-by-kind, slots, generators, computed + judged invariants, emits) and instances/<id>/instance.json (bind, slots, install). Also the correct fix when you find yourself inventing a new top-level folder with a "kind" field, adding a primitive to SPEC, or copying a working artifact to a second brand by editing its values. Generic and universe-parameterized.
---

# Add Projection

A **ProjectionType** is the contract for a kind of deliverable. A **ProjectionInstance** is one of
them. Splitting those two is the entire point: the type ships to a brand it has never seen, and the
instance is the only thing you rewrite.

## Read this first: you probably do not need a new primitive

The failure this skill exists to prevent, in the order it actually happens:

1. You build a new kind of artifact by hand, in a new folder, with a `"kind"` field.
2. Someone asks whether it conforms to the spec. It does not — it is a folder wearing the
   framework's clothes.
3. You promote it into SPEC as a **new primitive**, with a new engine class and new validation.
4. Someone asks *"isn't this just a projection?"* and it is.

Step 3 is the expensive mistake, and it is the one that feels most like diligence. Before adding a
primitive, check whether what you think is novel is actually one of these:

| you think you have | it is already |
|---|---|
| "the ORDER of these assets is the content" | a **crossSlot invariant** (§4.8) |
| "these N things are generated the same way" | a **slot** with `repeat` |
| "it needs a style pack / a character / a setting" | `requires`, by KIND |
| "this particular one binds these ids" | a **ProjectionInstance** (§4.9) |
| "it produces these files" | `emits` |

A new primitive is warranted only when the thing cannot be expressed as *a contract with slots that
emits files*. That is a much higher bar than it feels like at 2am.

## Inputs

- **The kind of deliverable**, in a sentence. "A scene separated into depth planes that move as the
  page scrolls."
- **The universe** — a path, for the instance.
- **What it needs from a brand**, as KINDS: style-pack, character, setting. Never ids.
- **The one you are making now** — the instance is not optional. A projection with no instance has
  never been tested against reality and is a guess.

## The rules that carry the weight

**`requires` names kinds; the instance binds ids.** This is the whole mechanism. The moment a
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
too: if your own instance legitimately violates a rule you were about to compute, that rule is
judged with a stated exemption. A computed rule your flagship instance fails is a lie with a green
checkmark.

**Write the invariants from failures you have actually shipped, not from principles.** A projection
whose rules were written before anything was built is a wish list. Every rule worth having came from
a screenshot. When one turns out to be wrong, DELETE it — a stale rule is worse than no rule,
because the next brand follows it and re-ships the bug it warns about.

**Surface geometry is a range, not the count your first instance happened to use.** `"planes": 3`
because today's scene has three is a number that will be wrong next week.

## Steps

1. **Check the table above.** If it is already a projection, stop and write the instance only.
2. **Write `projections/<id>/projection.json`** — `id`, semantic `version`, `author`, `surface`,
   `requires` (by kind), `slots`, `generators` (capability, not provider), `invariants`, `emits`.
3. **Write `instances/<id>/instance.json`** in the universe — `projection: "<id>@<version>"` pinned,
   `bind`, `slots`, `install`.
4. **Validate.** The engine resolves the pinned version, checks that every filled slot is declared,
   that every required kind is bound, and runs the computed rules.
5. **Break it on purpose.** Invert the ordering, bind nothing, fill an undeclared slot. A rule you
   have not seen fail is a rule you do not know is wired up.
6. **Emit the proof** the projection declares, composited with the SAME placement the artifact ships
   with — otherwise the proof is a pretty picture made separately, not evidence about what shipped.

## When the artifact has a placement contract

A projection normally stops at the artifact. When its output is only correct *in* something else —
a page, a print jig, a feed — add a `placement` block and put the rules there. They are part of the
contract; a consumer that renders the files correctly and places them wrongly has not conformed.

Keep placement rules honest against the implementation. This is where staleness is most dangerous,
because placement rules read like principles and get copied without testing.

## Anti-patterns

- **A projection with no instance.** Untested guess.
- **`requires` naming an id.** Not distributable; the engine rejects it.
- **A computed invariant with no rule.** Documentation cosplaying as enforcement.
- **Duplicating the instance's values into the consumer** (a component, a template). They disagree
  within one round of edits, and the moment they do, the validated invariant is validating a copy
  nobody renders. Read the instance.
- **Adding a SPEC primitive.** Nearly always the wrong layer. See the table.
