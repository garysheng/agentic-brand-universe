# Agentic Brand Universe — Cartridge Spec

**v0.30 — 2026-08-03.** The version-controlled brand-universe (cartridge) format: the first-principles
architecture for a brand as version-controlled canon + golden assets, agentically writable,
composable, and evolvable, rendered into any deliverable. Home: `agenticbranduniverse.com`.
Reference implementations: the Nation of Fire universe (storybooks) and Build on Anthropic (a
documentation brand: explanatory plates, ink-line illustration, share cards, a slide deck).

> **v0.30 changelog — two checks that fired at the wrong time, both from one book run.** *He Is
> a Jealous God*, nation-of-fire, 2026-08-03. **(1)** A REFS selector could not condition a
> reference shoot on the entity's OWN already-made art, because `requiredForRender` named a plate
> the shoot was about to create and the existence check refused on it. The blueprint-seeded chain
> this spec prescribes for a multi-state object was therefore unreachable without temporarily
> rewriting `requiredForRender`, which is an author falsifying canon to satisfy a guard about
> something else. A required sheet not on disk yet is now DROPPED; an explicitly selected one still
> refuses, and dropping everything is still a refusal. **(2)** `lint-universe` now warns
> `LOCKED-BUT-NO-SHEETS`: a LOCKED entity whose art hangs off `contract` alone with no
> `structured.sheets` can have NO plate resolved for it, and it fails silently at compose time as
> `available: NONE` rather than at lock time. Eleven entities in one universe were in that state,
> including two heavily-used settings, all of them looking finished.

> **v0.29 changelog — five checks that were lying, all earned in one book run.** *The Tithe Is a
> Test* (nation-of-fire, shipped 2026-08-02) walked the whole chain and every defect it surfaced has
> the same shape: a surface that LOOKS like it is enforcing something and is not. **(1) The book
> doctor's caption check produced 29 of 29 false positives** because it compared a `_caption` (the
> words the reader reads) against `beats[].text` (instruction for the renderer), which are different
> documents by design in any universe that keeps a manuscript. It now reads
> `stories/<id>.manuscript.md` when there is one, and a check that fails on every spread of every
> book stops teaching its operator to ignore it (§3.5). **(2) `structured.render.qa` steered nothing
> and checked nothing.** §4.6 has stated since v0.4 that the checklist is the union of `invariants`
> and `render.qa`, and no compiler ever read the second half, so a six-item `render.qa` compiled to
> zero checks. Fifth instance of the v0.23-v0.28 defect class: a spec guarantee no code could
> deliver. **(3) A POSE may now supersede a base invariant** (§12), because an `altLook` is the wrong
> instrument when the face must not change and the only alternative was hand-wording "...except in
> pose X". **(4) `lock-shot` and `resolve_setting` disagreed about what `locked` means** for a
> setting, the promoter demanding the advisory `scalePlate` this spec explicitly says is advisory, so
> settings that legitimately cannot have one were hand-flipped in JSON. One predicate now,
> `setting_contract_gaps`, plus the `emptyPlatesExpected` count. **(5) `contract.blockingPlate` and
> `contract.dressing` leaked one book's props into every book reusing the setting**, and a reference
> image plus an injected contract sentence beat a per-spread negative that banned the prop by name,
> on three of seven spreads. Lint warns; a spread can scope the plate out. Also: `backfill-prompts`
> now SCAFFOLDS a missing `prompts.md`, since an entity older than the scaffolder had none and was
> invisible to the sweep, which left a locked, actively-cast character unable to be re-shot.
>
> **v0.29 same-day pave addendum (2026-08-02, the-bible-all-points-to-jesus run).** Four more
> members of the same "a check that lied or a silent foot-gun" class, found by six stewards in one
> book run and paved the same day. **(1)** `stories/*.voice-waivers.json` — voice-gate's own default
> waiver sidecar, which lives in stories/ — parsed as a StorySpec, so `validate` emitted a false
> "story missing 'id'" per waiver file (bit twice in one day). Sidecars are excluded by one shared
> predicate. **(2)** `structured.sheetAliases` (§12) lets an intentional add-keys-never-remove
> rename be DECLARED, so lint can tell it from a dead duplicate. **(3)** `chain_matrix` now honours
> `identity.register.anchorSubject` (see Register) instead of every matrix shoot hand-negating the
> anchor's subject in prompts.md. **(4)** ONE recipe per asset: `chain_matrix` used to write
> `<shot>.recipe.json` while the provider wrote `<shot>.png.recipe.json` — two provenance sidecars
> for one asset, free to diverge; the chain now merges its conditioning metadata into the provider's
> file and removes the stale twin.
>
> **v0.29 same-day pave addendum #2 (2026-08-02, eleventh-hour-heroes run).** **(1)** The cover
> compiler (`cover/compile_cover.py`) now auto-negates `identity.register.anchorSubject`, closing
> the last render path that passed the anchor first without reading the field: a cover render
> painted the readiness-lamp anchor's ancient burning oil lamp onto the cover wall (one paid
> re-roll). Skipped when `--anchor-ref` overrides the anchor, since the declared subject no longer
> describes the first reference (see Register). **(2)** `make-a-book` guidance: `allowUncast` does
> not protect anonymous crowds from the cast closure — a spread with unnamed figures must declare
> the per-spread `anonymous` field (two paid re-rolls); and after voice-gate blesses a manuscript,
> beat `text` syncs to the manuscript verbatim, because book-doctor's caption check makes
> beats == manuscript == captions the invariant (two runs did this sync by hand). **Recorded, not
> built:** `lock-level` grades a deliberately-trimmed character matrix as 'partial' forever
> because it grades against the canonical 8-slot matrix rather than the entity's declared sheets;
> advisory-only (assert-story unaffected), deliberately not landed mid-flight while sibling book
> sessions hold worktrees.

> **v0.28 changelog — lookbooks became real, and clothes got attached to people.** From v0.12 to
> v0.27 a Lookbook was a specification with no implementation: `--lookbook` wrote the vocabulary's
> NAME into the recipe after the image already existed, sampling nothing and gating nothing, and the
> engine held zero lines about lookbooks. Craft canon in two universes meanwhile instructed renderers
> to "pass `--lookbook X` so the renderer samples 2-4 exemplars, applies the varietyRule and gates
> the output" — three behaviours described, none implemented. Fifth instance of the v0.23-v0.26
> defect class: canon that is correct and unexecutable. v0.28 implements the consumption contract
> (§4.7.1), adds `always` / `appliesWhen` / `negatives` so a vocabulary can say WHEN it applies,
> validates lookbooks for real, and introduces `structured.wardrobe` (§4.7.2) so a CHARACTER binds
> their own clothes. Renders resolve wardrobe automatically off `--entity`; `abu wardrobe` answers
> the same question outside a render. Earned when two fully-locked characters turned out to have no
> wardrobe binding of any kind, and the one prose instruction that gestured at one pointed at a
> field that was `null`.

> **v0.27 changelog — a standard for when a REAL PERSON is reproducible.** `lock-level` answers
> "are the files on disk." It never answered the question a brand actually needs: is there enough
> coverage here to reproduce this person reliably, in a new pose, months from now, without their
> likeness drifting. The character matrix requires TWO shots. For an invented character that is
> defensible; for a real person it is not, and one session proved it — `gary` reached the required
> set early and his likeness still had to be rebuilt across five rerolls, nine photographs and a
> purpose-built chest-up plate before it held. §12 adds `REAL_PERSON_COVERAGE` and an advisory
> `real_person_gaps()`, which measures three things the old model could not express. **Angle
> coverage:** ≥6 varied photographs, because the rule "a single reference lets a face drift" lived
> in one universe's prose preamble, was right all day, and nothing enforced it —
> `realPerson.photoStack` accepted a single photo. **Expression coverage:** a stack carrying one
> expression reproduces one expression; the standard wants the face known at rest AND in use.
> **Context coverage,** the sharpest of the three: a character carrying a recurring prop needs one
> plate where that prop is LEGIBLE at render scale. Gary's pendant kept rendering wrong not for want
> of pendant references but because no plate showed it big enough to copy — in a head-to-toe frame
> it is about forty pixels. A matrix that only asks "which angles of the person" cannot ask that.
> Advisory throughout, exactly like `lock-level`: it never blocks a render, and an invented
> character is not measured against it at all.

