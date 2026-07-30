---
name: add-setting
description: Add ONE setting (a location) to an Agentic Story universe (interview its fixed geometry, fixed camera angles, and dressing, reuse-first via casting sweep, then scaffold a typed `setting` entity with SPEC §12's contract slots (turnaround, per-angle empty plates, blueprint, plus map/blocking/dressing descriptor prose) and ready-to-run generation prompts). Stays `status: unlocked` (correctly refused by the render gate) until `shoot-references` fills the plates and you lock it. Art is NOT generated here. Use when a story needs to render into a location. Generic and universe-parameterized: pass the target universe.
---

# Add Setting

One location, into a universe's canon, as a typed record with its contract scaffolded. This is authoring, not art: it ends with a validated `unlocked` entity + ready-to-run prompts. `shoot-references` generates and locks the plates afterward.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and `assetRoot`.
- What the place is and which story needs it.

## Procedure

1. **Casting sweep first (reuse wins).** Before naming a new setting, sweep `canon/entities/` + any CANON.md for an existing location that already fits (a universe rarely needs two versions of "the kitchen"). Only proceed if genuinely new.
2. **Interview (one question at a time).** Gather only what the contract needs.
   - **What the place is:** its function in the story, its mood, who owns or frequents it.
   - **Cameras.** Decide the FIXED vantage points a book will actually shoot from (typically C1 + C2: e.g. wide establishing, and one closer working angle). More cameras cost more locked plates; pick the minimum the story needs.
   - **FIXED geometry.** The walls, furniture positions, doors, and sightlines that must never drift render to render (this is what "locked" buys you: continuity).
   - **Dressing.** The props, materials, and colors that make the place recognizable at a glance.
   - **SIZE, IN HUMAN TERMS. Ask this explicitly and never skip it.** How wide is the room, how high is the ceiling, how big is the fireplace opening, how many people fit? A setting that never states its size gets whatever size the model guesses, and every render inherits that guess forever (see the scale gap below). Write the answer into `contract.scale` as plain measurements a person can picture: "a circular hall about 80 feet across, dome 45 feet at the crown, the fire opening about 12 feet wide."
   - **BUILDABILITY.** Ask how each major feature is actually held up or vented. A free-standing firepit under a conical flue suspended from a dome shipped through a whole book before anyone noticed nothing was holding the cone. Anything structural that a plate would not have to explain is exactly where the physics quietly fails.
3. **Scaffold the entity (tested machinery).** From the engine dir:
   ```bash
   python3 -m agenticstory.cli add-entity <universe> setting <id> --name "<Name>" [--origin <first-story>]
   ```
   This writes `canon/entities/<id>.json` with `status: "unlocked"` and a `contract` whose fields (`turnaround`, `emptyPlates`, `blueprint`, `scalePlate`, `map`, `blocking`, `dressing`, `scale`) are all null/empty. It prints `lock_level: stub`.
4. **Fill the descriptor prose.** Edit `contract.map` (the spatial layout in words), `contract.blocking` (where characters can stand/move without breaking geometry), `contract.dressing` (the recognizable materials/props/palette), and `contract.scale` (the size in human measurements, from the interview). These three are load-bearing text, not flavor: the resolver requires them non-empty, and every render of this setting passes them in the prompt. Also fill `prose.rules` for any never-render constraint.
5. **BUILD THE BLUEPRINT IN CODE, not with the image model** (see below). It is the seed the rest of the matrix inherits, and it is free.
6. **Write the generation prompts.** Create `reference/<id>/prompts.md`: one block per contract file slot, a `turnaround`, one `emptyPlate` per fixed camera (C1, C2, ...), and a **`scalePlate`** (see below). The `blueprint` is NOT prompted; step 5 already drew it. Each prompt: (a) passes `identity.register.anchor` FIRST and bakes `register.rejectedPoles` as negatives; (b) **passes the blueprint from step 5 as a layout reference**; (c) restates the FIXED geometry from step 2 so every plate agrees with every other; (d) names the target output path `reference/<id>/<shot>.png`. These are what `shoot-references` will run.
7. **Validate + commit.** `agenticstory validate <universe>` stays green (an `unlocked` setting still validates: that is a correct, expected state, not an error). Commit the entity + reference dir + prompts.md. Report `lock_level: stub` and that the setting stays refused by `assert-story`/`assert-spread` until `shoot-references` fills every plate and flips `status` to `"locked"`.

### The blueprint is a 3D MASSING RENDER, drawn in code (SPEC v0.15)

**Do not prompt an image model for the blueprint, and do not settle for a top-down plan.** Run:

```bash
python3 -m agenticstory.cli massing <spec.json> --out <universe>/reference/<id>/blueprint.png \
    --universe <universe> --entity <id>
```

You declare the room once as boxes and quads with the cameras named, and the engine renders **the actual perspective each locked camera will see**. It is deterministic, costs nothing, needs no key, and writes its own `.recipe.json`.

**Why a plan was not good enough.** The blueprint seeds every empty plate, every spread and every re-render. A plan view makes the image model *infer* the perspective, and inference is exactly where geometry drifts: rooms change proportion between angles, furniture migrates, and **handedness silently flips**, so "the bookshelf wall is C1-LEFT" stops being true in half the book. A massing render hands the model a picture to match against a picture. It also forces you to commit to real numbers at authoring time, which is when a wrong room is still cheap.

Keep it **crude on purpose**: flat blocks, ink edges, no textures, no materials. A blueprint that looks like finished art invites the model to copy its surface; one that obviously reads as scaffolding gets used as scaffolding. The sheet self-stamps `LAYOUT REFERENCE ONLY, NEVER PAINTED`, and every consumer still passes the standard blueprint guard.

Spec shape (full reference in `engine/agenticstory/massing.py`):

```jsonc
{ "title": "THE LONG ROOM",
  "subtitle": "3D MASSING SEED / CAMERAS C1 + C2 LOCKED",
  "solids": [ {"type":"box","min":[0,0,0],"max":[9,4,3.1],"color":[214,206,192],
               "faces":["bottom","front","back"]} ],
  "cameras": [ {"id":"c1","caption":"C1 MASTER - from the door","eye":[0.5,2,1.65],
                "target":[9,2,1.3],"fov":62,
                "labels":[{"at":[1.4,3.9,2.3],"text":"BOOKSHELF WALL = C1-LEFT","screen":[28,40]}]} ],
  "notes": [ {"text":"THE ONE CHAIR FACES THE WINDOW. Never reversed.","tone":"rule"} ] }
```

Commit the spec JSON beside the entity. It is the editable source; the PNG is the artifact. Changing a room later is a re-run, not a re-draw.

**Applies to `visual-metaphor` too** whenever the object has fixed geometry across states: seed the state chain on the code-drawn blueprint, never on a sibling state plate, or parallel state renders come back as different objects.

### An empty plate cannot prove its own size (SPEC v0.9)

`emptyPlates` are people-free on purpose, so a setting reference never bakes a character's face into a room. That rule is right and it stays. But it has a cost that went unpriced for months: **a figure-free interior carries no unit of comparison.** The model picks a size, every render inherits the guess, and nobody can catch it, because the plate does not depict the dimension being judged. A hearth room rendered small and cramped through an entire 25-spread book before its owner said "that room is supposed to be much bigger than that."

So every setting gets ONE extra plate whose only job is size:

- **`contract.scalePlate`** — the same room with **ANONYMOUS SCALE FIGURES**: a few people, small in frame, at a distance, turned away or in profile, faces not readable, plain clothing, **never a canon character and never the subject**. That satisfies the identity rule (no face is baked) while making size checkable at a glance.
- It is a **separate file from `emptyPlates`, never a replacement.** Renders still cast an empty plate; the scale plate is what a human and `lint-universe` read the room's size from.
- **`contract.scale`** carries the same fact in words, and is passed in every prompt like `dressing`, because **prose survives a re-render and a plate does not.**

`lint-universe` warns `SETTING-NO-SCALE-PLATE` / `SETTING-NO-SCALE-DESCRIPTOR`. Both are advisory: a setting with no scale plate still locks and still renders.

## Gates honored
- **Reuse-first** (step 1): never invent a second version of a location an existing entity already covers.
- **Unlocked-until-plated**: a `null` contract field (or a missing descriptor) is a hard refusal from `resolve_setting`/`assert_story`. Never hand-edit `status` to `"locked"` without the real plates behind it; that refusal is the load-bearing feature, not a bug to route around.
- **No art here**: generation is `shoot-references`, so this skill never calls an image model.

## Not this skill
- Generating/locking the plates and flipping `status` to `locked` → `shoot-references`.
- A character, visual-metaphor, motif, prop, story, or relation → the sibling `add-*` skills.

## Shoot the SHOT LIST at creation, not one master plate

A character gets a reference matrix at creation: eight shots, made before anything
renders, so no later beat has to invent a view of them. **A setting needs the same
thing and for the same reason.** A close-up cannot inherit what the wide plate does
not show, so every framing you did not shoot up front gets re-invented at render
time, differently on every spread.

So before locking, ask what cameras this place will actually be asked for across the
property, and shoot each one as an EMPTY plate:

- **wide establishing** — the canonical view, the one that fixes the geometry
- **conversational distance** — the two-shot/close plate, with the far parts of the
  room OUT of frame entirely
- **reverse** — looking back the other way, if any beat needs it
- **a plate per recurring camera the story genuinely uses** (a doorway, a table, a
  specific corner)
- plus the non-camera plates: `blueprint`, `turnaround`, `scalePlate`

Name them in `structured.sheets` so the compiler can pass them; a plate that exists
on disk but is not in `sheets` can never be sent, and the rule naming it survives
only as words.

**Scope each plate to what it contains.** A close-up is not a wide shot with a
tighter crop: it does not contain the seating, the far wall or the crowd, and being
told about them is what makes the model paint them anyway. Declare that in
`contract.plates`:

```json
"plates": {
  "master":       { "note": "The wide establishing view. Use for arrival and departure." },
  "chairsCloseUp": { "includeBlocking": false,
                     "note": "Only the two chairs and the table are in frame. No tiers, no audience." }
}
```

`includeBlocking: false` drops the room-wide blocking law for that plate, which is
exactly what a close-up needs. Earned 2026-07-30: one wide master was locked and
twelve teaching beats were then asked for at conversational distance; the audience
drifted every spread until a dedicated close plate was shot and scoped.

`lint-universe` warns with `SETTING-HAS-NO-SHOT-LIST` when a setting locks with
fewer than two camera plates.

## Set dressing goes in the PLATE, never in the cast

A recurring crowd, a congregation, a market, a classroom of children: these are scenery,
and scenery re-described per spread is re-invented per spread. Sixteen guests described
in prose came back as sixteen different people in different seats on every render of one
evening.

The instinct is to model them as a cast (a group entity, a lineup sheet, a seat roster).
**That is cast machinery and it is far too much for scenery.** Set dressing is made
consistent the same way the furniture is: **bake it into a populated plate.**

So a setting's shot list may carry BOTH states of the same camera:

- `fromTheChairs` — the empty plate, which fixes the geometry
- `fromTheChairsFull` — the *same camera* with the crowd already seated in it

Scope the populated plate so a scene may say which ONE person is speaking, or what the
faces are doing, and nothing else about them. One image cannot drift.

Reach for a real entity only when a member of the crowd must be recognised BY NAME across
books. Otherwise the plate is the answer, and it is one render instead of a cast.

Earned 2026-07-30, nation-of-fire: "they are mostly just setting ornaments, just need to
make sure there is consistency of shots."
