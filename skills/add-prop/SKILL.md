---
name: add-prop
description: Add ONE prop (a discrete physical object a character holds, wears, or uses, that must render identically wherever it appears) to an Agentic Story universe (interview what it is and its load-bearing detail, reuse-first via casting sweep, then scaffold a typed `prop` entity with SPEC §12's hero + detail reference slots and ready-to-run generation prompts). Art is NOT generated here (that is `lock-references`). Use when a specific object needs to stay consistent across many renders. Generic and universe-parameterized: pass the target universe.
---

# Add Prop

One physical object, into a universe's canon, as a typed record with its reference slots scaffolded. This is authoring, not art: it ends with a validated `stub` entity + ready-to-run prompts. `lock-references` generates and locks the shots afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- What the object is and which character(s) use it.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new prop, sweep `canon/entities/` + any CANON.md for an existing object that already covers this role (two characters can share one canonical prop). Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what the reference matrix needs.
   - **What it is.** The object's form, scale, material, and who holds/wears/uses it and how.
   - **Its load-bearing detail.** The one specific feature that must never drift (an engraving, a wear mark, a color, a proportion). This is what the `detail` crop locks down; without it the prop reads as "a similar object," not "the same object."
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> prop <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `structured.sheets: {"hero": null, "detail": null}` and `requiredForRender: []`. It prints `lock_level: stub`.
4. **Fill the prose + invariants.** Edit `prose` (voice/lore/rules: what the object means, who is allowed to touch it) and `structured.invariants` (the load-bearing rules the read-back will check, e.g. the exact detail from step 2).
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: a **hero** shot (the object cleanly framed, its full form visible) and a **detail** crop (a tight close-up on the load-bearing feature). Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) states the invariant that must never drift; (c) names the target output path `reference/<id>/<shot>.png`. These are what `lock-references` will run.
6. **Validate + commit.** `agenticstory validate <universe>` stays green. Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the next step is `lock-references <universe> <id>`.

## Gates honored
- **Reuse-first** (step 1): never invent a second prop an existing entity already covers.
- **No art here**: generation is `lock-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the shots → `lock-references`.
- A character, setting, visual-metaphor, story, or relation → the sibling `add-*` skills. A recurring visual pattern not tied to a single discrete object (a gesture, a light quality) is `add-motif`.
