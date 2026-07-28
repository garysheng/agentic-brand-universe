# SAVE-LOG — Agentic Story

Checkpoint anchors for /save-your-progress (incremental saves read the last line).

The framework (NOT content): a first-principles system for compelling, agentically
writable, composable, evolvable story generation. Destined for `agenticstory.wiki`.
Five layers — Canon → Refs → Story spec → Renderer → Quality; universe-first; canon
medium-neutral; quality = taste × craft × truth; evolution = git; agent-writable by
construction.

2026-07-15T20:33:34Z · 598e16e · FRAMEWORK BORN this session. Spec v0.2 (SPEC.md) folds in 4 findings from backtesting the ~24 existing Nation of Fire books: non-journey story spines, a `visual-metaphor` entity kind, `register` as first-class, a `realPerson` dossier; plus craft-canon-discovered-then-encoded and story `status: stub|full`. README.md + a published presentation Artifact (docs/agenticstory.html — https://claude.ai/code/artifact/002eb4fe-03c3-456d-add3-49cd33b84f8c). Running engine in `engine/` (Python, 11 tests green): model.py (Entity/Relation/StorySpec + validation, StorySpec.status, Entity.is_locked_setting), store.py (CanonStore: loads a universe dir, graph queries, validate_canon; relation targets may be entity OR story), refs.py (resolve_entity_assets, resolve_setting, assert_story = THE pre-render gate, assert_spread), cli.py (validate/list/crossovers/relations/assert-story/assert-spread). Self-contained synthetic fixture in tests/fixtures/example (hero/sage/guide/the-hall) so the engine is decoupled from any content repo. MOST RECENT FIX (598e16e): setting contract splits file_fields (turnaround/blueprint/emptyPlates — must exist on disk) from descriptor_fields (map/blocking/dressing — prose passed in every prompt, must be non-empty), so a locked setting's prose isn't mistaken for missing files.
    RESUME: (a) the engine is proven end-to-end against the NoF universe — `assert-story not-every-fire-is-holy` went red→green when the arena locked; (b) open long-tail is filling NoF story stubs to `full` and migrating the remaining one-off characters + realPerson dossiers; (c) not yet scaffolded to agenticstory.wiki (the /start-new-wiki idea) — spec + engine + published page exist, the public wiki does not. No remote configured on this repo yet.

2026-07-15T21:53:45Z · 7602284 · SAVE: shipped `agenticstory init` — a TESTED scaffolder that lays down a schema-valid universe (universe.json with a SPEC PROVENANCE block [framework + version + wiki + conformsTo, like a BOOMERANG.md], canon/{entities,relations} + stories dirs, canon README, and the load-bearing `assert.sh` gate). `--example` drops a worked character/setting/story/relation that validates GREEN but whose gate REFUSES until real assets exist (load-bearing self-demo). SPEC_VERSION/SPEC_WIKI canonical in `__init__`; SPEC.md relabeled v0.1→v0.2 (content already carried the 4 backtest findings). 6 new tests → 17 green. NEW SKILL `start-new-story-universe` (repo-local home `agenticstory/skills/`, registered globally via symlink) for one-time universe generation. **PARKED per Gary: not promoted for use until the first book (Not Every Fire Is Holy) ships end-to-end through the framework** — the book is the proof, not the spec's self-description. Still no git remote on this repo.

2026-07-18 · v0.3 + v0.4 arc (24 commits this session) · MASSIVE build. **v0.3:** self-containment invariant (SPEC §3a — a universe owns its assets in its own repo) + Skills & Identity layer (SPEC §11 — framework ships skills, a universe ships data via a `universe.json` `identity` block). Earned by making the Nation of Fire universe self-contained first: 342 canon-referenced assets consolidated out of 44 book folders + 1 external repo INTO the universe (assetRoot flipped `..`→`.`), folder renamed `universe/`→`nof-universe/`, refs swept across repo + skills + 24 book prose files; then the 11 pre-existing not-on-disk defects resolved (2 re-pointed, 9 dead keys removed) → self-containment A=0/B=0/C=0. **v0.4 (framework skill catalog):** built the WHOLE generic catalog — Phase A+B (reference-matrix standard §12 + `lock_level` engine report + register-in-identity), C (7 authoring skills: add-character/-setting/-visual-metaphor/-motif/-prop/-story/-relation + `scaffold_entity`/`add-entity` CLI), D (art: lock-references + render-readback + `lock_shot`/`lock-shot` CLI), E1 (3 generic gates: canon-resolve, casting-sweep, voice-gate). **v0.4.1:** CraftCanon record type (§13, `canon/craft/*.json`, kinds spine|genre|register-rule) + extracted NoF's 7 craft records (obedient-servant spine; expectant-biography / visualized-epistle / expectant-future-present-fable genres; gold-belongs-to-god / testimony-over-prediction / awe-not-horror register-rules) from the picture-book prose. 13 generic skills total; engine 23 tests green. AITX (Michael Daigler's universe) carries its identity+register block and is the live test bed. All parallel-safe: the `nof` plugin + `picture-book` prose are UNTOUCHED and still drive live book-making.
    RESUME: Phases E3 + F remain (parallel-safe strategy chosen by Gary — additive first, delete last). **E3** = generalize the 4 renderers (picture-book, cover, book-platform, update-book) to read `identity` + the new craft records, then PROVE one real NoF book renders a spread through the generic path with its look intact (Gary is the taste gate; this is real image-gen, wants him in the loop). **F** = retire the `nof` plugin only AFTER E3 proves. Plans on disk: `docs/superpowers/plans/2026-07-18-phase-E-migrate-nof.md` (E1 done; E2/E3 noted) + the design umbrella `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md`. NOTE: aitx + nof-universe have Gary's OWN uncommitted WIP canon (aitx antler-venue/jake-oshea/merch; nof-universe the-golden-hour-rooftop/daydream) — left untouched, not mine to commit. nof-universe B=8 is that WIP (the-golden-hour-rooftop art not yet generated), not a regression.

