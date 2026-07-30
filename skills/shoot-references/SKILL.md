---
name: shoot-references
description: SHOOT an entity's reference matrix in an Agentic Brand Universe: make the art that gives a scaffolded entity a body. For each empty or DEFECT matrix slot it GENERATES the shot from the entity's `reference/<id>/prompts.md` (passing `identity.register.anchor` first, plus the photo stack for a real person and any already-shot slots for identity consistency), reads it back against the entity's invariants, and locks the passers with provenance via `abu lock-shot`. Locking is the last of the three steps, not the point of them. Idempotent, so re-runs only shoot what is still missing. Use after `add-character`/`add-setting`/`add-prop`/`add-motif`/`add-visual-metaphor` has scaffolded an entity and you want to SEE it: "shoot the references", "make the art for X", "generate X's sheets", "give X its body", "lock X's matrix", "X is still unlocked". Renamed from `lock-references` on 2026-07-26 because that named the bookkeeping instead of the work.
---

# Shoot References

Turn a scaffolded entity's empty matrix slots into locked reference shots. This is the ART step, and it does three things in order: **shoot, read back, lock.** `add-character` (and siblings) leave an entity at `lock_level: stub` with a `prompts.md` and no pictures; this skill gives it a body, then locks what passes, until the entity is `locked` (or at least `partial`, once its required shots pass).

> **Why the name changed (2026-07-26).** This was `lock-references`, which named only the third step. Agents reaching for "make the art for this character" did not find it, because locking sounds like a metadata operation on art that already exists. The unit the engine works in is already a **shot** (`abu lock-shot`), and the production verb for making shots is **shoot**. Old references to `lock-references` in shipped universe files are historical and were deliberately left alone.

## Inputs
- The target universe (a path with `universe.json`) and the entity id.
- Read `identity.register` (anchor + rejectedPoles). If `register.anchor` is null, STOP: the universe's style is not locked. Point the operator at the start-universe style-lock step and do not generate.

### Multi-register universes: `--register <pack-id>`

`identity.register` is the right anchor for a universe with ONE look. It is the wrong one for a universe where `identity.register` names only the **default** and each look is its own Style Pack under `reference/style/<id>/` (`gary-sheng-art` is the reference case). There, an entity whose story declares a different register would have its whole matrix shot in a medium it is never rendered in, and a sheet in the wrong medium is a weaker identity reference than one in the right medium.

So `chain_matrix.py` takes `--register <pack-id>`: it resolves `reference/style/<pack-id>/pack.json`, uses that pack's anchor and its `rejectedPoles`, and **does not** merge the default register's poles (a pack that permits what the default rejects would otherwise be fighting a negative it never declared). It refuses loudly on an unknown pack or an anchor that is not on disk, rather than falling back to the default and quietly shooting the wrong look. Omit the flag and behaviour is exactly as before.

Check which register a story declares before shooting its cast: `stories/<id>.json` may carry its own `register` block that overrides the universe default.

## Procedure
1. **Resolve the work.** Read `canon/entities/<id>.json` (its kind, matrix, invariants, and for a real person the `realPerson` photo stack + sensitive list) and `reference/<id>/prompts.md`. Run `abu lock-level <universe> <id>` to see what remains.
2. **For each shot that is missing or was a DEFECT** (skip already-locked passers, so re-runs are cheap):
   a. **Generate** via the `chatgpt-images` skill (gpt-image-2): pass `identity.register.anchor` as the FIRST input image; bake `register.rejectedPoles` as negatives; for a real person pass the photo stack (build from real photos, never a painting-of-a-painting) and honor the sensitive list; pass any already-locked shots of this entity so the face/build stays consistent; use the shot's prompt block from `prompts.md`. Write to `reference/<id>/<shot>.png`.
   b. **Read back** with `render-readback`: crop-zoom each of the entity's invariants, PASS/DEFECT. On any DEFECT, regenerate that shot FROM SCRATCH (never an edit pass), naming the defect as an explicit negative.
   c. **Write the shot's recipe.** Alongside the art, write `reference/<id>/<shot>.recipe.json` capturing what produced it: `{"provider": "gpt-image-2", "prompt": "<the exact prompt sent>", "specVersion": "<universe spec.version>", "refs": [{"path": "<each input image, universe-relative>"}]}`. This is the same recipe shape `compose` emits. Provenance is not optional: a golden locked without it is un-auditable and can never enter a divergence check.
   d. **Lock the passer WITH its recipe:** `python3 -m agenticstory.cli lock-shot <universe> <id> <shot> reference/<id>/<shot>.png --recipe reference/<id>/<shot>.recipe.json`. This sets the sheet path, promotes `requiredForRender` as the required shots lock, and freezes provenance at approval (the golden's own bytes plus each input's bytes now), so `lint-universe` can later tell you if the golden drifts from what Gary blessed.
3. **Verify + commit.** `abu validate <universe>` stays green. `lock-level` should reach `partial` once the required shots pass and `locked` once the full matrix passes. Commit the generated art + the updated entity JSON.

## Locking a DECLARED-FUTURE era look (SPEC v0.10)

An `altLooks.era-<year>` entry declares a body the entity does not have today. Its art
does NOT belong in the default matrix, so lock it into the look:

```bash
python3 -m agenticstory.cli lock-shot <universe> <id> forward-fullbody \
  reference/<id>/era-2030/forward-fullbody.png --look era-2030 \
  --recipe reference/<id>/era-2030/forward-fullbody.recipe.json
```

