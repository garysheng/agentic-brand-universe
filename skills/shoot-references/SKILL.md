---
name: shoot-references
description: SHOOT an entity's reference matrix in an Agentic Brand Universe: make the art that gives a scaffolded entity a body. For each empty or DEFECT matrix slot it GENERATES the shot from the entity's `reference/<id>/prompts.md` (passing `identity.register.anchor` first, plus the photo stack for a real person and any already-shot slots for identity consistency), reads it back against the entity's invariants, and locks the passers with provenance via `abu lock-shot`. Locking is the last of the three steps, not the point of them. Idempotent, so re-runs only shoot what is still missing. Use after `add-character`/`add-setting`/`add-prop`/`add-motif`/`add-visual-metaphor` has scaffolded an entity and you want to SEE it: "shoot the references", "make the art for X", "generate X's sheets", "give X its body", "lock X's matrix", "X is still unlocked". Renamed from `lock-references` on 2026-07-26 because that named the bookkeeping instead of the work.
---

# Shoot References

Turn a scaffolded entity's empty matrix slots into locked reference shots. This is the ART step, and it does three things in order: **shoot, read back, lock.** `add-character` (and siblings) leave an entity at `lock_level: stub` with a `prompts.md` and no pictures; this skill gives it a body, then locks what passes, until the entity is `locked` (or at least `partial`, once its required shots pass).

> **Why the name changed (2026-07-26).** This was `lock-references`, which named only the third step. Agents reaching for "make the art for this character" did not find it, because locking sounds like a metadata operation on art that already exists. The unit the engine works in is already a **shot** (`abu lock-shot`), and the production verb for making shots is **shoot**. Old references to `lock-references` in shipped universe files are historical and were deliberately left alone.

## Inputs
- The target universe (a path with `universe.json`) and the entity id.
- Read `identity.register` (anchor + rejectedPoles). If `register.anchor` is null, STOP: the universe's style is not locked. Point the operator at the start-universe style-lock step and do not generate. **Unless the entity declares `structured.registerNeutral`** — see below.
- **Read `identity.register.stylePack` too, and read the notes beside it.** A universe that declares a pack usually declares it BECAUSE its inline anchor misbehaved, and the note says how.

### A declared `stylePack` is not a decoration (v0.33)

A reference shoot is the sparsest render there is: one subject, no scene, and often nothing in frame but the style anchor. That is exactly where an anchor's own SUBJECT comes back wholesale instead of leaking subtly. So if the register declares a Style Pack, `chain_matrix.py` will not quietly shoot against the inline anchor:

| register declares | the shoot uses |
|---|---|
| `stylePack`, no inline `anchor` | the PACK (SPEC §4.7 full mode) |
| `anchor` only | the inline anchor, exactly as before |
| BOTH | **REFUSES at plan time** — answer with `--register <id-or-path>` or `--no-style-pack` |

Earned 2026-08-04 in nation-of-fire, which declares both. Its own `stylePackNote` records two renders that came back as the anchor's oil lamp and clay jar; the shoot that afternoon made a third, a seed that returned fully PHOTOREAL, that register's top rejected pole. Passing `--register nof-soft-painterly` was right on the first re-shot. The refusal is free and fires before any generation; a wrong seed is a paid image, and a blessed wrong seed is a whole matrix.

**Before answering the refusal, read the register's `anchorNote` / `stylePackNote`.** A universe that wrote one has usually already recorded which anchor leaked, when, and into what.

### The identity master: a matrix shot in NO register (v0.37)

One case legitimately owes the register nothing: a **photoreal identity master**, from
which every register rendition is later DERIVED. A real person's digital twin is the case
this exists for. It cannot wait for a blessed register, because it is the thing the
register conversions are made FROM, and a master shot inside a register can only ever
serve that register.

Declare it ON THE ENTITY, never at the command line:

```json
"structured": { "registerNeutral": {
    "medium": "hyper-realistic documentary photography",
    "why": "one photoreal master; every register is a conversion of it" } }
```

Then `chain_matrix.py` shoots with **no anchor at all**: no anchor image, no register
style line (the `medium` leads instead), no register poles as negatives, and a recipe that
records `registerNeutral` beside a null `anchor` so the absence is a statement rather than
an omission. `--register` and `--no-style-pack` are **REFUSED** here: both name WHICH
anchor to pass, and the answer is none.

