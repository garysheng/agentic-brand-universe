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
2b. **The standing EYELINE check, on every scene with a conversation in it (v0.38).** Beyond the
   entity invariants, any render whose scene has people talking with, laughing with, showing
   something to, or being introduced to someone gets one extra look: crop-zoom each
   participant's eyes and ask WHO THEY ARE LOOKING AT. Eyes on the interlocutor: PASS. Eyes on
   the camera or the middle distance while the scene says they are engaging someone: DEFECT,
   re-roll from scratch, naming the gaze in the re-roll ("her eyes are on HIS face, not the
   camera"). The one exception is a scene that explicitly hands the camera the interlocutor's
   role (a direct-address closing spread). Earned 2026-08-08 (the-introducer): three renders in
   one batch put the subject's eyes on the lens mid-conversation, because a warm grin toward
   camera is the model's strongest prior for a likeable subject; the operator's rule is "if the
   camera is not representing your interlocutor's eyes, why are you looking at it?" The prompt
   half of the same rule is `EYE_CONTACT_GUARD` in compose-spread.
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


## What NOT to measure: a mark's geometry

`measure star` existed for one afternoon and was WITHDRAWN the same day. It
answered "is this four-point mark the right shape" with a ratio, and it was wrong
five times out of five on real plates: it masked a warm backdrop and returned
0.93, locked onto a jacket button and returned 0.74 PASS, measured a chain
connected to the pendant at 6.11, returned 11.25 on a crop that isolated nothing,
and finally passed an obviously equilateral compass star that the operator
rejected on sight. That last one was disqualifying: the function assumed "top arm
equals side arm, by spec" and so never measured the top arm, which is precisely
what turns this mark from a cross into a compass star. It assumed away the defect
it existed to catch.

**Judge a mark by eye against its blessed plate. Then condition every render on
that plate.** That is not a workaround, it is the framework's thesis: a golden IS
human judgement, frozen. Reaching for a computed proxy replaces the one instrument
that actually works with one that produces false precision, and false precision is
worse than no number, because it survives review.

Gary, 2026-08-01, after four rerolls: *"I'm clearly going to need to just keep
rerolling with you until it's good, then you just use those goldens. Reminds me of
the importance of the human eye."*

`measure figure` remains, because head-to-body is a genuine ratio between two
unambiguous landmarks, and because it REFUSES rather than guessing when it cannot
find them. The distinction worth keeping: measure a quantity a human cannot
eyeball reliably, never a judgement a human makes instantly.
