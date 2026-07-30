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
   - **The object itself.** What it is, its material, its scale, and why it (not any other object) can carry the whole property's argument.
   - **Its argued states.** A visual metaphor is not static: it is the SAME object shown across the states the story's argument turns on (e.g. locked/opening/broken, empty/full, whole/fractured). Name each state explicitly; each becomes a plate.
   - **Why it's a metaphor, not scenery.** Confirm the object is genuinely load-bearing for the argument (every page depends on it), which is why it carries a setting-style contract even though it usually is not a place.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> visual-metaphor <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `status: "unlocked"` and a `contract` whose fields (`turnaround`, `emptyPlates`, `blueprint`, `map`, `blocking`, `dressing`) are all null/empty. It prints `lock_level: stub`.
4. **Fill the descriptor prose.** Edit `contract.map` (what the object's form/parts mean), `contract.blocking` (how it sits/reads in a frame across states), and `contract.dressing` (its material, finish, and palette). These three are load-bearing text: the resolver requires them non-empty, and every render passes them in the prompt. Also fill `prose.rules` for any never-render constraint (an argued state that must never be shown, a detail that must always be visible).
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: a **locked master** (the object's default/neutral state, mapped to `contract.turnaround`) plus one **state plate** per argued state from step 2 (mapped into `contract.emptyPlates`), and a `blueprint` if the object's internal structure matters. Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) states which argued state this plate depicts and what must stay invariant across all of them (so the object reads as the same object throughout); (c) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
6. **Validate + commit.** `abu validate <universe>` stays green (an `unlocked` visual-metaphor still validates: that is correct, not an error). Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the entity stays refused by `assert-story`/`assert-spread` until `shoot-references` fills every plate and flips `status` to `"locked"`.

## Gates honored
- **Reuse-first** (step 1): never invent a second spine-object an existing entity already carries.
- **Unlocked-until-plated**: a `null` contract field (or a missing descriptor) is a hard refusal, same discipline as a setting. Never hand-edit `status` to `"locked"` without the real plates; the refusal is the feature.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the plates and flipping `status` to `locked` → `shoot-references`.
- A character, setting, motif, prop, story, or relation → the sibling `add-*` skills.
