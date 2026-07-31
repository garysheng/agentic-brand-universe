# SAVE-LOG — Agentic Brand Universe

Checkpoint anchors for /save-your-progress (incremental saves read the last line).

The framework (NOT content): a first-principles system for compelling, agentically
writable, composable, evolvable story generation. Destined for `agenticstory.wiki`.
Five layers — Canon → Refs → Story spec → Renderer → Quality; universe-first; canon
medium-neutral; quality = taste × craft × truth; evolution = git; agent-writable by
construction.

2026-07-15T20:33:34Z · 598e16e · FRAMEWORK BORN this session. Spec v0.2 (SPEC.md) folds in 4 findings from backtesting the ~24 existing Nation of Fire books: non-journey story spines, a `visual-metaphor` entity kind, `register` as first-class, a `realPerson` dossier; plus craft-canon-discovered-then-encoded and story `status: stub|full`. README.md + a published presentation Artifact (docs/agenticstory.html — https://claude.ai/code/artifact/002eb4fe-03c3-456d-add3-49cd33b84f8c). Running engine in `engine/` (Python, 11 tests green): model.py (Entity/Relation/StorySpec + validation, StorySpec.status, Entity.is_locked_setting), store.py (CanonStore: loads a universe dir, graph queries, validate_canon; relation targets may be entity OR story), refs.py (resolve_entity_assets, resolve_setting, assert_story = THE pre-render gate, assert_spread), cli.py (validate/list/crossovers/relations/assert-story/assert-spread). Self-contained synthetic fixture in tests/fixtures/example (hero/sage/guide/the-hall) so the engine is decoupled from any content repo. MOST RECENT FIX (598e16e): setting contract splits file_fields (turnaround/blueprint/emptyPlates — must exist on disk) from descriptor_fields (map/blocking/dressing — prose passed in every prompt, must be non-empty), so a locked setting's prose isn't mistaken for missing files.
    RESUME: (a) the engine is proven end-to-end against the NoF universe — `assert-story not-every-fire-is-holy` went red→green when the arena locked; (b) open long-tail is filling NoF story stubs to `full` and migrating the remaining one-off characters + realPerson dossiers; (c) not yet scaffolded to agenticstory.wiki (the /start-new-wiki idea) — spec + engine + published page exist, the public wiki does not. No remote configured on this repo yet.

2026-07-15T21:53:45Z · 7602284 · SAVE: shipped `abu init` — a TESTED scaffolder that lays down a schema-valid universe (universe.json with a SPEC PROVENANCE block [framework + version + wiki + conformsTo, like a BOOMERANG.md], canon/{entities,relations} + stories dirs, canon README, and the load-bearing `assert.sh` gate). `--example` drops a worked character/setting/story/relation that validates GREEN but whose gate REFUSES until real assets exist (load-bearing self-demo). SPEC_VERSION/SPEC_WIKI canonical in `__init__`; SPEC.md relabeled v0.1→v0.2 (content already carried the 4 backtest findings). 6 new tests → 17 green. NEW SKILL `start-new-story-universe` (repo-local home `agenticstory/skills/`, registered globally via symlink) for one-time universe generation. **PARKED per Gary: not promoted for use until the first book (Not Every Fire Is Holy) ships end-to-end through the framework** — the book is the proof, not the spec's self-description. Still no git remote on this repo.

2026-07-18 · v0.3 + v0.4 arc (24 commits this session) · MASSIVE build. **v0.3:** self-containment invariant (SPEC §3a — a universe owns its assets in its own repo) + Skills & Identity layer (SPEC §11 — framework ships skills, a universe ships data via a `universe.json` `identity` block). Earned by making the Nation of Fire universe self-contained first: 342 canon-referenced assets consolidated out of 44 book folders + 1 external repo INTO the universe (assetRoot flipped `..`→`.`), folder renamed `universe/`→`nof-universe/`, refs swept across repo + skills + 24 book prose files; then the 11 pre-existing not-on-disk defects resolved (2 re-pointed, 9 dead keys removed) → self-containment A=0/B=0/C=0. **v0.4 (framework skill catalog):** built the WHOLE generic catalog — Phase A+B (reference-matrix standard §12 + `lock_level` engine report + register-in-identity), C (7 authoring skills: add-character/-setting/-visual-metaphor/-motif/-prop/-story/-relation + `scaffold_entity`/`add-entity` CLI), D (art: lock-references + render-readback + `lock_shot`/`lock-shot` CLI), E1 (3 generic gates: canon-resolve, casting-sweep, voice-gate). **v0.4.1:** CraftCanon record type (§13, `canon/craft/*.json`, kinds spine|genre|register-rule) + extracted NoF's 7 craft records (obedient-servant spine; expectant-biography / visualized-epistle / expectant-future-present-fable genres; gold-belongs-to-god / testimony-over-prediction / awe-not-horror register-rules) from the picture-book prose. 13 generic skills total; engine 23 tests green. AITX (Michael Daigler's universe) carries its identity+register block and is the live test bed. All parallel-safe: the `nof` plugin + `picture-book` prose are UNTOUCHED and still drive live book-making.
    RESUME: Phases E3 + F remain (parallel-safe strategy chosen by Gary — additive first, delete last). **E3** = generalize the 4 renderers (picture-book, cover, book-platform, update-book) to read `identity` + the new craft records, then PROVE one real NoF book renders a spread through the generic path with its look intact (Gary is the taste gate; this is real image-gen, wants him in the loop). **F** = retire the `nof` plugin only AFTER E3 proves. Plans on disk: `docs/superpowers/plans/2026-07-18-phase-E-migrate-nof.md` (E1 done; E2/E3 noted) + the design umbrella `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md`. NOTE: aitx + nof-universe have Gary's OWN uncommitted WIP canon (aitx antler-venue/jake-oshea/merch; nof-universe the-golden-hour-rooftop/daydream) — left untouched, not mine to commit. nof-universe B=8 is that WIP (the-golden-hour-rooftop art not yet generated), not a regression.

2026-07-18 (cont) · E3 done · Generic renderers built + proven. `render-book` / `cover` / `update-book` authored generic (read identity.register/mark/closingOrnament + craft-canon records + canon-resolve/voice-gate/render-readback; zero universe hardcodes). 16 framework skills total, engine 23 tests. RESOLUTION PROOF on `not-every-fire-is-holy` passed: `assert-story` OK (real 8-entity cast + the-arena resolve from self-contained nof-universe), all 7 craft records present, and `identity.register` added to nof-universe ("soft painterly storybook realism"). Parallel-safe throughout (the `nof` plugin + picture-book/cover/book-platform/update-book prose UNTOUCHED, still drive live book-making).
    RESUME: **Phase F (retire nof plugin) is GATED ON GARY** rendering a real NoF book through the generic `render-book` path and confirming the look holds (deleting working skills is not done on an agent proof alone). Two small steps before F: (1) Gary locks nof-universe's `register.anchor` as a style-anchor FILE on his first render-book run (currently null); (2) DEFERRED: generalize `book-platform` + the garysheng-books `nof-picture-book-reader`/NofBookReader/WispDot/NOF_THEME to read `identity` (platform-code work, its own follow-up). Plan: `docs/superpowers/plans/2026-07-18-phase-E3-generic-renderers.md` (has PROOF RESULT section).

2026-07-18 (cont) · agenticstory PLUGIN built + installed · The 16 generic skills are now an installable plugin (`agenticstory@garysheng`) in the garysheng marketplace, mirrored from `agenticstory/skills/` via `plugins/agenticstory/scripts/sync-from-source.sh` (edit skills in the framework repo, re-sync, commit the marketplace repo). Installed live; nof:* and abu:* run in parallel with no conflict. Gary is DEFERRING the nof-skill retirement (still using nof:* in another session).
    RETIREMENT RECIPE (when Gary is ready, after proving render-book on a real book): in garysheng-claude-plugins, `git rm -r plugins/nof/skills/{picture-book,cover,update-book,canon-resolve,casting-sweep,entity-register,render-readback,voice-gate}`; trim plugins/nof/.claude-plugin/plugin.json's description to just book-platform; commit + push; `/plugin marketplace update garysheng`. KEEP plugins/nof/skills/book-platform (deferred: needs the garysheng-books nof-picture-book-reader/WispDot/NOF_THEME generalized to read identity first). The 8 replaced skills all have generic abu:* equivalents (entity-register -> the add-* family).

2026-07-18T23:24 · 9c56925 · SPEC v0.5 — prompt compiler (§4.6) + entity render block (§4.1); reference impl compile_render.py, first migration jerry-man.

2026-07-23T11:40 · def48ee · **First full day of REAL use: 200 tests (from ~60), and nine structural holes that only execution found.** The judge became a subagent, not an API service (independence is a property of CONTEXT, not vendor). New NEEDS-JUDGMENT state; verdicts bind to the bytes they judged; goldens resolve against the universe root and generation REFUSES on an unresolved reference. Linter merges `extends` before checking and warns on INVARIANT-VS-QUIRK. Composer refuses scenes that name OR imply a rejected pole (negation scope, not word distance, decides it — three wrong versions before one that separates an exclusion from a request). **Biggest finding: a gate made entirely of NEGATIVES optimises toward the empty frame** — a plate passed all eight invariants as a blank rectangle, so `depicts-its-subject` is now checked two-stage and blind on both sides. **Second: nothing here constrains SELECTION.** Every safeguard constrains execution, and all three of the day's worst calls were the maker choosing an easier contract; `surface_shrink` now names it at plan time. Runner rewritten to DISCOVER test files and PARSE counts after it hid a 22-test suite behind `tail -4`.

2026-07-25T13:12:08Z · (pending commit) · NEW META-SKILL `evolve-abu` (plugin v0.6.4). Born from a Christofuturism session that hand-rolled a bespoke image `gen.py` + manual provenance instead of using `on-brand-image` + `lock-references`. The skill encodes the **Promotion Rule** ("fix the generator" principle): when you catch yourself doing framework-shaped work by hand, promote it UP into a skill/engine/spec rather than shipping the one-off; then bump version, run sync-plugin.sh, commit+push BOTH repos, /plugin update, log here, and self-update. Callable mid-session on Gary's frustration ("why are we hand-rolling this / update the templates"). Names the current top gap: **no `create-style-pack` scaffolder** (pack.json + refs/ is hand-made). synced (24 skills); NOT yet delivered (needs commit+push in agenticstory + garysheng-claude-plugins, then /plugin update).

2026-07-25T13:18:39Z · (pending) · NEW SKILL `create-style-pack` (plugin v0.6.5). Scaffolds a Style Pack (SPEC §4.7): pack.json + refs/ (self-contained), copies blessed refs in, requires a read-back gate (refuses a gateless mood board), validates 3-8 refs + content-neutral anchor first. Fills the exact gap evolve-abu named. Pairs with on-brand-image (consumer) + lock-references (locked masters). Born from Christofuturism needing "The Christofuturist" register as a portable pack.

2026-07-25T13:32:07Z · (pending) · PROVIDER ADAPTER + auto-provenance (plugin v0.6.6). Added skills/on-brand-image/scripts/generate.py: the single generate path that writes <output>.recipe.json (provider/prompt/specVersion/refs/sha256) as a SIDE EFFECT of generating, closing the gap where candidate renders had no provenance (only locks did). on-brand-image step 4 rewired to call it, never the raw model script. Same recipe shape lock-references freezes + compose emits, so every candidate is lock-ready + lint-auditable at birth. Answer to "are you saving provenance for all?": now yes, at the framework level.

2026-07-25T14:57:27Z · (pending) · NEW PRIMITIVE: Lookbook (plugin v0.7.0). SPEC §4.7.1 + skill create-lookbook (lookbook.json + refs/ + varietyRule + variety gate). The complement of a Style Pack: a curated but intentionally VARIED vocabulary (wardrobe/fashion, faces, silhouettes) for what must stay on-aesthetic yet DIFFER per instance, where motif/prop force sameness and a Style Pack is a render medium. on-brand-image gains --lookbook (sample 2-4 refs + prepend varietyRule + add variety gate); provider adapter records lookbook in the recipe. Bound to a universe via a craft-canon register-rule (first use: godly-aligned-dress -> christofuturist-fashion). Born from the Christofuturist village reading as a beige-linen commune because everyone dressed the same.

2026-07-25T15:54:27Z · (pending) · on-brand-image "Rendering operations" note (plugin v0.7.1): a render is NOT reproducible (gpt-image-2 has no seed; nano seed non-deterministic) so NEVER delete an un-locked candidate; and batch renders in the BACKGROUND (gpt-image-2 high ~2min/image, foreground 2-min caps + wide parallelism get killed mid-gen). Both learned the hard way in the Christofuturism fashion/yoke sessions.

2026-07-25 · 7c78193 · Plugin 0.7.2. Story TYPES became validated data. A story's spine and genre were free-text prose that nothing checked, so a typo, a near-duplicate (teaching-testimony vs testimony-teaching), or prose stuffed into the genre field passed silently. The SPEC (section 13) already models these as craft-canon records; lint-universe now ties every story back to that registry and warns (STORY-SPINE-UNREGISTERED / STORY-GENRE-UNREGISTERED) on any unregistered value, so "where are this universe's story types" is answerable by data. Advisory, not a hard validate error, so a universe mid-normalization still composes. Seeded the clean NoF spines (thesis, primer, testimony, blessing) and the new faithful-prophetic-realistic-fiction genre as craft records; the messy back-catalog genres now surface as normalization warnings. Also fixed a pre-existing linter crash on a golden recipe whose inputs entry is a bare path string. Engine and SPEC contract untouched, so no spec bump. 249 tests green (lint 30 to 35).

## 2026-07-25 — cover-conform convention (self-bleed default, flat bars banned)
Promoted a hand-roll: make-a-hyperagent-book was padding covers with a FLAT CREAM bar to hit the reader's 3:4 from the producible 2:3, which seams visibly against the art and looks unintentional (Gary: "very not a fan of the white left-right padding"). The framework already owned the fix (cover skill's conform_cover.py --mode pad = blurred self-bleed) and it was ignored. Changes: SPEC v0.6 -> v0.7 adds the normative cover-conform default (§ producible-vs-surface aspect): conform by blurred self-bleed, never a flat bar, never crop of load-bearing content; keyline is a per-universe opt-in, not the default. conform_cover.py docstring self-documents the default + the flat-fill ban. make-a-hyperagent-book step 5 now calls conform_cover.py --mode pad and bans flat padding. Both live books (a-book-to-live-by, the-narrow-path) re-fit and redeployed. Known remaining hand-roll to retire later: ~10 NoF book repos carry duplicated pad-cover.py copies (blurred self-bleed + gold keyline); fold into conform_cover.py and delete the copies. SPEC_VERSION -> 0.7, plugin 0.7.2 -> 0.8.0. 249 engine tests green.

