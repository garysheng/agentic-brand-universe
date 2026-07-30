# Agentic Brand Universe — Cartridge Spec

**v0.16 — 2026-07-29.** The version-controlled brand-universe (cartridge) format: the first-principles
architecture for a brand as version-controlled canon + golden assets, agentically writable,
composable, and evolvable, rendered into any deliverable. Home: `agenticbranduniverse.com`.
Reference implementations: the Nation of Fire universe (storybooks) and Build on Anthropic (a
documentation brand: explanatory plates, ink-line illustration, share cards, a slide deck).

> **v0.16 changelog — an entity has a LIFECYCLE, so canon can be RETIRED without rewriting history.**
> Additive and backward-compatible: an entity with no `lifecycle` is `active`, so no universe has to
> migrate. A universe accumulates canon faster than it retires it, and until now the only ways to stop
> casting something were deletion (which breaks every book that already shipped and falsifies its
> provenance) or a note in prose (which no tool reads). Neither is an archive.
>
> An entity may now declare `"lifecycle": "active" | "archived"` plus an `archived` block
> (`on`, `reason`, optional `supersededBy`). **`lifecycle` is EDITORIAL STANDING and is deliberately
> ORTHOGONAL to `status`**, which is reference-completeness: an archived entity is normally still fully
> locked, and its art stays valid forever.
>
> The load-bearing rule is WHERE the gate sits. **`assert-story` knows nothing about lifecycle**, so
> archiving can never retroactively break a book that already shipped. The refusal lives at the point
> of NEW casting: the spread compiler refuses before spending and names the replacement, and a
> deliberate re-render of a pre-archive book opts out per spread with `allowArchived`, which leaves an
> auditable trace of that decision. An archive with no recorded `reason` fails validation, because an
> archive nobody can audit is worse than none. CLI: `archive`, `unarchive`, `archived`.

> **v0.15 changelog — a setting's blueprint is a CODE-BUILT 3D MASSING RENDER.** Additive and
> advisory: no existing universe has to migrate, and a hand-drawn or prompted blueprint still
> validates. `blueprint` was under-specified as "top-down/schematic", and a plan view makes the image
> model INFER the perspective it has to paint. Inference is where geometry drifts: proportions change
> between angles, furniture migrates, and handedness silently flips, so a contract claim like "the
> bookshelf wall is C1-LEFT" quietly stops holding halfway through a book. The engine now ships
> `agenticstory.massing` and a `massing` CLI verb: declare the room once as boxes and quads with its
> cameras named, and it renders the ACTUAL perspective each locked camera will see, deterministically,
> with no model and no cost. The recommended blueprint is therefore a massing render from the entity's
> own locked cameras, kept deliberately crude (flat blocks, ink edges, no textures) so it reads as
> scaffolding rather than as art to copy. Same rule extends to a `visual-metaphor` with fixed geometry:
> seed the state chain on the blueprint, never on a sibling state plate.
>
> > **v0.14 changelog — Projection/Composition become Form/Work.** §4.8 and §4.9 are renamed, and the
> rename is the point rather than cosmetics. A *projection* is determined by (object, map); a work is
> not determined by (canon, form) — `beats` and `spine` are authored facts present in neither, and
> §4.9's `writesBack` lets a work change the canon it supposedly views, which no shadow does to its
> object. **Projection** therefore survives as the name of the RELATIONSHIP canon bears to a work,
> which is the one job that word does correctly, and stops naming either primitive. The pair that
> does fit is hylomorphic: canon is the matter, a form is what shapes it, a work is canon given form.
> "Instance" is dropped because it actively denies the authorship a work carries. §4.8 also gains the
> naming rule (name the TREATMENT, not the medium — if `id` equals `surface.medium`, every sibling
> treatment has nowhere to live) and the requirement that a computed invariant carry an evaluable
> `rule` rather than only an id. Directories move to `forms/*/form.json` and `works/*/work.json`; the
> pre-0.14 `projection` key on a work still loads.
>
> **v0.13 changelog — deterministic graphics get a typed home.** §4.11 adds the **Deterministic
> Generator**: code in the universe that DRAWS an asset rather than prompting for one, with a
> manifest declaring its params, seed, inputs, outputs, install map, and proof. The framework already
> required that deterministic graphics render in code rather than through an image model, but gave
> that code nowhere to live, so it accumulated as loose scripts with ad-hoc paths, hand-written
> provenance, and hand-written install copying. Three rules are load-bearing: every parameter is DATA
> and never a buried constant (two constants silently meaning different things sheared the descender
> off a whole favicon set); the gate is a human-approved PROOF SHEET at real size rather than a
> per-run read-back, because a generator is reproducible; and a generated asset carries a recipe
> naming generator + params + seed, because no asset ships without provenance.

> **v0.12 changelog — text is gated, not banned.** §4.7 adds `textPolicy` to the Style Pack
> (`none` | `diegetic` | `furniture`). A blanket "no text" rule conflated three different things and
> silently degraded artifacts whose job is to explain: a book cover in frame could not say what it
> says, and a wiki hero could not carry the title bar and captions that make it readable. The rule
> that survives is narrower and truer: never render text the surrounding layout already supplies.
> Any permitted text is declared by the caller and verified character-exact in read-back, the same
> posture already used on a cover title. Packs with no `textPolicy` read as `diegetic`.

> **v0.10 changelog — a character must be able to prove its own scale, and its future.** The v0.9
> lesson generalizes past settings: **a dimension nothing depicts cannot be judged.** §12 gives the
> character matrix the same treatment in two places. **(1) `structured.scale`** — `height` in human
> terms plus `relativeTo`, a map of other entity ids to a phrase ("several inches shorter than").
> Every entity was described alone, so two people sharing a frame came out the same height, or
> reversed, and nothing in canon could say otherwise. The compiler emits a RELATIVE SCALE line only
> when two or more in-frame characters declare a relation to each other, so solo spreads are
> unchanged. **(2) `altLooks` is documented for the first time**, having been load-bearing in the
> compiler and absent from this spec, plus `keepSheets` / `keepPhotos` for **declared-future
> (prophetic) looks**. An ordinary alt look changes the FACE (a beard, an age era) and supplies its
> own `anchorPhoto`, which is why base face sheets are auto-dropped. A declared-future look inverts
> that: the face is CONTINUOUS, the BODY changes, and the future has no photograph to anchor. Under
> the old rule such a look reached the model with body sheets only, which are the exact silhouette
> it supersedes, and the model drew a stranger. `compose-spread` now refuses that at compile time
> (free) and `lint-universe` warns `LOOK-NO-IDENTITY-ANCHOR` one step earlier. Advisory and
> back-compatible: a character with no `scale` still locks and still renders. Earned 2026-07-26
> adding `beef-jones`' 2028 and 2030 eras for a book whose final act is set in a declared future,
> and whose two leads differ in height by several inches.

> **v0.9 changelog — a setting must be able to prove its own size.** §12 adds `scalePlate` (file)
> and `scale` (descriptor) to the setting matrix. `emptyPlates` are people-free so a setting
> reference never bakes a character's face into a room; that rule is correct and unchanged. Its
> unpriced cost: a figure-free interior carries no unit of comparison, so the model picks a size,
> every render inherits it, and nobody can catch it because the plate does not depict the dimension
> being judged. A `scalePlate` is the same room with ANONYMOUS scale figures (small, distant, turned
> away, faces unreadable, never a canon character), which satisfies the identity rule and makes size
> checkable. The `scale` descriptor states the size in human terms and is passed in every prompt like
> `dressing`, because prose survives a re-render and a plate does not. Advisory: `lint-universe`
> warns `SETTING-NO-SCALE-PLATE`. Earned on `christofuturist-home`, whose hearth room rendered small
> and cramped through an entire book because nothing in its contract said how big it was, and whose
> free-standing central firepit under a suspended conical flue was quietly unbuildable for the same
> reason: no plate ever had to show how the thing stood up.

> **v0.8 changelog — the compiler guards come home, and a spread may carry its own register.**
> §4.6 gains four NORMATIVE guards that had been living in one universe's private fork of the
> compiler (`nof-universe/canon/scripts/compile_render.py`, which v0.5 named as the reference impl).
> Each was paid for with defective renders, and each was invisible to every other universe:
> **(1) anchor-style guard** — the register anchor is ref[0] on every render, so on a spread that
> casts nothing its SUBJECT leaks as content; the guard is a property of passing an anchor at all,
> not of a book's style text. **(2) single-image guard** — canon study sheets (turnarounds, states
> sheets) are multi-panel, and the model copies their LAYOUT; emitted by default, `allowMultiPanel`
> opts out. **(3) uncast-character refusal** — a character NAMED in scene text but not cast is
> silently rendered as an invented stranger; a pure-text check now refuses before spending,
> `allowUncast` overrides. **(4) per-spread preamble override** — a book may carry MORE THAN ONE
> visual register when the change is DIEGETIC (a game world on a screen, a vision blooming out of a
> canon device, a memory, a dream). A spread may override `style`, `negatives`, `guardedNegatives`,
> `anchorRef`, `size`, `allowMultiPanel`, `allowUncast`; a spread naming none of them compiles
> byte-identically to v0.7. The universe's own `rejectedPoles` are identity and can never be shed by
> a spread. Earned on `jerry-and-the-game-that-beat-gta`, a book that argues its thesis in its own
> paint. The reference impl is now the framework's own `assemble_prompt.py`, tested; a universe-local
> compiler is a fork to be migrated, not a sanctioned pattern.
>
> **v0.7 changelog — the cover-conform convention.** Added a normative default (§ producible-vs-surface
> aspect): when a producible aspect does not match the target surface, conform by **blurred self-bleed**
> (`conform_cover.py --mode pad`), never by a flat-color bar and never by cropping load-bearing content.
> A flat side-bar passes the aspect check but seams visibly against the art and looks unintentional;
> hand-rolling a per-universe pad script is the exact hand-roll the convention retires. Backward
> compatible: universes conforming to 0.6 remain valid.