2026-07-18 (cont) · E3 done · Generic renderers built + proven. `render-book` / `cover` / `update-book` authored generic (read identity.register/mark/closingOrnament + craft-canon records + canon-resolve/voice-gate/render-readback; zero universe hardcodes). 16 framework skills total, engine 23 tests. RESOLUTION PROOF on `not-every-fire-is-holy` passed: `assert-story` OK (real 8-entity cast + the-arena resolve from self-contained nof-universe), all 7 craft records present, and `identity.register` added to nof-universe ("soft painterly storybook realism"). Parallel-safe throughout (the `nof` plugin + picture-book/cover/book-platform/update-book prose UNTOUCHED, still drive live book-making).
    RESUME: **Phase F (retire nof plugin) is GATED ON GARY** rendering a real NoF book through the generic `render-book` path and confirming the look holds (deleting working skills is not done on an agent proof alone). Two small steps before F: (1) Gary locks nof-universe's `register.anchor` as a style-anchor FILE on his first render-book run (currently null); (2) DEFERRED: generalize `book-platform` + the garysheng-books `nof-picture-book-reader`/NofBookReader/WispDot/NOF_THEME to read `identity` (platform-code work, its own follow-up). Plan: `docs/superpowers/plans/2026-07-18-phase-E3-generic-renderers.md` (has PROOF RESULT section).

