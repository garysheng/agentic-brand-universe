# Phase E — Migrate NoF onto the framework (parallel-safe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Move Nation of Fire from its own `nof` plugin onto the generic framework skills, **without breaking the live book pipeline**. Generic skills read `nof-universe`'s data (`identity` + canon + craft-canon); the `nof:*` skills stay live in parallel until a real NoF book is proven on the generic path (then Phase F retires the plugin).

**Strategy (parallel-safe, decided with Gary):** additive first, delete last. Every step adds a generic capability or a data record; nothing removes a working `nof:*` skill until E3 proves the generic path on a real book.

**Sub-phases:**
- **E1 — Generalize the 3 remaining gates:** `canon-resolve`, `casting-sweep`, `voice-gate` become framework skills parameterized by `--universe` + `identity` (render-readback was already generalized in Phase D). Additive; the `nof:*` gates stay.
- **E2 — Craft-canon record type + extract NoF genres:** define a typed craft-canon record (engine + SPEC), then extract NoF's genres/spines (obedient-servant, expectant-biography, visualized-epistle, expectant-future-present-fable, and the register/awe-not-horror/gold-belongs-to-God rules) out of `picture-book`'s prose INTO `nof-universe` craft-canon records the renderer reads. Additive (new records).
- **E3 — Generalize the renderers + prove:** `picture-book`, `cover`, `book-platform`, `update-book` become framework skills reading `identity` + craft-canon; prove ONE real NoF book renders a spread through the generic path with its look intact. Only then Phase F retires the `nof` plugin.

This plan file details **E1** (the immediately-executable, lowest-risk unit). E2 and E3 get their own plans as reached (each is larger and E3 touches real rendering).

## Global Constraints (E1)

- **Parent design:** `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md` (Phase E).
- **Additive + parallel-safe:** author NEW generic skills in `agenticstory/skills/`; do NOT edit or delete any `nof:*` skill in this sub-phase.
- **Generic + universe-parameterized:** each gate takes a target universe (a path with `universe.json`) and reads its data. NEVER hardcode a universe name/path. `voice-gate` reads `identity.voice` (capitalize / oneWord) plus the universal rules.
- **Match the house style:** follow the shape of the existing framework skills (`add-character`, `render-readback`): YAML frontmatter (`name` matching the folder + a rich `description`), then a tight Procedure. No em dashes.
- **Back-compat:** no engine change in E1; `nof-universe` untouched.

**Absolute paths:** framework `/Users/garysheng/Documents/github-repos/agenticstory`.

---

## Task 1: `canon-resolve` (generic gate)

**Files:** Create `skills/canon-resolve/SKILL.md`.

- [ ] **Step 1: Write the skill.** Frontmatter `name: canon-resolve` + a description: "Before writing any render prompt in an Agentic Story universe, resolve EVERY named character/setting/motif to its canon entity: output the locked sheet paths (requiredForRender), the invariants, and the entity's prose rules, then run the load-bearing gate (`assert.sh spread|story`). Prevents reinventing locked designs, passing draft/wrong refs, and prompting from memory. Generic and universe-parameterized." Procedure: (1) take the universe + the list of entities (a spread's cast + location, or a story id). (2) For each entity, read `canon/entities/<id>.json`: its `structured.sheets` (resolve requiredForRender to real paths under assetRoot), `invariants`, and `prose.rules`. Report the exact ref-pass block (which sheet files to pass) + the invariant negatives to bake. (3) Run `python3 -m agenticstory.cli assert-spread <universe> --characters a,b [--location X]` (or `assert-story`); a non-zero exit BLOCKS the render. (4) Output the resolved paths + invariants + the register anchor from `identity.register`. Gates: no render prompt is written until resolve passes; never guess a path or describe from memory.

- [ ] **Step 2: Commit.** `git add skills/canon-resolve/SKILL.md && git commit -m "feat(skill): canon-resolve (generic pre-render ref-resolution gate)"`

---

## Task 2: `casting-sweep` (generic gate)

**Files:** Create `skills/casting-sweep/SKILL.md`.

- [ ] **Step 1: Write the skill.** Frontmatter `name: casting-sweep` + description: "BEFORE naming any new character/setting/motif in a story, sweep the universe's canon for an existing entity that fits the role natively, and emit a casting table (each role: reuse an entity id, or NEW + a one-line justification). Reuse wins by default (it saves the whole reference-matrix build and every reuse is a crossover receipt). Generic and universe-parameterized." Procedure: (1) take the universe + the roles a draft needs. (2) Sweep `canon/entities/` (+ any CANON.md) for entities whose kind/role/description fit each role. (3) Emit the casting table: role -> reused-entity-id, or NEW with a one-sentence justification for why no existing entity fits. (4) For each NEW, hand off to the matching `add-*` skill. Gates: reuse-first is the default; a NEW entity must justify itself against the swept canon.

- [ ] **Step 2: Commit.** `git add skills/casting-sweep/SKILL.md && git commit -m "feat(skill): casting-sweep (generic reuse-first canon sweep)"`

---

## Task 3: `voice-gate` (generic gate)

**Files:** Create `skills/voice-gate/SKILL.md`.

- [ ] **Step 1: Write the skill.** Frontmatter `name: voice-gate` + description: "Run a voice check on any manuscript, narration script, or overlaid caption text BEFORE it is locked or rendered to audio, in an Agentic Story universe. Blocks the lock until the text is clean of the universal rules (no em dashes, no filler, no performative 'not X but Y' inversions) plus the universe's own term rules from `identity.voice` (capitalize / one-word). Generic and universe-parameterized." Procedure: (1) take the universe + the text. (2) Read `identity.voice` (`capitalize` list, `oneWord` list). (3) Check the text against: the universal rules (no em dashes; no filler really/just/very/truly; no 'not X but Y' inversions) AND the universe rules (each `capitalize` term is capitalized; each `oneWord` term is one word). (4) Report every violation with the offending line; BLOCK the lock until clean. Gates: no words lock or render to audio until the voice check passes.

- [ ] **Step 2: Commit.** `git add skills/voice-gate/SKILL.md && git commit -m "feat(skill): voice-gate (generic voice check reading identity.voice)"`

---

## Verification (E1)

- [ ] All 3 skills exist with valid frontmatter (`name` matches folder): `for s in canon-resolve casting-sweep voice-gate; do head -3 skills/$s/SKILL.md | grep -q "^name: $s" && echo "$s OK"; done`.
- [ ] No universe hardcodes: `grep -il "nation of fire\|nof-universe\|\baitx\b" skills/canon-resolve/SKILL.md skills/casting-sweep/SKILL.md skills/voice-gate/SKILL.md` returns nothing.
- [ ] No em dashes: `grep -c "—"` on each returns 0.
- [ ] Parallel-safe: no `nof:*` skill and no `nof-universe` file was modified (E1 is purely additive). `git -C /Users/garysheng/Documents/github-repos/garysheng-claude-plugins status --short` and `git -C /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe status --short` show nothing from this sub-phase.
- [ ] Engine unchanged: `cd engine && python3 -m unittest discover -s tests -p 'test_*.py'` still OK (22).

## Out of scope (E2, E3, F)

- E2: the craft-canon record type + extracting NoF's genres into `nof-universe` records.
- E3: generalizing the renderers + proving one real NoF book on the generic path.
- F: retiring the `nof` plugin (only after E3 proves the generic path).
- Editing or deleting any live `nof:*` skill (that happens in E3/F, after proof).
