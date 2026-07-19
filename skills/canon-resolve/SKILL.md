---
name: canon-resolve
description: Before writing ANY render prompt in an Agentic Story universe, resolve every named character, setting, and motif to its canon entity: output the locked sheet paths (requiredForRender), the invariants to enforce, and the entity's prose rules, then run the load-bearing gate (assert.sh spread|story). Prevents reinventing locked designs, passing draft or wrong-era references, and prompting from memory. Generic and universe-parameterized: pass the target universe.
---

# Canon Resolve

The pre-render gate that turns "I remember this character" into "here are the exact locked files and rules." Run it before writing any prompt for a spread or a shot. It resolves canon to real paths and refuses the render if anything required is missing.

## Inputs
- The target universe (a path with `universe.json`). Read its `identity` (for `register.anchor`) and `assetRoot`.
- The entities in frame: a spread's cast + optional location, or a whole story id.

## Procedure
1. **Resolve each entity.** For every named character/setting/motif, read `canon/entities/<id>.json`: resolve `structured.requiredForRender` to real files under `assetRoot`, collect `structured.invariants`, and read `prose.rules`. Never guess a path by filename and never describe an entity from memory: read the locked record.
2. **Assemble the prompt scaffolding.** Output, per entity: the exact reference files to pass (the resolved required sheets, plus the entity's key optional shots when relevant), the invariants to bake as positives, and the failure modes to bake as negatives. Lead every prompt with `identity.register.anchor` (the universe style anchor).
3. **Run the load-bearing gate.** `python3 -m agenticstory.cli assert-spread <universe> --characters a,b [--location X]` (or `assert-story <universe> <id>`). A non-zero exit BLOCKS the render and names exactly what is missing or unlocked. Fix it (lock the reference, lock the setting) before proceeding.
4. **Hand off.** Return the resolved paths + invariants + register anchor to the renderer. No prompt is written until this resolve passes.

## Gates honored
- **Load-bearing refs:** a missing required sheet or unlocked setting is a hard stop, not a silent skip.
- **No memory rendering:** every design comes from the locked record, never from recall or a guess.

## Not this skill
- Generating or reading back the image (that is the renderer + `render-readback`).
- Authoring the entity (that is the `add-*` skills).
