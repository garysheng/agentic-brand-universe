---
name: add-generator
description: Add ONE deterministic generator to a universe (SPEC v0.13 §4.11) — code that DRAWS an asset instead of prompting for one. Use for anything whose correctness is a NUMBER rather than a judgement: a mark, a favicon set, a starfield, procedural clouds, grids, scale rules, colour-chip sheets, diagram furniture, share-card frames. Scaffolds generators/<id>/ with a typed generator.json (params, seed, inputs, outputs, install map, proof), an entrypoint that writes provenance recipes, and a proof sheet rendered at REAL size for a human to approve. Also the correct fix when you catch yourself writing a loose make_*.py beside an asset, hand-copying a generated file into several sites, or prompting an image model for something you could compute. Generic and universe-parameterized: pass the target universe.
---

# Add Generator

One generator, typed, proofed, installable. The framework has always insisted that **deterministic
graphics render in code, not an image model**; this is where that code lives.

Reach for `on-brand-image` / `shoot-references` when the asset requires *judgement* (a scene, a face,
a mood). Reach for THIS when the asset is *computable* and its correctness is checkable with a
number: geometry, tiling, noise, palettes, layout furniture, anything you would otherwise re-roll a
model for and still not get exactly right.

## Why a generator beats a render, when it is available

- **Reproducible.** A render is not. Once a good roll is gone it cannot be regenerated; a generator
  re-runs byte-identically forever.
- **Iterable at zero cost.** Changing a starfield's density is a half-second re-run, not another
  two-minute model call that may come back different in ten other ways.
- **Correct by construction.** "Keep this region dark so the logo reads" is a NUMBER in code and a
  hope in a prompt. Nothing else gets you a guarantee.
- **Free.** No API, no key, no quota, no queue.

## Inputs

- **The universe** — a path. The generator lands at `<universe>/generators/<id>/`.
- **What it draws**, in a sentence, plus the knobs a reviewer would want to turn.
- **Where its outputs are consumed** — the repos and paths, if any, for the `install` map.

## Procedure

1. **Confirm it is computable.** If any output needs taste rather than arithmetic, split it: compute
   the deterministic part here, render the rest through a Style Pack. A generator that "mostly" works
   and needs hand-touching afterward is the artifact you were told not to hand-edit.
2. **Scaffold** `generators/<id>/` with `generator.json`, `generate.py`, `out/`, `proof/`.
3. **Write every knob into `params`, not into the code.** This is the load-bearing rule of the
   primitive (SPEC §4.11) and the source of its characteristic bug: two constants that silently mean
   different things. A favicon generator once carried `MARK_SPAN` as "fraction of the tile the mark
   fills" while the SVG it also emitted used the same number as an SVG `scale()`, which multiplies the
   entire coordinate system. They disagreed by 30% and sheared the descender off every raster.
   **A value used two ways must be DERIVED in one place, never retyped in the other.**
4. **Declare `determinism`.** `pure` (no randomness) or `seeded` (+ a `seed` in the MANIFEST, never in
   the code — a seed the manifest cannot see is not reproducible by anyone reading it). Wall-clock and
   unseeded `random()` are defects; the engine validates this.
5. **Emit a `.recipe.json` beside every output.** Same provenance contract as any other asset,
   different fields: `generator` + `params` + `seed` + input hashes instead of provider + prompt +
   refs. No asset ships without its recipe.
6. **Render a proof sheet at REAL size, and have a human approve it.** A generator is reproducible, so
   it does not need a per-run read-back; it needs one honest look. Proof at the sizes and on the
   grounds where the thing will actually be seen — a favicon set that looked perfect at 512px was
   clipping at 16, and a hero plate that read beautifully in isolation washed its logo out entirely
   once the logo was composited on top. **Composite the real consumer into the proof.**
7. **Write the `install` map** if outputs are consumed elsewhere, and make installing idempotent and
   report-only-what-changed. Hand-copying a generated file into N repos is how N repos drift, and it
   is not hypothetical: one site shipped a mark from a rebrand fourteen months stale while another
   shipped an incomplete icon set, because both were copies.
8. **Validate:** `abu validate <universe>` — the engine checks kind, entrypoint existence,
   determinism/seed coherence, declared-vs-written outputs, and install sources.
9. **Test your assumptions rather than asserting them.** The whole advantage here is that checking is
   cheap. State a design belief in a comment, then disprove it: "the bevel is mush below 48px" held up
   right until it was proofed side by side, where the bevel read *better* small.
10. **MEASURE THE RENDER. Never reason about the geometry and believe the answer.** This is the one
   that keeps costing whole sessions, because the arithmetic is right and the picture is wrong, and
   the assert you wrote is checking the numbers you just computed rather than what they produced.
   Every one of these was found by rendering and comparing, and none of them was visible in a
   thumbnail:

   - **Text placed by its advance width, not its ink.** `text-anchor="middle"` centres the advance
     width, and `letter-spacing` appends a trailing space after the final glyph, so every phrase sits
     half a letter-space off centre. Measure the ink box and place by that.
   - **A path centred by its bounding box, not its ink.** A mark whose ink is not symmetric inside
     its own viewBox lands off-centre when you put the BOX on a point.
   - **A shape's optical centre is not its bounding-box centre.** Anything heavy at one end and
     tapering at the other reads as sitting wrong when box-centred against type. Compute the area
     centroid; then let a HUMAN choose what fraction of the correction to apply, because the offset
     is arithmetic and the fraction is taste.
   - **Type converted to outlines without the font's kerning.** The outer bounding box matches
     exactly while interior glyphs sit pixels off, which is precisely the signature that survives
     every check except a pixel diff.
   - **A proof sheet scaled on the wrong axis**, which manufactured the exact defect it existed to
     detect and sent the author hunting a bug in the geometry that was never there.

   The general form: **when a generator composes two things that must relate to each other, render
   the composition and measure the relationship you claimed.** Not the inputs, not the layout maths
   — the pixels. And a proof sheet is code too, so a defect it appears to find is a defect in one of
   two places.

## generator.json

```jsonc
{
  "id": "starfield",
  "name": "Celestial hero plate",
  "kind": "generator",
  "entrypoint": "generate.py",
  "determinism": "seeded",
  "seed": 20260727,
  "params": { "markSafe": [0.50, 0.22, 0.15], "floor": 0.42, "figures": 11 },
  "inputs": ["reference/north-star-cross/mark-3d-gold-transparent.png"],
  "outputs": [{ "path": "out/hero-heavens.webp", "description": "2560x1440 hero plate" }],
  "install": { "out/hero-heavens.webp": ["public/images/hero-heavens.webp"] },
  "proof": { "sheet": "proof/contact-sheet.png",
             "assertions": ["the mark reads against the plate at hero size"] }
}
```

## Gates honored

- **Deterministic graphics never go through an image model.** If you are prompting for a grid, a
  gradient, a tiling, or a geometric mark, stop and write this instead.
- **Provenance (§3.2)** — every output carries its recipe, naming the generator and its params.
- **Proof at real size (§4.11)** — approved once, by a human, at the size it will be seen, with the
  real consumer composited in.
- **Params are data (§4.11)** — a reviewer can see every knob without reading the code.

## Not this skill

- An asset needing judgement, mood, or a face → `on-brand-image` (with a Style Pack) or
  `shoot-references`.
- A recurring element that must render identically across many MODEL images → `add-motif` /
  `add-prop`, then `shoot-references`.
- A one-off diagram carrying labels → author it as SVG directly; it does not need a generator unless
  you will regenerate it.
