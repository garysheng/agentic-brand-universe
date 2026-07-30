---
name: add-motif
description: Add ONE motif (a recurring visual element, gesture, or pattern that must render identically wherever it appears, not a one-off image) to an Agentic Brand Universe (interview what it is and its load-bearing detail, reuse-first via casting sweep, then scaffold a typed `motif` entity with SPEC §12's hero + detail reference slots and ready-to-run generation prompts). Art is NOT generated here (that is `shoot-references`). Use when a repeating visual pattern needs to stay consistent across many renders. Generic and universe-parameterized: pass the target universe.
---

# Add Motif

One recurring motif, into a universe's canon, as a typed record with its reference slots scaffolded. This is authoring, not art: it ends with a validated `stub` entity + ready-to-run prompts. `shoot-references` generates and locks the shots afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- What the motif is and where it recurs.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new motif, sweep `canon/entities/` + any CANON.md for an existing motif that already covers this pattern. Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what the reference matrix needs.
   - **What it is.** The recurring element itself (a gesture, a light quality, a recurring symbol, a repeated compositional device) and why it needs to recur identically rather than be redrawn from scratch each time.
   - **Its load-bearing detail.** The one specific feature that, if it drifted, would break recognizability (the exact shape of a mark, the exact color of a glow, the exact framing of a gesture). This is what the `detail` crop locks down.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> motif <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `structured.sheets: {"hero": null, "detail": null}` and `requiredForRender: []`. It prints `lock_level: stub`.
4. **Fill the prose + invariants.** Edit `prose` (voice/lore/rules: when/how this motif is used) and `structured.invariants` (the load-bearing rules the read-back will check, e.g. the exact detail from step 2).
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: a **hero** shot (the motif in its clearest, most representative form) and a **detail** crop (a tight close-up on the load-bearing feature). Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) states the invariant that must never drift; (c) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
6. **Validate + commit.** `abu validate <universe>` stays green. Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the next step is `shoot-references <universe> <id>`.

## Gates honored
- **Reuse-first** (step 1): never invent a second motif an existing entity already covers.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the shots → `shoot-references`.
- A character, setting, visual-metaphor, prop, story, or relation → the sibling `add-*` skills. A physical object a character holds/uses (as opposed to a recurring pattern) is `add-prop`.
