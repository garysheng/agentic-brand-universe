---
name: start-new-story-universe
description: Stand up a brand-new story universe on the Agentic Story framework — a typed, git-versioned canon with a load-bearing pre-render gate, conforming to a named spec version. Interview the creator, scaffold via `agenticstory init`, seed the first canon (entities/relations/first story), wire the gate, and hand back a universe that validates green and refuses to render until real references exist. Use when the operator says "start a new story universe", "spin up a universe for X", "/start-new-story-universe", "I want a canon/story world for Y", or is about to build the first book/property of a NEW world (not a new book in an existing one). One-time generation, not for ongoing canon edits.
---

# Start New Story Universe

Birth a new **universe** on the Agentic Story framework. A universe is the first-class
object: a typed, git-versioned canon (entities + relations), with stories as compositions
over it, references made load-bearing (their absence is a crash, not a drift), and quality
wired as gates rather than remembered. This skill does the one-time generation; ongoing
work is normal canon commits plus a renderer skill (e.g. `create-brand-os-picture-book`).

> **What this is NOT:** a new *book* inside an existing universe. If the world already
> exists (e.g. Nation of Fire), do not scaffold a second universe — add to canon and use
> the book renderer. This skill is only for a genuinely NEW world with its own canon repo.

## Canonical source (read before executing)

The framework spec is the source of truth for every field contract and invariant. Read it,
do not re-derive it:

- **Spec:** `agenticstory/SPEC.md` (the repo this skill lives in) — canonical home `https://agenticstory.wiki`.
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
repo home (default: a new top-level repo `~/Documents/github-repos/<universe>/` with a
`universe/` canon dir inside, mirroring `nation-of-fire/universe`). One repo per universe
(SPEC §8) — do not add to a shared multi-universe store.

### Phase 1 — Interview (one question at a time)
Gather only what canon needs to begin. Do not over-ask; the universe grows by making stories.
- **Name** (slug) and one-line premise of the world.
- **Asset root** — where reference art/voice files will live relative to the canon dir
  (default `.`; for a multi-repo world like NoF, `..` so sibling property repos resolve).
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
python3 -m agenticstory.cli init <repo>/universe --name <slug> [--asset-root ..] [--example]
```
- Use `--example` for the operator's first-ever universe (drops a worked
  character/setting/story/relation so the shape is obvious); omit it once they know the shape.
- This writes `universe.json` (with spec provenance), `canon/{entities,relations}/`,
  `stories/`, a `canon/README.md`, and the load-bearing gate `canon/scripts/assert.sh`.
- The command prints a `validate → OK`. If it is not OK, stop and fix before seeding canon.

### Phase 3 — Seed the first canon
Translate the interview into typed records (SPEC §4 is the field contract; copy the shapes,
do not invent fields). Minimum viable first canon:
- **Entities:** the first property's protagonist(s)/setting/visual-metaphor. A renderer-consumed
  entity needs `structured.sheets` + `requiredForRender`; a setting/visual-metaphor needs a
  `status` + `contract` and stays **unlocked** (correctly refused) until its turnaround +
  empty plates + blueprint + map/blocking/dressing exist.
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
- `universe.json` names the **spec version** and the canonical wiki (provenance present).
- `validate` is GREEN; the first story is registered (stub or full).
- The load-bearing gate is wired and demonstrably refuses on a missing/unlocked reference.
- Real-subject properties are gated until blessed; no real person's private detail in canon.
- The scaffold does not bake in any single property's specifics — those live in that
  property's own surfaces, not in canon-wide files.

## When NOT to invoke
- A new book/property in an **existing** universe → add canon + run the renderer, not this.
- Ongoing canon edits → normal commits against the canon repo.
- A flat marketing site, a wiki, or a one-off illustration → wrong shape (see `start-new-wiki`
  for a wiki; the picture-book skills for a single book).

## Reference implementation
**Nation of Fire** (`nation-of-fire/universe`) is the proof this works: ~24 properties, a
typed canon, the load-bearing gate, and a real dogfood (*Not Every Fire Is Holy*, whose
arena setting was correctly *refused* until locked). Use it as the worked example of a filled
universe — but never copy its property-specific rules into a fresh universe's canon.
