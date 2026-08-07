---
name: reroll-slot
description: Re-roll ONE already-rendered slot (a spread, cover, closing plate, or any asset with a .recipe.json beside it) EXACTLY as its recipe records — same model, same prompt, same refs — with an optional one-line delta, in one command and one image call, reading ZERO canon. Resolves the recipe chain (including derive sidecars and the broken pre-v0.33 in-place-conform hole), regenerates through the provider adapter so provenance is written by construction, replays the recorded conform + publish steps for endcaps, backs up the previous roll, and ends with the render-readback reminder. Use when someone says "re-roll this image", "same but warmer/darker/at dusk", "regenerate the closing plate as-is", "run that render again", "identical but without X", or any art-only tweak to an existing rendered slot. NOT for edits that change text, cast, look, setting or register — those moved canon out from under the recipe, so use update-book / compose-spread, which re-resolve canon. Generic and recipe-parameterized: point it at any asset in any universe.
---

# Reroll Slot

The recipe beside every rendered asset is the complete reproduction context: model, full
prompt, every reference path, size, quality, and (for endcaps) the conform + publish steps
that followed. This skill is the verb that reads it back.

**Why it exists (the incident that earned it).** A trivial closing-plate edit on
*Nobody Labeled the Door* (hyperagentic-age, run `2026-08-07-1701-chat-a98f`) took **85
tool calls**, and the first render-adjacent call was #57: roughly 70% of the run was spent
re-reading the framework, SPEC and canon to reconstruct context that sat, complete, in
`closing-plate.png.recipe.json` the whole time. Recipes are written for reproducibility;
nothing consumed them. Orientation is only necessary when the answer is not already
written down.

## The one command

```bash
python3 skills/reroll-slot/scripts/reroll_from_recipe.py \
  <book>/closing-plate.png --note "identical, slightly warmer late-afternoon light"
```

- Point it at the **asset** (or its `.recipe.json`). It walks the chain itself:
  a `mode: "derive"` sidecar (platform copy, conform) is followed back to the
  generation; a chain broken by the pre-v0.33 in-place conform is recovered from
  `sourceRender` plus the closest-matching sibling `*-gen.recipe.json`, and the
  output says exactly which route it took.
- `--note` is the ONE intended delta, appended to the recorded prompt. Omit it for an
  identical re-roll. `--dry-run` prints the full resolved plan (prompt source, refs,
  replay steps) without spending anything.
- Generation goes through `on-brand-image/scripts/generate.py` (the provider adapter),
  never a raw model call, so the new roll carries its own recipe. Endcap chains replay
  `cover/scripts/conform_cover.py` with the recorded args, then the byte-identical
  platform publish with a derivative recipe. The previous roll is backed up to
  `candidates/pre-reroll-<ts>/` first.

## When this is the WRONG verb

The recipe is a snapshot of a render, not of canon. If the edit changes **words, cast,
a look, a setting, or the register**, canon has moved and a faithful replay would
reproduce the stale truth. Those edits go through `update-book` (which honors the
words-before-art gate) and `compose-spread` (which re-resolves canon). The `--note` is
for deltas the render's own vocabulary absorbs: light, weather, mood, a small
compositional nudge, "no lettering this time".

## The gate still applies

A re-roll is a render. Read it back before accepting
(`render-readback/scripts/verify_render.py`, crop-zoom the invariants); any DEFECT
re-rolls from scratch — run the command again — never an edit pass on the defective roll.
The script prints this reminder itself so a headless run cannot forget it.
