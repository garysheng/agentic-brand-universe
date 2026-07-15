# Agentic Story — Framework Spec

**v0.1 — 2026-07-15.** The first-principles architecture for compelling, agentically writable,
composable, evolvable story generation. Home: `agenticstory.wiki`. Reference implementation: the
Nation of Fire universe.

> **Thesis, in one line:** *A story is a query over an evolving canon, rendered into a medium, held
> to craft and to human taste.*

---

## 1. Why this exists

We have built ~15 illustrated books inside one shared universe (Nation of Fire). Each was strong, but
the *system* underneath was implicit and re-remembered every time: canon lived in prose, reference
art scattered across four different path conventions, craft rules survived as skill-file scar tissue,
and quality depended on the author holding it all in his head. The books were composable and
evolvable in spirit but not in mechanism — so the same failures recurred book after book (settings
that drift, references that silently go missing, beats that can't be traced to anything real).

Agentic Story makes the implicit system explicit: a small set of primitives and invariants that make
a narrative **universe** the first-class object, stories **compositions** over it, references
**load-bearing** (their absence is a crash, not a drift), and quality a set of **wired gates** rather
than a memory feat. It is designed to be written and evolved primarily **by agents**, with the human
in the loop exactly where taste is irreducible.

## 2. First principles (the bets)

1. **Universe-first.** The evolving canon is primary. A single work is a projection of it, and writes
   back into it. Composability and evolvability are then native, not bolted on.
2. **Canon is medium-neutral.** Canon entities carry no medium assumptions. Rendering into a medium
   (picture book, novel, script, comic, game bible) is a separate, pluggable layer. Ship one renderer
   first; add others without touching canon.
3. **References are load-bearing.** Every canon entity that has an asset (a character sheet, a setting
   plate, a voice sample) resolves to a real file or the build **fails loudly**. A reference you can
   forget is not a reference; it is a wish.
4. **Quality = taste × craft × truth.** Compelling output comes from three wired sources, never from
   the generator alone: (a) **human taste gates** at the irreducible moments; (b) **craft-canon** —
   narrative craft encoded as enforceable invariants; (c) **provenance** — beats grounded in real
   source material. All three are first-class, not optional passes.
5. **Evolution is version control.** Canon changes over time. Git is the evolution substrate: every
   canon mutation is a commit; contradictions are visible diffs; "what did the universe know on date
   X" is answerable. No bespoke versioning.
6. **Agent-writable by construction.** Every artifact is either structured data an agent can validate
   against a schema, or prose in a known slot. Nothing load-bearing lives only in a human's head or an
   unparseable blob.

## 3. The five layers

```
┌─────────────────────────────────────────────────────────────┐
│  QUALITY        taste gates · craft-canon · provenance       │  (cross-cuts all)
├─────────────────────────────────────────────────────────────┤
│  RENDERER       canon+story → a medium (picture-book first)  │
├─────────────────────────────────────────────────────────────┤
│  STORY SPEC     a composition: selects canon + beats + spine │
├─────────────────────────────────────────────────────────────┤
│  REFS           load-bearing resolver: entity → real asset   │
├─────────────────────────────────────────────────────────────┤
│  CANON          typed entities + relations; git-versioned    │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 Canon (the universe)
The living graph. **Entities** (characters, settings, doctrines, motifs, beats, props, groups) and
**relations** between them (appears-in, derived-from, crossover-with, contradicts, supersedes). Each
entity carries **structured fields** (machine, load-bearing) and **prose fields** (voice, lore,
rules). Source of truth is the structured record; prose is a first-class field on it, not a separate
document that can drift.

### 3.2 Refs (load-bearing)
A resolver maps every entity to its real assets and **asserts** them before any render. Missing,
renamed, or unlocked → hard error. This is the layer that kills silent drift. (The Nation of Fire
`resolve_gabr.py` + `gabr-index.json` are the v0 of this layer.)

### 3.3 Story spec (a composition)
A single work, medium-neutral. It **selects** canon entities to feature, declares a **beat sheet**
(the running order) and a **spine** (the arc invariant it must satisfy), and names its **provenance**
(what each beat traces to). It reads canon and, on completion, **writes back** (a new locked
character, a new crossover, a new doctrine occurrence).

### 3.4 Renderer (projection into a medium)
Takes canon + a story spec and produces a medium artifact. The **picture-book renderer** is first and
only (the existing `create-brand-os-picture-book` + `picture-book-platform` pipeline). A renderer
declares which entity fields it consumes; adding a novel/script/comic renderer never edits canon.

### 3.5 Quality (cross-cutting)
Three wired mechanisms, applied at defined points:
- **Taste gates** — human "that's it / that's not it" at irreducible moments (words-before-art,
  register-point, face-lock). The system's job: surface the *right* decision at the right time, never
  waste attention.
- **Craft-canon** — narrative craft as enforceable invariants attached to canon (spine shape, refrain
  presence, tension→turn, "awe not horror," show-don't-tell, the confusion-flag pass).
- **Provenance** — every beat cites a source (testimony, research, the author's own words). Unsourced
  vivid detail is flagged before it ships (the cross-person-contamination guard).

## 4. Primitives (the schemas)

> These are the v0.1 shapes. They will tighten as the engine implements them; treat field names as
> provisional but the *structure* as the commitment.

### 4.1 Canon Entity
```jsonc
{
  "id": "jerry-man",                       // stable slug, unique in the universe
  "kind": "character",                     // character | setting | doctrine | motif | beat | prop | group
  "originStory": "golden-path-book",       // where it entered canon
  "authority": { "lockedBy": "gary", "lockedOn": "2026-07-10" },
  "structured": {                          // machine, load-bearing
    "sheets": { "man": "…/gabr-02-jerry-man.png", "face": "…" },
    "requiredForRender": ["man", "face"],
    "invariants": ["no-lenses", "double-eyelid-crease", "north-star-cross-upper-back"]
  },
  "prose": {                               // first-class, human/agent-authored
    "voice": "earnest, wants to believe",
    "lore": "the obedient-servant builder…",
    "rules": "front patches only from the front; …"
  }
}
```
For a **setting**, `structured` carries the *contract*: `{ turnaround, emptyPlates[], blueprint, map,
blocking, dressing }` — all required before any spread in that location renders. A setting with a null
contract field is **unlocked** and the resolver refuses to render it. (This is the environment
load-bearing fix; see §6.)

### 4.2 Relation
```jsonc
{ "from": "jerry-man", "rel": "crossover-with", "to": "brenda-gentry", "story": "gold-belongs-to-god", "note": "…" }
```
Relations are their own records so the graph is queryable ("every crossover Jerry is in", "every
story that touches this doctrine") and so contradictions/supersessions are explicit.

### 4.3 Story Spec
```jsonc
{
  "id": "not-every-fire-is-holy",
  "logline": "…",
  "spine": "obedient-servant",             // the arc invariant this story must satisfy
  "refrain": "Not every fire is holy.",
  "features": ["jerry-man", "brenda-gentry", "anjali-sambalu", "wally-boone", "wisp", "the-fear-thing"],
  "beats": [ { "n": 1, "text": "…", "location": null, "characters": ["jerry-man"], "provenance": "…" } ],
  "writesBack": [ { "kind": "character", "id": "anjali-sambalu", "locked": true } ],
  "gates": { "wordsBlessed": "2026-07-15", "subjectApproval": "gated:brenda-gentry" }
}
```

### 4.4 Ref contract (the resolver)
- `resolve(entity) → real paths | error`
- `resolve-setting(location) → contract paths | error (if unlocked/missing)`
- `assert-spread(characters[], location?) → ok | non-zero exit listing what's missing`
- **Invariant:** no renderer may generate a unit whose `assert` has not passed.

### 4.5 Renderer interface
A renderer declares `consumes` (which entity fields it reads) and `produces` (medium artifacts), and
must call `assert-spread` before every unit. It never mutates canon; it only reads canon + story spec
and emits medium output + a `writesBack` proposal for the author to accept.

## 5. Evolution & versioning

- **Every canon change is a commit** in the canon repo. The diff *is* the changelog.
- **Write-back is a proposal, then a commit.** A finished story proposes new/updated entities and
  relations; accepting them commits them into canon. This is how the universe grows from making
  stories.
- **Contradictions are explicit.** A `contradicts`/`supersedes` relation records when new canon
  overrides old, instead of silently editing history (testimony-over-prediction is honored: real
  events enter canon after they happen).
- **Time-travel is free.** Because canon is git, "what did the universe contain when story X shipped"
  is a checkout, not a feature.

## 6. Nation of Fire as the reference implementation

Everything above already exists in Nation of Fire, informally. Agentic Story is the act of naming it.

| Agentic Story layer / primitive | Nation of Fire today | Gap to close |
| --- | --- | --- |
| Canon (entities + relations) | `universe/CANON.md` (prose) + brand OS | promote to typed records; keep prose as fields |
| Refs (load-bearing) | `universe/canon/gabr-index.json` + `resolve_gabr.py` | **built 2026-07-15**; generalize `nof-*` → universe-agnostic |
| Setting contract | skill rule 17 (blueprint, empty-plates, $MAP, blocking/dressing) | encode as the setting entity's structured contract (resolver already refuses unlocked) |
| Story spec | each book's `MANUSCRIPT.md` + brand.json `books` entry | unify into one story-spec record |
| Renderer | `create-brand-os-picture-book` + `picture-book-platform` | wrap as the first named renderer |
| Quality: taste gates | words-before-art, register-point, face-lock, subject-approval | keep; make the gate list a first-class checklist |
| Quality: craft-canon | obedient-servant spine, refrain, awe-not-horror, gold-belongs-to-God | encode as spine/invariant records stories are checked against |
| Quality: provenance | the provenance check (victory-boyd lesson) | make `provenance` a required field per beat |

**First dogfood:** *Not Every Fire Is Holy* is mid-production on exactly this — its refs already
resolve through the load-bearing resolver, its setting (the arena) is correctly *refused* until
locked.

## 7. Non-goals (for v0.1)

- Not a general-purpose CMS or a fiction-writing chatbot.
- Not multi-renderer yet (picture-book only; the architecture *permits* more, we don't *build* more).
- Not a mass refactor of all existing books at once (incremental adoption; NoF stays runnable
  throughout).
- Not a replacement for human taste — the gates are load-bearing, deliberately.

## 8. Open questions

- **Canon storage:** one canon repo per universe, or a shared multi-universe store? (Lean: per-universe
  repo, like `nation-of-fire/universe` today.)
- **Prose-vs-structured source of truth per field:** which fields must be structured vs may stay
  prose? (Lean: anything a renderer or resolver consumes is structured; everything else prose.)
- **Craft-canon enforcement:** advisory (a checklist an agent self-scores) vs hard (a validator that
  blocks)? Likely graduated — hard for the mechanical (refrain present, spine declared), advisory +
  judge-panel for the subjective (is the turn earned).
- **How much of the wiki is generated from canon** vs hand-authored? (Lean: concept pages
  hand-authored; worked-example pages generated/derived from real canon records.)

## 9. Glossary

- **Universe / Canon** — the evolving graph of everything true in a story world.
- **Entity** — a typed node in canon (character, setting, doctrine, motif, beat, prop, group).
- **Load-bearing reference** — a reference whose absence is a build error, not a silent drift.
- **Story spec** — a medium-neutral composition selecting canon + beats + spine + provenance.
- **Renderer** — a pluggable projection of canon + story into one medium.
- **Craft-canon** — narrative-craft rules encoded as enforceable invariants.
- **Write-back** — the new canon a finished story contributes to the universe.
- **Gate** — a point where human taste or a hard check must pass before proceeding.