Two things differ from an ordinary shot, and both are load-bearing:

1. **Generate it from the FACE, never from the body.** Pass the register anchor first, then
   the entity's locked FACE sheets and (for a real person) the photo stack. Do NOT pass
   `forward-fullbody`: that is the present-day silhouette this look supersedes, and a
   reference image outranks a word, so passing it drags the old body into the new one.
2. **`--look` never touches `requiredForRender`.** That is the default look's gate. An era
   plate must not be able to satisfy it.

Read back against the ERA's own invariants (`altLooks.<key>.invariants` plus the base
invariants it does not supersede), not against today's.

## Fill `prompts.md`. Never write the prompt into a throwaway script.

`add-entity` scaffolds every shot body as `TODO(author): replace each body below`.
**Filling those bodies is part of casting, not an optional extra**, and `chain_matrix.py`
now REFUSES to shoot while the marker is still present.

The refusal exists because of a specific, expensive failure (2026-07-30): faced with a
stub, an agent wrote its prompts inline in five throwaway bash scripts and called the
provider directly. The tool it needed already existed and already did chaining, the
register, and `--skip-existing`. Routing around it was simply easier than noticing the
authoring step had been skipped.

A prompt in `prompts.md` is versioned, reviewable, diffable, and reused on every re-run.
The same prompt in `/tmp/shoot-thing.sh` is gone when the session ends, which means the
next run cannot reproduce the shot and the entity's own art has no recorded intent.

So: write the shot bodies into `prompts.md` first, then shoot with `chain_matrix.py`. If a
shot needs something the file cannot express, fix the file format, not the workflow.

## A multi-state object: the blueprint holds the OBJECT, not the FRAMING

Seeding every state off one code-drawn blueprint is the right rule and it is not enough.
Earned 2026-07-30 on `the-book-of-your-days`, twice in a row.

The blueprint fixes what the object IS. It does not fix how the camera sees it, so two
states seeded off the same blueprint came back with different cover proportions and read as
two different books. For a thin state and a thick state of one book, that is fatal: the
whole argument is that it is the SAME life, and it got fuller.

So for any object whose states must read as one object:

- **Pin the shared dimensions as NUMBERS in every state's prompt**, not just in the
  blueprint. "The cover is a portrait rectangle exactly 1.4 times as tall as it is wide, and
  it fills the same footprint in this frame regardless of how many pages are inside."
- **Say what changes and what does not, in the same sentence.** "Only the thickness of the
  page block changes."
- **Put it on the ENTITY as an invariant**, so read-back can catch it and so the next state
  anyone adds inherits it:
  `every-state-shares-identical-cover-height-and-width-only-thickness-changes`.
- If a later state still drifts, **chain it off the state that already passed** rather than
  off the blueprint, so it inherits a cover that has been blessed.

The general form: a blueprint constrains geometry, a prompt constrains framing, and a state
set needs both pinned or the states are siblings rather than the same thing twice.

## SHOW THE OPERATOR EVERY SHOT. This is a GATE, not a courtesy.

**No shot locks until the human has actually seen it.** Reading an image back yourself is
QA, not delivery. The two are different and conflating them is the failure this rule exists
to stop: an agent can crop-zoom forty renders, pass every invariant, lock them all, and the
person who commissioned the book has seen nothing.

**`open-in-preview` alone does NOT count as delivery.** It opens macOS Preview on one
machine. Half the time the operator is remote, on a phone, or in another session, so
"opened 10 images" reports success for something they cannot see. Earned 2026-07-30, when
Gary asked directly why images were not reaching him after this exact pattern.

So, every time art is generated:

1. **Send the files to the operator** with the harness's own file-delivery tool, which
   reaches them wherever they are. This is the delivery that counts.
2. **Also open them locally** if they are at that machine. Convenience, not the mechanism.
3. **Say what each one is and which are decisions**, so a batch is scannable rather than a
   wall of pictures.

A batch of four or more goes as ONE contact sheet plus individual files for anything being
approved. `render-readback/scripts/contact_sheet.py` already builds the sheet and already
refuses a partial one, so a short sheet cannot read as "everything I rendered".

The tell that this is being skipped: a session that generated a dozen images and whose
transcript contains no delivery, only `Read` calls the agent made to itself.

## Gates honored
- **Register-first:** every generation leads with the universe style anchor; no anchor means stop.
  The register is ALSO named positively, in words, at the head of every shot's prompt (`style_line`),
  because the anchor image plus the rejected poles as bare negatives does not hold the medium on its
  own. A scaffolded `prompts.md` states the register in its HEADER, which the parser never sent, so
  four character seeds in a row came back photoreal in a universe that explicitly rejects photoreal
  and whose anchor is a painting (2026-07-30, The Lord Saw). It is sourced from `universe.json`, not
  from the markdown, so a `prompts.md` that forgets to mention it still gets it.
- **Read-back:** no shot locks without passing every invariant; DEFECT means regenerate from scratch.
- **Subject-approval:** a real person stays `realPerson.approval.state: "gated"` after art. This skill NEVER flips it to "approved"; that is the subject's own blessing, recorded separately.
- **Sensitivity:** the sensitive list is honored on every real-person render.
- **Idempotent:** locked passers are never regenerated.

## Not this skill
- Authoring the entity or its prompts (that is the `add-*` skills).
- Rendering a story's spreads (that is a renderer).
