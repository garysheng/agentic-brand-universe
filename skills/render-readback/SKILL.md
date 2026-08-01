---
name: render-readback
description: After EVERY render in an Agentic Brand Universe, read the image back and crop-zoom each of the in-frame entity's invariants, returning a per-invariant PASS or DEFECT verdict. Any DEFECT means regenerate the image FROM SCRATCH (never stack an edit pass). Use immediately after each generated image, before accepting or locking it. Generic and universe-parameterized: the invariants come from the entity's `structured.invariants`.
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

## Measuring a numeric invariant

Some invariants are NUMBERS: a character's head-to-body proportion, a mark's
height-to-width ratio. Cropping and zooming answers "does this look right"; it
cannot answer "is this 1:8 or 1:6.5". `scripts/measure.py` does.

    measure.py figure <image> --chin Y [--overlay out.png]
    measure.py star   <image> --box x0,y0,x1,y1 [--overlay out.png]

**It records HOW it measured, beside the image, as `<image>.measure.json`.** That
is the point, not a convenience. Three consecutive sessions hand-rolled this
ruler and reported 1:6.5 -> 1:7.6, then "both plates 1:7.2", then 1:7.04 ->
1:7.26 for overlapping plates, because none of them recorded their landmarks.
Nobody could tell whether a plate had improved or the method had changed. A bare
number is not a measurement.

**The chin is not auto-detected, deliberately.** A luminance-minimum detector
locks onto the shadow under the lower lip rather than the chin base and returns a
confident 1:8.8-1:9.2 on a figure that is really about 1:7.2. Pass `--chin Y`, or
render `--overlay` and read it off the ruler. The record says which you did, and
reports how much a 5px error would move the result.

**It refuses rather than guessing.** A predecessor scanner returned crown=0,
sole=1534 on a 1536px plate: the whole frame, silently, as if the figure filled
it. Every detector here validates its own output, and `star` refuses any result
above 3:1 because no rendering of a four-point mark with equal top and side arms
can be that narrow. If you get `UNMEASURABLE`, the crop is wrong; tighten it.
Do not hand-roll a ruler around a refusal.