2026-07-18 (cont) · agenticstory PLUGIN built + installed · The 16 generic skills are now an installable plugin (`agenticstory@garysheng`) in the garysheng marketplace, mirrored from `agenticstory/skills/` via `plugins/agenticstory/scripts/sync-from-source.sh` (edit skills in the framework repo, re-sync, commit the marketplace repo). Installed live; nof:* and agenticstory:* run in parallel with no conflict. Gary is DEFERRING the nof-skill retirement (still using nof:* in another session).
    RETIREMENT RECIPE (when Gary is ready, after proving render-book on a real book): in garysheng-claude-plugins, `git rm -r plugins/nof/skills/{picture-book,cover,update-book,canon-resolve,casting-sweep,entity-register,render-readback,voice-gate}`; trim plugins/nof/.claude-plugin/plugin.json's description to just book-platform; commit + push; `/plugin marketplace update garysheng`. KEEP plugins/nof/skills/book-platform (deferred: needs the garysheng-books nof-picture-book-reader/WispDot/NOF_THEME generalized to read identity first). The 8 replaced skills all have generic agenticstory:* equivalents (entity-register -> the add-* family).

2026-07-18T23:24 · 9c56925 · SPEC v0.5 — prompt compiler (§4.6) + entity render block (§4.1); reference impl compile_render.py, first migration jerry-man.

2026-07-23T11:40 · def48ee · **First full day of REAL use: 200 tests (from ~60), and nine structural holes that only execution found.** The judge became a subagent, not an API service (independence is a property of CONTEXT, not vendor). New NEEDS-JUDGMENT state; verdicts bind to the bytes they judged; goldens resolve against the universe root and generation REFUSES on an unresolved reference. Linter merges `extends` before checking and warns on INVARIANT-VS-QUIRK. Composer refuses scenes that name OR imply a rejected pole (negation scope, not word distance, decides it — three wrong versions before one that separates an exclusion from a request). **Biggest finding: a gate made entirely of NEGATIVES optimises toward the empty frame** — a plate passed all eight invariants as a blank rectangle, so `depicts-its-subject` is now checked two-stage and blind on both sides. **Second: nothing here constrains SELECTION.** Every safeguard constrains execution, and all three of the day's worst calls were the maker choosing an easier contract; `surface_shrink` now names it at plan time. Runner rewritten to DISCOVER test files and PARSE counts after it hid a 22-test suite behind `tail -4`.

2026-07-25T13:12:08Z · (pending commit) · NEW META-SKILL `evolve-agentic-story` (plugin v0.6.4). Born from a Christofuturism session that hand-rolled a bespoke image `gen.py` + manual provenance instead of using `on-brand-image` + `lock-references`. The skill encodes the **Promotion Rule** ("fix the generator" principle): when you catch yourself doing framework-shaped work by hand, promote it UP into a skill/engine/spec rather than shipping the one-off; then bump version, run sync-plugin.sh, commit+push BOTH repos, /plugin update, log here, and self-update. Callable mid-session on Gary's frustration ("why are we hand-rolling this / update the templates"). Names the current top gap: **no `create-style-pack` scaffolder** (pack.json + refs/ is hand-made). synced (24 skills); NOT yet delivered (needs commit+push in agenticstory + garysheng-claude-plugins, then /plugin update).

2026-07-25T13:18:39Z · (pending) · NEW SKILL `create-style-pack` (plugin v0.6.5). Scaffolds a Style Pack (SPEC §4.7): pack.json + refs/ (self-contained), copies blessed refs in, requires a read-back gate (refuses a gateless mood board), validates 3-8 refs + content-neutral anchor first. Fills the exact gap evolve-agentic-story named. Pairs with on-brand-image (consumer) + lock-references (locked masters). Born from Christofuturism needing "The Christofuturist" register as a portable pack.

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

2026-07-25 · plugin v0.11.0 · Shipped the agenticstory-steward AGENT (agents/agenticstory-steward.md): a framework-aware subagent whose job is to reach for the right verb instead of hand-rolling and to FLAG (never silently work around) framework gaps, escalating them to evolve-agentic-story. First agent in the plugin; sync-plugin.sh now mirrors agents/ down the same source-marketplace-remote-cache chain as skills. Delivered (both repos pushed); needs /plugin update.

