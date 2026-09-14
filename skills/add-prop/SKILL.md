---
name: add-prop
description: Add ONE prop (a discrete physical object a character holds, wears, or uses, that must render identically wherever it appears) to an Agentic Brand Universe (interview what it is and its load-bearing detail, reuse-first via casting sweep, then scaffold a typed `prop` entity with SPEC §12's hero + detail reference slots and ready-to-run generation prompts). Art is NOT generated here (that is `shoot-references`). Use when a specific object needs to stay consistent across many renders. Generic and universe-parameterized: pass the target universe.
---

# Add Prop

One physical object, into a universe's canon, as a typed record with its reference slots scaffolded. This is authoring, not art: it ends with a validated `stub` entity + ready-to-run prompts. `shoot-references` generates and locks the shots afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- What the object is and which character(s) use it.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new prop, sweep `canon/entities/` + any CANON.md for an existing object that already covers this role (two characters can share one canonical prop). Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what the reference matrix needs.
   - **What it is.** The object's form, material, and who holds/wears/uses it and how.
   - **HOW BIG IT IS, IN HUMAN TERMS. Ask this explicitly and never skip it.** Not "a laptop": how wide, how tall, how big beside the hand that holds it or the desk it sits on. A prop that never states its size gets whatever size the model guesses, and every render inherits a different guess. This is the same rule `add-setting` applies to a room and `add-character` to a person, and a prop needs it more, because the reader already knows roughly how big a room and a person are.
   - **Its load-bearing detail.** The one specific feature that must never drift (an engraving, a wear mark, a color, a proportion). This is what the `detail` crop locks down; without it the prop reads as "a similar object," not "the same object."
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> prop <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `structured.sheets: {"hero": null, "detail": null}` and `requiredForRender: []`. It prints `lock_level: stub`.
4. **Fill the prose + invariants.** Edit `prose` (voice/lore/rules: what the object means, who is allowed to touch it) and `structured.invariants` (the load-bearing rules the read-back will check, e.g. the exact detail from step 2).
4a. **State the size (SPEC §12, v0.49).** Fill `structured.scale.absolute` with the answer from step 2, as one plain sentence:

   ```json
   "scale": {
     "absolute": "a 14-inch notebook, 33cm wide, its open screen about twice the height of a mug beside it and about a quarter of the desk width",
     "relativeTo": {"other-entity-id": "about half the height of"}
   }
   ```

   `compose-spread` emits `absolute` as the TRUE SIZE line whenever this prop is in frame, alone or not, and it is the ONLY key it reads for a prop. `lint-universe` warns `PROP-NO-SCALE` when it is absent and `PROP-SCALE-NOT-EMITTED` when a size sits under any other key, which is the worse state: the prop looks compliant and contributes nothing to any prompt.

   - **PIN THE SIZE TO THINGS A RENDER ALREADY CONTAINS.** "33cm wide" is unverifiable in a painting and "about twice the height of the mug beside it" is checkable at read-back by looking. Write the ratio, then the measurement.
   - **The incident.** On `what-a-book-is-made-of` the supercharged laptop appears in most of twenty-one spreads and ranged from a notebook to a small television. The entity declared its FORM, its COLOUR and its rules and never once declared its SIZE. Colour was meaning; scale was a guess, and Gary caught it by eye: "why does the laptop look different sizes?" This is the prop version of the hearth room that earned the setting rule in v0.9.
   - **A code-drawn scale plate is the cheapest way to get the ratios right.** Model the object beside a desk, a mug and a spread hand in a `massing` spec (`add-generator`) and render it: deterministic, free, and it gives you a reference image to pass as well as the numbers to write down.

5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: a **hero** shot (the object cleanly framed, its full form visible) and a **detail** crop (a tight close-up on the load-bearing feature). Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) states the invariant that must never drift; (c) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
6. **Validate + commit.** `abu validate <universe>` stays green. Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the next step is `shoot-references <universe> <id>`.

## Gates honored
- **Reuse-first** (step 1): never invent a second prop an existing entity already covers.
- **A prop must be able to prove its own size** (step 4a): `structured.scale.absolute` is filled, so the TRUE SIZE line reaches every prompt this prop appears in. The same discipline `add-setting` enforces with `contract.scale` and `add-character` with `structured.scale`.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the shots → `shoot-references`.
- A character, setting, visual-metaphor, story, or relation → the sibling `add-*` skills. A recurring visual pattern not tied to a single discrete object (a gesture, a light quality) is `add-motif`.