> **v0.29 changelog — a setting may be `partOf` another setting.** Until now a setting carried
> exactly ONE flat contract: one `map`, one `blocking`, one `dressing`, one `scale`, for the whole
> entity. Correct for a shed, wrong for a house. `christofuturist-home` had grown to twelve plates
> covering nine rooms under a single room-agnostic `blocking`, and it had already cost the spec once:
> v0.13 added `contract.scalePlate` because "christofuturist-home, whose hearth room rendered small",
> a one-room problem that was unfixable on a nine-room entity and so became a new field for everyone.
> On 2026-08-02 it cost again. The sunken pit needed FIXED LETTERED SEATING (SEAT A / SEAT B) and
> there was nowhere to put it, since a `blocking` naming two seats would be a lie about the eight
> rooms that have none. The room was promoted to a top-level sibling, which lost the containment
> outright (nothing in the data said the pit is IN the home) and silently dropped the house rules,
> so `everyone-indoors-wears-the-house-slippers` had to be hand-copied onto the child.
>
> A setting now declares `partOf: <setting-id>`, and a parent declares
> `structured.houseRules: {invariants, dressing}`. THAT BLOCK ALONE is inherited: `invariants` union
> into the child (parent first, deduped) and `dressing` appends before the child's.
> **LAW inherits, ART never does.** `turnaround`, `blueprint`, `scalePlate`, `blockingPlate`,
> `emptyPlates`, `structured.sheets` and `contract.plates` are always the room's own, because
> inheriting a parent's plate would hand the model the hearth when it asked for the pit, which is
> the exact drift the feature exists to stop. `map`, `blocking` and `scale` stay the child's for the
> same reason.
>
> **Blind inheritance was implemented first and was wrong**, and it took ten minutes against real
> canon to prove it: folding the parent's whole invariant list into each child handed the pit
> `studyNook ONLY: EXACTLY TWO armchairs` and `hearthRotunda IS RETIRED`. Every setting invariant
> becomes a render-readback QA check, so the pit would have been graded on furniture it must not
> have. Hence the explicit opt-in. For the same reason `houseRules` accepts ONLY those two keys and
> REFUSES `always`/`qa` by name: both were in the first cut, both were verified dead on a real
> render (a setting's block is built from `contract`, its checks from `structured.invariants`), and
> a field that silently does nothing is the failure this spec keeps re-earning.
>
> Cycles, missing parents, non-setting parents and chains deeper than 8 are refused BY NAME at the
> gate rather than as a recursion traceback. Additive twice over: an entity with no `partOf`
> resolves byte-identically, and a parent with no `houseRules` gives its children nothing.

> **v0.26 changelog — `supersedes` now covers the negatives it always claimed to.** §12 has
> said since v0.10 that `supersedes` exists "so the QA checklist, the prompt block, AND THE
> COMPUTED NEGATIVES all agree by construction." For the negatives that was false from the moment
> v0.23 added `structured.negatives`: it shipped as a flat list, nothing was look-aware about it,
> and both consumers merged the whole list regardless of the selected look. Measured on
> christofuturism's `summer-quiet-luxury`, a look whose entire purpose is a BARE NECK: **32
> pendant-scoped negatives reached the model**, one of them literally `more than one necklace`,
> a negative that AFFIRMS a necklace is expected. The look survived only because a human hand-wrote
> an override sentence into the prompt body. `supersedes` now retires a negative by exact string
> exactly as it retires an invariant, via `Entity.look_negatives()`, honoured by both
> `compose-spread` and `shoot-references`; `altLooks.<key>.negatives` adds look-specific ones.
> Unrelated negatives survive, so superseding a pendant cannot disarm a beard rule. Fourth in a
> run of defects with one shape: the spec stated a guarantee and no code could deliver it.

> **v0.25 changelog — a shot can name WHICH of another entity's sheets it needs.**
> A shot's `REFS:` line took an entity id and nothing more, and the resolver passed that
> entity's `requiredForRender` set alone. So an entity's EXTRA sheets were unreachable from
> a shoot: a multi-angle `turnaround`, a worn/in-situ plate, a material variant could each be
> registered, carry full provenance, and be named by the entity's OWN `structured.render.always`
> instruction, and still no shot could ask for them. Proven on christofuturism's
> `north-star-cross`, whose fabrication spec warns in as many words that a single flat front
> view gets flattened back into an equilateral four-point star and that a multi-angle
> turnaround should be preferred. Three flat front plates were all the resolver could pass,
> and the pendant came back at 1.79:1 height-to-width against a spec of 1.24:1, reading as the
> crucifix the wearer's own invariant forbids by name. Now `REFS: <id>@<sheet>+<sheet>` names
> the sheets, they are passed FIRST, and `requiredForRender` still follows: **a selector may
> raise the ref set and must never lower it**, which is v0.24's lock rule one layer out. A
> selector naming a sheet the entity does not declare, or declares with no art, REFUSES.
> `--print-plan` now RESOLVES cross-entity refs instead of echoing them, and no longer hides
> them on the seed shot, so a typo costs nothing instead of costing a render. Two adjacent
> defects fixed in the same pass: a typed slot (`{"path","role"}`, v0.23) used as a cross-entity
> ref crashed the resolver, and a `Refuse` raised while shooting surfaced as a traceback rather
> than a message.

> **v0.24 changelog — a lock may raise a gate and must never lower one.** `lock-shot`
> recomputed `requiredForRender` from the KIND minimum alone, so any entity that legitimately
> required MORE than its kind demanded was silently demoted on its next lock. Proven on
> christofuturism's `north-star-cross`, a motif whose required set was `["hero","detail",
> "in-context"]` because that entity's own authority note records that ONE view of the mark
> reads as an equilateral star and only three views prove it is a cross: locking a new material
> plate rewrote it to `["hero"]`, so the entity guarding a filed trademark would have quietly
> stopped guarding it. Worse, the field that exists to rescue exactly this case,
> `requiredForRenderOnLock` (v0.11), REFUSED the key, because it validated names against the
> kind matrix alone and `in-context` is not a motif matrix shot. The escape hatch was closed
> against its own use case and the only way out was hand-editing the entity JSON, which is the
> hand-rolling the authoring module exists to remove. Now: a lock preserves any key the entity
> already required that still resolves on disk, and `requiredForRenderOnLock` accepts the kind's
> known shots PLUS the keys the entity actually declares. The typo check stays, so a key with
> neither art nor matrix membership is still refused, and a required key whose art is gone still
> drops. Found by a steward migrating a legacy brand OS, who worked around it by hand and flagged
> it rather than leaving it silent.

> **v0.23 changelog — a reference slot can say what it CONTRIBUTES, a negative can name one
> person, and a multi-line header stops being half-read.** §12 slots accept `{"path", "role"}`
> alongside the bare path they have always accepted, with roles `identity | geometry | garment |
> medium | scale`. A slot was previously `shot -> path` and nothing more, so nothing could declare
> "this plate supplies the cut of a garment, never its medium and never a face." That silence was
> not academic: a pair of watercolour-and-ink costume plates, whose own sidecars read "garment
> design ONLY; the render stays hyperreal", looked perfectly admissible as matrix slots on a
> HYPERREAL character and would have baked an illustrated medium into a photographic canon. The
> prose said the right thing and no gate could read it. The compiler now emits a per-ref
> `REFERENCE ROLES` instruction so a ref cannot contribute more than it should. Untyped slots emit
> nothing and are gated exactly as before, so no universe migrates. ALSO: `structured.negatives`
> on an entity, emitted ONLY when that entity is in frame. Six of nineteen banned-visual entries
> migrated out of a legacy brand OS name ONE person (no glasses on Gary, no black leather jacket,
> no stubble, no tattoos) while the same source explicitly PERMITS glasses on other people, so as
> flat pack `rejectedPoles` they would have forbidden those universe-wide and quietly overruled a
> decision the author had made the other way. AND a parser fix that cost a real render:
> `chain_matrix`'s `**Negatives (every shot):**` and `**Refs (every shot):**` headers were read
> with a single-line regex, so a header authored across four lines contributed only its first line
> and the rest was dropped in silence. On gary's first seed 5 of 18 negatives reached the model and
> `a crucifix` was among the thirteen discarded, so the pendant rendered as exactly the crucifix
> his invariant forbids by name. Both headers now read the whole block, splitting on commas or
> newlines and tolerating list markers. Same class as the header-implies-a-guarantee defects
> already fixed twice in that file.

> **v0.22 changelog — a character must be able to prove its own height, and so must an object.**
> §12 adds a `scale-plate` shot to the character and prop matrices (both `optional`), a `scale`
> descriptor for props, and a universe-level `identity.scaleReference`. v0.9 gave settings this and
> stated the reason in one line: *a plate cannot be judged on a dimension it does not depict.* That
> reasoning was never applied to people. `structured.scale` (v0.10) looks like it closes the gap and
> does not: its `height` is prose nothing depicts, and its `scalePlate` is explicitly a two-up of a
> PAIR at true relative height, so between them they answer "is he taller than her" and never "how
> tall is he." A `scale-plate` is a SOLO head-to-toe plate against a MEASURED reference whose real
> size is recorded, which makes the declared height checkable and gives the model an absolute unit
> for people and objects alike. The geometry is fixed by the framework and PROJECTED into §12 from
> `matrix.SCALE_PLATE_CONTRACT`, so it cannot drift; the treatment is the universe's, via
> `identity.scaleReference`, because "something tasteful" is register-local. `optional` rather than
> in `shots`, for the same reason `face-neutral-color` is: promoting it would demote every
> already-locked character in every universe. Advisory: `lint-universe` warns
> `CHARACTER-NO-SCALE-PLATE`, `CHARACTER-HEIGHT-UNDEPICTED`, `CHARACTER-SCALE-PLATE-MISSING`,
> `PROP-NO-SCALE`. Also in this release, three provenance defects found while migrating a legacy
> brand OS into a universe: `provenance.images()` swept `*.png` ONLY, so a `.jpg` photograph and a
> `.webp` pack ref were invisible to the sweep and could never be counted as missing, backfilled, or
> divergence-checked (it now sweeps `.png`, `.jpg`, `.jpeg`, `.webp`); `backfill-provenance` gains
> `--entity`, which `backfill-prompts` already had, so a one-character backfill is a reviewable diff
> instead of a whole-universe rewrite; and source classification now honours an EXPLICIT
> `realPerson.photoStack` declaration before the filename heuristic, because a photograph
> legitimately filling a matrix slot at `reference/<id>/face-neutral.png` matched neither `photo-N`
> nor a `photos/` parent and was stamped `attested`, asserting a render that never happened. Finally
> `abu list` shows lifecycle: an archived entity printed identically to an active one, so the listing
> invited a casting decision the entity had already been retired from. Earned 2026-08-01 on Gary's
> own entity, whose declared 6 ft existed only as prose.

> **v0.21 changelog — an asset from OUTSIDE arrives with its chain (`abu import-asset`), and the
> photo-stack rule stops existing twice.** Both additive: no universe migrates, and an asset already
> in canon is untouched.
>
> **(1) `import-asset`, and a fifth provenance class, `derived`.** A universe absorbs assets it did
> not generate: a retired brand repo is folded in, a blessed render is cut out of a product repo and
> installed as a photo-stack reference, a client hands over photographs. The framework had no verb
> for it, and every available path was a lie or a hand-roll. `backfill-provenance` can only classify
> an asset as `source` ("there is no generating call to record"), `reconstructed`, `attested`
> ("nothing about the generating call survives") or `deterministic`; for a CROP of a known
> gpt-image-2 render whose source hash, crop box and original prompt are all in hand, **all four are
> false**, and recording a knowable fact as unknowable is the failure that module exists to prevent,
> pointed the other way. The remaining option was writing the `.recipe.json` by hand, which is
> provenance saved by memory, which the provider adapter exists to abolish. §3.2 adds the class and
> the verb: the recipe is written as a side effect of the COPY, exactly as `generate.py` writes one
> as a side effect of generating, and a `derived` import with no stated antecedent is REFUSED.
> Manifest mode imports a batch fail-closed, because half an imported photo stack is worse than none.
> Earned 2026-08-01 on christofuturism `gary`: twelve blessed crops of subconscious-os renders.
>
> **(2) The photo-stack rule is now ONE implementation.** §12 has said since v0.17 that a
> `realPerson.photoStack` entry may be a file or a DIRECTORY, and called the directory the idiomatic
> whole-stack form. `compose-spread`'s assembler expanded it and applied `photoLimit` after
> expansion; `shoot-references` REFUSED a directory outright and never read `photoLimit` at all. So
> the form the spec recommends could be RENDERED from and not SHOT from, and an entity that declared
> a ceiling had it honored at render time and ignored at shoot time. The rule now lives in
> `agenticstory.refs.photo_stack`, both callers use it, and a parity test pins them together, because
> the assembler is deliberately dependency-free and will keep its own copy.

> **v0.18 changelog — a VARIANT may declare WHICH ERA it is legal in.** Additive, opt-in at both
> ends, and backward-compatible: a spread with no `when`, or an entity whose variants declare no
> `validFor`, compiles byte-identically to v0.17, so no universe has to migrate.
>
> A variant is a body a thing wears for part of its life: a character's `altLook`, a setting's era
> plate. Nothing gated which one a spread could select, so every variant was equally legal on every
> spread. On a book spanning three ages of one man, nothing stopped a 1933 beat picking the `elder`
> look, and nothing stopped a 1990 beat silently falling through to the default young face. **Both
> failures are silent**: the render succeeds, it passes read-back (the wrong era's invariants all
> hold), it is beautiful and internally consistent, and it is of the wrong person.
>
> §12 adds `validFor: {from, to}` on `structured.validFor` (the DEFAULT look), on
> `structured.altLooks.<key>`, and on `contract.plates.<plate>`, plus `when` on a spread. Both are
> plain numbers, so a universe may count in years or in beat indices. `compose-spread` refuses
> PRE-SPEND and names the variant that IS legal at that date; `lint-universe` sees what the compiler
> cannot, which is the shape of the whole variant SET, and warns `VALIDFOR-PARTIAL` when some
> variants are windowed and others are not, because an undeclared variant stays legal at every date
> and the gate then has a hole exactly where it looks closed.
>
> §12 also settles the setting question this raised: **two eras of one place stay ONE entity**, and
> the era axis is its PLATES rather than a new `eras[]` array. When a place appears in two periods
> the reason it is in the story is usually that it is the SAME GROUND, and splitting it into two
> entities destroys the only claim it exists to make. One `map`, one code-built massing `blueprint`
> both eras are seeded on, one `emptyPlates` list, a named MATCH POINT required visible in every
> plate of both eras. And `keepSheets` / `keepPhotos` are documented as TEMPORAL-DIRECTION-AGNOSTIC:
> they serve any era the photo stack does not cover, past as well as declared-future, which decides
> the shooting ORDER (shoot the era that has photographs first, chain the rest off it).
>
> Earned 2026-07-31 on `the-power-of-obeying` (69 spreads, 1917 to 2003, three eras of one man plus
> one piece of ground in two), where the look was named by hand on all 71 spreads.

> **v0.17 changelog — the slot-model composer is RETIRED, having never run.** `skills/compose/`
> (896 lines, 91 tests, zero works) is deleted, and with it `add-form`, `add-work`, `brand-card`
> and `forms/scrolling-diorama`, which existed only to author or emit documents that only that
> composer consumed. §4.8 and §4.9 now retire the ENCODING while keeping the concept; §4.10
> corrects "THE Composer" to a per-form composer over one shared compiler
> (`compose-spread/assemble_prompt.py`); §14's Managed Agents argument is marked ASPIRATIONAL,
> because nothing in this framework runs on it. No universe pins v0.17 yet, and none needs to
> migrate: this bump only removes a schema no universe ever used.
>
> **v0.19 changelog — an entity has a LIFECYCLE, so canon can be RETIRED without rewriting history.**
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

> **v0.19 changelog — a setting may declare a BLOCKING PLATE.** Additive and advisory: no
> existing universe migrates, and a setting without one validates and renders exactly as
> before. §12 adds `contract.blockingPlate` (file) to the setting contract: the room with
> featureless artist's mannequins in the LEGAL seat positions at correct relative size,
> plus the props the scene needs. `blocking` states the camera law in prose and
> `structured.seating` states handedness in one sentence; neither shows the model a
> geometry it can copy, so placement was re-decided every render. `compose-spread` appends
> the plate to the refs on EVERY camera of that setting, wide or close, because placement
> is continuity rather than composition. Deliberately NOT added to the required contract,
> so no already-locked setting drops back to unlocked. Earned on the-creamery-counter
> (nation-of-fire, will-there-be-ice-cream, 2026-08-01): two people at one counter across
> twenty-six spreads swapped viewer-left and viewer-right six times, and their stools
> rendered in front of a glass display case where neither could set a bowl down.

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
first-class object, deliverables **works** over it, references **load-bearing** (their absence
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
│  COMPOSER     agentic, per form: plan → compile → gate       │  §4.10
├─────────────────────────────────────────────────────────────┤
│  WORK         ONE made thing: this book, this flyer, a meme  │  §4.9
├─────────────────────────────────────────────────────────────┤
│  FORM         what makes a work the KIND of thing it is      │  §4.8
├─────────────────────────────────────────────────────────────┤
│  GOLDENS      load-bearing resolver: entity → real asset     │  §4.4
├─────────────────────────────────────────────────────────────┤
│  CANON        typed entities + relations; git-versioned      │  §4.1
└─────────────────────────────────────────────────────────────┘
```

