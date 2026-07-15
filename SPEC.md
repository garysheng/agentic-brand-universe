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
  "kind": "character",                     // character | setting | visual-metaphor | doctrine | motif | beat | prop | group
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
  },
  "realPerson": {                          // present ONLY when the entity is a real person (backtest finding 4)
    "photoStack": ["reference/photos/…"],  // 5+ real photos; GABR built from the stack, never a painting-of-a-painting
    "canonicalPhotos": { "face": "…", "fit": "…" },
    "approval": { "state": "gated", "by": "brenda-gentry", "on": null },  // gated | approved
    "sensitiveList": "RESEARCH.md#sensitive", // what never ships
    "wardrobeEras": { "default": "…", "activity": { "running": "…" } },   // activity-specific attire (rule: no street outfit while running)
    "groupCount": null                     // for a group/lineup: the EXACT member count (a research fact, not an art inference)
  }
}
```
**Entity kinds, and the two the backtest forced in:**
- For a **setting**, `structured` carries the *contract*: `{ turnaround, emptyPlates[], blueprint, map,
  blocking, dressing }` — all required before any spread in that location renders. A null contract
  field means **unlocked** and the resolver refuses to render it. (Environment load-bearing fix; §6.)
- **`visual-metaphor`** (backtest finding 2) is a first-class kind: the central object a whole book
  zooms into and argues through — *Hold It Up to Forever*'s locked scale, *Maximize*'s bazaar of
  cages. It carries a setting-style contract (a locked master + derived element crops) because, like a
  setting, every page depends on it — but it is the book's *spine-object*, not merely a location.
- **`realPerson`** is a sub-block on a `character`, not a flag (backtest finding 4): real-subject books
  (Brenda, Russ, Nait, Panama, Apostle Lee) need the photo stack, approval state, sensitive list,
  activity-wardrobe eras, and exact group counts — the multi-ref rule, the subject-approval gate, and
  the group-lineup lesson all live here.

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
  "spine": "obedient-servant",             // the arc invariant this story must satisfy —
                                           // obedient-servant | thesis | primer | testimony | ...
                                           // NOT every story is a hero-journey (backtest finding 1):
                                           // An Honest Primer on AI is a "primer" spine; Hold It Up
                                           // to Forever is a "thesis" spine built on a visual-metaphor.
  "refrain": "Not every fire is holy.",
  "register": {                            // the paint-language (backtest finding 3) — a first-class
    "id": "warm-oil-curdles-cold",         // per-story renderer config, not implicit in the renderer
    "anchor": "reference/style-anchor.png",// content-neutral palette/finish swatch, passed first
    "anchoredToRealArt": null,             // e.g. Painted in His Image anchors to Tadeo's own canvases
    "rejectedPoles": ["washed-out/mushy", "famous-artist pastiche"]
  },
  "features": ["jerry-man", "brenda-gentry", "anjali-sambalu", "wally-boone", "wisp", "the-fear-thing"],
  "beats": [ { "n": 1, "text": "…", "location": null, "characters": ["jerry-man"], "provenance": "…" } ],
  "writesBack": [ { "kind": "character", "id": "anjali-sambalu", "locked": true } ],
  "gates": { "wordsBlessed": "2026-07-15", "subjectApproval": "gated:brenda-gentry" }
}
```

**Spine (finding 1):** the NoF canon's claim that *every* property is an obedient-servant journey is
not actually true — *An Honest Primer on AI* is an explainer, not a hero-journey. `spine` is a
per-story **declared** invariant drawn from an open set (`obedient-servant`, `thesis`, `primer`,
`testimony`, …); craft-canon checks a story against *its declared* spine, never a single assumed one.

