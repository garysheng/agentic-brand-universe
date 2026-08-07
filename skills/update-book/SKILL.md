---
name: update-book
description: Edit or extend an existing picture book in an Agentic Brand Universe: add, insert, revise, or remove a spread (insert_spread.py), RECAST one canon entity as another across a whole story (recast_story.py), renumber, and regenerate only the touched art + narration. Honors the words-before-art gate (voice-gate on any changed text) and re-resolves canon (canon-resolve) + reads back (render-readback) on every regenerated spread. Generic and universe-parameterized.
---

# Update Book

For changing a book that already exists: words blessed, art on disk, usually already shipped. Creating a new book is `render-book`'s job. This skill owns the surgery: inserting, revising, or removing spreads without breaking numbering, canon, narration, or a sibling property's own delivery.

## Inputs
- The target universe (a path with `universe.json`).
- The story id of the book being edited, and the requested edit (add, insert, revise, or remove one or more spreads).

## Procedure

0. **FIRST: is this an art-only re-roll? Then the recipe already holds everything, and
   the route is ONE command.** If the edit changes no text, no cast, no look, no setting
   and no register — "re-roll the closing plate", "same cover but warmer light", "run
   spread 12 again without the lettering" — do NOT re-orient on canon. The complete
   reproduction context (model, full prompt, every ref path, the conform/publish steps)
   sits in the slot's own `.recipe.json`, and this script reads it back:

   ```bash
   python3 skills/reroll-slot/scripts/reroll_from_recipe.py \
     <book>/closing-plate.png --note "identical, slightly warmer light"
   ```

   It regenerates through the provider adapter (provenance by construction), replays the
   recorded `conform_cover.py` args and platform publish for endcaps, backs up the prior
   roll, and prints the render-readback reminder. Then read the result back and you are
   DONE — none of the steps below apply. This step exists because a real run spent 71 of
   85 tool calls re-reading the framework and canon to reconstruct what the recipe
   already said (hyperagentic-age, 2026-08-07). The moment the edit touches words, cast,
   a look or a setting, the recipe is a snapshot of stale truth: fall through to step 1.

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

## Inserting or removing a beat mid-book: `insert_spread.py`

**Never hand-roll the renumber.** An insert is a THREE-artifact edit with a silent
ordering trap in it: the story's `beats[]` and their `n`, the render-spec's
`spreads[]` and their `id`, and the rendered `spread-NN.png` plus each
`.png.recipe.json` beside it. Renaming the art ASCENDING overwrites, because
`spread-05 -> spread-06` lands on a `spread-06` that has not moved yet. You end up
with the right file count and the wrong pages, and nothing errors.

```bash
python3 skills/update-book/scripts/insert_spread.py <universe> <story> \
  --book <book-folder> --at 4 \
  --text "the new caption, verbatim" \
  --characters jerry-man,kenzie --location some-setting \
  --provenance "where this came from"        # dry run
# ... then --apply
```

- **Dry run by default.** It prints how many art files shift and what it will delete.
- **It moves the art DESCENDING**, which is the whole point.
- **Endcaps never shift.** `cover.png` and `closing-plate.png` are not indexed by beat.
- **It refuses when the story and the spec are already out of sync**, rather than
  shifting a mismatch into a worse mismatch.
- **It reports beat-number citations it cannot fix.** `aimDiscipline`, `spineNote` and
  provenance lines that say "beat 12" are invalidated by a shift, and no tool can know
  whether that sentence meant the old 12 or the new one. Same discipline as
  `recast_story.py`: swap what you can prove, report what you cannot.
- **It does NOT render.** The new spread lands with an empty `scene`, which the
  compiler refuses, so the hole cannot be shipped by accident. Author it, then render
  ONLY that spread. Everything else on disk is still valid: the renumber moved the
  art, it did not invalidate it.

`--remove --at N` deletes the beat, its spec entry and its art, and closes the gap.

## Recasting: swapping one canon entity for another

`add`, `insert`, `revise` and `remove` all operate on SPREADS. Replacing one entity
with another across a whole story is a different operation, and it was done twice by
blanket string replacement before this existed (2026-08-01, will-there-be-ice-cream:
a character re-aged from sixteen to twelve, and a setting abandoned after the room
would not hold its geometry across twenty-six spreads).

```bash
python3 skills/update-book/scripts/recast_story.py <universe> <story> <old-id> <new-id> \
    [--spec <book>/render-spec.json] [--review-out review.txt] [--apply]
```

**Dry run by default.** It refuses an unregistered entity, because a recast must land
on real canon.

**What it does deterministically**, because these are provable:
- swaps every structural id reference: beats' `location` and `characters`, `features`,
  `writesBack`, and the render-spec's `setting` and `cast[].id`
- flags any `plate` the NEW entity does not declare. Plate keys are per-entity
  (`master`/`empty` versus `wide`/`close-jerry`), so a swapped setting keeps a camera
  that no longer exists and the compiler refuses much later with no hint why. It
  reports and never guesses: **a swap must never choose a camera.**

**What it refuses to fake.** It emits a REVIEW PACKET, not a verdict: the old entity's
self-description, the new one's, and every beat. The question is "does this sentence
still describe the old place", which is a semantic judgment. Two heuristics were tried
on the real case and both failed the same way. Sweeping the old entity's contract
words buried the two true hits (`counter`, `stool`) under `jerry`, `toby`, `gold` and
`brand`, which come from character names, scale prose and NEGATIONS the entity states
about itself ("no brand marks"). Subtracting the new entity's vocabulary cleared those
and left `whole`, `conversation`, `showing`, `question`: `prose.rules` is discursive
English and furniture nouns are a tiny subset of it. **A sweep a human learns to ignore
is worse than no sweep.**

So the packet goes to a reader. This follows `judge-slot`: the judgment is a ROLE, not
a service. Fill it with a subagent, a fresh session, a human, or the next turn.

**Why this matters more than it sounds.** The five beats that shipped wrong (a bowl, a
spoon, a counter tapped twice, a stool turned on, a bowl pushed across a counter) sat
under finished paintings of a bench and two cones, and `book-doctor`'s caption-drift
check correctly reported all seventy-three captions verbatim. It compares the spec to
the story, and both were stale. **An entity swap is a MANUSCRIPT event.** Re-run
`voice-gate` on every beat you rewrite, then re-sync captions with `compose-spec`.

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