Read it bottom-up as a sentence: *canon* is what is true, *goldens* are what it looks like once
locked, a *form* is what shapes canon into a kind of thing, a *work* is canon given that form, and a
*composer* is the agent that makes one and answers to the gate.

The split that v0.6 introduced is between the middle two, and that much is durable: **a form is a
kind; a work is one made thing.** Conflating them is what made this standard storybook-shaped: the
one primitive that existed carried a story's required fields, so every deliverable had to be a story
to be expressible.

> **How these two middle layers are ENCODED is open, not settled.** From v0.6 to v0.16 a form and a
> work were typed documents executed by a single universal composer. That encoding is RETIRED
> (§4.8, §4.9): it was authored from one imagined example and produced zero works across the whole
> life of the framework. §4.8, §4.9 and §4.10 are now the record of what was retired and why, and
> they deliberately name no replacement until a second real composer exists to abstract from.
> Nothing at these two layers should be read as a live schema, here or there.

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

**A ref path may be a FILE or a DIRECTORY.** A directory expands to the image files directly inside
it, sorted. `agenticstory.refs.expand_ref` is the one implementation; `refs.photo_stack` layers the
`realPerson.photoLimit` cap on top of it (§12), and the cap applies AFTER expansion. A path that
does not resolve, or a directory holding no images, is a hard error rather than an empty list: a ref
that silently resolves to nothing is a silent downgrade to "invent it from prose".

**Every asset carries a `.recipe.json` sidecar, and there are exactly two honest ways to get one.**
The provider adapter writes one as a side effect of GENERATING. `abu import-asset` writes one as a
side effect of COPYING an asset in from outside. Nothing else writes a recipe by hand.

    abu import-asset <universe> <dest-rel> --from <src> \
      --from-repo <repo> --from-path <path-in-repo> --from-sha <sha> \
      --crop x0,y0,x1,y1 --source-generator gpt-image-2 --source-prompt-file <f> \
      --blessed-by "<who, when>"
    abu import-asset <universe> --manifest <manifest.json> --dest-dir <rel> [--prompts <f>]

**Provenance classes.** Four describe assets that were already here when the adapter arrived
(`source`, `reconstructed`, `attested`, `deterministic`; see `backfill-provenance`). The fifth,
**`derived` (v0.21), describes an asset that came from another repo as a stated transform of a known
asset**: `derivedFrom` names the source repo, path and hash, `transform` names what was done to the
bytes (a crop box), and `sourcePrompt` records the call that made the SOURCE, deliberately named so
nothing mistakes it for a call that produced these exact bytes. `derived` is NOT `unrecorded`: the
generating call is recorded, it simply happened elsewhere. **A `derived` import that cannot say what
it is derived FROM is refused**, because an import with no chain is not provenance; such an asset is
`--provenance source`, which claims only that it is an original input.

