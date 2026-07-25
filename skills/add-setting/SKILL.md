---
name: add-setting
description: Add ONE setting (a location) to an Agentic Story universe (interview its fixed geometry, fixed camera angles, and dressing, reuse-first via casting sweep, then scaffold a typed `setting` entity with SPEC §12's contract slots (turnaround, per-angle empty plates, blueprint, plus map/blocking/dressing descriptor prose) and ready-to-run generation prompts). Stays `status: unlocked` (correctly refused by the render gate) until `lock-references` fills the plates and you lock it. Art is NOT generated here. Use when a story needs to render into a location. Generic and universe-parameterized: pass the target universe.
---

# Add Setting

One location, into a universe's canon, as a typed record with its contract scaffolded. This is authoring, not art: it ends with a validated `unlocked` entity + ready-to-run prompts. `lock-references` generates and locks the plates afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- What the place is and which story needs it.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new setting, sweep `canon/entities/` + any CANON.md for an existing location that already fits (a universe rarely needs two versions of "the kitchen"). Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what the contract needs.
   - **What the place is:** its function in the story, its mood, who owns or frequents it.
   - **Cameras.** Decide the FIXED vantage points a book will actually shoot from (typically C1 + C2: e.g. wide establishing, and one closer working angle). More cameras cost more locked plates; pick the minimum the story needs.
   - **FIXED geometry.** The walls, furniture positions, doors, and sightlines that must never drift render to render (this is what "locked" buys you: continuity).
   - **Dressing.** The props, materials, and colors that make the place recognizable at a glance.
   - **SIZE, IN HUMAN TERMS. Ask this explicitly and never skip it.** How wide is the room, how high is the ceiling, how big is the fireplace opening, how many people fit? A setting that never states its size gets whatever size the model guesses, and every render inherits that guess forever (see the scale gap below). Write the answer into `contract.scale` as plain measurements a person can picture: "a circular hall about 80 feet across, dome 45 feet at the crown, the fire opening about 12 feet wide."
   - **BUILDABILITY.** Ask how each major feature is actually held up or vented. A free-standing firepit under a conical flue suspended from a dome shipped through a whole book before anyone noticed nothing was holding the cone. Anything structural that a plate would not have to explain is exactly where the physics quietly fails.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> setting <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `status: "unlocked"` and a `contract` whose fields (`turnaround`, `emptyPlates`, `blueprint`, `scalePlate`, `map`, `blocking`, `dressing`, `scale`) are all null/empty. It prints `lock_level: stub`.
4. **Fill the descriptor prose.** Edit `contract.map` (the spatial layout in words), `contract.blocking` (where characters can stand/move without breaking geometry), `contract.dressing` (the recognizable materials/props/palette), and `contract.scale` (the size in human measurements, from the interview). These three are load-bearing text, not flavor: the resolver requires them non-empty, and every render of this setting passes them in the prompt. Also fill `prose.rules` for any never-render constraint.
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: one block per contract file slot, a `turnaround`, one `emptyPlate` per fixed camera (C1, C2, ...), a `blueprint` (top-down/schematic), and a **`scalePlate`** (see below). Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) restates the FIXED geometry from step 2 so every plate agrees with every other; (c) names the target output path `reference/<id>/<shot>.png`. These are what `lock-references` will run.
6. **Validate + commit.** `agenticstory validate <universe>` stays green (an `unlocked` setting still validates: that is a correct, expected state, not an error). Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the setting stays refused by `assert-story`/`assert-spread` until `lock-references` fills every plate and flips `status` to `"locked"`.

### An empty plate cannot prove its own size (SPEC v0.9)

`emptyPlates` are people-free on purpose, so a setting reference never bakes a character's face into a room. That rule is right and it stays. But it has a cost that went unpriced for months: **a figure-free interior carries no unit of comparison.** The model picks a size, every render inherits the guess, and nobody can catch it, because the plate does not depict the dimension being judged. A hearth room rendered small and cramped through an entire 25-spread book before its owner said "that room is supposed to be much bigger than that."

So every setting gets ONE extra plate whose only job is size:

- **`contract.scalePlate`** — the same room with **ANONYMOUS SCALE FIGURES**: a few people, small in frame, at a distance, turned away or in profile, faces not readable, plain clothing, **never a canon character and never the subject**. That satisfies the identity rule (no face is baked) while making size checkable at a glance.
- It is a **separate file from `emptyPlates`, never a replacement.** Renders still cast an empty plate; the scale plate is what a human and `lint-universe` read the room's size from.
- **`contract.scale`** carries the same fact in words, and is passed in every prompt like `dressing`, because **prose survives a re-render and a plate does not.**

`lint-universe` warns `SETTING-NO-SCALE-PLATE` / `SETTING-NO-SCALE-DESCRIPTOR`. Both are advisory: a setting with no scale plate still locks and still renders.

## Gates honored
- **Reuse-first** (step 1): never invent a second version of a location an existing entity already covers.
- **Unlocked-until-plated**: a `null` contract field (or a missing descriptor) is a hard refusal from `resolve_setting`/`assert_story`. Never hand-edit `status` to `"locked"` without the real plates behind it; that refusal is the load-bearing feature, not a bug to route around.
- **No art here**: generation is `lock-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the plates and flipping `status` to `locked` → `lock-references`.
- A character, visual-metaphor, motif, prop, story, or relation → the sibling `add-*` skills.