## 2026-07-25 — retired the duplicated pad-cover.py (folded into conform_cover.py)
Finished the cover-conform promotion: conform_cover.py's pad mode is now a SUPERSET of the ~19 duplicated per-book pad-cover.py copies. Added --keyline <color> (draws the crisp gold frame flush to the artwork), --inset <frac> (leaves a hair of matte so a keyline never kisses the edge), and switched the self-bleed backdrop from a width-stretch to a cover-crop (truer matte colors). Default stays self-bleed, no keyline (SPEC v0.7). Reproducing NoF's look is now `--mode pad --keyline "#BF9540" --inset 0.99`. +2 cover-skill tests (self-bleed 2:3->3:4, keyline draws a frame), 251 total green. Killed the duplication at SOURCE: create-brand-os-picture-book ("ship pad-cover.py in every book") and picture-book-platform ("reuse pad-cover.py from a prior book") now call conform_cover.py instead. Deleted 15 committed pad-cover.py copies from clean NoF book repos (14 pushed); skipped 3 no-repo/untracked and 1 archived copy (do not touch other sessions' dirty state). Plugin 0.8.0 -> 0.8.1.

## 2026-07-25: the compiler guards come home (SPEC v0.8, plugin 0.9.0)
Promoted the biggest hand-roll in the framework: Nation of Fire has been rendering every book
through its OWN prompt compiler (`nof-universe/canon/scripts/compile_render.py`), which SPEC v0.5
wrongly blessed as "the reference impl". Caught while adding a per-spread register override to it
for `jerry-and-the-game-that-beat-gta` (a book that argues its thesis in its own paint: soft
painterly oil for the real world, heroic anime for the game Jerry builds, cold neon-grime for the
foil). The fork and the framework's `assemble_prompt.py` had drifted into DISJOINT feature sets, so
every guard earned on a NoF book was invisible to every other universe, and every framework
capability was invisible to the universe doing the most rendering. The fork held: anchor-style
guard, single-image guard, uncast-character refusal, registerAnchor auto. The framework held:
altLooks + dropSheets, auto-disambiguation, guardedNegatives, anchorRef. Neither could see the
other's.

All four fork guards are now NORMATIVE in SPEC 4.6 and implemented in assemble_prompt.py, plus the
new per-spread preamble override (`style`, `negatives`, `guardedNegatives`, `anchorRef`, `size`,
`allowMultiPanel`, `allowUncast`), so ONE book can carry more than one register when the change is
diegetic (a game world on a screen, a vision, a dream) without a second render-spec to drift against.
A spread that overrides nothing compiles byte-identically to v0.7; a spread can never shed the
universe's own rejectedPoles. 4.6's "reference impl" now points at the framework, and a
universe-local compiler is named a fork to migrate rather than a pattern to copy. compose-spread's
SKILL.md documents all four guards and carries an explicit "never fork this" section.

Found while testing: `unittest.main()` sat in the MIDDLE of
`skills/compose-spread/tests/test_assemble_prompt.py`, so TestAltLookDropSheets and
TestAltLookRenderBlock had never run once, while the suite reported ALL GREEN. Same silent-omission
failure run-tests.sh was hardened against, one level down. Moved to the true end with a comment
saying why. 251 -> 270 tests green (14 new guard tests, 5 revived).

The NoF fork is FROZEN, not yet deleted: 17 books' render-specs use its schema and parallel sessions
are rendering through it right now. It carries a DEPRECATED header naming the migration (a schema
adapter from `preamble`/`characters[].pose`/`extras[]` to compose-spread's `cast[].look`/`plate`),
which needs a quiet window with no sibling renders in flight. SPEC_VERSION 0.7 -> 0.8, plugin
0.8.1 -> 0.9.0.

## 2026-07-25: a setting must be able to prove its own size (SPEC v0.9, plugin 0.10.0)
Gary, looking at a rendered spread: "that fireplace room is supposed to be much bigger than it is
right now." The room was `christofuturist-home.hearthRotunda`, and it had rendered small and cramped
through a whole 25-spread book. Root cause is a framework rule with an unpriced cost: SPEC §12 makes
setting `emptyPlates` PEOPLE-FREE, for the good reason that a reference must never bake a character's
face into a room. But a figure-free interior carries no unit of comparison, so the model picks a
size, every render inherits that guess, and nobody can catch it because the plate does not depict the
dimension being judged. The same blind spot hid a free-standing central firepit under a SUSPENDED
CONICAL FLUE that nothing was holding up: no plate ever had to show how the thing stood.

Worse, this was already half-diagnosed and then walked past. make-a-nof-book has carried the line "a
visual-metaphor plate must carry its own scale cue, because a figure-free plate cannot prove scale by
comparison" since the-greatest-storybook-writer. It was written as one book's gotcha instead of being
promoted, so the next setting shipped with the same hole. Second occurrence is the trigger.

Promoted: SPEC §12 setting matrix gains `scalePlate` (file) and `scale` (descriptor). A scalePlate is
the SAME room with ANONYMOUS scale figures (small, distant, turned away, faces unreadable, never a
canon character, never the subject), which satisfies the identity rule and makes size checkable. It
is a SEPARATE file from emptyPlates, never a replacement: renders still cast an empty plate. The
`scale` descriptor states the size in human measurements and is passed in every prompt like
`dressing`, because prose survives a re-render and a plate does not. lint-universe warns
SETTING-NO-SCALE-PLATE / SETTING-NO-SCALE-DESCRIPTOR, both advisory so a setting with no scale plate
still locks and still renders. add-setting now ASKS how big the place is during the interview, and
asks how each structural feature is actually held up or vented, which is the question that would have
caught the floating cone. The scaffolder emits both fields. SPEC_VERSION 0.8 -> 0.9, plugin 0.9.0 ->
0.10.0. 270 -> 276 tests green.

Field note on the fix itself: the first instinct was to REPLACE the room (wall-set firebox, no
hood). Gary redirected to rescuing it with scale plates instead, and he was right twice over. A
suspended hood over a central hearth is genuinely buildable at great-hall scale and only read as
unbuildable because the room read small. And `kingdom-property` had already SHIPPED against that
geometry, so replacing it would have silently desynced a live book from every later one. Check who
already depends on a setting before redesigning it.

2026-07-25 · plugin v0.11.0 · Shipped the agenticstory-steward AGENT (agents/agenticstory-steward.md): a framework-aware subagent whose job is to reach for the right verb instead of hand-rolling and to FLAG (never silently work around) framework gaps, escalating them to evolve-abu. First agent in the plugin; sync-plugin.sh now mirrors agents/ down the same source-marketplace-remote-cache chain as skills. Delivered (both repos pushed); needs /plugin update.

2026-07-25 · engine fix · add-entity scaffolder (authoring.py + model.py SETTING_CONTRACT_FIELDS) now emits scalePlate + scale for settings, matching SPEC v0.9 (scaffold.py already had them; the CLI path was behind). Every add-entity setting was born without the size contract. Caught by formalizing the christofuturism environments as settings. Tests green.

2026-07-25 · plugin v0.12.0 · Shipped universe-doctor: a scorecard skill that grades a universe on a fixed completeness+quality rubric (identity, entity matrices, setting size-contracts v0.9, provenance, craft-canon, stories, self-containment), returns a letter grade + per-dimension scores + an impact-sorted punch-list naming the verb that closes each gap, then works the list. The rubric is the framework definition of a done, good universe. Self-contained grade.py + 5 tests (281 total). First live grade: christofuturism scored D (69/100). Delivered; needs /plugin update.

2026-07-25 · plugin v0.12.3 · compose-spread's uncast-character guard no longer treats DESIGNED TEXT as a person in frame. In-art text is first-class (a cover title, signage, a plaque) and the convention is that the exact string is QUOTED in the scene, so quoted spans are now stripped before name matching. Earned on nation-of-fire/the-higher-law, where a book cover reading 'APOSTLE DELMAR COWARD JR.' AND 'GARY SHENG' demanded two characters be cast who were not in the scene, and the tempting move was the allowUncast escape hatch. Two regression tests (284 total): quoted lettering passes, and an unquoted body standing next to designed text is still caught. Ported the same day rather than left to drift, which is the whole lesson the deprecated NoF fork header records: guards earned in one implementation stayed invisible to the other until their feature sets went disjoint. Delivered; needs /plugin update.

2026-07-25 · meta · evolve-abu corrected itself (step 8). It claimed the delivery chain ran through a git remote and that pushing both repos made a change live; sync-plugin.sh reports the marketplace is a DIRECTORY source, so pushing is hygiene and the installed cache only refreshes on a VERSION CHANGE plus /plugin update. It also carried a stale hardcoded version (0.6.3) and did not warn that editing the marketplace COPY is editing the artifact, which the next sync overwrites from source. All three fixed.

2026-07-25 · plugin v0.13.0 · Promoted three capabilities out of the Nation of Fire fork, measured rather than guessed: cast[].bake (a per-entry prose override that REPLACES the derived block, load-bearing for a multi-state visual-metaphor whose derived block otherwise describes every state and makes the model draw all of them at once), plate selection for ANY non-character kind (a motif or prop could previously only ever be passed its requiredForRender default, so a book that is sometimes open and sometimes shut had no way to say which), and settingRule (book-level, per-spread overridable, extra prose appended to one entity's block so the same room can read colder in a cancellation beat without editing canon). 181, 100 and 44 uses respectively across 31+ nation-of-fire books, all previously expressible only in the fork. Five tests, 289 total, green. This does NOT retire the fork: a new survey tool measured 61 fork specs vs 17 already on the compose-spread schema, and the fork bucket still carries at least six more dialect constructs (spread.refs 468 uses, spread.caption 137, spread.era 50, spread.cast+location 46, top-level story 41, top-level refs 21). The fork is one family of dialects, not one schema. Delivered; needs /plugin update.

- 2026-07-30: closed two gate holes found by the knowledge-shall-increase book run. `assert-story` skipped any featured entity whose `requiredForRender` was empty, so a story whose entire new cast was scaffolded and not yet shot returned OK; it now refuses an entity that declares reference slots and has filled none, and refuses a setting or visual-metaphor still marked `status: unlocked`. An entity with no slots at all (a doctrine, a prose motif) still passes. `Entity.validate` did not look at `structured.render` at all, so `render.poses` authored as bare strings passed validation and then crashed the spread assembler with an AttributeError mid-batch; poses are now checked for object shape, string `bake`, list `sheets`, and that every sheet a pose names exists. Six regression tests, engine 167 green, suite 523 green.
- 2026-07-25 — engine: lock-shot routes by kind. Settings and visual-metaphors are matrixed via their `contract`, not `structured.sheets`, but lock_shot wrote every kind into sheets, so a setting could be locked shot by shot, print success each time, and still be refused by assert_story with contract.turnaround null and nothing reporting it. Found live on encounter-school in nation-of-fire. Adds the scale-plate alias, refuses to duplicate a plate on re-lock, and promotes status to locked only when the whole contract including its prose descriptors is satisfied. Ten regression tests as unittest TestCases, because run-tests.sh discovers with unittest and pytest-shaped functions would never have run. Engine 42 to 52. Plugin 0.13.1.

- 2026-07-25 — engine: lock-shot writes a setting to BOTH `contract` and `structured.sheets`. The 0.13.1 fix over-corrected: contract-only passed assert-story and then crashed compile_render.py with KeyError 'structured', because the gate reads the contract checklist while the RENDERER selects a plate by sheet key per spread. A setting needs both or it is half-usable. Caught live rendering It Was Not Broken. Engine 52 to 53. Plugin 0.13.2.

- 2026-07-25 — skills: add-story gains a SCALE section and a DECLARED FUTURE GETS REAL WEIGHT section; render-book gains a proportion check. Caught by Gary mid-render on It Was Not Broken: "feel like you have been artificially constraining the number of spreads... prophetic fiction is often what I am trying to do, and if you do not show the future, I do not know what we are doing here." Nothing in the framework said a word about story length, so beat sheets were landing at fifteen to twenty because that is where drafting fatigue sits, and the declared future was getting a single closing beat. A story can obey every word of an anti-hedging amendment and still gut it by proportion, spending thirty beats on the problem and one on the promise. add-story now refuses a silent default length, counts movements, weighs diagnosis against answer, and budgets the declared future as an act (a quarter to a third of beats, shown at several scales, present tense and inhabited). Plugin 0.14.0.

- 2026-07-25 — skills: compose-spread gains READING MATERIAL FACES THE READER, NEVER THE CAMERA. Image models square a page up to the lens so the viewer can read it, which is what stock illustration does and what makes an otherwise good spread read as staged. A book belongs to the character holding it: top edge away from them, foreshortened or partly upside down from the camera, and if the camera cannot read it that is correct. Bake it as a book-level negative, because it recurs on every desk, Bible, report card and ledger spread and is invisible in a thumbnail. Caught by Gary on it-was-not-broken spread 36: "you continuously flip the book". Plugin 0.14.1.

- 2026-07-25 — lint-universe gains CASTABILITY checks (CAST-UNRENDERABLE, CAST-NO-POSES, CAST-POSE-SHAPE, CAST-POSE-SHEET-MISSING, CAST-POSE-SHEET-NULL). An entity can be locked, art-approved, pass validate AND pass assert-story and still be impossible to render, because compile_render reads structured.render.always and .poses while every gate reads sheets and files. It surfaced only as a hard KeyError at cast time, after the story was written and the spec was built. Repaired by hand three times before this (the-arena, then russ-vibes-apostle and nas, then the-chairman and chief-of-toil and the-battle-axe-girls). First run of the new rule over nation-of-fire found 101. Six tests, lint suite 41 to 47. Plugin 0.14.2.

- 2026-07-25 — lint-universe castability exemption corrected: an entity with `sheets: {}` has no art and owes no poses, same as one with no sheets key at all. Checking only for None flagged a doctrine-only group that has no art and wants none. Found while driving the nation-of-fire repair from 101 uncastable entities to 0; the last one standing was a bug in the rule, not in the canon. Lint suite 47 to 48. Plugin 0.14.3.

- 2026-07-25 — lint-universe gains SHEET-DUPLICATE-ALIAS and INVARIANT-IS-STATUS. Two sheet keys pointing at one file is not free: when requiredForRender names both, the compiler passes the SAME image twice, so a "face macro" contributes nothing while the entity looks better-referenced than it is (error when both are required, warning when one is a dead alias). And `invariants` is the array read-back checks are generated FROM, so a workflow flag parked there (design-pending-tier1, cast-approval-pending-gary) becomes a check nobody can run against an image; status belongs in `status` or `authority`. First run over nation-of-fire: 5 errors, 8 dead aliases, 23 status-as-invariant. Five errors fixed by removing the fake alias rather than faking a crop. Lint suite 48 to 53. Plugin 0.15.0.

- 2026-07-25 — provenance is now ENFORCED GOING FORWARD, with the pre-policy library accepted as historical (Gary decision). GOLDEN-NO-RECIPE was a warning fired 457 times, which buried every real finding; it is now an ERROR, exempted by an explicit grandfather FILE (canon/provenance-grandfathered.json) rather than a date, so the debt is a reviewable artifact that can only shrink. A golden missing a recipe and not on the list was locked after the policy and skipped the tool. One PROVENANCE-DEBT summary reports the outstanding count and any stale entries. nation-of-fire grandfathered 444. ALSO: documented a cliff in lint() — the NO-PROJECTIONS branch RETURNS, so any check written below it never runs for a universe with no projections, which is nation-of-fire, the universe doing the most rendering. A summary added below it was swallowed exactly that way. Lint suite 53 to 56. Plugin 0.16.0.

- 2026-07-25 — lint-universe gains AUTHORITY-UNFILLED, and INVARIANT-IS-STATUS learns that a PROHIBITION is a real visual rule. The scaffolder writes lockedBy "TODO-you" and nothing ever forces it to be filled, so an entity can carry locked art, frozen provenance and a full pose set while its record of WHO approved it is a placeholder; one such entity was created and locked in the same session that found this. First run over nation-of-fire: 5 placeholders plus 55 entities with no approver recorded at all, 60 total. The prohibition carve-out fixes two false positives caught on the first real run ("no-barcode-no-publisher-mark-no-subtitle-no-review-quote" is a checkable fact about an image, not workflow state). Lint suite 56 to 59. Plugin 0.16.1.

- 2026-07-25 — lock-shot now stamps `authority.lockedOn` and warns loudly when `lockedBy` is still the scaffolder placeholder. Locking IS the approval act, so it is the only moment the approver is guaranteed knowable, and the placeholder had been surviving all the way into locked art. Caught twice in one session: once across 60 nation-of-fire entities, and then again an hour later on a motif created and locked by the same session that had just fixed the first case. The lint rule catches it eventually; this catches it at the moment of approval. Engine 53 to 56. Plugin 0.16.2.

- 2026-07-26 — new skill book-doctor: the Doctor Pattern applied to one RENDERED book, on local disk, before delivery. The gap it closes is a hole in the gate chain rather than a missing convenience. assert-story gates BEFORE a render, when there is no output to measure, and lint-universe is static; nothing graded the OUTPUT. So a book shipped with its closing plate rendered at landscape interior aspect, when the reader composes the closing plate as a single-page BACK COVER at 3:4 and therefore crops it. "The closing plate is the last numbered spread file" describes where it lives, not what shape it is, and every pre-render gate passed. Checks: every declared spread exists, endcaps portrait and interiors landscape, every asset carries its provenance recipe, no asset generated from another spread render, and optionally every cast entity registered and locked. DELIVERY-AGNOSTIC ON PURPOSE (no bucket, no CDN, no network, no SDK): a delivery platform's own doctor is coupled to its storage and its frozen-tested aspect helper, and forking that logic here would turn a tested check into an untested copy, which is a bug those platforms have already had once. The two do not overlap, and checks 4 and 5 are ones a delivery probe structurally CANNOT do, because recipes are build artifacts that never ship. Its own suite caught a bug in it during authoring: the self-reference scan keyed off a role name beginning "spread-", which skipped the closing plate, the likeliest offender of all since the legacy migration recipe says to copy the final spread as the plate. First run on a real book reproduced the shipped defect and found a second one nobody had: conform_cover.py writes no recipe, so the provenance chain breaks at the conform step. That is the next promotion candidate. Skill suite 321 to 332. Plugin 0.16.3.

- 2026-07-26 — lint-universe: GOLDEN-INPUT-GONE now says that a rename is NOT a reason to rewrite provenance (0bda817, missed by the previous save). The message reported that an input "no longer resolves" and stopped there, which leaves the reader with one tempting fix: edit the recipe to match the new path. That falsifies the approval record, because the recipe is evidence of what was actually approved and not a pointer to be kept green. Nation of Fire's own canon already said historical recipes keep their pre-rename paths for exactly this reason, so the rule was quietly advising the operator to launder history the canon had already forbidden. A lint rule that recommends the wrong repair is worse than no rule, since it arrives with the authority of a gate.

---

2026-07-26 · SPEC v0.10 · a character must be able to prove its own scale, and its future.

Trigger: authoring a Nation of Fire story centered on Beef Jones whose final act is set in a declared
future (2028, 2030: lean, jacked, still bald), with two leads who differ in height by several inches.
Neither fact had anywhere to live in canon, and the hand-rolled alternative was to retype both into
every spread's scene text, where nothing checks them and every book restates them differently.

Both gaps are the v0.9 setting lesson generalized: A DIMENSION NOTHING DEPICTS CANNOT BE JUDGED.

Promoted (1): SPEC §12 character matrix gains `structured.scale` — `height` in human terms plus
`relativeTo`, a map of entity ids to a phrase. Every entity in the matrix is described ALONE, so two
characters in one frame come out the same height or reversed and it stays invisible until someone who
knows them says so. compose-spread emits a RELATIVE SCALE line ONLY when two or more in-frame
characters declare a relation to each other, so solo spreads are unchanged. lint-universe warns
CHARACTER-SCALE-ONE-SIDED (a relation its counterpart does not mirror; two half-records drift apart
and then contradict) and CHARACTER-SCALE-UNKNOWN-TARGET.

Promoted (2): `structured.altLooks` is DOCUMENTED for the first time. It has been load-bearing in the
compiler since the jerry-man age eras and absent from the spec the whole time, so anyone reading the
spec to author a look would have hand-rolled one. Plus `keepSheets` / `keepPhotos` for declared-future
looks, which is a real bug and not only a doc gap: an ordinary alt look changes the FACE and carries
its own anchorPhoto, which is why base face sheets are auto-dropped. A prophetic look inverts every
part of that — the face is CONTINUOUS, the BODY changes, and the future has no photograph — so it
reached the model with body sheets only, which are the exact silhouette it supersedes, and the render
came back a stranger with the right build. compose-spread now REFUSES a look with no face source at
compile time (costs nothing) and lint-universe warns LOOK-NO-IDENTITY-ANCHOR a step earlier.
dropSheets stays authoritative over keepSheets so the two fields can never fight to a coin flip.

Advisory and back-compatible: a character with no `scale` still locks and still renders, and every
existing alt look carries an anchorPhoto so none of them trip the new refusal.

Engine SPEC_VERSION 0.9 -> 0.10; plugin 0.16.3 -> 0.17.0. 12 new tests (5 declared-future, 3 relative
scale in compose-spread; 7 in lint-universe). Full suite 347 green. add-character gained steps 4a/4b;
compose-spread SKILL.md points at both.

2026-07-26 · engine · `lock-shot --look <key>` writes an alt-look's art into
`structured.altLooks[key].sheets` instead of the default matrix. Caught the same day v0.10 shipped,
while giving beef-jones' 2028/2030 eras their actual plates: the spec had gained the LOOK primitive
and no verb to give it ART, so the only way to register an era plate was to hand-edit the entity
JSON, which is the hand-rolling this engine exists to remove. It never touches `requiredForRender`
(that is the DEFAULT look's gate; an era plate must not satisfy it, or a character with no
present-day body sheet reads as gate-real off a future one), and it REFUSES an unknown look key
rather than creating it, because a typo would otherwise mint a look nothing selects and no read-back
ever checks. Provenance freezes exactly as on the default path. 4 tests; suite 351 green. Plugin
0.17.0 -> 0.17.1. lock-references SKILL.md gains the era-lock section, including the rule that an
era plate is generated from the FACE sheets and never from the superseded `forward-fullbody`.

2026-07-26 · tooling fix · sync-plugin.sh compared against the WRONG cache directory. The check did
`ls -d ~/.claude/plugins/cache/garysheng/agenticstory/*/skills | head -1`, and those directories sort
ALPHABETICALLY, so 0.11.0 beat 0.17.1. It compared source against a long-dead cache and reported
INSTALLED PLUGIN IS STALE forever, no matter how many times the plugin was genuinely updated. That
false negative sent a session telling the operator to run /plugin update three separate times when
the plugin was already current, until he pushed back. Now it reads the version out of the plugin
manifest and checks THAT directory, falling back to the most recently MODIFIED cache (ls -dt) and
saying so out loud when the declared version has no cache dir yet. Verified: reports "installed
plugin matches source" against 0.17.1. A staleness check that cannot be trusted is worse than none,
because it trains everyone to ignore it.

## 2026-07-26 — chain_matrix per-shot sizes, a bounded conditioning window, and 14 tests that never ran

Two gaps found live while locking `shelby-mullen` (a 9-shot character matrix) in
the Nation of Fire universe, both promoted into the framework rather than worked
around in the universe.

**Per-shot sizes.** `chain_matrix.py` applied one `--size` to every shot, even
though `prompts.md` headings already declare `(WxH)` per shot. A reference matrix
legitimately mixes aspects: full-bodies and profiles want portrait, multi-panel
sheets (expressions, era rows) want landscape. The mismatch letterboxed the
expressions sheet into a portrait canvas with dead bands over most of the frame.
The sizes were always written down; the chain simply was not reading them. It now
parses them from the heading, and `--size` is the documented fallback for a shot
that declares none.

**A bounded conditioning window.** The chain passed every accepted golden forever,
so each step uploaded a larger request than the last and the TAIL of a big matrix
died on `openai.APITimeoutError`. That is the worst place to fail, because the last
shots are the most expensive to redo. Identity is carried by the blessed seed plus
the few most recent shots, not by the back view, so conditioning is now
seed-plus-most-recent with `--max-conditioning` (default 4, `0` restores the old
unbounded behaviour). `--print-plan` shows the real window rather than advertising
conditioning the run will not perform.

**14 tests that never ran.** Adding coverage surfaced a latent bug: three test
files had their `if __name__ == "__main__"` block sitting MID-FILE, so
`run-tests.sh`, which executes each file directly, only ever ran the classes above
it. `test_chain_matrix.py` was reporting 9 of its 19 tests and `test_cover_scripts.py`
28 of 32; `test_engine.py` was masked only because the engine runs via `discover`.
Blocks moved to the end of all three, and the whole tree swept for the pattern.
This is exactly the failure `run-tests.sh` was already shaped against, one level
down: it discovers test FILES faithfully and could still not see inside them.

Suite: 352 -> 373 tests, all green (7 new, 14 recovered). Plugin 0.17.1 -> 0.17.2.

## 2026-07-26 — `lock-references` renamed to `shoot-references`; prompts.md scaffolding; per-entity render gate (spec v0.11, plugin 0.18.0)

Three promotions out of one Nation of Fire session (the Sol Rhodes story build).

1. **`lock-references` -> `shoot-references`.** The old name described the third of three
   steps. The skill generates art, reads it back, then locks; locking is the bookkeeping, not
   the work, and an agent reaching for "make the art for this character" did not find it. The
   engine already calls the unit a shot (`lock-shot`), so the verb for making shots is shoot.
   All 17 live cross-references, the steward agent, `on-brand-image/scripts/generate.py`,
   `universe-doctor/scripts/grade.py` and `engine/authoring.py` were updated. Historical
   mentions in shipped universe files and in `docs/superpowers/plans/` were left alone on
   purpose: they are a record of what was done, not instructions.

2. **`add-entity` now emits `reference/<id>/prompts.md`.** Every `add-*` skill promised
   "ready-to-run generation prompts" and `shoot-references` reads that file as its input, but
   nothing ever wrote it, so the step between scaffolding and shooting was hand-rolled in every
   universe (ten times in one sitting). The engine emits the STRUCTURE (register-anchor
   preamble, one section per matrix slot, the required set named up front, the output path) and
   leaves the prose to the author, because the engine knows which shots exist and cannot know
   what they depict. Never clobbers an existing prompts.md.

3. **`structured.requiredForRenderOnLock` is first-class (SPEC v0.11).** A per-entity override
   of the kind's matrix minimum, for a character whose `face-3q` carries a signature the front
   view cannot show. Four entities in nation-of-fire had already invented this exact field
   before anything read it, which is the tell: reinvented independently means it is a framework
   gap, not a universe quirk. Worse, `lock_shot` recomputed the gate from the kind default and
   clobbered the stricter set on the next lock. Now honoured in `lock_shot` and
   `required_sheet_keys`; it may only ADD to the kind minimum, since a kind's minimum is what
   makes "locked" mean something.

Engine 61 -> 69 tests. Caught while doing this: eight tests written pytest-style in
`engine/tests/` were never collected, because `run-tests.sh` drives the engine with
`unittest discover`. The file's own docstring warns about that trap. Converted to TestCases,
which is when they first actually ran.

## 2026-07-26 — update-book learns the redelivery trap and the reader-confusion rule

Both earned live, redelivering a caption-only fix to a published 36-spread book.

**The redelivery trap, and it destroys paid work.** A publish step that uploads to
remote storage prunes the local copies afterwards, so an already-shipped book has no
local interiors and no local audio. Regenerating one narration clip and re-running
publish therefore fails the art check, reports that it shipped NOTHING, and prunes
anyway, deleting the clip that was just paid for. The rule is now in the skill: for
ANY redelivery of a published book, re-stage the full art set FIRST, then regenerate
the touched narration, then publish. Staging is free and deterministic; the clip is
not. Noted there too that a publish run which ships nothing should prune nothing,
which is a bug worth fixing at the publish source.

**A reader who does not understand a beat is a defect in the beat**, including when
the reader is the author. Recorded on the revise branch, with the fix pattern that
worked: when the confusion lands on the beat carrying the property's thesis, give the
reader the mechanism instead of withholding it for a later payoff, and check whether
the ART is already doing its job, because a caption-only fix is common and far cheaper
than a re-render.

Plugin 0.17.2 -> 0.17.3.

## 2026-07-26 — sync-plugin.sh: scope the delivery gate, and guard the source branch

Two failures of the same kind, both found by the gate crying wolf during a long
multi-session day.

**The delivery gate was scoped to the whole marketplace repo.** It ran
`git status --porcelain` at the repo ROOT, which holds every plugin Gary owns, so any
sibling plugin being scaffolded or any other chat's edit reported this plugin as STALE
even when it was fully delivered. The honest answer became "STALE, but not mine", and a
gate whose failure you routinely explain away has stopped being a gate. It now tests
only `plugins/<this-plugin>` for dirt and for unpushed commits, and reports work
elsewhere in the repo as a NOTE that never blocks and is explicitly not to be committed
on another session's behalf.

**sync copies the WORKING TREE, so it ships whatever branch happens to be checked out.**
A sibling chat had a feature branch checked out in the source repo, and a routine sync
dragged its unmerged `render_spread.py` into the marketplace, where it then held the
delivery gate hostage. sync now warns loudly when the source is not on master or main,
naming the branch and saying what is about to be published. The fix when it fires is to
land the change on master through a worktree, which leaves the other session intact.

Related version discipline, learned the same hour: READ THE MANIFEST IMMEDIATELY BEFORE
BUMPING. A bump made from a version remembered earlier in the session set 0.17.3 while a
sibling had already shipped 0.18.0, which is a downgrade the installed cache silently
ignores. A long session is exactly when a sibling ships a release.

Plugin 0.18.1 -> 0.18.2.

## 2026-07-26 · spec v0.12 · text is gated, not banned

`on-brand-image` carried a blanket "ABSOLUTELY NO text, no letters, no numbers" and every
hyperagentic-age pack gated "no text or lettering". Gary caught the consequence: wiki hero strips
stopped carrying the title bars, panel captions, and footer bars that the older heroes had, and books
could not show a book cover that says what it says.

The ban was the wrong shape. It conflated three different things:

- **Duplicated** text (a spread burning in the caption the page already lays out) is the real defect,
  and it is about duplication rather than about glyphs.
- **Diegetic** text (a cover in frame, a sign, a jar label) belongs in the world and improves the image.
- **Furniture** (title bar, captions, footer bar) is what makes an explanatory hero readable.

SPEC §4.7 gains `textPolicy` (`none` | `diegetic` | `furniture`). Permitted text is declared by the
caller and verified character-exact in read-back; a misspelling or an invented string is a DEFECT that
re-rolls the whole image. Packs written before v0.12 read as `diegetic`. This is the posture the
framework already used on a cover title, applied where it was missing.

Cartridge: `anthropic-plate` is `none`, `warm-editorial` and `warm-editorial-neutral` are `diegetic`
(so book interiors gain natural text and keep no caption chrome), and a new self-contained
`warm-editorial-titled` is `furniture` for wiki heroes. `supersuit-org-comic` now routes heroes to the
titled pack and specifies the three furniture slots.

Models do still misspell. That is an argument for checking, not for forbidding.

## 2026-07-27 — `land-work` + `abu land`: branches go home by themselves (plugin v0.20.0)

Promoted the one manual step that survived every single pipeline run. A book run ends in its own
branch and worktree, because a repo with several concurrent agent sessions cannot be shared any
other way, and then the run reported "the canon branch is committed but PARKED, master is checked
out in another worktree". Gary's answer was identical every time: "follow your judgment, I don't
have an opinion about the merging, you know how to do it well." That is not a decision worth a
round trip, it is an unfinished job handed back, and it compounded: nation-of-fire had ELEVEN
worktrees and a stack of unmerged branches, which is the same defect eleven times.

Parking felt safe because the hazard underneath it is real. The target branch is usually checked
out in a SIBLING worktree owned by a live session, and moving a branch under a live worktree
corrupts that session (their files stay on disk, HEAD now lists yours, their index reports YOUR
files as deletions, and their next bare commit reverts your work). So the new engine module
classifies the target instead of guessing: FREE (checked out nowhere) merges inside a throwaway
worktree; IDLE (held by a clean worktree) merges in that worktree so ref and files move together;
BUSY (dirty, or mid merge/rebase/cherry-pick) is never touched; CONFLICT aborts and changes
nothing. It never uses `git update-ref` or `git branch -f`, the two classic ways to do the damage.

The part that makes it self-healing is the QUEUE. A blocked merge records its intent under
`.git/`, and every later `land` drains the queue first, so the next run finishes what this one
could not. No daemon, no cron, no human. A queued merge is reported as a success, not a decision.

It is repo-generic on purpose: `abu land <repo>` knows nothing about universes, so it
works on a canon repo, a platform repo or any other git repo. `--prune-stale` also removes
worktrees whose branch is already fully merged, which is the other half of the mess.

Two bugs the real run surfaced and both are fixed and tested. `git branch -d` measures "fully
merged" against HEAD rather than against the branch just merged into, so it refused to delete
branches that were provably safe whenever the main checkout sat on an unrelated third branch;
containment is now verified against the real target. And `stale_worktrees` used the merge-shaped
cleanliness check (which ignores untracked files) while `git worktree remove` refuses on them, so
it advertised 5 removable worktrees when the true answer was 3; pruning now asks the stricter
question, because pruning deletes a directory and an untracked file there is unrecoverable work.

19 tests, built against REAL temp git repos rather than mocks, since every hazard here is a real
git behaviour a mock would happily assert wrongly. The load-bearing one proves a dirty sibling
worktree is left byte-for-byte alone. Suite: 416 green.

Wired at the two ends of a run (drain at the start, land at the end, once per repo touched) into
make-a-nof-book and make-a-hyperagent-book, and stated as a general rule in the global AGENTS.md
so it applies to any repo, not just a universe.

2026-07-27 · THREE PROMOTIONS out of a book revision, plus a duplicated-work lesson worth more than any of them. (1) `update-book` gains the revision-is-a-rebuild sweep: re-run the casting sweep because canon moved since the book shipped, grep `canon/properties/*.json` before adopting a SCRIPTURE (the obvious verse for new material is often a shipped sibling's entire spine, and reusing it collapses two arguments into one), diff the book's render-spec preamble against a recent sibling's because an older spec is missing guards added since, and record in `aimDiscipline` when new beats EXTEND rather than reverse an earlier beat or the next canon check reads it as drift and "fixes" it back. (2) `universe-doctor` now flags FULL stories with no `canon/properties/<id>.json` record, which makes a shipped book invisible to every future casting sweep; the first run against nation-of-fire found FIFTY-EIGHT, including that universe's own reference book. 3 new tests. (3) `add-character` gains the rule that a public figure's PRIVATE FAMILY does not inherit their public-figure status: naming them is fine, rendering a verified likeness beside invented family faces is not, because the real face authenticates the invented ones and the frame becomes a documentary claim about how private people look. It holds even where a universe has abolished every approval gate, because it is about not asserting a falsehood, which no consent rule reaches.
    THE LESSON: this session also built a whole second `land` implementation, ~300 lines and 16 tests, because `abu land` failed with `invalid choice`. It failed because the MAIN CHECKOUT was parked on a branch from the previous day; `land` had shipped to master at 12:14 the same day and was working the entire time. A missing CLI verb is exactly the symptom a stale checkout produces, and the check costs one command. **Before concluding the framework lacks something, `git log --oneline master -5` and `git status` in the framework repo.** The duplicate was discarded and master's implementation kept; only the three promotions above survive from that work.

2026-07-28 · CANON RESOLUTION BECOMES A GATE INSTEAD OF A DOCUMENT (plugin 0.26.0). `canon-resolve` was always a SKILL: prose instructing whoever renders to look up an entity's locked sheets and pass them as `--ref`. That is a memory test, not a gate, and gary-sheng-art failed it seven consecutive batches in one night: a `jesus@spirit` render was given a hand-picked subset of the entity's plates, the canonical face never reached the model, and every batch drifted straight back to the base model's pale-European bias. Nothing refused those renders because nothing was checking. THE FIX, in three parts. (1) The engine now READS `altLooks`, which SPEC v0.10 declared and no code had ever consumed: `Entity.look_sheets(look)` composes a look (base required sheets, minus identity sheets, plus `keepSheets`, minus `dropSheets`, overlaid with the look's own sheets) and `Entity.look_invariants(look)` applies `supersedes` so a look can retire a base rule it contradicts without deleting it for every other render. 8 tests, and the guard test was verified to FAIL when the bug is reintroduced. (2) `on-brand-image/scripts/generate.py` gains `--entity <universe>:<id>[@look]`, repeatable: it resolves through the engine, prepends the sheets AHEAD of the style pack anchor (a pack pulls hard toward its own faces and must not outrank the subject's own plates), bakes the live invariants and `prose.rules` into the prompt, records what it resolved in the recipe, and REFUSES on a missing plate or unknown look. (3) `canon-resolve` and `on-brand-image` now say to use the flag and to reserve `--ref` for things that are not canon entities.
    TWO ENGINE BUGS out of the same night, both found only by hand-fixing their symptoms. `lock_shot` RECOMPUTES `requiredForRender` from the kind matrix on every call, so a required shot hand-written into that array is deleted by the next lock; the escape hatch `requiredForRenderOnLock` validated names against `matrix['shots']`, the COMPLETENESS list, so naming any plate outside it raised. The framework therefore could not express "this character needs one more plate than its peers", and the obvious workaround silently reverted. Kinds now carry an `optional` list: names the framework permits in `requiredForRenderOnLock` that do not count toward completeness. The first attempt put the plate in `shots` and the tests correctly killed it, because that demoted every already-locked character in every universe to `partial`. And `lock_shot` stored whatever path it was handed, so a CLI call planted an ABSOLUTE path among relative siblings and broke self-containment (SPEC 3a); it now normalises against the root and refuses a path outside it.
    THE GENERAL LESSON: a rule that lives only in a SKILL is advisory, and advice is followed until the moment it matters. `character.face-neutral-color` exists because a face sheet in any non-photographic medium (blue ballpoint engraving, ink study, graphite) carries architecture and NO complexion, so passing one fixes the bone structure and hands colouring to the style pack. Nobody opened the plates for seven batches. If a constraint can be forgotten, it is not a constraint yet.

2026-07-28 · §4.8 PROJECTION GETS AN IMPLEMENTATION, AND A PRIMITIVE GETS UN-ADDED. A layered parallax scene was hand-rolled as `scenes/<id>/scene.json` with a `"kind"` field — a folder wearing the framework's clothes. Asked whether it conformed, the honest answer was no, so it was promoted into SPEC as §4.12 "Layered Scene": a new primitive, a new engine class, new validation, tests green. Gary then asked *"isn't this just a projection?"* and it was. The argument for the primitive had been that the SPEED ORDERING between planes was novel content no existing primitive carried — but §4.8 defines a **crossSlot invariant** as one "only checkable across several" slots, which is exactly that. A primitive had been invented to hold a constraint the framework already had a word for. §4.12 and the engine class were reverted (`git checkout`, SPEC back to 0.13) and the thing was rebuilt as `ProjectionType parallax-scene@1.0.0` + `ProjectionInstance fellowship-terrace`.
    WHAT WAS ACTUALLY MISSING: §4.8 had been specified since v0.11 and **never implemented** — no engine had ever loaded a projection, which is why a bespoke primitive felt necessary in the first place. `ProjectionType` / `ProjectionInstance` (Gary's naming; `Projection` / `Composition` told you nothing about which was which) now load from `projections/*/projection.json` and `instances/*/instance.json`, and the store checks the three things an instance cannot check about itself: the pinned version resolves, every filled slot is declared, every required KIND is bound. `requires` naming an `id` is rejected outright — that is the one mechanism making a projection distributable, and welding it to one universe silently costs nothing until someone tries to ship it. 26 new tests, 120 total.
    COMPUTED INVARIANTS BECOME DATA. A generic engine cannot run a check it knows only by NAME, so a `computed` invariant now carries an evaluable `rule` and the store evaluates it: `monotonic` (a field ordered by another field), `count` (how many entries match a predicate), `extreme` (a matching entry sits at an end). Three ops covered every case so far, and each is about a RELATIONSHIP between slot entries, which is what a crossSlot invariant IS. An invariant marked computed with no rule is reported as a problem rather than silently passing — documentation cosplaying as enforcement is worse than an admitted gap.
    THE HONESTY RULE THAT CAME OUT OF IT: `aerial-perspective` (no plane may out-contrast one in front of it) was going to be computed, until the flagship instance legitimately violated it — a starfield DRAWN by a §4.11 generator is authored at final contrast and is not "faded", it is dark. It is judged with a stated exemption. **A computed rule your own instance fails is a lie with a green checkmark.**
    A STALE PLACEMENT RULE IS WORSE THAN NO RULE. The projection's `placement` block was written from the first implementation, and three rules were false by the time it worked — most damagingly "the containing element must NOT be overflow-hidden", when the frame in fact MUST be clipped (a positioned section paints above the non-positioned sections after it, so an overflowing plane lands on the next section's copy; what makes clipping safe is starting the frame above the section by the overhang so every plane's headroom is already inside it). The next brand follows a placement rule without testing it, because placement rules read like principles. Rewrite them from what shipped, and DELETE the ones that turned out wrong.
    NEW SKILL `add-projection`. The framework had `add-generator` but no verb for "a new KIND of deliverable", which is why the reflex was to add a primitive. It leads with the table of what people mistake for novelty (ordering → crossSlot invariant; N things generated alike → a slot with `repeat`; needs-a-style-pack → `requires` by kind) and states the bar: a new primitive is warranted only when the thing cannot be expressed as a contract with slots that emits files.
    ONE PROCESS NOTE, NOT A FRAMEWORK ONE: this session's engine work (`model.py`, `store.py`, `test_engine.py`, the projection) was swept into the gary-sheng-art session's commits `57b1e9b` and `e47ba50` by a `git add -A` in that session. Nothing was lost and the work is intact, but it is committed under someone else's message and rationale. Stage by explicit path in a shared checkout, in BOTH directions — the hazard is symmetric and this is the second time it has bitten.

2026-07-28 (later) · **SPEC v0.14 — PROJECTION/COMPOSITION BECOME FORM/WORK.** The entry above is left as written and its vocabulary is SUPERSEDED, not corrected: `ProjectionType parallax-scene@1.0.0` is now `Form scrolling-diorama@1.0.0`, and `ProjectionInstance` is `Work`. A log edited to look consistent stops being evidence of what was believed when.
    WHY IT MOVED. A projection is determined by (object, map) — give me the cube and the angle and the shadow follows. A work is NOT determined by (canon, form): `beats` and `spine` are authored facts present in neither, and §4.9's `writesBack` lets a work change the canon it supposedly views, which no shadow does to its object. The metaphor's own disproof had been sitting in the spec since v0.11. So `projection` survives as the name of the RELATIONSHIP canon bears to a work — the one job that word does correctly — and stops naming either primitive. The pair that fits is hylomorphic: **canon is the matter, a form is what shapes it, a work is canon given form.** "Instance" was dropped because it actively DENIES the authorship a work carries; a book's identity is not derived from being an instance of a book-shaped thing. Worth recording that `Composition`, the original §4.9 name, was ontologically CLOSER to right than the `ProjectionInstance` that replaced it — a composition is an authored thing made within a form from materials — and was traded away for legibility when the two names could not be kept straight in conversation. `Work` gets both.
    THE FIT VARIES BY FORM, and the slot schema measures it: `scrolling-diorama` is near-pure projection (its slots are derivable from canon plus geometry), `storybook` is mostly authorship. That stays PROSE and not a primitive, because no two forms need to agree on it — the same bar §4.8 sets for everything else. Three things were declined on that bar in one night: `medium` as a primitive (it earns it when a SECOND form targets one), work-NESTING (zero real nested works exist; designing the boundary from no examples is the §4.12 mistake in a new costume), and this.
    THE NAMING RULE THAT CAME FIRST. `parallax-scene`'s `id` equalled its `surface.medium`, which is the tell that a category's name has been taken for one way of working in it — vertical scroll, edge-pinned bands, sink-behind occlusion, with mouse-driven and horizontal and dolly scenes left nowhere to live. **Check `id` against `surface.medium` before shipping a form; they should never match.**
    ON NESTING, recorded rather than built: parts are not works (a spread has no independent existence; the same spread sold as a print IS a work, so nesting is a property of the RELATION, not the artifact). The hazard is that **crossSlot invariants do not cross the boundary** — nest a work and it becomes a black box to the outer work's checks, which is exactly where `character-identity` drift would slip through. And the `install` map is the SYMPTOM: every work today ends by reaching outward into repos it cannot see or validate. If a site were a work, that arrow inverts and `install` mostly dissolves.
    BACK-COMPAT IS TESTED, NOT REMEMBERED. A work keyed with the pre-0.14 `projection` field still loads, guarded by a test that fails if the fallback is removed. A rename that silently orphans the things it renamed is the failure mode renames are famous for. 121 tests.

2026-07-28 · ON-BRAND-IMAGE LEARNS THE COMMONEST DEFECT CLASS (plugin 0.26.1). Five failures in one night's art session were all one thing: a PHYSICAL RELATIONSHIP the prompt never named, which the model then resolved at random. A phone filmed a selfie while its rear camera faced the subject. A lifted floor hatch could not fit the hole it came out of. Burning letters reflected in still water the same way up as the originals. A man stood inside the well he was standing beside. A beam of light crossed a crowd of demons and struck none of them. Not one is a style, anatomy or composition problem, and not one was visible until a human pointed at it; every fix was the same shape, which is why it is now a skill section rather than five corrections. State the relationship, say which way it must read, say what the wrong version looks like.
    THE COROLLARY, proven twice the same night: A GEOMETRY RULE BELONGS IN CANON, NOT IN A PROMPT. The hatch rule was fixed once and then silently regressed when the same piece was re-shot with a newly-canonised character added, because the constraint lived in prompt text and nothing carried it forward. The same failure took the WEAPON out of every render (it existed only in a prompt until it was promoted to a typed prop) and kept a character rendering as depressed for batch after batch (because "faintly tired" was sitting in his invariants, where it kept firing). Fix canon or expect to fix it again.

2026-07-28T16:33:30Z · PROMOTED: a setting's blueprint is now a CODE-BUILT 3D MASSING RENDER, not a prompted image and not a top-down plan. Spec v0.14 -> v0.15 (additive + advisory; no universe has to migrate and a hand-drawn blueprint still validates), plugin 0.26.1 -> 0.27.0. New engine module `agenticstory/massing.py` + `massing` CLI verb: declare a room once as boxes and quads with its cameras named, and it renders the ACTUAL perspective each locked camera will see, deterministically, with no model, no key and no cost, writing its own .recipe.json. Pure-python vector math and a lazy Pillow import, so the engine takes no new hard dependency. WHY: `blueprint` was specified only as "top-down/schematic", and a plan makes the image model INFER the perspective it has to paint. Inference is where geometry drifts, and the expensive failure mode is handedness silently flipping, so a contract claim like "the bookshelf wall is C1-LEFT" stops holding halfway through a book. A massing render hands the model a picture to match a picture, and forces real numbers at authoring time when a wrong room is still cheap. Kept deliberately crude (flat blocks, ink edges, no textures) because a blueprint that looks like art invites the model to copy its surface. `add-setting` rewritten: building the blueprint is now its own step BEFORE the prompts, the blueprint is no longer prompted, and every plate prompt passes it. Same rule extended to a visual-metaphor with fixed geometry: seed the state chain on the blueprint, never on a sibling state plate, or parallel state renders come back as three different objects. Engine tests 121 -> 133 (handedness inversion, determinism, near-plane rejection, provenance, CLI round-trip). Earned on Beside Still Waters, whose four new peaceful settings were the first built this way.

2026-07-29T17:05:00Z · THREE SILENT PROMPT-ASSEMBLY BUGS FIXED, ALL FOUND IN ONE BOOK RUN (plugin 0.27.0 -> 0.28.0). Earned on it-only-has-to-fly (hyperagentic-age). None of the three raised, none logged, and each degraded output in a way that reads as the model being mediocre rather than the harness being broken, which is why they survived so long.
    (1) A STRING `negatives` WAS SHREDDED INTO SINGLE CHARACTERS. The assembler did `list(v)` on a documented-as-list field, so `list("NO STRAY TEXT")` became ['N','O',' ','S',...] and every book-wide negative reached the model as a comma-separated spray of letters. Already shipped: the-best-news-ever and the-room-it-was-made-in both carry a string, so every spread either of them ever rendered went out with its negatives destroyed. Their next rerun picks the fix up free. Same shape confusion the SPEC already records for realPerson.photoStack, which is the argument for fixing it at the chokepoint rather than in each book.
    (2) A SETTING'S GEOMETRY NEVER REACHED THE MODEL. resolve_setting built its block from contract.dressing alone, so `map`, `blocking` and `scale` were dead weight in every entity file that carried them, and a setting's consistency rested entirely on its plate image. That is not enough: the plate is one reference among many, and on a spread that also passes two character masters and a motif sheet its geometry gets diluted, so the model keeps the vibe and re-invents the layout. Gary caught it by eye at contact-sheet scale, 'the settings change': one small shed had its doorway camera-left on most spreads and camera-right on another, its window and shelves migrated between walls, and the room changed proportion, in a picture book whose whole premise is that the reader comes to know that shed. Order is map, then blocking, then dressing, then scale, because handedness is what a reader notices and it belongs before the clutter.
    (3) THE MASSING RENDERER DELETED ANY GROUND PLANE. It dropped any face with a vertex at or behind the near plane, documented as a deliberate crude tradeoff. It is wrong in the case authors hit constantly: a floor, lawn, road or tabletop is one big quad extending UNDER and BEHIND the camera, so the whole polygon vanished and the sheet rendered as empty background with the distant props floating in it. Cost two silent iterations before the cause was found, and pushes authors into chopping ground into strips that all sit forward of the eye. Replaced with a Sutherland-Hodgman near-plane clip that keeps the visible part. A polygon entirely in front is returned unchanged, so every existing spec renders identically, and geometry entirely behind the eye still draws nothing.
    ALSO, A DOC LESSON WITH NO CODE FIX: THE BOOK `style` MUST DESCRIBE THE BOOK, NEVER THE CAST. The style string is prepended to every spread, so anything it names is present on every spread whether or not that spread cast it, and it sails straight past the uncast-character guard because the guard reads the SCENE text while the invention comes from the preamble. A style reading 'about two children and a small hand-made helper' put a different invented robot into each of the five spreads that did not cast the helper, one of them three spreads before the character is introduced and one of them twice in the same frame at two different sizes. Five re-renders. compose-spread now says so with the worked bad/good pair.
    Tests 458 -> 463, all green, and each new test was negative-controlled against the old code rather than assumed: restoring the buggy versions fails 5 of them. A test that cannot fail is worth nothing.

2026-07-29T18:00:00Z · SPEC v0.16 + plugin 0.29.0 · ENTITY LIFECYCLE, so canon can be RETIRED without rewriting history. Promoted from a real gap hit mid-build: Gary asked to archive the setting `jerrys-porch` and the framework had no concept of it, so the only options were deletion (which breaks every shipped book and falsifies its provenance) or a note in prose that no tool reads. Neither is an archive. An entity now declares `lifecycle: active|archived` plus an `archived` block (`on`, `reason`, optional `supersededBy`); `lifecycle` is EDITORIAL STANDING and is deliberately orthogonal to `status`, which is reference-completeness, because an archived entity is normally still fully locked and its art stays valid forever. The load-bearing design decision is WHERE the gate sits: `assert-story` knows nothing about lifecycle (there is a test asserting its source never learns), so archiving can never retroactively break a shipped book; the refusal lives at the point of NEW casting, in the spread compiler, which refuses before spending and names the replacement, with a per-spread `allowArchived` opt-out for a deliberate re-render of a pre-archive book so that choice leaves an auditable trace. An archive with no recorded `reason` fails validation. Engine: `Entity.lifecycle/is_archived/superseded_by/archive_note`, `refs.archived_casts`, `refs.archived_entities`, CLI `archive`/`unarchive`/`archived`. Docs updated in `casting-sweep` (reuse-first must not resurrect retired canon) and `compose-spread` (the fifth guard). 472 tests green, up from 463.
    RESUME: applied to nation-of-fire (`jerrys-porch` archived, superseded by `the-creek-path`). Worth a later sweep: `universe-doctor` does not yet report archived-but-still-cast entities as a completeness dimension, and `lint-universe` could surface the same list statically.

2026-07-29T19:40:00Z · SCALE IS NOW DECLARABLE ON ANY ENTITY, NOT JUST CHARACTERS (plugin 0.28.0 -> 0.29.0). Gary, on a book mid-render: 'why does the laptop look different sizes?' It did, and nothing could have caught it. An entity file describes form, colour, materials and rules and never says HOW BIG the thing is, and every gate in this framework checks identity, register and composition, all of which a thing satisfies at any scale. The supercharged laptop appears in most of twenty-one spreads of what-a-book-is-made-of and ranged from a notebook to a small television. In that universe colour was MEANING and scale was a GUESS.
    The machinery existed and was pointed at the wrong thing. `structured.scale` was read only off CHARACTERS, and the RELATIVE SCALE block only fired when two or more of them declared a relation to each other. So a recurring PROP could not contribute its size at all, and no entity of any kind could state its own size alone. Scale is now collected from EVERY in-frame entity regardless of kind, and a new `scale.absolute` sentence is emitted as a TRUE SIZE line whenever that entity is in frame, solo or not. `relativeTo` is unchanged, and the two blocks are independent.
    THE AUTHORING RULE THAT MAKES IT WORK: pin the size to things a render already contains. '33cm wide' is unverifiable in a painting. 'About twice the height of the mug beside it, about a quarter of the desk width' is checkable at read-back by looking, which is the whole point. Write the ratio, then the measurement.
    Also promoted: a CODE-DRAWN SCALE PLATE via `massing` is the cheapest way to get those ratios right. Model the object beside a desk, a mug and a spread hand, render it deterministically for nothing, and you get both a reference image to pass and the numbers to write into canon. Tests 463 -> 478.

2026-07-29T22:10:00Z · CAST CLOSURE IS NOW EMITTED ON EVERY RENDER (plugin 0.30.0 -> 0.31.0). The prompt always said who IS in frame and never said that was ALL who is. Every other guard here reads the SCENE; this defect comes from the PREAMBLE, because a book-wide `style` string is prepended to every spread, so any figure it mentions is present on every spread whether or not that spread cast them. The uncast-character refusal cannot see it. Nor is it catchable by name: both styles that caused it described the cast GENERICALLY ('a small hand-made helper', 'a man at a desk'), so no entity name appears anywhere to match on.
    Cost in one session across two books: eleven re-renders. A different invented robot in five spreads of one book, one of them three spreads before that character is introduced in the story and one rendered twice in the same frame at two different sizes; then a man appearing in two spreads of another book whose scenes said the room was empty. THE LESSON WAS WRITTEN INTO THE SKILL AFTER THE FIRST OCCURRENCE AND THE SAME SENTENCE WAS WRITTEN AGAIN TWICE MORE, which is a fair measure of what a documentation-only fix is worth. The assembler now states the closure itself, derived from the cast, so an author cannot forget it and a preamble cannot contradict it. Empty-character spreads get a flat 'there are no people of any kind' instead.
    Two doc lessons landed alongside it. A LOAD-BEARING EXCLUSION GOES FIRST: two spreads kept rendering a seated figure through two rolls with the exclusion appended at the end of a two-hundred-word scene, and moving that same sentence to the front plus tightening the camera fixed it with no new words. And DO NOT COMPOSE FOR THE READ-BACK: side-on shows a face and a face is easy to verify, so it becomes the silent default; every interior spread of what-a-book-is-made-of came out side-on and the blueprint's own over-the-shoulder camera was never referenced once, in a book whose thesis is that the man is outside the machine looking in. Tests 478 -> 483.

## 2026-07-29 — pave-the-path, first run (she-had-everything-but-peace, 40 spreads)

The skill's own maiden sweep, run on the book that earned it. Evidence read from the diff
and the scratchpad, not from memory. Five throwaway scripts existed in the scratchpad by
the end of the run; all five were the SAME missing capability wearing different names.

### PAVED IN THIS SESSION (both were BUGs, both tested)

- **`realPerson.photoStack` cap did nothing on a directory stack.** The `[:2]` slice ran on
  the RAW list, and a stack entry may be a DIRECTORY, so a one-entry directory stack passed
  every photo in the folder. nof `victory` shipped SIX refs on 17 spreads, two of them
  multi-person family-band photographs. Fixed: expand first, cap after, default uncapped
  (which is what SPEC's own "5+ real photos" always meant), `realPerson.photoLimit` to cap.
  9 tests.
- **The readable-surface prompt guard contradicted itself.** It had no `card` in its word
  list and simultaneously demanded "NO real readable letters", so a scene specifying exact
  designed text made the model choose, and it chose legible-by-rotating-to-the-lens. Caught
  by Gary twice (it-was-not-broken sp36, she-had-everything-but-peace sp16). Fixed by naming
  the resolution — legibility is a CAMERA problem, move the camera to the reader's side,
  never turn the page — and by moving the guards into ONE shared `prompt_guards.py` that both
  generators import, because `nano-banana-pro` had no guards at all. Two further bugs found
  while fixing it: probes matched paraphrases (so a book's weaker restatement would SUPPRESS
  the authoritative guard) and the guards were not idempotent (`_GUARD_UI` says "Screens",
  so a second pass inferred a device). 8 tests, one of which proves the guard can stay silent.

### PAVED IN THIS SESSION, part two (after Gary corrected the skill's default)

The first version of this sweep wrote the items below into this file as ranked *proposals* and
shipped none of them. Gary: *"how am I supposed to integrate the pave-the-path suggestions that
are in SAVE-LOG.md? I feel like the default should be to integrate. Am I crazy?"* He was not. A
suggestion in a log is a to-do nobody does, and it is the exact failure `fix-the-generator`
already names: writing down a hazard is not removing it. The skill's default is now INTEGRATE,
the caution lives in the bar and nowhere else, and "shipping a list instead of a change" is
recorded there as its worst available outcome.

- **The book-manifest contract, three gates, BUILT** as
  `garysheng-books/apps/web/content/__tests__/book-manifest-contract.test.ts`. Each is calibrated
  to what could actually be verified, which turned out to be the whole job:
  - *BookEntry required fields*: HARD, all 178 books, verified clean today so it is a true
    invariant. This book shipped missing `slug`/`assetBase`/`releasedAt` and the failure surfaced
    much later in disguise, as narration reporting "no book with slug X in the registry" for a
    book that WAS in the registry.
  - *Captions verbatim from the blessed manuscript*: HARD for books released on/after the cutoff,
    reported before it. Unscoped it fails ~135 assertions across the back catalogue and every one
    opened was a REAL divergence, so the gate works; failing a hundred shipped books would just
    train everyone to ignore a red suite. It earned its keep within the hour, verifying all 44
    captions after the 40-to-44 restructure.
  - *Column budgets*: REPORT-ONLY, deliberately, and this is the honest part. The check detects
    an overrun; the three LIMITS are unverified, 99 of 178 books exceed them (longest subtitle is
    261 against a documented 52), and three of those shipped the same day from other sessions.
    Asserting an unverified number would break sibling work and encode a guess as a contract. The
    promotion path is written into the file.
- **`pave-the-path` is now auto-called**, which was the other half of the problem: a
  retrospective skill nothing invokes does not run. It is step 9 of `make-a-book`'s load-bearing
  order (story -> ... -> publish -> land -> **pave**), so it fires on every book, and it is a
  first-class item in `save-my-progress`, whose survey reads the git diff and would otherwise
  never see a scratchpad script at all.
- **A travel-direction guard**, from Gary catching spread 18: a character ARRIVING somewhere had
  the building behind her, so she read as leaving. Same failure shape as the readable-surface bug
  and the same resolution, now stated in the guard: the destination is AHEAD of an arriving
  character, and if you need their face, move the CAMERA to the destination side. Never turn the
  subject round.
- **`structured.seating` on settings**, from Gary catching that two women had swapped sides
  fifteen spreads into one dining room. The universe had already learned this once and written it
  as prose on `brendas-suv` ("FIXED SEATING, continuity-critical"); it is now DATA the compiler
  emits whenever two of the named entities share a frame.

### STILL PROPOSED, with the reason it was not built

- **Batch render mode in the renderer.** Five scratchpad scripts did the same job: render a list
  N-way parallel, retry on stochastic `moderation_blocked`, skip what exists. Three shell traps
  cost real time and one entirely wasted 17-spread pass that reported OK (`export -f` does not
  survive zsh into `bash -c`; macOS `xargs` has no `-a`; a `for n in $VAR` parking loop silently
  no-opped). NOT BUILT because it is the one item large enough to be its own project, and landing
  it half-done mid-book would have put the book at risk. It is the top of the next sweep.
- **`book_doctor` treats every `spreads[]` entry as a landscape interior**, so it demanded 3:2 of
  a 3:4 cover and could not say healthy until the endcaps were renamed `cover-0`/`plate-0`. It
  should read the declared per-spread `size`. NOT BUILT because it changes a gate other books
  depend on and deserves its own verification pass.
- **Face-crop step in `shoot-references`.** Small; deferred with the batch driver since both live
  in the same neighbourhood.

### DECLINED, and recorded so a later reader knows it was considered

- **A generic Wikimedia photo fetcher.** LEAVE. Every real person needs different sources
  under different licences, and a generic fetcher would encourage using whatever it returned.
- **"Chain a known-good sibling in as the control."** GUIDANCE, not code: which sibling is
  trustworthy is a judgement, and `make-a-book` already says it.
- **The contact-sheet builder.** Borderline; built ~8 times with small variations. Declined
  for now because each sheet's crop was scene-specific, and three of my crops were wrong in
  ways a helper would not have prevented.

The tell that the sweep was worth running: **five of the six proposals were invisible from
inside the run.** Each felt like "just getting unstuck" at the time.

2026-07-30 · PROMOTED: `chain_matrix.py --register <pack-id>`, so a MULTI-REGISTER universe can shoot an entity's reference matrix in a Style Pack other than `identity.register`. Caught while shooting `simone` in gary-sheng-art, whose README says it is built to hold many registers and whose `through-the-waters` story declares `cinematic-anime-cel`: the matrix would have been shot in the default `warm-crayon-parable` and then used as an identity reference for anime-cel renders. `resolve_register()` reads `reference/style/<id>/pack.json`, normalises the pack-relative anchor to universe-relative, and uses that pack's `rejectedPoles` ALONE rather than merging the default's, because a pack that permits what the default rejects would otherwise fight a negative it never declared. Refuses loudly on an unknown pack or an off-disk anchor instead of falling back and silently shooting the wrong look. Default behaviour unchanged. 4 new tests (chain_matrix 26 → 30; suite 495 → 499, ALL GREEN). Plugin 0.35.0 → 0.35.1. Also flagged and NOT worked around: relation sides resolve only within one universe (`store.py` validate_canon), so a cross-universe derivation like `gary-sheng-art:wisp` derived-from `nof-universe:wisp` cannot be recorded as a typed relation; that provenance currently lives in the entity's `authority.note`.

2026-07-30 · PROMOTED: `abu elevation`, a code-built 2D ELEVATION renderer for OBJECT blueprints (`engine/agenticstory/elevation.py` + CLI verb), the flat sibling of `massing`. `massing` renders a SETTING as a perspective view from a declared camera, which is right for a room and wrong for a door, a key, a lamp or a hatch: those are argued flat and head-on, so every object blueprint got hand-written instead. Nation of Fire had accumulated NINE such scripts (~1300 lines) by the time this landed, and they agree almost entirely on what they draw. Eight of the nine re-implement the same `font()` fallback chain; several re-implement dimension lines and dashed strokes. The expensive part was not the duplication: only FOUR of the nine stamped `LAYOUT REFERENCE ONLY` on the sheet, so five shipped a blueprint that does not declare itself one into a pipeline whose whole blueprint convention is that the guard is present. This renderer stamps the guard unconditionally with no flag to disable it. Geometry is declared in the OBJECT'S OWN UNITS (`scale.unit` + `pxPerUnit`) rather than pixels, because that is how an entity contract already states it ("about three feet wide by seven feet tall"), so the arithmetic stops living in the author's head. Parts: rect, line, ellipse, polygon, dim, note, and `repeat` for the five-planks / two-hinges / four-nails runs where hand-written member loops hide off-by-ones. Vertical dimension labels are clamped inside the sheet, because a generous offset used to push a measurement off the page silently. Fails closed on an unknown part kind, an unknown colour, a non-positive scale and a non-object repeat prototype. Deterministic, no model, no network, no cost, with a provenance recipe matching `massing`'s shape. Proven by rebuilding the-little-door's blueprint from a 40-line declarative spec at parity with its 175-line hand-rolled script, which was then deleted. 16 new tests (suite 499 → 515, ALL GREEN). Plugin 0.35.1 → 0.36.0.

2026-07-30 · PROMOTED: re-running `create-lookbook`'s scaffolder no longer forks a lookbook off its own provenance, and it now carries the `.recipe.json` sidecar it was leaving behind. A lookbook GROWS: you scaffold four exemplars, shoot four more, re-run with all eight. That re-run renamed every already-present exemplar to `<stem>-1.png`, because the basename-collision guard could not tell "a different file with the same name" from "this same file again", then pointed the manifest at the renamed copy while `<stem>.png.recipe.json` stayed beside the original. So the refs folder doubled and every re-scaffolded exemplar silently lost its provenance. Caught in christofuturism on 8 of 12 women's plates, and only by a manual audit, because nothing downstream checks a lookbook's provenance coverage. Identical content now reuses the name; genuinely different content sharing a basename still renames, which is the case the guard was written for. The second half is older and dumber: the scaffolder copied the image alone, so every caller hand-copied provenance afterwards, four times in the session that finally promoted this. `create-style-pack` had already solved the sidecar half and is now given the same re-run fix. The scaffolder also reports provenance coverage (`provenance 12/12`) and warns by name on any exemplar that lands un-audited, so the gap is visible at the moment it opens rather than at audit time. 2 new tests, one per failure mode, both verified to FAIL against the pre-fix scaffolder (suite 515 → 517, ALL GREEN). Plugin 0.36.0 → 0.36.1.

2026-07-30 · PROMOTED: a SETTING now gets a SHOT LIST at creation, the way a character gets a reference matrix, plus per-plate contract scoping so a close-up is not told what a wide shot contains. A character's eight shots are made BEFORE anything renders, so no later beat has to invent a view of them; a setting got a master, a turnaround and a blueprint, and every camera after that was improvised from the wide plate. That asymmetry fails the same way every time, because a close-up cannot inherit what the wide plate does not show, so the model re-invents whatever is out of frame, differently on every spread. Earned in nation-of-fire on the-teaching-room: one wide master was locked and twelve teaching beats were then asked for at conversational distance, and the audience seating drifted spread to spread until a dedicated chairsCloseUp plate was shot. Gary named the rule: "when you're creating a setting, you should basically create all the shots that you want inside that setting." Three parts landed. (1) `compose-spread`'s `resolve_setting` used to inject the WHOLE contract as text on every render regardless of camera, so a close two-shot of two chairs was still told the room held sixteen seated guests in tiers; a plate may now scope itself via `contract.plates.<name>` with an optional `note` and `includeBlocking: false`, and absent config every universe renders byte-identically. (2) `add-setting` now instructs shooting the shot list (wide, conversational, reverse, plus a plate per recurring camera) and scoping each plate before locking. (3) `lint-universe` gains SETTING-HAS-NO-SHOT-LIST, which flagged 14 locked settings in nation-of-fire on its first run, plus PROSE-NAMES-UNWIRED-FILE and POSE-CITES-SHEET-IT-DOES-NOT-PASS for the defect class found TWICE the same day: jerry-man's eight ql-* poses each cited a capsule reference sheet their `sheets` never passed, and christofuturist-village named three plates by file path that `sheets` never carried, so every village render silently fell back to the daytime master. A rule that lives only in prose is a memory test, not a gate. 3 new tests (suite 523 → 526, ALL GREEN). Plugin 0.36.1 → 0.37.0.

2026-07-30 · PROMOTED: consistency is now pinned by the framework rather than left to prose, across three primitives, after one book surfaced the same defect four separate times. The shape every time: a rule stated as WORDS where the compiler needed a REFERENCE or a concrete spec. (1) `compose-spread` REFUSES a cast entry whose `bake` would replace the canon block of a character carrying identity invariants. `bake` replaces rather than appends, which is right for a multi-state prop and catastrophic for a character, because the canon block is where ONE LOCKED FACE, the wardrobe rules and the modesty anatomy live. All 17 spreads of gain-everything-lose-nothing carried a hand-typed paragraph that replaced canon, aged the character a decade past what canon says, and shipped before anyone noticed; `allowIdentityOverride` keeps the override possible but auditable. (2) `compose-spread` REFUSES a setting cast with no plate: `resolve_plate` returns nothing for a null plate, so the spread passed no setting image at all and invented the place from prose, silently. An audit found 10 such spreads across shipped nation-of-fire books plus 42 selecting a plate absent from the entity's `sheets` map. (3) `add-character` now instructs pinning WARDROBE to a capsule sheet plus per-look poses that PASS it, and stating modesty and body rules as ANATOMY rather than adjectives; `lint-universe` gains CHARACTER-WARDROBE-NOT-PINNED, which flagged 123 characters in nation-of-fire on its first run, where `jerry-man` was the only character in the universe whose clothes were pinned to anything. (4) `add-setting` gains the populated-plate doctrine: recurring scenery (a congregation, a crowd, a classroom) belongs in a PLATE, not in a cast. A group entity with a lineup and a seat roster was started for sixteen guests and discarded as cast machinery far too heavy for set dressing; the fix is a second plate on the same camera with the crowd already in it, because one image cannot drift. Gary named it: "they are mostly just setting ornaments, just need to make sure there is consistency of shots." (5) `render-readback` finally ships `contact_sheet.py`, the read-back unit its own text has always prescribed and never provided; it was hand-rolled as the same PIL montage ten times in one session, and it REFUSES a partial sheet, because a silently short sheet reads as "everything I rendered" and is how a missing spread goes unnoticed. 7 new tests (suite 529 → 536, ALL GREEN). Plugin 0.37.0 → 0.38.0.

2026-07-30 · PROMOTED: `compose-spec`, the missing verb between a StorySpec and a book's render-spec. A story already knows its beats, their locations and who is in them, and a render-spec restated all of it by hand, so every book grew a bespoke authoring script and those scripts rot. The spec gets hand-edited after the first run, the script does not, and re-running it silently reverts the edits: gain-everything-lose-nothing's generator still carried an identity-overriding `bake` and crowd prose that six hours of fixes had removed, so one re-run would have undone every one of them. It is deliberately NOT a spec generator. It fills what canon DETERMINES (id, setting, cast membership, preamble, size, refreshed every run), ENUMERATES what canon merely constrains (plate, pose, look, carried forward and never chosen on the author's behalf), and never touches what a human AUTHORED (scene, negatives, flags) without `--force`. The enumeration is the real value: a null plate printed beside its legal values is visible, whereas a missing wardrobe pose is invisible, which is exactly how one character went twenty spreads with her clothes unpinned. A new beat appends; a spread not in the story (a cover, a closing plate, a removed beat) is kept and reported, never deleted. 5 tests covering derive, re-run preservation, insertion, non-beat survival and the force escape (suite 536 → 541, ALL GREEN). Plugin 0.38.0 → 0.39.0.

2026-07-30 · PROMOTED: the framework's own documentation is now a DERIVED artifact with a failing-test staleness gate, via `abu build-docs [--check]` and the new `engine/agenticstory/docsfile.py`. `canonfile` had already made a universe's CANON.md a projection of its record store, because a hand-maintained shared file drifts and git cannot catch it; the framework's own docs had the identical disease and no cure. Audited cold, the public README claimed spec v0.6 while SPEC.md was v0.16, claimed "165 tests across seven skill suites" against a real 541 across 22 files, and taught two layer names, Projection and Composition, that v0.14 had renamed to Form and Work. Every one of those numbers was true the day it was typed, which is the entire problem: prose asserts a fact once and then rots silently while the thing it describes keeps moving. Six blocks are now generated between BEGIN/END fences from the sources that already hold the truth: `status` in README.md (spec version and date, engine SPEC_VERSION, skill count, verb count, test count) and `skills`, `cli`, `forms`, `providers` and `spec-changelog` in the new `docs/REFERENCE.md`. The skill table reads each `skills/*/SKILL.md` frontmatter, the CLI table introspects the REAL argparse parser rather than a hand-kept list, which is how `archived` and `land` had shipped undocumented. That introspection needed `cli.main` split into `build_parser` plus dispatch, and it immediately exposed eight verbs carrying no `help=` at all, now written, because a blank help string renders as a blank documentation row and a blank row is how an undocumented verb hides in plain sight. `check()` also enforces the one invariant prose cannot: SPEC.md's version and the engine's SPEC_VERSION are bumped by hand in two files, and the comment asking for lockstep was never a mechanism. The gate is the point, not the generator. `build-docs --check` runs inside `run-tests.sh`, so drift is a RED SUITE rather than something a reader discovers months later, for the same reason a render writes its recipe as a side effect of generating: documentation you have to remember to refresh is not documentation. It proved itself immediately, going stale on its own test file the moment the file was added. Hand-written and deliberately NOT generated, because they are judgement rather than fact: `QUICKSTART.md`, which teaches the style-pack-plus-gate slice that needs no universe at all and is enough to make a zine, and `docs/GLOSSARY.md`, which defines the vocabulary by what each term REFUSES. Gary asked the question that started it, whether documentation could be generated as the framework evolves so it cannot go stale, after asking how hard it would be for a friend making a zine on chatgpt.com to adopt any of this. Still open and named in QUICKSTART as a known gap: `on-brand-image/scripts/generate.py` resolves its two provider scripts and the engine by absolute path into Gary's home directory, so image generation cannot run on a fresh clone. 19 new tests (suite 541 → 560, ALL GREEN). Plugin 0.39.0 → 0.40.0.

2026-07-30 · FIXED, by the tool on the book it was built for: `compose-spec` classed `setting` as DERIVED and refreshed it from `beat.location` on every run. A render-spec legitimately diverges from its story, because a beat says "their house" and the book stages it in one specific room that did not exist when the beat was written. Re-syncing gain-everything-lose-nothing therefore reverted 16 of 20 spreads to a BANNED hearth room, and the run reported "plates altered: NONE" because only the setting had moved, so it read as a clean pass. `setting` is now CARRIED FORWARD: filled when absent, kept when present, and any divergence from the beat is reported loudly by name. It also now validates that a chosen plate is actually a sheet of the chosen setting, which is the check that would have caught this immediately: 16 spreads were pointing at plates belonging to a different entity and resolving only through a filename fallback. 2 new tests (suite 541 → 560 with the engine, ALL GREEN).

2026-07-30 · PROMOTED: the framework got a FRONT DOOR, an install that is a conversation, a self-contained provider path, and its own name. Four things, one release, all driven by the same question: what does a non-technical person actually touch. (1) PORTABILITY. Four scripts each hardcoded an absolute path into one developer's home directory (`~/.agents/skills/chatgpt-images/...`, `~/Documents/github-repos/agenticstory/engine`), copy-pasted, which is the tell that the resolution wanted to be a function. A fresh clone could validate canon and pass every test and then fail to generate a single image, because the one thing it could not find was the thing that draws. Both provider scripts are now VENDORED under `providers/<id>/` and resolved by `engine/agenticstory/providers.py` in the order env-override, vendored, then the legacy home paths so an existing machine keeps working. A framework that demands self-containment of a Style Pack (§3a copies its refs IN) and does not practise it on itself is asserting a standard it fails. A test now greps every script and fails if a home path is reintroduced. (2) THE FRONT DOOR. `universe-doctor` could grade a universe from the day it shipped, but you had to know the verb existed, know you wanted a grade, and know the path: a destination, not a front door. New skill `abu` opens by telling you where you are. `engine/agenticstory/workspace.py` holds the small state that makes it possible (`~/.abu/universes.json`, `~/.abu/state.json`), finds the universe by walking UP from wherever you are standing, diffs today's score against the last one so a session can say "71 to 78 since Tuesday", and selects from the issue list rather than reciting it. Selection needed a correction found in testing: the first version picked the "if you're bored" job by GROUP SIZE, and the grader already aggregates, so "835 images have no recipe" arrives as ONE record and looked like the smallest job available when it was the largest. It now picks by lowest impact, which is the grader's own judgement and does not lie about scale. (3) ONBOARDING AS A CONVERSATION. QUICKSTART.md is deleted and replaced by WELCOME.md, which contains no commands at all, plus an `onboard` skill that runs the install and reports in sentences. Gary named the principle: the whole experience should live inside the harness, and all a player should have to know is what they want. The hard rule now written into both new skills is that the agent never shows the user a shell command, with one honest exception for the harness itself and an API key, because both are credentials rather than chores. The interview still PROPOSES rather than waits, since a system that only responds to desire cannot teach the vocabulary needed to have good desires: nobody asks for a content-neutral anchor. (4) THE RENAME. Three of four public surfaces already said Agentic Brand Universe (SPEC.md's title, the public repo, the domain) while the plugin namespace still said agenticstory, and "story" undersells a framework that does zines, decks, cards, favicons and diagrams. Plugin is now `abu`, invocations are `abu:*`, the CLI's prog name is `abu`, `evolve-agentic-story` is `evolve-abu`, and 98 files were rewritten across the framework, the marketplace and every external cartridge skill. The python package stays `agenticstory` and the local repo directory is unmoved: the prefix is developer-facing and nobody should ever be typing it, so the rename is worth doing for the public surface and not worth breaking every import over. Worth recording that `rg` silently skipped `~/.agents/skills` on the first survey and reported 5 external references when find+grep found 12; a rename driven by the first number would have left orphans in the cartridge skills. 50 new tests (suite 541 → 591, ALL GREEN). Plugin 0.40.0 → 0.41.0.

2026-07-30 · PROMOTED: `abu backfill-provenance`, which records what is knowable about art that predates the provenance-writing adapter and REFUSES to invent the rest. `universe-doctor` had been advising "on-brand-image (regenerate via the adapter)" for the 835 un-provenanced images in Nation of Fire, and that advice was actively dangerous: the set includes LOCKED GOLDENS (the-readiness-lamp/hero.png, the-cold-gala/master.png, turnarounds). A golden is the visual answer of record handed to every downstream render, and generation is stochastic, so re-rendering one to repair metadata mutates canon and leaves every spread that already cited it silently disagreeing. The new verb never invokes a model. It sorts every image into four honest tiers: 88 RECONSTRUCTED from the prompts.md beside them (the prompt is real; refs, size and quality were never recorded and are left explicitly null rather than guessed), 43 DETERMINISTIC (blueprint/massing/elevation, flagged as re-runnable from their specs for a TRUE recipe at zero cost and identical pixels), 57 SOURCE (photo-stack inputs, which were never generated at all, so "the generating call was not recorded" is simply false about them), and 647 ATTESTED, carrying sha256 plus the commit that introduced the file and `unrecorded: true`. That last flag is the point: you cannot recover what was never captured, and a plausible reconstruction presented as a captured call is worse than an admitted gap. Two bugs were found by checking the data instead of trusting the first pass. The prompt parser understood only the `## hero -> path` heading dialect and recovered 27 of 232 candidates; the second dialect in the wild is `## face-3q`, where the heading IS the file stem, and supporting both took recovery to 88. And the first version silently stamped 57 photographs of real people with a note about a render that never happened. The RUBRIC changed with it, because the old rule scored an unfixable thing: provenance was `with_recipe / total`, so the only path to 100 on a universe with history was to re-render locked goldens, which makes the score useless as the game board it is meant to be. It now scores whether every image carries a provenance RECORD, an honest `unrecorded: true` counts, source photos leave the denominator, and the attested count is reported as its own visible issue ("690/1051 records are attested-only, no action: history, not a defect") so the truth stays on the report rather than being laundered by the number. Run against Nation of Fire: provenance 3/10 to 10/10, universe C 72 to C 79, 835 recipe files written, zero images regenerated, zero dollars spent. 21 new tests (suite 591 → 614, ALL GREEN). Plugin 0.41.0 → 0.42.0.

2026-07-30 · FIXED: a vendored provider must be COMPLETE, not merely present. `providers.resolve_str` prefers the vendored copy under `<repo>/providers/<id>/` over the one in `~/.agents/skills`, and `generate_image.py` had been vendored WITHOUT its `prompt_guards.py` sibling, so the preferred copy raised ModuleNotFoundError on import and shadowed the working one. Twelve renders failed in a row and the batch reported success, because the failure lived in a subprocess log and the caller's grep was misread. The missing sibling is vendored for both providers, and a new engine test walks every vendored provider and imports its local siblings; on its first run it found a SECOND incomplete vendor (`nano-banana-pro`) that would have failed the next time anyone used it. Also promoted the verification lesson: check that a render LANDED (file freshness), never that a log looks clean. 2 new tests (suite 560 → 593 with the engine, ALL GREEN).

2026-07-30 · FIXED: the rename left orphans, and the lesson is now written into `evolve-abu` so the next one cannot. `agenticstory:` survived in five LIVE INSTRUCTION files after the sweep reported clean: make-a-nof-book (7 refs, in nof-universe), make-a-book-on-ma (3, in garysheng-books), nof-universe/README.md (3), hyperagentic-age/PROJECTIONS.md (1), and appliedai-wiki's hosted save-my-progress (1). Every one of them was missed for the same reason twice over: Gary's skills are SYMLINKED from `~/.agents/skills` into the repos that own them, and neither `rg` nor Python's `Path.rglob` follows a directory symlink. `rg` reported 5 external references where `find -L | xargs grep` found 12, and the later rglob pass silently skipped `make-a-nof-book` altogether, so the cartridge skill for the flagship universe spent the afternoon pointing at a namespace that no longer resolved. A rename verified by the wrong tool looks finished and is not. The second rule the sweep needed is the opposite of the first: NEVER rewrite a historical record. 1,213 `.recipe.json` files and a pile of dated canon attestations ("LOCKED 2026-07-26: every matrix slot generated via agenticstory:shoot-references") state what actually ran under the name it had at the time, and rewriting those to the new name falsifies them, which is exactly the sin `backfill-provenance` was built to prevent. The split was 5 files to fix and 1,213 to leave. Both rules are now in `evolve-abu` step 3. Separately, WORKTREES were swept: 10 removed across five repos, and every branch and all 18 unmerged commits survive because removing a worktree removes only the checkout. Four were KEPT because they hold uncommitted work that removal would have destroyed (render/before-you-can-see-it 6 files, salvage/owen-petrak-restage 11, story/teach-them-to-obey 1, garysheng-books render/dont-add-to-the-book 1); "clean up the worktrees" is not the same instruction as "discard uncommitted work", and the difference is only visible if you check before removing. Plugin 0.42.0 → 0.42.1.

2026-07-30 · FIXED: the spec cited a URL that serves nothing, and every universe manifest repeated the citation. `SPEC_WIKI` was `https://agenticstory.wiki`, which every `universe.json` names in `spec.wiki` and `conformsTo`, and which `init` stamps into every new universe. Gary: "I have not once opened that wiki." Checked rather than assumed: the domain resolves to a Namecheap parking IP and returns NO HTTP response at all. A citation that does not resolve is the same defect as a recipe pointing at a file that is not on disk, and this one was baked into the authority line of every universe on the framework. The obvious replacement was half wrong too: `agenticbranduniverse.com` serves 200 but `agenticbranduniverse.com/spec` 404s, so swapping in the tidy-looking URL would have replaced one dead citation with another. `SPEC_WIKI` now points at the live home and `SPEC_URL` at the spec DOCUMENT on GitHub, which was verified 200 before being written down. The `agenticstory-steward` agent was renamed `abu-steward` in the same pass, since the rename had left it unavailable. Deliberately untouched, same rule as always: `SAVE-LOG.md` and `docs/superpowers/plans/*` keep the old URL because they are dated records of what was true when written, and zero `.recipe.json` files cite it, so no provenance needed correcting. Still open and NOT changed here: `universe.json` in nation-of-fire and hyperagentic-age still declare the dead URL in `spec.wiki`/`conformsTo`, and nof's copy carries another session's uncommitted reindent, so those are Gary's call. Separately, ALL worktrees are now closed at Gary's instruction: the four holding uncommitted work had it COMMITTED to its own branch first, so closing destroyed nothing. Nine branches survive with 23 commits between them. Plugin 0.42.1 → 0.43.0.

2026-07-30 · PROMOTED: an ergonomics pass on `abu`, found by dogfooding it rather than by imagining what would be nice. Three real defects. (1) IT FORGOT. Standing inside a universe resolved it correctly and then never recorded it, so `abu` from anywhere else answered "you have no universes yet" about a universe you were standing in five minutes earlier. Seeing a universe now registers it. (2) IT LEAKED COMMANDS. The grader's `fix` strings are written for whoever maintains the grader ("write canon/properties/<id>.json, then `abu build-canon`") and the front door was printing them verbatim, in a skill whose one hard rule is that a person never sees a command. There is now an outcome sentence per dimension, and the grader keeps its own vocabulary while the translation happens at the edge. (3) IT COMPUTED AND DISCARDED. `weakest` and `to_100` were both calculated and never shown, so the score was a number with no handle on it; the weakest dimension and the gap to 100 are now in the output, which is what makes it a game board rather than a verdict. The same aggregation trap that broke the first `small` selector nearly repeated here: the obvious humanizer interpolated the group size and said "1 image(s) cannot say how they were made" about 276 images, because one issue record can stand for hundreds of files. The outcome sentences now carry NO counts at all and the grader's own `what` string supplies every number, with a test asserting no `{n}` survives in any template. Score history was added too, bounded to 10 and only appended when the date changes, so a session can say "71 to 79 to 80" instead of only today's number. Live on Nation of Fire, which the branch merges moved C 79 to B 80: the front door now reads "weakest: settings prove their size (1/10, 9 to gain) / biggest win: something you have made is not registered as a story (71 full stories with NO canon/properties record) / if bored: some images cannot say how they were made (18/1304)". 10 new tests (suite 617 → 627, ALL GREEN). Plugin 0.43.0 → 0.44.0.

2026-07-30 · PROMOTED: ABU is now INSTALLABLE BY A STRANGER, which it had not been at any point despite the framework being public since day one. Gary, correctly annoyed: "Why would you allow anything out of date and not installable?" Three things were blocking a friend from ever running it, and all three had been reported rather than fixed. (1) THE MARKETPLACE WAS PRIVATE. `abu` shipped from `garysheng-claude-plugins`, a personal marketplace whose own description reads "Gary's private Claude Code plugins (installed locally, never published)", which also carries `anthropic-campaign` (interview journal marked Gary-and-Jarvis-only, PRM/CRM, insider advice). Nothing about ABU belongs next to that; they were co-located only because that repo is where all of Gary's plugins were born. Publishing it was never an option, so the public framework repo is now its OWN marketplace: `.claude-plugin/marketplace.json` plus `.claude-plugin/plugin.json` at its root, `source: "."`, which works because `skills/` and `agents/` already sit there. Install is now `/plugin marketplace add garysheng/agentic-brand-universe` then `/plugin install abu`, and the private marketplace keeps carrying the private things. (2) THE ON-RAMP TAUGHT THE WRONG PATH. WELCOME.md still described cloning and hand-symlinking 37 skills; it is now two lines and then "set me up". `onboard` was rewritten to assume the plugin is already installed rather than to clone. (3) THE SITE WAS STALE AND HAD NO DOOR. agenticbranduniverse.com claimed FIVE layers against a v0.16 spec with six, and said "working systems you can open right now" while giving a visitor no way to open one. It now leads the spec section with a Start block carrying the two install lines and a link to WELCOME. A new suite, `test_installable.py`, asserts the whole path mechanically, because every gap in this project so far has been invisible until a stranger tried it: manifests exist and parse, the marketplace points at this repo, the payload is actually here, `abu` and `onboard` ship, WELCOME contains no shell blocks, the spec URLs are not the dead domain, and both providers resolve to their vendored copies. Installable is now a check rather than a claim. 10 new tests (suite 627 → 637, ALL GREEN). Plugin 0.44.0 → 0.45.0.

2026-07-30 · FIXED: two things that would each have broken Russ's install on his first session, both found by asking what a STRANGER's filesystem looks like rather than by testing on the machine that already works. (1) FIXED-DEPTH PATHS. Six runtime scripts located the engine by counting `parents[3]`, which encodes exactly one directory layout. This code runs from at least two: a git clone, and a plugin cache under `~/.claude/plugins/cache/`. Counting is right in the clone and silently wrong anywhere else. They now walk UP for a marker (`engine/agenticstory`) and raise an actionable message naming the reinstall command if it is not found. Worth recording WHY the old hardcoded home paths existed at all: the previous plugin shipped only `skills/`, `agents/`, `scripts/` and no engine, so reaching into `~/Documents/github-repos/agenticstory/engine` was the only way it could work; `source: "."` on the self-marketplace is what makes the engine actually travel with the plugin, and the walk-up is what stops the next layout change from breaking it again. (2) PERSONAL PATHS IN SHIPPED PROSE. `make-a-book`, `land-work` and `book-doctor` each instructed the agent to run commands at `~/Documents/github-repos/agenticstory/...`, and `start-new-story-universe` defaulted a new universe into `~/Documents/github-repos/<universe>/`. On any other machine those are directories that do not exist, so the skill would send the agent somewhere empty and fail in a way that looks like the framework is broken. All four are portable now. `evolve-abu` deliberately keeps its absolute paths: it is the MAINTAINER's skill, it edits the framework's own working copy, and it is meaningless without one. Three new tests hold the line: no personal absolute path in any shipped skill, no fixed-depth engine lookup in any runtime script (test harnesses exempt, since they only ever run from a clone), and the root finder resolves correctly from a deep path. 3 new tests (suite 637 → 640, ALL GREEN). Plugin 0.45.0 → 0.46.0.

2026-07-30 · COHERENCE SWEEP after the rename, and the worst finding was on the public site. `site/index.html` claimed SPEC v0.5 in three places against a v0.16 spec, sitting inches from the "five layers" claim against six that had been fixed hours earlier in the same file. That is the summary-layer blind spot the coherence skill names explicitly: a sweep looking for staleness fixed the noun and walked past the number. Both are now correct and, more importantly, `build-docs --check` now VALIDATES the site, collecting every `vN.N` token on the page and allowing only the versions the repo actually declares (SPEC.md's, plus BRAND-OS-SPEC.md's separate draft version). The first cut of that check matched two phrasings, "spec v0.5" and "standard · v0.5", and missed "The spec is v0.5" three inches away, which is precisely how the drift had survived; it now collects tokens rather than phrasings, and was proven by tampering the file and watching the suite go red. Other findings: `agents/abu-steward.md` told the agent to `ls agenticstory/skills/`, a path that exists on one machine, now portable. `docs/agenticstory.html` is an ORPHAN with zero inbound links, titled "Agentic Story" and claiming spec v0.2, fourteen versions stale; left in place and reported, because deleting someone's presentation artifact is their call, not the auditor's. Clean: zero broken internal markdown links across 62 files, all version claims now agree (SPEC.md, engine SPEC_VERSION, README's generated block, the site), and the remaining `agenticstory` strings are the Python package name (20 `agenticstory.cli`), dated plan records under docs/superpowers, and `evolve-abu`, which is the maintainer's own skill and legitimately names the working copy. Also worth recording a self-inflicted scare: a bad `str.index` slice while wiring this check produced a negative-length span, so `replace("", block)` inserted the block at every position and destroyed docsfile.py. `git checkout` restored it in one move because the work was committed, and the same checkout silently reverted the uncommitted site fix, which had to be re-applied. Commit before refactoring the thing that guards your commits. Plugin 0.46.0 → 0.47.0.

2026-07-30 · SITE CLEANUP, and the audit disagreed with the hunch that started it. Gary asked whether the Brand OS is still relevant, guessing not. The evidence says the CONCEPT is very much alive and the DOCUMENT is not: `aitx-brand-os.vercel.app` is deployed and returns 200, cartridge-plus-console is the site's central metaphor, and every one of the site's eight outbound links resolves; but `BRAND-OS-SPEC.md` is a v0.1 early draft, the oldest content file in the repo, untouched since 2026-07-19, and NOTHING in the framework implements it. So the document now carries an honest status note instead of being deleted or quietly left to rot, and the README's one-line description matches it. The bigger find was a genuine contradiction the mechanical passes cannot see: the corpus taught TWO different consoles. The site said a console is a deployed runtime you visit; WELCOME and the `abu` skill say the console is your own agentic harness and ABU is the cartridge you install into it. A reader who read the site and then installed the plugin got two incompatible mental models of the same word, and neither surface acknowledged the other. Both are true, so the fix was to say so: the site's three-part model now defines the console as anything that loads a universe and renders from it, names the two kinds that run today, hosted and your-own-harness, and says "same cartridge, either console". Also fixed: the layer stack still listed FIVE layers under pre-v0.14 names (Brief, Refs, Renderer, retired when Projection and Composition became Form and Work), sitting directly beneath the heading corrected to "Six layers" hours earlier, so the heading contradicted the list beneath it. It now shows Canon, Goldens, Form, Work, Composer, Quality. Checked and deliberately left alone: "projection" in the informal sense, which the README uses the same way ("declaring eight projections"), and "Agentic Story" as the name of the picture-book projection, which is a branding decision rather than rename residue and belongs to Gary. Plugin 0.47.0 → 0.48.0.

2026-07-30 · ONTOLOGY SETTLED on the public site, at Gary's direction and against the evidence rather than against the old copy. He was frank: BRAND-OS-SPEC.md was hackathon work from two weeks ago, "Brand OS" may not even be the right language anymore, and what he has ACTUALLY been doing is maintaining generators and universes and rendering through Claude Code plus the plugin. Counting before rewriting confirmed it: 7 universes on disk (nation-of-fire, hyperagentic-age, souls-of-tech, christofuturism, gary-sheng-art, arts-by-tadeo, gentry-tech-summit), 433 canon entities with 339 in Nation of Fire alone, and 183 books shipped on the platform. Zero of those 183 came from a hosted Brand OS. The site had been teaching that the console is a deployed runtime you visit, which described one hackathon demo and none of the real work. The three-part model now reads: the UNIVERSE is the cartridge, CLAUDE CODE + ABU is the console ("you do not visit a product; you install a cartridge into the console you already use", grounded with the real 183), and the DELIVERABLE is the output. Gary chose "console" over "engine" when offered both, which keeps the site consistent with his own published Playable Harness Experience canon, where the harness IS the console and the experience is the cartridge. "Brand OS" is out of the spine entirely: the hero node, the compile step, the loop copy, the social cards and eleven scattered "the OS renders / the OS runs / any OS can load" phrasings all now say console, and the only surviving mentions are the AITX product's own name and the spec filename. AITX itself is demoted from "the model" to what it honestly is, a hosted console built at a hackathon, proof the same cartridge runs somewhere other than a harness. The link to BRAND-OS-SPEC.md now reads "hosted-console notes (v0.1 draft, superseded)" rather than presenting a stale draft as the OS spec. Plugin 0.48.0 → 0.49.0.

2026-07-30 · DISAMBIGUATED "ABU", which had quietly been doing three jobs at once. Gary caught it: "Claude Code + ABU Agent/plugin is really what I'm saying is the console. Abu is an instance / a bunch of data." He is right, and the collision was introduced by the rename earlier the same day. "ABU" was simultaneously the STANDARD (the cartridge format), the PLUGIN (part of the console), and AN INSTANCE (a specific brand universe, of which 7 exist on disk). The site's slot 2 read "Claude Code + ABU", which parses as Claude Code plus a universe, exactly backwards from what it meant. Three fixes. Slot 2 is now "Claude Code + the ABU plugin" and states the relationship out loud: the plugin READS universes the way a PDF reader reads PDFs, which resolves the ambiguity permanently instead of asking the reader to infer it. The hero diagram node matches. Slot 1 now says what a universe IS in the first clause: "One brand as data... An Agentic Brand Universe is an instance, one per brand, and you can hold many." The naming overlap is not itself a bug (a format and its reader sharing a name is ordinary, as PDF shows) but leaving it unstated on the page where the reader first meets both words was. Plugin 0.49.0 → 0.50.0.

2026-07-30 · TERMINOLOGY SWEPT to the v0.14 vocabulary everywhere a reader can see it. Gary asked to "rename projection to form or whatever, make everything super consistent", and the "or whatever" mattered: FORM was the wrong target. SPEC §4.14 is precise about this. Canon is the matter, a form is what SHAPES it, and a work is canon GIVEN form, so a deliverable is a WORK, not a form. The spec also explicitly KEPT the word projection for one job: "Projection survives as the name of the RELATIONSHIP canon bears to a work, and stops naming either primitive." So the sweep had to be sense-aware rather than a find-and-replace, and three senses had to be told apart. The retired PRIMITIVE sense became form or work depending on whether it named a kind or an instance: the site's slot 3 is now WORK ("one thing a console renders from a universe: canon given form"), the gallery's category chips are FORMS because they name kinds (flyers, merch, memes, social), "many projections" is "many works", the footer chip reads cartridge · console · work, and the headline is now "Agentic storytelling is one form". The RELATIONSHIP sense was preserved untouched, exactly as the spec intends: "Canon is the source of truth, everything else is a projection of it" stays, as does "a work is a projection that writes back" in start-new-story-universe. The ARTISTIC sense was preserved too, and it is the reason a blind replace would have been a disaster: "a scene's composition", "a compositional device", "it catches composition, wrong anatomy" and eight others in compose-spread and on-brand-image are about pictures, not primitives. Also caught: `compose.py` and its skill documented their argument as `<composition.json>` while the framework scaffolds `works/<id>/work.json`, so the usage string named a file the framework no longer produces; 7 occurrences now say `<work.json>`. Files swept: site/index.html, README.md, and the compose, add-form, brand-card, lint-universe, add-story and start-new-story-universe skills. Plugin 0.50.0 → 0.51.0.

2026-07-30 · FIXED THE REST OF THE PUNCH LIST, and the top item was a real break rather than a wording problem. SPEC v0.14 renamed Projection to Form and `add-form` was updated to scaffold `forms/<id>/form.json`, but the two tools that READ that directory never were: `compose` loaded only `projections/<name>.json` and `lint-universe` looked only in `projections/`. So a universe built with today's scaffolder wrote a form the composer could not find at all, while the linter told it "declares no projections" and skipped every projection check. Both readers now try `forms/<id>/form.json` first and fall back to the legacy flat layout, so the 8 forms already shipped in hyperagentic-age keep working. The first cut of that fix was itself half-wrong and worth recording: pointing `pdir` at `forms/` silenced the false warning while `pdir.glob("*.json")` still found NOTHING, because the new layout nests one directory deeper. A check that silently inspects zero files is worse than the missing-directory warning it replaced, so resolution is now a helper that enumerates both shapes, proven against a temp universe in each layout. 3 tests. Also swept: `docs/ARCHITECTURE.md`, linked from the README as "the architecture", still taught "a projection is a type; a composition is an instance" in the very sentence defining the vocabulary (9 fixes); `docs/diagrams/the-layers.svg` still drew COMPOSITION and PROJECTION as layer names; and `site/og.html`, the share card, still called the console "Brand OS". The README claimed "Diagrams included, all machine-emitted" and no generator exists for them, which the hand-edit to the SVG settled, so the claim is gone rather than left standing. Nation of Fire's provenance went back to 10/10: the branch merges brought in 35 images with no records (17 source photos, 12 attested, 3 deterministic, 3 reconstructed), committed as 35 additions with zero non-additions staged. STILL OPEN and reported rather than papered over: `site/og.jpg` is a hand-exported image from 2026-07-19 with no generator, so the picture people actually see when the link is shared still shows the old ontology and only a re-export fixes it; and `docs/ARCHITECTURE.md` links a published standard at appliedai.wiki still named PROJECTION.json, which is cross-repo drift this repo cannot fix. Plugin 0.51.0 → 0.52.0.

2026-07-30 · DELETED the stale, at Gary's "don't be afraid to delete stale files", and REGENERATED the one file that could not simply go. Removed: `BRAND-OS-SPEC.md`, 329 lines of hackathon-era design notes that nothing implemented, that Gary himself said was "probably not that relevant anymore", and whose central claim (the console is a bespoke deployed runtime) the site had already stopped making; its README bullet and site link went with it, and the version allowlist in `docsfile` collapsed to just the spec version now that no second document declares one. Also removed `docs/superpowers/` entirely, 7 files and 124K of phase-by-phase implementation plans dated 2026-07-18 for skills that shipped days later; 4 of the 6 plans had zero inbound references, and every skill they planned (add-character, add-setting, shoot-references) exists. Git keeps all of it; a public repo should not. NOT deleted: `site/og.jpg`, because it is the share image every posted link renders and deleting it would blank the unfurl. It was a hand-export from 2026-07-19 with no generator, so it was REGENERATED from `og.html` with headless Chrome at 1200x630. Looking at the render is what made it worth doing: the card still said "AN OPEN STANDARD · V0.5" and "a Brand OS (the console)", neither of which any grep had surfaced, because both live in the card's own copy rather than in the page it previews. Fixed in the source and re-shot, so the image now reads v0.16 and "a console (Claude Code + the ABU plugin)", matching the site exactly. Plugin 0.52.0 → 0.53.0.

2026-07-30 · ONE SOURCE. `abu` was being advertised by TWO marketplaces at once: the public repo (canonical, carrying engine and providers) and Gary's private `garysheng-claude-plugins`, which held a duplicate `plugins/abu/` fed by `sync-plugin.sh`. The private copy was always the staler of the two by construction, since it only updated when the sync ran. It is deleted, the private marketplace is back to the three plugins that are genuinely private (anthropic-campaign, telontologist, telontology), and `sync-plugin.sh` is retired to a signpost that names the real ship sequence instead of doing anything. `evolve-abu` was rewritten to match: its "Repos and the delivery chain" section described copying skills into a second repo and chasing STALE reports, and every word of that is now false, so it now says there is ONE repo, that the repo IS the marketplace via `source: "."`, and that shipping is commit, push, bump `.claude-plugin/plugin.json`, `/plugin update`. Also swept the last skills naming the dead namespace, with the same sense-aware rule the rename used throughout: `souls-of-tech/README.md` told a reader to "use `agenticstory:update-book`", a live instruction pointing at a verb that no longer resolves, so it is fixed; `wonder-all-you-want-book/RESEARCH.md` records "Gary, 2026-07-19, /agenticstory:render-book invocation" and eight book-level SAVE-LOGs record what was invoked on their dates, so they are untouched. The install was verified END TO END for the first time this session, from the installed cache rather than the repo: `~/.claude/plugins/cache/agentic-brand-universe/abu/0.53.0/` carries engine, providers, forms and registry (not just skills, which is all the OLD plugin ever shipped and exactly why the home-directory hardcoding existed), `abu` graded Nation of Fire B 80/100 running from that path, and both providers resolved INSIDE the cache. The chain a stranger will use is now confirmed rather than assumed. Plugin 0.53.0 → 0.54.0.

2026-07-30 · PROMOTED, from a long book session: two craft rules, plus an honest list of what was NOT promoted. (1) A MULTI-STATE OBJECT'S BLUEPRINT HOLDS THE OBJECT, NOT THE FRAMING. Seeding every state off one code-drawn blueprint is the existing rule and it is not sufficient: on `the-book-of-your-days`, a thin state and a thick state seeded off the same blueprint came back with different cover proportions and read as two different books, which is fatal when the entire argument is that it is the SAME life and it got fuller. Gary caught it ("the thin one should have same length and height as the thick one"). The fix is to pin shared dimensions as NUMBERS in every state's prompt, say what changes and what does not in one sentence, put it on the entity as an invariant so read-back can catch it, and chain a stubborn state off the state that already passed rather than off the blueprint. (2) ASK WITH THE TOOL, NOT WITH PROSE. `make-a-book` already said to use `AskUserQuestion` at a gate, and it was still under-used four times in one session (the glow reading, the beat budget, Lorraine's likeness, the thickness invariant), two of which went unanswered for hours because a question at the end of a long report is easy to scroll past and a tappable option is not. The bar is now explicit: anything with an option set is a tool call, and prose is reserved for questions with no options, which are rare. NOT PROMOTED, and named here so it is not mistaken for done: this session wrote FIVE bespoke shoot scripts in the scratchpad (`shoot-jim.sh`, `glow.sh`, `meadow.sh`, `books.sh`, `books2.sh`), each re-implementing the same loop of style line plus anchor-first plus entity identity plus negatives plus output path. That is `shoot-references`'s own job and `chain_matrix.py` did not serve these entities, so it got hand-rolled five times. It is the exact tell `pave-the-path` names, a scratchpad full of `*.sh` at the end of a run, and it is the largest remaining gap. Also unpromoted: there is no tool to BUILD a real person's photo stack, which was done by hand with yt-dlp and ffmpeg against public interview footage, and `lock-shot` reports a malformed contract as a raw AttributeError rather than a legible message. Plugin 0.54.0 → 0.55.0.

2026-07-30 · PROMOTED: `chain_matrix.py` now REFUSES to shoot from an unfilled `prompts.md`, closing the largest gap the previous entry named. The diagnosis turned out to be sharper than "a tool is missing": the tool already existed and already did chaining, the register anchor, negatives and `--skip-existing`. What was missing was a GATE on the authoring step. `add-entity` scaffolds every shot body as `TODO(author): replace each body below`, nothing checked it, and an agent meeting that stub wrote its prompts inline in five throwaway bash scripts and called the provider directly, because routing around the tool was easier than noticing the step had been skipped. The refusal is wired into `parse_prompts`, the single choke point every shoot passes through, and its message names the anti-pattern explicitly rather than just reporting a missing value. The reason it matters is reproducibility: a prompt in `prompts.md` is versioned, diffable and reused on every re-run, while the same prompt in `/tmp/shoot-thing.sh` is gone when the session ends, so the entity's own art ends up with no recorded intent. Verified by running it against a real stub and watching it refuse. Plugin 0.55.0 → 0.56.0.

2026-07-30 · PROMOTED: the anti-hand-rolling machinery, after Gary asked the question that exposed it ("are we even activating the sub-agent that exists in the plugin?"). The answer was no. `abu-steward` ships in this plugin, its stated job is "reach for the RIGHT framework verb instead of hand-rolling, and FLAG any gap rather than silently working around it", and it was invoked ZERO times across a full book session in which the main agent hand-rolled five shoot scripts, a photo-stack extraction, and prompt assembly the framework already owned. The countermeasure was installed and unused for the entire run. Three changes. (1) `make-a-book` now DISPATCHES the steward per chain step that touches canon or art, rather than merely having it. The reasoning is written down because it is not obvious: the main agent is carrying the book's momentum and is therefore the WORST judge of "should I write a quick script here", while a fresh context whose only question is "which verb is this" has no such incentive and has not spent an hour becoming attached to a plan. (2) The governing principle is now stated in the chain: PROSE DOES NOT BIND, REFUSALS BIND. Every rule broken on 2026-07-30 existed as prose (use AskUserQuestion at a gate, ignored four times; angels are light beings, a European man rendered; show the operator every shot, written that same session then not done). Every rule obeyed was a refusal in code (assert-story, build-docs --check, the uncast-character guard, and the prompts.md TODO refusal that ended a five-times-repeated workaround the moment it existed). So when a rule is broken, do not restate it more emphatically; move it into something that stops you, at the choke point every path already goes through. (3) `pave-the-path` gained `detect_handroll.py`, because discouragement is not detection. It scans a scratchpad for scripts calling a provider directly or hardcoding the register, and a universe for art sitting beside a `prompts.md` that still says TODO(author). Its FIRST RUN returned 79 findings across at least SEVEN different sessions: `shoot.py`, `gen.sh`, `shoot-r1.sh`, `shoot-r2.sh`, `room_variants.py` in scratchpads weeks apart. The expectation was five, from today. Hand-rolling was never an incident, it was the normal usage pattern, invisible the whole time because nothing ever looked. Plugin 0.56.0 → 0.57.0.

## 2026-07-30 — 0.58.0 — two verbs the framework was telling you to work around

`backfill-prompts` (engine, `promptsfile.py`, 11 tests). The inverse of
`backfill-provenance`: it recovers a scaffolded `prompts.md` from the `.recipe.json`
files beside it. Shoot a matrix outside the framework and the art lands with a recipe
while `prompts.md` stays all `TODO(author)`, so the prompt survives only as an
attestation of one past call and never as a live instruction. It refuses to overwrite
an authored body, leaves a shot with no recipe honestly TODO, and appends a heading
when the entity's slots moved after the scaffold was written. Constrained to the
entity's DECLARED sheets, because unconstrained it proposed 384 headings against 21
real recoveries on Nation of Fire. `--entity` scopes the apply; the plan stays
universe-wide. Nation of Fire has 253 recoverable prompts still outstanding.

`chain_matrix.py --shoot-seed`. The chain refused an unblessed seed with the advice
"generate it alone", which is the framework instructing you to leave the framework.
The seed then got shot by a hand-written provider call: no recipe, no register line,
no size from prompts.md, on the one plate every other shot in the matrix inherits
from. Now it shoots the seed through the same code path as every other shot and stops
without blessing it, because a run that shot its own seed and then approved it would
have no human in the loop at all. The per-shot generate was extracted to `_shoot()`
so both paths share it.

Both were found by working a real book (Two Angels and a Forklift) rather than by
reading the framework. 655 tests green.

## 2026-07-30 — voice-gate becomes a script, and a refusal stops eating its own documentation

`voice-gate` shipped as a SKILL.md and nothing else, which made the words-before-art
gate prose, and prose does not bind. Now `scripts/voice_gate.py`, exiting non-zero. It
skips quoted spans, because a verbatim quotation from a real person is never edited to
satisfy a style rule and checking inside quotes rewards paraphrasing a testimony into
house style. `Spirit` capitalisation and the `neverDisparage` list print as REVIEW
rather than blocking: both need a human to read the sense, and a checker that blocks on
them trains the author to pass `--force`. It caught three real intensifiers in Two
Angels and a Forklift and one false positive of its own, `just as`, now excluded along
with the other comparative, temporal and limiting senses of `just`.

`chain_matrix`'s TODO refusal now scans the SHOT BODIES, not the whole file. The
scaffold's own header instruction is literally "TODO(author): replace each body below",
so the whole-file scan could only ever be satisfied by deleting the guidance that tells
an author what a prompt must contain. A refusal whose only remedy is destroying
documentation is one people learn to route around, which is the behaviour it exists to
stop.

Still open, found the same way: `assert-story` checks `requiredForRender` but NOT the
sheets that `structured.render.poses` name. Two Angels passed the gate with seven pose
sheets missing from disk, which `compose-spread` hard-exits on. The gate should catch
what the compiler will refuse.

## 2026-07-30 — 0.60.0 — chain_matrix --look: era plates get a shoot path

`lock-shot --look` could FILE an era plate and `make-a-book` documented at length how one
must be generated, but nothing generated one. So every alt-look in this framework was
either shot by a hand-written provider call or never shot at all, and the second outcome
is silent: the look's prose says "gaunt and grey" while the references passed are the
entity's HEALTHY plates, and a reference image outranks a word. Two Angels and a Forklift
rendered seven illness-era spreads with a hale man in them before anyone looked.

`--look <key>` shoots into `reference/<id>/<look>/` from that look's own prompts.md, and
seeds the chain off the entity's FACE sheets and photo stack rather than
`forward-fullbody`, which is the silhouette the look supersedes.

One correction earned inside the same hour: those face refs are for the SEED ONLY. Passed
to the second shot they carry the very body being superseded, and the `wasted` full-body
came back as a hale man in a blazer with a wings pin against a prompt asking for a thinner
man in loose plain clothes. Once a look has its own blessed plate, that plate is the
identity. `altLooks.dropSheets` then removes the default plates at render time, which took
spread-06's ref list from six images to three.

655 tests green.

## 2026-07-30 — 0.62.0 — the limb-anatomy guard is REVERTED

Added in 0.61.0 and removed the same hour by Gary: "it's over engineering something that
just needs reroll."

He is right, and the distinction is worth keeping even though the code is not. Generation
is stochastic, so a one-off ugly limb is a ROLL, not a rule. Guards are for things that
come back wrong the SAME WAY every time from a knowable cause: a screen painted on the
back of a laptop, a page rotated square to the lens, a figure walking away from the thing
they are walking toward. Those have a mechanism, so a sentence can fix them permanently.
A stretched arm has no mechanism; it is variance, and the cost of the guard is a permanent
paragraph on every braced-figure prompt in every universe, forever, to save one re-roll.

The test for the next candidate guard: can you name the WRONG THING THE MODEL BELIEVES? If
yes, guard it. If the honest answer is "it just came out badly", re-roll and move on.

The craft lesson from the same two spreads stands and cost nothing: on the sleeping
spread, showing LESS of the man beat describing his arm better. Head on the pillow, one
hand at his own chin, everything else a shape under the bedding, and there is no long limb
in frame to get wrong. When a figure is not the subject, crop the problem out.

## 2026-07-30 — 0.63.0 — chain_matrix --look, and the casting sweep that has to cover LOOKS

`--look <key>` shoots a declared alt-look into `reference/<id>/<look>/` from that look's own
prompts.md, seeded off the look's `anchorPhoto` and `photoStack` when it declares them and
off the base FACE sheets otherwise, never off `forward-fullbody`, which is the silhouette
the look supersedes. A look that declares no face reference at all is allowed and says so:
some looks exist to INTRODUCE a face the default matrix never had.

The seed face refs are SEED-ONLY. Passed downstream they carry the body being superseded;
the `wasted` era's full-body came back as a hale man in a blazer against a prompt asking
for a thinner man in loose clothes.

THE EXPENSIVE LESSON, and it is not about code. `add-character` step 1 says sweep canon
for an existing entity before inventing one. That sweep was run over ENTITIES and not over
ALT-LOOKS, so a whole "revealed" look was authored, a colour anchor generated from the
FaithWalk engravings, the entity restructured, and every bit of it already existed:
`the-lord.altLooks.incarnate`, built 2026-07-28 from the same source, non-blue, fully
resolved, Levantine, explicitly never Anglo, with five poses. Reverted whole.

The sweep is not "does this entity exist". It is "does this ENTITY OR ANY OF ITS LOOKS
already cover what I am about to author". An entity with alt-looks is a small canon of its
own, and the looks are where the specific authorizations live.

## 2026-07-30 — 0.64.0 — render_cover.py: the cover generator now reaches the artifact

`compile_cover.py` emitted a JSON job and NOTHING CONSUMED IT. The skill said "never
hand-roll a cover render" and then handed the operator a compiled job with no runner, so
every cover in this framework was in fact hand-rolled. Two Angels and a Forklift shipped a
cover with no title, no byline and no universe mark, because the hand-written version was
authored as an ordinary spread and an ordinary spread does not know a cover carries three
exact strings (Gary: "fix the generator to embed the text on the cover").

A generator that stops one step short of the artifact is a generator nobody uses.

`render_cover.py` runs compile -> generate -> conform -> report, prints the baked strings
so the read-back has something to check that is not the operator's memory, and refuses to
call itself done. `compile_cover.py` now exposes `textLines` on the job for the same reason.

FIXED the same hour, and the cause is worth more than the bug. `compile_cover.py` emitted
`mode: "safe-margin-crop"`, which `conform_cover.py` does not implement: it has `crop` and
`pad` and nothing else. Rather than make the two components agree, the runner translated
between them with a substring test, `"pad" if "pad" in mode else "crop"`. The string
contains "crop", so it chose crop, removed the bottom 171px of a finished cover and took
"A NATION OF FIRE story" with it. `make-a-book` had already said in writing to use
`--mode pad`; a guess overrode a written instruction.

THE RULE (Gary: "crop is not the right move it's to extend what is generated"): A COVER
CONFORM EXTENDS AND NEVER REMOVES. The model emits 2:3 and the reader wants 3:4, so the
image must get WIDER relative to its height. Cropping height to reach that ratio deletes a
strip, and on a cover the bottom strip is the byline and the mark. Padding the sides adds
canvas and loses nothing, which is why the compiled prompt reserves the outer 10% as safe
margin in the first place.

`compile_cover.py` now emits `mode: "pad"`, a mode the conformer actually has, so nothing
downstream has to guess. The general lesson: when two components speak different
vocabularies, make them agree. A translation layer in the middle is a place for a default
to be wrong quietly, and the wrong default here was the destructive one.

## 2026-07-31 — scrapped the slot-model composer (SPEC v0.17, plugin 0.66.0)

Deleted `skills/compose/` (896 lines, 91 tests, ZERO works), and with it `add-form`, `add-work`,
`brand-card` and `forms/scrolling-diorama`, which authored or emitted documents only it consumed.
No `work.json` ever existed in the framework's life; no `work/` or `recipes/` directory was ever
written. It was the most-tested unrun code in the repo, and it had grown its own 30-line
`compile_slot` instead of calling `compose-spread/assemble_prompt.py` — the same disjoint-compiler
failure this framework diagnosed and fixed when it retired the Nation of Fire fork, and which
`compose-spread`'s SKILL.md forbids in a section titled "never fork this". There is now exactly one
compiler.

SPEC §4.8 and §4.9 retire the ENCODING and keep the concept; §4.10 corrects "THE Composer" to a
per-form composer over one shared compiler; §14 is marked ASPIRATIONAL, because nothing here runs
on Managed Agents and the section read as description.

Also found and recorded: the v0.6 changelog claimed the narrative fields had moved into "the
storybook form's slot schema, where they always belonged," with `Story Spec` kept as a back-compat
alias. No storybook form was ever authored, so that migration never happened and `Story Spec` is
still the live primitive every book uses.

DELIBERATELY NOT DONE: the replacement model (golden works + a PROMPT for the console + incremental
evals + an END eval) is NOT written as normative. It waits on the second composer,
`garysheng-art-series`, being built now in `gary-sheng-art-universe`. Authoring it from one instance
is exactly what produced the model just deleted.

Also noted, not fixed: a second checkout at `~/.claude/plugins/marketplaces/agentic-brand-universe`
is 8 plugin versions behind (0.57.0) and still present, despite commit 2b8d06a recording "One
source: retire the private marketplace copy and the sync script". An agent read a stale SPEC from it
for a full session without noticing.

The retired section owned TWELVE lint error codes, not the five the plan predicted (`SLOT-NO-EMITTER`,
`EMITTER-UNKNOWN`, `EMITTER-MISSING`, `SLOT-NO-GENERATOR`, `NO-FORMS`, `EXTENDS-UNRESOLVED`,
`SURFACE-INFEASIBLE`, `NO-PRODUCIBLE-ASPECTS`, `PIN-UNKNOWN-PROVIDER`, `INVARIANT-UNTYPED`,
`NO-INVARIANTS`, `INVARIANT-VS-QUIRK`). 19 tests went with them; lint tests 69 to 50, suite 655 to 545.
`explanatory-plate` survives: it was the `EMITTERS` table's other entry but is standalone-runnable and
emitted every diagram in `docs/ARCHITECTURE.md`. `docs/ARCHITECTURE.md` was itself documenting six of
the deleted codes as live checks. It is hand-authored, so no gate caught it. Fixed in the same branch.
A PRE-EXISTING crash was found and deliberately NOT fixed: `lint.py`'s `rec.get("inputs", [])` returns
`None` on an explicit `"inputs": null`, killing the linter on a real universe. It predates this work
and wants its own commit.

## 2026-07-31 (cont) — the first work after the demolition, and what it cost to make

CORRECTION TO THE ENTRY ABOVE. That entry says no `work.json` ever existed. That was
checked only inside THIS repo and stated as though it covered everything.
`christofuturism-universe/works/fellowship-terrace/work.json` exists, binds
`scrolling-diorama@1.0.0`, and has real assets beside it. What holds is the narrower and
more damning claim: **`compose.py` never ran.** No `recipes/`, no `.state`, and every
asset's recipe carries a `stylePack` key, which only `on-brand-image/generate.py` writes.
Someone wanted a work in that form, wrote the contract, and then made the whole thing
through a different tool. That is stronger evidence for scrapping the executor than
"nobody tried", but the sentence was wrong and the scope of the check did not match it.

`on-brand-image` had **293 works and zero tests**; the composer deleted this morning had
91 tests and zero works. That inversion is now closed: 99 tests, no network, no API key,
validated by five deliberate mutations. They immediately found two bugs in `--permit`,
written hours earlier the same day, and both were the exact silent no-op its loud refusal
existed to prevent: a permit with no `--style-pack` fell through the branch entirely, and
`--permit ""` counted as matching every pole while lifting none, because the lift loop
guarded `t and t in r.lower()` and the unmatched check did not.

Four things shipped on the render path. `--permit` un-rejects one pole for one render,
re-homing the capability `compose.py` had as slot `permits`. `--ref-first` gives an
explicit ref the standing entity refs already had. Renders now OPEN in Preview by default;
`generate.py` had appended `--no-open` unconditionally, so looking at the image, which IS
the gate, required going to find the file. And `Work.validate()` stopped requiring a
pinned `form@version` and non-empty `slots` — the retired §4.8/§4.9 encoding, which the
prose retired everywhere while the engine went on enforcing it.

FOUND BY MAKING SOMETHING, not by review. A trademark passed as ONE padded square
reference rendered as an equilateral star; three edge-to-edge views rendered a true cross.
An accurate invariant reading "the bottom point is DRAMATICALLY longer" warped the mark,
while the same invariant written plainly did not: emphasis over-steers. And an entity's
`prose.rules` is INJECTED INTO THE PROMPT, so a note warning against the word
"dramatically" put that word into every prompt resolving the entity.

The mark is now a `motif` entity with three adopted sheets. Adopted, not shot: it is
deterministic generator output with a USPTO drawing set, and `add-entity` had scaffolded a
TODO telling the next agent to prompt an image model to draw a filed trademark. That file
is now a refusal.

    RESUME: the two-tier ref-ordering problem is open and real. Identity refs (who the
    picture is OF) should outrank fidelity refs (a mark that must be exact) which outrank
    style refs. Today there is one rule and `--ref-first` is a blunt substitute; making the
    mark an entity fixed the mark and pushed the subject's photos to positions 9 and 10,
    weakening the likeness. Also open: SPEC 3a never got the `workRoot` rule written into
    it (the four universes declare it in data, the standard does not describe it), and the
    pre-existing `lint.py` crash on an explicit `"inputs": null` is still unfixed by design.

## 2026-07-31 (cont) — plugin 0.67.0: forms become data, and the render path gets a net

Six commits of capability had shipped at 0.66.0 with no bump, which makes `/plugin update`
a silent no-op. Gary caught it while wrapping: "did we /evolve-abu yet? to increase version
number." Bumped to 0.67.0 and `make-a-work` registered in the manifest catalog, which is
the part that makes a skill discoverable rather than merely present.

NEW SKILL `make-a-work`. The generic front door for any form a universe declares. Born the
moment the question "is there a skill for making a flyer next time?" got the answer "no",
and the obvious fix (write `make-a-flyer`) would have been the same hand-rolling one level
up: a skill per form is not a framework. A form is now a FOLDER at `<universe>/forms/<id>/`
holding FORM.md and PROMPT.md, where PROMPT.md IS that form's composer. Adding a kind of
work adds a folder. `forms.py` discovers and RESOLVES, and its real job is refusing: a
folder without PROMPT.md is not usable, a folder holding only the retired SPEC 4.8
`form.json` is reported as retired rather than offered, an unknown form names what IS
declared, and a form's STATUS warning is surfaced up front because a one-instance form is a
hypothesis an agent would otherwise follow with unearned confidence. 14 tests, all about
the refusals. Deliberately NO scaffolder for authoring a form: until one exists in more
than one universe there is nothing proven to scaffold.

`on-brand-image` went from 293 works and ZERO tests to 99, and they found two bugs in
`--permit` on the day it shipped. Three flags now: `--permit` (un-reject one pole for one
render), `--ref-first` (give an explicit ref the standing entity refs already had), and
renders OPEN in Preview by default because looking at the image IS the gate and it should
not require going to find the file.

`lint-universe` no longer dies on an explicit JSON null. `d.get("k", [])` returns the
default only when the key is ABSENT; present-and-null returns None and iterating it raises.
A linter that dies mid-run reports NOTHING, so one null field hid every real finding in the
universe. The regression test is STRUCTURAL rather than by-example, greps for the bug
CLASS, and immediately found a seventh site the manual pass had missed.

    RESUME: two-tier ref ordering is the open one, and it is real rather than theoretical.
    Identity refs (who the picture is OF) should outrank fidelity refs (a mark that must be
    exact) which outrank style refs. Today there is one rule: making the mark an entity
    fixed the mark and pushed the subject's photos to positions 9 and 10, weakening the
    likeness. `--ref-first` is a blunt substitute. This wants a second work in a DIFFERENT
    universe to test against rather than more theory. Also open: SPEC 3a never got the
    `workRoot` rule written into it, so four universes declare it in data while the standard
    stays silent.