Manifest mode refuses the WHOLE batch before copying anything. Half an imported photo stack is worse
than none: the entity then declares a stack whose provenance is inconsistent, and nothing says which
half is which.

This exists because the alternatives were dishonest. Twelve blessed crops of known gpt-image-2
renders entered `christofuturism`'s `gary` photo stack on 2026-08-01. `backfill-provenance` would
have stamped each one `source` ("there is no generating call to record") when the source hash, the
crop box and the original prompt were all in hand.

### 3.3 Form (a kind of deliverable)
What makes a work the KIND of thing it is. A storybook, a flyer, a meme, a share card, an explanatory
plate and a slide deck are six forms over one canon; the canon does not change when the kind does.

*How* a form is written down is an open question rather than a settled contract. From v0.6 to v0.16
this standard answered it with a typed document — surface, required kinds, slots, generators,
invariants — and promised that defining a new kind of deliverable was filling that document in rather
than writing a renderer. That encoding is retired, and **§4.8 is now the record of its retirement,
not the specification of a live contract**. Until a second proven composer exists to abstract from, a
form is whatever a proven composer needs it to be, and no universe is asked to conform to a schema
this standard cannot yet justify.

### 3.4 Work (one made thing) and the composer (who makes it)
A **work** is one flyer, one book: canon given form. It names the kind of thing it is, selects the
canon entities it features, and carries **authorship** — decisions present in neither the canon nor
the form. It never mutates canon: a finished work *proposes* new canon back (a newly locked
character, a new crossover, a new doctrine occurrence) for the author to accept and commit (§5).

A **composer** (§4.10) is the agent that turns canon plus a form into the work, calling the
deterministic compiler (§4.6) and answering to the gate. It is **per form**, not one universal
executor: a storybook, a diptych series and a deck genuinely plan differently, and what they share
sits underneath the plan rather than inside it. What a work is encoded as, and which of a composer's
parts belong *under* it rather than *inside* it, are questions §4.9 and §4.10 hold open rather than
answer.

### 3.5 Quality (cross-cutting)
Three wired mechanisms, applied at defined points:
- **Taste gates** — human "that's it / that's not it" at irreducible moments (words-before-art,
  register-point, face-lock). The system's job: surface the *right* decision at the right time, never
  waste attention.
