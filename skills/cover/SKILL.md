---
name: cover
description: Create a picture-book cover for a story in an Agentic Brand Universe, at the platform's portrait aspect. Bakes the diegetic title + the universe mark (identity.mark), passes the register anchor first, and runs render-readback on the title spelling + hero likeness + register discipline. Generic and universe-parameterized.
---

# Cover

**EVERY book ships a cover, and a cover is not done until the TITLE and the universe MARK are baked into it.** This is the single most-forgotten step: a beautiful hero render with no title on it is NOT a cover, it is cover art. If you generated portrait hero art with a raw `generate.py`/`on-brand-image` call and moved on, you skipped the cover — come back here. **Never hand-roll a cover render**; a cover always goes through this skill, because the title-bake and the title-spelling read-back live here and nowhere else. A book must not be published until its cover carries its title.

The cover is not a normal spread. Interior spreads render at the story's landscape spread size; a cover renders PORTRAIT, because the reader platform displays covers at a taller aspect and center-crops anything shipped landscape. Rendering the cover at spread size is the recurring failure this skill exists to prevent: it ships as a sliver, or the title clips.

## Inputs
- The target universe (a path with `universe.json`).
- The story id, and its title.

## Procedure

1. **canon-resolve the cover's in-frame entities.** Run `canon-resolve` on the hero (and any other named character, setting, or motif the cover composes) exactly as for an interior spread: resolve locked reference paths, collect invariants, and run the assert gate. No cover prompt is written except from that output.

2. **Compose the cover beat.** The hero, in the register the universe's `identity.register` names, oriented toward whatever the story sends them toward (not squared to the viewer, unless the beat calls for a direct address). Honor the universe's `register-rule` craft records (e.g. a rule governing where warm light may appear) the same as any interior spread.

3. **Render at portrait aspect, never the landscape spread size.** Use the renderer's guarded cover path (the same guard that forbids passing a prior spread render as an input applies here: a revised cover is regenerated from references, never edited on top of the old attempt). Bake the diegetic title text and the `identity.mark` byline directly into the render (in-art text is licensed for a cover title and a mark line; quote the exact strings in the prompt). Pass `identity.register.anchor` FIRST and bake `identity.register.rejectedPoles` as negatives, same as every render.

4. **VERIFY THE LETTERING WITH YOUR EYES, FROM THE BANDS, BEFORE ANYTHING ELSE.**
   ```bash
   python3 <abu>/skills/cover/scripts/cover_text_bands.py <cover.png> [more covers...] --out /tmp/bands.png
   ```
   Then OPEN that sheet and rule per cover, per line: is the title drawn, is the byline
   drawn, is the series mark drawn. A missing line means regenerate; never patch lettering
   afterwards.

   **The BAKED TEXT block is not evidence.** It records what was REQUESTED. A batch of
   twelve covers was reported as "all three lines present" off that block on 2026-08-05 and
   four of them had no byline and no series mark at all; the operator caught it, not the
   pipeline. If you have not looked at pixels, you have not checked.

   **Do not use OCR as the judge.** It was tried on that same batch and produced THREE FALSE
   NEGATIVES out of twelve, reading "LOOKE" for "LOOKED" and missing two titles outright.
   These are stylised painted letters, often light on dark and sometimes brush-drawn. A
   false negative here re-rolls art that was already correct, which is the most expensive
   mistake available. The judge is a pair of eyes; the script only prepares what they need.

   **Do not judge from a full-cover contact sheet either.** Covers downscale to thumbnails
   and small lettering stops being readable, which is exactly how a missing byline survived
   review. That is what the band crops are for.

5. **render-readback the cover.** Crop-zoom: the title spelled exactly (regenerate on any typo, never patch text after the fact), the hero's likeness against their entity's invariants, and the register discipline (the anchor's palette and finish held, no drift toward a rejected pole). Any DEFECT means regenerate the whole cover from scratch.

6. **Wire it.** Point the story's cover field (in whatever manifest the target renderer/platform uses) at the finished file.

## Gates honored
- **Register-anchor-first:** `identity.register.anchor` passes first, same as every render in the universe.
- **Read-back:** title spelling, hero likeness, and register discipline are all checked before the cover is accepted; any DEFECT regenerates from scratch.
- **Correct aspect:** the cover never ships at the interior spread's landscape size.
- **Subject-approval:** a real-person hero's cover likeness carries the same approval gate as any other depiction of them.

## Not this skill
- The interior spreads → `render-book`.
- Editing a cover on an already-shipped book (still uses this skill's procedure, invoked by) → `update-book`.
- Shipping the cover to a shared platform → the platform-delivery skill (deferred).
