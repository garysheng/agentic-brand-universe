---
name: start-new-story-universe
description: Stand up a brand-new story universe on the Agentic Brand Universe framework — a typed, git-versioned canon with a load-bearing pre-render gate, conforming to a named spec version. Interview the creator, scaffold via `abu init`, seed the first canon (entities/relations/first story), wire the gate, and hand back a universe that validates green and refuses to render until real references exist. Use when the operator says "start a new story universe", "spin up a universe for X", "/start-new-story-universe", "I want a canon/story world for Y", or is about to build the first book/property of a NEW world (not a new book in an existing one). One-time generation, not for ongoing canon edits.
---

# Start New Story Universe

Birth a new **universe** on the Agentic Brand Universe framework. A universe is the first-class
object: a typed, git-versioned canon (entities + relations), with stories as works
over it, references made load-bearing (their absence is a crash, not a drift), and quality
wired as gates rather than remembered. This skill does the one-time generation; ongoing
work is normal canon commits plus a renderer skill (e.g. `create-brand-os-picture-book`).

> **What this is NOT:** a new *book* inside an existing universe. If the world already
> exists (e.g. Nation of Fire), do not scaffold a second universe — add to canon and use
> the book renderer. This skill is only for a genuinely NEW world with its own canon repo.

## Canonical source (read before executing)

The framework spec is the source of truth for every field contract and invariant. Read it,
do not re-derive it:

- **Spec:** `agenticstory/SPEC.md` (the repo this skill lives in) — canonical home `https://agenticbranduniverse.com`.
- **Engine:** `agenticstory/engine/` — the scaffolder + validator + gate. Run its CLI; do
  not hand-write universe files the engine can generate and check.

Every universe this skill creates records, in its `universe.json` `spec` block, exactly
which spec **version** it conforms to and the wiki that defines it — provenance, like a
`BOOMERANG.md` `conforms_to`. Never scaffold a universe that does not name its spec version.

## The six bets you are honoring (from SPEC §2)

1. **Universe-first** — the evolving canon is primary; a work is a projection that writes back.
2. **Canon is medium-neutral** — entities carry no medium; a renderer is a separate, pluggable layer.
3. **References are load-bearing** — every asset resolves to a real file or the build fails loudly.
4. **Quality = taste × craft × truth** — human taste gates, encoded craft-canon, and per-beat provenance.
5. **Evolution is version control** — every canon change is a commit; contradictions are diffs.
6. **Agent-writable by construction** — everything is validated structured data or prose in a known slot.

## The recipe

### Phase 0 — Route & confirm scope
Confirm this is a NEW world, not a new property in an old one. If the operator names an
existing universe, stop and redirect to that universe's canon + renderer. Pick the canon
repo home (default: a new top-level repo `<universe>/` beside your other repos (ask where they keep projects; never assume) with a
`universe/` canon dir inside, mirroring `nation-of-fire/nof-universe`). One repo per universe
(SPEC §8) — do not add to a shared multi-universe store.

### Phase 1 — Interview (one question at a time)
Gather only what canon needs to begin. Do not over-ask; the universe grows by making stories.
- **Name** (slug) and one-line premise of the world.
- **Asset root** — leave it `.` (the default). Every asset lives INSIDE this universe repo
  (SPEC §3a self-containment). Do NOT set it to `..` to reach sibling property repos — that is
  the scatter the framework exists to kill (the Nation of Fire canon started that way and had to
  be consolidated back in). A universe you can clone as one folder, whose refs all resolve, is the
  guarantee. Properties keep their own spread art / narration; the universe owns the canonical
  refs (character sheets, setting plates, reference photos) under its own root.
- **Identity** — the constants this universe is known by, written into `universe.json` `identity`
  (SPEC §11): its `mark` (the "made in this universe" byline), a `platformUniverseId` if it will
  ship to a shared platform, a `theme` (brand token set), a `closingOrnament` if it has a recurring
  closing motif, and `voice` term rules (words to capitalize / keep one-word for the voice gate).
  These are DATA the generic framework skills read — never hardcode them into a skill.
  Also set `identity.register`: the universe's illustrative **style** (default **"detailed comic
  book"**), which the renderer passes as a style anchor on every render. Note any `rejectedPoles`
  (styles to bake as negatives, e.g. photoreal, anime, washed-out).
- **The first property** — its working title, its **spine** (the arc invariant it must
  satisfy: `obedient-servant | thesis | primer | testimony | …`; NOT assumed to be a
  hero-journey — SPEC finding 1), and whether it is carried by a character, a **setting**,
  or a **visual-metaphor** (finding 2).
- **Any real people** as subjects — if yes, each becomes a `character` with a `realPerson`
  dossier (photo stack, approval gate, sensitive list — finding 4) and the property stays
  gated until the subject blesses it.

### Phase 2 — Scaffold (tested machinery, not hand-authoring)
From the engine dir (`agenticstory/engine`):
```bash
python3 -m agenticstory.cli init <repo>/<slug>-universe --name <slug> [--example]
```
- Use `--example` for the operator's first-ever universe (drops a worked
  character/setting/story/relation so the shape is obvious); omit it once they know the shape.