> **v0.6 changelog — the projection release.** The spec claimed (§3.3) that a composition was
> "medium-neutral" while the primitive (§4.3) *required* `logline`, `spine`, `refrain`, and `beats`.
> A flyer has no beats; a meme has no refrain. So the standard could only actually express STORIES,
> which is why a brand framework kept reading as a storybook tool no matter how it was described.
> The fix names the missing layer:
> - **§4.8 Projection** — a typed contract for a KIND of deliverable (storybook, flyer, meme, share
>   card, explanatory plate, slide deck), with `surface` / `requires` / `slots` / `generators` /
>   `invariants` / `emits`. Adding a new kind of deliverable is now filling in a contract, not
>   inventing a renderer.
> - **§4.9 Composition** — one INSTANCE of a projection. Narrative fields move out of the generic
>   primitive into the storybook form's slot schema, where they always belonged. `Story Spec`
>   is retained as an alias so existing universes validate unchanged.
> - **§4.10 The Composer** — the render step splits into three parts with genuinely different
>   natures: an *agentic* composer that PLANS, a *deterministic* compiler (§4.6) that turns one
>   planned slot into an exact prompt, and a *verifying* gate that re-rolls the slot on defect.
>   This is the only layer where model intelligence belongs.
> - **§14 Why this runtime is Managed Agents** — the composer is a long-running, multi-step,
>   multi-modal loop holding state and secrets. That is not a preference, it is the workload.
> - **Per-slot vs cross-slot invariants** (§4.8) make "simple deliverable" versus "complex
>   deliverable" a property of the ontology rather than a vibe.

> **v0.5 changelog:** **§4.6 Prompt compiler (the render step) + entity `render` block.** The
> resolver asserted that refs *exist* (§4.4), but the load-bearing PROMPT was still hand-assembled by
> the author each render — so a rule the entity already carried could silently be dropped (earned
> 2026-07-18, *The Room With No Fire*: a hand-written prompt omitted Jerry's front patches and aged
> him down, wrecking likeness across a whole batch, even though the entity spelled both out). The fix
> makes prompt assembly *deterministic*: a compiler emits the prompt text + ref list + QA checklist
> straight from canon, so nothing load-bearing is retyped. New entity structured field **`render`**
> (`always` / `poses{pose:{sheets[],bake}}` / `qa[]`) is the compiler-consumable home for identity
> craft that used to live as `prose.rules` scar tissue. Determinism ceiling made explicit: the
> compiler makes the INPUT deterministic; model output stays stochastic, so the read-back gate (§3.5)
> is still mandatory. Reference impl: `nof-universe/canon/scripts/compile_render.py`, first migration
> `jerry-man.render`. Back-compatible: an entity with no `render` block still renders via a
> hand-written prompt.

