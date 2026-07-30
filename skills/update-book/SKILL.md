---
name: update-book
description: Edit or extend an existing picture book in an Agentic Brand Universe: add, insert, revise, or remove a spread, renumber, and regenerate only the touched art + narration. Honors the words-before-art gate (voice-gate on any changed text) and re-resolves canon (canon-resolve) + reads back (render-readback) on every regenerated spread. Generic and universe-parameterized.
---

# Update Book

For changing a book that already exists: words blessed, art on disk, usually already shipped. Creating a new book is `render-book`'s job. This skill owns the surgery: inserting, revising, or removing spreads without breaking numbering, canon, narration, or a sibling property's own delivery.

## Inputs
- The target universe (a path with `universe.json`).
- The story id of the book being edited, and the requested edit (add, insert, revise, or remove one or more spreads).

## Procedure

1. **Load the story + the edit.** Read `stories/<id>.json` (its `beats`, `spine`, `genre`, `register` override if any) and whatever asset manifest the target renderer/platform uses for this book. Identify exactly which beats/spreads the edit touches; leave everything else alone.

2. **Re-run the sweeps the book was BUILT with. A revision is not a small edit, it is a new build against canon that has moved since the book shipped.** All three of these were skipped on a real revision because it felt like a text tweak:
   - **Casting sweep on every proper noun in the new text** (`casting-sweep`). An entity the book could not have used at ship time may exist now. A revision that names a person canon already has, and does not check, either invents a duplicate or misses a locked likeness.
   - **Sibling properties, for the SCRIPTURE and the argument, not just the cast.** Grep `canon/properties/*.json` before adopting a verse or a thesis. The obvious verse for a new movement is often the entire spine of a shipped sibling, and reusing it collapses two distinct arguments into one book's worth of meaning.
   - **The render-spec's own preamble, which predates flags added since.** An older spec can be missing a guard that never mattered while every spread cast a setting, and that goes wrong on the FIRST spread the revision adds that casts none. Diff the book's preamble against a recently-built sibling's before adding a spread.

3. **Apply the structural edit.**
   - **Add/insert:** draft the new beat(s) in the book's own voice, at the strongest thematic insert point (an appended-at-the-end placement is rarely the right one; confirm with the author if it's an authorial call). Renumber beats at and after the insert point.
   - **Revise:** edit the beat's text and/or its cast/location in place. No renumber needed.
     **A reader who does not understand a beat is a DEFECT IN THE BEAT, not in the reader**, and that is true even when the
     reader is the author. When the confusion lands on a beat carrying the property's own thesis, fix it by giving the reader
     the mechanism rather than by withholding it for a later payoff: state what the thing IS, then point at what it could
     become. A spine-object introduced with no help and no payoff for fifteen spreads is asking the reader to hold an
     unexplained image on trust. Check whether the ART is doing its job before touching it: a caption-only fix is common here
     and is far cheaper than a re-render.
   - **Remove:** delete the beat and renumber everything after it down by one.
   In every case, verify the beat numbering stays contiguous `1..LAST` afterward, across the manuscript, the asset manifest, and any narration index.

   **If the new beats re-value something an EXISTING beat argued against, say so in `aimDiscipline`.** New material often extends an earlier claim rather than reversing it (a book can call a crown counterfeit at beat 10 and still praise the same worldly success at beat 13, because what was counterfeit was the crown worn alone). Unrecorded, that reads to the next canon check as drift, and someone "fixes" it back. Write the distinction down, and update the book's `canon/properties/<id>.json` record in the same pass so the next casting sweep sees the revised shape.

4. **Words-before-art gate on any changed text.** If a beat's text is new or revised, run `voice-gate` on it before any art or narration for that beat is touched. No art, narration, manifest sync, or delivery for a changed beat until the words are blessed and voice-clean. Mark an unblessed addition clearly so a later session never generates art against unblessed text. A removal is itself an authorial call and gets the same blessing before it executes.

5. **Regenerate only the touched spreads**, via the same discipline as `render-book`:
   - `canon-resolve` the spread's cast + location (resolved paths, invariants, the assert gate).
   - Generate passing `identity.register.anchor` FIRST, with `identity.register.rejectedPoles` and the universe's `register-rule` records baked as negatives, honoring the story's genre format canon.
   - `render-readback` the render (crop-zoom every invariant); any DEFECT regenerates from scratch, never an edit pass on the prior attempt.
   - Re-render narration for any spread whose text changed; leave a renamed-but-textually-unchanged spread's narration alone.

6. **Leave untouched spreads alone.** A renumber may shift a file's name, but a spread whose text and art are unchanged does not get regenerated, re-read-back, or re-narrated: minimal-regeneration is the point of this skill over re-running `render-book` on the whole story.

7. **Redelivery of an ALREADY-PUBLISHED book: re-stage the art even when no art changed.**
   This is the single most expensive trap in this skill and it costs real money every time. A publish step that uploads to
   remote storage typically **PRUNES the local copies afterwards**, because the bucket is their home. So an already-shipped
   book has NO local interiors and NO local audio. If you then regenerate one narration clip for a caption-only edit and run
   publish, three things happen in order: the art check fails (there are no staged interiors), the run reports that it shipped
   NOTHING, and **the prune runs anyway and deletes the clip you just paid to generate**. You are left worse off than before
   you started, with a confusing success-shaped message.

   The rule: **for ANY redelivery of a published book, re-stage the full art set FIRST, then regenerate the touched narration,
   then publish.** Staging is free and deterministic; the clip is not. Keep the book's render output (or its staging input) on
   disk permanently for exactly this reason, and never treat "the book is published" as "the local build is disposable".

   If the platform's publish step prunes on a run that shipped nothing, that is a bug in the publish step worth fixing at the
   source: a run that publishes nothing should prune nothing.

8. **Verify + deliver.** Confirm the beat/spread numbering is contiguous everywhere it's tracked, re-stamp `identity.mark`/`identity.closingOrnament` on the closing plate if the edit touched it, and hand off to whatever delivery step the target renderer/platform uses. If the book ships to a shared platform, verify sibling properties on that platform are unaffected by the edit before calling it done.

## Gates honored
- **Words-before-art + voice-gate:** any changed text is blessed and voice-clean before its art or narration regenerates.
- **Canon-resolve before every regenerated prompt.**
- **Read-back after every regenerated render:** any DEFECT regenerates from scratch.
- **Re-stage before redelivery:** an already-published book has no local assets; stage the art before regenerating narration, or the publish prune eats the new clip.
- **Minimal-regeneration:** only the touched spreads (and their downstream narration) regenerate; everything else stays as-is.
- **Subject-approval:** a real person's confusion-flags and likeness approval on a revised beat count the same as the author's.

## Not this skill
- Creating a brand-new book → `render-book`.
- Rendering or re-rendering the cover → `cover` (this skill calls it when the edit touches the cover).
- Pure art regeneration with no text change is still this skill's job; it just skips the words-before-art gate.
- Shipping the edit to a shared platform → the platform-delivery skill (deferred).