2026-07-25 · engine fix · add-entity scaffolder (authoring.py + model.py SETTING_CONTRACT_FIELDS) now emits scalePlate + scale for settings, matching SPEC v0.9 (scaffold.py already had them; the CLI path was behind). Every add-entity setting was born without the size contract. Caught by formalizing the christofuturism environments as settings. Tests green.

2026-07-25 · plugin v0.12.0 · Shipped universe-doctor: a scorecard skill that grades a universe on a fixed completeness+quality rubric (identity, entity matrices, setting size-contracts v0.9, provenance, craft-canon, stories, self-containment), returns a letter grade + per-dimension scores + an impact-sorted punch-list naming the verb that closes each gap, then works the list. The rubric is the framework definition of a done, good universe. Self-contained grade.py + 5 tests (281 total). First live grade: christofuturism scored D (69/100). Delivered; needs /plugin update.

2026-07-25 · plugin v0.12.3 · compose-spread's uncast-character guard no longer treats DESIGNED TEXT as a person in frame. In-art text is first-class (a cover title, signage, a plaque) and the convention is that the exact string is QUOTED in the scene, so quoted spans are now stripped before name matching. Earned on nation-of-fire/the-higher-law, where a book cover reading 'APOSTLE DELMAR COWARD JR.' AND 'GARY SHENG' demanded two characters be cast who were not in the scene, and the tempting move was the allowUncast escape hatch. Two regression tests (284 total): quoted lettering passes, and an unquoted body standing next to designed text is still caught. Ported the same day rather than left to drift, which is the whole lesson the deprecated NoF fork header records: guards earned in one implementation stayed invisible to the other until their feature sets went disjoint. Delivered; needs /plugin update.

2026-07-25 · meta · evolve-agentic-story corrected itself (step 8). It claimed the delivery chain ran through a git remote and that pushing both repos made a change live; sync-plugin.sh reports the marketplace is a DIRECTORY source, so pushing is hygiene and the installed cache only refreshes on a VERSION CHANGE plus /plugin update. It also carried a stale hardcoded version (0.6.3) and did not warn that editing the marketplace COPY is editing the artifact, which the next sync overwrites from source. All three fixed.

2026-07-25 · plugin v0.13.0 · Promoted three capabilities out of the Nation of Fire fork, measured rather than guessed: cast[].bake (a per-entry prose override that REPLACES the derived block, load-bearing for a multi-state visual-metaphor whose derived block otherwise describes every state and makes the model draw all of them at once), plate selection for ANY non-character kind (a motif or prop could previously only ever be passed its requiredForRender default, so a book that is sometimes open and sometimes shut had no way to say which), and settingRule (book-level, per-spread overridable, extra prose appended to one entity's block so the same room can read colder in a cancellation beat without editing canon). 181, 100 and 44 uses respectively across 31+ nation-of-fire books, all previously expressible only in the fork. Five tests, 289 total, green. This does NOT retire the fork: a new survey tool measured 61 fork specs vs 17 already on the compose-spread schema, and the fork bucket still carries at least six more dialect constructs (spread.refs 468 uses, spread.caption 137, spread.era 50, spread.cast+location 46, top-level story 41, top-level refs 21). The fork is one family of dialects, not one schema. Delivered; needs /plugin update.

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

## 2026-07-27 — `land-work` + `agenticstory land`: branches go home by themselves (plugin v0.20.0)

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

It is repo-generic on purpose: `agenticstory land <repo>` knows nothing about universes, so it
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
    THE LESSON: this session also built a whole second `land` implementation, ~300 lines and 16 tests, because `agenticstory land` failed with `invalid choice`. It failed because the MAIN CHECKOUT was parked on a branch from the previous day; `land` had shipped to master at 12:14 the same day and was working the entire time. A missing CLI verb is exactly the symptom a stale checkout produces, and the check costs one command. **Before concluding the framework lacks something, `git log --oneline master -5` and `git status` in the framework repo.** The duplicate was discarded and master's implementation kept; only the three promotions above survive from that work.

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