> **v0.4 changelog:** (1) **§12 Reference-matrix standard** — a per-kind canonical shot set defines
> what "locked" means; the engine reports `lock_level` (stub/partial/locked), advisory and
> back-compatible (the load-bearing gate's hard-fail on missing required sheets is unchanged).
> (2) **Register in identity** — a universe's illustrative style is a first-class `identity.register`
> (named style + a content-neutral style anchor passed first on every render), defaulted by the
> start-universe flow.

> **v0.4.1 changelog:** **§13 Craft-canon records** — a typed home (`canon/craft/*.json`, kinds
> `spine` | `genre` | `register-rule`) for the genres, spines, and register rules a renderer honors,
> so craft is data, not skill prose (§11). Optional and back-compatible: a universe with no
> `canon/craft/` validates unchanged.

> **v0.3 changelog:** (1) **Self-containment** made an explicit invariant (principle 3a) — a universe
> owns its assets inside its own repo; refs never point outward. (2) New **§11 Skills & Identity layer**
> — generic framework skills parameterized by a target universe read a universe's `identity` block;
> a universe ships *data*, the framework ships *skills*. Both were earned making the Nation of Fire
> universe self-contained and auditing its skills for multi-universe reuse.

> **Thesis, in one line:** *A deliverable is a **projection** of an evolving canon: planned by an
> agent, compiled deterministically, and held to craft and to human taste.*
>
> The four nouns are the whole standard. **Canon** is what is true. **Goldens** are what it looks
> like, locked. A **projection** is a kind of thing you can make from them. The **composer** is the
> agent that makes one, and is answerable to a gate.

---

## 1. Why this exists

We have built ~15 illustrated books inside one shared universe (Nation of Fire). Each was strong, but
the *system* underneath was implicit and re-remembered every time: canon lived in prose, reference
art scattered across four different path conventions, craft rules survived as skill-file scar tissue,
and quality depended on the author holding it all in his head. The books were composable and
evolvable in spirit but not in mechanism — so the same failures recurred book after book (settings
that drift, references that silently go missing, beats that can't be traced to anything real).

The Agentic Brand Universe standard makes the implicit system explicit: a small set of primitives and
invariants that make a brand **universe** — version-controlled canon + golden assets — the
first-class object, deliverables **compositions** over it, references **load-bearing** (their absence
is a crash, not a drift), and quality a set of **wired gates** rather than a memory feat. It is
designed to be written and evolved primarily **by agents**, with the human in the loop exactly where
taste is irreducible. (An **Agentic Brand Universe** — the picture-book / comic — is one such deliverable.)

## 2. First principles (the bets)

1. **Universe-first.** The evolving canon is primary. A single work is a projection of it, and writes
   back into it. Composability and evolvability are then native, not bolted on.
2. **Canon is medium-neutral.** Canon entities carry no medium assumptions. Rendering into a medium
   (picture book, novel, script, comic, game bible) is a separate, pluggable layer. Ship one renderer
   first; add others without touching canon.
3. **References are load-bearing.** Every canon entity that has an asset (a character sheet, a setting
   plate, a voice sample) resolves to a real file or the build **fails loudly**. A reference you can
   forget is not a reference; it is a wish.
   - **3a. Self-containment.** A universe owns its assets *inside its own repo*. `assetRoot` resolves
     within the universe repo, and every referenced file lives under it — never in a sibling folder or
     another repo. The test: you can clone the universe repo alone and every reference still resolves,
     the gate still runs. Assets scattered across the folders that happen to *use* them is the drift
     this kills (the Nation of Fire canon began that way — 342 assets across 44 book folders — and was
     consolidated into one self-contained repo, 2026-07-18). A universe that cannot move as one folder
     is not yet a universe.
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

## 3. The six layers

```
┌─────────────────────────────────────────────────────────────┐
│  QUALITY      taste gates · craft-canon · read-back          │  (cross-cuts all)
├─────────────────────────────────────────────────────────────┤
│  COMPOSER     agentic: plan → compile → generate → gate      │  §4.10
├─────────────────────────────────────────────────────────────┤
│  COMPOSITION  ONE instance: this book, this flyer, this meme │  §4.9
├─────────────────────────────────────────────────────────────┤
│  PROJECTION   the typed contract for a KIND of deliverable   │  §4.8
├─────────────────────────────────────────────────────────────┤
│  GOLDENS      load-bearing resolver: entity → real asset     │  §4.4
├─────────────────────────────────────────────────────────────┤
│  CANON        typed entities + relations; git-versioned      │  §4.1
└─────────────────────────────────────────────────────────────┘
```

Read it bottom-up as a sentence: *canon* is what is true, *goldens* are what it looks like once
locked, a *projection* is a kind of thing you can make, a *composition* is one of them, and the
*composer* is the agent that makes it and answers to the gate.

The split that v0.6 introduces is between the middle two. **A projection is a type; a composition is
an instance.** Conflating them is what made this standard storybook-shaped: the one primitive that
existed carried a story's required fields, so every deliverable had to be a story to be expressible.

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

### 3.3 Projection (a kind of deliverable)
The typed contract for a KIND of artifact: what surface it occupies, which canon it requires before it
may render, what slots it composes, which generators it invokes, and which invariants it is held to.
A storybook, a flyer, a meme, a share card, an explanatory plate and a slide deck are six projections
of the same canon. Defining a new one is filling in a contract (§4.8), not writing a renderer.

### 3.4 Composition (one instance) and the Composer (who makes it)
A **composition** is one flyer, one book: it names its projection, selects the canon entities to
feature, and fills the projection's slots. It reads canon and, on completion, **writes back** (a new
locked character, a new crossover, a new doctrine occurrence).

The **composer** (§4.10) is the agent that turns a composition into the artifact. It plans the slots
and their order, calls the deterministic compiler (§4.6) per slot, invokes generators across
modalities, and repairs against the gate. It never mutates canon; it emits medium output plus a
`writesBack` proposal.

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

> These are the v0.2 shapes. They will tighten as the engine implements them; treat field names as
> provisional but the *structure* as the commitment.

### 4.1 Canon Entity
```jsonc
{
  "id": "jerry-man",                       // stable slug, unique in the universe
  "kind": "character",                     // character | setting | visual-metaphor | doctrine | motif | beat | prop | group
  "originStory": "golden-path-book",       // where it entered canon
  "authority": { "lockedBy": "gary", "lockedOn": "2026-07-10" },
  "structured": {                          // machine, load-bearing
    "sheets": { "man": "…/gabr-02-jerry-man.png", "face": "…", "jacketBack": "…", "shoes": "…" },
    "requiredForRender": ["man", "face"],
    "invariants": ["no-lenses", "double-eyelid-crease", "north-star-cross-upper-back"],
    "render": {                            // compiler-consumable identity craft (§4.6) — NOT prose
      "always": "canonical adult face per the face sheet; clean-shaven; NO lenses; …",
      "poses": {                           // pose-conditional refs + bake text the compiler emits
        "front": { "sheets": ["man","face","pendant","shoes"],
                   "bake": "front patches: SMILEY on one chest, TEXAS FLAG on the other" },
        "back":  { "sheets": ["man","jacketBack","face","shoes"],
                   "bake": "ONLY the north-star back patch; front patches invisible from behind" }
      },
      "qa": ["face matches face sheet (adult)", "front pose: both patches present", "pendant is a STAR not a crucifix"]
    }
  },
  "prose": {                               // first-class, human/agent-authored
    "voice": "earnest, wants to believe",
    "lore": "the obedient-servant builder…",
    "rules": "front patches only from the front; …"
  },
  "realPerson": {                          // present ONLY when the entity is a real person (backtest finding 4)
    "photoStack": ["reference/photos/…"],  // 5+ real photos; GABR built from the stack, never a painting-of-a-painting
    // An entry may be a FILE or a DIRECTORY. A directory expands to the sorted image files
    // directly inside it, so `["reference/<id>/photos"]` is the idiomatic whole-stack form.
    "photoLimit": null,                    // v0.17: cap how many EXPANDED photos reach the model.
    // null (default) = pass them ALL, which is what "5+ real photos" above always meant: more
    // bare-face angles make a stronger identity lock. Set an integer only when a stack has more
    // photos than a prompt should carry. THE CAP APPLIES AFTER DIRECTORY EXPANSION. Before v0.17
    // the assembler hard-capped at 2 by slicing the RAW stack, so a one-entry DIRECTORY stack
    // sailed past the cap entirely and passed every photo in the folder: the ceiling did nothing
    // in exactly the case this convention encourages, and it contradicted the "5+" rule above.
    // Found 2026-07-29 (she-had-everything-but-peace): nof `victory` passed SIX refs on every
    // spread that cast her, two of them multi-person family-band photographs. A group photo used
    // as an identity anchor is how a scene grows an extra confident stranger. When you cap, cap a
    // stack of NAMED SOLO FILES rather than a directory: an alphabetical truncation of a folder
    // picks whichever files sort first, not the best faces.
    "canonicalPhotos": { "face": "…", "fit": "…" },
    "approval": { "state": "gated", "by": "brenda-gentry", "on": null },  // gated | approved | none-required
    // `none-required` (v0.6.1) is for a universe whose identity.subjectApproval.realLivingPerson
    // is itself `none-required`: the per-subject blessing gate is abolished, so the whole
    // `approval` block is optional and validation does not demand a state. Before this, such an
    // entity had no honest value — `approved` asserts a blessing nobody asked for, and `gated`
    // reinstates the retired gate.
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
  **`blueprint` SHOULD be a code-built 3D MASSING RENDER shot from the setting's own locked cameras**
  (v0.15, advisory): `abu massing <spec.json> --out .../blueprint.png`. A top-down plan still
  validates, but it forces the image model to infer the perspective, which is where room proportion
  and handedness drift. Keep the massing sheet crude on purpose so it reads as scaffolding, and pass
  it with the standard blueprint guard: layout reference only, never painted.
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

**Story status (`stub` | `full`):** a story may be registered as a `stub` (title + declared spine,
no beats yet) so the canon reflects the whole roster before every book is fully migrated — the
features/beats/provenance requirements apply only to a `full` story. (Mirrors a setting being
`unlocked`.)

**Register (finding 3):** the paint-language is a first-class per-story renderer config, sometimes
anchored to a real artist's own body of work (*Painted in His Image* → Tadeo's canvases). It is
locked via register experiments (Gary points), then passed as a content-neutral **style anchor** on
every render — never left implicit inside the renderer.

### 4.4 Ref contract (the resolver)
- `resolve(entity) → real paths | error`
- `resolve-setting(location) → contract paths | error (if unlocked/missing)`
- `assert-spread(characters[], location?) → ok | non-zero exit listing what's missing`
- **Invariant:** no renderer may generate a unit whose `assert` has not passed.

### 4.5 Renderer interface (superseded by §4.10; invariants retained)

**v0.6:** what this section called a *renderer* is now the **composer** (§4.10), and a *story spec* is
now a **composition** (§4.9). The rename matters because "renderer" implies a deterministic template
engine, and the layer that plans a composition is not one. Three invariants from this section survive
unchanged and remain normative for the composer:

- It declares `consumes` (which entity fields it reads) and `produces` (medium artifacts).
- It **must assert refs before every unit** (§4.4). No unit is generated whose `assert` has not passed.
- It **never mutates canon.** It reads canon plus a composition and emits medium output plus a
  `writesBack` proposal for the author to accept.

### 4.6 Prompt compiler (the render step)
`assert-spread` guarantees the refs *exist*; it says nothing about the **prompt**. Left to a human or
LLM, the prompt is retyped every render and any rule not recalled in that moment is silently dropped
— the single highest-frequency defect class (earned 2026-07-18: a hand-written prompt omitted a
character's canon-declared front patches and invented an age, across a whole batch). The compiler
removes that step.

- **Contract:** `compile(spread-spec, preamble) → (prompt, refs[], qa[])`, pure and deterministic.
  A *spread-spec* is thin — `{ setting:{entity,sheet?}, characters:[{entity,pose}], extras:[{entity,bake?,sheet?}], scene }` — the only free text is the scene *action*. Everything identity-bearing is compiled from canon:
  - refs = each entity's `requiredForRender` + the pose's `render.poses[pose].sheets` (de-duped);
  - prompt = `preamble.register` + setting bake (the setting's `contract.dressing` + book rule) + each character's `render.always` + `render.poses[pose].bake` + extra bakes + `scene` + `preamble.negatives`;
  - qa = the union of every in-frame entity's `invariants` + `render.qa` — **the checklist is compiled from the same canon as the prompt**, so read-back can never check the wrong things (the second half of the earned failure: the QA checklist was also hand-written and never checked the missing patches).
- **Provider-agnostic:** the compiler emits `(prompt, refs, size)` and hands off to a swappable
  provider adapter (`gpt-image-2` today, others behind the same interface). The adapter normalizes the
  *call*; per-provider reference-conditioning and moderation (e.g. a `public-figure` block) remain
  provider facts, not framework facts.
- **Determinism ceiling (invariant):** the compiler makes the *input* deterministic; the model output
  stays stochastic. A compiled prompt is necessary, not sufficient — the read-back gate (§3.5) is
  still mandatory, and a drift-prone shape is guaranteed by *passing its reference image*, never by
  wording it harder.
- **Normative guards (v0.8).** Four rules the compiler emits or enforces on every job, because each
  is a property of *how the compiler works*, not of what a given book contains. A universe that
  writes these into each book's style text will drop them the one time it forgets.
  - **Anchor-style guard.** Whenever a register anchor is passed, the prompt states that ref[0] is a
    style sample only: match its medium, brushwork, palette and light, take NO subject from it. The
    anchor leads every render, so on a spread that casts no setting and no characters it is one of
    only two references and the model reads it as CONTENT. A pure-vision beat came back as a room
    full of period strangers holding the anchor's own props. Every other spread survived only
    because setting plates and character sheets outweighed it, which is why this looked safe for
    months.
  - **Single-image guard.** Emitted by default: one continuous full-bleed image, never a grid,
    contact sheet, comic page or panelled study. Canon legitimately supplies multi-panel references
    (a character turnaround, a visual-metaphor's states sheet) and the model copies their layout.
    `allowMultiPanel` (book- or spread-level) opts out.
  - **Uncast-character refusal.** Before any spend, the compiler matches every character entity's
    given name against the scene text and REFUSES on any name it does not cast, because the model
    invents a confident stranger for each. An over-the-shoulder single needs both people cast: the
    shoulder is a person. `allowUncast` overrides when the mention is genuinely not in frame. Name
    tokens already covered by a cast entity do not fire (`chief-of-*` and `apostle-*` ids share a
    head token).
  - **Per-spread preamble override.** A book may carry more than one visual register when the change
    is DIEGETIC. A spread may override `style`, `negatives`, `guardedNegatives`, `anchorRef`, `size`,
    `allowMultiPanel` and `allowUncast`; anything it does not name falls back to the book preamble.
    The alternative (a second render-spec per register) duplicates the whole preamble and drifts the
    moment one copy is edited. The universe's `rejectedPoles` are identity and are never shed by a
    spread override.
- **Reference impl:** the framework's own `skills/compose-spread/scripts/assemble_prompt.py`, with
  tests. Superseded 2026-07-25: v0.5 named `nof-universe/canon/scripts/compile_render.py` here, and
  sanctioning a universe-local compiler is how the two implementations diverged into disjoint
  feature sets — the fork held the four guards above while the framework held alt-looks,
  auto-disambiguation, guarded negatives and `anchorRef`, and neither could see the other's. A
  universe-local compiler is now a FORK to be migrated, never a sanctioned pattern.

### 4.7 Style Pack (the portable look)

A **Style Pack** is a self-contained folder that defines ONE look and is consumable **without a
universe**. It is the register's paint-language (§3.5, glossary) extracted into a portable artifact so
that generating an on-brand image needs only *a style*, never a canon. This is the layer that makes
the framework useful for the common case — "here is a folder of images, make more that look like
them" — which has no recurring-identity requirement and therefore no need for entities.

```
<pack>/
  pack.json         # the manifest (below)
  refs/*.png        # 3-8 style reference images: the load-bearing source of the look
```

```jsonc
{
  "id": "anthropic-plate",
  "name": "Anthropic ink-line plate",
  "anchor": "refs/hands-blocks.png",          // the one ref always passed FIRST
  "refs": ["refs/hands-blocks.png", "..."],   // 3-8, pack-relative; a subject-matched one is chosen per render
  "palette": { "ground": ["#CC785C","#F5F1E9","#B9C7BA","#C9C3DE"], "fill": ["#F5F1E9"], "line": ["#1A1A17"] },
  "styleLine": "single-weight wobbly black ink brush line, flat cream fills, flat solid ground, face-on",
  "rejectedPoles": ["neon","3D/CGI/Pixar","perspective","isometric","shading","gradients","coloured linework","any text"],
  "gate": [                                    // read-back assertions, checked against the OUTPUT
    "single-weight wobbly black ink line only, no coloured linework",
    "flat cream fills; no shading, gradients, or painterly texture",
    "ground is one flat pack-palette colour",
    "<= 4 elements, generous negative space",
    "NO text, letters, or numbers anywhere",   // because textPolicy is "none"
    "any hands are loopy and non-anatomical (this look has no realistic finger-count to get wrong)"
  ],
  "maxElements": 4,
  "textPolicy": "none"                         // none | diegetic | furniture (v0.12)
}
```

- **Consumed two ways.** (a) **Quick mode** — the `on-brand-image` skill takes a pack path + a scene
  and generates + reads-back, no `universe.json` in sight. (b) **Full mode** — a `register` MAY set
  `stylePack: "<id-or-path>"` to source its `anchor` + `rejectedPoles` from a pack instead of inlining
  them, so a universe's canon renders and a one-off image share ONE definition of the look. Registers
  that inline their anchor stay valid; the field is additive.
- **Portable (mirrors §3a self-containment).** A pack resolves every ref within its own folder, so it
  can be copied anywhere and still generate. A pack may live standalone OR inside a universe
  (`reference/style/<pack>/`); the skill only ever needs the pack path.
- **The gate is the load-bearing half.** A pack without a `gate` is a mood board. The gate is what
  turns "looks roughly right" into a checkable read-back (§3.5): generate, verify each assertion
  against the pixels, re-roll the specific failure. The finger-count defect is a gate concern, not a
  prompt concern — and an ink-line look whose hands are deliberately non-anatomical sidesteps it by
  construction.
- **`textPolicy` (v0.12, REQUIRED on new packs).** One of three values. A blanket text ban was the
  wrong shape: it conflated three different things, and it silently degraded artifacts whose whole
  job is to explain something.

  | value | means | example |
  |---|---|---|
  | `none` | no glyphs at all | a mark or icon destined for a cutout |
  | `diegetic` | text that exists IN the depicted world is allowed and must be spelled correctly | a book cover in frame, a sign, a jar label, a spine |
  | `furniture` | `diegetic`, PLUS explanatory chrome the image itself carries | a hero strip's title bar, per-panel captions, footer bar |

  The prohibition that survives all three: **never render text the surrounding
  layout already supplies.** A spread must not burn in the caption the page lays
  out beside it, and a wiki page's H1 does not belong inside its own hero. That
  duplication was the real defect the old ban was reaching for. It is about
  duplication, not about glyphs.

  **Any text a pack permits is gated, never trusted.** The caller declares the exact
  strings; the read-back (§3.5) verifies each one character-exact against the pixels;
  a misspelling or a dropped glyph is a DEFECT and forces a re-roll from scratch. This
  is the same posture the framework already takes on a cover's title. Packs written
  before v0.12 with no `textPolicy` are read as `diegetic`, which matches what most of
  them meant.

### 4.7.1 Lookbook (the portable VARIED vocabulary)

A **Lookbook** is the complement of a Style Pack. A Style Pack defines ONE look and every render
matches it; a Lookbook defines a curated but intentionally **varied** family — a wardrobe/fashion, a
range of building silhouettes, a crowd of faces — and every render must draw from the range while
**differing** from any single exemplar. It exists because the alternatives are wrong for variety: a
`motif`/`prop` (SPEC §12) forces a thing to render *identically*, and a Style Pack is a render medium,
not subject content. Improvising a bare folder of "clothing refs" is the drift it kills.

```
<lookbook>/
  lookbook.json
  refs/*.png   # 4-12 deliberately VARIED exemplars; range is the point
```

```jsonc
{
  "id": "christofuturist-fashion",
  "kind": "lookbook",
  "name": "Christofuturist Fashion",
  "refs": ["refs/a.png", "..."],              // 4-12, pack-relative; NO single anchor (nothing to match)
  "aesthetic": "modest, dignified, individual, timeless-yet-modern Kingdom dress",
  "varietyRule": "dress each person differently, drawn from this range; never a uniform, never two people matching",
  "gate": [                                    // checked against the OUTPUT — VARIETY assertions
    "no two people are dressed alike",
    "not one palette across the whole crowd",
    "individual, dignified, modest dress (never a commune uniform)"
  ],
  "minRefs": 3
}
```

- **Consumed** by a renderer (`on-brand-image --lookbook`): sample 2-4 refs (varying the subset), prepend
  `varietyRule`, add the `gate` to the read-back, re-roll a uniform result from scratch. It rides
  ALONGSIDE a Style Pack (pack = medium, lookbook = varied subject).
- **Bound to a universe** through a **craft-canon register-rule** (§13) whose `rules` name the lookbook,
  so uniformity can never silently return. (First use: rule `godly-aligned-dress` → lookbook
  `christofuturist-fashion`, because a Christofuturist community that dresses in one beige linen reads as
  a commune, not a flourishing Kingdom.)
- **The gate is load-bearing, and it checks VARIETY.** A lookbook without a variety gate is a mood board
  that drifts back to a uniform on the first render.

### 4.8 Form (what makes a work the KIND of thing it is)

**Canon is the matter. A form is what shapes it. A work (§4.9) is canon given form.**

A **Form** is a typed contract for a kind of work. It is the layer the standard was missing:
`Story Spec` (§4.3) conflated *what kind of thing this is* with *this particular one*, and baked a
story's required fields into the generic primitive, so only stories were expressible.

A form is a **distributable artifact**, not a config block: it carries an id, a semantic version, an
author, and may `extend` another form rather than copying it. The framework ships a starter set; it
is explicitly **not a closed set**. The intended shape is a registry others publish into.

**Name the treatment, not the medium.** If a form's `id` equals its `surface.medium`, it has taken
the name of a whole category for one specific way of working in it, and every sibling treatment is
left with nowhere to live. `scrolling-diorama`, not `parallax-scene` — mouse-driven, horizontal and
dolly scenes are all parallax scenes, and none of them fit a contract that hardcodes vertical scroll,
edge-pinned bands and sink-behind occlusion. The MEDIUM stays a string in `surface`; it earns being
a primitive when a SECOND form targets it and the two must agree on something, not before.

```jsonc
{
  "id": "storybook", "version": "2.1.0",
  "extends": null,                       // "storybook@2.0.0" to fork without copying
  "author": "agenticbranduniverse.com/registry",

  "surface": { "medium": "picture-book", "geometry": { "spreads": 24, "aspect": "2:3" } },

  // BY KIND, never by id. A marketplace form cannot know your canon.
  "requires": [ { "kind": "character", "min": 1 }, { "kind": "setting", "min": 1 },
                { "kind": "style-pack", "min": 1 } ],

  "slots": [ { "id": "spread", "repeat": "$.spreads", "type": "generated",
               "schema": { "beat": "string", "characters": "entity[]", "location": "entity" } },
             { "id": "cover", "type": "generated" } ],

  // capability, not provider. `pin` only where the model IS the look (see below).
  "generators": [ { "for": "spread", "capability": "image", "accepts": "reference-images",
                    "pin": null },
                  { "for": "spread", "capability": "text" },
                  { "for": "spread", "capability": "audio", "optional": true } ],

  "invariants": {
    "perSlot":   [ { "id": "no-text-in-art", "check": "judged" },
                   { "id": "palette-only",   "check": "computed" } ],
    "crossSlot": [ { "id": "character-identity", "check": "judged",
                     "scope": "all slots binding the same character entity" } ]
  },

  "emits": [ "book-manifest.json", "spreads/*.webp", "narration/*.mp3" ]
}
```

**`requires` names kinds; the work binds ids.** This is the whole mechanism that lets a form ship to
a brand it has never seen. The form says "I need at least one character"; the work says "the
character is `jerry-man`".

**A computed invariant carries an evaluable `rule`, not just an id.** A generic engine cannot run a
check it knows only by NAME. Three ops cover the cases so far, and each is about a RELATIONSHIP
between slot entries, which is what a crossSlot invariant IS: `monotonic` (a field ordered by
another field), `count` (how many entries match a predicate), `extreme` (a matching entry sits at an
end). An invariant marked `computed` with no `rule` is reported as a problem rather than silently
passing. Be honest in the other direction too: if a form's own flagship work legitimately violates a
rule, that rule is `judged` with a stated exemption. A computed rule your own work fails is a lie
with a green checkmark.

**Per-slot vs cross-slot invariants, and why it matters.** A per-slot invariant is checkable against
one output in isolation ("this image contains no text"). A **cross-slot** invariant is only checkable
across several ("the character on spread 19 is the same person as on spread 3"), and it is the
expensive, hard class: it is what forces locked goldens, it is what the reference matrix (§12) exists
to serve, and it cannot be satisfied by making each slot individually good.

This makes "simple deliverable" versus "complex deliverable" a **property of the ontology rather than
a matter of taste**: a meme has zero cross-slot invariants, a share card has zero, a flyer has one
(brand consistency), a storybook has the hardest one there is. Complexity is cross-slot invariant
count, and a projection declares its own.

**A cross-slot invariant is ITEMIZED and checked against the golden, never pairwise.** Two failures,
both found 2026-07-23 by generating three spreads of a locked character and inspecting them:

- *Itemized.* A projection that declares one invariant reading "character identity holds across every
  spread" throws away all its resolution. The entity carried twelve specific invariants; ten held and
  one (`translucent-holographic-digital-being`) failed in every spread, rendering as opaque felt
  instead of a hologram. A judge asked "is this the same character?" says yes and ships it. A judge
  asked about each declared invariant catches it. **The cross-slot rule therefore names the entity's
  invariant list as its checklist and is evaluated per item per slot**, rather than as one holistic
  question.
- *Against the golden, never pairwise.* All three spreads drifted the SAME way, because each
  inherited the same drift in the master-to-generation step. A spread-to-spread consistency check
  finds them perfectly consistent with one another and uniformly wrong. **Consistency is not
  fidelity.** Every slot is judged against the locked golden.

**Slots are heterogeneous.** A slot is `deterministic` (emitted by code, e.g. an SVG layout) or
`generated` (a model produces it). A share card is one projection containing both: a deterministic
text panel beside a generated art panel. The pre-v0.6 "renderer" concept could not express this at
all, which is why composite deliverables kept being hand-assembled.

**Provider quirks are first-class, and they belong to the generator, not the style.** A style pack's
`rejectedPoles` say what is off-brand. A **quirk** says what a specific model gets reliably wrong
regardless of brand, and it is therefore a property of the *capability binding*, not of the look. It
survives a change of brand and dies with a change of provider, which is the opposite of a rejected
pole.

```jsonc
"generators": [ { "for": "spread", "capability": "image", "pin": "gpt-image-2",
    "quirks": [
      { "id": "artwork-within-artwork-renders-inverted",
        "seen": "When a person is depicted drawing or holding a picture, the depicted picture is rendered upside down relative to the viewer.",
        "counter": "Any picture, page, book, or artwork shown inside the scene must be RIGHT SIDE UP and correctly oriented to the viewer. Never inverted, never rotated.",
        "check": "judged" } ] } ]
```

Three rules make this useful rather than a notes file:

- **The `counter` is appended to every compiled prompt for that slot**, automatically. A quirk you have
  to remember is a quirk you will ship.
- **The `check` becomes a gate item**, so countering it in the prompt is never assumed to have worked.
  Prompts do not reliably beat a model's priors; that is why the gate exists at all.
- **Quirks travel with the pin.** Removing the pin removes the quirks, because they were never true of
  the capability, only of that model.

This is where hard-won provider knowledge accumulates instead of being re-learned per project. It is
the same discipline as the rest of the standard: the thing that must not be forgotten becomes data
that is passed, rather than prose someone is supposed to recall.

**Registers bind PER SLOT, and a composition may weave several.** A book is not written in one
visual language: narrative spreads carry a painterly storybook register while the diagram woven
between them is a flat characterless plate. Binding one style pack per composition makes that
inexpressible and quietly forces every artifact into a single voice. `bind.style-pack` therefore takes
either a single pack or a map of slot id to pack, with a `default`. Goldens bind the same way.

**A register that rejects the cast must never be handed the cast.** The plate register in the
reference universe lists the storybook characters among its `rejectedPoles`, because a plate is a
diagrammatic gesture and not a scene. Passing a character's locked master into that slot is a
contradiction between two parts of canon, and it must be **refused by the compiler**, not left for the
model to resist while holding a reference image that argues the opposite. Verified 2026-07-23: one
composition produced three narrative spreads carrying the character golden and one plate carrying
none, in two registers, from a single contract.

**Feasibility must cover the SCENE against canon, not only geometry.** Plan-time checking currently
catches an undeliverable surface and stops. It does not catch a composition whose *content*
contradicts a declared invariant. Earned the same day: a book brief about serving churches was planned
against a character whose canon states `no-religious-iconography-anywhere-in-this-universe`, and the
render duly produced steeples. Nothing was broken except the plan, and the plan was never checked. A
composition that asks for what canon forbids should be refused before generation, exactly like a bad
aspect ratio.

**A `deterministic` slot MUST name its emitter.** A slot typed `deterministic` with no `emitter`
field is not deterministic, it is unspecified: nothing can produce it and the type is decoration.
Earned 2026-07-23 by trying to execute a contract whose text panel declared `{recipient, body,
signoff}` and could not be laid out, because field NAMES are not a layout. `explanatory-plate` was
runnable only because it happened to name one. Normative: `type: "deterministic"` requires `emitter`.

**A projection's `surface` must be FEASIBLE against its own generators.** A contract can be
internally coherent and still describe an artifact nobody can make. Earned the same day: a card
declared a 1200x1200 surface with a two-thirds text split, which makes its art panel 400x1200, an
aspect of 0.333. No image generator produces 0.333; the tallest commonly available is 0.667. The
contract was valid, reviewed, and undeliverable.

So a projection carries the producible aspects of the capability it depends on, and **feasibility is
checked before the run, not discovered inside it**:

```jsonc
"generators": [ { "for": "art-panel", "capability": "image",
                  "producibleAspects": [1.0, 0.667, 1.5],   // what the capability can actually emit
                  "tolerance": 0.25 } ]
```

The composer resolves each generated slot's geometry from `surface`, compares it to
`producibleAspects`, and refuses to start if no aspect is within tolerance. This is a **`computed`**
invariant and it belongs at plan time: the alternative is discovering it an hour into a composition,
or worse, silently cropping to fit and losing exactly the edges the composition needed.

**When a producible aspect does not match the surface, CONFORM by self-bleed, never by flat bars
and never by cropping load-bearing content (§cover-conform, earned 2026-07-25).** The common case is
a cover: image models emit the tallest producible portrait at 2:3 (0.667), while the reader page is
3:4 (0.75). The gap is bridged by `conform_cover.py` (in the `cover` skill), whose default `--mode
pad` widens the render with **blurred self-bleed side panels**: the art's own colors, scaled and
blurred, fill the panels so the padding reads as an intentional soft matte and vanishes into the
composition. Two things are NORMATIVE and were both learned by shipping the wrong one: (1) the fill is
a self-bleed, **never a flat color** — a flat bar seams visibly against the art's textured, vignetted
background, and passing the aspect check does not make it look intentional; (2) `--mode crop` (equal
top/bottom trim) is licensed ONLY when the render carried a safe-margin block, because cropping a
cover's height eats its title. The default cover fill is self-bleed with no keyline; a keyline is a
per-universe stylistic opt-in, not the default. Producing the conform by hand (a universe-local pad
script, a flat-fill one-liner) is the hand-roll this convention exists to retire: call the tool.

**Generators declare a capability, with an optional pin.** Faithful reproduction does not come from
pinning a provider, because generative output is stochastic regardless (§4.6, determinism ceiling). It
comes from three other places: the **goldens** (pass the same locked reference, get the same
character), the **gate** (verify and re-roll, which is what converts stochastic output into reliably
correct output), and recorded **provenance**. So a slot declares what it needs and the runtime binds a
provider, EXCEPT where the model itself is the aesthetic. Where a locked golden carries the look, any
competent provider works. Where there is no golden and the model's own hand is the register (a fresh
ink-line illustration), the provider is part of the brand and must be pinned. Every render records
provider, model version, params, and the exact refs passed, so drift is always diagnosable.

### 4.9 Work (canon given form)

```jsonc
{
  "id": "not-every-fire-is-holy",
  "form": "storybook@2.1.0",
  "bind": { "character": ["jerry-man", "brenda-gentry"], "setting": ["the-yard"],
            "style-pack": "warm-oil-curdles-cold" },
  "slots": { "spread": [ { "beat": "…", "characters": ["jerry-man"], "location": "the-yard" } ] },
  "writesBack": [ { "kind": "character", "id": "anjali-sambalu", "locked": true } ],
  "gates": { "wordsBlessed": "2026-07-15", "subjectApproval": "gated:brenda-gentry" }
}
```

A work is **not** an "instance". A book's identity is not derived from being an instance of a
book-shaped thing. A work carries AUTHORSHIP that exists in neither the canon nor the form: `beats`
and `spine` are new facts about the world, and `writesBack` lets a work add to canon outright.

That is also why **projection** names the *relationship* here and never a primitive. A projection is
determined by (object, map); a work is not determined by (canon, form), and a shadow does not change
the object it falls from. The fit varies by form, and the slot schema is the measure of it: a form
whose slots are derivable is near a true projection, and one with a rich authored schema is far from
it.

`logline`, `spine`, `refrain`, and `beats` are **not** universal fields. They belong to the storybook
form's slot schema and craft-canon (§13), which is where they were always story-specific. A flyer
work has none of them and is now expressible.

**Back-compatible, twice over:** `StorySpec` is retained as an alias for a work whose form resolves
to `storybook`; a universe with existing `stories/*.json` and no form declared validates unchanged
and is treated as `storybook@1`. And a work keyed with the pre-0.14 `projection` field still loads,
because a rename that silently orphans the things it renamed is the failure mode renames are famous
for.

### 4.10 The Composer, the Compiler, and the Gate

The render step is three parts with genuinely different natures. Collapsing them is what produces
either a rigid template engine (no composer) or an unaccountable one (no gate).

| Part | Nature | Answers |
|---|---|---|
| **Composer** | agentic, generative | *What should exist?* Plans slots and their order, decides which goldens each slot needs, sequences modalities, handles composite slots. |
| **Compiler** (§4.6) | deterministic | *What exactly do I send?* One planned slot → exact prompt + ref list + QA checklist, compiled from canon so nothing load-bearing is retyped. |
| **Gate** | adjudicating | *Does this artifact satisfy this stated invariant?* Returns PASS or DEFECT with evidence; a defect re-rolls THAT SLOT, never the artifact. |

**The gate is agentic wherever the invariant is perceptual.** The meaningful split is not
agentic-versus-not, it is **generative versus adjudicating**. Every invariant is therefore typed:

- **`computed`** — checkable by pure code against the artifact (palette-only, content fits the
  viewBox, a column header fits its column, required metadata present). Free, and it runs every time.
- **`judged`** — requires a model to look (no text anywhere in the image, hands non-anatomical, the
  digit count, character identity across spreads).

**A `judged` check is a ROLE, not a service, and inside the composer it is free.** The load-bearing
property is that the judge has not seen the plan, which is a fact about context rather than about
transport. In the runtime the composer already has model access, so a verification step scoped to
golden plus slot plus checklist is simply another turn. Treating the judge as an external service to
call is a modelling error: it invents a dependency the runtime does not have, and it makes
verification look like something bolted on rather than something an agent does by default.

A projection's token cost is approximately its count of `judged` invariants times its slots, which is
a useful thing to be able to read off a contract before running it.

**The judge must not be the maker (normative).** A `judged` invariant is evaluated in fresh context,
given the artifact and the invariant ONLY, never the plan that produced it. An agent shown its own
reasoning defends it rather than inspecting the pixels. Earned 2026-07-23: a three-element graphic
shipped with one element deliberately missing its defining feature, because the maker "knew" the
omission was intentional variety and read its own intent instead of the output; an observer with no
access to the plan caught it instantly.

**A subagent is the default judge (normative).** Independence is a property of *context*, not of
vendor, process, or billing account. A fresh subagent dispatched inside the runtime that is already
composing satisfies the rule completely: it never sees the plan, and that is the only thing the rule
asks for. It also costs no second credential and no second provider.

An implementation MUST therefore be able to fill the judge role without an API key. The composer
itself MUST NOT judge; it emits, per slot, a **judging brief** naming exactly what a judge is shown:

```jsonc
{ "artifact": "<path>", "reference": "<path>", "mode": "identity" | "style",
  "checklist": ["<invariant id>", "..."],
  "withheld": "the plan, the beats, the compiled prompt, and the intent" }
```

The brief is what enforces the separation. Asking an agent to disregard what it already knows is not
a control; handing a different agent a bounded brief is.

- **`mode: identity`** judges against a character golden: *is this the same subject?*
- **`mode: style`** judges against a style-pack anchor, whose SUBJECT is explicitly irrelevant: *is
  this the same visual voice?* Asking the identity question of a characterless plate is nonsense, and
  asking only the style question of a character lets a stranger through with matching linework.

**The checklist comes from the contract, not from a bound entity.** It is this projection's `judged`
invariants plus the resolved provider's quirk checks, unioned with a bound entity's itemized
invariants only where one is actually bound. Sourcing it from an entity alone means a projection with
no cast has no checkable rules, so its declared invariants are computed and then discarded. Found
2026-07-23 by the first characterless *book*; every earlier characterless deliverable was a single
plate with nothing to judge across.

**An absent verdict is not a pass, and neither is an unreadable one.** A slot awaiting judgment is
`NEEDS-JUDGMENT`, which is distinct from both PASS and DEFECT: the artifact exists and is sound, and
one check has not run. Re-running MUST NOT regenerate it, because re-rolling something nobody has
judged pays twice and discards the very artifact the judge was about to look at.

**Failure model: park the slot, finish the composition, report.** When a slot exhausts its re-rolls,
it is marked DEFECT, the remaining slots continue, and the artifact emits as incomplete with a precise
per-slot report. A human then repairs one slot rather than re-running a book. This requires **durable
per-slot state across a long unattended run**, which is a load-bearing requirement on the runtime and
the subject of §14.


### 4.11 Deterministic Generator (the asset that is CODE)

A **Deterministic Generator** is a program in the universe that DRAWS an asset instead of prompting
for one. It is the typed home for the rule the framework already asserts everywhere else and never
gave a place to live: *deterministic graphics render in code, not an image model.* Marks, favicon
sets, starfields, clouds, grids, scale rules, diagram furniture, colour-chip sheets — anything whose
correctness is a NUMBER rather than a judgement — belongs here.

Before this section, such code existed as loose scripts beside the assets they wrote, with ad-hoc
paths, hand-written provenance, hand-written install copying, and no discoverability. That is
framework-shaped work, so the framework owns it.

```
<universe>/generators/<id>/
  generator.json     # the manifest (below)
  generate.py        # the entrypoint; writes into out/
  out/               # generated artifacts + their .recipe.json sidecars
  proof/             # optional: contact sheets a human approved (see "the gate", below)
```

```jsonc
{
  "id": "north-star-cross-favicons",
  "name": "North Star Cross favicon set",
  "kind": "generator",
  "entrypoint": "generate.py",
  "determinism": "seeded",                  // "pure" (no randomness) | "seeded"
  "seed": 20260727,                          // REQUIRED when determinism is "seeded"
  "params": {                                // every knob, as DATA (see below)
    "markSpan": 0.71,
    "ground": "#0A0B10"
  },
  "inputs": ["reference/north-star-cross/mark-3d-gold-transparent.png"],
  "outputs": [
    { "path": "out/favicon.ico", "description": "multi-resolution .ico, 16 + 32 + 48" }
  ],
  "install": {                               // where an output lands in a consuming repo
    "out/favicon.ico": ["public/favicon.ico", "src/app/favicon.ico"]
  },
  "proof": {                                 // how a human checks it; see "the gate"
    "sheet": "proof/contact-sheet.png",
    "assertions": ["the mark reads at 16px on BOTH a light and a dark ground"]
  }
}
```

- **Every parameter is DATA, never a buried constant.** This is the load-bearing rule, and it is not
  tidiness. A generator's constants are its contract with the artifact, and two of them silently
  meaning different things is the characteristic bug of this primitive: a favicon generator carried
  `MARK_SPAN` as "fraction of the tile the mark fills" while the SVG it also emitted used the same
  number as an SVG `scale()`, which multiplies the whole coordinate system. The two disagreed by
  30%, and the descender was sheared off the bottom edge of every raster. Params in `generator.json`
  are what let a reviewer see the knobs without reading the code, and what force a derived value to
  be *derived* rather than retyped.
- **The gate is a PROOF, not a read-back.** §3.5 gives a render read-back because a model is
  stochastic and each output must be re-checked. A generator is reproducible, so re-checking every
  run is waste; what it needs instead is a **proof sheet a human approved once**, rendering the output
  at the sizes and on the grounds where it will actually be seen. Proof at real size, never at
  convenient size: the same favicon set looked correct at 512px and was clipping its descender at 16.
  A generator whose output is only ever viewed zoomed-in is untested.
- **Assumptions in a generator are testable, so test them.** Because it is cheap and repeatable, the
  cost of checking a design belief is one re-run. A ruling that "the 3D bevel turns to mush below
  48px, so small sizes use the flat vector" survived only until it was proofed side by side; the
  bevel read *better* small, because the lit/shadow split preserved the mark's long descender where
  the flat silhouette collapsed. State the assumption in a comment, then disprove it.
- **Provenance is the same contract, different fields.** A generated artifact still carries a
  `.recipe.json` sidecar (§3.2), but it records `generator` + `params` + `seed` + input hashes rather
  than `provider` + `prompt` + `refs`. The invariant is unchanged: no asset without its recipe.
- **`install` makes the universe the source of truth for derived assets.** A favicon set copied by
  hand into three sites is three sites that will drift, and they did: one shipped a mark from a
  rebrand fourteen months stale while another shipped an incomplete set. The manifest declares where
  each output belongs; installing is idempotent and reports only what changed.
- **Determinism is declared and enforced.** `pure` means byte-identical output for identical inputs.
  `seeded` means byte-identical *given the seed*, which must therefore be in the manifest and never
  in the code. Wall-clock, `random()` without a seed, and dict iteration order are defects.

Generators are the counterpart to Style Packs (§4.7): a pack governs what a MODEL should produce,
a generator replaces the model entirely where the answer is computable. When an asset can be
expressed either way, prefer the generator, because it is reproducible, reviewable, and free.


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

Everything above already exists in Nation of Fire, informally. Agentic Brand Universe is the act of naming it.

| Agentic Brand Universe layer / primitive | Nation of Fire today | Gap to close |
| --- | --- | --- |
| Canon (entities + relations) | `nof-universe/CANON.md` (prose) + typed `canon/entities` | promote to typed records; keep prose as fields |
| Refs (load-bearing) | `nof-universe/canon` (typed) + `assert.sh` → the engine | **built 2026-07-15**; generalized `nof-*` → universe-agnostic (the engine); **reference implementation made self-contained 2026-07-18** — all canon assets moved into `nof-universe/` (`assetRoot: "."`), so the universe resolves every reference inside its own repo and the folder was renamed `universe/` → `nof-universe/` |
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
- **Canon storage → one repo per universe.** Like `nation-of-fire/nof-universe` today. A shared
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

## 11. Skills & Identity layer (v0.3)

The framework's operations — resolve an entity's refs, sweep canon before naming, register a new
entity, read back a render, gate voice, run a renderer — are **universe-agnostic**. They differ
between universes only in *data*, never in *procedure*. So:

> **A universe ships data; the framework ships skills.** Standing up universe #2 is filling in canon +
> an identity block, not forking a pipeline. A skill must NEVER hardcode a universe's name, path, mark,
> theme, cast, or voice terms — it takes a target universe and reads them.

**The identity block.** Every `universe.json` carries an `identity` object: the constants a universe is
known by, that generic skills read.

```jsonc
"identity": {
  "mark": "A NATION OF FIRE story",     // the "made in this universe" byline a renderer stamps
  "platformUniverseId": "nation-of-fire",// registry id when shipping to a shared platform
  "theme": "gold-belongs-to-god",        // brand token set / palette id
  "closingOrnament": "wisp",             // a recurring closing motif, if any
  "voice": { "capitalize": ["Kingdom","Spirit"], "oneWord": ["Christofuturist"] }, // voice-gate rules
  "subjectApproval": { "realLivingPerson": "requires-blessing" }, // requires-blessing | none-required
  // `none-required` abolishes the per-subject blessing gate universe-wide. Entity validation then
  // stops demanding realPerson.approval.state, because there is no gate left to enforce (v0.6.1).
  "register": {                              // the universe's illustrative style (v0.4)
    "name": "detailed comic book",           // named style, defaulted by start-universe
    "anchor": "reference/register/style-anchor.png", // content-neutral swatch, passed FIRST every render
    "rejectedPoles": ["photoreal", "anime", "washed-out"]
  }
}
```

**Register (v0.4).** A universe renders in one illustrative style. `identity.register` names it and
points at a content-neutral **style anchor** the renderer passes as the first reference on every
render, with `rejectedPoles` baked as negatives. A per-property `register` (SPEC §4.3) may still
override it. `start-new-story-universe` defaults `register.name` to "detailed comic book" and locks
the anchor via a style-lock step.

**Craft-canon is data, not skill prose.** Genres, spines, and register rules a universe discovers
(SPEC §3.5, §5) are typed canon records the renderer reads — NOT paragraphs buried in a skill file.
Craft rules living as skill-file scar tissue is the exact drift this framework exists to kill (§1); a
genre like "expectant biography" or a spine like "obedient-servant" is a record stories declare against,
so it is paid for once and reused by every future universe that adopts it.

**Two skill tiers.**
- **Framework skills** (in the `agenticstory` plugin, parameterized by `--universe <path>` or by
  discovering `universe.json` upward): ref resolution, casting sweep, entity registration, render
  read-back, voice gate, and each medium renderer. Written once; every universe inherits them.
- **Universe data** (in the universe repo): canon (entities/relations/stories), assets (self-contained,
  §3a), the `identity` block, and craft-canon records. No per-universe skill *code* — only data the
  framework skills consume.

The tell that a "universe-specific" skill is really a framework skill wearing a costume: renaming the
universe folder edits the skill. If a rename touches a skill, that skill was hardcoding a universe that
belonged in its `identity` block. (The Nation of Fire audit, 2026-07-18, found all nine of its skills
were generic procedure over universe-specific data — zero needed bespoke code.)

## 13. Craft-canon records (v0.4.1)

Craft-canon is data, not skill prose (SPEC §11). A universe's discovered craft lives as typed records
in `canon/craft/*.json`, loaded and validated by the engine:

- **spine** — a story's arc invariant (obedient-servant, thesis, primer, testimony, ...). A story's
  `spine` field names one. Craft-canon checks a story against ITS declared spine, never one assumed shape.
- **genre** — a book type with its own format canon (e.g. the expectant biography, the visualized
  epistle). A renderer reads the genre a property declares.
- **register-rule** — a universe-wide visual or narrative law (e.g. "gold belongs to God",
  "testimony over prediction", "awe not horror") the renderer honors on every unit.

Each record: `{ id, kind, name, summary, rules, origin }`. `rules` (or `summary`) is required; `origin`
records where a rule was discovered. The collection is OPTIONAL: a universe with no `canon/craft/`
validates unchanged. This is how a genre discovered making one book (SPEC §5, craft is discovered then
encoded) is paid for once and reused by every future property and universe.

## 12. Reference-matrix standard (v0.4)

"Locked" must mean something checkable per kind. The reference matrix is the canonical set of
reference shots an entity needs before it is fully renderable, so tooling can report
under-referenced entities the way the gate reports missing files.

- **character** — the anti-uncanny-valley set: `face-neutral`, `face-3q`, `expressions`,
  `forward-fullbody`, `profile-left`, `profile-right`, `back`, `signature-pose`. Minimum
  (`requiredForRender`) is `forward-fullbody` + `face-neutral`; the rest strengthen identity
  consistency across renders. Real people are generated from a photo stack (never a
  painting-of-a-painting); fictional characters from a locked design.
  - **`structured.requiredForRenderOnLock` (v0.11) — a per-entity override of the kind's minimum.**
    The matrix minimum above is a per-KIND default, and some entities need a STRICTER gate: a
    character whose three-quarter face carries a signature the front view cannot show should not
    become renderable without `face-3q`. Authors kept discovering this and independently inventing
    this exact field in their universes, where nothing read it, so the stricter intent silently did
    nothing. It is now first-class: when present it REPLACES the kind's required list everywhere the
    engine computes the gate (`lock-shot` promotion and `lock-level`). It may only ADD to the kind
    minimum, never drop below it, because a kind's minimum is what makes "locked" mean something.
    Omit it to accept the kind default, which is the common case.
  - **`structured.scale` (v0.10) — relative height is canon, not a per-spread guess.** `{ "height":
    "5 ft 8 in", "relativeTo": { "<entity-id>": "several inches shorter than" }, "scalePlate":
    "reference/<id>/scale-two-up.png" }`. Every entity in the matrix is described ALONE, so two
    characters sharing a frame have a dimension that no record states: the model makes them the
    same height, or reverses them, and the drift is invisible until somebody who knows them says
    "he is much shorter than that." This is the v0.9 setting lesson applied to people. The
    compiler emits a `RELATIVE SCALE` line ONLY when two or more in-frame characters declare a
    relation to each other, so a solo spread is byte-identical to before. An optional `scalePlate`
    is a two-up plate of the pair at true relative height. Advisory: a character with no `scale`
    still locks and still renders; `lint-universe` warns `CHARACTER-SCALE-ONE-SIDED` when one
    character declares a relation its counterpart does not mirror, because two half-records drift
    apart and then contradict each other.
  - **`structured.altLooks` (documented in v0.10; load-bearing in the compiler well before it).**
    A named look that REPLACES part of the entity's identity for the spreads that select it:
    `{ "anchorPhoto", "sheets", "supersedes": [], "invariants": [], "dropSheets": [],
    "keepSheets": [], "keepPhotos": false, "render": {} }`. `supersedes` removes base invariants
    the look contradicts and `invariants` adds its own, so the QA checklist, the prompt block, and
    the computed negatives all agree by construction. `dropSheets` removes base sheets the look
    contradicts, because **a reference image outranks a word**: a look whose invariant said "neck
    completely bare" still had the adult pendant sheet passed, and the necklace rendered. An alt
    look **auto-drops the base FACE sheets**, since the look's own `anchorPhoto` is the face.
  - **Declared-future (prophetic) looks (v0.10): `keepSheets`, `keepPhotos`.** A universe that
    permits expectant work renders a person's declared future, and that look inverts every
    assumption above: **the face is CONTINUOUS, the body changes, and the future has no
    photograph.** With no `anchorPhoto` and the face sheets auto-dropped, only BODY sheets reach
    the model, and those are the exact silhouette the look supersedes, so the output is a stranger
    with the right build. `keepSheets` names base sheets to pass anyway (the continuous face);
    `keepPhotos` passes the real person's photo stack, which is otherwise default-look only.
    `dropSheets` stays authoritative where the two overlap, so an explicit contradiction always
    outranks a keep. A look supplying no face source at all is REFUSED by `compose-spread` at
    compile time (which costs nothing) and warned by `lint-universe` as `LOOK-NO-IDENTITY-ANCHOR`
    one step earlier still. Each era gets its own key (`era-2028`, `era-2030`) and its own
    invariants, so a read-back checks the future body against what was declared rather than
    against today's.
  - **Locking an alt-look's art:** `lock-shot <universe> <id> <shot> <path> --look <key>` writes
    into `structured.altLooks[key].sheets` instead of the default matrix. It deliberately never
    touches `requiredForRender`, which is the DEFAULT look's gate: an era plate must not be able
    to satisfy it, or a character with no present-day body sheet would read as gate-real off a
    future one. An unknown look key is REFUSED rather than created, because a typo would
    otherwise mint a look nothing selects and no read-back ever checks.
- **setting** — the existing `contract`: `turnaround`, `emptyPlates[]`, `blueprint` (files) plus
  `map`, `blocking`, `dressing` (descriptors), **and `scalePlate` + the `scale` descriptor (v0.9)**.
  - **`scalePlate` (file) and `scale` (descriptor) exist because AN EMPTY PLATE CANNOT PROVE SIZE.**
    `emptyPlates` are people-free on purpose, so that a setting reference never bakes a character's
    face into the room. That rule is right and it stays. But it has a cost nobody priced: a
    figure-free interior has no unit of comparison, so a room reads as whatever size the model
    guesses, every render inherits the guess, and the drift is invisible until somebody who knows
    the place says "that room is supposed to be much bigger than that." A plate cannot be judged on
    a dimension it does not depict.
  - **A `scalePlate` is the same room with ANONYMOUS SCALE FIGURES**: a few people, small in frame,
    at a distance, turned away or in profile, faces not readable, plain clothing, never a canon
    character and never the subject. That satisfies the identity rule (no face is baked) while
    making size checkable. It is a SEPARATE file from `emptyPlates`, never a replacement: renders
    still cast an empty plate, and the scale plate is what a human and a linter read the room's size
    from.
  - **The `scale` descriptor states the size in HUMAN TERMS** ("a circular hall about 80 feet across,
    dome 45 feet at the crown, the fire opening about 12 feet wide"), because prose survives a
    re-render and a plate does not. It is passed in every prompt like `dressing`.
  - Advisory in v0.9, like the rest of the matrix: a setting with no `scalePlate` still locks and
    still renders. `lint-universe` warns (`SETTING-NO-SCALE-PLATE`) so the gap is visible before it
    is expensive. Earned 2026-07-25 on `christofuturist-home`, whose hearth room rendered small and
    cramped through a whole book because nothing in its contract said how big it was.
- **visual-metaphor** — a locked master plus `state` plates (the object across its argued states).
- **prop / motif** — `hero` plus `detail` crops.

**`lock_level(entity) -> stub | partial | locked`** (engine) reports completeness against the kind's
matrix. It is **advisory** in v0.4 and back-compatible: an entity that predates the matrix, or uses
its own sheet-key names, reports `partial` when its own `requiredForRender` resolves — it is not
broken, just not matrix-complete. The load-bearing gate (`assert_story` / `assert_spread`) is
unchanged: a missing REQUIRED sheet is still a hard error. A renderer MAY require `locked`.

## 14. Why this runtime is Managed Agents (v0.6)

This section is normative about the *shape* of the workload, not about a vendor. It exists because
"use a hosted agent runtime" is the kind of claim that sounds like a preference, and it is not one:
the composer's requirements fall out of §4.8 and §4.10 mechanically.

**What composing one non-trivial projection actually is.** Not a request. A storybook composition is
tens of slots; each slot is a compiler pass, one or more generator calls across different modalities,
then one or more gate evaluations, some of which are themselves model calls in fresh context. Slots
that fail re-roll. The whole thing runs for tens of minutes to hours, and the operator is not watching.

Five requirements, each traceable to a section above:

1. **Long-running and unattended.** From the failure model (§4.10): the composition continues past a
   defective slot and reports at the end. There is no human in the loop mid-run to answer a question,
   so the runtime must not depend on one.
2. **Durable state per slot.** Parking slot 19 and finishing slots 20 through 24 is only possible if
   per-slot state survives. A restart in the middle of an hour-long composition must not lose the
   nineteen slots that already passed their gate.
3. **Isolation.** A composer runs generated content, fetches references, and writes artifacts. Where
   one runtime serves several brands, one brand's canon and outputs must never reach another's.
4. **Secrets it holds but never sees.** Generators are third-party providers and publishing targets.
   The composer needs credentials at call time and must not embed them, which is what a vault is for.
5. **Skills, not a mega-prompt.** §4.10 requires the compiler to be deterministic and the craft to
   live in canon. In practice that means the agent carries the craft as *attached skills* it reads,
   with the doctrine that **the skill wins over the prompt** on conflict. A prompt that paraphrases a
   skill loses detail, and every defect traced back to the paraphrase (earned on the reference
   implementation's first unattended run).

**The honest scope of the claim.** Most work on a model platform is a single call, and most people
integrating an LLM into an app correctly need nothing from this section: one request, one response, no
state, no isolation problem. That is the overwhelmingly common case and it is well served by any SDK.

The claim here is narrower and therefore checkable: **once a deliverable requires many interdependent
generations, held to cross-slot invariants, over a run long enough that nobody watches it, the
workload has changed kind.** At that point the choice is to operate that infrastructure yourself, or
to rent it. Both are legitimate. The standard takes no position on which, and only insists that the
requirements above be met by whatever runs the composer.

**Reference implementation.** `yourparables-book-builder`: an agent created against the Messages API
with an agent toolset, a vault holding scoped credentials with a limited-networking allowlist, and
five attached craft skills (`canon-resolve`, `casting-sweep`, `compose-spread`, `cover`,
`render-readback`). Its doctrine states that it runs unattended, that it finishes or reports failure
clearly, that it never asks a human a question mid-run, and that the skill wins where the prompt and a
skill disagree. It composes and publishes illustrated, narrated books while the operator's machine is
closed.

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
- **Projection (§4.8)** — a typed, versioned, distributable contract for a KIND of deliverable
  (storybook, flyer, meme, share card, explanatory plate). Declares surface, required canon BY KIND,
  slots, generator capabilities, invariants, and outputs. Defining a new kind of deliverable is
  filling in this contract, not writing a renderer.
- **Composition (§4.9)** — ONE instance of a projection: it names the projection, binds real canon
  entity ids to the projection's required kinds, and fills its slots. Supersedes `Story Spec`, which
  remains a back-compatible alias for a composition whose projection is `storybook`.
- **Composer (§4.10)** — the agentic layer that plans a composition into slots and sequences their
  generation. The only layer where open-ended model intelligence belongs.
- **Gate, `computed` vs `judged` (§4.10)** — an invariant checkable by pure code versus one requiring
  a model to look. A `judged` invariant is evaluated in fresh context by an agent that never sees the
  plan, because the maker defends its own intent.
- **Cross-slot invariant (§4.8)** — an invariant only checkable across several slots at once (a
  character being the same person on spread 3 and spread 19). The expensive class, and the thing
  locked goldens exist to serve. A deliverable's complexity is its cross-slot invariant count.
- **Register** — a story's paint-language: a first-class per-story renderer config, sometimes anchored
  to a real artist's own work, locked via experiments and passed as a content-neutral style anchor.
- **Style Pack (§4.7)** — a register's look extracted into a portable, universe-free folder (refs +
  anchor + palette + rejected poles + read-back gate). What "generate more images in this style"
  consumes when there is no recurring identity to pin, so no canon is needed. A register may point at
  one; the `on-brand-image` skill runs off one directly.
- **realPerson dossier** — the sub-block on a real-subject character: photo stack, approval state,
  sensitive list, activity-wardrobe eras, exact group count.
- **Self-containment (§3a)** — a universe owns its assets inside its own repo; you can clone the
  universe folder alone and every reference resolves. A universe that cannot move as one folder is not
  yet a universe.
- **Identity block** — the `universe.json` object holding a universe's constants (mark, platform id,
  theme, closing ornament, voice terms, subject-approval policy) that generic framework skills read
  instead of hardcoding the universe.
- **Framework skill vs universe data** — operations (ref resolution, casting sweep, entity register,
  render read-back, voice gate, renderers) are written once in the framework and parameterized by a
  target universe; a universe ships only data (canon, assets, identity, craft-canon), never skill code.
- **Reference matrix (§12)** — the canonical set of reference shots an entity needs per kind
  (a character's ~8 angles, a setting's contract, a visual-metaphor's states, a prop's hero+crops).
- **lock_level** — an advisory engine report of an entity's reference completeness: stub, partial,
  or locked against its kind's matrix. Distinct from the load-bearing gate, which hard-fails on
  missing required sheets.
- **Register** — a universe's illustrative style, a first-class `identity.register` (named style +
  a content-neutral style anchor passed first on every render); may be overridden per property.
- **Craft-canon record (§13)** — a typed `canon/craft/*.json` record (kind spine | genre |
  register-rule) holding a genre, spine, or universe-wide craft law a renderer honors; craft as data,
  not skill prose.
