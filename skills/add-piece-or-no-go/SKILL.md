---
name: add-piece-or-no-go
description: Record ONE brand PIECE (a reusable part of the brand with its exact recipe, or a pointer to the canon that already defines it - a selection state, a button, a thread of stripes, a section marker, a mark at a size) or ONE NO-GO (a thing the brand refuses, why, and the piece to use instead) into a universe's kit record (SPEC 13.1, craft-canon kind `kit`), with who decided it, when and in what words. Supersedes a contradicting canon line IN PLACE with the old words kept, and runs `abu check-kit` over the surfaces so a detectable no-go becomes a refusal instead of a remembered preference. Use the moment a human rules on a brand detail ("I don't like it when you...", "never do X", "use this instead", "that's the look for selected", "make that part of the ABU"), when you find a refusal scattered in rule prose or a STATE file, or when you are about to hand-write the same CSS recipe for a brand part a second time. Generic and universe-parameterized: pass the target universe.
---

# Add a piece or a no-go

A brand is small reusable parts plus the things it refuses. This skill puts ONE of either into the
universe's kit, where `validate` holds it to live canon and `abu check-kit` can enforce it. It never
writes site code: surfaces outside the universe are LISTED for whoever owns them.

## Inputs
- The target universe (a path containing `universe.json`). Run `abu kit <universe>` first: the
  piece may already exist, and a second id for one part is the drift this record exists to stop.
- The ruling, in the decider's own words, with the date. No verbatim means no ruling: ask, or cite
  the canon line it was lifted from as a `source` with its exact `quote`.
- For a no-go, the piece to use instead (record that piece first if it is new). If nothing replaces
  it, `instead: null` with an `insteadNote` saying so.

## Method

1. **Find the kit.** `abu list-craft <universe>` shows records of kind `kit`. None yet: create
   `canon/craft/brand-kit.json` with `id`, `kind: "kit"`, `name`, `summary`, `tokensFrom` (the
   `<file>#<path>` of the token map recipes name), and empty `pieces` / `noGos`. Shape: SPEC 13.1.
2. **A piece already defined in canon POINTS, never copies.** Give it `definedAt:
   "<file>#<dot.path>"` (numeric segments index lists). Only a new part gets a full `recipe`
   (tokens by name, sizes, CSS where it applies) and `usedIn`.
3. **A no-go names its replacement and its provenance.** `refuses`, `why`, `instead`, `decided`
   {by, on, verbatim}. Harvested from existing canon: add `source: [{at, quote}]`, quoting the line
   exactly; a sibling repo's file is `<repo>:<path>@<commit>` (recorded, not checked).
4. **If the ruling contradicts a live canon line, supersede it in place, never delete.** Rewrite
   the live line to point at the piece, keep the old words in a supersession note beside it with
   the date and verbatim, and add `supersedes: [{at: <live line>, said: <old words>}]` to the
   no-go. `validate` refuses the kit while the live line still says the old words.
5. **Give it a detector when the shape is mechanical.** `detect: [{pattern, files?, note}]`, a
   regex over source files, written with `[^}]*` so one match cannot span two CSS rules. Test it
   against the shape that actually shipped, and against the replacement so it does not fire there.
   A taste rule with no mechanical shape gets no detector; say so in the no-go.
6. **Gate.** `abu validate <universe>` (and the universe's own `assert.sh` if it has one) must be
   green. Then `abu check-kit <universe> <every surface repo it governs>`: hits inside the universe
   get fixed now; hits in repos you were not asked to edit are LISTED in your report, file:line,
   for their owners. Never edit them on the strength of this skill.
7. **Commit** the kit and any superseded canon file by explicit path.

## Refusals
- No item without `decided.by`, a `YYYY-MM-DD` date and the verbatim (or a quoted `source`).
- No second id for a part the kit already has; extend the existing piece.
- No silent deletion of a superseded rule; the old words stay, marked superseded.
- No editing a consumer repo from here; the report lists where the old rule still renders.
