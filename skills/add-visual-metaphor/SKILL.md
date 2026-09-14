---
name: add-visual-metaphor
description: Add ONE visual metaphor (a spine-object a whole property argues through, not merely a location) to an Agentic Brand Universe (interview the object and the states it argues across, reuse-first via casting sweep, then scaffold a typed `visual-metaphor` entity with SPEC §12's setting-style contract: a locked master plus per-state plates, and map/blocking/dressing descriptor prose). Stays `status: unlocked` (correctly refused by the render gate) until `shoot-references` fills the plates and you lock it. Art is NOT generated here. Use when a story is built by zooming into one recurring object across changing states. Generic and universe-parameterized: pass the target universe.
---

# Add Visual Metaphor

One spine-object, into a universe's canon, as a typed record with its contract scaffolded. This is authoring, not art: it ends with a validated `unlocked` entity + ready-to-run prompts. `shoot-references` generates and locks the plates afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- The object, and the property it is the spine of.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new visual metaphor, sweep `canon/entities/` + any CANON.md for an existing object already carrying this argument. Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what the contract needs.
   - **The object itself.** What it is, its material, and why it (not any other object) can carry the whole property's argument.
   - **HOW BIG IT IS, IN HUMAN TERMS. Ask this explicitly and never skip it.** How tall, how wide, how big beside a person or a hand or a doorway, and how many people fit if it is enterable. An object that never states its size gets whatever size the model guesses, and every render inherits that guess forever. Same rule and same reason as `add-setting`, which is not a coincidence: a visual-metaphor carries a setting-style contract, `universe-doctor` grades both on the SAME `setting_size` dimension, and until v0.49 this was the one of the two whose authoring skill never asked.
   - **Its argued states.** A visual metaphor is not static: it is the SAME object shown across the states the story's argument turns on (e.g. locked/opening/broken, empty/full, whole/fractured). Name each state explicitly; each becomes a plate.
   - **Why it's a metaphor, not scenery.** Confirm the object is genuinely load-bearing for the argument (every page depends on it), which is why it carries a setting-style contract even though it usually is not a place.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> visual-metaphor <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `status: "unlocked"` and a `contract` whose fields (`turnaround`, `emptyPlates`, `blueprint`, `scalePlate`, `blockingPlate`, `map`, `blocking`, `dressing`, `scale`) are all null/empty, plus `states` (the ordered plate list: blueprint, master, then each argued state) and `emptyPlatesExpected`. It prints `lock_level: stub`. This list used to omit `scalePlate` and `scale`, which is part of why nobody filled them.
4. **Fill the descriptor prose.** Edit `contract.map` (what the object's form/parts mean), `contract.blocking` (how it sits/reads in a frame across states), and `contract.dressing` (its material, finish, and palette). These three are load-bearing text: the resolver requires them non-empty, and every render passes them in the prompt. Also fill `prose.rules` for any never-render constraint (an argued state that must never be shown, a detail that must always be visible).

4a. **State the size, and plan a plate that proves it (SPEC §12, v0.49).** Fill `contract.scale` with the answer from step 2, as plain measurements a person can picture and PINNED to something a render already contains: "about the height of a doorway and twice a person's shoulders across; a hand covers a third of its face." Prose is the half that matters most, because prose survives a re-render and a plate does not, and `contract.scale` is passed in every prompt like `dressing`.

   Then declare `contract.scalePlate`: the same object with **ANONYMOUS SCALE FIGURES**, a person or two small in frame, at a distance, turned away or in profile, faces not readable, plain clothing, **never a canon character**. It is a separate file from the state plates, never a replacement, and it is what a human and `lint-universe` read the object's size from.

   - **`lint-universe` warns `SETTING-NO-SCALE-PLATE` / `SETTING-NO-SCALE-DESCRIPTOR`** on a visual-metaphor as of v0.49, the same codes it has always used for a setting, because `universe-doctor` has scored both on one dimension since v0.9. Both are advisory: an object with no scale plate still locks and still renders.
   - **A REASONED DECLINE IS NOT A GAP.** If this object's own invariants forbid a figure in every plate, write `contract.scalePlateWaiver` saying why. Declining the plate is allowed; declining to state the size at all is not.
   - **Where the states make size ambiguous, say so in `contract.scale` once** rather than per state. An object argued across open/shut/broken is the SAME object at the same size in all three, and that sentence is what keeps it so.
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: a **locked master** (the object's default/neutral state, mapped to `contract.turnaround`) plus one **state plate** per argued state from step 2 (mapped into `contract.emptyPlates`), a **`scalePlate`** from step 4a, and a `blueprint` if the object's internal structure matters. Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) states which argued state this plate depicts and what must stay invariant across all of them (so the object reads as the same object throughout); (c) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
6. **Validate + commit.** `abu validate <universe>` stays green (an `unlocked` visual-metaphor still validates: that is correct, not an error). Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the entity stays refused by `assert-story`/`assert-spread` until `shoot-references` fills every plate and flips `status` to `"locked"`.

## Gates honored
- **Reuse-first** (step 1): never invent a second spine-object an existing entity already carries.
- **It must be able to prove its own size** (step 4a): `contract.scale` in words and a `scalePlate` with anonymous figures, or a written `scalePlateWaiver` saying why the plate is impossible. The same discipline `add-setting` enforces, on the dimension `universe-doctor` already grades this kind on.
- **Unlocked-until-plated**: a `null` contract field (or a missing descriptor) is a hard refusal, same discipline as a setting. Never hand-edit `status` to `"locked"` without the real plates; the refusal is the feature.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the plates and flipping `status` to `locked` → `shoot-references`.
- A character, setting, motif, prop, story, or relation → the sibling `add-*` skills.