- This writes `universe.json` (with spec provenance + a stub `identity` block + the
  self-containment note), `canon/{entities,relations}/`, `stories/`, a `canon/README.md`, and the
  load-bearing gate `canon/scripts/assert.sh`. Name the repo folder `<slug>-universe` (not the
  generic `universe`), so it stands on its own.
- **Fill the `identity` block** with the values gathered in Phase 1 (mark, theme, voice terms,
  etc.). Leave `assetRoot` at `.`.
- **Style-lock (register anchor).** The scaffold sets `register.name` (default "detailed comic
  book") with `register.anchor: null`. Lock the anchor before rendering: generate a content-neutral
  style swatch in that named style (no universe characters, just palette + line + finish), get the
  operator's "that's the look" approval, save it to `reference/register/style-anchor.png`, and set
  `identity.register.anchor` to that path. Until locked, renderers warn and fall back to wording.
- Do NOT scaffold or fork any per-universe skill. The operations (ref resolution, casting sweep,
  entity register, render read-back, voice gate, the renderer) are **framework skills** the
  universe inherits, parameterized by this universe's path + `identity` (SPEC §11). A universe
  ships data, not skill code.
- The command prints a `validate → OK`. If it is not OK, stop and fix before seeding canon.

### Phase 3 — Seed the first canon
Translate the interview into typed records (SPEC §4 is the field contract; copy the shapes,
do not invent fields). Minimum viable first canon:
- **Entities:** the first property's protagonist(s)/setting/visual-metaphor. A renderer-consumed
  entity needs `structured.sheets` + `requiredForRender`; a setting/visual-metaphor needs a
  `status` + `contract` and stays **unlocked** (correctly refused) until its turnaround +
  empty plates + blueprint + map/blocking/dressing exist.
  A renderer-consumed entity is complete when its **reference matrix** (SPEC §12) is locked: for a
  character, the ~8-shot set (face-neutral/3q/expressions, forward-fullbody, profile L+R, back,
  signature-pose); for a setting, its contract plates; for a visual-metaphor, its states. Use
  `abu lock-level <universe> <entity>` to see stub/partial/locked. Authoring a new entity
  is the job of the `add-*` framework skills (they scaffold the matrix slots + prompts).
- **Relations:** any known `appears-in` / `crossover-with` / `derived-from` edges.
- **First story:** one `stories/<id>.json`. Register it as `status: "stub"` (spine + logline
  only) if beats are not written yet; promote to `"full"` (features + beats + per-beat
  provenance + register) when it is real.
- Run `validate` after each addition; keep it green.

### Phase 4 — Wire quality gates (surface, don't automate away)
The gates are load-bearing on purpose (SPEC §3.5). Establish, for this universe:
- **Taste gates** — the human "that's it / that's not it" moments the renderer must stop at
  (words-before-art, register lock, face lock, subject approval). Name them; do not skip them.
- **Craft-canon** — the world's enforceable invariants (its spine shapes, its refrain rule,
  "awe not horror", palette laws). Encode discovered rules as they are earned — craft is
  discovered then encoded (SPEC §5), never assumed up front.
- **Provenance** — every full-story beat cites a real source. Unsourced vivid detail is a flag.

### Phase 5 — Version, verify, hand off
- `git init` in the new repo; first commit is the scaffold + first canon (the diff is the
  changelog; every later canon mutation is a commit — SPEC §5).
- Verify: `validate` green; `assert-story <first-story>` behaves correctly (green if assets
  exist, or a clear refusal naming exactly what is missing — that refusal is the feature).
- Hand off: the renderer (`create-brand-os-picture-book` / a universe-specific layer) calls
  `canon/scripts/assert.sh spread|story …` before drawing any unit. No renderer may generate
  a unit whose assert has not passed.

## Definition of done
- A new one-repo universe exists, `git init`'d, first commit made.
- `universe.json` names the **spec version** and the canonical wiki (provenance present), and its
  **`identity` block is filled** (mark, theme, voice terms, etc. — SPEC §11).
- **Self-contained (SPEC §3a):** `assetRoot` is `.` and every referenced asset lives inside the
  repo. You could clone this folder alone and every ref would resolve. No ref points at a sibling
  folder or another repo.
- `identity.register` is set (default "detailed comic book") and its **style anchor is locked**
  (`reference/register/style-anchor.png` exists, `register.anchor` points at it).
- `validate` is GREEN; the first story is registered (stub or full).
- The load-bearing gate is wired and demonstrably refuses on a missing/unlocked reference.
- Real-subject properties are gated until blessed; no real person's private detail in canon.
- **No per-universe skill code was created** — the universe inherits framework skills and ships
  only data (canon, assets, identity, craft-canon).
- The scaffold does not bake in any single property's specifics — those live in that
  property's own surfaces, not in canon-wide files.

## When NOT to invoke
- A new book/property in an **existing** universe → add canon + run the renderer, not this.
- Ongoing canon edits → normal commits against the canon repo.
- A flat marketing site, a wiki, or a one-off illustration → wrong shape (see `start-new-wiki`
  for a wiki; the picture-book skills for a single book).

## Reference implementation
**Nation of Fire** (`nation-of-fire/nof-universe`) is the proof this works: ~24 properties, a
typed canon, the load-bearing gate, and a real dogfood (*Not Every Fire Is Holy*, whose
arena setting was correctly *refused* until locked). Use it as the worked example of a filled
universe — but never copy its property-specific rules into a fresh universe's canon.