- **Craft-canon** — narrative craft as enforceable invariants attached to canon (spine shape, refrain
  presence, tension→turn, "awe not horror," show-don't-tell, the confusion-flag pass).
- **Provenance** — every beat cites a source (testimony, research, the author's own words). Unsourced
  vivid detail is flagged before it ships (the cross-person-contamination guard).

**Two delivery-side refusals (v0.20), both earned because they exited 0 and looked like success:**
- **`--out` is a file path, never a directory.** Handed a directory, the renderer's existence check
  is true for every spread, so `--skip-existing` reports "exists, skip" for the whole batch and
  renders nothing while still exiting 0. It now refuses and names the exact fix, and the check runs
  **before** the skip, or the skip still swallows the batch.
- **Captions must match the blessed manuscript verbatim.** A render-spec's `_caption` is copied from
  the blessed text when the spec is scaffolded and nothing re-syncs it, so editing that text
  afterwards leaves the art following the new words and the caption keeping the old. The book doctor
  compares every caption against the blessed source and fails on any drift. **Its limit is stated
  deliberately:** it compares two artifacts, so it cannot see prose that is stale in BOTH, which is
  exactly what an entity recast produces (§4.3). Earned 2026-08-01, where it correctly passed all 73
  captions of a book whose story still described the room it had left.
  - **WHICH source is the blessed one (v0.29).** When `stories/<id>.manuscript.md` exists it is the
    source, and `beats[].text` is the source only when it does not. These are different documents on
    purpose: a beat's `text` is **instruction for the renderer** ("Theo sitting on the bench beside
    Jerry, telling him about the baptism") while a `_caption` is **the words the reader reads** ("It
    had been a year since he stood at the back of the room"). Comparing the two therefore fails on
    every spread of every book in any universe that keeps a manuscript, which is what happened: 29 of
    29 verbatim-correct captions were reported stale on *The Tithe Is a Test* (2026-08-02). **A check
    that fails on every spread of every book trains its operator to ignore it**, which costs more
    than never having written it. The defect the check exists for survives the change, because the
    manuscript is what gets rewritten.
  - Three manuscript conventions are parsed (`**7.**`, `**Spread 7**:`, `### 7`), a wholly-italic
    line is treated as stage direction rather than caption, and comparison normalises whitespace,
    emphasis and typographic punctuation. Every one of those normalisations exists to prevent a
    false positive; a caption that is a SUBSTRING of its beat passes, because one beat set across two
    spreads is legitimate and a wholesale stale caption is neither equal nor contained.
  - **The endcap naming rule is a PAIR, not a list.** A spread id is the closing plate if it is one
    of the known names or carries `closing` as a word (`closing-plate`, `plate-closing`,
    `spread-30-closing`). The fixed list contradicted itself: an unrecognised id was demanded at
    landscape interior aspect by one check and at portrait endcap aspect by another, so no file could
    satisfy both and the only escape was renaming the spec id.

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
    // v0.21: BOTH RULES APPLY AT SHOOT TIME AS WELL AS AT RENDER TIME. `agenticstory.refs.
    // photo_stack` is the one implementation and `shoot-references` now calls it. It used to
    // refuse a directory outright ("is a DIRECTORY, not an image") and never read photoLimit, so
    // the form this comment calls idiomatic could be RENDERED from and not SHOT from, and a
    // declared ceiling was honored in one half of the framework and ignored in the other. Found
    // 2026-08-01 on christofuturism `gary`.
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

**Recasting (v0.20):** replacing one canon entity with another across a whole story is a
distinct operation from editing a spread, and it is a **manuscript event rather than a data
edit**. `recast-story` swaps every structural reference it can prove (beats' `location` and
`characters`, `features`, `writesBack`, and the render-spec's `setting` and `cast[].id`), and
**refuses an unregistered entity**, because a recast must land on real canon. It **flags any
`plate` the new entity does not declare** and never substitutes one: plate keys are per-entity
(`master`/`empty` versus `wide`/`close-jerry`), so a swapped setting silently keeps a camera that
no longer exists, and the compiler then refuses much later with no hint why. **A swap must never
guess a camera.**

It deliberately does NOT decide which prose went stale. It emits a review packet (both entities'
self-descriptions plus every beat) for a reader, per §3.5's taste-gate principle and the
role-not-a-service pattern of slot judging. Two word-list heuristics were built and discarded:
sweeping the old entity's contract buried the true hits under character names and under negations
the entity states about itself ("no brand marks"), and subtracting the new entity's vocabulary left
ordinary discursive words, because `prose.rules` is English and furniture nouns are a tiny subset
of it. A sweep a human learns to ignore is worse than no sweep. Earned 2026-08-01 on
*Will There Be Ice Cream*, where two blanket string replacements left a `spineNote` citing the
replaced character's origin book, `aimDiscipline` pointing at pre-renumber beat numbers, and five
beats still describing a counter, a stool, a bowl and a spoon beneath finished paintings of a park
bench and two ice cream cones.

### 4.4 Ref contract (the resolver)
- `resolve(entity) → real paths | error`
- `resolve-setting(location) → contract paths | error (if unlocked/missing)`
- `assert-spread(characters[], location?) → ok | non-zero exit listing what's missing`
- **Invariant:** no renderer may generate a unit whose `assert` has not passed.

### 4.5 Renderer interface (superseded by §4.10; invariants retained)

**v0.6:** what this section called a *renderer* is now a **composer** (§4.10). The rename matters
because "renderer" implies a deterministic template engine, and the layer that plans a work is not
one. This section also once claimed a *story spec* had become an instance of the generic deliverable
primitive; §4.9 retracts that, because it never happened. **§4.3 remains canonical for stories.**
Three invariants from this section survive unchanged and remain normative for a composer:

- It declares `consumes` (which entity fields it reads) and `produces` (medium artifacts).
- It **must assert refs before every unit** (§4.4). No unit is generated whose `assert` has not passed.
- It **never mutates canon.** It reads canon plus the story or work it is making, and emits medium
  output plus a `writesBack` proposal for the author to accept.

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
    **`render.qa` was finally implemented in v0.29.** This line has stated the union since v0.4 and
    no compiler ever read the second half of it, so an entity could carry a well-written
    `structured.render.qa`, validate, lint clean, and contribute ZERO lines to the checklist. Earned
    on `theo-doorchaser` (2026-08-02), six qa items and an empty `invariants`: a dry assemble
    reported thirteen QA invariants on a two-hander (all thirteen the other man's) and zero on the
    spread where he stands alone, and his half-on jacket was the spine of the book. Compiled for
    every kind, look-aware (an alt look may replace the render block wholesale), and de-duped against
    `invariants`. `lint-universe` additionally warns `ENTITY-QA-WITHOUT-INVARIANTS`, because
    `invariants` is what the identity bake guard, auto-disambiguation, `supersedes` and `judge-slot`
    read: an entity guarded only by `render.qa` is guarded in one place out of five.
- **Provider-agnostic:** the compiler emits `(prompt, refs, size)` and hands off to a swappable
  provider adapter (`gpt-image-2` today, others behind the same interface). The adapter normalizes the
  *call*; per-provider reference-conditioning and moderation (e.g. a `public-figure` block) remain
  provider facts, not framework facts.
- **Determinism ceiling (invariant):** the compiler makes the *input* deterministic; the model output
  stays stochastic. A compiled prompt is necessary, not sufficient — the read-back gate (§3.5) is
  still mandatory, and a drift-prone shape is guaranteed by *passing its reference image*, never by
  wording it harder.
  <!-- BEGIN GENERATED: guards -->
| Guard                | Fires        | Predicate                |
|----------------------|--------------|--------------------------|
| `ADDRESSING_GUARD`   | conditional  | `_has_audience()`        |
| `ANCHOR_STYLE_GUARD` | every render | unconditional            |
| `BEDCLOTHES_GUARD`   | conditional  | `_in_bed()`              |
| `BED_LENGTH_GUARD`   | conditional  | `_person_lying_on_bed()` |
| `CROWD_MEMBER_GUARD` | conditional  | `_cast_inside_crowd()`   |
| `MOTION_GUARD`       | conditional  | `_has_motion()`          |
| `SINGLE_IMAGE_GUARD` | every render | unconditional            |
<!-- END GENERATED: guards -->

- **Normative guards (v0.8, extended v0.19).** Rules the compiler emits or enforces on every job,
  because each is a property of *how the compiler works*, not of what a given book contains. A
  universe that writes these into each book's style text will drop them the one time it forgets.
  Guards divide into two kinds. An **unconditional** guard is emitted on every render (anchor-style,
  single-image). A **conditional** guard is emitted only when the SCENE TEXT shows the defect is in
  reach, detected by a `_has_*`/`_in_*` predicate beside it (motion, addressing, bedclothes); this
  keeps the prompt from filling with rules irrelevant to the beat, at the cost of a detector that
  must itself be tested against real scenes.
  **A conditional guard's detector is the part that fails.** Written narrowly it is silent on the
  very case that earned it: the addressing detector's first version matched the phrase `at a
  pulpit` and missed a scene reading `at a plain pulpit`, which was the exact spread that prompted
  the guard. Prefer the bare noun, accept some noise, and PROVE the guard fires on the defective
  scene before believing it.
  **The list below is asserted by a test** (`GuardsDocumentedTest`): every `*_GUARD` constant in
  `assemble_prompt.py` must be named here, because this section already drifted once when
  `MOTION_GUARD` shipped 2026-07-28 and was never documented.
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
  - **Motion guard** (conditional; v0.15). When a scene has someone moving toward something, the
    destination must be AHEAD of them in frame and they are seen from behind, because a face toward
    the lens means they are walking away from everything behind them. Earned where a man "stepping
    toward the door" rendered walking at the camera with the lit doorway behind him, so the picture
    said the opposite of the beat.
  - **Addressing guard** (conditional; v0.19). When one person addresses a group, the prompt states
    the two legal cameras: either the camera is among the audience (backs of heads near, speaker
    beyond facing us) or at the speaker (his back to us, audience beyond facing us). The audience is
    never arrayed behind the speaker. Earned three times in one book: a congregation seated facing
    the back wall of its own church, a vote taken at that back wall, and a preacher at a pulpit with
    his congregation blurred BEHIND him. This is a COMPOSITION prior rather than a facing prior, so
    `FACING_TOKENS` cannot neutralise it and naming the camera does not help; the model satisfies the
    camera and then places the people by cliche.
  - **Bedclothes guard** (conditional; v0.19). Someone asleep, waking or getting out of bed wears
    nightclothes, not a suit, with an explicit exception for a scene that states the person is
    dressed. Earned where three spreads put a man in a business suit and necktie in his own bed,
    because his canon asserted a default outfit and canon prose outranks whatever a scene leaves
    unsaid. Fixing the entity was not enough: ANY character with a stated default outfit is put to
    bed in it, in any universe.
  - **Bed-length guard** (conditional; v0.20). When a person is lying on a bed, the bed is drawn
    at true adult length, head at the pillow and feet reaching most of the way down, with the
    footboard beyond the feet rather than at the hips or knees. Earned where an old man lay in a
    bed whose foot reached his waist, leaving nowhere for his legs. The model composes the
    reclining figure to fill the frame and then fits the furniture around the part it drew, so
    the bed gets truncated to whatever the visible body needed. Distinct from the bedclothes
    guard, which fires on bed + a SLEEP signal and governs what the person WEARS; this fires on
    bed + a LYING signal and governs how long the BED is.
  - **Crowd-member guard** (conditional; v0.20). A named character seated inside an audience
    faces the same way everyone around them faces and holds the same posture; if the scene needs
    their face, the CAMERA moves rather than the person. Earned where a book's subject sat in a
    seminar audience and was rotated three-quarters to the lens while every other listener faced
    the speaker, so he alone appeared to be looking away from her. This is the mirror of the
    addressing guard: that one governs geometry BETWEEN a speaker and a crowd, this one governs a
    character INSIDE one, where the pull is not composition cliche but the model's preference for
    showing a protagonist's face, which it satisfies by turning the body instead of the camera.
    Its detector deliberately excludes bare "seated in" / "sits in", which describe the crowd
    itself and fired it on speaker scenes it has nothing to say about.
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

Optional fields, all added in v0.28 so a lookbook can say WHEN it applies and what it forbids:

```jsonc
{
  "always": true,                        // the universe BASELINE: governs every clothed figure
  "appliesWhen": ["children", "meal"],   // context tags that pull it in without anyone naming it
  "negatives": ["no kaftans", "..."]     // goes INTO the prompt; `gate` is checked on the OUTPUT
}
```

- **Consumed** by a renderer (`on-brand-image --lookbook`, repeatable): sample 2-4 refs (varying the
  SUBSET, not merely the order), prepend `aesthetic` + `varietyRule`, add `negatives` to the prompt,
  carry the `gate` into read-back, re-roll a uniform result from scratch. It rides ALONGSIDE a Style
  Pack (pack = medium, lookbook = varied subject). Lookbook refs are ordered AFTER entity refs and
  after the pack anchor: a lookbook is a range to draw FROM, never a thing to reproduce, so it must
  not outrank the subject's own locked plates.
- **Sampling must vary MEMBERSHIP.** A renderer that always hands the model `refs[:n]` has quietly
  turned the lookbook into a Style Pack with extra steps; the range on disk stops being range the
  moment the renderer stops rotating through it. Sampling is seeded (normally on the output path) so
  it varies across a batch while any single render replays identically from its recipe.
- **Bound to a universe** through a **craft-canon register-rule** (§13) whose `lookbook`/`alsoBinds`
  name it, so uniformity can never silently return. (First use: rule `godly-aligned-dress` → lookbook
  `christofuturist-fashion`, because a Christofuturist community that dresses in one beige linen reads as
  a commune, not a flourishing Kingdom.)
- **A craft binding does NOT make a lookbook fire.** It says "this vocabulary is canon here"; `always`,
  `appliesWhen` or an entity binding say "this render obeys it". Conflating the two means resolving two
  people standing together drags in the MEAL vocabulary and the ROOM-DRESSING vocabulary, which is
  exactly what the v0.28 implementation did on its first pass. Bound-but-untriggered lookbooks are
  reported as *available*, so nobody concludes the universe lacks one.
- **The gate is load-bearing, and it checks VARIETY.** A lookbook without a variety gate is a mood board
  that drifts back to a uniform on the first render. `validate` now REFUSES a lookbook with an empty
  `gate`, with refs declared but missing on disk, or with fewer live refs than its own `minRefs`.

**WHY v0.28 EXISTS.** From v0.12 to v0.27 every bullet above except the last two was FICTION.
`--lookbook` wrote the lookbook's name into the recipe, after the image already existed, and did
nothing else: it sampled nothing, prepended nothing and gated nothing, while the engine held zero
lines about lookbooks. Craft canon in two universes instructed renderers to "pass `--lookbook X` so
the renderer samples 2-4 exemplars, applies the varietyRule and gates the output" — three behaviours
described, none implemented, and the recipe asserted the vocabulary had been used. This is the same
defect class as v0.23 through v0.26: **canon that is correct and unexecutable.** The observable cost
was that a universe's clothing rules reached the model only when an agent happened to read the craft
canon and retype it by hand, so the look drifted between sessions for reasons nobody could see.

### 4.7.2 Wardrobe (v0.28) — binding clothes to a PERSON

`structured.wardrobe` on an entity answers "what does *this one* wear", which no primitive could
express before. A lookbook is a universe's vocabulary; a wardrobe is one character's claim on it.

```jsonc
"wardrobe": {
  "lookbooks": ["christofuturist-fashion", "christofuturist-mens-fashion"],
  "era": "the house line, favoring The Texas as his everyday fit",   // prose, steers the look
  "alwaysWears": ["the north-star-cross pendant at the sternum"],    // per-render non-negotiables
  "negatives": ["no beaded devotional strands", "..."],              // garment-level, additive
  "note": "why this binding exists"
}
```

Resolution merges, in order of increasing specificity: the universe **baseline** (`always`) →
**context** triggers (`appliesWhen` vs the render's tags) → each entity's **binding** → anything named
**explicitly**. Later layers only ADD. Nothing removes, because a wardrobe rule that a more specific
layer could silently switch off is the v0.24 lock-gate demotion bug wearing a different hat; an entity
that must not wear something says so in its own additive `negatives`.

`validate` refuses a `wardrobe` with an unknown key, a scalar where a list belongs, or a binding to a
lookbook that is not on disk — the same failure class as a `requiredForRender` naming a sheet with no
path: it reads as a constraint and is silently nothing.

**The point is automatic resolution.** `on-brand-image --entity <universe>:gary` now brings Gary's
bound lookbooks, era, always-worn props and garment negatives with it, without the caller knowing any
of those exist. `abu wardrobe <universe> <entity...> [--context tags]` answers the same question
outside a render. The defect that earned it, 2026-08-01: two fully-locked characters with nine blessed
plates between them had NO wardrobe binding of any kind, and the one prose instruction that gestured
at one pointed at a field that was `null`.

### 4.8 Form (RETIRED ENCODING, v0.17)

**Canon is the matter. A form is what shapes it. A work (§4.9) is canon given form.** That much
holds and is not in question.

**What is retired is the ENCODING, not the concept.** From v0.6 to v0.16 this section specified a
form as `surface` / `requires` / `slots` / `generators` / `invariants` / `emits`, executed by a
single universal composer (§4.10). That model was authored from one imagined example and never ran:
across the whole framework's life it produced **zero works**. No `work.json` was ever written, no
`work/` or `recipes/` directory ever existed, and the one form in the registry
(`scrolling-diorama`) was never worked. It shipped 91 unit tests and nothing made.

Meanwhile the pipeline that has produced more than a hundred illustrated books
(`make-a-book` → `render-book` → `compose-spread`) was never described by this section at all, and
was not even called a composer. The naming had the authority backwards: the proven thing was
unnamed and the unnamed thing was proven.

**The diagnosis, stated plainly so it is not repeated.** A slot schema caps a work at the
imagination of whoever authored the form, frozen at the worst possible moment. The failure was not
in the details of the encoding; it was in specifying a SHAPE where the standard should specify a
STANDARD.

**The replacement is deliberately not written here yet.** A second composer is being built for real
(`garysheng-art-series`, in the `gary-sheng-art` universe). When it is finished and judged good,
the shared surface between it and the book composer becomes this section. Writing the replacement
now, from one instance, is precisely the mistake that produced the retired model. Abstract from the
second instance, not the first.

Until then, a form is whatever a proven composer needs it to be, and no universe is asked to
conform to a schema this section cannot yet justify.

### 4.9 Work (RETIRED ENCODING, v0.17)

A **work** is one instance of a form, and that idea survives. Retired with §4.8 is its encoding: a
`work.json` binding ids to a form's required kinds and filling its declared slots.

Nothing was lost by deleting it, because nothing was ever expressed in it.

**One consequence worth stating.** The v0.6 changelog claimed the narrative fields (`logline`,
`spine`, `refrain`, `beats`) had moved out of `Story Spec` "into the storybook form's slot schema,
where they always belonged," with `Story Spec` retained only as a back-compat alias. That migration
was recorded as done and never happened: no storybook form was ever authored, so `Story Spec`
remained the live primitive that every book actually uses. It is not an alias and never became one.
Treat §4.3 as canonical for stories.

### 4.10 The Composer, the Compiler, and the Gate (v0.17)

The three-part split still holds and is the most durable thing this section ever said:

| Part | Nature | Answers |
|---|---|---|
| **Composer** | agentic, generative | *What should exist?* |
| **Compiler** | deterministic | *What exact prompt does this one slot become?* |
| **Gate** | verifying | *Is what came back actually right?* |

**What changed in v0.17 is the article.** This section said "THE Composer", singular, and a
universal executor was built to be it. The correction: **a composer is per-form.** Each kind of work
plans differently, and a storybook, a diptych series and a deck have genuinely different plans. What
they share is not the plan; it is everything underneath it.

**The compiler is shared and there is exactly one.** It is
`skills/compose-spread/scripts/assemble_prompt.py`, which carries every §4.6 normative guard
(uncast-character refusal, anchor-style guard, single-image guard, `registerAnchor` auto, altLooks,
dropSheets, auto-disambiguation, `guardedNegatives`). The retired composer forked it rather than
calling it, and the fork's 30-line `compile_slot` had none of those guards. That is the second time
this framework has grown two disjoint compilers, and the first time cost real books. There is one
compiler. Do not write a second.

**The gate is a role, not a service** (see `judge-slot`), and it fails closed: a slot whose judged
invariants could not be checked is UNJUDGED, never PASS.

**What belongs under a composer rather than inside one** is still being drawn, and is the open
question this section will answer once two composers exist to compare. The candidates, all of which
the retired executor implemented and none of which are form-specific: durable per-slot state,
resumability, recipes and drift-checking, provider adapters, and plan-time feasibility refusal
(which is not form machinery at all, but simply the first incremental eval).

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
    "rejectedPoles": ["photoreal", "anime", "washed-out"],
    "anchorSubject": "an ancient oil lamp, a clay jar, robed figures" // optional: what the anchor DEPICTS
  }
}
```

**Register (v0.4).** A universe renders in one illustrative style. `identity.register` names it and
points at a content-neutral **style anchor** the renderer passes as the first reference on every
render, with `rejectedPoles` baked as negatives. A per-property `register` (SPEC §4.3) may still
override it. `start-new-story-universe` defaults `register.name` to "detailed comic book" and locks
the anchor via a style-lock step.

**`register.anchorSubject` (optional).** When the anchor is not perfectly content-neutral, this
field NAMES what it depicts, so a renderer can ban that subject concretely on every render. The
generic "take no subject from the style anchor" guard loses to a concrete picture: an oil-lamp
anchor put its own lamp and jar onto a spread that carried EIGHT other references, because the
scene had a table and the anchor had tabletop objects. Declared once per universe; kept in sync
with `anchor` (if the anchor image changes, this sentence changes with it). Consumers: Nation of
Fire's spread compiler negates it at render time (where the field was first earned), the
framework's `chain_matrix` negates it on every matrix shot (2026-08-02; before that, every matrix
shoot had to hand-negate it in prompts.md, and three did in one book run), and the framework's
cover compiler (`cover/compile_cover.py`, which `render_cover.py` delegates to) negates it on
every cover (2026-08-02; a cover passes the anchor FIRST like everything else, and the
readiness-lamp anchor painted an ancient burning oil lamp onto a cover wall — one paid re-roll on
eleventh-hour-heroes). When `--anchor-ref` overrides the anchor image, the cover compiler skips
the register's declared subject, because the sentence no longer describes what the first
reference depicts; a Style Pack override in `chain_matrix` likewise reads the PACK's own
`anchorSubject`. The framework's own spread composer (`compose-spread/assemble_prompt`) does NOT
yet read it and carries only the generic anchor guard; that gap is logged, not hidden. A Style
Pack may declare the same field for the same reason.

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

**Cross-entity refs in a shoot, and the `@sheet` selector (v0.25).** A shot in
`reference/<id>/prompts.md` declares the OTHER canon entities it shows, so they are
conditioned on their locked art rather than redrawn from prose:

    **Refs (every shot):** <entity-id>, ...          (header, applies to every shot)
    REFS: <entity-id>, ...                           (in a shot body, that shot only)
    REFS: <entity-id>@<sheet>+<sheet>, ...           (v0.25: name the sheets)

A **bare id** passes that entity's `requiredForRender` set, which is unchanged and is the
common case. An **`@sheet+sheet` selector** names additional sheets, which are passed FIRST,
with `requiredForRender` still following. **A selector may raise the ref set and must never
lower it** — v0.24's lock rule one layer out, and for the same reason: the mechanism that
lets an author say MORE must not quietly become a mechanism for saying less. A selector
naming a sheet the entity does not declare, or declares with no art on disk, is a REFUSAL
rather than a shrug, because silently ignoring a mistyped selector sends the render off with
exactly the plate set the author was trying to add to.

**A REQUIRED sheet that is not on disk YET is DROPPED; a SELECTED one still refuses (v0.30).**
The two halves of the wanted set are held to different standards on purpose. A sheet the
author NAMED in the token must exist, for the reason just given. A sheet that arrived only
because it sits in `requiredForRender` is silently skipped when its art has not been made
yet, and the shoot proceeds on whatever remains; if nothing remains, that is a refusal.

This applies during a REFERENCE SHOOT only, where a not-yet-existing plate is the normal
state of the world rather than an error. `requiredForRender` is the gate on RENDERING a
spread, and `assert-story` and the compiler still enforce it in full there.

The defect that earned it (2026-08-03, nation-of-fire `he-is-a-jealous-god`): the
blueprint-seeded chain this spec and `make-a-book` both prescribe for a multi-state object.
`the-aimed-mirror` had a code-drawn `blueprint.png` on disk and four state plates yet to be
shot, so its seed shot said `REFS: the-aimed-mirror@blueprint`. That refused, because
`requiredForRender` named `master`, whose art the shoot was about to create. The only way
past it was to temporarily rewrite `requiredForRender` to a sheet that already existed,
shoot, and put it back after locking, which is an author falsifying an entity's own render
gate to satisfy a check about something else. A guard that can only be cleared by lying
about canon is a guard that teaches people to edit canon.

Tokens are merged by ENTITY, not by string, so a header `Refs` and a per-shot `REFS` naming
one entity resolve it once. Each ref is recorded in the shot's `.recipe.json` under
`crossEntityRefs` with its `sheet` name as well as its path and hash: once two shots can
reference one entity with different plates, "entity + path" no longer identifies what was
approved in a form a later divergence check can read.

The defect that earned it: an entity's extra sheets were unreachable from a shoot. A
multi-angle `turnaround`, a worn/in-situ plate, or a material variant could be registered and
provenanced and named by the entity's own `structured.render.always`, and no shot could ask
for it. On christofuturism's `north-star-cross` the fabrication spec explicitly prefers the
turnaround because a single flat front view flattens back into an equilateral star; three
flat plates were all the resolver could pass, and the rendered pendant measured 1.79:1
height-to-width against a spec of 1.24:1.

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
  - **`scale-plate` (v0.22) — the plate that makes a declared height CHECKABLE.** The `scale`
    record above is RELATIVE. It fixes two people against each other and cannot fix either
    against the world, and its `height` is prose that nothing depicts. Between them they answer
    "is he taller than her" and never "how tall is he", so a solo `forward-fullbody` on a blank
    ground still carries no unit of comparison: the model picks a stature and every render
    inherits the guess. That is v0.9's own sentence about rooms, unpaid for people — *a plate
    cannot be judged on a dimension it does not depict.*

    A `scale-plate` is a **solo, head-to-toe plate against a measured reference**, listed in
    `structured.sheets` like any other shot. The framework fixes the GEOMETRY, because that is
    what makes the plate readable at all:

    <!-- BEGIN GENERATED: scale-plate-contract -->
- solo subject, no second figure in frame
- full head-to-toe, feet visible and flat on even ground, nothing cropped
- camera at mid-torso height, square to the subject, no low or high angle
- no perspective foreshortening; the figure reads at true proportion
- a MEASURED reference in frame whose real size is stated in the recipe
- the subject's declared `structured.scale.height` is legible against that reference

Default measured reference, when a universe declares no `identity.scaleReference`: a discreet graduated vertical batten marked at each foot, or an architectural element of stated height (a door, a standard step riser, a counter) with its real dimension recorded in the plate's recipe
<!-- END GENERATED: scale-plate-contract -->

    The universe supplies the TREATMENT, via `identity.scaleReference`. The default is
    deliberately architectural rather than clinical: a graduated batten or a door of stated
    height reads as part of a built world in nearly every register, where a medical stadiometer
    reads as a prop and a symbolic or painterly universe would refuse it outright. Gary's ask
    (2026-08-01) was for "a measuring stick or something TASTEFUL", and taste here is
    register-local, which is exactly why the framework declines to fix it.

    It is a SEPARATE file from `forward-fullbody` and never a replacement: renders still cast
    the fullbody, and the scale plate is what a human and a linter read the height from.
    `optional`, not in `shots`, for the same reason `face-neutral-color` is — promoting it would
    demote every already-locked character in every universe to `partial`. Advisory:
    `lint-universe` warns `CHARACTER-NO-SCALE-PLATE`, `CHARACTER-HEIGHT-UNDEPICTED` (a height is
    declared but nothing on disk depicts it, the precise v0.9 failure) and
    `CHARACTER-SCALE-PLATE-MISSING`.
  - **A slot may declare its ROLE (v0.23).** `"sheets": {"denim-front": {"path": "...", "role":
    "garment"}}`. Roles are `identity` (face and likeness), `geometry` (shape and proportion),
    `garment` (the CUT of clothing, never its medium), `medium` (the paint language itself) and
    `scale` (see `scale-plate`). The bare-path form is unchanged and still correct; a slot that
    declares no role behaves exactly as it always did, which is why this migrates nothing. What
    the role buys is a per-ref instruction in the prompt — `REFERENCE ROLES, obey exactly:` —
    so the model is told what each reference is for instead of weighing them all equally. Earned
    on two watercolour costume plates that were admissible as matrix slots on a hyperreal
    character because their sidecars said "garment design only" in prose no gate could read.
  - **`structured.sheetAliases: {newKey: oldKey}` (2026-08-02) — a DECLARED sheet alias.** The
    add-keys-never-remove pattern (a camera slot renamed without breaking every story or spec that
    names the old key: retired-hearthRotunda precedent; the-park-bench and apostle-lee-study camera
    aliases) used to be encoded by writing BOTH keys into `sheets` pointing at one file, which is
    indistinguishable from a dead duplicate and tripped `SHEET-DUPLICATE-ALIAS` on every
    intentional rename. Declaring the alias makes the intent a record: the resolver treats the
    alias as a sheet-lookup fallback (one hop; a real `sheets` key always wins), `validate` refuses
    an alias to nothing, to itself, or one whose two keys have diverged to different files, and
    lint skips declared aliases while undeclared duplicates still warn. `requiredForRender` naming
    both halves of an alias is still an error, because the same image passed twice carries no
    information regardless of intent.
  - **`structured.negatives` (v0.23) — a negative that names ONE person.** Emitted only on
    spreads where that entity is in frame. Some rules are absolute about an individual and must
    be silent about everyone else: a universe may forbid glasses on one character while
    explicitly permitting them on others, and a flat pack `rejectedPoles` entry cannot express
    that without overruling the second decision.
  - **`structured.altLooks` (documented in v0.10; load-bearing in the compiler well before it).**
    A named look that REPLACES part of the entity's identity for the spreads that select it:
    `{ "anchorPhoto", "sheets", "supersedes": [], "invariants": [], "dropSheets": [],
    "keepSheets": [], "keepPhotos": false, "render": {} }`. `supersedes` removes base invariants
    the look contradicts and `invariants` adds its own, so the QA checklist, the prompt block, and
    the computed negatives all agree by construction. `dropSheets` removes base sheets the look
    contradicts, because **a reference image outranks a word**: a look whose invariant said "neck
    completely bare" still had the adult pendant sheet passed, and the necklace rendered. An alt
    look **auto-drops the base FACE sheets**, since the look's own `anchorPhoto` is the face.
  - **`structured.render.poses.<key>.supersedes` / `.invariants` / `.negatives` (v0.29) — when the
    thing that changes is a POSE, not a look.** A pose could add a `bake` sentence and extra
    `sheets` and could not retire anything, so a pose that INVERTS one signature invariant had no
    legal expression. An `altLook` is the wrong instrument whenever the FACE must not change, because
    a look auto-drops the base face sheets; the only remaining move was hand-wording the base
    invariant as "...except in pose X", which is a rule enforced by an author remembering to phrase
    it and a read-back checklist that contradicts itself. A pose now retires base invariants and
    base negatives by exact string exactly as a look does, and adds its own, so **the prompt block,
    the QA checklist and the computed negatives agree by construction** for a pose as well as for a
    look. A pose that declares none of the three compiles exactly as before. Earned on
    `theo-doorchaser` (*The Tithe Is a Test*, 2026-08-02), whose jacket is worn half-on with the left
    sleeve off the shoulder in one recurring pose and fully on everywhere else.
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
  - **A DOCUMENTED PAST uses the same two fields, and this is not obvious from their name.**
    `keepSheets` / `keepPhotos` were introduced for a declared FUTURE, but the mechanism is
    TEMPORAL-DIRECTION-AGNOSTIC: it serves **any era the photo stack does not cover**, forward or
    back. A historical subject has exactly the same shape as a prophetic one. There is no
    photograph of Kenneth E. Hagin bedfast at fifteen in 1933; the only photographs that exist are
    of him in his eighties, so the two eras with no ground truth are both in the PAST.
  - **Where the photographs land decides the SHOOTING ORDER, and the order is load-bearing.**
    The default assumption is that the default look is shot from the photo stack and every era
    chains off it. When the photographs cover a NON-default era, **shoot the era that has ground
    truth FIRST and chain the others off it**, so the whole chain converges on one face. On
    `kenneth-hagin` that runs fully inverted: `elder` is shot from the two public photographs, the
    default young look is chained off `elder`, and `bedfast` is chained off the young look. Shooting
    the three eras in parallel from prose returns three different men who merely share a
    description, which is the failure the golden chain exists to prevent. A look whose photographs
    ARE the ground truth declares its own `anchorPhoto` / `photoStack`, which outranks the base face
    sheets by design.
  - **Locking an alt-look's art:** `lock-shot <universe> <id> <shot> <path> --look <key>` writes
    into `structured.altLooks[key].sheets` instead of the default matrix. It deliberately never
    touches `requiredForRender`, which is the DEFAULT look's gate: an era plate must not be able
    to satisfy it, or a character with no present-day body sheet would read as gate-real off a
    future one. An unknown look key is REFUSED rather than created, because a typo would
    otherwise mint a look nothing selects and no read-back ever checks.
  - **`validFor`: WHICH ERA A VARIANT IS LEGAL IN (v0.18).** A variant is a body a thing wears for
    part of its life, and until v0.18 nothing gated which one a spread could select: every altLook
    was equally legal on every spread. On a book spanning three ages of one man, nothing stopped a
    1933 beat picking the `elder` look, and nothing stopped a 1990 beat silently falling through to
    the default young face. **Both failures are silent.** The render succeeds, it is internally
    consistent and beautiful, and it is simply of the wrong person, so it survives read-back (which
    checks invariants, and the wrong era's invariants all pass) and is caught only by a human who
    happens to look at the date.
    - A variant may declare `"validFor": { "from": <n>, "to": <n> }`, either bound optional, so an
      open-ended era ("from 1974 onward") is expressible. A spread declares `"when": <n>`. Both are
      plain NUMBERS and the framework only ever compares them, so a universe may count in years or
      in beat indices without the framework knowing which.
    - **The DEFAULT look carries its window at `structured.validFor`**, not only the alt looks. The
      dangerous case is not merely picking the wrong alt look; it is FORGETTING to name one, and a
      gate that cannot see the default cannot catch that.
    - `compose-spread` REFUSES pre-spend and **names the variant that is legal at that date**, which
      is where the saving is: a gate that only says no still sends the operator to read canon.
    - **Opt-in at both ends, so nothing migrates.** A spread with no `when`, or an entity whose
      variants declare no window, compiles exactly as before. The gate fires only when both facts
      are stated and they contradict each other.
    - `lint-universe` sees what the compiler cannot: the shape of the whole variant SET.
      `VALIDFOR-PARTIAL` warns when some variants declare a window and others do not, because an
      undeclared variant stays legal at every date and the gate then has a hole precisely where the
      author believed it was closed. `VALIDFOR-INVERTED` and `VALIDFOR-MALFORMED` are errors.
    - Earned 2026-07-31 on `the-power-of-obeying` (69 spreads, 1917 to 2003), where the look had to
      be named by hand on all 71 spreads because nothing could check it.
- **setting** — the existing `contract`: `turnaround`, `emptyPlates[]`, `blueprint` (files) plus
  `map`, `blocking`, `dressing` (descriptors), **and `scalePlate` + the `scale` descriptor (v0.9)**.
  - **WHAT `locked` MEANS FOR A SETTING, IN ONE PLACE (v0.29).** The gate fields are
    `turnaround` + `blueprint` (non-null and on disk), `emptyPlates` (non-empty, all on disk) and the
    `map` / `blocking` / `dressing` descriptors (non-empty). `scalePlate`, `scale` and
    `blockingPlate` are **advisory** and never block promotion or rendering, which this section has
    said since v0.9. Three surfaces used to answer this question and gave three answers: `lock-shot`
    and `abu list` demanded every field including the advisory ones, while `resolve_setting`, the
    gate that actually refuses a render, looked at none of them. So a setting whose empty plates must
    contain no people (a painted scale plate would drag figures into every state of it) could never
    be promoted by the tool at all and had to be hand-flipped to `locked` in its JSON, which is the
    hand-editing the engine exists to remove. All three now call one predicate,
    `model.setting_contract_gaps`, and `lint-universe` warns `SETTING-LOCKED-BUT-GATE-REFUSES` on
    older canon whose recorded status the gate contradicts (six such entities in nation-of-fire).
  - **`contract` DESCRIBES the art; `structured.sheets` is what the RESOLVER READS (v0.30).**
    An entity that fills the first and leaves the second empty looks completely finished:
    `status: locked`, files on disk, every one carrying provenance. It fails much later and
    somewhere else, as `compose-spec` printing `available: NONE` for a place the author has
    already written into a beat, at which point no plate is passed and the spread renders off
    the style anchor alone. `lint-universe` now warns `LOCKED-BUT-NO-SHEETS` on any LOCKED
    entity that declares contract plates and no `sheets`, and prints the deterministic repair
    (`contract.turnaround` -> `sheets.turnaround`, `blueprint` -> `sheets.blueprint`, each
    `emptyPlates` entry -> its basename) as pasteable JSON rather than as a description of it.
    Unlocked entities are never flagged: `add-setting` scaffolds exactly that shape and it is
    correct until `shoot-references` fills the plates. Earned 2026-08-03 (nation-of-fire
    `he-is-a-jealous-god`) on `the-great-stage`, locked since 2026-07-19 with four plates and
    never once cast through the framework compiler, with ten sibling entities in the same state.
  - **`contract.emptyPlatesExpected` (v0.29, optional int) — the declared COUNT.** Without it the
    gate can only ask whether the list is non-empty, so a setting that genuinely needs four cameras
    is promoted to `locked` on the second and the two nobody shot are improvised at render time,
    differently every spread. Omit it to keep the old behaviour.
  - **A SETTING'S CONTRACT RIDES ON EVERY BOOK THAT REUSES IT, so it must hold nothing that
    belongs to ONE story (v0.29).** `contract.dressing` is injected into every prompt that casts the
    place and `contract.blockingPlate` is passed as a REFERENCE IMAGE on every one of those renders,
    whichever camera plate was selected, because placement is continuity rather than composition.
    Both are correct for the setting and catastrophic for a prop. `the-park-bench` was authored for
    *Will There Be Ice Cream*: its `dressing` read "Each of them holds an ice cream cone" and its
    blocking plate showed two mannequins holding cones. Three of the first seven spreads of an
    unrelated book came back with both men holding ice cream, through scene text AND a per-spread
    negative that banned ice cream BY NAME on every one of them. **A reference image plus an injected
    contract sentence together outrank a negative word**, which is the same law §12 already states as
    "a reference image outranks a word", one level up.
    - The durable fix is to move the prop into the spread's `scene` and reshoot the plate propless.
      `lint-universe` warns `SETTING-DRESSING-NAMES-HELD-PROP` when a setting's `dressing` or
      `blocking` says a person is holding, carrying or wearing a named object.
    - The escape hatch for the spread in front of you: `"blockingPlate": false` on the cast entry
      drops the plate for that spread, and `contract.plates.<plate>.includeBlockingPlate: false`
      drops it for every spread that selects that camera. Absent either, behaviour is unchanged.
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
  - **TWO ERAS OF ONE PLACE STAY ONE ENTITY, and its ERA AXIS IS ITS PLATES (v0.18).** A setting
    deliberately does NOT get an `eras[]` array parallel to a character's `altLooks`. When a place
    must appear in two periods, the reason it is in the story at all is usually that **it is the
    same ground**, and splitting it into two entities destroys the only claim it exists to make.
    So both eras live in one `contract`: one `map` for the geometry that never changes, one
    `blueprint` (the code-built massing render of §12/v0.15) that BOTH eras are seeded on, and one
    `emptyPlates` list holding each era's plates. `blocking` and `dressing` name what each era adds
    and removes.
  - **A plate declares its own era window** under the existing per-plate config map,
    `contract.plates.<plate>.validFor` (see `validFor` above), so a dated spread cannot select the
    wrong period's plate. `contract.plates` already existed to scope what a close-up is told, so
    the era window needed no new schema shape.
  - **Compose both eras so one image can be laid over the other.** Name the MATCH POINT (a ridge, a
    roofline, a doorway) in `blocking` and require it visible in every plate of every era, or the
    two eras become two places that merely share an entity id. Earned 2026-07-31 on
    `the-broken-arrow-ground`, one Oklahoma parcel as a 1900s farm and as the 1976 site bought for
    RHEMA, whose whole argument is that the ground is the same.
- **visual-metaphor** — a locked master plus `state` plates (the object across its argued states).
- **prop / motif** — `hero` plus `detail` crops.
  - **`prop.structured.scale` and an optional `prop` `scale-plate` (v0.22).** A prop had no size
    record of ANY kind, neither descriptor nor plate, which is the character defect one level
    down: an object that renders at the wrong size beside a figure is as wrong as a room that
    renders too small, and a pendant, a chair and a door were each whatever size the model
    assumed. This is the other half of Gary's 2026-08-01 ask — how tall different people **and
    different things** are. State the size in human terms (`"about 40 mm across, worn at the
    collarbone"`) and shoot a `scale-plate` when the object's size is load-bearing. Advisory:
    `lint-universe` warns `PROP-NO-SCALE`. A motif is a graphic signature rather than a physical
    object, so it takes neither.

**`lock_level(entity) -> stub | partial | locked`** (engine) reports completeness against the kind's
matrix. It is **advisory** in v0.4 and back-compatible: an entity that predates the matrix, or uses
its own sheet-key names, reports `partial` when its own `requiredForRender` resolves — it is not
broken, just not matrix-complete. The load-bearing gate (`assert_story` / `assert_spread`) is
unchanged: a missing REQUIRED sheet is still a hard error. A renderer MAY require `locked`.

## 14. Why this runtime is Managed Agents (v0.6)

> **STATUS, v0.17: ASPIRATIONAL, NOT DESCRIPTIVE.** Nothing in this framework runs on Managed
> Agents. The composer this section argues for was deleted in v0.17 having never run, and the
> pipeline that does the work (`make-a-book`) runs locally. The argument below about the SHAPE of
> the workload is still believed to be correct, and hosted execution remains the intended
> direction. It is recorded here as a claim about where this is going, not a description of how it
> works today. A reader deciding what to build on should treat local execution as the only reality.
>
> The one real body of Managed Agents work lives outside this repo, in `garysheng-books/scripts/`
> (`ma_session.py`, `ma_render_helper.py`, `render-narration-on-ma.py`), and is book-shaped rather
> than framework-shaped. Bringing it in is a live option, not a done thing.

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
- **Story spec (§4.3)** — a medium-neutral spec selecting canon + beats + spine + provenance. The
  live primitive every book actually uses; it never became an alias for anything else (§4.9).
- **Renderer** — a pluggable projection of canon + story into one medium.
- **Craft-canon** — narrative-craft rules encoded as enforceable invariants (discovered, then encoded).
- **Write-back** — the new canon a finished story contributes to the universe.
- **Gate** — a point where human taste or a hard check must pass before proceeding.
- **Spine** — a story's declared arc invariant (obedient-servant, thesis, primer, testimony, …); not
  a single assumed shape.
- **Visual-metaphor** — an entity kind: the central object a whole book zooms into and argues through
  (the locked scale, the bazaar of cages); the book's spine-object.
- **Form (§4.8)** — what makes a work the KIND of thing it is (storybook, flyer, meme, share card,
  explanatory plate). Called *Projection* before v0.14. How a form is encoded is an OPEN question:
  the v0.6–v0.16 typed contract (surface, required kinds, slots, generators, invariants) is retired
  and §4.8 records that retirement rather than specifying a live contract.
- **Work (§4.9)** — ONE made thing: canon given form, carrying authorship present in neither. Called
  *Composition* before v0.14. Its v0.6–v0.16 encoding is retired with §4.8's. It never superseded
  `Story Spec`, which is still the live primitive for stories (§4.3).
- **Composer (§4.10)** — the agentic layer that plans a work and sequences its generation, answering
  to the gate. **Per form**, not one universal executor. The only layer where open-ended model
  intelligence belongs.
- **Gate, `computed` vs `judged` (§4.10)** — an invariant checkable by pure code versus one requiring
  a model to look. A `judged` invariant is evaluated in fresh context by an agent that never sees the
  plan, because the maker defends its own intent.
- **Cross-slot invariant** — an invariant only checkable across several generated units at once (a
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
