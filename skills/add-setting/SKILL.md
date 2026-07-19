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
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> setting <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `status: "unlocked"` and a `contract` whose fields (`turnaround`, `emptyPlates`, `blueprint`, `map`, `blocking`, `dressing`) are all null/empty. It prints `lock_level: stub`.
4. **Fill the descriptor prose.** Edit `contract.map` (the spatial layout in words), `contract.blocking` (where characters can stand/move without breaking geometry), and `contract.dressing` (the recognizable materials/props/palette). These three are load-bearing text, not flavor: the resolver requires them non-empty, and every render of this setting passes them in the prompt. Also fill `prose.rules` for any never-render constraint.
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: one block per contract file slot, a `turnaround`, one `emptyPlate` per fixed camera (C1, C2, ...), and a `blueprint` (top-down/schematic). Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) restates the FIXED geometry from step 2 so every plate agrees with every other; (c) names the target output path `reference/<id>/<shot>.png`. These are what `lock-references` will run.
6. **Validate + commit.** `agenticstory validate <universe>` stays green (an `unlocked` setting still validates: that is a correct, expected state, not an error). Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the setting stays refused by `assert-story`/`assert-spread` until `lock-references` fills every plate and flips `status` to `"locked"`.

## Gates honored
- **Reuse-first** (step 1): never invent a second version of a location an existing entity already covers.
- **Unlocked-until-plated**: a `null` contract field (or a missing descriptor) is a hard refusal from `resolve_setting`/`assert_story`. Never hand-edit `status` to `"locked"` without the real plates behind it; that refusal is the load-bearing feature, not a bug to route around.
- **No art here**: generation is `lock-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the plates and flipping `status` to `locked` → `lock-references`.
- A character, visual-metaphor, motif, prop, story, or relation → the sibling `add-*` skills.
