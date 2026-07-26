---
name: on-brand-image
description: Generate ONE on-brand image from a Style Pack (SPEC §4.7) — a portable folder of style references plus a read-back gate — with NO universe required. Compiles the prompt from the pack (style line + subject + the pack's rejected poles as negatives), generates with the pack's anchor reference passed FIRST, then reads the output back against the pack's gate assertions and re-rolls any defect from scratch. Use for the common case "here is a folder of images, make more that look like them": deck plates, page heroes, section art, icons, one-off brand illustration. Optionally accepts a locked canon master (a character/motif/prop reference) as an extra input so a recurring element stays identical. Generic and pack-parameterized: pass the target style pack.
---

# On-Brand Image

One image, in a known look, gated. This is the framework's **lightweight front door**: it consumes a
**Style Pack** (SPEC §4.7), not a universe, because "generate more images in this style" has no
recurring-identity requirement and therefore needs no canon.

Reach for the full canon flow (`add-*` + `shoot-references`) only when a *specific thing must render
identically everywhere*. If the subject changes every time and only the *look* is shared, you are in
the right skill.

## Inputs

- **The style pack** — a path to a folder containing `pack.json` + `refs/` (SPEC §4.7). Read its
  `anchor`, `refs`, `styleLine`, `palette`, `rejectedPoles`, `gate`, `maxElements`.
- **The scene** — what the image depicts, in one or two sentences. The ONLY free text in the prompt.
- **The output path**, and optionally a size (default square; pick landscape for page heroes).
- **Optional: locked masters** — paths to already-locked canon shots (e.g. a motif's `hero.png`) for
  any recurring element that appears in this image.

## Procedure

1. **Load the pack.** Resolve `anchor` and `refs` inside the pack folder. A ref that does not resolve
   is a hard error, not a warning: the look is the references, and a missing one silently degrades the
   render into generic AI illustration.
2. **Select references.** Always the `anchor` FIRST, then up to three more `refs`, choosing at least
   one whose motif matches the scene (hands, a figure, a diagram-ish arrangement). Append any locked
   masters AFTER the style refs. Never generate from prose alone.
3. **Compile the prompt** (do not free-write it):
   ```
   Create a NEW illustration in EXACTLY the visual style of the reference images.
   STRICT STYLE: <pack.styleLine>. <ground/fill/line rules from pack.palette>.
   Subject: <the scene>.
   <negatives: "no " + each of pack.rejectedPoles>.
   ABSOLUTELY NO text, no letters, no numbers.
   ```
   Keep the element count at or under `pack.maxElements`; if the scene needs more, the scene is wrong
   for this look (split it, or it belongs on a diagram instead).
4. **Generate via the framework provider adapter** `scripts/generate.py` — NEVER the raw model script.
   It generates AND writes `<output>.recipe.json` (provider, prompt, specVersion, refs, sha256) in the
   same shape `shoot-references` freezes, so **every candidate is provenanced at birth**, not only at
   lock. Pass the selected references in order (anchor first) plus `--style-pack <pack-id>`. Provenance
   is a side effect of generating here; there is no un-provenanced image.
5. **Read back against the gate (mandatory).** Open the output and check EACH `pack.gate` assertion
   against the actual pixels, returning PASS or DEFECT per item. This is the load-bearing half; a pack
   without a gate is a mood board.
6. **Re-roll defects from scratch.** On any DEFECT, regenerate the whole image with a clause added to
   counter that specific defect. Never stack an edit pass on a defective render. Cap at 3 rolls, then
   stop and report the surviving defects rather than shipping a silent failure.
7. **Report** the output path and the per-assertion verdict.

## Lookbooks (curated variety, SPEC §4.7.1)

A scene with a **crowd or a wardrobe** takes an optional **Lookbook** alongside the pack (`create-lookbook`). Where the pack sets the render medium, the lookbook sets a VARIED subject vocabulary (fashion, faces, home silhouettes). When given one:
- **Sample 2-4 of its refs** (not all; and not the same subset every render) and pass them AFTER the pack refs.
- **Prepend its `varietyRule`** to the prompt ("dress each person differently from this range; never a uniform, never two people matching").
- **Add its `gate` assertions** to the read-back, and re-roll from scratch if the crowd comes back uniform.
- Pass `--lookbook <path>` to the provider adapter so the recipe records it.
A universe binds a lookbook everywhere via a `craft-canon` register-rule that names it (e.g. `godly-aligned-dress` → `christofuturist-fashion`), so uniformity can never silently creep back in.

## Rendering operations (hard-won)

- **A render is NOT reproducible.** gpt-image-2 has no seed parameter; nano's `seed` is not pixel-deterministic. So **never delete an un-locked candidate** — once a good roll is gone it cannot be regenerated. Stage candidates, prune only AFTER the winner is locked. (A blessed yoke roll was lost exactly this way.)
- **Batch renders in the background.** gpt-image-2 at `--quality high` is ~2 minutes per image; a foreground call under a 2-minute cap, or several in parallel, gets killed mid-generation with nothing saved. Run multi-image batches detached and collect them when they finish.
- **A logo/mark destined for a transparent cutout must be rendered on a GREEN SCREEN, not a "nice" ground.** Prompt it FLOATING on a flat chroma-key green (`#00B140`) with NO shadow, NO reflection, NO surface — then key it (`greenness = G - max(R,B) > threshold`, border-connected flood so interior highlights survive, + green despill). A warm/bone background bakes a floor reflection or contact-shadow that reads as high-chroma gold and defeats every heuristic cutout (a whole cutout was lost fighting one). Green makes the key trivial and artifact-free.
- **Verify a rendered mark's geometry against its spec; the model exaggerates.** An image model reliably over-stretches a deliberate proportion (a North Star Cross with a 1.48x-longer bottom rendered at ~1.7x). Measure the actual arm ratios in the output (isolate the shape by chroma, find the tip extents) and, since a render is not reproducible, DETERMINISTICALLY correct it (e.g. scale only the region past the crossing to hit the exact ratio) rather than re-rolling and hoping.

## Gates honored

- **References-first** — the look is carried by the reference images, never by wording it harder. A
  prompt-only attempt at a locked style reliably produces generic AI illustration.
- **Read-back (SPEC §3.5)** — every render is verified against the pack's gate before it is accepted.
- **No text, ever** — image models misspell and silently drop glyphs, and a wordless image stays
  reusable across surfaces and languages. Words belong in the page around the image.
- **Anatomy is a gate concern, not a prompt concern.** You cannot reliably prompt away a bad hand.
  Either the look is deliberately non-anatomical (loopy ink hands have no finger-count to get wrong,
  which is why this style sidesteps the defect by construction), or the gate catches it and re-rolls.
  When a hand IS anatomical enough to count, state the digit budget explicitly ("exactly four fingers
  plus one thumb") AND count it in the read-back; the prompt alone will not hold.
- **A set must be uniform in kind.** When the scene contains several of the same element, give every
  one of them the defining feature. Varying a set by OMISSION reads as failure, not as variety: three
  winged towers where one lacks wings does not say "these are different companies", it says "that one
  is broken". Vary size, height, spacing, or angle instead, and never the thing that defines the set.

## Not this skill

- A recurring element that must be identical across many images → `add-motif` / `add-prop` /
  `add-character`, then `shoot-references`. Pass the resulting locked master back into THIS skill as an
  extra input.
- A full book spread with characters, poses, and a setting → `compose-spread`.
- Standing up a new look from scratch, or a universe → `start-new-story-universe`.
- An explanatory diagram carrying labels and text → not an image-model job at all; author it as SVG.
