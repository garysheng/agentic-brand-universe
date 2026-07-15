# SAVE-LOG — Agentic Story

Checkpoint anchors for /save-your-progress (incremental saves read the last line).

The framework (NOT content): a first-principles system for compelling, agentically
writable, composable, evolvable story generation. Destined for `agenticstory.wiki`.
Five layers — Canon → Refs → Story spec → Renderer → Quality; universe-first; canon
medium-neutral; quality = taste × craft × truth; evolution = git; agent-writable by
construction.

2026-07-15T20:33:34Z · 598e16e · FRAMEWORK BORN this session. Spec v0.2 (SPEC.md) folds in 4 findings from backtesting the ~24 existing Nation of Fire books: non-journey story spines, a `visual-metaphor` entity kind, `register` as first-class, a `realPerson` dossier; plus craft-canon-discovered-then-encoded and story `status: stub|full`. README.md + a published presentation Artifact (docs/agenticstory.html — https://claude.ai/code/artifact/002eb4fe-03c3-456d-add3-49cd33b84f8c). Running engine in `engine/` (Python, 11 tests green): model.py (Entity/Relation/StorySpec + validation, StorySpec.status, Entity.is_locked_setting), store.py (CanonStore: loads a universe dir, graph queries, validate_canon; relation targets may be entity OR story), refs.py (resolve_entity_assets, resolve_setting, assert_story = THE pre-render gate, assert_spread), cli.py (validate/list/crossovers/relations/assert-story/assert-spread). Self-contained synthetic fixture in tests/fixtures/example (hero/sage/guide/the-hall) so the engine is decoupled from any content repo. MOST RECENT FIX (598e16e): setting contract splits file_fields (turnaround/blueprint/emptyPlates — must exist on disk) from descriptor_fields (map/blocking/dressing — prose passed in every prompt, must be non-empty), so a locked setting's prose isn't mistaken for missing files.
    RESUME: (a) the engine is proven end-to-end against the NoF universe — `assert-story not-every-fire-is-holy` went red→green when the arena locked; (b) open long-tail is filling NoF story stubs to `full` and migrating the remaining one-off characters + realPerson dossiers; (c) not yet scaffolded to agenticstory.wiki (the /start-new-wiki idea) — spec + engine + published page exist, the public wiki does not. No remote configured on this repo yet.
