---
name: render-book
description: Render a story from an Agentic Story universe into a picture book. Wraps the universal create-brand-os-picture-book pipeline and adds the universe layer from DATA: the story's spine + genre (craft-canon records), the universe's register (identity.register style anchor, passed first on every render), the mark (identity.mark), canon resolved via canon-resolve, text checked by voice-gate, every render checked by render-readback. Generic and universe-parameterized: pass the target universe + story id.
---

# Render Book

Turn a validated `StorySpec` into an illustrated, narrated picture book. This skill is the universe layer over `create-brand-os-picture-book`, which owns the mechanics (manuscript staging, verified art batches, narration, reader delivery). Nothing here is universe-specific: every fact that makes the book look and sound like ITS universe (the mark, the register, the arc discipline, the world's laws) comes from that universe's `identity` block and its `canon/craft/` records, never from this file.

## Inputs
- The target universe (a path with `universe.json`).
- The story id (`stories/<id>.json`, written by `add-story`).

## Procedure

1. **Load the universe + story.** Read `identity` (`register.anchor`, `register.rejectedPoles`, `mark`, `closingOrnament`, `voice`) and `stories/<id>.json` (its `spine`, `features`, `beats`, and any per-story `register` override). If `identity.register.anchor` is null, STOP: the universe's style is not locked; point the operator at the style-lock step and do not render.

2. **Read the craft.** Load the story's declared `spine` craft record and its `genre` craft record from `canon/craft/` (`python3 -m agenticstory.cli list-craft <universe>`), plus any `register-rule` records the universe has discovered. These carry the arc discipline the story must satisfy, the book-type's own format canon (a primer reads differently than a testimony; an expectant biography and a visualized epistle have different closing shapes), and the universe-wide laws every render must honor. A universe with no `canon/craft/` records has none to honor; proceed on the story's declared `spine` alone.

   **RESOLVE THE DECLARED `spine` AND `genre` AGAINST `list-craft` BEFORE RENDERING, and STOP if either does not exist.** A story can declare a genre that reads perfectly and matches no record, in which case that record's rules are silently never applied and nothing errors. Worked failure: a book declared `prophetic-biography`, which is not a registered record. The real record was `faithful-prophetic-realistic-fiction`, and it is the one that EXPLICITLY SUPERSEDES the `testimony-over-prediction` register-rule; unresolved, the superseded rule would have governed and forced the book's whole declared-future act back into "imagine, one day" hedging, inverting what the book was for. Fix the story's `genre` to a real record id and record why in `aimDiscipline`.

   **When two records conflict, find the supersession and write down which one wins.** Craft records are not independent: a genre record may explicitly retire a register-rule it contradicts. Read both, decide, and state the resolution in `aimDiscipline` so the next reader sees a ruling instead of apparent drift.

3. **Words before art (gate).** Draft or confirm the manuscript against the story's `beats` (each beat's `provenance` traces to a real source; an unsourced vivid detail does not ship). Run `voice-gate` on the full manuscript. Do not proceed to art until the words are blessed (`gates.wordsBlessed`) and voice-clean. For a `realPerson` entity in the cast, the subject's confusion-flags and likeness approval count the same as the author's, and no spread renders until they bless it (`identity.subjectApproval`).

4. **Per spread: resolve, generate, read back.** For each beat/spread:
   a. Run `canon-resolve` on the spread's cast + location. It resolves each entity's locked reference paths and invariants and runs `assert-spread` (a non-zero exit blocks the render; fix the missing lock before proceeding, never render around it).

   **SELECT EACH CAST ENTITY'S POSE/LOOK FOR THE BEAT'S MOMENT IN THAT CHARACTER'S OWN TIMELINE.** An entity with `render.poses` or `structured.altLooks` has a DEFAULT that is silently applied whenever a spread descriptor omits one, and that default is usually the character's resolved, post-arc self. So any beat set during their valley, their before, or their childhood renders them as already healed. Nothing errors and the plate looks fine. Worked failure: a character rendered in the wardrobe his canon ties to life AFTER his deliverance, on the beat depicting his own psychiatric emergency, when that same canon named the valley-era look explicitly. That is a doctrinal error about a real person, not a wardrobe nit. Sweep every cast entity that HAS poses and ask which era each beat sits in; a book spanning a character's arc needs different poses for the same character across its spreads.
   b. Generate via `create-brand-os-picture-book`'s mechanics, passing `identity.register.anchor` FIRST, baking `identity.register.rejectedPoles` plus the honored `register-rule` records as negatives, and honoring the genre record's format canon (panel count, caption placement, closing shape).
   c. Run `render-readback` on the render: crop-zoom every in-frame entity's invariants. Any DEFECT means regenerate the image FROM SCRATCH, never an edit pass.

5. **Close + write back.** Apply the universe's closing: stamp `identity.mark` (the "made in this universe" byline) in the back matter, and use `identity.closingOrnament` on the final plate if the universe has one. On completion, propose the story's `writesBack` (any new/updated canon the finished book earned, e.g. an entity that graduated from `stub` to `locked`, a new crossover) for the author to accept before committing.

## Gates honored
- **Words-before-art + voice-gate:** no spread renders until the manuscript is blessed and voice-clean.
- **Canon-resolve before every prompt:** no render prompt is written except from a resolved entity record.
- **Register-anchor-first:** every generation leads with `identity.register.anchor`.
- **Read-back after every render:** any DEFECT regenerates from scratch.
- **Spine + genre + register-rules honored:** the story is checked against its own declared spine, its genre's format canon, and the universe's discovered laws.
- **Subject-approval:** a real person in the cast blesses words and likeness before any spread featuring them renders.

## Not this skill
- Authoring a new entity named in a beat → the matching `add-*` skill.
- Locking an entity's reference matrix → `shoot-references`.
- Rendering the cover → `cover`.
- Editing an already-built book → `update-book`.
- Shipping the finished book to a shared platform → the platform-delivery skill (deferred).

## Proportion is a render-time check too

Before rendering, count the beats spent on the problem versus the beats spent on the answer, and in an expectant or prophetic story count how many beats live in the declared future. A story that spends thirty beats diagnosing and one declaring has hedged by proportion, whatever its wording says. Rendering is the LAST cheap moment to catch that: every beat added afterwards renumbers the render-spec, the manuscript, the platform manifest, the staged assets and the narration. Send it back to `add-story` rather than rendering an unbalanced book.
