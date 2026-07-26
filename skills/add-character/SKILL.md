---
name: add-character
description: Add ONE character to an Agentic Story universe: interview the source (a real person's story/wardrobe/sensitive-list, or a fictional design brief), reuse-first via casting sweep, then scaffold a typed `character` entity with the SPEC §12 reference-matrix slots (8 shots) and a ready-to-run generation prompt per shot. Real people get a photo stack and a subject-approval gate; art is NOT generated here (that is `shoot-references`). Use when adding a person/character to a universe. Generic and universe-parameterized: pass the target universe.
---

# Add Character

One character, into a universe's canon, as a typed record with its reference matrix scaffolded. This is authoring, not art: it ends with a validated `stub` entity + ready-to-run prompts. `shoot-references` generates and locks the shots afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- Whether the character is a REAL living person (triggers the dossier + gate) or FICTIONAL.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new character, sweep `canon/entities/` + any CANON.md for an existing entity that fits the role. If one fits, STOP and reuse it (a reuse is a crossover receipt, and it saves the whole matrix build). Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what canon needs.
   - **Real person:** their name; the role they play in this universe; their story/voice; wardrobe eras (default + any activity-specific, e.g. no street clothes while running); signature physical invariants (glasses, a scar, a pendant); and the **sensitive list** (the private details that must NEVER ship). Collect a **photo stack** (aim for 8+ varied real photos: front, 3/4, profile, full-body, candids) into `reference/<id>/photos/`. Never invent or store details the subject did not authorize.
   - **Fictional:** a design brief: look, silhouette, palette, signature invariants, voice. No photo stack; no gate.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> character <id> --name "<Name>" \
     [--origin <first-story>] [--photo reference/<id>/photos/01.jpg --photo ...]
   ```
   This writes `canon/entities/<id>.json` with the 8 matrix slots (null), `requiredForRender: []`, and (for a real person with photos) a `gated` `realPerson` block. It prints `lock_level: stub`.
4. **Fill the prose + invariants.** Edit the entity's `prose` (voice/lore/rules) and `structured.invariants` (the load-bearing identity rules the read-back will check, e.g. `no-lenses`, `double-eyelid-crease`). For a real person, fill `realPerson.wardrobeEras` and confirm `sensitiveList` points at the universe `RESEARCH.md#sensitive` entry you populated.
4a. **State the scale if this character ever shares a frame (SPEC v0.10).** Fill `structured.scale`: `height` in human terms, and `relativeTo` mapping other entity ids to a phrase (`{"russ-vibes-apostle": "several inches shorter than"}`). Every entity is described ALONE, so without this two people in one frame come out the same height or reversed, and nobody catches it until someone who knows them does. **Record the inverse on the other character in the same pass** or `lint-universe` warns `CHARACTER-SCALE-ONE-SIDED`, because two half-records drift apart and then contradict each other.
4b. **A DECLARED-FUTURE (prophetic) look is an `altLooks` entry, never a second entity (SPEC v0.10).** When a universe permits expectant work and a story renders someone's blessed future, add `structured.altLooks.era-<year>` with its own `invariants` (the declared body) and `supersedes` (the present-day invariants it retires). The trap: an ordinary alt look changes the FACE and carries its own `anchorPhoto`, so base face sheets are auto-dropped, but **a future look inverts that** (the face is continuous, the body changes, and the future has no photograph). Set **`keepSheets`** (the base face sheet) and/or **`keepPhotos: true`**, or only body sheets reach the model, which are the very silhouette you are superseding, and it renders a stranger with the right build. `compose-spread` refuses this at compile time and `lint-universe` warns `LOOK-NO-IDENTITY-ANCHOR`. Give each era its own reference shots under `reference/<id>/era-<year>/` so the read-back checks the future body against what was declared.
5. **Write the generation prompts.** Create `reference/<id>/prompts.md`: one block per matrix shot (face-neutral, face-3q, expressions, forward-fullbody, profile-left, profile-right, back, signature-pose). Each prompt: (a) passes `identity.register.anchor` FIRST as the style anchor and bakes `register.rejectedPoles` as negatives; (b) for a real person, passes the photo stack (build from photos, never a painting-of-a-painting); (c) states the shot's angle + the entity's invariants; (d) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
6. **Validate + commit.** `agenticstory validate <universe>` stays green. Commit the entity + reference dir + prompts.md. Report the `lock_level` (stub) and that the next step is `shoot-references <universe> <id>`.

## Gates honored
- **Reuse-first** (step 1): never invent a character an existing entity already covers.
- **Subject-approval**: a real person is `gated`; no property featuring them renders until they bless the words and art (enforced downstream; never bypass).
- **Sensitivity**: the sensitive list is populated before any art; private detail never ships.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the shots → `shoot-references`.
- A setting, prop, motif, story, or relation → the sibling `add-*` skills.