**Register (finding 3):** the paint-language is a first-class per-story renderer config, sometimes
anchored to a real artist's own body of work (*Painted in His Image* → Tadeo's canvases). It is
locked via register experiments (Gary points), then passed as a content-neutral **style anchor** on
every render — never left implicit inside the renderer.

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
- **Craft-canon is DISCOVERED, then encoded — not given (the deepest backtest finding).** The hardest
  book (*Kenosis*, immersive venue) ran on a large pile of rules the author learned *by failing*:
  hologram-vs-visitor translucency, projection inventories, "make her more obviously a hologram," the
  style-anchor-leaks-content trap. The framework does **not** produce those taste discoveries up
  front. What it does: (a) turn the *mechanical* failures (missing refs, drifting settings, unsourced
  beats) into hard errors so they stop recurring, and (b) give each *discovered* rule a first-class
  home (a craft-canon invariant, a new entity field) so it is paid for once and reused forever. Craft
  grows by making stories; the system's job is to capture it, not to pretend it precedes the work.

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

## 8. Decisions (resolved 2026-07-15) + genuinely-open

**Decided (were open questions; the backtest gave enough evidence):**
- **Canon storage → one repo per universe.** Like `nation-of-fire/universe` today. A shared
  multi-universe store is a premature abstraction; per-universe keeps git-as-evolution clean.
- **Structured-vs-prose → consumption decides.** Any field a renderer or resolver *consumes* is
  structured (load-bearing); everything else is prose. No field is both source-of-truth.
- **Craft-canon enforcement → graduated.** Hard-blocking for the mechanical and checkable (refrain
  present, spine declared, refs resolve, provenance non-empty, setting locked); advisory + judge-panel
  for the subjective (is the turn earned, is it moving). Never block on taste; never let a mechanical
  miss through.

**Still genuinely open:**
- **How much of the wiki is generated from canon** vs hand-authored. (Lean: concept pages
  hand-authored; worked-example pages derived from real canon records — but not committed until the
  wiki is scaffolded.)
- **Judge-panel design** for the subjective half of quality (rubric, how many lenses, when it runs).

## 9. Backtest / validation (2026-07-15)

The spec was audited against the real Nation of Fire roster (24 properties + a 24-entry crossover
log) — *would the books already made be creatable on this framework?*

- **~18 fit cleanly:** character-carried, antagonist-cast, ensemble, real-subject, setting-carried.
  **Crossovers are the strongest validation** — the 24-entry log is native as Relation records.
- **4 types strained v0.1 and are now folded in above:** non-journey **spines** (finding 1, *Honest
  Primer*), **`visual-metaphor`** as a kind (finding 2, *Hold It Up to Forever*), **register** as
  first-class (finding 3, *Painted in His Image*), the **`realPerson`** dossier (finding 4, the
  real-subject books).
- **Honest caveat:** the framework is reverse-engineered *from* these books, so post-hoc
  expressibility is half-circular. Its real value is preventing the *recurring mechanical* failures
  (ref-scatter, setting drift, the Charlotte leak, provenance contamination) and giving *discovered*
  taste a home — not auto-producing taste (see §5, craft-canon is discovered-then-encoded).
- **Verdict:** every existing book is expressible; the four additions close the strain; the next real
  test is whether the framework makes the *next* book cheaper, not the last fifteen describable.

## 10. Glossary

- **Universe / Canon** — the evolving graph of everything true in a story world.
- **Entity** — a typed node in canon (character, setting, doctrine, motif, beat, prop, group).
- **Load-bearing reference** — a reference whose absence is a build error, not a silent drift.
- **Story spec** — a medium-neutral composition selecting canon + beats + spine + provenance.
- **Renderer** — a pluggable projection of canon + story into one medium.
- **Craft-canon** — narrative-craft rules encoded as enforceable invariants (discovered, then encoded).
- **Write-back** — the new canon a finished story contributes to the universe.
- **Gate** — a point where human taste or a hard check must pass before proceeding.
- **Spine** — a story's declared arc invariant (obedient-servant, thesis, primer, testimony, …); not
  a single assumed shape.
- **Visual-metaphor** — an entity kind: the central object a whole book zooms into and argues through
  (the locked scale, the bazaar of cages); the book's spine-object.
- **Register** — a story's paint-language: a first-class per-story renderer config, sometimes anchored
  to a real artist's own work, locked via experiments and passed as a content-neutral style anchor.
- **realPerson dossier** — the sub-block on a real-subject character: photo stack, approval state,
  sensitive list, activity-wardrobe eras, exact group count.
