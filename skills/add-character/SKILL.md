---
name: add-character
description: Add ONE character to an Agentic Brand Universe: interview the source (a real person's story/wardrobe/sensitive-list, or a fictional design brief), reuse-first via casting sweep, then scaffold a typed `character` entity with the SPEC §12 reference-matrix slots (8 shots) and a ready-to-run generation prompt per shot. Real people get a photo stack and a subject-approval gate; art is NOT generated here (that is `shoot-references`). Use when adding a person/character to a universe. Generic and universe-parameterized: pass the target universe.
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
4c. **Is this character a PHOTOREAL IDENTITY MASTER? Declare `structured.registerNeutral` (SPEC v0.37 §12).** The tell: the brand wants one hyper-realistic version of a real person and then register-specific variations DERIVED from it, rather than a character drawn in the universe's register. Declare `{"medium": "...", "why": "..."}` and the matrix is shot with NO anchor at all: no anchor image, no register style line, no register poles, and `--register` / `--no-style-pack` are refused. Do this BEFORE `shoot-references`, and do it even when the universe has no blessed register yet, because that is exactly the case it unblocks: the master cannot wait for the register, since the register renditions are made from the master. Give each sheet slot a `role` too (`{"path": ..., "role": "identity"}`; never `medium`), so a plate cast into a stylised render is told to contribute its likeness and not its medium.
5. **Write the generation prompts.** `prompts.md` holds MATRIX SHOTS ONLY. A shot's body runs until the NEXT `## ` heading, so any appendix, sub-heading, or horizontal rule after the last shot is silently appended to that shot's prompt and corrupts its art. Alt-look/era shots go in a SEPARATE file (`prompts-era.md`); they lock with `lock-shot --look <key>` and are never base-matrix shots. `chain_matrix.py` refuses this, but write it right the first time. (Earned 2026-07-26: four era sections kept at `###` after the last shot produced a 4397-character prompt and a 3x3 contact sheet that leaked a child, a superseded era wardrobe, and a banned pendant shape into a base plate.)

   Create `reference/<id>/prompts.md`: one block per matrix shot (face-neutral, face-3q, expressions, forward-fullbody, profile-left, profile-right, back, signature-pose). Each prompt: (a) passes `identity.register.anchor` FIRST as the style anchor and bakes `register.rejectedPoles` as negatives; (b) for a real person, passes the photo stack (build from photos, never a painting-of-a-painting); (c) states the shot's angle + the entity's invariants; (d) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
6. **Validate + commit.** `abu validate <universe>` stays green. Commit the entity + reference dir + prompts.md. Report the `lock_level` (stub) and that the next step is `shoot-references <universe> <id>`.
   - **An unshot entity carries `requiredForRender: []`.** The scaffolder writes it empty for a reason: naming a required slot whose sheet is still `null` makes `validate` report a problem per slot. Record the intended set in a note and let `shoot-references` populate the real thing when it locks.
   - **Check for a concurrent writer before step 3's scaffold, not here.** `git status` + `git branch --show-current` first. Dirty with work you did not do means a live writer: author in a worktree, `git add <exact paths> && git commit` as ONE command, never `git add -A`, never rebase or switch branches under an in-flight render. See `add-story` step 5 for the full rule and the two incidents behind it.
   - **Never invent a real person's measurements.** Absolute height, weight, and age are facts, and an entity is read as canon by every later render. Write only what the author supplied, mark the rest `NOT ON RECORD`, and carry the claim in `scale.relativeTo` where a comparison is all you actually know.
   - **A public figure's PRIVATE FAMILY does not inherit their public-figure status.** Whatever a universe's real-people law permits for a public person covers that person, not their mother, father, spouse, or children, who are private individuals and usually have no photo stack and no public record. Naming them in the words is fine. Rendering a verified likeness of the public figure BESIDE invented family faces is not: the real face authenticates the invented ones, so the frame reads as a documentary claim about how those private people actually look. The fix is compositional, not a disclaimer. Name the public figure in the caption and keep them OUT of frame, rendering the family as deliberately archetypal; or render the public figure alone. This applies even where the universe has abolished every blessing and approval gate, because it is about not asserting a falsehood about someone, which no consent rule reaches.

## Gates honored
- **Reuse-first** (step 1): never invent a character an existing entity already covers.
- **Subject-approval**: a real person is `gated`; no property featuring them renders until they bless the words and art (enforced downstream; never bypass).
- **Sensitivity**: the sensitive list is populated before any art; private detail never ships.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the shots → `shoot-references`.
- A setting, prop, motif, story, or relation → the sibling `add-*` skills.

## Pin the WARDROBE to a capsule sheet, not to an adjective

A character's clothes drift for exactly the reason their face does not: the face is
pinned to a sheet the compiler passes, and the clothes are usually a phrase. "Refined
modern-chic wardrobe in cream and gold" is a colour with an adjective attached, and the
model invents a different cream garment on every render while satisfying canon perfectly.
Over a 20-spread book that is 20 different shirts.

Earned 2026-07-30 (nation-of-fire, `selah`): her three poses were NECKLACE and CALLING
states, not outfits, and all three passed only face sheets. `jerry-man` had had the right
shape all along and nobody had generalised it. `lint-universe` then found **123** unpinned
characters in that one universe; he was the only one pinned to anything.

So for any character who RECURS:

1. **Shoot a wardrobe capsule sheet.** One study sheet, 4 figures of the SAME character
   standing in a row against a neutral ground, each in a different complete outfit drawn
   from their canon palette and modesty rules. Register it in `structured.sheets`.
2. **Add one pose per look**, each naming its figure and PASSING the capsule:
   ```json
   "ql-shirt-trousers": {
     "sheets": ["quietLuxuryCapsule", "goldenPath", "faceTruth"],
     "bake": "WARDROBE, matching FIGURE 1 FROM THE LEFT on the supplied capsule reference
              sheet and no other figure on it: <the outfit, concretely>. The capsule is a
              multi-figure STUDY SHEET: take the CLOTHING from it, never its layout."
   }
   ```
3. **A book then selects a look once** and it holds across every spread.

**The pose's `sheets` list is what makes this real.** A bake that says "matching the
supplied capsule sheet" while listing only `face` passes no capsule at all, and the rule
survives as words. That exact defect sat in all eight of `jerry-man`'s `ql-*` poses.

**State modesty and any body rule as ANATOMY, not adjectives.** "Covenant-modest" does not
survive a render; "neckline high and closed at or above the collarbone, buttoned to the
second button, no cleavage at any scale, sleeves at least to the elbow" does. Same lesson
as an "undefended face" needing brow, eyes and mouth spelled out.

`lint-universe` warns `CHARACTER-WARDROBE-NOT-PINNED` when a recurring character has no
wardrobe sheet and no pose passing one.