Two things to hold onto:

- **It is canon and not a flag on purpose.** A flag cannot refuse a re-shoot it is not
  passed. Once the universe finally blesses a register, an in-register re-shoot would bake
  that register into the one asset whose job is to be medium-free, and a plate cannot be
  un-baked.
- **Shoot the RENDITIONS from the master, never from the photographs again.** Two
  independent shoots of one subject produce two subjects. Renditions live beside the master
  (`reference/<id>/renditions/<register-id>/`) with a recipe naming the master plate.

At render time `compose-spread` emits one line per register-neutral cast entry telling the
model to take likeness and geometry from those plates and no medium. Give each slot a
`role` too (`identity` / `geometry` / `garment` / `scale`, never `medium`), which says the
same thing per plate; `lint-universe` warns `REGISTER-NEUTRAL-UNTYPED-SLOT` if you do not.

### Multi-register universes: `--register <pack-id>`

`identity.register` is the right anchor for a universe with ONE look. It is the wrong one for a universe where `identity.register` names only the **default** and each look is its own Style Pack under `reference/style/<id>/` (`gary-sheng-art` is the reference case). There, an entity whose story declares a different register would have its whole matrix shot in a medium it is never rendered in, and a sheet in the wrong medium is a weaker identity reference than one in the right medium.

So `chain_matrix.py` takes `--register <pack-id>`: it resolves `reference/style/<pack-id>/pack.json`, uses that pack's anchor and its `rejectedPoles`, and **does not** merge the default register's poles (a pack that permits what the default rejects would otherwise be fighting a negative it never declared). It refuses loudly on an unknown pack or an anchor that is not on disk, rather than falling back to the default and quietly shooting the wrong look. Omit the flag and behaviour is exactly as before.

Check which register a story declares before shooting its cast: `stories/<id>.json` may carry its own `register` block that overrides the universe default.

## Procedure
1. **Resolve the work.** Read `canon/entities/<id>.json` (its kind, matrix, invariants, and for a real person the `realPerson` photo stack + sensitive list) and `reference/<id>/prompts.md`. Run `abu lock-level <universe> <id>` to see what remains.
2. **For each shot that is missing or was a DEFECT** (skip already-locked passers, so re-runs are cheap):
   a. **Generate** via the `chatgpt-images` skill (gpt-image-2): pass `identity.register.anchor` as the FIRST input image; bake `register.rejectedPoles` as negatives; for a real person pass the photo stack (build from real photos, never a painting-of-a-painting) and honor the sensitive list; pass any already-locked shots of this entity so the face/build stays consistent; use the shot's prompt block from `prompts.md`. Write to `reference/<id>/<shot>.png`.
   b. **Read back** with `render-readback`: crop-zoom each of the entity's invariants, PASS/DEFECT. On any DEFECT, regenerate that shot FROM SCRATCH (never an edit pass), naming the defect as an explicit negative.
   c. **The shot's recipe is `reference/<id>/<shot>.png.recipe.json`** — ONE sidecar per asset, at the engine-wide `<asset>.recipe.json` name. The provider adapter writes it on every render and `chain_matrix` merges its conditioning metadata (photo stack, goldens conditioned on, cross-entity refs, method) into that same file. Never write a second `<shot>.recipe.json` beside it: two sidecars for one asset can diverge, and did (2026-08-02). Provenance is not optional: a golden locked without it is un-auditable and can never enter a divergence check.
   d. **Lock the passer WITH its recipe:** `python3 -m agenticstory.cli lock-shot <universe> <id> <shot> reference/<id>/<shot>.png --recipe reference/<id>/<shot>.png.recipe.json`. This sets the sheet path, promotes `requiredForRender` as the required shots lock, and freezes provenance at approval (the golden's own bytes plus each input's bytes now), so `lint-universe` can later tell you if the golden drifts from what Gary blessed.
3. **Verify + commit.** `abu validate <universe>` stays green. `lock-level` should reach `partial` once the required shots pass and `locked` once the full matrix passes. Commit the generated art + the updated entity JSON.

## Locking a DECLARED-FUTURE era look (SPEC v0.10)

An `altLooks.era-<year>` entry declares a body the entity does not have today. Its art
does NOT belong in the default matrix, so lock it into the look:

