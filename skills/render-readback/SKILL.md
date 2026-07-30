---
name: render-readback
description: After EVERY render in an Agentic Story universe, read the image back and crop-zoom each of the in-frame entity's invariants, returning a per-invariant PASS or DEFECT verdict. Any DEFECT means regenerate the image FROM SCRATCH (never stack an edit pass). Use immediately after each generated image, before accepting or locking it. Generic and universe-parameterized: the invariants come from the entity's `structured.invariants`.
---

# Render Read-back

The quality gate that catches a defective render before it ships or locks. A render that looks fine at thumbnail can be wrong at the invariant level (a lens that should not be there, a missing patch, a wrong pendant). Read-back forces a per-invariant check.

## Procedure
1. **Load the entity's invariants.** From `canon/entities/<id>.json` read `structured.invariants` (the load-bearing identity rules). If the entity has none, there is nothing to check and the render passes trivially.
2. **Read the image back.** Open the just-generated image. For EACH invariant, crop-zoom the relevant region (the face for a face rule, the chest for a patch rule, the feet for a shoe rule) and judge it directly against the invariant. Do not judge from the thumbnail or from memory of the prompt.

   Use the two scripts in `scripts/` rather than writing PIL by hand. Both take FRACTIONS of the image, so a box survives a re-render at another size:
   - `contact_sheet.py OUT.png --cols N IMG...` — the WIDE pass over a batch.
   - `crop_zoom.py OUT.png IMG --box X0,Y0,X1,Y1 --label "what this must show"` (repeatable) — the NARROW pass, which is where most invariants actually live: a pendant that must be a four-point star and not a crucifix, two gold incisors, a patch on the correct side, a face-down phone.

   Pass `--grid 4x4` instead of `--box` when you do not already know where the detail sits. Guessing a box, getting back a rectangle of empty shadow, and guessing again costs two round trips; the grid costs one. (Earned on the-little-door, 2026-07-30, which guessed wrong twice in one run.)
3. **Verdict per invariant.** PASS (the invariant holds) or DEFECT (it does not), with a one-line reason on any DEFECT.
4. **Act on the result.** All PASS: the render is accepted. Any DEFECT: regenerate the image FROM SCRATCH with the defect named as an explicit negative. Never stack an edit pass on a defective render (it compounds artifacts).

## Not this skill
- Generating the image (that is the caller, e.g. `shoot-references` or a renderer).
- Locking the passed shot into canon (that is `shoot-references` / the renderer).
