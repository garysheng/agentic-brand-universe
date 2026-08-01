# Reference

Every table on this page is **generated** from the thing it describes. Do not hand-edit inside the
`BEGIN GENERATED` / `END GENERATED` fences: `abu build-docs` overwrites them, and
`build-docs --check` (which runs inside `./run-tests.sh`) fails the suite when they drift.

To change a row, change its source. The skill table comes from each `skills/*/SKILL.md` frontmatter,
the CLI table from the real argument parser, the provider table from `registry/providers.json`, the
form table from `forms/*/form.json`, and the changelog from `SPEC.md`.

For the narrative introduction see [`../README.md`](../README.md); for the architecture see
[`ARCHITECTURE.md`](./ARCHITECTURE.md); for the contract itself see [`../SPEC.md`](../SPEC.md).

## Skills

The framework is used mostly through these. They are universe-agnostic: each takes the target
universe or style pack as a parameter and hardcodes nothing about any particular one.

If you are new, the two that need no universe are `create-style-pack` and `on-brand-image` — a look
plus a gate is the smallest useful slice of the framework, and it is enough to make a zine, a deck,
or a set of page heroes without ever declaring canon.

<!-- BEGIN GENERATED: skills -->
| Skill | What it does | Tested |
|---|---|---|
| `abu` | THE FRONT DOOR to Agentic Brand Universe. |  |
| `add-character` | Add ONE character to an Agentic Brand Universe: interview the source (a real person's story/wardrobe/sensitive-list, or a fictional design brief), reuse-first via casting sweep, then scaffold a typed `character` entity with the SPEC §12 reference-matrix slots (8 shots) and a ready-to-run generation prompt per shot. |  |
| `add-generator` | Add ONE deterministic generator to a universe (SPEC v0.13 §4.11) — code that DRAWS an asset instead of prompting for one. |  |
| `add-motif` | Add ONE motif (a recurring visual element, gesture, or pattern that must render identically wherever it appears, not a one-off image) to an Agentic Brand Universe (interview what it is and its load-bearing detail, reuse-first via casting sweep, then scaffold a typed `motif` entity with SPEC §12's hero + detail reference slots and ready-to-run generation prompts). |  |
| `add-prop` | Add ONE prop (a discrete physical object a character holds, wears, or uses, that must render identically wherever it appears) to an Agentic Brand Universe (interview what it is and its load-bearing detail, reuse-first via casting sweep, then scaffold a typed `prop` entity with SPEC §12's hero + detail reference slots and ready-to-run generation prompts). |  |
| `add-relation` | Record ONE typed relation between two ids in an Agentic Brand Universe's canon graph (`crossover-with`, `appears-in`, `derived-from`, `contradicts`, `supersedes`) as a `from`/`rel`/`to`/`story`/`note` record written to `canon/relations/`. |  |
| `add-setting` | Add ONE setting (a location) to an Agentic Brand Universe (interview its fixed geometry, fixed camera angles, and dressing, reuse-first via casting sweep, then scaffold a typed `setting` entity with SPEC §12's contract slots (turnaround, per-angle empty plates, blueprint, plus map/blocking/dressing descriptor prose) and ready-to-run generation prompts). |  |
| `add-story` | Add ONE story to an Agentic Brand Universe as a typed StorySpec (a medium-neutral work over canon, NOT an `add-entity` kind). |  |
| `add-visual-metaphor` | Add ONE visual metaphor (a spine-object a whole property argues through, not merely a location) to an Agentic Brand Universe (interview the object and the states it argues across, reuse-first via casting sweep, then scaffold a typed `visual-metaphor` entity with SPEC §12's setting-style contract: a locked master plus per-state plates, and map/blocking/dressing descriptor prose). |  |
| `book-doctor` | Grade a RENDERED book on local disk against what its render-spec declares, BEFORE it is delivered anywhere. | yes |
| `canon-resolve` | Before writing ANY render prompt in an Agentic Brand Universe, resolve every named character, setting, and motif to its canon entity: output the locked sheet paths (requiredForRender), the invariants to enforce, and the entity's prose rules, then run the load-bearing gate (assert.sh spread\|story). |  |
| `casting-sweep` | Before naming any NEW character, setting, or motif in a story, sweep the universe's canon for an existing entity that fits the role natively, and emit a casting table (each role: reuse an entity id, or NEW plus a one-line justification). |  |
| `compose-spec` | Scaffold and RE-SYNC a book's render-spec from its StorySpec, filling everything canon determines, enumerating every legal choice canon constrains, and never overwriting authored scene text. | yes |
| `compose-spread` | Render ONE spread of an Agentic Brand Universe book as an atomic unit — resolve canon, deterministically ASSEMBLE the prompt + refs from canon (register-anchor-first, each in-frame entity's block for its SELECTED look including alt-looks, auto-disambiguation, and negatives COMPUTED from the selected looks so a blanket negative can never fight a canon alt-look), generate, then read back. | yes |
| `cover` | Create a picture-book cover for a story in an Agentic Brand Universe, at the platform's portrait aspect. | yes |
| `create-lookbook` | Scaffold a Lookbook (SPEC §4.7.1) — a portable folder (lookbook.json + refs/) that defines a curated but intentionally VARIED visual vocabulary (a wardrobe/fashion, a range of building silhouettes, a set of faces), the complement of a Style Pack. | yes |
| `create-style-pack` | Scaffold a Style Pack (SPEC §4.7) — a portable folder (pack.json + refs/) that defines ONE look and is consumable by on-brand-image with no universe. |  |
| `evolve-abu` | Evolve the Agentic Brand Universe framework itself — its skills, engine, spec, templates, and plugin — instead of hand-rolling around its gaps. |  |
| `judge-slot` | Judge one generated slot against an entity's locked golden, item by item over its declared invariants, in a context that has NOT been told how the slot was made. |  |
| `land-work` | Merge a finished work branch home instead of leaving it parked, in ANY git repo (a universe, a platform repo, a site, anything). |  |
| `lint-universe` | Lint a brand universe. Static checks over the universe and everything it declares (style packs, entities, goldens, provenance, craft canon, provider quirks) with no generation, no API calls, and no cost. | yes |
| `make-a-book` | The base orchestrator for making an illustrated, narrated picture book in ANY Agentic Brand Universe universe. |  |
| `make-a-work` | Make ONE work in a form a universe already declares — a flyer, a card, a poster, a scene, whatever forms/ holds. | yes |
| `on-brand-image` | Generate ONE on-brand image from a Style Pack (SPEC §4.7) — a portable folder of style references plus a read-back gate — with NO universe required. | yes |
| `onboard` | Install Agentic Brand Universe for someone, as a conversation rather than a list of commands they have to run. |  |
| `pave-the-path` | The retrospective sweep at the END of a chain run. | yes |
| `render-book` | Render a story from an Agentic Brand Universe into a picture book. |  |
| `render-readback` | After EVERY render in an Agentic Brand Universe, read the image back and crop-zoom each of the in-frame entity's invariants, returning a per-invariant PASS or DEFECT verdict. | yes |
| `shoot-references` | SHOOT an entity's reference matrix in an Agentic Brand Universe: make the art that gives a scaffolded entity a body. | yes |
| `start-new-story-universe` | Stand up a brand-new story universe on the Agentic Brand Universe framework — a typed, git-versioned canon with a load-bearing pre-render gate, conforming to a named spec version. |  |
| `universe-doctor` | Grade how COMPLETE and how HIGH-QUALITY an Agentic Brand Universe is, then work the punch-list. | yes |
| `update-book` | Edit or extend an existing picture book in an Agentic Brand Universe: add, insert, revise, or remove a spread, renumber, and regenerate only the touched art + narration. |  |
| `voice-gate` | Run a voice check on any manuscript, narration script, or overlaid caption text BEFORE it is locked or rendered to audio, in an Agentic Brand Universe. |  |
<!-- END GENERATED: skills -->

## CLI

The engine. Stdlib only, no network, no API key, and it generates no images: it types canon,
answers questions about it, and refuses renders whose references do not exist on disk.

<!-- BEGIN GENERATED: cli -->
| Verb | What it does |
|---|---|
| `add-entity` | scaffold a schema-valid entity stub with reference-matrix slots |
| `archive` | retire an entity from NEW casting (history keeps rendering) |
| `archived` | list retired entities, or who still casts them |
| `assert-spread` | the pre-render gate for ONE spread's cast and location |
| `assert-story` | the pre-render gate: refuse a story whose cast lacks real art on disk |
| `backfill-prompts` | recover a scaffolded prompts.md from the recipes beside it, so a matrix shot outside the framework still records its prompts |
| `backfill-provenance` | record provenance for art that predates the adapter, without regenerating it (never invokes a model) |
| `build-canon` | regenerate CANON.md from canon/properties + canon/crossovers |
| `build-docs` | regenerate the framework's own derived docs (README + docs/REFERENCE.md) |
| `crossovers` | list the crossovers an entity appears in |
| `elevation` | render an OBJECT's blueprint as a code-built 2D elevation sheet from a declarative spec (deterministic, no model, no cost) |
| `init` | scaffold a new universe (conforms to spec v0.18) |
| `land` | merge a finished work branch home, or queue it if that is not safe yet |
| `list` | list every entity in a universe |
| `list-craft` | list a universe's craft-canon records |
| `lock-level` | report how locked an entity is (which matrix slots are filled) |
| `lock-shot` | lock a generated reference shot into an entity |
| `massing` | render a setting's blueprint as a code-built 3D massing sheet from a declarative spec (deterministic, no model, no cost) |
| `massing-scaffold` | write a STARTER massing spec for a rectangular room (shell + opposed cameras + notes stub) to edit, so authoring a blueprint does not start from a blank file |
| `relations` | list an entity's typed relations |
| `unarchive` | put a retired entity back in service |
| `validate` | typecheck a universe against the spec schema |
<!-- END GENERATED: cli -->

## Forms

A **form** is what makes a work the KIND of thing it is; a **work** is one made thing, canon given
form. The concepts survive; the v0.6–v0.16 encoding of them (a typed contract of surface, required
kinds, slots and generators, plus the universal composer that executed it) was **retired in v0.17**
having produced zero works, and the `add-form` / `add-work` verbs went with it. No replacement schema
is written until a second composer is proven — see SPEC §4.8, §4.9 and §4.10. The table below lists
whatever forms this repo still ships, and is empty when it ships none.

<!-- BEGIN GENERATED: forms -->
| Form | Medium | What it is |
|---|---|---|
<!-- END GENERATED: forms -->

## Providers

Provider knowledge, not brand knowledge: what a specific model gets reliably wrong regardless of
what you are making. It attaches to the provider, so every universe benefits when one project learns
something.

<!-- BEGIN GENERATED: providers -->
| Provider | Recorded quirks |
|---|---|
| `gpt-image-2` | 3 |
<!-- END GENERATED: providers -->

## Spec changelog

Headlines only, parsed from `SPEC.md`. Read the spec for the full text of any entry.

<!-- BEGIN GENERATED: spec-changelog -->
| Version | What changed |
|---|---|
| v0.18 | a VARIANT may declare WHICH ERA it is legal in. |
| v0.17 | the slot-model composer is RETIRED, having never run. |
| v0.16 | an entity has a LIFECYCLE, so canon can be RETIRED without rewriting history. |
| v0.15 | a setting's blueprint is a CODE-BUILT 3D MASSING RENDER. |
| v0.14 | Projection/Composition become Form/Work. |
| v0.13 | deterministic graphics get a typed home. |
| v0.12 | text is gated, not banned. |
| v0.10 | a character must be able to prove its own scale, and its future. |
| v0.9 | a setting must be able to prove its own size. |
| v0.8 | the compiler guards come home, and a spread may carry its own register. |
| v0.7 | the cover-conform convention. |
| v0.6 | the projection release. |
<!-- END GENERATED: spec-changelog -->