```bash
python3 -m agenticstory.cli lock-shot <universe> <id> forward-fullbody \
  reference/<id>/era-2030/forward-fullbody.png --look era-2030 \
  --recipe reference/<id>/era-2030/forward-fullbody.png.recipe.json
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

## The photo stack: point at the FOLDER, and import into it with `abu import-asset`

`realPerson.photoStack` may name files or a DIRECTORY, and the directory
(`["reference/<id>/photos"]`) is the idiomatic form: it expands to the sorted images inside
it, and `realPerson.photoLimit` caps the result AFTER expansion. Both halves of the
framework now read that one rule (SPEC v0.21); before that this script refused a directory,
so the recommended form rendered fine and could not be shot from.

**A photograph or blessed render that comes from OUTSIDE the universe is installed with
`abu import-asset`, never copied by hand.** The copy writes the `.recipe.json` for you, the
same way generating does:

```bash
python3 -m agenticstory.cli import-asset <universe> --manifest <manifest.json> \
  --dest-dir reference/<id>/photos --prompts <source-prompts.json>
```

Use `--provenance source` for an original photograph and the default `derived` for a crop
or transform of a known asset, where `derivedFrom` + `transform` + `sourcePrompt` carry the
chain. Hand-writing a recipe beside a copied file is provenance saved by memory, which is
the thing the adapter exists to abolish.

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

**DO NOT TYPE THE FIRST DRAFT. COMPOSE IT FROM THE ENTITY:**

```bash
python3 scripts/compose_prompts.py <universe> <entity-id> --all            # every sheet key
python3 scripts/compose_prompts.py <universe> <entity-id> queen=queen:1024x1536
```

It builds each body out of the entity's own strings: `structured.render.always` becomes
WHO, the selected pose's `bake` becomes POSE, and `structured.invariants` become the
binding rules, verbatim. That is the point, and it is not about saving typing. A
hand-typed prompt paraphrases the invariants slightly, and read-back then checks the art
against the OTHER wording; a composed prompt cannot diverge from the rule it will be
judged by, because it is the same string. It never touches a body that already exists (a
human's words always win), it is idempotent, and it refuses on an unknown sheet, an
unknown pose, a missing `render.always` or an entity with no invariants rather than
guessing.

Then READ what it wrote before shooting. Every sentence came from canon, so a sentence
that is wrong in the prompt is wrong in the entity, and the entity is where you fix it.

This is the complement of `backfill_prompts.py` below: compose is for an entity with no
art yet, backfill is for art that already exists. Neither invents.

## Cross-entity refs: name the SHEETS when the required set is not the right set

A shot body declares the other canon entities it shows, so they are conditioned on their
locked art instead of redrawn from prose:

```
**Refs (every shot):** north-star-cross          # header, every shot
REFS: north-star-cross                           # in a shot body, that shot only
REFS: north-star-cross@turnaround+worn-pendant   # v0.25: name the sheets
```

A bare id passes that entity's `requiredForRender` set. `@sheet+sheet` passes the named
sheets FIRST and `requiredForRender` still follows, so **a selector can only ADD**. That is
deliberate: the field that lets you say more must not become a way to skip a plate the
entity's own gate demands.

Reach for the selector when the required set is not the set THIS shot needs. Typical cases:
an in-situ or worn plate that is only correct in some renders, a material variant, or a
multi-angle turnaround. Read the referenced entity's `structured.render.always` first, which
is where an author records "pass X first, and Y when it is worn."

A selector naming a sheet the entity does not declare refuses. `--print-plan` resolves the
refs and prints the sheet names it will pass, on the seed shot too, so a typo is caught for
free instead of mid-render.

Earned 2026-08-01 on christofuturism's `north-star-cross`, whose fabrication spec says in as
many words to prefer the multi-angle turnaround because a single flat front view gets
flattened back into an equilateral star. The turnaround was registered, provenanced and named
by the entity's own render rule, and no shot could reach it; three flat plates were all that
resolved, and the pendant rendered at 1.79:1 against a spec of 1.24:1.

## A multi-state object: seed on the blueprint, and use `--star`

Two flags carry the pattern SPEC §12 prescribes, so you never hand-build it again:

```bash
python3 skills/shoot-references/scripts/chain_matrix.py <universe> <entity> --star --print-plan
```

- **A code-drawn blueprint is found and passed automatically.** If `reference/<id>/blueprint.png`
  exists and its `.recipe.json` names a deterministic generator (`abu elevation` / `abu massing`,
  or any `deterministic` generator with no `model`), the chain will NOT generate it and WILL pass
  it as conditioning to every shot in the matrix. You do not add `REFS: <id>@blueprint` to each
  section and you do not pre-declare `structured.sheets.blueprint`. Ask for it explicitly with
  `--shots blueprint` or `--seed blueprint` and the chain refuses rather than overwriting it.
- **`--star` when the shots are STATES rather than angles.** Every non-seed shot then conditions on
  the blessed seed plus the blueprint, and on no sibling. Reach for it the moment two states differ
  in lighting, weather, season, or the presence of something — a cold night plate and a warm-gold
  noon plate chained serially walk the night into the noon, and a negative cannot undo a reference
  image. Do NOT use it for a character's angle matrix, where cumulative chaining is the point.

`--print-plan` prints the topology and every code-drawn input on every line, so both decisions are
checkable for free before anything is spent.

### The blueprint holds the OBJECT, not the FRAMING

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
  off the blueprint, so it inherits a cover that has been blessed. This is the one case that
  wants a sibling, so drop `--star` for that shot alone
  (`--shots <blessed-state>,<drifting-state> --skip-existing`) rather than for the matrix.

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

## The photographs decide the SHOOTING ORDER, and the order is load-bearing

`keepSheets` / `keepPhotos` are documented above for a DECLARED FUTURE, and the section
heading has misled people, so state it plainly: **the mechanism is temporal-direction-agnostic.**
It serves any era the photo stack does not cover, past as readily as future. There is no
photograph of Kenneth E. Hagin bedfast at fifteen in 1933, and the only photographs that
exist are of him in his eighties, so on that entity BOTH un-photographed eras are in the past.

The default assumption is that the default look is shot from the photo stack and every era
chains off it. When the photographs cover a NON-default era, **shoot the era that has ground
truth FIRST and chain the others off it.** On `kenneth-hagin` that runs fully inverted:
`elder` from the two public photographs, the default young look chained off `elder`, and
`bedfast` chained off the young look. Shooting the three in parallel from prose returns three
different men who merely share a description, which is exactly the failure the golden chain
exists to prevent. A look whose photographs ARE its ground truth declares its own
`anchorPhoto` / `photoStack`, which outranks the base face sheets by design.

## Repairing an entity whose prompts.md was never filled

`chain_matrix.py` refuses to shoot while a body says `TODO(author)`, which is right. For art
that already got made some other way that refusal is PERMANENT: nobody can add one more angle
without re-authoring every prompt, and the prompts are sitting in each plate's `.recipe.json`.

```bash
python3 scripts/backfill_prompts.py <universe> [entity-id ...] [--dry-run] [--strip REGEX]
```

It fills a TODO body from the plate's recipe, ADOPTS a locked plate that has no section at
all (an entity's real matrix drifts from its scaffold), and strips what the shooter re-adds so
the next run does not double it. Three things it will not do, and each was earned:

- **Never overwrite an authored body.** A human's words always win.
- **Never invent.** A plausible reconstruction would look like provenance while being fiction,
  which is worse than an admitted gap.
- **Never accept a prompt that is itself a `TODO` stub.** `abu backfill-provenance` recovers a
  recipe by reading prompts.md, so where that file was a stub it faithfully recorded the stub.
  Writing it back would satisfy every checker and launder the gap into something that looks
  like provenance. The two recovery tools would otherwise chase each other in a circle.

**It also SCAFFOLDS a `prompts.md` for an entity that has none (2026-08-02).** That is the
commonest state of any entity older than the scaffolder, and it used to be a dead end: this tool
walks the files that EXIST, `chain_matrix.py` refuses to shoot without one, and `add-entity` writes
one only for entities it creates, so three correct behaviours summed to a locked, actively-cast
character that could not be re-shot. `--entity <id>` on such an entity exited 2. The scaffold
invents nothing: headings come from the entity's own declared slots and every body stays
`TODO(author)` until a recipe fills it or a human writes it. `--dry-run` names it and writes
nothing.

It never touches a code-built blueprint: a massing render carries `"prompt": null` by design,
because its provenance is a declarative spec plus deterministic code, which is better than a
prompt.

Applied to nation-of-fire 2026-07-31: 74 detector findings to 5, and the five that remain are
honestly unrecoverable and say so.

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
