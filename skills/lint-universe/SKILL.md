---
name: lint-universe
description: Lint a brand universe. Static checks over the universe and everything it declares (style packs, entities, goldens, provenance, craft canon, provider quirks) with no generation, no API calls, and no cost. Catches the failure classes that were previously only discovered by rendering, sometimes an hour into one. Run it before rendering anything.
---

# Brand Universe Linter

`python3 scripts/lint.py <universe-dir>`

Exit **0** clean, **1** warnings only, **2** errors.

## Why this exists

Every check here corresponds to a failure that actually shipped and was only caught by rendering.
Canon can be internally valid, reviewed by two people, and still impossible to put in a picture. The
linter moves those discoveries to the cheapest possible moment.

An entity can be fully locked, fully art-approved, pass `validate` AND pass `assert-story`, and still
be uncastable, because the render compiler reads `structured.render` while every other gate reads
sheets and files. It surfaced as a hard `KeyError` at cast time, after the story was written. That
class is now static and free.

## What it checks

**Universe.** `universe.json` parses. `identity.register.anchor` is set and resolves. A null anchor
means the style is not locked and generation should refuse.

**The spec pin.** `spec.version` is declared (error if absent: an unpinned universe conforms to nothing
anyone can check, and cannot detect its own drift), and it matches the engine's `SPEC_VERSION` (warns
if the universe is behind). This catches the class where three surfaces each give a consistent but
different answer: on 2026-07-24 `SPEC.md` said v0.6, the engine constant said 0.4.1, and the reference
universe pinned 0.5, and every one was internally consistent. Consistency is not truth; the pin is now
verified against the engine rather than trusted.

**Story types are data, not prose.** Every story declares a `spine` (arc invariant) and an optional
`genre` (book type). The SPEC (§13) says these are craft-canon records (`canon/craft/*.json`, kinds
`spine` | `genre`), so "where are this universe's story types?" is answerable by listing them. The linter
ties each story back to that registry: a declared `spine`, or a non-null `genre`, that is not a
registered craft record is a warning (`STORY-SPINE-UNREGISTERED`, `STORY-GENRE-UNREGISTERED`). This
catches the drift that used to pass silently: a typo (`expectant-biograhpy`), a near-duplicate
(`teaching-testimony` vs `testimony-teaching`), or free-text prose stuffed into the genre field
(`testimony (Jerry-voiced ...)`). The fix a warning points at is one JSON file: register the value as a
craft record (which makes the mode discoverable data) or correct the value. It is a WARNING, not an
error, so a universe mid-normalization still validates and renders.

**Style packs.** `pack.json` parses; the anchor and every ref resolve on disk; a `gate` exists, because
a pack without one is a mood board; `styleLine` exists. Warns under three refs.

**Goldens.** Every sheet named in an entity's `requiredForRender` resolves to a file
(`GOLDEN-UNDECLARED`, `GOLDEN-MISSING`). And every LOCKED sheet, required or not, carries a
`<golden>.recipe.json` provenance sidecar:
- `GOLDEN-NO-RECIPE` (warn): the approval recorded only a path, so nothing can say what it was
  approved against. It is un-auditable and cannot enter a divergence check. Re-lock with
  `lock-shot --recipe`.
- `GOLDEN-STALE` / `GOLDEN-INPUT-GONE` (warn): the sidecar recorded each input's bytes at approval;
  one of them has since changed or vanished. The golden was blessed against an input that no longer
  exists, and no human is looking. This is the free half of the divergence loop: the whole approved
  corpus audited statically at zero cost.

A golden is Gary's approved answer of record. These checks make the golden library an auditable eval
set rather than a pile of images with no memory of how they were judged.

**A setting's contract belongs to the PLACE, not to one book** (`SETTING-DRESSING-NAMES-HELD-PROP`,
warn). `contract.dressing` is injected into every prompt that casts the setting and
`contract.blockingPlate` is passed as a reference image on every one of those renders, in every book
that reuses it. So a prop written into either leaks forever: `the-park-bench` said "Each of them
holds an ice cream cone" and its plate showed two mannequins holding cones, and three of the first
seven spreads of an unrelated book came back with both men holding ice cream **through a per-spread
negative that banned ice cream by name**. A reference image plus an injected contract sentence
outrank a negative word. The detector requires a person and a held object in the SAME sentence and
still lets some noise through; that is the right trade for a warning, since the version tuned until
it was silent on everything questionable was also silent on the entity that earned it.

**`locked` must mean what the render gate means** (`SETTING-LOCKED-BUT-GATE-REFUSES`, warn). The
promoter and the gate disagreed until v0.29, so the only way to lock some settings was to hand-edit
the JSON, and a hand-flip cannot be checked by the tool it bypassed. Both now call one predicate;
this reports canon whose recorded status the gate contradicts (six entities in nation-of-fire, all
predating the fix).

**An entity guarded only by `render.qa`** (`ENTITY-QA-WITHOUT-INVARIANTS`, warn). `render.qa` reaches
the read-back checklist from v0.29, but `structured.invariants` is what the identity bake guard,
auto-disambiguation, `supersedes` and `judge-slot` all read, so an entity with a populated `render.qa`
and an empty `invariants` is guarded in one place out of five.

**Quirks.** The provider registry parses, and a pinned provider that the registry has never heard of is
flagged, because it will silently inherit no quirks.

## Where it belongs

Before any render, always. It is free, it is instant, and the alternative is finding the same problem
after paying for generation.
